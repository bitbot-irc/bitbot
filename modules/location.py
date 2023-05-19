#--depends-on config
#--require-config opencagedata-api-key

import typing
import pytz
from src import ModuleManager, utils

URL_OPENCAGE = "https://api.opencagedata.com/geocode/v1/json"

class Module(ModuleManager.BaseModule):
    def on_load(self):
        setting = utils.FunctionSetting(self._get_location, "location",
            "Set your location", example="London, GB")
        self.exports.add("set", setting)

    @utils.export("get-location")
    def _get_location(self,  s):
        page = utils.http.request(URL_OPENCAGE, get_params={"limit": "1",
            "q": s, "key": self.bot.config["opencagedata-api-key"]}).json()
        if page and page["results"]:
            result = page["results"][0]
            timezone = result["annotations"]["timezone"]["name"]
            try:
                pytz.timezone(timezone)
            except pytz.exceptions.UnknownTimeZoneError:
                return None

            lat = result["geometry"]["lat"]
            lon = result["geometry"]["lng"]

            name_parts = []
            components = result["components"]
            for part in ["town", "city", "state", "country"]:
                if part in components:
                    name_parts.append(components[part])

            if not name_parts:
                name_parts.append(result["formatted"])

            name = ", ".join(name_parts)

            return {"timezone": timezone, "lat": lat, "lon": lon, "name": name}
