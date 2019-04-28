#--require-config openweathermap-api-key

from src import ModuleManager, utils

URL_WEATHER = "http://api.openweathermap.org/data/2.5/weather"

class Module(ModuleManager.BaseModule):
    def _user_location(self, user):
        user_location = user.get_setting("location", None)
        if not user_location == None:
            return "%s, %s" % (user_location["city"], user_location["country"])

    @utils.hook("received.command.weather")
    def weather(self, event):
        """
        :help: Get current weather for you or someone else
        :usage: [nickname]
        """
        api_key = self.bot.config["openweathermap-api-key"]

        location = None
        if event["args"]:
            target_user = event["server"].get_user(event["args_split"][0])
            location = self._user_location(target_user)
            if location == None:
                raise utils.EventError("%s doesn't have a location set"
                    % target_user.nickname)
        else:
            location = self._user_location(event["user"])
            if location == None:
                raise utils.EventError("You don't have a location set")

        page = utils.http.request(URL_WEATHER, get_params={
            "q": location, "units": "metric",
            "APPID": api_key},
            json=True)
        if page:
            if "weather" in page.data:
                location = "%s, %s" % (page.data["name"], page.data["sys"][
                    "country"])
                celsius = "%dC" % page.data["main"]["temp"]
                fahrenheit = "%dF" % ((page.data["main"]["temp"]*(9/5))+32)
                description = page.data["weather"][0]["description"].title()
                humidity = "%s%%" % page.data["main"]["humidity"]
                wind_speed = "%sKM/h" % page.data["wind"]["speed"]

                event["stdout"].write(
                    "(%s) %s/%s | %s | Humidity: %s | Wind: %s" % (
                    location, celsius, fahrenheit, description, humidity,
                    wind_speed))
            else:
                event["stderr"].write("No weather information for this location")
        else:
            raise utils.EventsResultsError()
