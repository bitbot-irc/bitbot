#--depends-on channel_access
#--depends-on check_mode
#--depends-on commands
#--depends-on config
#--depends-on permissions
#--depends-on rest_api

import datetime, itertools, json, math, re, urllib.parse
from src import EventManager, ModuleManager, utils

COLOR_BRANCH = utils.consts.ORANGE
COLOR_REPO = utils.consts.GREY
COLOR_POSITIVE = utils.consts.GREEN
COLOR_NEUTRAL = utils.consts.LIGHTGREY
COLOR_NEGATIVE = utils.consts.RED
COLOR_ID = utils.consts.PINK

API_ISSUE_URL = "https://api.github.com/repos/%s/%s/issues/%s"
API_PULL_URL = "https://api.github.com/repos/%s/%s/pulls/%s"

@utils.export("channelset", {"setting": "github-default-repo",
    "help": "Set the default github repo for the current channel",
    "example": "jesopo/bitbot"})
@utils.export("channelset", {"setting": "auto-github",
    "help": "Enable/disable automatically getting github issue/PR info",
    "validate": utils.bool_or_none, "example": "on"})
@utils.export("channelset", {"setting": "auto-github-cooldown",
    "help": "Set amount of seconds between auto-github duplicates",
    "validate": utils.int_or_none, "example": "300"})
class Module(ModuleManager.BaseModule):
    def _parse_ref(self, channel, ref):
        repo, _, number = ref.rpartition("#")
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
        if not number.isdigit():
            raise utils.EventError("Issue number must be a number")
        return org, repo, number

    def _short_url(self, url):
        try:
            page = utils.http.request("https://git.io", method="POST",
                post_data={"url": url})
            return page.headers["Location"]
        except utils.http.HTTPTimeoutException:
            self.log.warn(
                "HTTPTimeoutException while waiting for github short URL", [])
            return url

    def _change_count(self, n, symbol, color):
        return utils.irc.color("%s%d" % (symbol, n), color)+utils.irc.bold("")
    def _added(self, n):
        return self._change_count(n, "+", COLOR_POSITIVE)
    def _removed(self, n):
        return self._change_count(n, "-", COLOR_NEGATIVE)
    def _modified(self, n):
        return self._change_count(n, "~", utils.consts.PURPLE)

    def _parse_issue(self, page, username, repository, number):
        repo = utils.irc.color("%s/%s" % (username, repository), COLOR_REPO)
        number = utils.irc.color("#%s" % number, COLOR_ID)
        labels = [label["name"] for label in page.data["labels"]]
        labels_str = ""
        if labels:
            labels_str = "[%s] " % ", ".join(labels)

        url = self._short_url(page.data["html_url"])

        state = page.data["state"]
        if state == "open":
            state = utils.irc.color("open", COLOR_NEUTRAL)
        elif state == "closed":
            state = utils.irc.color("closed", COLOR_NEGATIVE)

        return "(%s issue%s, %s) %s %s%s" % (
            repo, number, state, page.data["title"], labels_str, url)
    def _get_issue(self, username, repository, number):
        return utils.http.request(
            API_ISSUE_URL % (username, repository, number),
            json=True)

    @utils.hook("received.command.ghissue", min_args=1)
    def github_issue(self, event):
        if event["target"].get_setting("github-hide-prefix", False):
            event["stdout"].hide_prefix()
            event["stderr"].hide_prefix()

        username, repository, number = self._parse_ref(
            event["target"], event["args_split"][0])

        page = self._get_issue(username, repository, number)
        if page and page.code == 200:
            self._parse_issue(page, username, repository, number)
        else:
            event["stderr"].write("Could not find issue")

    def _parse_pull(self, page, username, repository, number):
        repo = utils.irc.color("%s/%s" % (username, repository), COLOR_REPO)
        number = utils.irc.color("#%s" % number, COLOR_ID)
        branch_from = page.data["head"]["label"]
        branch_to = page.data["base"]["label"]
        added = self._added(page.data["additions"])
        removed = self._removed(page.data["deletions"])
        url = self._short_url(page.data["html_url"])

        state = page.data["state"]
        if page.data["merged"]:
            state = utils.irc.color("merged", COLOR_POSITIVE)
        elif state == "open":
            state = utils.irc.color("open", COLOR_NEUTRAL)
        elif state == "closed":
            state = utils.irc.color("closed", COLOR_NEGATIVE)

        return "(%s PR%s, %s) %s → %s [%s/%s] %s %s" % (
            repo, number, state, branch_from, branch_to, added, removed,
            page.data["title"], url)
    def _get_pull(self, username, repository, number):
        return utils.http.request(
            API_PULL_URL % (username, repository, number),
            json=True)
    @utils.hook("received.command.ghpull", min_args=1)
    def github_pull(self, event):
        if event["target"].get_setting("github-hide-prefix", False):
            event["stdout"].hide_prefix()
            event["stderr"].hide_prefix()

        username, repository, number = self._parse_ref(
            event["target"], event["args_split"][0])
        page = self._get_pull(username, repository, number)

        if page and page.code == 200:
            self._parse_pull(page, username, repository, number)
        else:
            event["stderr"].write("Could not find pull request")

    def _get_info(self, target, ref):
        username, repository, number = self._parse_ref(target, ref)
        page = self._get_issue(username, repository, number)
        if page and page.code == 200:
            if "pull_request" in page.data:
                pull = self._get_pull(username, repository, number)
                return self._parse_pull(pull, username, repository, number)
            else:
                return self._parse_issue(page, username, repository, number)
        else:
            return None

    @utils.hook("received.command.gh", alias_of="github")
    @utils.hook("received.command.github", min_args=1)
    def github(self, event):
        if event["target"].get_setting("github-hide-prefix", False):
            event["stdout"].hide_prefix()
            event["stderr"].hide_prefix()
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
                self.bot.cache.temporary_cache(cache, cooldown)
                return True
            else:
                return False
        else:
            return True

    @utils.hook("command.regex", ignore_action=False)
    def url_regex(self, event):
        """
        :command: github
        :pattern: https?://github.com/([^/]+)/([^/]+)/(pull|issues)/(\d+)
        """
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
                        event["stdout"].hide_prefix()
                    event["stdout"].write(result)

    @utils.hook("command.regex", ignore_action=False)
    def ref_regex(self, event):
        """
        :command: github
        :pattern: (?:\S+(?:\/\S+)?)?#\d+
        """
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
                       event["stdout"].hide_prefix()
                    event["stdout"].write(result)
