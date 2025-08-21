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
    def admin(cities, can_manage_roles: bool = False, can_manage_bot: bool = False):
        buttons = []
        for city in cities:
            buttons.append([
                InlineKeyboardButton(text=f"📋 {city}", callback_data=f"manage_city:{city}"),
                InlineKeyboardButton(text="➕ Добавить работу", callback_data=f"admin_city:{city}")
            ])
        buttons.append([InlineKeyboardButton(text="➕ Добавить новый город", callback_data="admin_city:new")])
        if can_manage_roles:
            buttons.append([InlineKeyboardButton(text="👤 Управление ролями", callback_data="roles_menu")])
        if can_manage_bot:
            buttons.append([InlineKeyboardButton(text="🛠 Управление ботом", callback_data="dev_menu")])
        buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="admin_back")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin_city_menu(city: str):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📝 Переименовать город", callback_data=f"admin_city_rename:{city}")],
            [InlineKeyboardButton(text="🗑 Удалить город", callback_data=f"admin_city_delete:{city}")],
            [InlineKeyboardButton(text="📋 Список работ", callback_data=f"admin_jobs:{city}")],
            [InlineKeyboardButton(text="⬅ Назад к городам", callback_data="admin_back_to_city")]
        ])

    @staticmethod
    def admin_jobs(city: str, vacancies: list[dict]):
        buttons = []
        for i, v in enumerate(vacancies):
            buttons.append([InlineKeyboardButton(text=v["title"], callback_data=f"admin_job:{city}:{i}")])
        buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data=f"manage_city:{city}")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def admin_job_menu(city: str, index: int):
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✏️ Название", callback_data=f"admin_job_edit_title:{city}:{index}")],
            [InlineKeyboardButton(text="📝 Описание", callback_data=f"admin_job_edit_desc:{city}:{index}")],
            [InlineKeyboardButton(text="🔗 Ссылка", callback_data=f"admin_job_edit_url:{city}:{index}")],
            [InlineKeyboardButton(text="🗑 Удалить работу", callback_data=f"admin_job_delete:{city}:{index}")],
            [InlineKeyboardButton(text="⬅ Назад к работам", callback_data=f"admin_jobs:{city}")]
        ])

    @staticmethod
    def reply_start():
        return ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="Главное меню")]],
            resize_keyboard=True,
            one_time_keyboard=False
        )

    @staticmethod
    def reply_menu(has_admin_access: bool = False):
        if has_admin_access:
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

    # ===Меню распределения ролей===
    @staticmethod
    def roles_menu(is_dev: bool):
        buttons = [
            [InlineKeyboardButton(text="➕ Добавить админа", callback_data="role:add_admin")],
            [InlineKeyboardButton(text="➖ Удалить админа", callback_data="role:remove_admin")],
            [InlineKeyboardButton(text="👥 Список администраторов", callback_data="roles:list_admins")],
        ]
        if is_dev:
            buttons.extend([
                [InlineKeyboardButton(text="➕ Добавить супер админа", callback_data="role:add_sadmin")],
                [InlineKeyboardButton(text="➖ Удалить супер админа", callback_data="role:remove_sadmin")],
            ])
        buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="admin_back_to_city")])
        return InlineKeyboardMarkup(inline_keyboard=buttons)

    @staticmethod
    def dev_controls():
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Перезапустить", callback_data="dev:restart")],
            [InlineKeyboardButton(text="⏹ Остановить", callback_data="dev:stop")],
            [InlineKeyboardButton(text="⬅ Назад", callback_data="admin_back_to_city")],
        ])