#--depends-on commands
#--depends-on config

import datetime, typing
from src import ModuleManager, utils

DATE_YEAR_FORMAT = "%Y-%m-%d"
DATE_FORMAT = "%d-%b"

EXAMPLE_DATE_YEAR = "1995-09-15"
EXAMPLE_DATE = "01-jan"

def _parse(s):
    if s.count("-") == 1:
        try:
            return False, datetime.datetime.strptime(s, DATE_FORMAT)
        except ValueError:
            return None
    else:
        try:
            return True, datetime.datetime.strptime(s, DATE_YEAR_FORMAT)
        except ValueError:
            return None

def _format_year(dt):
    return "%s-%s-%s" % (str(dt.year).zfill(4), str(dt.month).zfill(2),
        str(dt.day).zfill(2))
def _format_noyear(dt):
    return datetime.datetime.strftime(dt, DATE_FORMAT)

def _format(years, dt):
    if years:
        return _format_year(dt)
    else:
        return _format_noyear(dt)

def _parse_setting(value):
    parsed = _parse(value)
    if parsed:
        years, parsed = parsed
        return _format(years, parsed)
    else:
        raise utils.settings.SettingParseException(
            "Please provide either yyyy-mm-dd or dd-mmm (e.g. %s or %s)" %
            (EXAMPLE_DATE_YEAR, EXAMPLE_DATE))

def _apostrophe(nickname):
    if nickname[-1].lower() == "s":
        return "%s'" % nickname
    return "%s's" % nickname

@utils.export("set", utils.FunctionSetting(_parse_setting, "birthday",
    "Set your birthday", example=EXAMPLE_DATE_YEAR))
class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.birthday")
    def birthday(self, event):
        """
        :help: Get your, or someone else's, birthday
        :usage: [nickname]
        :require_setting: birthday
        :require_setting_unless: 1
        """
        target_user = event["user"]
        if event["args"]:
            target_user = event["server"].get_user(event["args_split"][0])

        birthday = target_user.get_setting("birthday", None)

        if not birthday == None:
            years, birthday_parsed = _parse(birthday)
            birthday_parsed = birthday_parsed.date()
            now = datetime.datetime.utcnow().date()

            next_birthday = datetime.date(year=now.year,
                month=birthday_parsed.month, day=birthday_parsed.day)
            if next_birthday < now:
                next_birthday = next_birthday.replace(year=next_birthday.year+1)
            days = (next_birthday-now).days
            days_str = "day" if days == 1 else "days"
            age = next_birthday.year-birthday_parsed.year

            if days > 0:
                if years:
                    event["stdout"].write("%s is %d in %d %s" % (
                        target_user.nickname, age, days, days_str))
                else:
                    event["stdout"].write("%s birthday is in %d %s" % (
                        _apostrophe(target_user.nickname), days, days_str))
            else:
                if years:
                    event["stdout"].write("%s is %d today! 🎉" % (
                        target_user.nickname, age))
                else:
                    event["stdout"].write("%s birthday is today! 🎉" %
                        _apostrophe(target_user.nickname))
        else:
            event["stderr"].write("No birthday set for %s" %
                target_user.nickname)

    @utils.hook("received.command.birthdays")
    def birthdays(self, event):
        birthday_settings = event["server"].get_all_user_settings("birthday")
        birthdays = {}

        today = datetime.datetime.utcnow().date()
        for nickname, birthday in birthday_settings:
            years, birthday_parsed = _parse(birthday)
            birthday_parsed = birthday_parsed.date()
            if birthday_parsed.replace(year=today.year) == today:
                birthdays[nickname] = [years, today.year-birthday_parsed.year]
        if birthdays:
            birthdays_str = []
            for nickname, (years, age) in birthdays.items():
                nickname = event["server"].get_user(nickname).nickname
                if years:
                    birthdays_str.append("%s (%d)" % (nickname, age))
                else:
                    birthdays_str.append(nickname)

            event["stdout"].write("Birthdays today: %s" %
                ", ".join(birthdays_str))
        else:
            event["stdout"].write("There are no birthdays today")
