#--require-config trakt-api-key

import Utils

URL_TRAKT = "https://api-v2launch.trakt.tv/users/%s/watching"
URL_TRAKTSLUG = "https://trakt.tv/%s/%s"

class Module(object):
    def __init__(self, bot):
        self.bot = bot
        bot.events.on("received").on("command").on("nowwatching",
            "nw").hook(self.now_watching,
            help="Get what you or another user is now watching "
            "on trakt.tv", usage="[username]")

        bot.events.on("postboot").on("configure").on("set"
            ).call(setting="trakt", help="Set username on trakt.tv")

    def now_watching(self, event):
        if event["args"]:
            username = event["args_split"][0]
        else:
            username = event["user"].get_setting("trakt",
                event["user"].nickname)
        page = Utils.get_url(URL_TRAKT % username, headers={
            "Content-Type": "application/json",
            "trakt-api-version": "2", "trakt-api-key":
            self.bot.config["trakt-api-key"]}, json=True,
            code=True)
        if page[0]:
            code, page = page
            if code == 200:
                type = page["type"]
                if type == "movie":
                    title = page["movie"]["title"]
                    year = page["movie"]["year"]
                    slug = page["movie"]["ids"]["slug"]
                    event["stdout"].write(
                        "%s is now watching %s (%s) %s" % (
                        username, title, year,
                        URL_TRAKTSLUG % ("movie", slug)))
                elif type == "episode":
                    season = page["episode"]["season"]
                    episode_number = page["episode"]["number"]
                    episode_title = page["episode"]["title"]
                    show_title = page["show"]["title"]
                    show_year = page["show"]["year"]
                    slug = page["show"]["ids"]["slug"]
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
            event["stderr"].write("Failed to load results")
