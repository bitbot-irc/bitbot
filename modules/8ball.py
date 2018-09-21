import random
import Utils

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
    "I'm on a break, ask again later",
    "As I see it, yes",
    "It is certain",
    "Naturally",
    "Reply hazy, try again later",
    Utils.underline(Utils.color("DO NOT WASTE MY TIME", Utils.COLOR_RED)),
    "Hmm... Could be!",
    "I'm leaning towards no",
    "Without a doubt",
    "Sources say no",
    "Sources say yes",
    "Sources say maybe"
]

class Module(object):
    def __init__(self, bot, events, exports):
        events.on("received.command.8ball").hook(
            self.decide,
            min_args=1,
            help="Ask the mystic 8ball a question!",
            usage="<question>"
        )

    def decide(selfs, event):
        event["stdout"].write("You shake the magic ball... it "
                              "says " + Utils.bold(random.choice(CHOICES)))
