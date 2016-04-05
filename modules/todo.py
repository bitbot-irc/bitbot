

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("todo").hook(
            self.todo)

    def todo(self, event):
        if len(event["args_split"]) > 1:
            action = event["args_split"][0].lower()
            arg = " ".join(event["args_split"][1:])
            arg_lower = arg.lower()
            todo = event["user"].get_setting("todo", [])
            if action == "add":
                for item in todo:
                    if item.lower() == arg_lower:
                        event["stderr"].write(
                            "That is already in your todo")
                        return
                todo.append(arg)
                event["user"].set_setting("todo", list(todo))
                event["stdout"].write("Saved")
            elif action == "remove":
                if event["args_split"][1].isdigit():
                    index = int(event["args_split"][1])
                    if len(todo) >= index:
                        todo.pop(index-1)
                        event["user"].set_setting("todo", todo)
                        event["stdout"].write("Todo item removed")
                    else:
                        event["stderr"].write("You do not have that many things in "
                            "your todo")
                else:
                    event["stderr"].write("Please provided a todo item number to remove")
            elif action == "show":
                if event["args_split"][1].isdigit():
                    index = int(event["args_split"][1])
                    if len(todo) >= index:
                        event["stdout"].write("Todo %d: %s" % (index, todo[index-1]))
                    else:
                        event["stderr"].write("You do not have that many things in "
                            "your todo")
                else:
                    event["stderr"].write("Please provide a todo item number to show")
        elif len(event["args_split"]) == 1:
            event["stderr"].write("Please provided an action and an argument")
        else:
            todo_count = len(event["user"].get_setting("todo", []))
            event["stdout"].write("There are %d items in your todo" % todo_count)
