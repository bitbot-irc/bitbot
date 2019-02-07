from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("api.post.travis")
    def webhook(self, event):
        payload = urllib.parse.unquote(urllib.parse.parse_qs(
            event["data"].decode("utf8"))[0])
        data = json.loads(payload)

        repo_fullname = event["data"]["headers"]["Travis-Repo-Slug"]
        repo_organisation, repo_name = repo_fullname.split("/", 1)

        hooks = self.bot.database.channel_settings.find_by_setting(
            "travis-hooks")
        targets = []

        repo_hooked = False
        for server_id, channel_name, hooked_repos in hooks:
            found_hook = None
            if repo_fullname and repo_fullname in hooked_repos:
                found_hook = hooked_repos[repo_fullname]
            elif repo_organisation and repo_organisation in hooked_repos:
                found_hook = hooked_repos[repo_organisation]

            if found_hook:
                repo_hooked = True
                server = self.bot.get_server(server_id)
                if server and channel_name in server.channels:
                    targets.append([server, channel])

        if not targets:
            return "" if repo_hooked else None

        summary = self._summary(data)

        if summary:
            for server, channel in targets:
                output = "(%s) %s" % (repo_fullname, summary)

                hide_prefix = channel.get_setting("travis-hide-prefix",
                    False)
                self.events.on("send.stdout").call(target=channel,
                    module_name="Travis", server=server, message=output,
                    hide_prefix=hide_prefix)

        return ""

    def _summary(self, data):
        result_color = utils.consts.RED
        if data["result"] == 0:
            result_color = utils.consts.GREEN
        result = utils.irc.color(data["result_mesasge"], result_color)

        commit = utils.irc.bold(data["commit"][:8])

        type_source = ""
        if data["type"] == "pull_request":
            pr_number = data["pull_request_number"]
            pr = utils.irc.color("PR#%d" % pr_number, utils.consts.LIGHTBLUE)
            type_source = "%s @%s" % (pr, commit)
        else:
            branch = utils.irc.color(data["branch"], utils.consts.LIGHTBLUE)
            type_source = "%s @%s" % (branch, commit)

        timing = ""
        if data["finished_at"]:
            timing = " in %ds" % data["duration"]

        url = self.exports.get("shortlink")(data["build_url"])
        return "[%s] Build %d %s%s - %s" % (
            type_source, data["number"], result, timing, url)
