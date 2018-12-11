#--require-config trakt-api-key

from src import ModuleManager, utils

URL_TRAKT = "https://api-v2launch.trakt.tv/users/%s/watching"
URL_TRAKTSLUG = "https://trakt.tv/%s/%s"

@utils.export("set", {"setting": "trakt", "help": "Set username on trakt.tv"})
class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.nw", alias_of="nowwatching")
    @utils.hook("received.command.nowwatching")
    def now_watching(self, event):
        """
        :help: Get what you or another user is now watching on trakt.tv
        :usage: [username]
        """
        if event["args"]:
            username = event["args_split"][0]
        else:
            username = event["user"].get_setting("trakt",
                event["user"].nickname)
        page = utils.http.request(URL_TRAKT % username, headers={
            "Content-Type": "application/json",
            "trakt-api-version": "2", "trakt-api-key":
            self.bot.config["trakt-api-key"]}, json=True,
            code=True)
        if page
            if page.code == 200:
                type = page.data["type"]
                if type == "movie":
                    title = page.data["movie"]["title"]
                    year = page.data["movie"]["year"]
                    slug = page.data["movie"]["ids"]["slug"]
                    event["stdout"].write(
                        "%s is now watching %s (%s) %s" % (
                        username, title, year,
                        URL_TRAKTSLUG % ("movie", slug)))
                elif type == "episode":
                    season = page.data["episode"]["season"]
                    episode_number = page.data["episode"]["number"]
                    episode_title = page.data["episode"]["title"]
                    show_title = page.data["show"]["title"]
                    show_year = page.data["show"]["year"]
                    slug = page.data["show"]["ids"]["slug"]
                    event["stdout"].write(
                        "%s is now watching %s s%se%s - %s %s" % (
                        username, show_title, str(season).zfill(2),
                        str(episode_number).zfill(2), episode_title,
                        URL_TRAKTSLUG % ("shows", slug)))
                else:
                    print("ack! unknown trakt media type!")
            else:
                event["stderr"].write(
                    "%s is not watching anything" % username)
        else:
            raise utils.EventsResultsError()
