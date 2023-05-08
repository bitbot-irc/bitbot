#--depends-on commands
#--depends-on location
#--require-config openweathermap-api-key

from src import ModuleManager, utils

URL_WEATHER = "http://api.openweathermap.org/data/2.5/weather"

class Module(ModuleManager.BaseModule):
    def _user_location(self, user):
        user_location = user.get_setting("location", None)
        if not user_location == None:
            name = user_location.get("name", None)
            return [user_location["lat"], user_location["lon"], name]

    @utils.hook("received.command.w", alias_of="weather")
    @utils.hook("received.command.weather")
    def weather(self, event):
        """
        :help: Get current weather for you or someone else
        :usage: [nickname]
        :require_setting: location
        :require_setting_unless: 1
        """
        api_key = self.bot.config["openweathermap-api-key"]

        location = None
        query = None
        nickname = None
        if event["args"]:
            query = event["args"]
            if len(event["args_split"]) == 1 and event["server"].has_user_id(
                    event["args_split"][0]):
                target_user = event["server"].get_user(event["args_split"][0])
                location = self._user_location(target_user)
                if not location == None:
                    nickname = target_user.nickname
        else:
            location = self._user_location(event["user"])
            nickname = event["user"].nickname
            if location == None:
                raise utils.EventError("You don't have a location set")

        args = {"units": "metric", "APPID": api_key}


        if location == None and query:
            location_info = self.exports.get("get-location")(query)
            if not location_info == None:
                location = [location_info["lat"], location_info["lon"],
                    location_info.get("name", None)]
        if location == None:
            raise utils.EventError("Unknown location")

        lat, lon, location_name = location
        args["lat"] = lat
        args["lon"] = lon

        page = utils.http.request(URL_WEATHER, get_params=args).json()
        if page:
            if "weather" in page:
                if location_name:
                    location_str = location_name
                else:
                    location_parts = [page["name"]]
                    if "country" in page["sys"]:
                        location_parts.append(page["sys"]["country"])
                    location_str = ", ".join(location_parts)

                celsius = "%dC" % page["main"]["temp"]
                fahrenheit = "%dF" % ((page["main"]["temp"]*(9/5))+32)
                kelvin = "%dK" % ((page["main"]["temp"])+273.15)
                description = page["weather"][0]["description"].title()
                humidity = "%s%%" % page["main"]["humidity"]

                # wind speed is in metres per second - 3.6* for KMh
                wind_speed = 3.6*page["wind"]["speed"]
                wind_speed_k = "%skm/h" % round(wind_speed, 1)
                wind_speed_m = "%smi/h" % round(0.6214*wind_speed, 1)

                if not nickname == None:
                    location_str = "(%s) %s" % (nickname, location_str)

                event["stdout"].write(
                    "%s | %s/%s/%s | %s | Humidity: %s | Wind: %s/%s" % (
                    location_str, celsius, fahrenheit, kelvin, description,
                    humidity, wind_speed_k, wind_speed_m))
            else:
                event["stderr"].write("No weather information for this location")
        else:
            raise utils.EventResultsError()

