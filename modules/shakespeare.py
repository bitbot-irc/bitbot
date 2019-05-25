#--depends-on commands
import random
from src import ModuleManager, utils

INSULT_INTRO = ["Thou art a", "Ye", "Thou", "Thy", "Thee"]

INSULT_PART_1 = ["artless", "bawdy", "beslubbering", "bootless", "churlish",
                 "cockered", "clouted", "craven", "currish", "dankish",
                 "dissembling",
                 "droning", "errant", "fawning", "fobbing", "forward", "frothy",
                 "gleeking", "goatish", "gorbellied", "impertinent",
                 "infectious",
                 "jarring", "loggerheaded", "lumpish", "mammering", "mangled",
                 "mewling", "paunchy", "pribbling", "puking", "puny",
                 "qualling",
                 "rank", "reeky", "roguish", "ruttish", "saucy", "spleeny",
                 "spongy",
                 "surly", "tottering", "unmuzzled", "vain", "venomed",
                 "villainous",
                 "warped", "wayward", "weedy", "yeast"]

INSULT_PART_2 = ["base-court", "bat-fowling", "beef-witted", "beetle-headed",
                 "boil-brained", "clapper-clawed", "clay-brained",
                 "common-kissing",
                 "crook-pated", "dismal-dreaming", "dizzy-eyed", "doghearted",
                 "dread-bolted", "earth-vexing", "elf-skinned", "fat-kidneyed",
                 "fen-sucked", "flap-mouthed", "fly-bitten", "folly-fallen",
                 "fool-born", "full-gorged", "guts-griping", "half-faced",
                 "hasty-witted", "hedge-born", "hell-hated", "idle-headed",
                 "ill-breeding", "ill-nurtured", "knotty-pated", "milk-livered",
                 "motley-minded", "onion-eyed", "plume-plucked", "pottle-deep",
                 "pox-marked", "reeling-ripe", "rough-hewn", "rude-growing",
                 "rump-fed", "shard-borne", "sheep-biting", "spur-galled",
                 "swag-bellied", "tardy-gaited", "tickle-brained",
                 "toad-spotted",
                 "unchin-snouted", "weather-bitten"]

INSULT_PART_3 = ["apple-john", "baggage", "barnacle", "bladder", "boar-pig",
                 "bugbear", "bum-bailey", "canker-blossom", "clack-dish",
                 "clotpole",
                 "coxcomb", "codpiece", "death-token", "dewberry",
                 "flap-dragon",
                 "flax-wench", "flirt-gill", "foot-licker", "fustilarian",
                 "giglet",
                 "gudgeon", "haggard", "harpy", "hedge-pig", "horn-beast",
                 "hugger-mugger", "joithead", "lewdster", "lout", "maggot-pie",
                 "malt-worm", "mammet", "measle", "minnow", "miscreant",
                 "moldwarp",
                 "mumble-news", "nut-hook", "pigeon-egg", "pignut", "puttock",
                 "pumpion", "ratsbane", "scut", "skainsmate", "strumpet",
                 "varlot",
                 "vassal", "whey-face", "wagtail"]


class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.insult")
    def dispense_insult(self, event):
        insult = [random.choice(INSULT_INTRO), random.choice(INSULT_PART_1),
                  random.choice(INSULT_PART_2), random.choice(INSULT_PART_3)]

        insult = " ".join(insult)
        target = ""

        if event["args_split"]:
            target = event["args_split"][0]
            if event["server"].has_user(target):
                target= event["server"].get_user(target).nickname
            target = "%s, " % target

        event["stdout"].write(target + insult + "!")
