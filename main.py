import requests
import json
import sys

__version__ = "1.3beta03"

with open("data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)


class Bloodtrail:
    def __init__(self, phone, data):
        if phone == "":
            if data["last_used_number"]:
                self.phone = data["last_used_number"]
                pass
            else:
                print(f"{'ERROR :': >40} write number as a target to save it")
                sys.exit()
        else:
            self.phone = phone
            data["last_used_number"] = self.phone
            with open("data.json", "w", encoding="utf-8") as j:
                json.dump(obj=data, fp=j, ensure_ascii=False, indent=4)
        self.data = data

    @staticmethod
    def print_request_result(r_status_code, r_service_name):
        print(f"{'REQUEST STATUS OF ' + r_service_name + ' :': >40} {r_status_code}")

    def format_data_in_services(self):
        for i in self.data["services"]:
            for k, v in self.data["services"][i]["data"].items():
                if "%PHONE%" in v:
                    v = v.replace("%PHONE%", self.phone[int(self.data["services"][i]["phone_f"]):])
                    self.data["services"][i]["data"][k] = v

    def send_requests(self, repeats=1):
        for i in range(repeats):
            for s in self.data["services"]:
                r_type = self.data["services"][s]["data_type"]
                if r_type == "json":
                    r = (requests.post(url=self.data["services"][s]["url"],
                                       json=self.data["services"][s]["data"]))
                else:
                    r = (requests.post(url=self.data["services"][s]["url"],
                                       data=self.data["services"][s]["data"]))
                self.print_request_result(r.status_code, s)


if __name__ == '__main__':
    script = Bloodtrail(input(f"{'BLOODTRAIL :': >40} {__version__}\n{'TARGET NUMBER :': >40} "), json_data)
    script.format_data_in_services()
    script.send_requests(int(input(f"{'REPEATS COUNT :': >40} ")))
