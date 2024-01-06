from threading import Thread
import requests
import json
import sys

__version__ = "1.3"


class Bloodtrail:
    def __init__(self, number):
        with open("data.json", "r", encoding="utf-8") as f:
            json_data = json.load(f)
        self.data = json_data
        if number == "":
            if self.data["last_used_number"]:
                self.number = self.data["last_used_number"]
                print(f"{'USING LATEST NUMBER :': >40} {self.data['last_used_number']}")
                pass
            else:
                print(f"{'ERROR :': >40} write number as a target to save it")
                sys.exit()
        else:
            self.number = number
            self.data["last_used_number"] = self.number
            with open("data.json", "w", encoding="utf-8") as j:
                json.dump(obj=self.data, fp=j, ensure_ascii=False, indent=4)

    def format_data(self):
        for i in self.data["services"]:
            for k, v in self.data["services"][i]["data"].items():
                if "%NUMBER%" in v:
                    v = v.replace("%NUMBER%", self.number[int(self.data["services"][i]["phone_f"]):])
                    self.data["services"][i]["data"][k] = v

    @staticmethod
    def post_request(service, _url, _json=None, _data=None):
        if _json:
            r = requests.post(url=_url,
                              json=_json)
        else:
            r = requests.post(url=_url,
                              data=_data)
        return print(f"{'REQUEST STATUS OF ' + service + ' :': >40} {r.status_code}")

    def start_threads(self, repeats=1):
        for i in range(repeats):
            for service in self.data["services"]:
                data_type = self.data["services"][service]["data_type"]
                if data_type == "json":
                    t = Thread(target=self.post_request, args=(service,
                                                               self.data["services"][service]["url"],
                                                               self.data["services"][service]["data"],
                                                               None))
                    t.start()
                else:
                    t = Thread(target=self.post_request, args=(service,
                                                               self.data["services"][service]["url"],
                                                               None,
                                                               self.data["services"][service]["data"]))
                    t.start()


if __name__ == '__main__':
    bloodtrail = Bloodtrail(input(f"{'BLOODTRAIL :': >40} {__version__}\n{'TARGET NUMBER :': >40} "))
    bloodtrail.format_data()
    bloodtrail.start_threads((int(input(f"{'REPEATS COUNT :': >40} "))))
