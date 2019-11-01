from src import ModuleManager, utils
from . import colors

COMMIT_URL = "https://github.com/%s/commit/%s"
COMMIT_RANGE_URL = "https://github.com/%s/compare/%s...%s"
CREATE_URL = "https://github.com/%s/tree/%s"

PR_COMMIT_RANGE_URL = "https://github.com/%s/pull/%s/files/%s..%s"
PR_COMMIT_URL = "https://github.com/%s/pull/%s/commits/%s"

DEFAULT_EVENT_CATEGORIES = [
    "ping", "code", "pr", "issue", "repo"
]
EVENT_CATEGORIES = {
    "ping": [
        "ping" # new webhook received
    ],
    "code": [
        "push", "commit_comment"
    ],
    "pr-minimal": [
        "pull_request/opened", "pull_request/closed", "pull_request/reopened"
    ],
    "pr": [
        "pull_request/opened", "pull_request/closed", "pull_request/reopened",
        "pull_request/edited", "pull_request/assigned",
        "pull_request/unassigned", "pull_request_review",
        "pull_request_review_comment"
    ],
    "pr-all": [
        "pull_request", "pull_request_review", "pull_request_review_comment"
    ],
    "pr-review-minimal": [
        "pull_request_review/submitted", "pull_request_review/dismissed"
    ],
    "pr-review-comment-minimal": [
        "pull_request_review_comment/created",
        "pull_request_review_comment/deleted"
    ],
    "issue-minimal": [
        "issues/opened", "issues/closed", "issues/reopened", "issues/deleted"
    ],
    "issue": [
        "issues/opened", "issues/closed", "issues/reopened", "issues/deleted",
        "issues/edited", "issues/assigned", "issues/unassigned", "issue_comment"
    ],
    "issue-all": [
        "issues", "issue_comment"
    ],
    "issue-comment-minimal": [
        "issue_comment/created", "issue_comment/deleted"
    ],
    "repo": [
        "create", # a repository, branch or tag has been created
        "delete", # same as above but deleted
        "release",
        "fork"
    ],
    "team": [
        "membership"
    ],
    "star": [
        # "watch" is a misleading name for this event so this add "star" as an
        # alias for "watch"
        "watch"
    ]
}

COMMENT_ACTIONS = {
    "created": "commented",
    "edited":  "edited a comment",
    "deleted": "deleted a comment"
}

CHECK_RUN_CONCLUSION = {
    "success": "passed",
    "failure": "failed",
    "neutral": "finished",
    "cancelled": "was cancelled",
    "timed_out": "timed out",
    "action_required": "requires action"
}
CHECK_RUN_FAILURES = ["failure", "cancelled", "timed_out", "action_required"]

class GitHub(object):
    def __init__(self, log):
        self.log = log

    def is_private(self, data, headers):
        if "repository" in data:
            return data["repository"]["private"]
        return False

    def names(self, data, headers):
        full_name = None
        repo_username = None
        repo_name = None
        if "repository" in data:
            full_name = data["repository"]["full_name"]
            repo_username, repo_name = full_name.split("/", 1)

        organisation = None
        if "organization" in data:
            organisation = data["organization"]["login"]
        return full_name, repo_username, repo_name, organisation

    def branch(self, data, headers):
        if "ref" in data:
            return data["ref"].rpartition("/")[2]
        return None

    def event(self, data, headers):
        event = headers["X-GitHub-Event"]
        action = None
        event_action = None
        if "action" in data:
            action = data["action"]

        category = None
        category_action = None
        if "review" in data and "state" in data["review"]:
            category = "%s+%s" % (event, data["review"]["state"])

        if action:
            if category:
                category_action = "%s/%s" % (category, action)
            event_action = "%s/%s" % (event, action)

        return [event]+list(filter(None,
            [event_action, category, category_action]))

    def event_categories(self, event):
        return EVENT_CATEGORIES.get(event, [event])

    def webhook(self, full_name, event, data, headers):
        out = []
        if event == "push":
            out = self.push(full_name, data)
        elif event == "commit_comment":
            out = self.commit_comment(full_name, data)
        elif event == "pull_request":
            out = self.pull_request(full_name, data)
        elif event == "pull_request_review":
            out = self.pull_request_review(full_name, data)
        elif event == "pull_request_review_comment":
            out = self.pull_request_review_comment(full_name, data)
        elif event == "issue_comment":
            out = self.issue_comment(full_name, data)
        elif event == "issues":
            out = self.issues(full_name, data)
        elif event == "create":
            out = self.create(full_name, data)
        elif event == "delete":
            out = self.delete(full_name, data)
        elif event == "release":
            out = self.release(full_name, data)
        elif event == "check_run":
            out = self.check_run(data)
        elif event == "fork":
            out = self.fork(full_name, data)
        elif event == "ping":
            out = self.ping(data)
        elif event == "membership":
            out = self.membership(organisation, data)
        elif event == "watch":
            out = self.watch(data)
        return list(zip(out, [None]*len(out)))

    def _short_url(self, url):
        self.log.debug("git.io shortening: %s" % url)
        try:
            page = utils.http.request("https://git.io", method="POST",
                post_data={"url": url}, detect_encoding=False)
            return page.headers["Location"]
        except utils.http.HTTPTimeoutException:
            self.log.warn(
                "HTTPTimeoutException while waiting for github short URL", [])
            return url

    def _iso8601(self, s):
        return datetime.datetime.strptime(s, utils.ISO8601_PARSE)

    def ping(self, data):
        return ["Received new webhook"]

    def _change_count(self, n, symbol, color):
        return utils.irc.color("%s%d" % (symbol, n), color)+utils.irc.bold("")
    def _added(self, n):
        return self._change_count(n, "+", colors.COLOR_POSITIVE)
    def _removed(self, n):
        return self._change_count(n, "-", colors.COLOR_NEGATIVE)
    def _modified(self, n):
        return self._change_count(n, "~", utils.consts.PURPLE)

    def _short_hash(self, hash):
        return hash[:8]

    def _flat_unique(self, commits, key):
        return set(itertools.chain(*(commit[key] for commit in commits)))

    def push(self, full_name, data):
        outputs = []
        branch = data["ref"].split("/", 2)[2]
        branch = utils.irc.color(branch, colors.COLOR_BRANCH)
        author = utils.irc.bold(data["pusher"]["name"])

        range_url = None
        if len(data["commits"]):
            first_id = data["before"]
            last_id = data["commits"][-1]["id"]
            range_url = COMMIT_RANGE_URL % (full_name, first_id, last_id)

        single_url = COMMIT_URL % (full_name, "%s")

        return self._format_push(branch, author, data["commits"],
            data["forced"], single_url, range_url)

    def _format_push(self, branch, author, commits, forced, single_url,
            range_url):
        outputs = []

        forced_str = ""
        if forced:
            forced_str = "%s " % utils.irc.color("force", utils.consts.RED)

        if len(commits) == 0 and forced:
            outputs.append(
                "%s %spushed to %s" % (author, forced_str, branch))
        elif len(commits) <= 3:
            for commit in commits:
                hash = commit["id"]
                hash_colored = utils.irc.color(self._short_hash(hash), colors.COLOR_ID)
                message = commit["message"].split("\n")[0].strip()
                url = self._short_url(single_url % hash)

                outputs.append(
                    "%s %spushed %s to %s: %s - %s"
                    % (author, forced_str, hash_colored, branch, message, url))
        else:
            outputs.append("%s %spushed %d commits to %s - %s"
                % (author, forced_str, len(commits), branch,
                self._short_url(range_url)))

        return outputs

    def commit_comment(self, full_name, data):
        action = data["action"]
        commit = self._short_hash(data["comment"]["commit_id"])
        commenter = utils.irc.bold(data["comment"]["user"]["login"])
        url = self._short_url(data["comment"]["html_url"])
        return ["[commit/%s] %s %s a comment - %s" % (commit, commenter,
            action, url)]

    def pull_request(self, full_name, data):
        raw_number = data["pull_request"]["number"]
        number = utils.irc.color("#%s" % data["pull_request"]["number"],
            colors.COLOR_ID)
        action = data["action"]
        action_desc = "%s %s" % (action, number)
        branch = data["pull_request"]["base"]["ref"]
        colored_branch = utils.irc.color(branch, colors.COLOR_BRANCH)
        author = utils.irc.bold(data["sender"]["login"])

        if action == "opened":
            action_desc = "requested %s merge into %s" % (number,
                colored_branch)
        elif action == "closed":
            if data["pull_request"]["merged"]:
                action_desc = "%s %s into %s" % (
                    utils.irc.color("merged", colors.COLOR_POSITIVE), number,
                    colored_branch)
            else:
                action_desc = "%s %s" % (
                    utils.irc.color("closed", colors.COLOR_NEGATIVE), number)
        elif action == "ready_for_review":
            action_desc = "marked %s ready for review" % number
        elif action == "synchronize":
            action_desc = "committed to %s" % number

            commits_url = data["pull_request"]["commits_url"]
            commits = utils.http.request(commits_url, json=True)
            if commits:
                seen_before = False
                new_commits = []
                for commit in commits.data:
                    if seen_before:
                        new_commits.append({"id": commit["sha"],
                            "message": commit["commit"]["message"]})
                    elif commit["sha"] == data["before"]:
                        seen_before = True

                range_url = PR_COMMIT_RANGE_URL % (full_name, raw_number,
                    data["before"], data["after"])
                single_url = PR_COMMIT_URL % (full_name, raw_number, "%s")
                if new_commits:
                    outputs = self._format_push(number, author, new_commits,
                        False, single_url, range_url)
                    for i, output in enumerate(outputs):
                        outputs[i] = "[PR] %s" % output
                    return outputs
        elif action == "labeled":
            action_desc = "labled %s as '%s'" % (number, data["label"]["name"])

        pr_title = data["pull_request"]["title"]
        url = self._short_url(data["pull_request"]["html_url"])
        return ["[PR] %s %s: %s - %s" % (
            author, action_desc, pr_title, url)]

    def pull_request_review(self, full_name, data):
        if not data["action"] == "submitted":
            return []

        if not "submitted_at" in data["review"]:
            return []

        state = data["review"]["state"]
        if state == "commented":
            return []

        number = utils.irc.color("#%s" % data["pull_request"]["number"],
            colors.COLOR_ID)
        action = data["action"]
        pr_title = data["pull_request"]["title"]
        reviewer = utils.irc.bold(data["sender"]["login"])
        url = self._short_url(data["review"]["html_url"])

        state_desc = state
        if state == "approved":
            state_desc = "approved changes"
        elif state == "changes_requested":
            state_desc = "requested changes"
        elif state == "dismissed":
            state_desc = "dismissed a review"

        return ["[PR] %s %s on %s: %s - %s" %
            (reviewer, state_desc, number, pr_title, url)]

    def pull_request_review_comment(self, full_name, data):
        number = utils.irc.color("#%s" % data["pull_request"]["number"],
            colors.COLOR_ID)
        action = data["action"]
        pr_title = data["pull_request"]["title"]
        sender = utils.irc.bold(data["sender"]["login"])
        url = self._short_url(data["comment"]["html_url"])
        return ["[PR] %s %s on a review on %s: %s - %s" %
            (sender, COMMENT_ACTIONS[action], number, pr_title, url)]

    def issues(self, full_name, data):
        number = utils.irc.color("#%s" % data["issue"]["number"],
            colors.COLOR_ID)
        action = data["action"]
        action_str = "%s %s" % (action, number)
        if action == "labeled":
            action_str = "labeled %s as '%s'" % (number, data["label"]["name"])

        issue_title = data["issue"]["title"]
        author = utils.irc.bold(data["sender"]["login"])
        url = self._short_url(data["issue"]["html_url"])
        return ["[issue] %s %s: %s - %s" %
            (author, action_str, issue_title, url)]
    def issue_comment(self, full_name, data):
        if "changes" in data:
            # don't show this event when nothing has actually changed
            if data["changes"]["body"]["from"] == data["comment"]["body"]:
                return

        number = utils.irc.color("#%s" % data["issue"]["number"], colors.COLOR_ID)
        action = data["action"]
        issue_title = data["issue"]["title"]
        type = "PR" if "pull_request" in data["issue"] else "issue"
        commenter = utils.irc.bold(data["sender"]["login"])
        url = self._short_url(data["comment"]["html_url"])
        return ["[%s] %s %s on %s: %s - %s" %
            (type, commenter, COMMENT_ACTIONS[action], number, issue_title,
            url)]

    def create(self, full_name, data):
        ref = data["ref"]
        ref_color = utils.irc.color(ref, colors.COLOR_BRANCH)
        type = data["ref_type"]
        sender = utils.irc.bold(data["sender"]["login"])
        url = self._short_url(CREATE_URL % (full_name, ref))
        return ["%s created a %s: %s - %s" % (sender, type, ref_color, url)]

    def delete(self, full_name, data):
        ref = data["ref"]
        ref_color = utils.irc.color(ref, colors.COLOR_BRANCH)
        type = data["ref_type"]
        sender = utils.irc.bold(data["sender"]["login"])
        return ["%s deleted a %s: %s" % (sender, type, ref_color)]

    def release(self, full_name, data):
        action = data["action"]
        tag = data["release"]["tag_name"]
        name = data["release"]["name"] or ""
        if name:
            name = ": %s" % name
        author = utils.irc.bold(data["release"]["author"]["login"])
        url = self._short_url(data["release"]["html_url"])
        return ["%s %s a release%s - %s" % (author, action, name, url)]

    def check_run(self, data):
        name = data["check_run"]["name"]
        commit = self._short_hash(data["check_run"]["head_sha"])
        commit = utils.irc.color(commit, utils.consts.LIGHTBLUE)

        url = ""
        if data["check_run"]["details_url"]:
            url = data["check_run"]["details_url"]
            url = " - %s" % self.exports.get_one("shorturl-any")(url)

        duration = ""
        if data["check_run"]["completed_at"]:
            started_at = self._iso8601(data["check_run"]["started_at"])
            completed_at = self._iso8601(data["check_run"]["completed_at"])
            if completed_at > started_at:
                seconds = (completed_at-started_at).total_seconds()
                duration = " in %s" % utils.to_pretty_time(seconds)

        status = data["check_run"]["status"]
        status_str = ""
        if status == "queued":
            status_str = utils.irc.bold("queued")
        elif status == "in_progress":
            status_str = utils.irc.bold("started")
        elif status == "completed":
            conclusion = data["check_run"]["conclusion"]
            conclusion_color = colors.COLOR_POSITIVE
            if conclusion in CHECK_RUN_FAILURES:
                conclusion_color = colors.COLOR_NEGATIVE
            if conclusion == "neutral":
                conclusion_color = colors.COLOR_NEUTRAL

            status_str = utils.irc.color(
                CHECK_RUN_CONCLUSION[conclusion], conclusion_color)

        return ["[build @%s] %s: %s%s%s" % (
            commit, name, status_str, duration, url)]

    def fork(self, full_name, data):
        forker = utils.irc.bold(data["sender"]["login"])
        fork_full_name = utils.irc.color(data["forkee"]["full_name"],
            utils.consts.LIGHTBLUE)
        url = self._short_url(data["forkee"]["html_url"])
        return ["%s forked into %s - %s" %
            (forker, fork_full_name, url)]

    def membership(self, organisation, data):
        return ["%s %s %s to team %s" %
            (data["sender"]["login"], data["action"], data["member"]["login"],
            data["team"]["name"])]

    def watch(self, data):
        return ["%s starred the repository" % data["sender"]["login"]]
