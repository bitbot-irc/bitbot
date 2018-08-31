class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("todo").hook(
            self.todo, help="Find out what's in your todo list",
            usage="[item number]")
        bot.events.on("received").on("command").on("todoadd").hook(
            self.todo_add, min_args=1, help="Add something to your todo list",
            usage="<description>")
        bot.events.on("received").on("command").on("tododel").hook(
            self.todo_del, min_args=1, help="Remove something from your "
                                            "todo list", usage="<item number>")

    def todo(self, event):
        todo = event["user"].get_setting("todo", [])
        if event["args"]:
            if event["args_split"][0].isdigit() and int(
                    event["args_split"][0]) > 0:
                index = int(event["args_split"][0])
                if len(todo) >= index:
                    event["stdout"].write(
                        "Todo %d: %s" % (index, todo[index - 1]))
                else:
                    event["stderr"].write(
                        "You do not have that many things in your todo")
            else:
                event["stderr"].write("Please provide a number")
        else:
            todo_count = len(todo)
            event["stdout"].write(
                "There are %d items in your todo" % todo_count)

    def todo_add(self, event):
        arg_lower = event["args"].lower()
        todo = event["user"].get_setting("todo", [])
        for item in todo:
            if item.lower() == arg_lower:
                event["stderr"].write(
                    "That is already in your todo")
                return
        todo.append(event["args"])
        event["user"].set_setting("todo", todo)
        event["stdout"].write("Saved")

    def todo_del(self, event):
        todo = event["user"].get_setting("todo", [])
        if event["args_split"][0].isdigit() and int(event["args_split"][0]) > 0:
            index = int(event["args_split"][0])
            if len(todo) >= index:
                todo.pop(index - 1)
                event["user"].set_setting("todo", todo)
                event["stdout"].write("Todo item removed")
            else:
                event["stderr"].write("You do not have that many things in "
                                      "your todo")
        else:
            event["stderr"].write(
                "Please provided a todo item number to remove")
