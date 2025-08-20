import json
from typing import Dict, List

class Jobservice:
    def __init__(self, jobs_file: str = 'jobs.json', admins_file: str = 'admins.json'):
        self.jobs_file = jobs_file
        self.admins_file = admins_file
        self.jobs = self.load_jobs()
        self.admins = self.load_admins()

    # ==Вакансии==
    def load_jobs(self) -> Dict[str, List[Dict]]:
        try:
            with open(self.jobs_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def save_jobs(self):
        with open(self.jobs_file, "w", encoding="utf-8") as f:
            json.dump(self.jobs, f, indent=4, ensure_ascii=False)

    def get_cities(self) -> List[str]:
        return list(self.jobs.keys())

    def get_jobs(self, city: str) -> List[Dict]:
        return self.jobs.get(city, [])

    def get_job(self, city: str, index: int) -> Dict:
        return self.jobs[city][index]

    def add_city(self, city: str):
        if city not in self.jobs:
            self.jobs[city] = []
            self.save_jobs()

    def add_job(self, city: str, title: str, desc: str, url: str):
        if city not in self.jobs:
            self.jobs[city] = []
            self.save_jobs()
        self.jobs[city].append({"title": title, "desc": desc, "url": url})
        self.save_jobs()

    #==Админка==
    def load_admins(self) -> List[int]:
        try:
            with open(self.admins_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def save_admins(self):
        with open(self.admins_file, "w", encoding="utf-8") as f:
            json.dump(self.admins, f, indent=4, ensure_ascii=False)

    def is_admin(self, user_id: int) -> bool:
        return user_id in self.admins

    def add_admin(self, user_id: int):
        if user_id not in self.admins:
            self.admins.append(user_id)
            self.save_admins()

    def remove_admin(self, user_id: int):
        if user_id in self.admins:
            self.admins.remove(user_id)
            self.save_admins()