import json
from src import ModuleManager, utils

@utils.export("channelset", {"setting": "github-hook",
    "help": ("Disable/Enable showing BitBot's github commits in the "
    "current channel"), "validate": utils.bool_or_none})
class Module(ModuleManager.BaseModule):
    @utils.hook("api.post.github")
    def github(self, event):
        data = event["data"]
        try:
            data = json.loads(data)
        except:
            return

        if "commits" in data:
            full_name = data["repository"]["full_name"]

            for commit in data["commits"]:
                id = commit["id"]

                message = commit["message"].split("\n")
                message = [line.strip() for line in message]
                message = " ".join(message)

                author = "%s <%s>" % (commit["author"]["username"],
                    commit["author"]["email"])
                modified_count = len(commit["modified"])
                added_count = len(commit["added"])
                removed_count = len(commit["removed"])

                line = ("(%s) [files: %d/%d/%d mod/add/del] commit by %s: "
                    "'%s'") % (full_name, modified_count, added_count,
                    removed_count, author, message)
                hooks = self.bot.database.channel_settings.find_by_setting(
                    "github-hook")
                hooks = [hook for hook in hooks if hook[2]]
                for server_id, channel_name, _ in hooks:
                    server = self.bot.get_server(server_id)
                    channel = server.get_channel(channel_name)

                    self.events.on("send.stdout").call(target=channel,
                        module_name="Github", server=server, message=line)
                    self.bot.register_both(server)
