from src import ModuleManager, utils
from . import colors

EVENT_CATEGORIES = {
    "ping": [
        "ping" # new webhook received
    ],
    "code": ["push"],
    "pr-minimal": [
        "merge_request/open", "merge_request/close", "merge_request/reopen",
        "merge_request/merge"
    ],
    "pr": [
        "merge_request/open", "merge_request/close", "merge_request/reopen",
        "merge_request/update", "merge_request/merge", "note+mergerequest",
        "confidential_note+mergerequest"
    ],
    "pr-all": [
        "merge_request", "note+mergerequest", "confidential_note+mergerequest"
    ],
    "issue-minimal": [
        "issue/open", "issue/close", "issue/reopen", "confidential_issue/open",
        "confidential_issue/close", "confidential_issue/reopen"
    ],
    "issue": [
        "issue/open", "issue/close", "issue/reopen", "issue/update",
        "confidential_issue/open", "confidential_issue/close",
        "confidential_issue/reopen", "confidential_issue/update", "note+issue",
        "confidential_note+issue"
    ],
    "issue-all": [
        "issue", "confidential_issue", "note+issue", "confidential_note+issue"
    ],
    "repo": ["tag_push"]
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
    "update": "updated",
    "merge": "merged"
}

class GitLab(object):
    def is_private(self, data, headers):
        if "project" in data:
            return not data["project"]["visibility_level"] == 20
        return False

    def names(self, data, headers):
        if "project" in data:
            full_name = data["project"]["path_with_namespace"]
        else:
            full_name = data["project_name"].replace(" ", "")
        repo_username, repo_name = full_name.split("/", 1)

        organisation = None
        if full_name.count("/") == 2:
            organisation = repo_username
            repo_username = full_name.rsplit("/", 1)[0]

        return full_name, repo_username, repo_name, organisation

    def branch(self, data, headers):
        if "ref" in data:
            return data["ref"].rpartition("/")[2]
        return None

    def event(self, data, headers):
        event = headers["X-GitLab-Event"].rsplit(" ", 1)[0].lower()

        event = event.replace(" ", "_")
        action = None
        event_action = None

        category = None
        category_action = None

        if "object_attributes" in data:
            if "action" in data["object_attributes"]:
                action = data["object_attributes"]["action"]
            if "noteable_type" in data["object_attributes"]:
                category = data["object_attributes"]["noteable_type"].lower()
                category = "%s+%s" % (event, category)

        if action:
            if category:
                category_action = "%s/%s" % (category, action)
            event_action = "%s/%s" % (event, action)

        return [event]+list(filter(None,
            [event_action, category, category_action]))

    def event_categories(self, event):
        return EVENT_CATEGORIES.get(event, [event])

    def webhook(self, full_name, event, data, headers):
        if event == "push":
            return self.push(full_name, data)
        elif event == "merge_request":
            return self.merge_request(full_name, data)
        elif event in ["issue", "confidential_issue"]:
            return self.issues(full_name, data)
        elif event in ["note", "confidential_note"]:
            return self.note(full_name, data)
        elif event == "tag_push":
            return self.tag_push(full_name, data)

    def _short_hash(self, hash):
        return hash[:7]

    def tag_push(self, full_name, data):
        create = not data["after"].strip("0") == ""
        tag = utils.irc.color(data["ref"].rsplit("/", 1)[-1],
            colors.COLOR_BRANCH)
        author = utils.irc.bold(data["user_username"])
        action = "created" if create else "deleted"

        return [["%s %s a tag: %s" % (author, action, tag), None]]

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

                outputs.append(["%s pushed %s to %s: %s"
                    % (author, hash_colored, branch, message), url])
        else:
            first_id = data["before"]
            last_id = data["after"]
            url = data["compare_url"]

            outputs.append(["%s pushed %d commits to %s"
                % (author, len(data["commits"]), branch), None])

        return outputs

    def merge_request(self, full_name, data):
        number = utils.irc.color("!%s" % data["object_attributes"]["iid"],
            colors.COLOR_ID)
        action = data["object_attributes"]["action"]
        action_desc = "%s %s" % (ISSUE_ACTIONS.get(action, action), number)
        branch = data["object_attributes"]["target_branch"]
        colored_branch = utils.irc.color(branch, colors.COLOR_BRANCH)

        if action == "open":
            action_desc = "requested %s merge into %s" % (number,
                colored_branch)
        elif action == "close":
            action_desc = "%s %s" % (
                utils.irc.color("closed", colors.COLOR_NEGATIVE), number)
        elif action == "merge":
            action_desc = "%s %s into %s" % (
                utils.irc.color("merged", colors.COLOR_POSITIVE), number,
                colored_branch)

        pr_title = data["object_attributes"]["title"]
        author = utils.irc.bold(data["user"]["username"])
        url = data["object_attributes"]["url"]
        return [["[MR] %s %s: %s" % (author, action_desc, pr_title), url]]

    def issues(self, full_name, data):
        if not "action" in data["object_attributes"]:
            return

        number = utils.irc.color("#%s" % data["object_attributes"]["iid"],
            colors.COLOR_ID)
        action = data["object_attributes"]["action"]
        action = ISSUE_ACTIONS.get(action, action)
        issue_title = data["object_attributes"]["title"]
        author = utils.irc.bold(data["user"]["username"])
        url = data["object_attributes"]["url"]

        return [["[issue] %s %s %s: %s" %
            (author, action, number, issue_title), url]]

    def note(self, full_name, data):
        type = data["object_attributes"]["noteable_type"]
        if type == "Issue":
            self._note(full_name, data, data["issue"])
        elif type == "MergeRequest":
            self._note(full_name, data, data["merge_request"])

    def _note(self, full_name, data, object):
        number = utils.irc.color("#%s" % object["iid"], colors.COLOR_ID)
        type = data["object_attributes"]["noteable_type"]
        type == "issue" if type == "Issue" else "MR"

        title = object["title"]
        commenter = utils.irc.bold(data["user"]["username"])
        url = data["object_attributes"]["url"]
        return [["[%s] %s commented on %s: %s" %
            (type, commenter, number, title), url]]
