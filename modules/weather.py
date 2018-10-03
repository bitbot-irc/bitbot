#--require-config openweathermap-api-key

from src import ModuleManager, utils

URL_WEATHER = "http://api.openweathermap.org/data/2.5/weather"

class Module(ModuleManager.BaseModule):
    @utils.hook("received.command.weather", min_args=1, usage="<location>")
    def weather(self, event):
        """
        :help: Get current weather data for a provided location
        :usage: <location>
        """
        api_key = self.bot.config["openweathermap-api-key"]
        page = utils.http.get_url(URL_WEATHER, get_params={
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
