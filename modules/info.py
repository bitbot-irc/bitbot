import os
from bitbot import IRCBot, ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.version")
    def version(self, event):
        commit_hash = None
        git_dir = os.path.join(self.bot.directory, ".git")
        head_filepath = os.path.join(git_dir, "HEAD")
        if os.path.isfile(head_filepath):
            ref = None
            with open(head_filepath, "r") as head_file:
                ref = head_file.readline().split(" ", 1)[1].strip()
            branch = ref.rsplit("/", 1)[1]

            ref_filepath = os.path.join(git_dir, ref)
            if os.path.isfile(ref_filepath):
                with open(ref_filepath, "r") as ref_file:
                    commit_hash = ref_file.readline().strip()

        out = "Version: BitBot %s" % IRCBot.VERSION
        if not commit_hash == None:
            out = "%s (%s@%s)" % (out, branch, commit_hash[:8])
        event["stdout"].write(out)

    @utils.hook("received.command.source")
    def source(self, event):
        event["stdout"].write("Source: %s" % IRCBot.SOURCE)
