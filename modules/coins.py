import random, time
import Utils

SIDES = {"heads": 0, "tails": 1}
DEFAULT_REDEEM_DELAY = 600 # 600 seconds, 10 minutes
DEFAULT_REDEEM_AMOUNT = 100

class Module(object):
    def __init__(self, bot):
        bot.events.on("received.command.coins").hook(self.coins,
            help="Show how many coins you have")
        bot.events.on("received.command.redeemcoins").hook(
            self.redeem_coins, help="Redeem free coins")
        bot.events.on("received.command.flip").hook(self.flip,
            help="Bet coins on a coin flip", usage=
            "heads|tails <coin amount>", min_args=2)

    def coins(self, event):
        coins = event["user"].get_setting("coins", 0)
        event["stdout"].write("%s has %d coin%s" % (
            event["user"].nickname, coins,
            "" if coins == 1 else "s"))

    def redeem_coins(self, event):
        user_coins = event["user"].get_setting("coins", 0)
        if user_coins == 0:
            last_redeem = event["user"].get_setting("last-redeem", None)
            redeem_delay = event["server"].get_setting("redeem-delay",
                DEFAULT_REDEEM_DELAY)

            if last_redeem == None or (time.time()-last_redeem
                    ) >= redeem_delay:
                user_coins = event["user"].get_setting("coins", 0)
                redeem_amount = event["server"].get_setting(
                    "redeem-amount", DEFAULT_REDEEM_AMOUNT)
                event["user"].set_setting("coins", user_coins+redeem_amount)
                event["stdout"].write("Redeemed %d coins" % redeem_amount)
                event["user"].set_setting("last-redeem", time.time())
            else:
                time_left = (last_redeem+redeem_delay)-time.time()
                event["stdout"].write("Please wait %s before redeeming" %
                    Utils.to_pretty_time(time_left))
        else:
            event["stderr"].write(
                "You can only redeem coins when you have none")

    def flip(self, event):
        side_name = event["args_split"][0].lower()
        coin_bet = event["args_split"][1]

        if not coin_bet.isdigit():
            event["stderr"].write("Please provide a number of coins to bet")
            return
        coin_bet = int(coin_bet)
        if not side_name in SIDES:
            event["stderr"].write("Please provide 'heads' or 'tails'")
            return

        user_coins = event["user"].get_setting("coins", 0)
        if coin_bet > user_coins:
            event["stderr"].write("You don't have enough coins to bet")
            return

        chosen_side = random.choice(list(SIDES.keys()))
        win = side_name == chosen_side

        if win:
            event["user"].set_setting("coins", user_coins+coin_bet)
            event["stdout"].write("%s flips %s and wins %d!" % (
                event["user"].nickname, side_name, coin_bet))
        else:
            event["user"].set_setting("coins", user_coins-coin_bet)
            event["stdout"].write("%s flipped %s and loses %d!" % (
                event["user"].nickname, side_name, coin_bet))
