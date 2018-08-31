import Utils

class Module(object):
    _name = "BTC"
    def __init__(self, bot, events):
        self.bot = bot
        events.on("received").on("command").on("btc").hook(
            self.btc, help="Get the exchange rate of bitcoins",
            usage="[currency]")

    def btc(self, event):
        currency = (event["args"] or "USD").upper()
        page = Utils.get_url("https://blockchain.info/ticker",
            json=True)
        if page:
            if currency in page:
                conversion = page[currency]
                buy, sell = conversion["buy"], conversion["sell"]
                event["stdout"].write("1 BTC = %.2f %s (buy) %.2f %s "
                    "(sell)" % (buy, currency, sell, currency))
            else:
                event["stderr"].write("Unknown currency, available "
                    "currencies: %s" % ", ".join(page.keys()))
        else:
            event["stderr"].write("Failed to load results")
