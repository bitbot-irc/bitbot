import datetime
from src import ModuleManager, utils

DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"

class Module(ModuleManager.BaseModule):
    def _now(self):
        return datetime.datetime.isonow()
    def _format_datetime(self, dt: datetime.datetime):
        return datetime.datetime.strftime(dt, DATETIME_FORMAT)
    def _parse_datetime(self, dt: str):
        return datetime.datetime.strptime(dt, DATETIME_FORMAT)

    def _days_since(self, now: datetime.datetime, dt: datetime.datetime):
        return (now-dt).days

    def _get_badges(self, user):
        return user.get_setting("badges", {})
    def _set_badges(self, user, badges):
        user.set_setting("badges", badges)

    @utils.hook("received.command.badges")
    def badges(self, event):
        user = event["user"]
        if event["args"]:
            user = event["server"].get_user(event["args_split"][0])

        now = self._now()
        badges = []
        for badge, date in self._get_badges(user):
            days_since = self._days_since(now, self._parse_datettime(date))
            badges.append("%s: %s" % (badge, days_since))

        event["stdout"].write("Badges for %s: %s" % (
            user.nickname, ", ".join(badges)))

    @utils.hook("received.command.addbadge", min_args=1)
    def add_badge(self, event):
        badge = event["args"]
        badge_lower = badge.lower()
        badges = self._get_badges(event["user"])

        for badge_name in badges.keys():
            if badge_name.lower() == badge_lower:
                raise utils.EventError("You already have a '%s' badge" % badge)
        badges[badge] = self._now()
        self._set_badges(event["user"], badges)
        event["stdout"].write("Added '%s' badge" % badge)

    def remove_badge(self, event):
        badge = event["args"]
        badge_lower = badge.lower()
        badges = self._get_badges(event["user"])

        found_badge = None
        for badge_name in badges.keys():
            if badge_name.lower() == badge_lower:
                found_badge = badge_name
                break
        if found_badge:
            del badges[found_badge]
            self._set_badges(event["user"], badges)
            event["stdout"].write("Removed '%s' badge" % badge)
        else:
            event["stderr"].write("You have no '%s' badge" % badge)

    def resetbadge(self, event):
        badge = event["args"]
        badge_lower = badge.lower()
        badges = self._get_badges(event["user"])

        found_badge = None
        for badge_name in badges.keys():
            if badge_name.lower() == badge_lower:
                found_badge = badge_name
                break

        if found_badge:
            badges[found_badge] = self._now()
            self._set_badges(event["user"], badges)
            event["stdout"].write("Reset badge '%s'" % badge)
        else:
            event["stderr"].write("You have no '%s' badge" % badge)
