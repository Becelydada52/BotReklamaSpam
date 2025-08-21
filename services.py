import json
import logging
from typing import Dict, List

logger = logging.getLogger(__name__)

class Jobservice:
    def __init__(self, jobs_file: str = 'jobs.json', admins_file: str = 'admins.json'):
        self.jobs_file = jobs_file
        self.admins_file = admins_file
        self.jobs = self.load_jobs()
        self.roles = self.load_roles()

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

    #==Роли/Админка==
    def load_roles(self) -> Dict[str, List[int]]:
        """Load roles from admins_file. Supports old list format for backward compatibility."""
        try:
            with open(self.admins_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            logger.warning("Roles file missing or invalid, starting with defaults: %s", self.admins_file)
            data = []


        if isinstance(data, list):
            logger.info("Loaded legacy roles format (list of admins), count=%d", len(data))
            return {"admins": data, "super_admins": [], "developers": []}

        if isinstance(data, dict):
            roles = {
                "admins": list(map(int, data.get("admins", []))),
                "super_admins": list(map(int, data.get("super_admins", []))),
                "developers": list(map(int, data.get("developers", []))),
            }
            logger.info(
                "Loaded roles: admins=%d, super_admins=%d, developers=%d",
                len(roles["admins"]), len(roles["super_admins"]), len(roles["developers"])
            )
            return roles

        logger.warning("Unknown roles format, using empty roles")
        return {"admins": [], "super_admins": [], "developers": []}

    def save_roles(self):
        with open(self.admins_file, "w", encoding="utf-8") as f:
            json.dump(self.roles, f, indent=4, ensure_ascii=False)
        logger.debug(
            "Saved roles to %s (admins=%d, super_admins=%d, developers=%d)",
            self.admins_file,
            len(self.roles.get("admins", [])),
            len(self.roles.get("super_admins", [])),
            len(self.roles.get("developers", [])),
        )


    def is_admin(self, user_id: int) -> bool:
        return int(user_id) in self.roles.get("admins", [])

    def is_super_admin(self, user_id: int) -> bool:
        return int(user_id) in self.roles.get("super_admins", [])

    def is_developer(self, user_id: int) -> bool:
        return int(user_id) in self.roles.get("developers", [])

    def has_admin_access(self, user_id: int) -> bool:
        """Any role that can use admin panel (admin, super admin, developer)."""
        uid = int(user_id)
        return (
            uid in self.roles.get("admins", [])
            or uid in self.roles.get("super_admins", [])
            or uid in self.roles.get("developers", [])
        )


    def add_admin(self, user_id: int):
        uid = int(user_id)
        if uid not in self.roles["admins"]:
            self.roles["admins"].append(uid)
            self.save_roles()
            logger.info("Added admin uid=%d", uid)

    def remove_admin(self, user_id: int):
        uid = int(user_id)
        if uid in self.roles["admins"]:
            self.roles["admins"].remove(uid)
            self.save_roles()
            logger.info("Removed admin uid=%d", uid)

    def add_super_admin(self, user_id: int):
        uid = int(user_id)
        if uid not in self.roles["super_admins"]:
            self.roles["super_admins"].append(uid)
            self.save_roles()
            logger.info("Added super_admin uid=%d", uid)

    def remove_super_admin(self, user_id: int):
        uid = int(user_id)
        if uid in self.roles["super_admins"]:
            self.roles["super_admins"].remove(uid)
            self.save_roles()
            logger.info("Removed super_admin uid=%d", uid)

    def add_developer(self, user_id: int):
        uid = int(user_id)
        if uid not in self.roles["developers"]:
            self.roles["developers"].append(uid)
            self.save_roles()
            logger.info("Added developer uid=%d", uid)
            logger.info("Roles updated: admins=%s, super_admins=%s, developers=%s", self.roles.get("admins", []), self.roles.get("super_admins", []), self.roles.get("developers", []))

    def remove_developer(self, user_id: int):
        uid = int(user_id)
        if uid in self.roles["developers"]:
            self.roles["developers"].remove(uid)
            self.save_roles()
            logger.info("Removed developer uid=%d", uid)
            logger.info("Roles updated: admins=%s, super_admins=%s, developers=%s", self.roles.get("admins", []), self.roles.get("super_admins", []), self.roles.get("developers", []))