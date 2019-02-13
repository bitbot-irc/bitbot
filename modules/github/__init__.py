import datetime, itertools, json, math, urllib.parse
from src import ModuleManager, utils

FORM_ENCODED = "application/x-www-form-urlencoded"

COMMIT_URL = "https://github.com/%s/commit/%s"
COMMIT_RANGE_URL = "https://github.com/%s/compare/%s...%s"
CREATE_URL = "https://github.com/%s/tree/%s"

API_ISSUE_URL = "https://api.github.com/repos/%s/%s/issues/%s"
API_PULL_URL = "https://api.github.com/repos/%s/%s/pulls/%s"

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
    "repo": [
        "create", # a repository, branch or tage has been created
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

@utils.export("channelset", {"setting": "github-hide-prefix",
    "help": "Hide/show command-like prefix on Github hook outputs",
    "validate": utils.bool_or_none})
@utils.export("channelset", {"setting": "github-default-repo",
    "help": "Set the default github repo for the current channel"})
@utils.export("channelset", {"setting": "github-prevent-highlight",
    "help": "Enable/disable preventing highlights",
    "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    def _parse_ref(self, channel, ref):
        repo, _, number = ref.rpartition("#")
        if not repo:
            repo = channel.get_setting("github-default-repo", None)

        username, repository = None, None
        if repo:
            username, _, repository = repo.partition("/")

        if not username or not repository or not number:
            raise utils.EventError("Please provide username/repo#number")
        if not number.isdigit():
            raise utils.EventError("Issue number must be a number")
        return username, repository, number

    def _gh_issue(self, event, page, username, repository, number):
        labels = [label["name"] for label in page.data["labels"]]
        url = self._short_url(page.data["html_url"])

        event["stdout"].write("(%s/%s issue#%s, %s) %s [%s] %s" % (
            username, repository, number, page.data["state"],
            page.data["title"], ", ".join(labels), url))
    def _gh_get_issue(self, username, repository, number):
        return utils.http.request(
            API_ISSUE_URL % (username, repository, number),
            json=True)

    @utils.hook("received.command.ghissue", min_args=1)
    def github_issue(self, event):
        username, repository, number = self._parse_ref(
            event["target"], event["args_split"][0])

        page = self._gh_get_issue(username, repository, number)
        if page and page.code == 200:
            self._gh_issue(event, page, username, repository, number)
        else:
            event["stderr"].write("Could not find issue")

    def _gh_pull(self, event, page, username, repository, number):
        repo_from = page.data["head"]["label"]
        repo_to = page.data["base"]["label"]
        added = self._added(page.data["additions"])
        removed = self._removed(page.data["deletions"])
        url = self._short_url(page.data["html_url"])

        event["stdout"].write(
            "(%s/%s pull#%s, %s) [%s/%s] %s→%s - %s %s" % (
            username, repository, number, page.data["state"],
            added, removed, repo_from, repo_to, page.data["title"], url))

    def _gh_get_pull(self, username, repository, number):
        return utils.http.request(
            API_PULL_URL % (username, repository, number),
            json=True)

    @utils.hook("received.command.ghpull", min_args=1)
    def github_pull(self, event):
        username, repository, number = self._parse_ref(
            event["target"], event["args_split"][0])
        page = self._gh_get_pull(username, repository, number)

        if page and page.code == 200:
            self._gh_pull(event, page, username, repository, number)
        else:
            event["stderr"].write("Could not find pull request")

    @utils.hook("received.command.gh", alias_of="github")
    @utils.hook("received.command.github", min_args=1)
    def github(self, event):
        username, repository, number = self._parse_ref(
            event["target"], event["args_split"][0])
        page = self._gh_get_issue(username, repository, number)
        if page and page.code == 200:
            if "pull_request" in page.data:
                pull = self._gh_get_pull(username, repository, number)
                self._gh_pull(event, pull, username, repository, number)
            else:
                self._gh_issue(event, page, username, repository, number)
        else:
            event["stderr"].write("Issue/PR not found")

    @utils.hook("received.command.ghwebhook", min_args=1, channel_only=True)
    def github_webhook(self, event):
        """
        :help: Add/remove/modify a github webhook
        :require_mode: high
        :permission: githuboverride
        :usage: list
        :usage: add <hook>
        :usage: remove <hook>
        :usage: events <hook> [category [category ...]]
        :usage: branches <hook> [branch [branch ...]]
        """
        all_hooks = event["target"].get_setting("github-hooks", {})
        hook_name = None
        existing_hook = None
        if len(event["args_split"]) > 1:
            hook_name = event["args_split"][1]
            for existing_hook_name in all_hooks.keys():
                if existing_hook_name.lower() == hook_name.lower():
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

            all_hooks[hook_name] = {
                "events": DEFAULT_EVENT_CATEGORIES.copy(),
                "branches": []
            }
            event["target"].set_setting("github-hooks", all_hooks)
            event["stdout"].write("Added hook for %s" % hook_name)
        elif subcommand == "remove":
            if not existing_hook:
                event["stderr"].write("No hook found for %s" % hook_name)
                return
            del all_hooks[existing_hook]
            if all_hooks:
                event["target"].set_setting("github-hooks", all_hooks)
            else:
                event["target"].del_setting("github-hooks")
            event["stdout"].write("Removed hook for %s" % hook_name)
        elif subcommand == "events":
            if not existing_hook:
                event["stderr"].write("No hook found for %s" % hook_name)
                return

            if len(event["args_split"]) < 3:
                event["stdout"].write("Events for hook %s: %s" %
                    (hook_name, " ".join(all_hooks[existing_hook]["events"])))
            else:
                new_events = [e.lower() for e in event["args_split"][2:]]
                all_hooks[existing_hook]["events"] = new_events
                event["target"].set_setting("github-hooks", all_hooks)
                event["stdout"].write("Updated events for hook %s" % hook_name)
        elif subcommand == "branches":
            if not existing_hook:
                event["stderr"].write("No hook found for %s" % hook_name)
                return

            if len(event["args_split"]) < 3:
                branches = ",".join(all_hooks[existing_hook]["branches"])
                event["stdout"].write("Branches shown for hook %s: %s" %
                    (hook_name, branches))
            else:
                all_hooks[existing_hook]["branches"] = event["args_split"][2:]
                event["target"].set_setting("github-hooks", all_hooks)
                event["stdout"].write("Updated shown branches for hook %s" %
                    hook_name)
        else:
            event["stderr"].write("Unknown command '%s'" %
                event["args_split"][0])

    @utils.hook("api.post.github")
    def webhook(self, event):
        payload = event["data"].decode("utf8")
        if event["headers"]["Content-Type"] == FORM_ENCODED:
            payload = urllib.parse.unquote(urllib.parse.parse_qs(payload)[
                "payload"][0])
        data = json.loads(payload)

        github_event = event["headers"]["X-GitHub-Event"]

        full_name = None
        repo_username = None
        repo_name = None
        if "repository" in data:
            full_name = data["repository"]["full_name"]
            repo_username, repo_name = full_name.split("/", 1)

        organisation = None
        if "organization" in data:
            organisation = data["organization"]["login"]

        event_action = None
        if "action" in data:
            event_action = "%s/%s" % (github_event, data["action"])

        branch = None
        if "ref" in data:
            _, _, branch = data["ref"].rpartition("/")

        hooks = self.bot.database.channel_settings.find_by_setting(
            "github-hooks")
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

            if found_hook:
                repo_hooked = True
                server = self.bot.get_server(server_id)
                if server and channel_name in server.channels:
                    if (branch and
                            found_hook["branches"] and
                            not branch in found_hook["branches"]):
                        continue

                    github_events = []
                    for event in found_hook["events"]:
                        github_events.append(EVENT_CATEGORIES.get(
                            event, [event]))
                    github_events = list(itertools.chain(*github_events))

                    channel = server.channels.get(channel_name)
                    if (github_event in github_events or
                            (event_action and event_action in github_events)):
                        targets.append([server, channel])

        if not targets:
            if not repo_hooked:
                return None
            else:
                return {"state": "success", "deliveries": 0}

        outputs = None
        if github_event == "push":
            outputs = self.push(full_name, data)
        elif github_event == "commit_comment":
            outputs = self.commit_comment(full_name, data)
        elif github_event == "pull_request":
            outputs = self.pull_request(full_name, data)
        elif github_event == "pull_request_review":
            outputs = self.pull_request_review(full_name, data)
        elif github_event == "pull_request_review_comment":
            outputs = self.pull_request_review_comment(full_name, data)
        elif github_event == "issue_comment":
            outputs = self.issue_comment(full_name, data)
        elif github_event == "issues":
            outputs = self.issues(full_name, data)
        elif github_event == "create":
            outputs = self.create(full_name, data)
        elif github_event == "delete":
            outputs = self.delete(full_name, data)
        elif github_event == "release":
            outputs = self.release(full_name, data)
        elif github_event == "check_run":
            outputs = self.check_run(data)
        elif github_event == "fork":
            outputs = self.fork(full_name, data)
        elif github_event == "ping":
            outputs = self.ping(data)
        elif github_event == "membership":
            outputs = self.membership(organisation, data)
        elif github_event == "watch":
            outputs = self.watch(data)

        if outputs:
            for server, channel in targets:
                for output in outputs:
                    source = full_name or organisation
                    output = "(%s) %s" % (source, output)
                    if channel.get_setting("github-prevent-highlight", False):
                        output = self._prevent_highlight(channel, output)

                    self.events.on("send.stdout").call(target=channel,
                        module_name="Github", server=server, message=output,
                        hide_prefix=channel.get_setting(
                        "github-hide-prefix", False))

        return {"state": "success", "deliveries": len(targets)}

    def _prevent_highlight(self, channel, s):
        for user in channel.users:
            while user.nickname.lower() in s.lower():
                index = s.lower().index(user.nickname.lower())
                length = len(user.nickname.lower())

                original = s[index:index+length]
                original = utils.prevent_highlight(original)

                s = s[:index] + original + s[index+length:]
        return s

    def _short_url(self, url):
        try:
            page = utils.http.request("https://git.io", method="POST",
                post_data={"url": url})
            return page.headers["Location"]
        except utils.http.HTTPTimeoutException:
            self.log.warn(
                "HTTPTimeoutException while waiting for github short URL")
            return url

    def _iso8601(self, s):
        return datetime.datetime.strptime(s, utils.ISO8601_FORMAT)

    def ping(self, data):
        return ["Received new webhook"]

    def _change_count(self, n, symbol, color):
        return utils.irc.color("%s%d" % (symbol, n), color)+utils.irc.bold("")
    def _added(self, n):
        return self._change_count(n, "+", utils.consts.GREEN)
    def _removed(self, n):
        return self._change_count(n, "-", utils.consts.RED)
    def _modified(self, n):
        return self._change_count(n, "~", utils.consts.PURPLE)

    def _short_hash(self, hash):
        return hash[:8]

    def _flat_unique(self, commits, key):
        return set(itertools.chain(*(commit[key] for commit in commits)))

    def push(self, full_name, data):
        outputs = []
        branch = data["ref"].split("/", 2)[2]
        branch = utils.irc.color(branch, utils.consts.LIGHTBLUE)

        forced = ""
        if data["forced"]:
            forced = "%s " % utils.irc.color("force", utils.consts.RED)

        if len(data["commits"]) <= 3:
            for commit in data["commits"]:
                id = self._short_hash(commit["id"])
                message = commit["message"].split("\n")[0].strip()
                author = utils.irc.bold(data["pusher"]["name"])
                url = self._short_url(COMMIT_URL % (full_name, id))

                added = self._added(len(commit["added"]))
                removed = self._removed(len(commit["removed"]))
                modified = self._modified(len(commit["modified"]))

                outputs.append(
                    "%s %spushed to %s [%s/%s/%s files] %s - %s"
                    % (author, forced, branch, added, removed, modified,
                    message, url))
        else:
            first_id = self._short_hash(data["before"])
            last_id = self._short_hash(data["commits"][-1]["id"])
            pusher = utils.irc.bold(data["pusher"]["name"])
            url = self._short_url(
                COMMIT_RANGE_URL % (full_name, first_id, last_id))

            commits = data["commits"]
            added = self._added(len(self._flat_unique(commits, "added")))
            removed = self._removed(len(self._flat_unique(commits, "removed")))
            modified = self._modified(len(self._flat_unique(commits,
                "modified")))

            outputs.append("%s %spushed %d commits to %s [%s/%s/%s files] - %s"
                % (pusher, forced, len(data["commits"]), branch,
                added, removed, modified, url))

        return outputs


    def commit_comment(self, full_name, data):
        action = data["action"]
        commit = self._short_hash(data["comment"]["commit_id"])
        commenter = utils.irc.bold(data["comment"]["user"]["login"])
        url = self._short_url(data["comment"]["html_url"])
        comment = utils.irc.bold(data["comment"]["body"])
        return ["[commit/%s] %s %s %s" % (commit, COMMENT_ACTIONS[action],
                                          commenter, comment)]

    def pull_request(self, full_name, data):
        number = data["pull_request"]["number"]
        action = data["action"]
        action_desc = action
        branch = data["pull_request"]["base"]["ref"]
        colored_branch = utils.irc.color(branch, utils.consts.LIGHTBLUE)

        if action == "opened":
            action_desc = "requested merge into %s" % colored_branch
        elif action == "closed":
            if data["pull_request"]["merged"]:
                action_desc = "%s into %s" % (
                    utils.irc.color("merged", utils.consts.GREEN),
                    colored_branch)
            else:
                action_desc = utils.irc.color("closed without merging",
                    utils.consts.RED)
        elif action == "synchronize":
            action_desc = "committed to"

        pr_title = data["pull_request"]["title"]
        author = utils.irc.bold(data["sender"]["login"])
        url = self._short_url(data["pull_request"]["html_url"])
        return ["[pr #%d] %s %s: %s - %s" % (
            number, author, action_desc, pr_title, url)]

    def pull_request_review(self, full_name, data):
        if data["review"]["state"] == "commented":
            return []

        number = data["pull_request"]["number"]
        action = data["action"]
        pr_title = data["pull_request"]["title"]
        reviewer = utils.irc.bold(data["sender"]["login"])
        url = self._short_url(data["review"]["html_url"])
        return ["[pr #%d] %s %s a review on: %s - %s" % (
            number, reviewer, action, pr_title, url)]

    def pull_request_review_comment(self, full_name, data):
        number = data["pull_request"]["number"]
        action = data["action"]
        pr_title = data["pull_request"]["title"]
        sender = utils.irc.bold(data["sender"]["login"])
        url = self._short_url(data["comment"]["html_url"])
        return ["[pr #%d] %s %s on a review: %s - %s" %
            (number, sender, COMMENT_ACTIONS[action], pr_title, url)]

    def issues(self, full_name, data):
        number = data["issue"]["number"]
        action = data["action"]
        action_desc = action

        issue_title = data["issue"]["title"]
        author = utils.irc.bold(data["sender"]["login"])
        url = self._short_url(data["issue"]["html_url"])
        return ["[issue #%d] %s %s: %s - %s" %
            (number, author, action_desc, issue_title, url)]
    def issue_comment(self, full_name, data):
        if "changes" in data:
            # don't show this event when nothing has actually changed
            if data["changes"]["body"]["from"] == data["comment"]["body"]:
                return

        number = data["issue"]["number"]
        action = data["action"]
        issue_title = data["issue"]["title"]
        type = "pr" if "pull_request" in data["issue"] else "issue"
        commenter = utils.irc.bold(data["comment"]["user"]["login"])
        url = self._short_url(data["comment"]["html_url"])
        return ["[%s #%d] %s %s on: %s - %s" %
            (type, number, commenter, COMMENT_ACTIONS.get(action, "commented"),
             issue_title, url)]

    def create(self, full_name, data):
        ref = data["ref"]
        ref_color = utils.irc.color(ref, utils.consts.LIGHTBLUE)
        type = data["ref_type"]
        sender = utils.irc.bold(data["sender"]["login"])
        url = self._short_url(CREATE_URL % (full_name, ref))
        return ["%s created a %s: %s - %s" % (sender, type, ref_color, url)]

    def delete(self, full_name, data):
        ref = data["ref"]
        type = data["ref_type"]
        sender = utils.irc.bold(data["sender"]["login"])
        return ["%s deleted a %s: %s" % (sender, type, ref)]

    def release(self, full_name, data):
        action = data["action"]
        tag = data["release"]["tag_name"]
        name = data["release"]["name"] or ""
        if name:
            name = ": %s"
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
            url = " - %s" % self.exports.get_one("shortlink")(url)

        duration = ""
        if data["check_run"]["completed_at"]:
            started_at = self._iso8601(data["check_run"]["started_at"])
            completed_at = self._iso8601(data["check_run"]["completed_at"])
            if completed_at > started_at:
                seconds = math.floor((completed_at-started_at).total_seconds())
                duration = " in %s" % utils.to_pretty_time(seconds)

        status = data["check_run"]["status"]
        status_str = ""
        if status == "queued":
            status_str = utils.irc.bold("queued")
        elif status == "in_progress":
            status_str = utils.irc.bold("started")
        elif status == "completed":
            conclusion = data["check_run"]["conclusion"]
            conclusion_color = utils.consts.GREEN
            if conclusion in CHECK_RUN_FAILURES:
                conclusion_color = utils.consts.RED
            if conclusion == "neutral":
                conclusion_color = utils.consts.LIGHTGREY

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
