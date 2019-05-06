import datetime
from src import ModuleManager, utils

DATE_FORMAT = "%Y-%m-%d"

def _parse(s):
    try:
        return datetime.datetime.strptime(s, DATE_FORMAT)
    except ValueError:
        return None
def _format(dt):
    return datetime.datetime.strftime(dt, DATE_FORMAT)
def _check(s):
    parsed = _parse(s)
    if parsed:
        return _format(parsed)
    return None

@utils.export("set", {"setting": "birthday", "help": "Set your birthday",
    "validate": _check})
class Module(ModuleManager.BaseModule):

    @utils.hook("received.command.birthday")
    def birthday(self, event):
        """
        :help: Get your, or someone else's, pronouns
        :usage: [nickname]
        """
        target_user = event["user"]
        if event["args"]:
            target_user = event["server"].get_user(event["args_split"][0])

        birthday = target_user.get_setting("birthday", None)

        if not birthday == None:
            birthday_parsed = _parse(birthday).date()
            now = datetime.datetime.utcnow().date()

            next_birthday = datetime.date(year=now.year,
                month=birthday_parsed.month, day=birthday_parsed.day)
            if next_birthday < now:
                next_birthday = next_birthday.replace(year=next_birthday.year+1)
            days = (next_birthday-now).days
            age = next_birthday.year-birthday_parsed.year

            if days > 0:
                event["stdout"].write("%s is %d in %d days" % (
                    target_user.nickname, age, days))
            else:
                event["stdout"].write("%s is %d today! 🎉" % (
                    target_user.nickname, age))
        else:
            event["stderr"].write("No birthday set for %s" %
                target_user.nickname)

    @utils.hook("received.command.birthdays")
    def birthdays(self, event):
        birthday_settings = event["server"].get_all_user_settings("birthday")
        birthdays = {}

        today = datetime.datetime.utcnow().date()
        for nickname, birthday in birthday_settings:
            birthday_parsed = _parse(birthday).date()
            if birthday_parsed.replace(year=today.year) == today:
                birthdays[nickname] = today.year-birthday_parsed.year
        if birthdays:
            birthdays_str = []
            for nickname, age in birthdays.items():
                nickname = event["server"].get_user(nickname).nickname
                birthdays_str.append("%s (%d)" % (nickname, age))

            event["stdout"].write("Birthdays today: %s" %
                ", ".join(birthdays_str))
        else:
            event["stdout"].write("There are no birthdays today")
