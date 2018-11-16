import json
from src import ModuleManager, utils

COMMIT_URL = "https://github.com/%s/commit/%s"

COMMENT_ACTIONS = {
    "created": "commented",
    "edited":  "edited a comment",
    "deleted": "deleted a comment"
}

@utils.export("channelset", {"setting": "github-hook",
    "help": ("Disable/Enable showing BitBot's github commits in the "
    "current channel")})
@utils.export("channelset", {"setting": "github-hide-prefix",
    "help": "Hide/show command-like prefix on Github hook outputs",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @utils.hook("api.post.github")
    def github(self, event):
        data = json.loads(event["data"])

        github_event = event["headers"]["X-GitHub-Event"]
        if github_event == "ping":
            return True

        full_name = data["repository"]["full_name"]
        hooks = self.bot.database.channel_settings.find_by_setting(
            "github-hook")
        for i, (server_id, channel_name, values) in list(
                enumerate(hooks))[::-1]:
            if not full_name in values:
                hooks.pop(i)
        if not hooks:
            return None

        outputs = None
        if github_event == "push":
            outputs = self.push(event, full_name, data)
        elif github_event == "commit_comment":
            outputs = self.commit_comment(event, full_name, data)
        elif github_event == "pull_request":
            outputs = self.pull_request(event, full_name, data)
        elif github_event == "pull_request_review":
            outputs = self.pull_request_review(event, full_name, data)
        elif github_event == "pull_request_review_comment":
            outputs = self.pull_request_review_comment(event, full_name, data)
        elif github_event == "issue_comment":
            outputs = self.issue_comment(event, full_name, data)
        elif github_event == "issues":
            outputs = self.issues(event, full_name, data)

        if outputs:
            for server_id, channel_name, _ in hooks:
                for output in outputs:
                    server = self.bot.get_server(server_id)
                    channel = server.channels.get(channel_name)
                    trigger = self._make_trigger(channel, server, output)
                    self.bot.trigger(trigger)

        return True

    def _make_trigger(self, channel, server, line):
        return lambda: self.events.on("send.stdout").call(target=channel,
            module_name="Github", server=server, message=line,
            hide_prefix=channel.get_setting("github-hide-prefix", False))

    def push(self, event, full_name, data):
        outputs = []
        if len(data["commits"]) <= 3:
            for commit in data["commits"]:
                id = commit["id"]

                message = commit["message"].split("\n")
                message = "".join(line.strip() for line in message)
                author = commit["author"]["name"] or commit["author"]["login"]
                author = utils.irc.bold(author)

                url = COMMIT_URL % (full_name, id[:8])

                added = utils.irc.color("+%d" % len(commit["added"]),
                    utils.consts.GREEN)
                added = added+utils.irc.bold("")

                removed = utils.irc.color("-%d" % len(commit["removed"]),
                    utils.consts.RED)
                removed = removed+utils.irc.bold("")

                modified = utils.irc.color("±%d" % len(commit["modified"]),
                    utils.consts.PURPLE)

                outputs.append("(%s) [%s/%s/%s files] commit by '%s': %s - %s"
                    % (full_name, added, removed, modified, author, message,
                    url))

        return outputs


    def commit_comment(self, event, full_name, data):
        action = data["action"]
        commit = data["commit_id"][:8]
        commenter = utils.irc.bold(data["comment"]["user"]["login"])
        url = data["comment"]["html_url"]
        return ["(%s) [commit/%s] %s commented" %
            (full_name, commit, commenter, action)]

    def pull_request(self, event, full_name, data):
        action = data["action"]
        action_desc = action
        if action == "closed":
            if data["pull_request"]["merged"]:
                action_desc = utils.irc.color("merged", utils.consts.GREEN)
            else:
                action_desc = utils.irc.color("closed without merging",
                    utils.consts.RED)
            action_desc = utils.irc.bold(action_desc)
        elif action == "synchronize":
            action_desc = "committed to"

        pr_title = data["pull_request"]["title"]
        author = utils.irc.bold(data["sender"]["login"])
        url = data["pull_request"]["html_url"]
        return ["(%s) [pr] %s %s: %s - %s" %
            (full_name, author, action_desc, pr_title, url)]

    def pull_request_review(self, event, full_name, data):
        if data["review"]["state"] == "commented":
            return []

        action = data["action"]
        pr_title = data["pull_request"]["title"]
        reviewer = utils.irc.bold(data["review"]["user"]["login"])
        url = data["review"]["html_url"]
        return ["(%s) [pr] %s %s a review on: %s - %s" %
            (full_name, reviewer, action, pr_title, url)]

    def pull_request_review_comment(self, event, full_name, data):
        action = data["action"]
        pr_title = data["pull_request"]["title"]
        commenter = data["comment"]["user"]["login"]
        url = data["comment"]["html_url"]
        return ["(%s) [pr] %s %s on a review: %s - %s" %
            (full_name, commenter, COMMENT_ACTIONS[action], pr_title, url)]

    def issues(self, event, full_name, data):
        action = data["action"]
        issue_title = data["issue"]["title"]
        author = utils.irc.bold(data["sender"]["login"])
        url = data["issue"]["html_url"]
        return ["(%s) [issue] %s %s: %s - %s" %
            (full_name, author, action, issue_title, url)]
    def issue_comment(self, event, full_name, data):
        action = data["action"]
        issue_title = data["issue"]["title"]
        type = "pr" if "pull_request" in data["issue"] else "issue"
        commenter = utils.irc.bold(data["comment"]["user"]["login"])
        url = data["comment"]["html_url"]
        return ["(%s) [%s] %s %s on: %s - %s" %
            (full_name, type, commenter, COMMENT_ACTIONS[action], issue_title,
            url)]
