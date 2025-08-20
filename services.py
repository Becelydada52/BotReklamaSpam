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

    #==Расширенные операции (админка)==
    def rename_city(self, old_city: str, new_city: str) -> bool:
        if old_city not in self.jobs:
            return False
        if new_city in self.jobs and new_city != old_city:
            return False
        self.jobs[new_city] = self.jobs.pop(old_city)
        self.save_jobs()
        return True

    def delete_city(self, city: str) -> bool:
        if city in self.jobs:
            del self.jobs[city]
            self.save_jobs()
            return True
        return False

    def update_job(self, city: str, index: int, title: str | None = None, desc: str | None = None, url: str | None = None) -> bool:
        jobs = self.jobs.get(city)
        if jobs is None or not (0 <= index < len(jobs)):
            return False
        if title is not None:
            jobs[index]["title"] = title
        if desc is not None:
            jobs[index]["desc"] = desc
        if url is not None:
            jobs[index]["url"] = url
        self.save_jobs()
        return True

    def delete_job(self, city: str, index: int) -> bool:
        jobs = self.jobs.get(city)
        if jobs is None or not (0 <= index < len(jobs)):
            return False
        jobs.pop(index)
        self.save_jobs()
        return True

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