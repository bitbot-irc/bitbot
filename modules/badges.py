import datetime, re
from src import ModuleManager, utils

RE_HUMAN_FORMAT = re.compile(r"(\d\d\d\d)-(\d?\d)-(\d?\d)")
HUMAN_FORMAT_HELP = "year-month-day (e.g. 2018-12-29)"
DATETIME_FORMAT = "%Y-%m-%dT%H:%M:%SZ"
DATE_FORMAT = "%Y-%m-%d"

class Module(ModuleManager.BaseModule):
    def _now(self):
        return datetime.datetime.utcnow()
    def _format_datetime(self, dt: datetime.datetime):
        return datetime.datetime.strftime(dt, DATETIME_FORMAT)
    def _parse_datetime(self, dt: str):
        return datetime.datetime.strptime(dt, DATETIME_FORMAT)

    def _date_str(self, dt: datetime.datetime):
        return datetime.datetime.strftime(dt, DATE_FORMAT)

    def _round_up_day(self, dt: datetime.datetime):
        return dt.date()+datetime.timedelta(days=1)
    def _days_since(self, now: datetime.date, dt: datetime.datetime):
        return (now-dt.date()).days

    def _get_badges(self, user):
        return user.get_setting("badges", {})
    def _set_badges(self, user, badges):
        user.set_setting("badges", badges)

    @utils.hook("received.command.badge", min_args=1)
    def badge(self, event):
        badge = event["args"]
        badge_lower = badge.lower()
        badges = self._get_badges(event["user"])

        now = self._round_up_day(self._now())

        found_badge = None
        for badge_name in badges.keys():
            if badge_name.lower() == badge_lower:
                found_badge = badge_name
                break

        if found_badge:
            dt = self._parse_datetime(badges[found_badge])
            days_since = self._days_since(now, dt)
            event["stdout"].write("(%s) %s on day %s (%s)" % (
                event["user"].nickname, found_badge, days_since,
                self._date_str(dt)))
        else:
            event["stderr"].write("You have no '%s' badge" % badge)

    @utils.hook("received.command.badges")
    def badges(self, event):
        user = event["user"]
        if event["args"]:
            user = event["server"].get_user(event["args_split"][0])

        now = self._round_up_day(self._now())
        badges = []
        for badge, date in self._get_badges(user).items():
            days_since = self._days_since(now, self._parse_datetime(date))
            badges.append("%s on day %s" % (
                badge, days_since))

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
        badges[badge] = self._format_datetime(self._now())
        self._set_badges(event["user"], badges)
        event["stdout"].write("Added '%s' badge" % badge)

    @utils.hook("received.command.removebadge", min_args=1)
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
            event["stdout"].write("Removed '%s' badge" % found_badge)
        else:
            event["stderr"].write("You have no '%s' badge" % badge)

    @utils.hook("received.command.resetbadge", min_args=1)
    def reset_badge(self, event):
        badge = event["args"]
        badge_lower = badge.lower()
        badges = self._get_badges(event["user"])

        found_badge = None
        for badge_name in badges.keys():
            if badge_name.lower() == badge_lower:
                found_badge = badge_name
                break

        if found_badge:
            badges[found_badge] = self._format_datetime(self._now())
            self._set_badges(event["user"], badges)
            event["stdout"].write("Reset badge '%s'" % found_badge)
        else:
            event["stderr"].write("You have no '%s' badge" % badge)

    @utils.hook("received.command.updatebadge", min_args=2)
    def update_badge(self, event):
        badge = " ".join(event["args_split"][:-1])
        badge_lower = badge.lower()
        badges = self._get_badges(event["user"])

        found_badge = None
        for badge_name in badges.keys():
            if badge_name.lower() == badge_lower:
                found_badge = badge_name
                break

        if not found_badge:
            raise utils.EventError("You have no '%s' badge" % badge)

        value = event["args_split"][-1]
        if value.lower() == "today":
            value = self._now()
        else:
            match = RE_HUMAN_FORMAT.match(value)
            if not match:
                raise utils.EventError("Invalid date format, please use %s" %
                    HUMAN_FORMAT_HELP)
            value = datetime.datetime(
                year=int(match.group(1)),
                month=int(match.group(2)),
                day=int(match.group(3))
            )

        badges[found_badge] = self._format_datetime(value)
        self._set_badges(event["user"], badges)
        event["stdout"].write("Updated '%s' badge" % found_badge)
