#--depends-on commands
#--depends-on config

import datetime, math, re
from src import EventManager, ModuleManager, utils

COLOR_BRANCH = utils.consts.ORANGE
COLOR_REPO = utils.consts.GREY
COLOR_POSITIVE = utils.consts.GREEN
COLOR_NEUTRAL = utils.consts.LIGHTGREY
COLOR_NEGATIVE = utils.consts.RED
COLOR_ID = utils.consts.PINK

REGEX_ISSUE = re.compile(
    r"https?://github.com/([^/]+)/([^/]+)/(pull|issues)/(\d+)", re.I)
REGEX_ISSUE_REF = re.compile(r"(?:\S+(?:\/\S+)?)?#\d+")
REGEX_COMMIT_REF = re.compile(r"(?:\S+(?:\/\S+)?)?@[0-9a-fA-F]+")

API_COMMIT_URL = "https://api.github.com/repos/%s/%s/commits/%s"
API_ISSUE_URL = "https://api.github.com/repos/%s/%s/issues/%s"
API_PULL_URL = "https://api.github.com/repos/%s/%s/pulls/%s"

@utils.export("channelset", utils.Setting("github-default-repo",
    "Set the default github repo for the current channel",
    example="jesopo/bitbot"))
@utils.export("channelset", utils.BoolSetting("auto-github",
    "Enable/disable automatically getting github issue/PR info"))
@utils.export("channelset", utils.IntSetting("auto-github-cooldown",
    "Set amount of seconds between auto-github duplicates", example="300"))
class Module(ModuleManager.BaseModule):
    def _parse_ref(self, channel, ref, sep):
        repo, _, number = ref.rpartition(sep)
        org, _, repo = repo.partition("/")

        default_repo = channel.get_setting("github-default-repo", "")
        default_org, _, default_repo = default_repo.partition("/")

        if org and not repo:
            repo = org or default_repo
            org = default_org
        else:
            org = org or default_org
            repo = repo or default_repo

        if not org or not repo or not number:
            raise utils.EventError("Please provide username/repo#number")
        return org, repo, number

    def _short_url(self, url):
        return self.exports.get("shorturl")(self.bot, url) or url

    def _change_count(self, n, symbol, color):
        return utils.irc.color("%s%d" % (symbol, n), color)+utils.irc.bold("")
    def _added(self, n):
        return self._change_count(n, "+", COLOR_POSITIVE)
    def _removed(self, n):
        return self._change_count(n, "-", COLOR_NEGATIVE)
    def _modified(self, n):
        return self._change_count(n, "~", utils.consts.PURPLE)

    def _get(self, url):
        oauth2_token = self.bot.config.get("github-token", None)
        headers = {}
        if not oauth2_token == None:
            headers["Authorization"] = "token %s" % oauth2_token
        request = utils.http.Request(url, headers=headers)
        return utils.http.request(request)

    def _commit(self, username, repository, commit):
        page = self._get(API_COMMIT_URL % (username, repository, commit))
        if page and page.code == 200:
            page = page.json()
            repo = utils.irc.color("%s/%s" % (username, repository), COLOR_REPO)
            sha = utils.irc.color(page["sha"][:8], COLOR_ID)
            return "(%s@%s) %s - %s %s" % (repo, sha,
                page["author"]["login"], page["commit"]["message"],
                self._short_url(page["html_url"]))
    def _parse_commit(self, target, ref):
        username, repository, commit = self._parse_ref(target, ref, "@")
        return self._commit(username, repository, commit)

    @utils.hook("received.command.ghcommit")
    @utils.kwarg("min_args", 1)
    @utils.kwarg("help", "Get information for a given commit on github")
    @utils.kwarg("usage", "<organsation>/<repo>@<commit>")
    def github_commit(self, event):
        out = self._parse_commit(event["target"], event["args_split"][0])
        if not out == None:
            event["stdout"].write(out)
        else:
            event["stderr"].write("Commit not found")

    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("command", "github")
    @utils.kwarg("pattern", REGEX_COMMIT_REF)
    def commit_regex(self, event):
        if event["target"].get_setting("auto-github", False):
            event.eat()
            ref = event["match"].group(0)
            if self._auto_github_cooldown(event["target"], ref):
                try:
                    out = self._parse_commit(event["target"], ref)
                except utils.EventError:
                    return

                if out:
                    event["stdout"].write(out)

    def _parse_issue(self, page, username, repository, number):
        repo = utils.irc.color("%s/%s" % (username, repository), COLOR_REPO)
        number = utils.irc.color("#%s" % number, COLOR_ID)
        labels = [label["name"] for label in page["labels"]]
        labels_str = ""
        if labels:
            labels_str = "[%s] " % ", ".join(labels)

        url = self._short_url(page["html_url"])

        state = page["state"]
        if state == "open":
            state = utils.irc.color("open", COLOR_NEUTRAL)
        elif state == "closed":
            state = utils.irc.color("closed", COLOR_NEGATIVE)

        return "(%s issue%s, %s) %s %s%s" % (
            repo, number, state, page["title"], labels_str, url)
    def _get_issue(self, username, repository, number):
        return self._get(API_ISSUE_URL % (username, repository, number))

    @utils.hook("received.command.ghissue", min_args=1)
    def github_issue(self, event):
        if event["target"].get_setting("github-hide-prefix", False):
            event["stdout"].prefix = None
            event["stderr"].prefix = None

        username, repository, number = self._parse_ref(
            event["target"], event["args_split"][0], "#")
        if not number.isdigit():
            raise utils.EventError("Issue number must be a number")

        page = self._get_issue(username, repository, number)
        if page and page.code == 200:
            self._parse_issue(page.json(), username, repository, number)
        else:
            event["stderr"].write("Could not find issue")

    def _parse_pull(self, page, username, repository, number):
        repo = utils.irc.color("%s/%s" % (username, repository), COLOR_REPO)
        number = utils.irc.color("#%s" % number, COLOR_ID)
        branch_from = page["head"]["label"]
        branch_to = page["base"]["label"]
        added = self._added(page["additions"])
        removed = self._removed(page["deletions"])
        url = self._short_url(page["html_url"])

        state = page["state"]
        if page["merged"]:
            state = utils.irc.color("merged", COLOR_POSITIVE)
        elif state == "open":
            state = utils.irc.color("open", COLOR_NEUTRAL)
        elif state == "closed":
            state = utils.irc.color("closed", COLOR_NEGATIVE)

        return "(%s PR%s, %s) %s → %s [%s/%s] %s %s" % (
            repo, number, state, branch_from, branch_to, added, removed,
            page["title"], url)
    def _get_pull(self, username, repository, number):
        return self._get(API_PULL_URL % (username, repository, number))
    @utils.hook("received.command.ghpull", min_args=1)
    def github_pull(self, event):
        if event["target"].get_setting("github-hide-prefix", False):
            event["stdout"].prefix = None
            event["stderr"].prefix = None

        username, repository, number = self._parse_ref(
            event["target"], event["args_split"][0], "#")
        if not number.isdigit():
            raise utils.EventError("PR number must be a number")

        page = self._get_pull(username, repository, number)

        if page and page.code == 200:
            self._parse_pull(page.json(), username, repository, number)
        else:
            event["stderr"].write("Could not find pull request")

    def _get_info(self, target, ref):
        username, repository, number = self._parse_ref(target, ref, "#")
        if not number.isdigit():
            raise utils.EventError("PR number must be a number")

        page = self._get_issue(username, repository, number)
        if page and page.code == 200:
            page = page.json()
            if "pull_request" in page:
                pull = self._get_pull(username, repository, number)
                return self._parse_pull(pull.json(), username, repository,
                    number)
            else:
                return self._parse_issue(page, username, repository, number)
        else:
            return None

    @utils.hook("received.command.gh", alias_of="github")
    @utils.hook("received.command.github", min_args=1)
    def github(self, event):
        if event["target"].get_setting("github-hide-prefix", False):
            event["stdout"].prefix = None
            event["stderr"].prefix = None
        result = self._get_info(event["target"], event["args_split"][0])
        if not result == None:
            event["stdout"].write(result)
        else:
            event["stderr"].write("Issue/PR not found")

    def _cache_ref(self, ref):
        return "auto-github-%s" % ref.lower()
    def _auto_github_cooldown(self, channel, ref):
        cooldown = channel.get_setting("auto-github-cooldown", None)
        if not cooldown == None:
            cache = self._cache_ref(ref)
            if not self.bot.cache.has_item(cache):
                self.bot.cache.temporary_cache(cache, True, cooldown)
                return True
            else:
                return False
        else:
            return True

    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("command", "github")
    @utils.kwarg("pattern", REGEX_ISSUE)
    def url_regex(self, event):
        if event["target"].get_setting("auto-github", False):
            event.eat()
            ref = "%s/%s#%s" % (event["match"].group(1),
                event["match"].group(2), event["match"].group(4))
            if self._auto_github_cooldown(event["target"], ref):
                try:
                    result = self._get_info(event["target"], ref)
                except utils.EventError:
                    return
                if result:
                    if event["target"].get_setting("github-hide-prefix", False):
                        event["stdout"].prefix = None
                    event["stdout"].write(result)

    @utils.hook("command.regex")
    @utils.kwarg("ignore_action", False)
    @utils.kwarg("command", "github")
    @utils.kwarg("pattern", REGEX_ISSUE_REF)
    def ref_regex(self, event):
        if event["target"].get_setting("auto-github", False):
            event.eat()
            ref = event["match"].group(0)
            if self._auto_github_cooldown(event["target"], ref):
                try:
                    result = self._get_info(event["target"],
                        event["match"].group(0))
                except utils.EventError:
                    return
                if result:
                    if event["target"].get_setting("github-hide-prefix", False):
                        event["stdout"].prefix = None
                    event["stdout"].write(result)
