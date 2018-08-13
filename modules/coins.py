import datetime, decimal, math, random, re, time
import Utils

SIDES = {"heads": 0, "tails": 1}
DEFAULT_REDEEM_DELAY = 600 # 600 seconds, 10 minutes
DEFAULT_REDEEM_AMOUNT = "100.0"
DEFAULT_INTEREST_RATE = "0.01"
INTEREST_INTERVAL = 60*60 # 1 hour
DECIMAL_ZERO = decimal.Decimal("0")
REGEX_FLOAT = re.compile("\d+(?:\.\d{1,2}|$)")

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received.command.coins").hook(self.coins,
            help="Show how many coins you have")
        bot.events.on("received.command.richest").hook(
            self.richest, help="Show the top 10 richest users")
        bot.events.on("received.command.redeemcoins").hook(
            self.redeem_coins, help="Redeem free coins")
        bot.events.on("received.command.flip").hook(self.flip,
            help="Bet coins on a coin flip", usage=
            "heads|tails <coin amount>", min_args=2)
        bot.events.on("received.command.sendcoins").hook(
            self.send, min_args=2, help="Send coins to a user",
            usage="<nickname> <amount>")

        now = datetime.datetime.now()
        until_next_hour = 60-now.second
        until_next_hour += ((60-(now.minute+1))*60)

        bot.events.on("timer").on("coin-interest").hook(self.interest)
        bot.add_timer("coin-interest", INTEREST_INTERVAL, persist=False,
            next_due=time.time()+until_next_hour)

    def coins(self, event):
        if event["args_split"]:
            target = event["server"].get_user(event["args_split"][0])
        else:
            target = event["user"]
        coins = decimal.Decimal(target.get_setting("coins", "0.0"))
        event["stdout"].write("%s has %s coin%s" % (target.nickname,
            "{0:.2f}".format(coins), "" if coins == 1 else "s"))

    def richest(self, event):
        all_coins = event["server"].get_all_user_settings("coins", [])
        all_coins = list(filter(lambda coin: decimal.Decimal(coin[1]),
            all_coins))
        items = [(coin[0], decimal.Decimal(coin[1])) for coin in all_coins]
        all_coins = dict(items)

        top_10 = sorted(all_coins.keys())
        top_10 = sorted(top_10, key=all_coins.get, reverse=True)[:10]
        top_10 = ", ".join("%s (%s)" % (Utils.prevent_highlight(event[
            "server"].get_user(nickname).nickname), "{0:.2f}".format(
            all_coins[nickname])) for nickname in top_10)
        event["stdout"].write("Richest users: %s" % top_10)

    def redeem_coins(self, event):
        user_coins = decimal.Decimal(event["user"].get_setting(
            "coins", "0.0"))
        if user_coins == DECIMAL_ZERO:
            last_redeem = event["user"].get_setting("last-redeem", None)
            redeem_delay = event["server"].get_setting("redeem-delay",
                DEFAULT_REDEEM_DELAY)

            if last_redeem == None or (time.time()-last_redeem
                    ) >= redeem_delay:
                redeem_amount = decimal.Decimal(event["server"
                    ].get_setting("redeem-amount", DEFAULT_REDEEM_AMOUNT))
                event["user"].set_setting("coins", str(
                    user_coins+redeem_amount))
                event["stdout"].write("Redeemed %s coins" % "{0:.2f}".format(
                    redeem_amount))
                event["user"].set_setting("last-redeem", time.time())
            else:
                time_left = (last_redeem+redeem_delay)-time.time()
                event["stderr"].write("Please wait %s before redeeming" %
                    Utils.to_pretty_time(math.ceil(time_left)))
        else:
            event["stderr"].write(
                "You can only redeem coins when you have none")

    def flip(self, event):
        side_name = event["args_split"][0].lower()
        coin_bet = event["args_split"][1].lower()
        if coin_bet == "all":
            coin_bet = event["user"].get_setting("coins", "0.0")
            if decimal.Decimal(coin_bet) <= DECIMAL_ZERO:
                event["stderr"].write("You have no coins to bet")
                return

        match = REGEX_FLOAT.match(coin_bet)
        if not match or round(decimal.Decimal(coin_bet), 2) <= DECIMAL_ZERO:
            event["stderr"].write("Please provide a number of coins to bet")
            return
        coin_bet = decimal.Decimal(match.group(0))
        coin_bet_str = "{0:.2f}".format(coin_bet)
        if not side_name in SIDES:
            event["stderr"].write("Please provide 'heads' or 'tails'")
            return

        user_coins = decimal.Decimal(event["user"].get_setting(
            "coins", "0.0"))
        if coin_bet > user_coins:
            event["stderr"].write("You don't have enough coins to bet")
            return

        chosen_side = random.choice(list(SIDES.keys()))
        win = side_name == chosen_side

        if win:
            event["user"].set_setting("coins", str(user_coins+coin_bet))
            event["stdout"].write("%s flips %s and wins %s coin%s!" % (
                event["user"].nickname, side_name, coin_bet_str,
                "" if coin_bet == 1 else "s"))
        else:
            event["user"].set_setting("coins", str(user_coins-coin_bet))
            event["stdout"].write("%s flips %s and loses %s coin%s!" % (
                event["user"].nickname, side_name, coin_bet_str,
                "" if coin_bet == 1 else "s"))

    def send(self, event):
        send_amount = event["args_split"][1]
        match = REGEX_FLOAT.match(send_amount)
        if not match or round(decimal.Decimal(send_amount), 2
                ) <= DECIMAL_ZERO:
            event["stderr"].write(
                "Please provide a positive number of coins to send")
            return
        send_amount = decimal.Decimal(match.group(0))

        user_coins = decimal.Decimal(event["user"].get_setting("coins",
            "0.0"))
        redeem_amount = decimal.Decimal(event["server"].get_setting(
            "redeem-amount", DEFAULT_REDEEM_AMOUNT))
        new_user_coins = user_coins-send_amount

        if new_user_coins == DECIMAL_ZERO:
            event["stderr"].write("You have no coins")
            return
        elif new_user_coins < redeem_amount:
            event["stderr"].write(
                "You cannot send an amount of money that puts"
                " you below %s coins" % "{0:.2f}".format(redeem_amount))
            return
        target_user = event["server"].get_user(event["args_split"][0])
        target_user_coins = decimal.Decimal(target_user.get_setting(
            "coins", "0.0"))
        event["user"].set_setting("coins", str(new_user_coins))
        target_user.set_setting("coins", str(target_user_coins+send_amount))

        event["stdout"].write("%s sent %s coins to %s" % (
            event["user"].nickname, "{0:.2f}".format(send_amount),
            target_user.nickname))

    def interest(self, event):
        for server in self.bot.servers.values():
            all_coins = server.get_all_user_settings(
                "coins", [])
            interest_rate = decimal.Decimal(server.get_setting(
                "interest-rate", DEFAULT_INTEREST_RATE))
            redeem_amount = decimal.Decimal(server.get_setting(
                "redeem-amount", DEFAULT_REDEEM_AMOUNT))
            for nickname, coins in all_coins:
                coins = decimal.Decimal(coins)
                if coins > redeem_amount:
                    coins += round(coins*interest_rate, 2)
                    server.get_user(nickname).set_setting("coins",
                        str(coins))
        event["timer"].redo()
