#--depends-on commands

from src import ModuleManager, utils

UPCITEMDB_URL = "https://api.upcitemdb.com/prod/trial/lookup"

class Module(ModuleManager.BaseModule):
    _name = "UPC"

    @utils.hook("received.command.upc|ean|gtin", min_args=1)
    def upc(self, event):
        """
        :help: Look up a product by UPC, EAN or GTIN
        :usage: <UPC|EAN|GTIN>
        """
        arg_len = len(event["args_split"][0])
        if not arg_len == 12 and not arg_len == 13:
            raise utils.EventError("Invalid UPC/EAN/GTIN provided")

        page = utils.http.request(UPCITEMDB_URL,
            get_params={"upc": event["args_split"][0]},
            json=True)
        if page:
            if not len(page.data["items"]):
                raise utils.EventError("UPC/EAN not found")
            item = page.data["items"][0]

            brand = item.get("brand", None)
            brand = "" if not brand else "%s - " % brand
            title = item["title"]
            description = item.get("description", None)
            description = " " if not description else ": %s " % description

            weight = item.get("weight", None)
            weight = weight or "unknown"
            size = item.get("dimension", None)
            size = size or "unknown"

            currency = item.get("currency", None)
            lowest_price = item.get("lowest_recorded_price", None)
            highest_price = item.get("highest_recorded_price", None)

            pricing = "price: unknown"
            if lowest_price and highest_price and currency:
                pricing = "price: %s to %s %s" % (
                    lowest_price, highest_price, currency)

            event["stdout"].write("%s%s%s(weight: %s"
                ", size: %s, price: %s)" % (
                brand, title, description, weight, size, pricing))
        else:
            raise utils.EventsResultsError()
