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
        buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="back:cities")])
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
        buttons.append([InlineKeyboardButton(text="⬅ К списку работ", callback_data=f"back:jobs:{city}")])
        buttons.append([InlineKeyboardButton(text="⬅ К городам", callback_data=f"back:cities")])
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

    @staticmethod
    def reply_menu(is_admin: bool = False):
        if is_admin:
            return ReplyKeyboardMarkup(
                keyboard=[[KeyboardButton(text="Главное меню"), KeyboardButton(text="Админка")]],
                resize_keyboard=True,
                one_time_keyboard=False
            )
        else:
            return Keyboards.reply_start()

    @staticmethod
    def admin_back_to_city():
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅ Назад к городам", callback_data="admin_back_to_city")]]
        )

    @staticmethod
    def admin_back_to_title():
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅ Назад", callback_data="admin_back_to_title")]]
        )

    @staticmethod
    def admin_back_to_desc():
        return InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅ Назад", callback_data="admin_back_to_desc")]]
        )

    @staticmethod
    def back(callback_data: str, text: str = "⬅ Назад"):
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=text, callback_data=callback_data)]])