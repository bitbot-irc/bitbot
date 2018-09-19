#--require-config omdbapi-api-key

import json
import Utils

URL_OMDB = "http://www.omdbapi.com/"
URL_IMDBTITLE = "http://imdb.com/title/%s"

class Module(object):
    _name = "IMDb"
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received.command.imdb").hook(self.imdb, min_args=1,
            help="Search for a given title on IMDb", usage="<movie/tv title>")

    def imdb(self, event):
        page = Utils.get_url(URL_OMDB, get_params={
            "t": event["args"],
            "apikey": self.bot.config["omdbapi-api-key"]},
            json=True)
        if page:
            if "Title" in page:
                event["stdout"].write("%s, %s (%s) %s (%s/10.0) %s" % (
                    page["Title"], page["Year"], page["Runtime"],
                    page["Plot"], page["imdbRating"],
                    URL_IMDBTITLE % page["imdbID"]))
            else:
                event["stderr"].write("Title not found")
        else:
            event["stderr"].write("Failed to load results")
