#--depends-on config
#--depends-on shorturl

import difflib, hashlib, time, re
from src import ModuleManager, utils
import feedparser

RSS_INTERVAL = 60 # 1 minute

SETTING_BIND = utils.Setting("rss-bindhost",
    "Which local address to bind to for RSS requests", example="127.0.0.1")
@utils.export("botset", utils.IntSetting("rss-interval",
    "Interval (in seconds) between RSS polls", example="120"))
@utils.export("channelset", utils.BoolSetting("rss-shorten",
    "Whether or not to shorten RSS urls"))
@utils.export("channelset", utils.Setting("rss-format", "Format of RSS announcements", example="${longtitle}: ${title} - ${link} [${author}]"))
@utils.export("serverset", SETTING_BIND)
@utils.export("channelset", SETTING_BIND)
class Module(ModuleManager.BaseModule):
    _name = "RSS"
    def _migrate_formats(self):
        count = 0
        migration_re = re.compile(r"(?:\$|{)+(?P<variable>[^}:\s]+)(?:})?")
        old_formats = self.bot.database.execute_fetchall("""
            SELECT channel_id, value FROM channel_settings
            WHERE setting = 'rss-format'
        """)

        for channel_id, format in old_formats:
            new_format = migration_re.sub(r"${\1}", format)
            self.bot.database.execute("""
                UPDATE channel_settings SET value = ?
                WHERE setting = 'rss-format'
                AND channel_id = ?
            """, [new_format, channel_id])
            count += 1

        self.log.info("Successfully migrated %d rss-format settings" % count)

    def on_load(self):
        if not self.bot.get_setting("rss-fmt-migration", False):
            self.log.info("Attempting to migrate old rss-format settings")
            self._migrate_formats()
            self.bot.set_setting("rss-fmt-migration", True)
        self.timers.add("rss-feeds", self._timer,
            self.bot.get_setting("rss-interval", RSS_INTERVAL))

    def _format_entry(self, server, channel, feed_title, entry, shorten):
        link = entry.get("link", None)
        if shorten:
            try:
                link = self.exports.get("shorturl")(server, link)
            except:
                pass
        link = "%s" % link if link else ""

        variables = dict(
            longtitle=feed_title or "",
            title=utils.parse.line_normalise(utils.http.strip_html(
                entry["title"])),
            link=link or "",
            author=entry.get("author", "unknown author") or "",
        )
        variables.update(entry)

        # just in case the format starts keyerroring and you're not sure why
        self.log.trace("RSS Entry: " + str(entry))
        template = channel.get_setting("rss-format", "${longtitle}: ${title} by ${author} - ${link}")
        _, formatted = utils.parse.format_token_replace(template, variables)
        return formatted


    def _timer(self, timer):
        start_time = time.monotonic()
        self.log.trace("Polling RSS feeds")

        timer.redo()
        hook_settings = self.bot.database.channel_settings.find_by_setting(
            "rss-hooks")
        hooks = {}
        for server_id, channel_name, urls in hook_settings:
            server = self.bot.get_server_by_id(server_id)
            if server and channel_name in server.channels:
                channel = server.channels.get(channel_name)
                for url in urls:
                    bindhost = channel.get_setting("rss-bindhost",
                        server.get_setting("rss-bindhost", None))

                    if url.startswith("www."):
                        url = url.replace("www.", "", 1)

                    key = (url, bindhost)
                    if not key in hooks:
                        hooks[key] = []

                    hooks[key].append((server, channel))

        if not hooks:
            return

        requests = []
        for url, bindhost in hooks.keys():
            requests.append(utils.http.Request(url, id=f"{url} {bindhost}",
                bindhost=bindhost))

        pages = utils.http.request_many(requests)

        for (url, bindhost), channels in hooks.items():
            key = f"{url} {bindhost}"
            if not key in pages:
                # async url get failed
                continue

            try:
                data = pages[key].decode()
            except Exception as e:
                self.log.error("Failed to decode rss URL %s", [url],
                    exc_info=True)
                continue

            feed = feedparser.parse(data)
            feed_title = feed["feed"].get("title", None)
            max_ids = len(feed["entries"])*10

            for server, channel in channels:
                seen_ids = channel.get_setting("rss-seen-ids-%s" % url, [])
                valid = 0
                for entry in feed["entries"][::-1]:
                    entry_id, entry_id_hash = self._get_id(entry)
                    if entry_id_hash in seen_ids or entry_id in seen_ids:
                        continue

                    if valid == 3:
                        continue
                    valid += 1

                    shorten = channel.get_setting("rss-shorten", False)
                    output = self._format_entry(server, channel, feed_title, entry,
                        shorten)

                    self.events.on("send.stdout").call(target=channel,
                        module_name="RSS", server=server, message=output)
                    seen_ids.append(entry_id_hash)

                if len(seen_ids) > max_ids:
                    seen_ids = seen_ids[len(seen_ids)-max_ids:]
                channel.set_setting("rss-seen-ids-%s" % url, seen_ids)

        total_milliseconds = (time.monotonic() - start_time) * 1000
        self.log.trace("Polled RSS feeds in %fms", [total_milliseconds])

    def _get_id(self, entry):
        entry_id = entry.get("id", entry["link"])
        entry_id_hash = hashlib.sha1(entry_id.encode("utf8")).hexdigest()
        return entry_id, "sha1:%s" % entry_id_hash

    def _get_entries(self, url, max: int=None):
        try:
            feed = feedparser.parse(utils.http.request(url).data)
        except Exception as e:
            self.log.warn("failed to parse RSS %s", [url], exc_info=True)
            feed = None
        if not feed or not feed["feed"]:
            return None, None

        entry_ids = []
        for entry in feed["entries"]:
            entry_ids.append(entry.get("id", entry["link"]))
        return feed["feed"].get("title", None), feed["entries"][:max]

    @utils.hook("received.command.rss", min_args=1, channel_only=True)
    def rss(self, event):
        """
        :help: Modify RSS/Atom configuration for the current channel
        :usage: list
        :usage: add <url>
        :usage: remove <url>
        :permission: rss
        """
        changed = False
        message = None

        rss_hooks = event["target"].get_setting("rss-hooks", [])

        subcommand = event["args_split"][0].lower()
        if subcommand == "list":
            event["stdout"].write("RSS hooks: %s" % ", ".join(rss_hooks))
        elif subcommand == "add":
            if not len(event["args_split"]) > 1:
                raise utils.EventError("Please provide a URL")

            url = utils.http.url_sanitise(event["args_split"][1])
            if url in rss_hooks:
                raise utils.EventError("That URL is already being watched")

            title, entries = self._get_entries(url)
            if entries == None:
                raise utils.EventError("Failed to read feed")

            seen_ids = [self._get_id(e)[1] for e in entries]
            event["target"].set_setting("rss-seen-ids-%s" % url, seen_ids)

            rss_hooks.append(url)
            changed = True
            message = "Added RSS feed"
        elif subcommand == "remove":
            if not len(event["args_split"]) > 1:
                raise utils.EventError("Please provide a URL")

            url = utils.http.url_sanitise(event["args_split"][1])
            if not url in rss_hooks:
                matches = difflib.get_close_matches(url, rss_hooks, cutoff=0.5)
                if matches:
                    raise utils.EventError("Did you mean %s ?" % matches[0])
                else:
                    raise utils.EventError("I'm not watching that URL")
            rss_hooks.remove(url)
            changed = True
            message = "Removed RSS feed"
        elif subcommand == "read":
            url = None
            if not len(event["args_split"]) > 1:
                if len(rss_hooks) == 1:
                    url = rss_hooks[0]
                else:
                    raise utils.EventError("Please provide a url")
            else:
                url = event["args_split"][1]

            title, entries = self._get_entries(url)
            if not entries:
                raise utils.EventError("%s has no entries" % url)

            shorten = event["target"].get_setting("rss-shorten", False)
            out = self._format_entry(event["server"], event["target"], title, entries[0],
                shorten)
            event["stdout"].write(out)
        else:
            raise utils.EventError("Unknown subcommand '%s'" % subcommand)

        if changed:
            if rss_hooks:
                event["target"].set_setting("rss-hooks", rss_hooks)
            else:
                event["target"].del_setting("rss-hooks")
            event["stdout"].write(message)
