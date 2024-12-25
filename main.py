import re
import asyncio
import aiohttp
import json
import sys
from fake_useragent import UserAgent

__version__ = "1.4"


def format_phone(raw_number, phone_pattern) -> str:
    digits = re.sub(r"[^\d]", "", raw_number)

    if len(digits) < 11:
        raise ValueError(f"{' ' : >40}Wrong format.")

    formatted = phone_pattern
    for digit in digits:
        formatted = formatted.replace('X', digit, 1)

    return formatted


class Service:
    def __init__(self,
                 service_name: str,
                 url: str,
                 data: dict,
                 phone: str,
                 timeout: int):
        self.service_name = service_name
        self.url = url
        self.data = data
        self.phone = phone
        self.timeout = timeout
        self.time = 0

    async def request(self):
        ua = UserAgent()
        headers = {"User-Agent": ua.random}

        async with aiohttp.ClientSession() as session:
            try:
                async with session.post(self.url, json=self.data, headers=headers) as response:
                    result = response.status
                    print(f"{' ' : >40}SERVICE: '{self.service_name}' - STATUS: {result}")
            except Exception as e:
                print(f"{' ' : >40}SERVICE: '{self.service_name}' - ERROR: {e}")

    async def update(self):
        if self.time == 0:
            self.time = self.timeout
            await self.request()
            print(f"{' ' : >40}TIMEOUT: '{self.service_name}' for {self.time}sec.")
        else:
            self.time -= 1


class Services:
    def __init__(self):
        self.services: list[Service] = []

    def import_dict(self, service_dict, phone):
        for service_name, service_data in service_dict.items():
            formatted_phone = format_phone(phone, service_data["phone_pattern"])

            for key, value in service_data["data"].items():
                if "%PHONE%" in value:
                    service_data["data"][key] = value.replace("%PHONE%", formatted_phone)

            service = Service(
                service_name=service_name,
                url=service_data["url"],
                data=service_data["data"],
                phone=formatted_phone,
                timeout=service_data["timeout"]
            )
            self.services.append(service)

    async def start(self, timer):
        while (timer > 0):
            await asyncio.gather(*(service.update() for service in self.services))
            await asyncio.sleep(1)
            timer -= 1


class BloodTrail:
    def __init__(self, number, timer):
        try:
            with open("data.json", "r", encoding="utf-8") as f:
                self.data = json.load(f)
            if not number or not timer:
                print(f"{' ' : >40}ERROR: Wrong args.")
                sys.exit()
            else:
                self.number = number
                self.timer = timer
        except FileNotFoundError:
            print(f"{' ' : >40}ERROR: data.json file not found.")
            sys.exit()

    async def start_services(self):
        services = Services()
        services.import_dict(self.data["services"], self.number)
        await services.start(self.timer)


if __name__ == "__main__":
    async def main():
        print(f"{' ' : >40}BLOODTRAIL: v{__version__}")
        bloodtrail = BloodTrail(input(f"{' ' : >40}TARGET NUMBER (+7XXXXXXXXX): "),
                                int(input(f"{' ' : >40}TIMER: ")))
        await bloodtrail.start_services()

    asyncio.run(main())