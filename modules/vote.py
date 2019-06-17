import binascii, functools, operator, os, uuid
from src import ModuleManager, utils

STR_NOVOTE = "Unknown vote '%s'"

class Module(ModuleManager.BaseModule):
    def _get_vote(self, channel, vote_id):
        return channel.get_setting("vote-%s" % vote_id, None)
    def _set_vote(self, channel, vote_id, vote):
        channel.set_setting("vote-%s" % vote_id, vote)

    def _random_id(self, channel):
        while True:
            vote_id = binascii.hexlify(os.urandom(4)).decode("ascii")
            if self._get_vote(channel, vote_id) == None:
                return vote_id

    def _close_vote(self, channel, vote_id):
        vote = self._get_vote(channel, vote_id)
        if vote:
            vote["open"] = False
            self._set_vote(channel, vote_id, vote)
            return True
        return False

    def _start_vote(self, channel, description):
        vote_id = self._random_id(channel)
        vote = {"description": description, "options": {"yes": [], "no": []},
            "electorate": [], "open": True, "id": vote_id}
        self._set_vote(channel, vote_id, vote)
        return vote

    def _format_vote(self, vote):
        options = ["%d %s" % (len(v), k) for k, v in vote["options"].items()]
        return "%s (%s)" % (vote["description"], ", ".join(options))
    def _format_options(self, vote):
        return ", ".join("'%s'" % o for o in vote["options"])

    def _cast_vote(self, channel, vote_id, user, option):
        vote = self._get_vote(channel, vote_id)
        option = vote["options"][option]
        voters = functools.reduce(operator.concat,
            list(vote["options"].values()))

        if user.name in voters:
            return False

        option.append(user.name)
        self._set_vote(channel, vote_id, vote)
        return True

    def _open_votes(self, channel):
        open = []
        for setting, vote in channel.find_settings_prefix("vote-"):
            if vote["open"]:
                open.append(vote)
        return open

    @utils.hook("received.command.startvote", channel_only=True, min_args=1)
    def start_vote(self, event):
        """
        :help: Start a vote
        :usage: <description>
        :require_mode: o
        :permission: vote
        """
        vote = self._start_vote(event["target"], event["args"])
        event["stdout"].write(
            "Vote %s started. use '%svote <option>' to vote (options: %s)" %
            (vote["id"], event["command_prefix"], self._format_options(vote)))

    @utils.hook("received.command.endvote", channel_only=True, min_args=1)
    def end_vote(self, event):
        """
        :help: End a vote
        :usage: <id>
        :require_mode: o
        :permission: vote
        """
        vote_id = event["args_split"][0]

        if self._close_vote(event["target"], vote_id):
            vote = self._get_vote(event["target"], vote_id)
            event["stdout"].write("Vote %s ended: %s" %
                (vote_id, self._format_vote(vote)))
        else:
            event["stderr"].write(STR_NOVOTE % vote_id)

    @utils.hook("received.command.vote", channel_only=True, min_args=1)
    def vote(self, event):
        """
        :help: Vote in the channel's current vote
        :usage: <id> [choice]
        """
        vote_id = event["args_split"][0]
        vote = self._get_vote(event["target"], vote_id)
        if vote == None:
            raise utils.EventError(STR_NOVOTE % vote_id)

        if not len(event["args_split"]) > 1:
            closed = "" if vote["open"] else " (closed)"
            event["stdout"].write("Vote %s%s: %s" % (
                vote_id, closed, self._format_vote(vote)))
        else:
            choice = event["args_split"][1].lower()
            if not choice in vote["options"]:
                raise utils.EventError("Vote options: %s" %
                    self._format_options(vote))

            if self._cast_vote(event["target"], vote_id, event["user"], choice):
                event["stdout"].write("%s: your vote has been cast." %
                    event["user"].nickname)
            else:
                event["stderr"].write("%s: you have already voted." %
                    event["user"].nickname)

    @utils.hook("received.command.votes", channel_only=True)
    def votes(self, event):
        """
        :help: List open votes in the current channel
        """
        open_votes = self._open_votes(event["target"])
        if open_votes:
            open_votes_str = [
                "%s (%s)" % (v["description"], v["id"]) for v in open_votes]
            event["stdout"].write("Open votes: %s" % ", ".join(open_votes_str))
        else:
            event["stderr"].write("There are no open votes")
