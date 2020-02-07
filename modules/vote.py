#--depends-on check_mode
#--depends-on commands
#--depends-on permissions

import binascii, enum, os, uuid
from src import ModuleManager, utils

STR_NOVOTE = "Unknown vote '%s'"

class VoteCastResult(enum.Enum):
    Cast = 1
    Changed = 2
    Unchanged = 3

@utils.export("channelset", utils.BoolSetting("votes-start-restricted",
    "Whether starting a vote should be restricted to ops"))
@utils.export("channelset", utils.BoolSetting("votes-cast-restricted",
    "Whether casting a vote should be restricted to voiced-and-above users"))
class Module(ModuleManager.BaseModule):
    def _get_vote(self, channel, vote_id):
        return channel.get_setting("vote-%s" % vote_id, None)
    def _set_vote(self, channel, vote_id, vote):
        channel.set_setting("vote-%s" % vote_id, vote)

    def _random_id(self, channel):
        while True:
            vote_id = binascii.hexlify(os.urandom(3)).decode("ascii")
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

    def _cast_vote(self, channel, vote_id, user, chosen_option):
        vote = self._get_vote(channel, vote_id)
        option_nicks = vote["options"][chosen_option]

        cast_type = VoteCastResult.Cast

        for option, nicks in vote["options"].items():
            if user.name in nicks:
                if option == chosen_option:
                    return VoteCastResult.Unchanged
                else:
                    nicks.remove(user.name)
                    cast_type = VoteCastResult.Changed
                    break

        option_nicks.append(user.name)
        self._set_vote(channel, vote_id, vote)
        return cast_type

    def _open_votes(self, channel):
        open = []
        for setting, vote in channel.find_settings(prefix="vote-"):
            if vote["open"]:
                open.append(vote)
        return open

    @utils.hook("received.command.startvote", channel_only=True, min_args=1)
    def start_vote(self, event):
        """
        :help: Start a vote
        :usage: <description>
        """

        if event["target"].get_setting("votes-start-restricted", True):
            event["check_assert"](utils.Check("channel-mode", "o")|
                utils.Check("permission", "vote")|
                utils.Check("channel-access", "low,vote"))

        vote = self._start_vote(event["target"], event["args"])
        event["stdout"].write(
            "Vote %s started. use '%svote %s <option>' to vote (options: %s)" %
            (vote["id"], event["command_prefix"], vote["id"],
            self._format_options(vote)))

    @utils.hook("received.command.endvote", channel_only=True, min_args=1)
    def end_vote(self, event):
        """
        :help: End a vote
        :usage: <id>
        :require_mode: o
        :require_access: high,vote
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
        :help: Cast choice for a given vote
        :usage: <id> [choice]
        """
        if event["target"].get_setting("votes-cast-restricted", True):
            event["check_assert"](utils.Check("channel-mode", "v")|
                utils.Check("permission", "vote")|
                utils.Check("channel-access", "low,vote"))

        vote_id = event["args_split"][0]
        vote = self._get_vote(event["target"], vote_id)
        if vote == None:
            raise utils.EventError(STR_NOVOTE % vote_id)

        if not len(event["args_split"]) > 1:
            closed = "" if vote["open"] else " (closed)"
            event["stdout"].write("Vote %s%s: %s" % (
                vote_id, closed, self._format_vote(vote)))
        else:
            if not vote["open"]:
                raise utils.EventError("%s: vote %s is closed" % (
                    event["user"].nickname, vote_id))

            choice = event["args_split"][1].lower()
            if not choice in vote["options"]:
                raise utils.EventError("Vote options: %s" %
                    self._format_options(vote))

            cast_result = self._cast_vote(event["target"], vote_id,
                event["user"], choice)

            cast_desc = "has been cast"
            if cast_result == VoteCastResult.Changed:
                cast_desc = "has been changed"
            elif cast_result == VoteCastResult.Unchanged:
                cast_desc = "is unchanged"

            event["stdout"].write("%s: your vote %s." %
                (event["user"].nickname, cast_desc))

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
