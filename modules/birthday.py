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
