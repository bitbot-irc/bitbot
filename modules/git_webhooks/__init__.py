#--depends-on channel_access
#--depends-on check_mode
#--depends-on commands
#--depends-on shorturl

import itertools, json, re, urllib.parse
from src import ModuleManager, utils
from . import colors, gitea, github, gitlab

FORM_ENCODED = "application/x-www-form-urlencoded"

DEFAULT_EVENT_CATEGORIES = [
    "ping", "code", "pr", "issue", "repo"
]

PRIVATE_SETTING_NAME = "git-show-private"
PRIVATE_SETTING = utils.BoolSetting(PRIVATE_SETTING_NAME,
    "Whether or not to show git activity for private repositories")

@utils.export("channelset", utils.BoolSetting("git-prevent-highlight",
    "Enable/disable preventing highlights"))
@utils.export("channelset", utils.BoolSetting("git-hide-organisation",
    "Hide/show organisation in repository names"))
@utils.export("channelset", utils.BoolSetting("git-hide-prefix",
    "Hide/show command-like prefix on git webhook outputs"))
@utils.export("channelset", utils.BoolSetting("git-shorten-urls",
    "Weather or not git webhook URLs should be shortened"))
@utils.export("botset", PRIVATE_SETTING)
@utils.export("channelset", PRIVATE_SETTING)
class Module(ModuleManager.BaseModule):
    _name = "Webhooks"

    def on_load(self):
        self._github = github.GitHub(self.log, self.exports)
        self._gitea = gitea.Gitea()
        self._gitlab = gitlab.GitLab()

    @utils.hook("api.post.github")
    def _api_github_webhook(self, event):
        return self._webhook("github", "GitHub", self._github,
            event["data"], event["headers"], event["params"])

    @utils.hook("api.post.gitea")
    def _api_gitea_webhook(self, event):
        return self._webhook("gitea", "Gitea", self._gitea,
            event["data"], event["headers"], event["params"])

    @utils.hook("api.post.gitlab")
    def _api_gitlab_webhook(self, event):
        return self._webhook("gitlab", "GitLab", self._gitlab,
            event["data"], event["headers"], event["params"])

    def _webhook(self, webhook_type, webhook_name, handler, payload_str,
            headers, params):
        payload = payload_str.decode("utf8")
        if headers["Content-Type"] == FORM_ENCODED:
            payload = urllib.parse.unquote(urllib.parse.parse_qs(payload)[
                "payload"][0])
        data = json.loads(payload)

        is_private = handler.is_private(data, headers)
        if is_private and not self.bot.get_setting(PRIVATE_SETTING_NAME, True):
            return {"state": "success", "deliveries": 0}

        full_name, repo_username, repo_name, organisation = handler.names(
            data, headers)

        full_name_lower = (full_name or "").lower()
        repo_username_lower = (repo_username or "").lower()
        repo_name_lower = (repo_name or "").lower()
        organisation_lower = (organisation or "").lower()

        branch = handler.branch(data, headers)
        current_events = handler.event(data, headers)

        unfiltered_targets = []
        if "channels" in params:
            channels = params["channels"].split(",")
            for channel in params["channels"].split(","):
                server, _, channel_name = channel.partition(":")
                if server and channel_name:
                    server = self.bot.get_server_by_alias(server)

                    if server and channel_name in server.channels:
                        channel = server.channels.get(channel_name)
                        hooks = channel.get_setting("git-webhooks", {})

                        if hooks:
                            found_hook = self._find_hook(
                                full_name_lower, repo_username_lower,
                                organisation_lower, hooks)

                            if found_hook:
                                unfiltered_targets.append([
                                    server, channel, found_hook])
        else:
            unfiltered_targets = self._find_targets(full_name_lower,
                repo_username_lower, organisation_lower)

        repo_hooked = bool(unfiltered_targets)
        targets = []
        for server, channel, hook in unfiltered_targets:
            if is_private and not channel.get_setting(
                    PRIVATE_SETTING_NAME, False):
                continue

            if (branch and
                    hook["branches"] and
                    not branch in hook["branches"]):
                continue

            hooked_events = []
            for hooked_event in hook["events"]:
                hooked_events.append(handler.event_categories(hooked_event))
            hooked_events = set(itertools.chain(*hooked_events))

            if bool(set(current_events)&set(hooked_events)):
                targets.append([server, channel])

        if not targets:
            if not repo_hooked:
                return None
            else:
                return {"state": "success", "deliveries": 0}

        outputs = handler.webhook(full_name, current_events[0], data, headers)

        if outputs:
            for server, channel in targets:
                source = full_name or organisation
                hide_org = channel.get_setting("git-hide-organisation", False)
                if repo_name and hide_org:
                    source = repo_name

                for output, url in outputs:
                    output = "(%s) %s" % (
                        utils.irc.color(source, colors.COLOR_REPO), output)
                    
                    if channel.get_setting("git-prevent-highlight", False):
                        output = self._prevent_highlight(server, channel,
                            output)

                    if url:
                        if channel.get_setting("git-shorten-urls", False):
                            url = self.exports.get("shorturl")(server, url,
                                context=channel) or url
                        output = "%s - %s" % (output, url)

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

            regex = re.compile(r"([0-9]|\W)(%s)(%s)" % (
                re.escape(user.nickname[0]), re.escape(user.nickname[1:])),
                re.I)
            s = regex.sub("\\1\\2\u200c\\3", s)

        return s

    def _find_targets(self, full_name_lower, repo_username_lower,
            organisation_lower):
        hooks = self.bot.database.channel_settings.find_by_setting(
            "git-webhooks")
        targets = []
        for server_id, channel_name, hooked_repos in hooks:
            found_hook = self._find_hook(full_name_lower, repo_username_lower,
                organisation_lower, hooked_repos)
            server = self.bot.get_server_by_id(server_id)
            if found_hook and server and channel_name in server.channels:
                channel = server.channels.get(channel_name)
                targets.append([server, channel, found_hook])

        return targets

    def _find_hook(self, full_name_lower, repo_username_lower,
            organisation_lower, hooks):
        hooked_repos_lower = {k.lower(): v for k, v in hooks.items()}
        if full_name_lower and full_name_lower in hooked_repos_lower:
            return hooked_repos_lower[full_name_lower]
        elif (repo_username_lower and
                repo_username_lower in hooked_repos_lower):
            return hooked_repos_lower[repo_username_lower]
        elif (organisation_lower and
                organisation_lower in hooked_repos_lower):
            return hooked_repos_lower[organisation_lower]


    @utils.hook("received.command.webhook", min_args=1, channel_only=True)
    def github_webhook(self, event):
        """
        :help: Add/remove/modify a git webhook
        :require_mode: high
        :require_access: admin,git-webhook
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
            if hook_name == None:
                command = "%s%s" % (event["command_prefix"], event["command"])
                raise utils.EventError("Not enough arguments (Usage: %s add <hook>)" % command)

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
