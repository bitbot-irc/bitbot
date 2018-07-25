import Utils

UPCITEMDB_URL = "https://api.upcitemdb.com/prod/trial/lookup"

class Module(object):
    _name = "UPC"
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on(
            "upc", "ean", "gtin").hook(
            self.upc, min_args=1, usage="<UPC|EAN>",
            help="Look up a product by UPC or EAN")

    def upc(self, event):
        arg_len = len(event["args_split"][0])
        if not arg_len == 12 and not arg_len == 13:
            event["stderr"].write("Invalid UPC/EAN provided")
            return

        page = Utils.get_url(UPCITEMDB_URL,
            get_params={"upc": event["args_split"][0]},
            json=True)
        if page:
            if not len(page["items"]):
                event["stderr"].write("UPC/EAN not found")
                return
            item = page["items"][0]

            brand = item["brand"]
            title = item["title"]
            description = item["description"]

            weight = item["weight"]
            size = item["dimension"]

            currency = item["currency"]
            lowest_price = item["lowest_recorded_price"]
            highest_price = item["highest_recorded_price"]

            event["stdout"].write("%s - %s: %s (weight: %s"
                ", size: %s, price: %s to %s %s)" % (
                brand, title, description, weight, size,
                lowest_price, highest_price, currency))
        else:
            event["stderr"].write("Failed to load results")
