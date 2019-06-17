import binascii, os, uuid
from src import ModuleManager, utils

STR_NOVOTE = "There is currently no vote running."

class Module(ModuleManager.BaseModule):
    def _get_vote(self, channel):
        return channel.get_setting("vote", None)
    def _set_vote(self, channel, vote):
        channel.set_setting("vote", vote)
    def _del_vote(self, channel):
        channel.del_setting("vote")

    def _add_archive_vote(self, channel, vote, id):
        channel.set_setting("vote-%s" % id, vote)
    def _get_archive_vote(self, channel, id):
        return channel.get_setting("vote-%s" % id, None)

    def _random_id(self):
        return binascii.hexlify(os.urandom(4)).decode("ascii")
    def _archive_vote(self, channel):
        vote = self._get_vote(channel)
        vote_id = self._random_id()
        self._add_archive_vote(channel, vote, vote_id)
        self._del_vote(channel)
        return vote_id

    def _format_vote(self, vote):
        return "%s (%s yes, %s no)" % (vote["description"], len(vote["yes"]),
            len(vote["no"]))

    def _cast_vote(self, channel, user, yes):
        vote = self._get_vote(channel)
        key = "yes" if yes else "no"
        voters = vote["yes"]+vote["no"]

        if user.name in voters:
            return False

        vote[key].append(user.name)
        self._set_vote(channel, vote)
        return True

    @utils.hook("received.command.startvote", channel_only=True, min_args=1)
    def start_vote(self, event):
        """
        :help: Start a yes/no vote
        :usage: <description>
        :require_mode: o
        :permission: vote
        """
        current_vote = self._get_vote(event["target"])
        if not current_vote == None:
            raise utils.EventError("There's already a vote running")

        self._set_vote(event["target"], {"description": event["args"],
            "yes": [], "no": [], "electorate": []})
        event["stdout"].write(
            "Vote started. use '%svote yes' or '%svote no' to vote." % (
            event["command_prefix"], event["command_prefix"]))

    @utils.hook("received.command.endvote", channel_only=True)
    def end_vote(self, event):
        """
        :help: End the current yes/no vote
        :require_mode: o
        :permission: vote
        """
        vote = self._get_vote(event["target"])
        if vote == None:
            event["stderr"].write(STR_NOVOTE)
        else:
            vote_id = self._archive_vote(event["target"])
            event["stdout"].write("Vote %s ended: %s" %
                (vote_id, self._format_vote(vote)))

    @utils.hook("received.command.vote", channel_only=True)
    def vote(self, event):
        """
        :help: Vote in the channel's current vote
        :usage: yes|no
        """
        vote = self._get_vote(event["target"])
        if vote == None:
            raise utils.EventError(STR_NOVOTE)

        if not event["args"]:
            event["stdout"].write("Current vote: %s)" % self._format_vote(vote))
        else:
            choice = event["args_split"][0].lower()
            if not choice in ["yes", "no"]:
                raise utils.EventError("Please vote 'yes' or 'no'")

            if self._cast_vote(event["target"], event["user"], choice=="yes"):
                event["stdout"].write("%s: your vote has been cast." %
                    event["user"].nickname)
            else:
                event["stderr"].write("%s: you have already voted." %
                    event["user"].nickname)

    @utils.hook("received.command.getvote", min_args=1)
    def get_vote(self, event):
        """
        :help: Show stats for a previous vote
        :usage: <id>
        """
        vote_id = event["args_split"][0].lower()
        vote = self._get_archive_vote(event["target"], vote_id)

        if vote == None:
            event["stderr"].write("Unknown vote '%s'" % vote_id)
        else:
            event["stdout"].write("Vote %s: %s" % (vote_id,
                self._format_vote(vote)))
