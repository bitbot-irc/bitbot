#--depends-on config

import typing
from src import ModuleManager, utils

URL_OPENCAGE = "https://api.opencagedata.com/geocode/v1/json"

class LocationSetting(utils.Setting):
    _func = None
    def parse(self, value: str) -> typing.Any:
        return self._func(value)

class Module(ModuleManager.BaseModule):
    def on_load(self):
        setting = LocationSetting("location", "Set your location",
            example="London, GB")
        setting._func = self._get_location
        self.exports.add("set", setting)
        self.exports.add("get-location", self._get_location)

    def _get_location(self,  s):
        page = utils.http.request(URL_OPENCAGE, get_params={
            "q": s, "key": self.bot.config["opencagedata-api-key"], "limit": "1"
            }, json=True)
        if page and page.data["results"]:
            result = page.data["results"][0]
            timezone = result["annotations"]["timezone"]["name"]
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
