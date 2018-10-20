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

WALLET_DEFAULT = "default"

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
        server.set_setting("coins", self._coin_str(amount))
    def _take_from_pool(self, server, amount):
        coins = self._get_pool(server)
        self._set_pool(server, coins-amount)
    def _give_to_pool(self, server, amount):
        coins = self._get_pool(server)
        self._set_pool(server, coins+amount)

    def _get_user_wallets(self, user):
        return user.get_setting("wallets", {WALLET_DEFAULT: "0.0"})
    def _set_user_wallets(self, user, wallets):
        user.set_setting("wallets", wallets)
    def _reset_user_wallets(self, user):
        user.del_setting("wallets")
    def _user_has_wallet(self, user, wallet):
        return wallet.lower() in self._get_user_wallets(user)

    def _get_user_coins(self, user, wallet=WALLET_DEFAULT):
        wallets = self._get_user_wallets(user)
        return decimal.Decimal(wallets.get(wallet.lower(), "0.0"))
    def _get_all_user_coins(self, user):
        wallets = self._get_user_wallets(user)
        return sum(decimal.Decimal(amount) for amount in wallets.values())
    def _set_user_coins(self, user, coins, wallet=WALLET_DEFAULT):
        wallets = self._get_user_wallets(user)
        wallets[wallet.lower()] = self._coin_str(coins)
        self._set_user_wallets(user, wallets)
    def _add_user_wallet(self, user, wallet):
        wallets = self._get_user_wallets(user)
        wallets[wallet.lower()] = "0.0"
        self._set_user_wallets(user, wallets)
    def _remove_user_wallet(self, user, wallet):
        wallets = self._get_user_wallets(user)
        del wallets[wallet.lower()]
        self._set_user_wallets(user, wallets)

    def _all_coins(self, server):
        coins = server.get_all_user_settings("wallets", [])

        for i, (nickname, wallet) in enumerate(coins):
            user_coins = sum(decimal.Decimal(v) for v in wallet.values())
            coins[i] = (nickname, user_coins)

        return dict(filter(lambda coin: coin[1], coins))

    def _redeem_amount(self, server):
        return decimal.Decimal(server.get_setting("redeem-amount",
            DEFAULT_REDEEM_AMOUNT))
    def _redeem_delay(self, server):
        return server.get_setting("redeem-delay", DEFAULT_REDEEM_DELAY)

    def _give(self, server, user, amount, wallet=WALLET_DEFAULT):
        user_coins = self._get_user_coins(user, wallet)
        self._take_from_pool(server, amount)
        self._set_user_coins(user, user_coins+amount, wallet)
        return user_coins+amount
    def _take(self, server, user, amount, wallet=WALLET_DEFAULT):
        user_coins = self._get_user_coins(user, wallet)
        self._give_to_pool(server, amount)
        self._set_user_coins(user, user_coins-amount, wallet)
        return user_coins-amount
    def _move(self, user1, user2, amount, from_wallet=WALLET_DEFAULT,
            to_wallet=WALLET_DEFAULT):
        user1_coins = self._get_user_coins(user1, from_wallet)
        self._set_user_coins(user1, user1_coins-amount, from_wallet)

        user2_coins = self._get_user_coins(user2, to_wallet)
        self._set_user_coins(user2, user2_coins+amount, to_wallet)

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

    def _default_wallets(self, user):
        return WALLET_DEFAULT, WALLET_DEFAULT
    def _parse_wallets(self, user, s):
        if not s:
            return self._default_wallets()
        if not ":" in s:
            return s, s
        wallet_1, _, wallet_2 = s.partition(":")
        wallet_1 = wallet_1.lower() or WALLET_DEFAULT
        wallet_2 = wallet_2.lower() or WALLET_DEFAULT

        wallets = self._get_user_wallets(user)
        if not wallet_1 in wallets or not wallet_2 in wallets:
            raise utils.EventError("Unknown wallet")

        return wallet_1, wallet_2

    @utils.hook("received.command.bank")
    def bank(self, event):
        """
        :help: Show how many coins The Bank currently has
        """
        event["stdout"].write("The Bank has %s coins" %
            self._coin_str(self._get_pool(event["server"])))

    def _total_coins(self, server):
        all_coins = sum(self._all_coins(server).values())
        return self._get_pool(server)+all_coins

    @utils.hook("received.command.totalcoins")
    def total_coins(self, event):
        """
        :help: Show how many coins are currently in circulation
        """
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
        coins = self._get_all_user_coins(target)
        event["stdout"].write("%s has %s coin%s" % (target.nickname,
            self._coin_str(coins), "" if coins == 1 else "s"))

    @utils.hook("received.command.wallet")
    def wallet(self, event):
        """
        :help: Show your wallets and their balances
        :usage: [wallet]
        """
        if not event["args_split"]:
            wallets = self._get_user_wallets(event["user"]).keys()
            event["stdout"].write("%s: your available wallets are: %s" %
                (event["user"].nickname, ", ".join(wallets)))
        else:
            wallet = event["args"]
            if not self._user_has_wallet(event["user"], wallet):
                raise utils.EventError("%s: you don't have a '%s' wallet" %
                    (event["user"].nickname, wallet))
            coins = self._get_user_coins(event["user"], wallet)
            event["stdout"].write("%s: you have %s coins in your '%s' wallet" %
                (event["user"].nickname, self._coin_str(coins), wallet))

    @utils.hook("received.command.addwallet", authenticated=True, min_args=1)
    def add_wallet(self, event):
        wallet = event["args_split"][0]
        if self._user_has_wallet(event["user"], wallet):
            raise utils.EventError("%s: you already have a '%s' wallet" %
                (event["user"].nickname, wallet))
        self._add_user_wallet(event["user"], wallet)
        event["stdout"].write("%s: added a '%s' wallet" % (
            event["user"].nickname, wallet))
    @utils.hook("received.command.removewallet", authenticated=True, min_args=1)
    def remove_wallet(self, event):
        wallet = event["args_split"][0]
        if not self._user_has_wallet(event["user"], wallet):
            raise utils.EventError("%s: you don't have a '%s' wallet" %
                (event["user"].nickname, wallet))
        if wallet.lower() == WALLET_DEFAULT.lower():
            raise utils.EventError("%s: you cannot delete the default wallet" %
                event["user"].nickname)

        coins = self._get_user_coins(event["user"], wallet)
        self._give(event["server"], event["user"], coins, WALLET_DEFAULT)
        self._remove_user_wallet(event["user"], wallet)
        event["stdout"].write("%s: removed wallet '%s' and shifted any funds "
            "to your default wallet" % (event["user"].nickname, wallet))

    @utils.hook("received.command.resetcoins", min_args=1)
    def reset_coins(self, event):
        """
        :help: Reset a user's coins to 0
        :usage: <target>
        :permission: resetcoins
        """
        target = event["server"].get_user(event["args_split"][0])
        coins = self._get_all_user_coins(target)
        self._take(event["server"], target, coins)
        self._reset_user_wallets(target)
        event["stdout"].write("Reset coins for %s" % target.nickname)

    @utils.hook("received.command.givecoins", min_args=1)
    def give_coins(self, event):
        """
        :help: Give coins to a user
        :usage: <nickname> <coins>
        :permission: givecoins
        """
        _, wallet_out = self._default_wallets(event["user"])
        if len(event["args_split"]) > 2:
            _, wallet_out = self._parse_wallets(event["user"],
                event["args_split"][2])

        target = event["server"].get_user(event["args_split"][0])
        try:
            coins = self._parse_coins(event["args_split"][1], DECIMAL_ZERO)
        except CoinParseException as e:
            raise utils.EventError("%s: %s" % (event["user"].nickname, str(e)))

        self._give(event["server"], target, coins, wallet_out)
        event["stdout"].write("Gave '%s' %s coins" % (target.nickname,
            self._coin_str(coins)))

    @utils.hook("received.command.richest")
    def richest(self, event):
        """
        :help: Show the top 10 richest users
        """
        top_10 = utils.top_10(self._all_coins(event["server"]),
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
        user_coins = self._get_all_user_coins(event["user"])
        if user_coins == DECIMAL_ZERO:
            cache = self._redeem_cache(event["server"], event["user"])
            if not self.bot.cache.has_item(cache):
                _, wallet_out = self._default_wallets(event["user"])
                if len(event["args_split"]) > 0:
                    _, wallet_out = self._parse_wallets(event["user"],
                        event["args_split"][0])

                redeem_amount = self._redeem_amount(event["server"])
                self._give(event["server"], event["user"], redeem_amount,
                    wallet_out)

                event["stdout"].write("Redeemed %s coins" % self._coin_str(
                    redeem_amount))

                redeem_delay = self._redeem_delay(event["server"])
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
        wallet_in, wallet_out = self._default_wallets(event["user"])
        if len(event["args_split"]) > 2:
            wallet_in, wallet_out = self._parse_wallets(event["user"],
                event["args_split"][2])

        side_name = event["args_split"][0].lower()
        coin_bet = event["args_split"][1].lower()
        if coin_bet == "all":
            coin_bet = self._get_user_coins(event["user"], wallet_in)
            if coin_bet <= DECIMAL_ZERO:
                raise utils.EventError("%s: You have no coins to bet" %
                    event["user"].nickname)
        else:
            try:
                coin_bet = self._parse_coins(coin_bet, DECIMAL_ZERO)
            except CoinParseException as e:
                raise utils.EventError("%s: %s" % (event["user"].nickname,
                    str(e)))

        if not side_name in SIDES:
             raise utils.EventError("%s: Please provide 'heads' or 'tails'" %
                event["user"].nickname)

        user_coins = self._get_user_coins(event["user"], wallet_in)
        if coin_bet > user_coins:
            raise utils.EventError("%s: You don't have enough coins to bet" %
                event["user"].nickname)

        chosen_side = secrets.choice(list(SIDES.keys()))
        win = side_name == chosen_side

        coin_bet_str = self._coin_str(coin_bet)
        if win:
            new_total = self._give(event["server"], event["user"], coin_bet,
                wallet_out)
            event["stdout"].write(
                "%s flips %s and wins %s coin%s! (new total: %s)" % (
                    event["user"].nickname, side_name, coin_bet_str,
                    "" if coin_bet == 1 else "s", self._coin_str(new_total)
                )
            )
        else:
            self._take(event["server"], event["user"], coin_bet, wallet_in)
            event["stdout"].write(
                "%s flips %s and loses %s coin%s! (new total: %s)" % (
                    event["user"].nickname, side_name, coin_bet_str,
                    "" if coin_bet == 1 else "s",
                    self._coin_str(user_coins-coin_bet)
                )
            )

    @utils.hook("received.command.sendcoins", min_args=2, authenticated=True)
    def send(self, event):
        """
        :help: Send coins to another user
        :usage: <nickname> <amount>
        """
        target_user = event["server"].get_user(event["args_split"][0])

        wallet_in, _ = self._default_wallets(event["user"])
        _, wallet_out = self._default_wallets(target_user)
        if len(event["args_split"]) > 2:
            wallet_in, _ = self._parse_wallets(event["user"],
                event["args_split"][2])
            _, wallet_out = self._parse_wallets(target_user,
                event["args_split"][2])

        if event["user"].get_id() == target_user.get_id():
            raise utils.EventError("%s: You can't send coins to yourself" %
                event["user"].nickname)

        send_amount = event["args_split"][1]
        try:
            send_amount = self._parse_coins(send_amount, DECIMAL_ZERO)
        except CoinParseException as e:
            raise utils.EventError("%s: %s" % (event["user"].nickname, str(e)))

        user_coins = self._get_user_coins(event["user"], wallet_in)
        redeem_amount = self._redeem_amount(event["server"])
        new_total_coins = self._get_all_user_coins(event["user"])-send_amount

        if user_coins == DECIMAL_ZERO:
            raise utils.EventError("%s: You have no coins" %
                event["user"].nickname)
        elif new_total_coins < redeem_amount:
            raise utils.EventError(
                "%s: You cannot send an amount of money that puts"
                " you below %s coins" % (
                event["user"].nickname,
                self._coin_str(redeem_amount)))

        target_user_coins = self._get_user_coins(target_user, wallet_out)
        if target_user_coins == None:
            raise utils.EventError("%s: You can only send coins to users that "
                "have had coins before" % event["user"].nickname)

        self._move(event["user"], target_user, send_amount, wallet_in,
            wallet_out)

        event["stdout"].write("%s sent %s coins to %s" % (
            event["user"].nickname, self._coin_str(send_amount),
            target_user.nickname))

    @utils.hook("received.command.roulette", min_args=2, authenticated=True)
    def roulette(self, event):
        """
        :help: Spin a roulette wheel
        :usage: <type> <amount>
        """
        wallet_in, wallet_out = self._default_wallets(event["user"])
        if len(event["args_split"]) > 2:
            wallet_in, wallet_out = self._parse_wallets(event["user"],
                event["args_split"][2])

        bets = event["args_split"][0].lower().split(",")
        if "0" in bets:
            raise utils.EventError("%s: You can't bet on 0" %
                event["user"].nickname)
        bet_amounts = [amount.lower() for amount in event["args_split"][1:]]
        if len(bet_amounts) < len(bets):
            raise utils.EventError("%s: Please provide an amount for each bet" %
                event["user"].nickanme)
        if len(bet_amounts) == 1 and bet_amounts[0] == "all":
            bet_amounts[0] = self._get_user_coins(event["user"], wallet_in)
            if bet_amounts[0] <= DECIMAL_ZERO:
                raise utils.EventError("%s: You have no coins to bet" %
                    event["user"].nickname)
            bet_amounts[0] = self._coin_str(bet_amounts[0])

        for i, bet_amount in enumerate(bet_amounts):
            try:
                bet_amounts[i] = self._parse_coins(bet_amount, DECIMAL_ZERO)
            except CoinParseException as e:
                raise utils.EventError("%s: %s" % (event["user"].nickname,
                    str(e)))

        bet_amount_total = sum(bet_amounts)

        user_coins = self._get_user_coins(event["user"], wallet_in)
        if bet_amount_total > user_coins:
            raise utils.EventError("%s: You don't have enough coins to bet" %
                event["user"].nickname)

        payin = sum(bet_amounts)
        self._take(event["user"], payin, wallet_in)
        self._give_to_pool(event["server"], payin)
        # black, red, odds, evens, low (1-18), high (19-36)
        # 1dozen (1-12), 2dozen (13-24), 3dozen (25-36)
        # 1column (1,4..34), 2column (2,5..35), 3column (3,6..36)
        choice = secrets.randbelow(37)
        winnings = {}
        losses = {}
        if choice == 0:
            event["stdout"].write("Roulette spin lands on 0, "
                "the house wins, %s loses %s" % (
                event["user"].nickname, payin))
            return

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
                raise utils.EventError("%s: Unknown bet" %
                    event["user"].nickname)

            if odds == 0:
                losses[bet] = bet_amounts[i]
            else:
                winnings[bet] = [odds, bet_amounts[i]*odds]

        winnings_str = ["%s for %s (%d to 1)" % (winnings[bet][1], bet,
            winnings[bet][0]) for bet in winnings.keys()]

        coin_winnings = sum(bet[1] for bet in winnings.values())
        coin_losses = sum(loss for loss in losses.values())

        if coin_winnings:
            self._give(event["server"], event["user"], coin_winnings,
                wallet_out)

        total_winnings_str = " (%s total)" % coin_winnings if len(
            winnings.keys()) > 1 else ""

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
            all_coins = self._all_coins(server)

            interest_rate = decimal.Decimal(server.get_setting(
                "interest-rate", DEFAULT_INTEREST_RATE))
            redeem_amount = self._redeem_amount(server)

            for nickname, coins in all_coins.items():
                if coins > redeem_amount:
                    interest = round(coins*interest_rate, 2)
                    self._take_from_pool(server, interest)

                    wallets = server.get_user_setting(nickname, "wallets", {})
                    default_coins = wallets.get(WALLET_DEFAULT, "0.0")
                    default_coins = decimal.Decimal(default_coins)
                    wallets[WALLET_DEFAULT] = self._coin_str(
                        default_coins+interest)
                    server.set_user_setting(nickname, "wallets", wallets)
        event["timer"].redo()

    @utils.hook("received.command.lotterybuy", authenticated=True)
    def lottery_buy(self, event):
        """
        :help: By ticket(s) for the lottery
        :usage: [amount]
        """
        wallet_in, _ = self._default_wallets(event["user"])
        if len(event["args_split"]) > 0:
            wallet_in, _ = self._parse_wallets(event["user"],
                event["args_split"][0])

        amount = 1
        if event["args_split"]:
            amount = event["args_split"][0]
        if not amount.isdigit():
            raise utils.EventError("%s: Please provide a positive number "
                "of tickets to buy" % event["user"].nickname)
        amount = int(amount)

        user_coins = self._get_user_coins(event["user"], wallet_in)
        coin_amount = decimal.Decimal(LOTTERY_BUYIN)*amount
        if coin_amount > user_coins:
            raise utils.EventError("%s: You don't have enough coins" %
                event["user"].nickname)

        self._take(event["server"], event["user"], coin_amount, wallet_in)

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
        """
        :help: Show how many lottery tickets you currently have
        """
        lottery = event["server"].get_setting("lottery", {})
        count = lottery.get(event["user"].nickname_lower, 0)
        event["stdout"].write("%s: You have %d lottery ticket%s" % (
            event["user"].nickname, count, "" if count == 1 else "s"))

    @utils.hook("received.command.jackpot")
    def jackpot(self, event):
        """
        :help: Show the current lottery jackpot
        """
        lottery = event["server"].get_setting("lottery", {})
        count = sum(value for nickname, value in lottery.items())
        event["stdout"].write("%s: The current jackpot is %s" % (
            event["user"].nickname, decimal.Decimal(LOTTERY_BUYIN)*count))

    @utils.hook("received.command.nextlottery")
    def next_lottery(self, event):
        """
        :help: Show time until the next lottery draw
        """
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
            new_coins = coins+winnings

            self._give(server, user, winnings)
            server.set_setting("lottery-winner", user.nickname)
            user.send_notice("You won %s in the lottery! you now have %s coins"
                % (self._coin_str(winnings), self._coin_str(new_coins)))
