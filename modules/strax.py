#--depends-on commands

import random
from src import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.strax")
    def strax(self, event):
        """
        :help: Suggests a glorious method of battle for the glory of the
            Sontaran Empire, through IRC!
        """
        suggestion_greeting = ["Might I suggest", "Can I suggest", "Should we attack immediately with"]
        command_greeting = ["We should attack now with", "We must attack now with", "I suggest attacking with",
                            "We should coordinate an attack with"]
        method_of_attack_a = ["full-frontal", "pincer", "surprise", "brutally excessive", "multi-pronged", "glorious",
                              "violent", "devastating", "superior", "fast-paced", "fleet-wide", "stealth",
                              "diversionary", "exceptional", "point-blank", "night time"]
        method_of_attack_an = ["acid-heavy", "immediate", "overwhelming", "unstoppable", "underground", "arial",
                               "naval", "amphibious", "full-scale"]
        type_of_attack = ["assault", "attack", "bombardment", "offensive", "barrage", "charge", "strike", "operation",
                          "manoeuvre", "blitzkrieg", "ambush", "massacre"]
        attack_adjective = ["laser", "berserker", "acid", "armoured attack", "proton",
                            "three kinds of", "atomic", "toxic", "explosive",
                            "red-hot", "thermal", "automated fire", "cluster",
                            "enhanced germ", "energy-drink-fueled", "battle ready", "Sontaran", "military"]
        attack_object = ["bees", "chainsaws", "marmots", "acid", "monkeys", "mines", "bombs", "snakes", "spiders",
                         "knives", "rockets", "sharks", "owls", "repurposed cybermats", "cannons", "alligators", "ants",
                         "gorillas", "genetically enhanced cyber-elephants", "mechanoids", "KGB agents",
                         "MI5 operatives", "thermonuclear missiles"]
        attack_object_two = ["robots", "ninjas", "grenades", "a dolphin full of napalm", "dynamite",
                             "xenomorphs", "lots and lots of C4", "tactical nukes", "bio-weapons",
                             "rocket launchers", "an elephant", "a memory worm for afterwards", "this pencil"]

        method_of_attack = " an " + random.choice(method_of_attack_an) if random.choice([1,
                                                                                         2]) == 1 else " a " + random.choice(
            method_of_attack_a)

        greeting_choice = random.choice([1, 2])
        greeting = random.choice(suggestion_greeting) if greeting_choice == 1 else random.choice(command_greeting)
        exclamation = "?" if greeting_choice == 1 else "!"

        suggestion = greeting + method_of_attack + " " + random.choice(type_of_attack) + " with " + random.choice(
            attack_adjective) + " " + random.choice(attack_object) + " and " + random.choice(
            attack_object_two) + exclamation

        event["stdout"].write(suggestion)
