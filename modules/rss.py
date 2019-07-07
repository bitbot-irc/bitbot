from src import ModuleManager, utils
import feedparser

RSS_INTERVAL = 60 # 1 minute

def _format_entry(feed_title, entry):
    title = entry["title"]

    author = entry.get("author", None)
    author = " by %s" % author if author else ""

    link = entry.get("link", None)
    link = " - %s" % link if link else ""

    feed_title_str = "%s: " % feed_title if feed_title else ""

    return "%s%s%s%s" % (feed_title_str, title, author, link)

@utils.export("botset", utils.IntSetting("rss-interval",
    "Interval (in seconds) between RSS polls", example="120"))
class Module(ModuleManager.BaseModule):
    _name = "RSS"
    def on_load(self):
        self.timers.add("rss", self.bot.get_setting("rss-interval",
            RSS_INTERVAL))

    @utils.hook("timer.rss")
    def timer(self, event):
        event["timer"].redo()
        hook_settings = self.bot.database.channel_settings.find_by_setting(
            "rss-hooks")
        hooks = {}
        for server_id, channel_name, urls in hook_settings:
            server = self.bot.get_server_by_id(server_id)
            if server and channel_name in server.channels:
                channel = server.channels.get(channel_name)
                for url in urls:
                    if not url in hooks:
                        hooks[url] = []
                    hooks[url].append((server, channel))

        for url, channels in hooks.items():
            try:
                data = utils.http.request(url)
                feed = feedparser.parse(data.data)
                feed["feed"] or ValueError("Feed info empty")
            except Exception as e:
                self.log.warn("Failed to GET RSS for %s: %s",
                    [url, str(e)])
                continue

            feed_title = feed["feed"].get("title", None)
            entry_formatted = {}

            for server, channel in channels:
                seen_ids = channel.get_setting("rss-seen-ids-%s" % url, [])
                new_ids = []
                valid = 0
                for entry in feed["entries"][::-1]:
                    if entry["id"] in seen_ids:
                        new_ids.append(entry["id"])
                        continue

                    if valid == 3:
                        continue
                    valid += 1

                    if not entry["id"] in entry_formatted:
                        output = _format_entry(feed_title, entry)
                        entry_formatted[entry["id"]] = output
                    else:
                        output = entry_formatted[entry["id"]]

                    self.events.on("send.stdout").call(target=channel,
                        module_name="RSS", server=server, message=output)
                    new_ids.append(entry["id"])

                channel.set_setting("rss-seen-ids-%s" % url, new_ids)

    def _check_url(self, url):
        try:
            data = utils.http.request(url)
            feed = feedparser.parse(data.data)
        except Exception as e:
            self.log.warn("failed to parse RSS %s", [url], exc_info=True)
            feed = None
        if not feed or not feed["feed"]:
            return None
        return [entry["id"] for entry in feed["entries"]]

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

            url = event["args_split"][1]
            if url in rss_hooks:
                raise utils.EventError("That URL is already being watched")

            seen_ids = self._check_url(url)
            if seen_ids == None:
                raise utils.EventError("Failed to read feed")
            event["target"].set_setting("rss-seen-ids-%s" % url, seen_ids)

            rss_hooks.append(url)
            changed = True
            message = "Added RSS feed"
        elif subcommand == "remove":
            if not len(event["args_split"]) > 1:
                raise utils.EventError("Please provide a URL")

            url = event["args_split"][1]
            if not url in rss_hooks:
                raise utils.EventError("I'm not watching that URL")
            rss_hooks.remove(url)
            changed = True
            message = "Removed RSS feed"
        else:
            raise utils.EventError("Unknown subcommand '%s'" % subcommand)

        if changed:
            if rss_hooks:
                event["target"].set_setting("rss-hooks", rss_hooks)
            else:
                event["target"].del_setting("rss-hooks")
            event["stdout"].write(message)
