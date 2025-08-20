from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from urllib.parse import urlparse

class Keyboards:

    @staticmethod
    def cities(cities: list[str]):
        buttons = []
        for city in cities:
            buttons.append([InlineKeyboardButton(text=city, callback_data=f"city:{city}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def jobs(city, vacancies):
        buttons = []
        for i, vacancy in enumerate(vacancies):
            buttons.append([InlineKeyboardButton(text=vacancy["title"], callback_data=f"job:{city}:{i}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def job_detail(city, index, url):
        def _is_valid_http_url(u: str) -> bool:
            try:
                parsed = urlparse(u)
                return parsed.scheme in ("http", "https") and bool(parsed.netloc)
            except Exception:
                return False

        buttons = []
        if _is_valid_http_url(url):
            buttons.append([InlineKeyboardButton(text="🔗 Перейти к вакансиям", url=url)])
        buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"city:{city}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin(cities):
        buttons = []
        for city in cities:
            buttons.append([InlineKeyboardButton(text=city, callback_data=f"admin_city:{city}")])
        buttons.append([InlineKeyboardButton(text="➕ Добавить новый город", callback_data="admin_city:new")])
        buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="admin_back")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def reply_start():
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Главное меню")]],
            resize_keyboard=True,
            one_time_keyboard=False
        )