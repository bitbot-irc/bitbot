from src import ModuleManager, utils
from . import colors

EVENT_CATEGORIES = {
    "ping": [
        "ping" # new webhook received
    ],
    "code": ["push"],
    "pr-minimal": [
        "merge_request/open", "merge_request/close", "merge_request/reopen"
    ],
    "pr": [
        "merge_request/open", "merge_request/close", "merge_request/reopen",
        "merge_request/update",
    ],
    "pr-all": ["merge_request"],
    "issue-minimal": [
        "issue/open", "issue/close", "issue/reopen"
    ],
    "issue": [
        "issue/open", "issue/close", "issue/reopen", "issue/update",
    ],
    "issue-all": [
        "issue", "issue_comment"
    ],
    "issue-comment-minimal": [
        "issue_comment/created", "issue_comment/deleted"
    ],
    "repo": [
        "create", # a repository, branch or tag has been created
        "delete", # same as above but deleted
        "release",
        "fork",
        "repository"
    ]
}

COMMENT_ACTIONS = {
    "created": "commented",
    "edited":  "edited a comment",
    "deleted": "deleted a comment"
}

ISSUE_ACTIONS = {
    "open": "opened",
    "close": "closed",
    "reopen": "reopened",
    "update": "updated"
}

class GitLab(object):
    def is_private(self, data, headers):
        if "project" in data:
            return not data["project"]["visibility_level"] == 20
        return False

    def names(self, data, headers):
        full_name = data["project"]["path_with_namespace"]
        repo_username = data["project"]["namespace"]
        repo_name = data["project"]["name"]

        return full_name, repo_username, repo_name, None

    def branch(self, data, headers):
        if "ref" in data:
            return data["ref"].rpartition("/")[2]
        return None

    def event(self, data, headers):
        event = headers["X-GitLab-Event"].rsplit(" ", 1)[0].lower()
        event = event.replace(" ", "_")
        event_action = None
        if ("object_attributes" in data and
                "action" in data["object_attributes"]):
            event_action = "%s/%s" % (
                event, data["object_attributes"]["action"])
        return event, event_action

    def event_categories(self, event):
        return EVENT_CATEGORIES.get(event, [event])

    def webhook(self, full_name, event, data, headers):
        if event == "push":
            return self.push(full_name, data)
        elif event == "merge_request":
            return self.merge_request(full_name, data)
        elif event == "issue":
            return self.issues(full_name, data)
        elif event == "note":
            return self.note(full_name, data)

    def _short_hash(self, hash):
        return hash[:8]

    def push(self, full_name, data):
        outputs = []
        branch = data["ref"].rpartition("/")[2]
        branch = utils.irc.color(branch, colors.COLOR_BRANCH)
        author = utils.irc.bold(data["user_username"])

        if len(data["commits"]) <= 3:
            for commit in data["commits"]:
                hash = commit["id"]
                hash_colored = utils.irc.color(self._short_hash(hash),
                    colors.COLOR_ID)
                message = commit["message"].split("\n")[0].strip()
                url = commit["url"]

                outputs.append(
                    "%s pushed %s to %s: %s - %s"
                    % (author, hash_colored, branch, message, url))
        else:
            first_id = data["before"]
            last_id = data["after"]
            url = data["compare_url"]

            outputs.append("%s pushed %d commits to %s"
                % (author, len(data["commits"]), branch))

        return outputs

    def merge_request(self, full_name, data):
        number = utils.irc.color("!%s" % data["object_attributes"]["iid"],
            colors.COLOR_ID)
        action = ISSUE_ACTIONS[data["object_attributes"]["action"]]
        action_desc = "%s %s" % (action, number)
        branch = data["object_attributes"]["target_branch"]
        colored_branch = utils.irc.color(branch, colors.COLOR_BRANCH)

        if action == "open":
            action_desc = "requested %s merge into %s" % (number,
                colored_branch)
        elif action == "close":
            if data["pull_request"]["merged"]:
                action_desc = "%s %s into %s" % (
                    utils.irc.color("merged", colors.COLOR_POSITIVE), number,
                    colored_branch)
            else:
                action_desc = "%s %s" % (
                    utils.irc.color("closed", colors.COLOR_NEGATIVE), number)

        pr_title = data["object_attributes"]["title"]
        author = utils.irc.bold(data["user"]["username"])
        url = data["object_attributes"]["url"]
        return ["[MR] %s %s: %s - %s" % (
            author, action_desc, pr_title, url)]

    def issues(self, full_name, data):
        number = utils.irc.color("#%s" % data["object_attributes"]["iid"],
            colors.COLOR_ID)
        action = ISSUE_ACTIONS[data["object_attributes"]["action"]]
        issue_title = data["object_attributes"]["title"]
        author = utils.irc.bold(data["user"]["username"])
        url = data["object_attributes"]["url"]

        return ["[issue] %s %s %s: %s - %s" %
            (author, action, number, issue_title, url)]

    def note(self, full_name, data):
        type = data["object_attributes"]["noteable_type"]
        if type in ["Issue", "MergeRequest"]:
            return self.issue_comment(full_name, data)

    def issue_note(self, full_name, data):
        number = utils.irc.color("#%s" % data["object_attributes"]["iid"],
            colors.COLOR_ID)
        type = data["object_attributes"]["noteable_type"]
        type == "issue" if type == "Issue" else "MR"

        issue_title = data["issue"]["title"]
        commenter = utils.irc.bold(data["user"]["username"])
        url = data["object_attributes"]["url"]
        return ["[%s] %s commented on %s: %s - %s" %
            (type, commenter, number, issue_title, url)]
