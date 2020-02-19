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
    @utils.spec("!'add !<name>marginstring !'now,today")
    @utils.spec("!'add !<name>marginstring !date")
    @utils.spec("!'remove !<name>string")
    def badge(self, event):
        if event["spec"][0] == "list":
            target = event["spec"][1] or event["user"]
            badges = self._get_badges(target)
            if not badges:
                raise utils.EventError("%s has no badges" % target.nickname)

            now = self._round_up_day(utils.datetime.utcnow())

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
            if event["spec"][0] == "add":
                if event["spec"][2] in ["now", "today"]:
                    dt = utils.datetime.utcnow()
                else:
                    dt = event["spec"][2]

                exists = event["spec"][1] in badges
                action = "updated" if exists else "added"

                badges[event["spec"][1]] = utils.datetime.format.iso8601(dt)
                human = utils.datetime.format.date_human(dt)
                event["stdout"].write("%s: %s badge %s (%s)"
                    % (event["user"].nickname, action, event["spec"][1], human))

            elif event["spec"][0] == "remove":
                if not event["spec"][1] in badges:
                    raise utils.EventError("%s: you don't have a '%s' badge"
                        % (event["user"].nickname, event["spec"][1]))

                human = utils.datetime.format.date_human(
                    utils.datetime.parse.iso8601(badges.pop(event["spec"][1])))
                event["stdout"].write("%s: removed badge '%s' (%s)"
                    % (event["user"].nickname, event["spec"][1], human))
            self._set_badges(event["user"], badges)

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
