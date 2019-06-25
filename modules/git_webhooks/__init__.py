#--depends-on channel_access
#--depends-on check_mode
#--depends-on commands
#--depends-on shorturl

import itertools, json, re, urllib.parse
from src import ModuleManager, utils
from . import colors, gitea, github

FORM_ENCODED = "application/x-www-form-urlencoded"

DEFAULT_EVENT_CATEGORIES = [
    "ping", "code", "pr", "issue", "repo"
]

@utils.export("channelset", {"setting": "git-prevent-highlight",
    "help": "Enable/disable preventing highlights",
    "validate": utils.bool_or_none, "example": "on"})
@utils.export("channelset", {"setting": "git-hide-organisation",
    "help": "Hide/show organisation in repository names",
    "validate": utils.bool_or_none, "example": "on"})
@utils.export("channelset", {"setting": "git-hide-prefix",
    "help": "Hide/show command-like prefix on git webhook outputs",
    "validate": utils.bool_or_none, "example": "on"})
class Module(ModuleManager.BaseModule):
    _name = "Webhooks"

    def on_load(self):
        self._github = github.GitHub()
        self._gitea = gitea.Gitea()

    @utils.hook("api.post.github")
    def _api_github_webhook(self, event):
        return self._webhook("github", "GitHub", self._github,
            event["data"], event["headers"])

    @utils.hook("api.post.gitea")
    def _api_gitea_webhook(self, event):
        return self._webhook("gitea", "Gitea", self._gitea,
            event["data"], event["headers"])

    def _webhook(self, webhook_type, webhook_name, handler, payload_str,
            headers):
        payload = payload_str.decode("utf8")
        if headers["Content-Type"] == FORM_ENCODED:
            payload = urllib.parse.unquote(urllib.parse.parse_qs(payload)[
                "payload"][0])
        data = json.loads(payload)

        if handler.is_private(data, headers):
            return {"state": "success", "deliveries": 0}

        full_name, repo_username, repo_name, organisation = handler.names(
            data, headers)
        branch = handler.branch(data, headers)
        current_event, event_action = handler.event(data, headers)

        hooks = self.bot.database.channel_settings.find_by_setting(
            "git-webhooks")

        targets = []
        repo_hooked = False

        for server_id, channel_name, hooked_repos in hooks:
            found_hook = None
            if full_name and full_name in hooked_repos:
                found_hook = hooked_repos[full_name]
            elif repo_username and repo_username in hooked_repos:
                found_hook = hooked_repos[repo_username]
            elif organisation and organisation in hooked_repos:
                found_hook = hooked_repos[organisation]
            else:
                continue

            repo_hooked = True
            server = self.bot.get_server_by_id(server_id)
            if server and channel_name in server.channels:
                if (branch and
                        found_hook["branches"] and
                        not branch in found_hook["branches"]):
                    continue

                events = []
                for hooked_event in found_hook["events"]:
                    events.append(handler.event_categories(hooked_event))
                events = list(itertools.chain(*events))

                channel = server.channels.get(channel_name)
                if (current_event in events or
                        (event_action and event_action in events)):
                    targets.append([server, channel])

        if not targets:
            if not repo_hooked:
                return None
            else:
                return {"state": "success", "deliveries": 0}

        outputs = handler.webhook(full_name, current_event, data, headers)

        if outputs:
            for server, channel in targets:
                source = full_name or organisation
                hide_org = channel.get_setting("git-hide-organisation", False)
                if repo_name and hide_org:
                    source = repo_name

                for output in outputs:
                    output = "(%s) %s" % (
                        utils.irc.color(source, colors.COLOR_REPO), output)

                    if channel.get_setting("git-prevent-highlight", False):
                        output = self._prevent_highlight(server, channel,
                            output)

                    hide_prefix = channel.get_setting("git-hide-prefix", False)
                    self.events.on("send.stdout").call(target=channel,
                        module_name=webhook_name, server=server, message=output,
                        hide_prefix=hide_prefix)

        return {"state": "success", "deliveries": len(targets)}

    def _prevent_highlight(self, server, channel, s):
        for user in channel.users:
            if len(user.nickname) == 1:
                # if we don't ignore 1-letter nicknames, the below while loop
                # will fire indefininitely.
                continue

            regex = re.compile(r"(.)\b(%s)(%s)" % (
                re.escape(user.nickname[0]), re.escape(user.nickname[1:])),
                re.I)
            s = regex.sub("\\1\\2\u200c\\3", s)

        return s

    @utils.hook("received.command.webhook", min_args=1, channel_only=True)
    def github_webhook(self, event):
        """
        :help: Add/remove/modify a git webhook
        :require_mode: high
        :require_access: git-webhook
        :permission: gitoverride
        :usage: list
        :usage: add <hook>
        :usage: remove <hook>
        :usage: events <hook> [category [category ...]]
        :usage: branches <hook> [branch [branch ...]]
        """
        all_hooks = event["target"].get_setting("git-webhooks", {})
        hook_name = None
        existing_hook = None
        if len(event["args_split"]) > 1:
            hook_name = event["args_split"][1]
            for existing_hook_name in all_hooks.keys():
                if existing_hook_name.lower() == hook_name.lower():
                    existing_hook = existing_hook_name
                    break

        success_message = None

        subcommand = event["args_split"][0].lower()
        if subcommand == "list":
            event["stdout"].write("Registered webhooks: %s" %
                ", ".join(all_hooks.keys()))
        elif subcommand == "add":
            if existing_hook:
                raise utils.EventError("There's already a hook for %s" %
                    hook_name)

            all_hooks[hook_name] = {
                "events": DEFAULT_EVENT_CATEGORIES.copy(),
                "branches": [],
            }
            success_message = "Added hook for %s" % hook_name

        elif subcommand == "remove":
            if not existing_hook:
                raise utils.EventError("No hook found for %s" % hook_name)

            del all_hooks[existing_hook]
            success_message = "Removed hook for %s" % hook_name

        elif subcommand == "events":
            if not existing_hook:
                raise utils.EventError("No hook found for %s" % hook_name)

            if len(event["args_split"]) < 3:
                event["stdout"].write("Events for hook %s: %s" %
                    (hook_name, " ".join(all_hooks[existing_hook]["events"])))
            else:
                new_events = [e.lower() for e in event["args_split"][2:]]
                all_hooks[existing_hook]["events"] = new_events
                success_message = "Updated events for hook %s" % hook_name
        elif subcommand == "branches":
            if not existing_hook:
                raise utils.EventError("No hook found for %s" % hook_name)

            if len(event["args_split"]) < 3:
                branches = ",".join(all_hooks[existing_hook]["branches"])
                event["stdout"].write("Branches shown for hook %s: %s" %
                    (hook_name, branches))
            else:
                all_hooks[existing_hook]["branches"] = event["args_split"][2:]
                success_message = "Updated branches for hook %s" % hook_name
        else:
            event["stderr"].write("Unknown command '%s'" %
                event["args_split"][0])

        if not success_message == None:
            if all_hooks:
                event["target"].set_setting("git-webhooks", all_hooks)
            else:
                event["target"].del_setting("git-webhooks")

            event["stdout"].write(success_message)
