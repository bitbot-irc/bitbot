from src import ModuleManager, Utils

class Module(ModuleManager.BaseModule):
    _name = "BTC"

    @Utils.hook("received.command.btc")
    def btc(self, event):
        """
        :help: Get the exchange rate of bitcoins
        :usage: [currency]
        """
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
