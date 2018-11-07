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
    "current channel"), "hidden": True})
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
                    channel = server.get_channel(channel_name)
                    trigger = self._make_trigger(channel, server, output)
                    self.bot.trigger(trigger)

        return True

    def _make_trigger(self, channel, server, line):
        return lambda: self.events.on("send.stdout").call(target=channel,
            module_name="Github", server=server, message=line, hide_prefix=True)

    def push(self, event, full_name, data):
        outputs = []
        for commit in data["commits"]:
            id = commit["id"]

            message = commit["message"].split("\n")
            message = [line.strip() for line in message]
            message = " ".join(message)

            author = "%s <%s>" % (commit["author"]["username"],
                commit["author"]["email"])
            modified_count = len(commit["modified"])
            added_count = len(commit["added"])
            removed_count = len(commit["removed"])
            url = COMMIT_URL % (full_name, id[:8])

            outputs.append("(%s) [files: +%d ∆%d -%d] commit by '%s': %s - %s"
                % (full_name, added_count, modified_count, removed_count,
                author, message, url))
        return outputs


    def commit_comment(self, event, full_name, data):
        action = data["action"]
        commit = data["commit_id"][:8]
        commenter = data["comment"]["user"]["login"]
        url = data["comment"]["html_url"]
        return ["(%s) [commit/%s] %s commented" %
            (full_name, commit, commenter, action)]

    def pull_request(self, event, full_name, data):
        action = data["action"]
        action_desc = action
        if action == "closed":
            if data["pull_request"]["merged"]:
                action_desc = utils.irc.color("merged", utils.irc.COLOR_GREEN)
            else:
                action_desc = utils.irc.color("closed without merging",
                    utils.irc.COLOR_RED)

        pr_title = data["pull_request"]["title"]
        author = data["sender"]["login"]
        url = data["pull_request"]["html_url"]
        return ["(%s) [pr] %s %s: %s - %s" %
            (full_name, author, action_desc, pr_title, url)]

    def pull_request_review(self, event, full_name, data):
        if data["review"]["state"] == "commented":
            return []

        action = data["action"]
        pr_title = data["pull_request"]["title"]
        reviewer = data["review"]["user"]["login"]
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
        author = data["sender"]["login"]
        url = data["issue"]["html_url"]
        return ["(%s) [issue] %s %s: %s - %s" %
            (full_name, author, action, issue_title, url)]
    def issue_comment(self, event, full_name, data):
        action = data["action"]
        issue_title = data["issue"]["title"]
        type = "pr" if "pull_request" in data["issue"] else "issue"
        commenter = data["comment"]["user"]["login"]
        url = data["comment"]["html_url"]
        return ["(%s) [%s] %s %s on: %s - %s" %
            (full_name, type, commenter, COMMENT_ACTIONS[action], issue_title,
            url)]
