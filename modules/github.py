import json
from src import ModuleManager, utils

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
                id = command["id"]
                message = commit["message"]
                author = "%s <%s>" % (commit["author"]["username"],
                    commit["author"]["email"])
                modified_count = len(commit["modified"])
                added_count = len(commit["added"])
                removed_count = len(commit["removed"])

                print("(%s) [%d/%d/%d mod/add/del] commit by %s: %s" % (
                    full_name, modified_count, added_count, removed_count,
                    author, message))
