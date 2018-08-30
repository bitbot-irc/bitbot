import random


class Module(object):
    def __init__(self, bot):
        bot.events.on("received.command.strax").hook(
            self.strax, help="Glory to the sontaran empire, through IRC!")

    def strax(self, event):
        suggestion_greeting = ["Might I suggest", "I'd suggest", "We should attack now with", "We must attack now with"]
        method_of_attack_a = ["full-frontal", "pincer", "surprise", "brutally excessive", "multi-pronged", "glorious",
                              "violent", "devestating" "superior"]
        method_of_attack_an = ["acid-heavy", "immediate", "overwhelming", "unstoppable"]
        type_of_attack = ["assault", "attack", "bombardment", "offensive", "barrage", "charge", "strike", "operation",
                          "manoeuvre", "blitzkrieg"]
        attack_adjective = ["laser", "berserker", "acid", "armoured attack", "proton",
                            "three kinds of", "atomic", "toxic", "explosive",
                            "red-hot", "thermal", "automated fire", "cluster",
                            "enhanced germ", "energy-drink-fueled"]
        attack_object = ["bees", "chainsaws", "marmots", "acid", "monkeys", "mines", "bombs", "snakes", "spiders",
                         "knives", "rockets", "sharks", "owls", "repurposed cybermats", "cannons", "alligators"]
        attack_object_two = ["robots", "ninjas", "grenades", "a dolphin full of napalm", "acid", "dynamite",
                             "xenomorphs", "lots and lots of C4", "tactical nukes", "MacGyver", "bio-weapons",
                             "rocket launchers", "an elephant", "a memory worm for afterwards", "this pencil"]

        method_of_attack = " an " + random.choice(method_of_attack_an) if random.choice(1,
                                                                                        2) == 1 else " a " + random.choice(
            method_of_attack_a)

        suggestion = random.choice(
            suggestion_greeting) + method_of_attack + " " + type_of_attack + " with " + attack_adjective + " " + attack_object + " and " + attack_object_two + "?"

        event["stdout"].write(suggestion)
