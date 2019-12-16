#--depends-on commands

from bitbot import ModuleManager, utils

class Module(ModuleManager.BaseModule):
    _name = "BTC"

    @utils.hook("received.command.btc")
    def btc(self, event):
        """
        :help: Get the exchange rate of bitcoins
        :usage: [currency]
        """
        currency = (event["args"] or "USD").upper()
        page = utils.http.request("https://blockchain.info/ticker").json()
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
            raise utils.EventResultsError()
