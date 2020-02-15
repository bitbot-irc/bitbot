#--depends-on commands

from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.todo")
    @utils.spec("!'list ?<index>int")
    @utils.spec("!'add !<description>string")
    @utils.spec("!'remove !<index>int")
    @utils.spec("!'move !<from>int !<to>int")
    def todo(self, event):
        user_todo = event["user"].get_setting("todo", [])
        if event["spec"][0] == "list":
            if not user_todo:
                raise utils.EventError("%s: you have no todo items"
                    % event["user"].nickname)

            if not event["spec"][1] == None:
                index = event["spec"][1]-1
                if not index in dict(enumerate(user_todo)):
                    raise utils.EventError("%s: unknown todo index %d"
                        % (event["user"].nickname, event["spec"][1]))
                event["stdout"].write("%s: (%d) %s"
                    % (event["user"].nickname, event["spec"][1],
                    user_todo[index]))
            else:
                outs = ["(%d) %s" % (i+1, s) for i, s in enumerate(user_todo)]
                event["stdout"].write("%s: %s"
                    % (event["user"].nickname, ", ".join(outs)))

        elif event["spec"][0] == "add":
            user_todo.append(event["spec"][1])
            event["user"].set_setting("todo", user_todo)
            event["stdout"].write("%s: todo item %d added"
                % (event["user"].nickname, len(user_todo)))

        elif event["spec"][0] == "remove":
            index = event["spec"][1]-1
            if not index in dict(enumerate(user_todo)):
                raise utils.EventError("%s: unknown todo index %d"
                    % event["user"].nickname)
            description = user_todo.pop(index)
            event["user"].set_setting("todo", user_todo)
            event["stdout"].write("%s: todo item %d removed: %s"
                % (event["user"].nickname, event["spec"][1], description))

        elif event["spec"][0] == "move":
            todo_dict = dict(enumerate(user_todo))
            start_index, end_index = event["spec"][1]-1, event["spec"][2]-1
            for i, name in [[start_index, "start"], [end_index, "end"]]:
                if not i in todo_dict:
                    raise utils.EventError("%s: unknown todo %s index %d"
                        % (event["user"].nickname, name, i+1))
            description = user_todo.pop(start_index)
            user_todo.insert(end_index, description)
            event["user"].set_setting("todo", user_todo)
            event["stdout"].write("%s: todo item moved to %d: %s"
                % (event["user"].nickname, event["spec"][2], description))
