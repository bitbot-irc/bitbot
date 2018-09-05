import datetime, decimal, math, random, re, time
import Utils

SIDES = {"heads": 0, "tails": 1}
DEFAULT_REDEEM_DELAY = 600 # 600 seconds, 10 minutes
DEFAULT_REDEEM_AMOUNT = "100.0"
DEFAULT_INTEREST_RATE = "0.01"
INTEREST_INTERVAL = 60*60 # 1 hour
DECIMAL_ZERO = decimal.Decimal("0")
REGEX_FLOAT = re.compile("\d+(?:\.\d{1,2}|$)")

RED = [1, 3, 5, 7, 9, 12, 14, 16, 18, 19, 21, 23, 25, 27, 30, 32, 34, 36]
BLACK = [2, 4, 6, 8, 10, 11, 13, 15, 17, 20, 22, 24, 26, 28, 29, 31, 33, 35]

SMALL = range(1, 19)
BIG = range(19, 37)

FIRST_DOZEN = list(range(1, 13))
SECOND_DOZEN = list(range(13, 25))
THIRD_DOZEN = list(range(25, 37))

FIRST_COLUMN = list(range(1, 37))[0::3]
SECOND_COLUMN = list(range(1, 37))[1::3]
THIRD_COLUMN = list(range(1, 37))[2::3]

REGEX_STREET = re.compile("street([1-9]|1[0-2])$")

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received.command.coins").hook(self.coins,
            help="Show how many coins you have")
        events.on("received").on("command").on("resetcoins").hook(
            self.reset_coins, permission="resetcoins",
            min_args=1, help=
            "Reset a specified user's coins to %s" % str(DECIMAL_ZERO),
            usage="<target>")
        events.on("received.command.richest").hook(
            self.richest, help="Show the top 10 richest users")
        events.on("received.command.redeemcoins").hook(
            self.redeem_coins, help="Redeem free coins")
        events.on("received.command.flip").hook(self.flip,
            help="Bet coins on a coin flip", usage=
            "heads|tails <coin amount>", min_args=2, protect_registered=True)
        events.on("received.command.sendcoins").hook(
            self.send, min_args=2, help="Send coins to a user",
            usage="<nickname> <amount>", authenticated=True)
        events.on("received.command.roulette").hook(
            self.roulette, min_args=2, help="Spin the roulette wheel",
            usage="<type> <amount>", protect_registered=True)

        now = datetime.datetime.now()
        until_next_hour = 60-now.second
        until_next_hour += ((60-(now.minute+1))*60)

        events.on("timer").on("coin-interest").hook(self.interest)
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

    def reset_coins(self, event):
        target = event["server"].get_user(event["args_split"][0])
        coins = decimal.Decimal(target.get_setting("coins", "0.0"))
        if coins == DECIMAL_ZERO:
            event["stderr"].write("%s already has %s coins" % (
                target.nickname, str(DECIMAL_ZERO)))
        else:
            target.del_setting("coins")
            event["stdout"].write("Reset coins for %s" % target.nickname)


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
        if event["user"].get_id() == event["args_split"][0].get_id():
            event["stderr"].write("You can't send coins to yourself")
            return
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
        target_user_coins = target_user.get_setting("coins", None)
        if target_user_coins == None:
            event["stderr"].write("You can only send coins to users that "
                "have had coins before")
            return
        target_user_coins = decimal.Decimal(target_user_coins)

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

    def roulette(self, event):
        bets = event["args_split"][0].lower().split(",")
        if "0" in bets:
            event["stderr"].write("You can't bet on 0")
            return
        bet_amounts = [amount.lower() for amount in event["args_split"][1:]]
        if len(bet_amounts) < len(bets):
            event["stderr"].write("Please provide an amount for each bet")
            return
        if len(bet_amounts) == 1 and bet_amounts[0] == "all":
            bet_amounts[0] = event["user"].get_setting("coins", "0.0")
            if decimal.Decimal(bet_amounts[0]) <= DECIMAL_ZERO:
                event["stderr"].write("You have no coins to bet")
                return

        for i, bet_amount in enumerate(bet_amounts):
            match = REGEX_FLOAT.match(bet_amount)
            if not match or round(decimal.Decimal(bet_amount), 2
                    ) <= DECIMAL_ZERO:
                event["stderr"].write(
                    "Please provide a positive number of coins to bet")
                return
            bet_amounts[i] = decimal.Decimal(match.group(0))
        bet_amount_total = sum(bet_amounts)

        user_coins = decimal.Decimal(event["user"].get_setting("coins",
            "0.0"))
        if bet_amount_total > user_coins:
            event["stderr"].write("You don't have enough coins to bet")
            return

        # black, red, odds, evens, high (1-18), low (19-36)
        # 1dozen (1-12), 2dozen (13-24), 3dozen (25-36)
        # 1column (1,4..34), 2column (2,5..35), 3column (3,6..36)
        choice = random.randint(0, 36)
        winnings = {}
        losses = {}
        if choice == 0:
            loss = sum(bet_amounts)
            event["user"].set_setting("coins", str(user_coins-loss))
            event["stdout"].write("Roulette spin lands on 0, "
                "the house wins, %s loses %s" % (
                event["user"].nickname, loss))
            return

        failed = False
        colour = "red" if choice in RED else "black"
        for i, bet in enumerate(bets):
            street_match = REGEX_STREET.match(bet)
            odds = 0
            if bet == "even":
                odds = 1*((choice % 2) == 0)
            elif bet == "odd":
                odds = 1*((choice % 2) == 1)
            elif bet == "red":
                odds = 1*(choice in RED)
            elif bet == "black":
                odds = 1*(choice in BLACK)
            elif bet == "small" or bet == "low":
                odds = 1*(choice in SMALL)
            elif bet == "big" or bet == "high":
                odds = 1*(choice in BIG)
            elif bet == "dozen1":
                odds = 2*(choice in FIRST_DOZEN)
            elif bet == "dozen2":
                odds = 2*(choice in SECOND_DOZEN)
            elif bet == "dozen3":
                odds = 2*(choice in THIRD_DOZEN)
            elif bet == "column1":
                odds = 2*(choice in FIRST_COLUMN)
            elif bet == "column2":
                odds = 2*(choice in SECOND_COLUMN)
            elif bet == "column3":
                odds = 2*(choice in THIRD_COLUMN)
            elif street_match:
                row = int(street_match.group(1))
                odds = 11*(((row*3)-2) <= choice <= (row*3))
            elif bet.isdigit() and (1 <= int(bet) <= 36):
                odds = 35*(choice == int(bet))
            else:
                event["stderr"].write("Unknown bet")
                failed = True
                break
            if odds == 0:
                losses[bet] = bet_amounts[i]
            else:
                winnings[bet] = [odds, bet_amounts[i]*odds]
        if failed:
            return

        winnings_str = ["%s for %s (%d to 1)" % (winnings[bet][1], bet,
            winnings[bet][0]) for bet in winnings.keys()]

        coin_winnings = sum(bet[1] for bet in winnings.values())
        coin_losses = sum([loss for loss in losses.values()])
        total_winnings_str = " (%s total)" % coin_winnings if len(
            winnings.keys()) > 1 else ""

        new_user_coins = (user_coins-coin_losses)+coin_winnings
        event["user"].set_setting("coins", str(new_user_coins))

        choice = "%d %s" % (choice, colour)
        if not losses and winnings:
            event["stdout"].write("Roulette spin lands on %s, "
                "%s wins %s%s" % (choice, event["user"].nickname,
                ", ".join(winnings_str), str(total_winnings_str)))
        elif losses and winnings:
            event["stdout"].write("Roulette spin lands on %s, "
                "%s wins %s%s; loses %s" % (choice,
                event["user"].nickname, ", ".join(winnings_str),
                str(total_winnings_str), str(coin_losses)))
        else:
            event["stdout"].write("Roulette spin lands on %s, "
                "%s loses %s" % (choice, event["user"].nickname,
                str(coin_losses)))
