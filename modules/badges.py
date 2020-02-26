#--depends-on commands

import datetime, re
from src import ModuleManager, utils

RE_HUMAN_FORMAT = re.compile(r"(\d\d\d\d)-(\d?\d)-(\d?\d)")
HUMAN_FORMAT_HELP = "year-month-day (e.g. 2018-12-29)"

class Module(ModuleManager.BaseModule):
    @utils.export("command-spec.marginstring")
    def _marginstring_spec(self, server, channel, user, args):
        if len(args) > 1:
            new_args = args[:-1]
            return " ".join(new_args), len(new_args)
        else:
            return None, 1

    def _round_up_day(self, dt: datetime.datetime):
        return dt.date()+datetime.timedelta(days=1)
    def _days_since(self, now: datetime.date, dt: datetime.datetime):
        return (now-dt.date()).days

    def _get_badges(self, user):
        return user.get_setting("badges", {})
    def _set_badges(self, user, badges):
        user.set_setting("badges", badges)
    def _del_badges(self, user):
        user.del_setting("badges")

    @utils.hook("received.command.badge")
    @utils.kwarg("help", "List, add and remove badges")
    @utils.spec("!'list ?<nickname>ouser")
    @utils.spec("!'show !<name>string")
    @utils.spec("!'add !<name>marginstring !'now,today")
    @utils.spec("!'add !<name>marginstring !date")
    @utils.spec("!'remove !<name>string")
    def badge(self, event):
        now = self._round_up_day(utils.datetime.utcnow())

        if event["spec"][0] == "list":
            target = event["spec"][1] or event["user"]
            badges = self._get_badges(target)
            if not badges:
                raise utils.EventError("%s has no badges" % target.nickname)

            outs = []
            for name in sorted(badges.keys()):
                dt = utils.datetime.parse.iso8601(badges[name])
                days_since = self._days_since(now, dt)
                human = utils.datetime.format.date_human(dt)
                outs.append("%s on day %d (%s)"
                    % (name, days_since, human))
            event["stdout"].write("badges for %s: %s"
                % (target.nickname, ", ".join(outs)))
        else:
            badges = self._get_badges(event["user"])
            mut_badges = badges.copy()
            name = event["spec"][1]

            if event["spec"][0] == "add":
                if event["spec"][2] in ["now", "today"]:
                    dt = utils.datetime.utcnow()
                else:
                    dt = event["spec"][2]

                exists = name in badges
                action = "updated" if exists else "added"

                mut_badges[name] = utils.datetime.format.iso8601(dt)
                human = utils.datetime.format.date_human(dt)
                event["stdout"].write("%s: %s badge %s (%s)"
                    % (event["user"].nickname, action, name, human))

            else:
                if not name in badges:
                    raise utils.EventError("%s: you don't have a '%s' badge"
                        % (event["user"].nickname, name))

                dt = utils.datetime.parse.iso8601(badges[name])
                human = utils.datetime.format.date_human(dt)
                if event["spec"][0] == "remove":
                    del mut_badges[name]
                    event["stdout"].write("%s: removed badge '%s' (%s)"
                        % (event["user"].nickname, name, human))
                elif event["spec"][0] == "show":
                    days_since = self._days_since(now, dt)
                    event["stdout"].write("%s: your %s badge is on day %d (%s)"
                        % (event["user"].nickname, name, days_since, human))

            if not mut_badges == badges:
                self._set_badges(event["user"], mut_badges)

    @utils.hook("received.command.badgeclear")
    @utils.kwarg("help", "Clear a user's badges")
    @utils.kwarg("permission", "badge-clear")
    @utils.spec("!<nickname>ouser")
    def badgeclear(self, event):
        if self._get_badges(event["spec"][0]):
            self._del_badges(event["spec"][0])
            event["stdout"].write("Cleared badges for %s"
                % event["spec"][0].nickname)
        else:
            event["stderr"].write("%s has no badges"
                % event["spec"][0].nickname)
