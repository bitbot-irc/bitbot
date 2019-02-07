from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.traviswebhook", min_args=1)
    def travis_webhook(self, event):
        """
        :help: List/add/remove travis webhooks
        :require_mode: high
        :permission: githuboverride
        :usage: list
        :usage: add <repository>
        :usage: remove <repository>
        """
        all_hooks = event["target"].get_setting("travis-hooks", {})
        hook_name = None
        existing_hook = None
        if len(event["args_split"]) > 1:
            hook_name = event["args_split"][1]
            for existing_hook_name in all_hooks.keys():
                if existing_hook_name.lower() == hook.lower():
                    existing_hook = existing_hook_name
                    break

        subcommand = event["args_split"][0].lower()
        if subcommand == "list":
            event["stdout"].write("Registered web hooks: %s" %
                ", ".join(all_hooks.keys()))
        elif subcommand == "add":
            if existing_hook:
                event["stderr"].write("There's already a hook for %s" %
                    hook_name)
                return

            all_hooks[hook_name] = {"events", []}
            event["target"].set_setting("travis-hooks", all_hooks)
            event["stdout"].write("Added hook for %s" % hook_name)
        elif subcommand == "remove":
            if not existing_hook:
                event["stderr"].write("No hook found for %s" % hook_name)
                return
            del all_hooks[existing_hook]
            if all_hooks:
                event["target"].set_setting("travis-hooks", all_hooks)
            else:
                event["target"].del_setting("travis-hooks")
            event["stdout"].write("Removed hook for %s" % hook_name)
        else:
            event["stderr"].write("Unknown command '%s'" %
                event["args_split"][0])


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
