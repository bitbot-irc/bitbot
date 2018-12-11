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
        page = utils.http.request(URL_OMDB, get_params={
            "t": event["args"],
            "apikey": self.bot.config["omdbapi-api-key"]},
            json=True)
        if page:
            if "Title" in page.data:
                event["stdout"].write("%s, %s (%s) %s (%s/10.0) %s" % (
                    page.data["Title"], page.data["Year"], page.data["Runtime"],
                    page.data["Plot"], page.data["imdbRating"],
                    URL_IMDBTITLE % page.data["imdbID"]))
            else:
                event["stderr"].write("Title not found")
        else:
            raise utils.EventsResultsError()
