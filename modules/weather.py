#--require-config openweathermap-api-key

from src import Utils

URL_WEATHER = "http://api.openweathermap.org/data/2.5/weather"

class Module(object):
    def __init__(self, bot, events, exports):
        self.bot = bot
        events.on("received.command.weather").hook(self.weather, min_args=1,
            help="Get current weather data for a provided location",
            usage="<location>")

    def weather(self, event):
        api_key = self.bot.config["openweathermap-api-key"]
        page = Utils.get_url(URL_WEATHER, get_params={
            "q": event["args"], "units": "metric",
            "APPID": api_key},
            json=True)
        if page:
            if "weather" in page:
                location = "%s, %s" % (page["name"], page["sys"][
                    "country"])
                celsius = "%dC" % page["main"]["temp"]
                fahrenheit = "%dF" % ((page["main"]["temp"]*(9/5))+32)
                description = page["weather"][0]["description"].title()
                humidity = "%s%%" % page["main"]["humidity"]
                wind_speed = "%sKM/h" % page["wind"]["speed"]

                event["stdout"].write(
                    "(%s) %s/%s | %s | Humidity: %s | Wind: %s" % (
                    location, celsius, fahrenheit, description, humidity,
                    wind_speed))
            else:
                event["stderr"].write("No weather information for this location")
        else:
            event["stderr"].write("Failed to load results")
