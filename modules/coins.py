#--depends-on commands
#--depends-on permissions

import datetime, decimal, functools, math, random, re, time
from src import ModuleManager, utils

SIDES = {"heads": 0, "tails": 1}
DEFAULT_REDEEM_DELAY = 600 # 600 seconds, 10 minutes
DEFAULT_REDEEM_AMOUNT = "100.0"
DEFAULT_INTEREST_RATE = "0.01"
REGEX_FLOAT = re.compile("(?:\d+(?:\.\d{1,2}|$)|\.\d{1,2})")

DECIMAL_ZERO = decimal.Decimal("0")
DECIMAL_BET_MINIMUM = decimal.Decimal("0.01")

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
REGEX_DOUBLESTREET = re.compile("2street([1-9]|1[0-1])$")
REGEX_CORNER = re.compile("([lr])corner([1-9]|1[0-1])$")

class CoinParseException(Exception):
    pass

class Module(ModuleManager.BaseModule):
    def on_load(self):
        self.exports.add("command-spec.coins", self._coins_spec)
        self.exports.add("command-spec.coinsmany", self._coins_many_spec)

    def _coin_spec_parse(self, word):
        try:
            out = decimal.Decimal(word)
        except decimal.InvalidOperation:
            raise utils.parse.SpecTypeError(
                "Please provide a valid coin amount")
        if out >= DECIMAL_ZERO:
            return out
        else:
            raise utils.parse.SpecTypeError(
                "Please provide a positive coin amount")
    def _coins_spec(self, server, channel, user, args):
        if args:
            return self._coin_spec_parse(args[0]), 1
        else:
            raise utils.parse.SpecTypeError("No coin amount provided")
    def _coins_many_spec(self, server, channel, user, args):
        out = []
        for arg in args:
            out.append(self._coin_spec_parse(arg))
        return (out or None), 1

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

    def _get_user_coins(self, user):
        return decimal.Decimal(user.get_setting("coins", "0.0"))
    def _set_user_coins(self, user, coins):
        user.set_setting("coins", self._coin_str(coins))

    def _all_coins(self, server):
        all_coins = server.get_all_user_settings("coins", [])

        for i, (nickname, coins) in enumerate(all_coins):
            all_coins[i] = (nickname, decimal.Decimal(coins))

        return dict(filter(lambda coin: coin[1], all_coins))

    def _redeem_amount(self, server):
        return decimal.Decimal(server.get_setting("redeem-amount",
            DEFAULT_REDEEM_AMOUNT))
    def _redeem_delay(self, server):
        return server.get_setting("redeem-delay", DEFAULT_REDEEM_DELAY)

    def _give(self, server, user, amount):
        user_coins = self._get_user_coins(user)
        self._set_user_coins(user, user_coins+amount)
        return user_coins+amount
    def _take(self, server, user, amount):
        user_coins = self._get_user_coins(user)
        self._set_user_coins(user, user_coins-amount)
        return user_coins-amount
    def _move(self, user1, user2, amount):
        user1_coins = self._get_user_coins(user1)
        self._set_user_coins(user1, user1_coins-amount)

        user2_coins = self._get_user_coins(user2)
        self._set_user_coins(user2, user2_coins+amount)

    def _coin_str(self, coins):
        return "{0:.2f}".format(coins)
    def _coin_str_human(self, coins):
        return "{0:,.2f}".format(coins)
    def _parse_coins(self, s, minimum=None):
        try:
            s = utils.parse.parse_number(s)
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

    @utils.hook("received.command.coins")
    @utils.kwarg("help", "Show how many coins you have")
    def coins(self, event):
        if event["args_split"]:
            target = event["server"].get_user(event["args_split"][0])
        else:
            target = event["user"]
        coins = self._get_user_coins(target)
        event["stdout"].write("%s has %s coin%s" % (target.nickname,
            self._coin_str_human(coins), "" if coins == 1 else "s"))

    @utils.hook("received.command.resetcoins")
    @utils.kwarg("help", "Reset a user's coins to 0")
    @utils.kwarg("permission", "reset-coins")
    @utils.spec("!<nickname>ouser")
    def reset_coins(self, event):
        target = event["server"].get_user(event["args_split"][0])
        coins = self._get_user_coins(target)
        self._take(event["server"], target, coins)
        event["stdout"].write("Reset coins for %s" % target.nickname)

    @utils.hook("received.command.givecoins")
    @utils.kwarg("help", "Create coins and give them to a user")
    @utils.kwarg("permission", "give-coins")
    @utils.spec("!<nickname>ouser !<amount>coins")
    def give_coins(self, event):
        target = event["spec"][0]
        coins = event["spec"][1]
        self._give(event["server"], target, coins)
        event["stdout"].write("Gave '%s' %s coins" % (target.nickname,
            self._coin_str(coins)))

    @utils.hook("received.command.richest")
    @utils.kwarg("help", "Show the top 10 richest users")
    def richest(self, event):
        top_10 = utils.top_10(self._all_coins(event["server"]),
            convert_key=lambda nickname:
            event["server"].get_user(nickname).nickname,
            value_format=lambda value: self._coin_str_human(value))
        event["stdout"].write("Richest users: %s" % ", ".join(top_10))

    def _redeem_cache(self, server, user):
        return "redeem|%s|%s@%s" % (server.id, user.username, user.hostname)

    @utils.hook("received.command.redeemcoins")
    @utils.kwarg("help", "Redeem your free coins")
    def redeem_coins(self, event):
        user_coins = self._get_user_coins(event["user"])
        if user_coins == DECIMAL_ZERO:
            cache = self._redeem_cache(event["server"], event["user"])
            if not self.bot.cache.has_item(cache):
                redeem_amount = self._redeem_amount(event["server"])
                self._give(event["server"], event["user"], redeem_amount)

                event["stdout"].write("%s: redeemed %s coins"
                    % (event["user"].nickname, self._coin_str(redeem_amount)))

                redeem_delay = self._redeem_delay(event["server"])
                self.bot.cache.temporary_cache(cache, True, redeem_delay)
            else:
                time_left = self.bot.cache.until_expiration(cache)
                event["stderr"].write("%s: Please wait %s before redeeming" % (
                    event["user"].nickname,
                    utils.datetime.format.to_pretty_time(time_left)))
        else:
            event["stderr"].write(
                "%s: You can only redeem coins when you have none" %
                event["user"].nickname)

    @utils.hook("received.command.flip")
    @utils.kwarg("help", "Bet on a coin flip")
    @utils.kwarg("authenticated", True)
    @utils.spec("!'heads,tails !'all")
    @utils.spec("!'heads,tails !<amount>coins")
    def flip(self, event):
        side_name = event["spec"][0]
        coin_bet = event["spec"][1]
        if coin_bet == "all":
            coin_bet = self._get_user_coins(event["user"])
            if coin_bet <= DECIMAL_ZERO:
                raise utils.EventError("%s: You have no coins to bet" %
                    event["user"].nickname)

        user_coins = self._get_user_coins(event["user"])
        if coin_bet > user_coins:
            raise utils.EventError("%s: You don't have enough coins to bet" %
                event["user"].nickname)

        chosen_side = random.SystemRandom().choice(list(SIDES.keys()))
        win = side_name == chosen_side

        coin_bet_str = self._coin_str_human(coin_bet)
        if win:
            new_total = self._give(event["server"], event["user"], coin_bet)
            event["stdout"].write(
                "%s flips %s and wins %s coin%s! (new total: %s)" % (
                    event["user"].nickname, side_name, coin_bet_str,
                    "" if coin_bet == 1 else "s",
                    self._coin_str_human(new_total)
                )
            )
        else:
            self._take(event["server"], event["user"], coin_bet)
            event["stdout"].write(
                "%s flips %s and loses %s coin%s! (new total: %s)" % (
                    event["user"].nickname, side_name, coin_bet_str,
                    "" if coin_bet == 1 else "s",
                    self._coin_str_human(user_coins-coin_bet)
                )
            )

    @utils.hook("received.command.sendcoins")
    @utils.kwarg("help", "Send coins to another user")
    @utils.kwarg("authenticated", True)
    @utils.spec("!<nickname>ouser !<amount>coins")
    def send(self, event):
        target_user = event["spec"][0]

        if event["user"].get_id() == target_user.get_id():
            raise utils.EventError("%s: You can't send coins to yourself" %
                event["user"].nickname)

        send_amount = event["spec"][1]

        user_coins = self._get_user_coins(event["user"])
        redeem_amount = self._redeem_amount(event["server"])
        new_total_coins = self._get_user_coins(event["user"])-send_amount

        if user_coins == DECIMAL_ZERO:
            raise utils.EventError("%s: You have no coins" %
                event["user"].nickname)
        elif new_total_coins < redeem_amount:
            raise utils.EventError(
                "%s: You cannot send an amount of money that puts"
                " you below %s coins" % (
                event["user"].nickname,
                self._coin_str(redeem_amount)))

        target_user_coins = self._get_user_coins(target_user)
        if target_user_coins == None:
            raise utils.EventError("%s: You can only send coins to users that "
                "have had coins before" % event["user"].nickname)

        self._move(event["user"], target_user, send_amount)

        event["stdout"].write("%s sent %s coins to %s" % (
            event["user"].nickname, self._coin_str(send_amount),
            target_user.nickname))

    def _double_street(self, i):
        return (i*3)-2, (i*3)+3

    @utils.hook("received.command.roulette")
    @utils.kwarg("help", "Spin a roulette wheel")
    @utils.kwarg("authenticated", True)
    @utils.spec("!<types>word !'all")
    @utils.spec("!<types>word !<amounts>coinsmany")
    def roulette(self, event):
        bets = event["spec"][0].lower().split(",")
        if not len(bets) <= len(event["spec"][1]):
            raise utils.EventError("%s: Please provide an amount for each bet" %
                event["user"].nickname)

        if "0" in bets:
            raise utils.EventError("%s: You can't bet on 0" %
                event["user"].nickname)
        bet_amounts = []
        if event["spec"][1] == "all":
            all_coins = self._get_user_coins(event["user"])
            if all_coins <= DECIMAL_ZERO:
                raise utils.EventError("%s: You have no coins to bet" %
                    event["user"].nickname)
            bet_amounts = [all_coins]
        else:
            bet_amounts = event["spec"][1]

        bet_amount_total = sum(bet_amounts)

        user_coins = self._get_user_coins(event["user"])
        if bet_amount_total > user_coins:
            raise utils.EventError("%s: You don't have enough coins to bet" %
                event["user"].nickname)

        # black, red, odds, evens, low (1-18), high (19-36)
        # 1dozen (1-12), 2dozen (13-24), 3dozen (25-36)
        # 1column (1,4..34), 2column (2,5..35), 3column (3,6..36)
        choice = random.SystemRandom().randint(0, 36)
        winnings = {}
        losses = {}
        if choice == 0:
            event["stdout"].write("Roulette spin lands on 0, "
                "the house wins, %s loses %s" % (
                event["user"].nickname, bet_amount_total))
            self._take(event["server"], event["user"], bet_amount_total)
            return

        colour = "red" if choice in RED else "black"
        for i, bet in enumerate(bets):
            street_match = REGEX_STREET.match(bet)
            doublestreet_match = REGEX_DOUBLESTREET.match(bet)
            corner_match = REGEX_CORNER.match(bet)

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
            elif doublestreet_match:
                row = int(doublestreet_match.group(1))
                min_num, max_num = self._double_street(row)
                odds = 5*(min_num <= choice <= max_num)
            elif corner_match:
                row = int(corner_match.group(2))
                min_num, max_num = self._double_street(row)
                numbers = list(range(min_num, max_num+1))
                if corner_match.group(1) == "l":
                    numbers = numbers[:2] + numbers[3:5]
                else:
                    numbers = numbers[1:3] + numbers[-2:]
                odds = 8*(choice in numbers)
            elif bet.isdigit() and (1 <= int(bet) <= 36):
                odds = 35*(choice == int(bet))
            else:
                raise utils.EventError("%s: Unknown bet" %
                    event["user"].nickname)

            if odds == 0:
                losses[bet] = bet_amounts[i]
            else:
                winnings[bet] = [odds, bet_amounts[i]]

        self._take(event["server"], event["user"], bet_amount_total)

        winnings_str = ["%s for %s (%d to 1)" % (
            winnings[bet][1]*winnings[bet][0],
            bet,
            winnings[bet][0]) for bet in winnings.keys()]

        coin_winnings = DECIMAL_ZERO
        for odds, amount in winnings.values():
            coin_winnings += amount # give back bet
            coin_winnings += amount*odds # give winnings
        coin_losses = sum(loss for loss in losses.values())

        if coin_winnings:
            self._give(event["server"], event["user"], coin_winnings)

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

    @utils.hook("cron")
    @utils.kwarg("schedule", "0 *")
    def _interest(self, event):
        for server in self.bot.servers.values():
            if not server.get_setting("coin-interest", False):
                continue
            all_coins = self._all_coins(server)

            interest_rate = decimal.Decimal(server.get_setting(
                "interest-rate", DEFAULT_INTEREST_RATE))
            redeem_amount = self._redeem_amount(server)

            for nickname, coins in all_coins.items():
                if coins > redeem_amount:
                    interest = round(coins*interest_rate, 2)
                    server.set_user_setting(nickname, "coins",
                        self._coin_str(coins+interest))

    @utils.hook("received.command.lotterybuy")
    @utils.kwarg("help", "Buy ticket(s) for the lottery")
    @utils.kwarg("authenticated", True)
    @utils.spec("?<count>int")
    def lottery_buy(self, event):
        amount = event["spec"][0] or 1

        user_coins = self._get_user_coins(event["user"])
        coin_amount = decimal.Decimal(LOTTERY_BUYIN)*amount
        new_user_coins = user_coins-coin_amount
        redeem_amount = self._redeem_amount(event["server"])

        if coin_amount > user_coins:
            raise utils.EventError("%s: You don't have enough coins" %
                event["user"].nickname)
        elif new_user_coins < redeem_amount:
            raise utils.EventError(
                "%s: you can't play the lottery if it puts your total coins "
                "below %s" % (event["user"].nickname,
                self._coin_str(redeem_amount)))

        self._take(event["server"], event["user"], coin_amount)

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
    @utils.kwarg("help", "Show how many lottery tickets you currently have")
    def my_lottery(self, event):
        lottery = event["server"].get_setting("lottery", {})
        count = lottery.get(event["user"].nickname_lower, 0)
        event["stdout"].write("%s: You have %d lottery ticket%s" % (
            event["user"].nickname, count, "" if count == 1 else "s"))

    @utils.hook("received.command.jackpot")
    @utils.kwarg("help", "Show the current lottery jackpot")
    def jackpot(self, event):
        lottery = event["server"].get_setting("lottery", {})
        count = sum(value for nickname, value in lottery.items())
        event["stdout"].write("%s: The current jackpot is %s" % (
            event["user"].nickname, decimal.Decimal(LOTTERY_BUYIN)*count))

    @utils.hook("received.command.nextlottery")
    @utils.kwarg("help", "Show time until the next lottery draw")
    def next_lottery(self, event):
        until = self._until_next_6_hour()
        event["stdout"].write("Next lottery is in: %s" %
            utils.datetime.format.to_pretty_time(until))

    @utils.hook("received.command.lotterywinner")
    @utils.kwarg("help", "Show who last won the lottery")
    def lottery_winner(self, event):
        winner = event["server"].get_setting("lottery-winner", None)
        if winner:
            event["stdout"].write("Last lottery winner: %s" % winner)
        else:
            event["stderr"].write("There have been no lottery winners!")

    @utils.hook("cron")
    @utils.kwarg("schedule", "0 */6")
    def _lottery(self, event):
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
