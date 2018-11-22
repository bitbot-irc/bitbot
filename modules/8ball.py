import random
from src import ModuleManager, utils

CHOICES = [
    "Definitely",
    "Yes",
    "Probably",
    "Maybe",
    "Probably not",
    "No",
    "Definitely not",
    "I don't know",
    "Ask again later",
    "The answer is unclear",
    "Absolutely",
    "Dubious at best",
    "As I see it, yes",
    "Without a doubt, it's a certainty",
    "Yep.",
    "It is certain",
    "Naturally",
    "Reply hazy, try again later",
    utils.irc.underline(utils.irc.color("DO NOT WASTE MY TIME",
        utils.consts.RED)),
    "Hmm... Could be!",
    "Without a doubt",
    "Sources say no",
    "Sources say yes",
    "Sources say maybe",
    "For sure",
    "It's guaranteed"
]

class Module(ModuleManager.BaseModule):
    _name = "8-ball"
    @utils.hook("received.command.8ball", min_args=1)
    def decide(selfs, event):
        """
        :help: Ask the mystic 8ball a question!
        :usage: <question>
        """
        event["stdout"].write("You shake the magic ball... it says %s" %
            utils.irc.bold(random.choice(CHOICES)))
