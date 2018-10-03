#--require-config omdbapi-api-key

import json
from src import ModuleManager, utils

URL_OMDB = "http://www.omdbapi.com/"
URL_IMDBTITLE = "http://imdb.com/title/%s"

class Module(ModuleManager.BaseModule):
    _name = "IMDb"

    @utils.hook("received.command.imdb", min_args=1)
    def imdb(self, event):
        """
        :help: Search for a given title on IMDb
        :usage: <movie/tv title>
        """
        page = utils.http.get_url(URL_OMDB, get_params={
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
