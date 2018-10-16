import datetime, decimal, functools, math, random, re, secrets, time
from src import ModuleManager, utils

SIDES = {"heads": 0, "tails": 1}
DEFAULT_REDEEM_DELAY = 600 # 600 seconds, 10 minutes
DEFAULT_REDEEM_AMOUNT = "100.0"
DEFAULT_INTEREST_RATE = "0.01"
INTEREST_INTERVAL = 60*60 # 1 hour
DECIMAL_ZERO = decimal.Decimal("0")
REGEX_FLOAT = re.compile("(?:\d+(?:\.\d{1,2}|$)|\.\d{1,2})")
DEFAULT_MARKET_CAP = str(1_000_000_000)

HOUR_SECONDS = (1*60)*60
LOTTERY_INTERVAL = (60*60)*6 # 6 hours
LOTTERY_BUYIN = "100.00"

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

class CoinParseException(Exception):
    pass

class Module(ModuleManager.BaseModule):
    def on_load(self):
        self.timers.add("coin-interest", INTEREST_INTERVAL,
            time.time()+self._until_next_hour())
        self.timers.add("coin-lottery", LOTTERY_INTERVAL,
            time.time()+self._until_next_6_hour())

    def _until_next_hour(self, now=None):
        now = now or datetime.datetime.utcnow()
        until_next_hour = 60-now.second
        return until_next_hour+((60-(now.minute+1))*60)
    def _until_next_6_hour(self):
        now = datetime.datetime.utcnow()
        until_next_hour = self._until_next_hour(now)
        until_next_6_hour = (6-(now.hour%6))-1
        until_next_6_hour = until_next_6_hour*HOUR_SECONDS
        return until_next_hour+until_next_6_hour

    def _get_pool(self, server):
        return decimal.Decimal(server.get_setting("coins", DEFAULT_MARKET_CAP))
    def _set_pool(self, server, amount):
        server.set_setting("coins", str(amount))
    def _take_from_pool(self, server, amount):
        coins = self._get_pool(server)
        self._set_pool(server, coins-amount)
    def _give_to_pool(self, server, amount):
        coins = self._get_pool(server)
        self._set_pool(server, coins+amount)

    def _get_user_coins(self, user):
        return decimal.Decimal(user.get_setting("coins", "0.0"))
    def _set_user_coins(self, user, coins):
        user.set_setting("coins", self._coin_str(coins))
    def _reset_user_coins(self, user):
        user.del_setting("coins")

    def _coin_str(self, coins):
        return "{0:.2f}".format(coins)
    def _parse_coins(self, s, minimum=None):
        try:
            s = utils.parse_number(s)
        except ValueError:
            pass

        match = REGEX_FLOAT.match(s)
        if match:
            coins = decimal.Decimal(match.group(0))
            if minimum == None or coins >= minimum:
                return coins
            else:
                raise CoinParseException(
                    "Coin amount provided is lower than %s" % minimum)
        else:
            raise CoinParseException(
                "Please provide a valid positive coin amount")

    @utils.hook("received.command.bank")
    def bank(self, event):
        event["stdout"].write("The Bank has %s coins" %
            self._coin_str(self._get_pool(event["server"])))

    def _total_coins(self, server):
        all_coins = server.get_all_user_settings("coins", [])
        all_coins = list(filter(lambda coin: decimal.Decimal(coin[1]),
            all_coins))
        all_coins = [decimal.Decimal(coin[1]) for coin in all_coins]
        all_coins = sum(all_coins)
        return self._get_pool(server)+all_coins

    @utils.hook("received.command.totalcoins")
    def total_coins(self, event):
        event["stdout"].write("Total coins: %s" % self._coin_str(
            self._total_coins(event["server"])))

    @utils.hook("received.command.coins")
    def coins(self, event):
        """
        :help: Show how many coins you have
        """
        if event["args_split"]:
            target = event["server"].get_user(event["args_split"][0])
        else:
            target = event["user"]
        coins = self._get_user_coins(target)
        event["stdout"].write("%s has %s coin%s" % (target.nickname,
            self._coin_str(coins), "" if coins == 1 else "s"))

    @utils.hook("received.command.resetcoins", min_args=1)
    def reset_coins(self, event):
        """
        :help: Reset a user's coins to 0
        :usage: <target>
        :permission: resetcoins
        """
        target = event["server"].get_user(event["args_split"][0])
        coins = self._get_user_coins(target)
        if coins == DECIMAL_ZERO:
            event["stderr"].write("%s already has %s coins" % (
                target.nickname, str(DECIMAL_ZERO)))
        else:
            self._give_to_pool(event["server"], coins)
            self._reset_user_coins(target)
            event["stdout"].write("Reset coins for %s" % target.nickname)

    @utils.hook("received.command.givecoins", min_args=1)
    def give_coins(self, event):
        """
        :help: Give coins to a user
        :usage: <nickname> <coins>
        :permission: givecoins
        """
        target = event["server"].get_user(event["args_split"][0])
        try:
            coins = self._parse_coins(event["args_split"][0], DECIMAL_ZERO)
        except CoinParseException as e:
            event["stderr"].write("%s: %s" % (event["user"].nickname, str(e)))
            return

        target_coins = self._get_user_coins(target)
        self._take_from_pool(event["server"], coins)
        self._set_user_coins(target, target_coins+coins)

        event["stdout"].write("Gave '%s' %s coins" % (target.nickname,
            str(coins)))

    @utils.hook("received.command.richest")
    def richest(self, event):
        """
        :help: Show the top 10 richest users
        """
        all_coins = event["server"].get_all_user_settings("coins", [])
        all_coins = list(filter(lambda coin: decimal.Decimal(coin[1]),
            all_coins))
        items = [(coin[0], decimal.Decimal(coin[1])) for coin in all_coins]
        all_coins = dict(items)

        top_10 = utils.top_10(all_coins,
            convert_key=lambda nickname: utils.prevent_highlight(
                event["server"].get_user(nickname).nickname),
            value_format=lambda value: self._coin_str(value))
        event["stdout"].write("Richest users: %s" % ", ".join(top_10))

    def _redeem_cache(self, server, user):
        return "redeem|%s|%s@%s" % (server.id, user.username, user.hostname)

    @utils.hook("received.command.redeemcoins")
    def redeem_coins(self, event):
        """
        :help: Redeem your free coins
        """
        user_coins = self._get_user_coins(event["user"])
        if user_coins == DECIMAL_ZERO:
            cache = self._redeem_cache(event["server"], event["user"])
            if not self.bot.cache.has_item(cache):
                redeem_amount = decimal.Decimal(event["server"
                    ].get_setting("redeem-amount", DEFAULT_REDEEM_AMOUNT))
                self._set_user_coins(event["user"], user_coins+redeem_amount)
                self._take_from_pool(event["server"], redeem_amount)

                event["stdout"].write("Redeemed %s coins" % self._coin_str(
                    redeem_amount))

                redeem_delay = event["server"].get_setting("redeem-delay",
                    DEFAULT_REDEEM_DELAY)
                self.bot.cache.temporary_cache(cache, redeem_delay)
            else:
                time_left = self.bot.cache.until_expiration(cache)
                event["stderr"].write("%s: Please wait %s before redeeming" % (
                    event["user"].nickname,
                    utils.to_pretty_time(math.ceil(time_left))))
        else:
            event["stderr"].write(
                "%s: You can only redeem coins when you have none" %
                event["user"].nickname)

    @utils.hook("received.command.flip", min_args=2, authenticated=True)
    def flip(self, event):
        """
        :help: Bet on a coin flip
        :usage: heads|tails <coin amount>
        """
        side_name = event["args_split"][0].lower()
        coin_bet = event["args_split"][1].lower()
        if coin_bet == "all":
            coin_bet = self._get_user_coins(event["user"])
            if coin_bet <= DECIMAL_ZERO:
                event["stderr"].write("%s: You have no coins to bet" %
                    event["user"].nickname)
                return
        else:
            try:
                coin_bet = self._parse_coins(coin_bet, DECIMAL_ZERO)
            except CoinParseException as e:
                event["stderr"].write("%s: %s" % (event["user"].nickname,
                    str(e)))
                return

        if not side_name in SIDES:
            event["stderr"].write("%s: Please provide 'heads' or 'tails'" %
                event["user"].nickname)
            return

        user_coins = self._get_user_coins(event["user"])
        if coin_bet > user_coins:
            event["stderr"].write("%s: You don't have enough coins to bet" %
                event["user"].nickname)
            return

        chosen_side = secrets.choice(list(SIDES.keys()))
        win = side_name == chosen_side

        coin_bet_str = self._coin_str(coin_bet)
        if win:
            new_coins = user_coins+coin_bet
            self._take_from_pool(event["server"], coin_bet)
            self._set_user_coins(event["user"], new_coins)

            event["stdout"].write(
                "%s flips %s and wins %s coin%s! (new total: %s)" % (
                    event["user"].nickname, side_name, coin_bet_str,
                    "" if coin_bet == 1 else "s", self._coin_str(new_coins)
                )
            )
        else:
            new_coins = user_coins-coin_bet
            self._give_to_pool(event["server"], coin_bet)
            self._set_user_coins(event["user"], new_coins)

            event["stdout"].write(
                "%s flips %s and loses %s coin%s! (new total: %s)" % (
                    event["user"].nickname, side_name, coin_bet_str,
                    "" if coin_bet == 1 else "s", self._coin_str(new_coins)
                )
            )

    @utils.hook("received.command.sendcoins", min_args=2, authenticated=True)
    def send(self, event):
        """
        :help: Send coins to another user
        :usage: <nickname> <amount>
        """
        if event["user"].get_id() == event["server"].get_user(event[
                "args_split"][0]).get_id():
            event["stderr"].write("%s: You can't send coins to yourself" %
                event["user"].nickname)
            return

        send_amount = event["args_split"][1]
        try:
            send_amount = self._parse_coins(send_amount, DECIMAL_ZERO)
        except CoinParseException as e:
            event["stderr"].write("%s: %s" % (event["user"].nickname, str(e)))
            return

        user_coins = self._get_user_coins(event["user"])
        redeem_amount = decimal.Decimal(event["server"].get_setting(
            "redeem-amount", DEFAULT_REDEEM_AMOUNT))
        new_user_coins = user_coins-send_amount

        if user_coins == DECIMAL_ZERO:
            event["stderr"].write("%s: You have no coins" %
                event["user"].nickname)
            return
        elif new_user_coins < redeem_amount:
            event["stderr"].write(
                "%s: You cannot send an amount of money that puts"
                " you below %s coins" % (
                event["user"].nickname,
                self._coin_str(redeem_amount)))
            return

        target_user = event["server"].get_user(event["args_split"][0])
        target_user_coins = self._get_user_coins(target)
        if target_user_coins == None:
            event["stderr"].write("%s: You can only send coins to users that "
                "have had coins before" % event["user"].nickname)
            return

        self._set_user_coins(event["user"], new_user_coins)
        # get target_user_coins again, just in case *somehow* someone's
        # sending coins to themselves.
        target_user_coins = self._get_user_coins(target_user)
        self._set_user_coins(target_user, target_user_coins+send_amount)

        event["stdout"].write("%s sent %s coins to %s" % (
            event["user"].nickname, self._coin_str(send_amount),
            target_user.nickname))

    @utils.hook("received.command.roulette", min_args=2, authenticated=True)
    def roulette(self, event):
        """
        :help: Spin a roulette wheel
        :usage: <type> <amount>
        """
        bets = event["args_split"][0].lower().split(",")
        if "0" in bets:
            event["stderr"].write("%s: You can't bet on 0" %
                event["user"].nickname)
            return
        bet_amounts = [amount.lower() for amount in event["args_split"][1:]]
        if len(bet_amounts) < len(bets):
            event["stderr"].write("%s: Please provide an amount for each bet" %
                event["user"].nickanme)
            return
        if len(bet_amounts) == 1 and bet_amounts[0] == "all":
            bet_amounts[0] = self._get_user_coins(event["user"])
            if bet_amounts[0] <= DECIMAL_ZERO:
                event["stderr"].write("%s: You have no coins to bet" %
                    event["user"].nickname)
                return
            bet_amounts[0] = self._coin_str(bet_amounts[0])

        for i, bet_amount in enumerate(bet_amounts):
            try:
                bet_amount = utils._parse_coins(bet_amount, DECIMAL_ZERO)
            except CoinParseException as e:
                event["stderr"].write("%s: %s" % (event["user"].nickname,
                    str(e)))
                return

        bet_amount_total = sum(bet_amounts)

        user_coins = self._get_user_coins(event["user"])
        if bet_amount_total > user_coins:
            event["stderr"].write("%s: You don't have enough coins to bet" %
                event["user"].nickname)
            return

        # black, red, odds, evens, low (1-18), high (19-36)
        # 1dozen (1-12), 2dozen (13-24), 3dozen (25-36)
        # 1column (1,4..34), 2column (2,5..35), 3column (3,6..36)
        choice = secrets.randbelow(37)
        winnings = {}
        losses = {}
        if choice == 0:
            loss = sum(bet_amounts)
            self._give_to_pool(event["server"], loss)
            self._set_user_coins(event["user"], user_coins-loss)
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
                event["stderr"].write("%s: Unknown bet" %
                    event["user"].nickname)
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

        if coin_winnings:
            self._take_from_pool(event["server"], coin_winnings)
        if coin_losses:
            self._give_to_pool(event["server"], coin_losses)

        total_winnings_str = " (%s total)" % coin_winnings if len(
            winnings.keys()) > 1 else ""

        new_user_coins = (user_coins-coin_losses)+coin_winnings
        self._set_user_coins(event["user"], new_user_coins)

        choice = "%d %s" % (choice, colour)
        if not losses and winnings:
            event["stdout"].write("Roulette spin lands on %s, "
                "%s wins %s%s" % (choice, event["user"].nickname,
                ", ".join(winnings_str), total_winnings_str))
        elif losses and winnings:
            event["stdout"].write("Roulette spin lands on %s, "
                "%s wins %s%s; loses %s" % (choice,
                event["user"].nickname, ", ".join(winnings_str),
                str(total_winnings_str), str(coin_losses)))
        else:
            event["stdout"].write("Roulette spin lands on %s, "
                "%s loses %s" % (choice, event["user"].nickname,
                str(coin_losses)))

    @utils.hook("timer.coin-interest")
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
                    interest = round(coins*interest_rate, 2)
                    self._take_from_pool(server, interest)
                    server.set_user_setting(nickname, "coins",
                        self._coin_str(coins+interest))
        event["timer"].redo()

    @utils.hook("received.command.lotterybuy", authenticated=True)
    def lottery_buy(self, event):
        """
        :help: By ticket(s) for the lottery
        :usage: [amount]
        """
        amount = 1
        if event["args_split"]:
            amount = event["args_split"][0]
        if not amount.isdigit():
            event["stderr"].write("%s: Please provide a positive number "
                "of tickets to buy" % event["user"].nickname)
            return
        amount = int(amount)

        user_coins = self._get_user_coins(event["user"])
        coin_amount = decimal.Decimal(LOTTERY_BUYIN)*amount
        if coin_amount > user_coins:
            event["stderr"].write("%s: You don't have enough coins" %
                event["user"].nickname)
            return

        self._give_to_pool(event["server"], coin_amount)
        self._set_user_coins(event["user"], user_coins-coin_amount)

        lottery = event["server"].get_setting("lottery", {})
        nickname = event["user"].nickname_lower
        if not nickname in lottery:
            lottery[nickname] = 0
        lottery[nickname] += amount
        event["server"].set_setting("lottery", lottery)

        event["stdout"].write("%s: You bought %d lottery ticket%s for %s" % (
            event["user"].nickname, amount, "" if amount == 1 else "s",
            self._coin_str(coin_amount)))

    @utils.hook("received.command.mylottery")
    def my_lottery(self, event):
        lottery = event["server"].get_setting("lottery", {})
        count = lottery.get(event["user"].nickname_lower, 0)
        event["stdout"].write("%s: You have %d lottery ticket%s" % (
            event["user"].nickname, count, "" if count == 1 else "s"))

    @utils.hook("received.command.jackpot")
    def jackpot(self, event):
        lottery = event["server"].get_setting("lottery", {})
        count = sum([value for nickname, value in lottery.items()])
        event["stdout"].write("%s: The current jackpot is %s" % (
            event["user"].nickname, decimal.Decimal(LOTTERY_BUYIN)*count))

    @utils.hook("received.command.nextlottery")
    def next_lottery(self, event):
        until = self._until_next_6_hour()
        event["stdout"].write("Next lottery is in: %s" %
            utils.to_pretty_time(until))

    @utils.hook("received.command.lotterywinner")
    def lottery_winner(self, event):
        """
        :help: Show who last won the lottery
        """
        winner = event["server"].get_setting("lottery-winner", None)
        if winner:
            event["stdout"].write("Last lottery winner: %s" % winner)
        else:
            event["stderr"].write("There have been no lottery winners!")

    @utils.hook("timer.coin-lottery")
    def lottery(self, event):
        for server in self.bot.servers.values():
            lottery = server.get_setting("lottery", {})
            if lottery:
                server.del_setting("lottery")
            else:
                continue

            users = [(nickname,)*value for nickname, value in lottery.items()]
            users = functools.reduce(lambda x, y: x+y, users)
            winner = random.choice(users)

            user = server.get_user(winner)
            coins = self._get_user_coins(user)
            winnings = decimal.Decimal(LOTTERY_BUYIN)*len(users)

            self._take_from_pool(server, winnings)
            new_coins = coins+winnings
            self._set_user_coins(user, new_coins)
            server.set_setting("lottery-winner", user.nickname)
            user.send_notice("You won %s in the lottery! you now have %s coins"
                % (self._coin_str(winnings), self._coin_str(new_coins)))
