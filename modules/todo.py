#--depends-on commands

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.todo")
    def todo(self, event):
        """
        :help: Find out what's in your todo list
        :usage: [item number]
        """
        todo = event["user"].get_setting("todo", [])
        if event["args"]:
            if event["args_split"][0].isdigit() and int(event["args_split"][0]) > 0:
                index = int(event["args_split"][0])
                if len(todo) >= index:
                    event["stdout"].write("Todo %d: %s" % (index, todo[index-1]))
                else:
                    event["stderr"].write("You do not have that many things in your todo list")
            else:
                event["stderr"].write("Please provide a number")
        else:
            todo_count = len(todo)
            event["stdout"].write("There are %d items in your todo list" % todo_count)

    @utils.hook("received.command.todoadd", min_args=1)
    def todo_add(self, event):
        """
        :help: Add something to your todo list
        :usage: <description>
        """
        arg_lower = event["args"].lower()
        todo = event["user"].get_setting("todo", [])
        for item in todo:
            if item.lower() == arg_lower:
                raise utils.EventError("That is already in your todo list")
        todo.append(event["args"])
        event["user"].set_setting("todo", todo)
        event["stdout"].write("Saved")

    @utils.hook("received.command.tododel", min_args=1)
    def todo_del(self, event):
        """
        :help: Remove something from your todo list
        :usage: <item number>
        """
        todo = event["user"].get_setting("todo", [])
        if event["args_split"][0].isdigit() and int(event["args_split"][0]) > 0:
            index = int(event["args_split"][0])
            if len(todo) >= index:
                todo.pop(index-1)
                event["user"].set_setting("todo", todo)
                event["stdout"].write("Todo item removed")
            else:
                event["stderr"].write("You do not have that many things in "
                    "your todo list")
        else:
            event["stderr"].write("Please provided a todo item number to remove")

    @utils.hook("received.command.todomove", min_args=2)
    def todo_move(self, event):
        """
        :help: Move a todo item to a different index
        :usage: <from> <to>
        """
        _from_str, to_str = event["args_split"][0], event["args_split"][1]
        if not _from_str.isdigit() or not to_str.isdigit():
            event["stdout"].write("Please provide numeric indexes")
            return

        _from, to = int(_from_str)-1, int(to_str)-1
        if _from < 0 or to < 0:
            raise utils.EventError("Both indexes must be above 0")

        todo = event["user"].get_setting("todo", [])
        if _from > len(todo) or to > len(todo):
            raise utils.EventError("Both indexes must be less than the "
                "size of your todo list")

        todo.insert(to, todo.pop(_from))
        event["user"].set_setting("todo", todo)
        event["stdout"].write("Moved todo item %s to position %s" % (
            _from_str, to_str))
