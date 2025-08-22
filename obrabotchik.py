from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
from keyboards import Keyboards
from services import Jobservice
from urllib.parse import urlparse
import logging
import sys
import os

router = Router()
jobs_service = Jobservice()
logger = logging.getLogger(__name__)



async def resolve_to_user_id(text: str, bot) -> int | None:
    logger.debug("resolve_to_user_id: raw='%s'", text)
    value = text.strip()
    if not value:
        logger.debug("resolve_to_user_id: empty input")
        return None
    if value.startswith("@"):
        try:
            chat = await bot.get_chat(value)
            uid = int(chat.id)
            logger.debug("resolve_to_user_id: @ resolved username=%s -> uid=%d", value, uid)
            return uid
        except Exception as e:
            logger.warning("resolve_to_user_id: failed to resolve username=%s error=%s", value, e)
            return None
    try:
        uid = int(value)
        logger.debug("resolve_to_user_id: parsed uid=%d", uid)
        return uid
    except ValueError:
        logger.warning("resolve_to_user_id: invalid numeric value='%s'", value)
        return None

async def display_name(bot, uid: int) -> str:
    try:
        chat = await bot.get_chat(uid)
        if getattr(chat, "username", None):
            return f"@{chat.username}"
        if getattr(chat, "full_name", None):
            return f"{chat.full_name} ({uid})"
    except Exception:
        pass
    return str(uid)


async def send_new_and_delete(callback: CallbackQuery, text: str, reply_markup=None):
    new_msg = await callback.message.answer(text, reply_markup=reply_markup)
    try:
        await callback.message.delete()
    except TelegramBadRequest:
        pass
    return new_msg

class AddJob(StatesGroup):
    city_choise = State()
    new_city_name = State()
    title = State()
    desc = State()
    url = State()

class AdminEdit(StatesGroup):
    rename_city = State()
    edit_title = State()
    edit_desc = State()
    edit_url = State()

def is_admin(user_id: int) -> bool:
    return jobs_service.is_admin(user_id)

def is_super_admin(user_id: int) -> bool:
    return jobs_service.is_super_admin(user_id)

def is_developer(user_id: int) -> bool:
    return jobs_service.is_developer(user_id)

def has_admin_access(user_id: int) -> bool:
    return jobs_service.has_admin_access(user_id)


class RolesEdit(StatesGroup):
    add_admin = State()
    remove_admin = State()
    add_sadmin = State()
    remove_sadmin = State()


#==Пользователь==
@router.message(CommandStart())
async def start_cmd(message: Message):
    cities = jobs_service.get_cities()
    if not cities:
        return await message.answer("⚠ В базе пока нет городов.")
    await message.answer(
        "Главное меню",
        reply_markup=Keyboards.reply_menu(has_admin_access(message.from_user.id))
    )
    await message.answer("👋Здравствуйте! Это бот по поиску работы. Скорее выбирай город. Выберите город:", reply_markup=Keyboards.cities(cities))

@router.message(F.text.casefold() == "главное меню")
async def back_to_start(message: Message):
    await start_cmd(message)

@router.message(F.text.casefold() == "админка")
async def open_admin_panel(message: Message, state: FSMContext):
    if not has_admin_access(message.from_user.id):
        return await message.answer("⚠ У вас нет прав администратора.")
    await state.set_state(AddJob.city_choise)
    await message.answer(
        "📍 Выберите город или добавьте новый:",
        reply_markup=Keyboards.admin(
            jobs_service.get_cities(),
            can_manage_roles=(is_super_admin(message.from_user.id) or is_developer(message.from_user.id)),
            can_manage_bot=is_developer(message.from_user.id)
        )
    )

# == Админ: управление городом и работами ==
@router.callback_query(F.data.startswith("manage_city:"))
async def admin_manage_city(callback: CallbackQuery, state: FSMContext):
    if not has_admin_access(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    city = callback.data.split(":")[1]
    await state.update_data(city=city)
    await callback.message.edit_text(f"⚙️ Настройка города: {city}", reply_markup=Keyboards.admin_city_menu(city))
    await callback.answer()

@router.callback_query(F.data.startswith("admin_jobs:"))
async def admin_list_jobs(callback: CallbackQuery, state: FSMContext):
    if not has_admin_access(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    city = callback.data.split(":")[1]
    await state.update_data(city=city)
    vacancies = jobs_service.get_jobs(city)
    text = f"📋 Работы в городе: {city}"
    await callback.message.edit_text(text, reply_markup=Keyboards.admin_jobs(city, vacancies))
    await callback.answer()

@router.callback_query(F.data.startswith("admin_job:"))
async def admin_job_menu(callback: CallbackQuery, state: FSMContext):
    if not has_admin_access(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    _, city, idx = callback.data.split(":")
    index = int(idx)
    job = jobs_service.get_job(city, index)
    await state.update_data(city=city, index=index)
    text = f"💼 {job['title']}\n\n{job['desc']}\n\n🔗 {job.get('url','-')}"
    await callback.message.edit_text(text, reply_markup=Keyboards.admin_job_menu(city, index))
    await callback.answer()

@router.callback_query(F.data.startswith("admin_city_rename:"))
async def admin_city_rename_start(callback: CallbackQuery, state: FSMContext):
    if not has_admin_access(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    city = callback.data.split(":")[1]
    await state.update_data(city=city)
    await state.set_state(AdminEdit.rename_city)
    await send_new_and_delete(callback, f"✏️ Введите новое название для города '{city}':", reply_markup=Keyboards.admin_back_to_city())
    await callback.answer()

@router.message(AdminEdit.rename_city)
async def admin_city_rename_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    old_city = data.get("city")
    new_city = message.text.strip()
    if not new_city:
        return await message.answer("⚠ Название не может быть пустым")
    ok = jobs_service.rename_city(old_city, new_city)
    await state.clear()
    if not ok:
        return await message.answer("⚠ Не удалось переименовать (возможно, новое имя уже существует)")
    await message.answer(
        "✅ Город переименован",
        reply_markup=Keyboards.admin(
            jobs_service.get_cities(),
            can_manage_roles=(is_super_admin(message.from_user.id) or is_developer(message.from_user.id)),
            can_manage_bot=is_developer(message.from_user.id)
        )
    )

@router.callback_query(F.data.startswith("admin_city_delete:"))
async def admin_city_delete(callback: CallbackQuery, state: FSMContext):
    if not has_admin_access(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    city = callback.data.split(":")[1]
    ok = jobs_service.delete_city(city)
    text = "✅ Город удалён" if ok else "⚠ Не удалось удалить город"
    await state.set_state(AddJob.city_choise)
    await callback.message.edit_text(
        text,
        reply_markup=Keyboards.admin(
            jobs_service.get_cities(),
            can_manage_roles=(is_super_admin(callback.from_user.id) or is_developer(callback.from_user.id)),
            can_manage_bot=is_developer(callback.from_user.id)
        )
    )
    await callback.answer()

@router.callback_query(F.data.startswith("admin_job_edit_title:"))
async def admin_job_edit_title_start(callback: CallbackQuery, state: FSMContext):
    if not has_admin_access(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    _, city, idx = callback.data.split(":")
    await state.update_data(city=city, index=int(idx))
    await state.set_state(AdminEdit.edit_title)
    await send_new_and_delete(callback, "✏️ Введите новое название работы:", reply_markup=Keyboards.admin_back_to_desc())
    await callback.answer()

@router.message(AdminEdit.edit_title)
async def admin_job_edit_title_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    city = data["city"]
    index = int(data["index"])
    title = message.text.strip()
    jobs_service.update_job(city, index, title=title)
    await state.clear()
    await message.answer("✅ Название обновлено", reply_markup=Keyboards.admin_jobs(city, jobs_service.get_jobs(city)))

@router.callback_query(F.data.startswith("admin_job_edit_desc:"))
async def admin_job_edit_desc_start(callback: CallbackQuery, state: FSMContext):
    if not has_admin_access(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    _, city, idx = callback.data.split(":")
    await state.update_data(city=city, index=int(idx))
    await state.set_state(AdminEdit.edit_desc)
    await send_new_and_delete(callback, "📝 Введите новое описание:", reply_markup=Keyboards.admin_back_to_desc())
    await callback.answer()

@router.message(AdminEdit.edit_desc)
async def admin_job_edit_desc_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    city = data["city"]
    index = int(data["index"])
    desc = message.text.strip()
    jobs_service.update_job(city, index, desc=desc)
    await state.clear()
    await message.answer("✅ Описание обновлено", reply_markup=Keyboards.admin_jobs(city, jobs_service.get_jobs(city)))

@router.callback_query(F.data.startswith("admin_job_edit_url:"))
async def admin_job_edit_url_start(callback: CallbackQuery, state: FSMContext):
    if not has_admin_access(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    _, city, idx = callback.data.split(":")
    await state.update_data(city=city, index=int(idx))
    await state.set_state(AdminEdit.edit_url)
    await send_new_and_delete(callback, "🔗 Введите новую ссылку (http/https):", reply_markup=Keyboards.admin_back_to_desc())
    await callback.answer()

@router.message(AdminEdit.edit_url)
async def admin_job_edit_url_finish(message: Message, state: FSMContext):
    data = await state.get_data()
    city = data["city"]
    index = int(data["index"])
    url_text = message.text.strip()
    parsed = urlparse(url_text)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        return await message.answer("⚠ Некорректная ссылка. Введите корректный URL, начинающийся с http:// или https://")
    jobs_service.update_job(city, index, url=url_text)
    await state.clear()
    await message.answer("✅ Ссылка обновлена", reply_markup=Keyboards.admin_jobs(city, jobs_service.get_jobs(city)))

@router.callback_query(F.data.startswith("admin_job_delete:"))
async def admin_job_delete(callback: CallbackQuery, state: FSMContext):
    if not has_admin_access(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    _, city, idx = callback.data.split(":")
    index = int(idx)
    ok = jobs_service.delete_job(city, index)
    vacancies = jobs_service.get_jobs(city)
    text = "✅ Работа удалена" if ok else "⚠ Не удалось удалить работу"
    await callback.message.edit_text(text, reply_markup=Keyboards.admin_jobs(city, vacancies))
    await callback.answer()

@router.callback_query(F.data.startswith("city:"))
async def choose_city(callback: CallbackQuery):
    city = callback.data.split(":")[1]
    vacancies = jobs_service.get_jobs(city)
    if not vacancies:
        await callback.message.edit_text(
            f"📍 В городе {city} пока нет работ.",
            reply_markup=Keyboards.back("back:cities")
        )
    else:
        await callback.message.edit_text(f"📍 Город: {city}\nВыберите работу:",
                                        reply_markup=Keyboards.jobs(city, vacancies))
    await callback.answer()

@router.callback_query(F.data == "back:cities")
async def back_cities(callback: CallbackQuery):
    cities = jobs_service.get_cities()
    if not cities:
        await callback.message.edit_text("⚠ В базе пока нет городов.")
    else:
        await callback.message.edit_text("👋 Выберите город:", reply_markup=Keyboards.cities(cities))
    await callback.answer()


@router.callback_query(F.data.startswith("job:"))
async def choose_job(callback: CallbackQuery):
    _, city, index = callback.data.split(":")
    index = int(index)
    job = jobs_service.get_job(city, index)
    await callback.message.edit_text(f"💼 {job['title']}\n\n{job['desc']}",
                                    reply_markup=Keyboards.job_detail(city, index, job["url"]))
    await callback.answer()

# ==Навигация назад (пользователь)==
@router.callback_query(F.data == "back:cities")
async def back_to_cities(callback: CallbackQuery):
    cities = jobs_service.get_cities()
    if not cities:
        await callback.message.edit_text("⚠ В базе пока нет городов.")
    else:
        await callback.message.edit_text("👋 Выберите город:", reply_markup=Keyboards.cities(cities))
    await callback.answer()

@router.callback_query(F.data.startswith("back:jobs:"))
async def back_to_jobs(callback: CallbackQuery):
    _, _, city = callback.data.split(":")
    vacancies = jobs_service.get_jobs(city)
    await callback.message.edit_text(f"📍 Город: {city}\nВыберите работу:",
                                    reply_markup=Keyboards.jobs(city, vacancies))
    await callback.answer()


#==Админка через FSM(не знаешь не лезь)==
@router.message(F.text == "/addjob")
async def cmd_addjob(message: Message, state: FSMContext):
    if not has_admin_access(message.from_user.id):
        return await message.answer("⚠ У вас нет прав администратора.")
    await state.set_state(AddJob.city_choise)
    await message.answer(
        "📍 Выберите город или добавьте новый:",
        reply_markup=Keyboards.admin(
            jobs_service.get_cities(),
            can_manage_roles=(is_super_admin(message.from_user.id) or is_developer(message.from_user.id)),
            can_manage_bot=is_developer(message.from_user.id)
        )
    )

@router.callback_query(F.data.startswith("admin_city:"))
async def fsm_city(callback: CallbackQuery, state: FSMContext):
    city = callback.data.split(":")[1]
    if city == "new":
        await callback.message.answer(
            "✍ Введите название нового города:",
            reply_markup=Keyboards.admin_back_to_city()
        )
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
        await state.set_state(AddJob.new_city_name)
    else:
        await state.update_data(city=city)
        await callback.message.answer(f"Выбран город: {city}")
        await state.set_state(AddJob.title)
        await callback.message.answer("Введите название работы:", reply_markup=Keyboards.admin_back_to_city())
        try:
            await callback.message.delete()
        except TelegramBadRequest:
            pass
    await callback.answer()    

@router.message(AddJob.new_city_name)
async def fsm_new_city_name(message: Message, state: FSMContext):
    city = message.text.strip()
    jobs_service.add_city(city)
    await state.update_data(city=city)
    await message.answer(f"✅ Новый город '{city}' добавлен.")
    await state.set_state(AddJob.title)
    await message.answer("Введите название работы:", reply_markup=Keyboards.admin_back_to_city())

@router.message(AddJob.title)
async def fsm_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(AddJob.desc)
    await message.answer("📝 Введите описание работы:", reply_markup=Keyboards.admin_back_to_title())

@router.message(AddJob.desc)
async def fsm_desc(message: Message, state: FSMContext):
    await state.update_data(desc=message.text.strip())
    await state.set_state(AddJob.url)
    await message.answer("🔗 Введите ссылку на работу:", reply_markup=Keyboards.admin_back_to_desc())

@router.message(AddJob.url)
async def fsm_url(message: Message, state: FSMContext):
    url_text = message.text.strip()
    parsed = urlparse(url_text)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        await message.answer("⚠ Некорректная ссылка. Введите корректный URL, начинающийся с http:// или https://")
        return

    data = await state.get_data()
    city = data["city"]
    title = data["title"]
    desc = data["desc"]
    jobs_service.add_job(city, title, desc, url_text)
    await state.clear()
    await message.answer(f"✅ Вакансия добавлена!\n📍 {city}\n💼 {title}\n📝 {desc}\n🔗 {url_text}")

# === Управление ролями ===
@router.callback_query(F.data == "roles_menu")
async def open_roles_menu(callback: CallbackQuery):
    uid = callback.from_user.id
    if not (is_super_admin(uid) or is_developer(uid)):
        logger.warning("open_roles_menu: no permissions uid=%d", uid)
        return await callback.answer("Нет прав", show_alert=True)
    await callback.message.edit_text(
        "👤 Управление ролями",
        reply_markup=Keyboards.roles_menu(is_dev=is_developer(uid))
    )
    logger.debug("open_roles_menu shown to uid=%d", uid)
    await callback.answer()

@router.callback_query(F.data.startswith("role:"))
async def role_action_start(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split(":")[1]
    uid = callback.from_user.id
    if action in ("add_admin", "remove_admin"):
        if not (is_super_admin(uid) or is_developer(uid)):
            return await callback.answer("Нет прав", show_alert=True)
    elif action in ("add_sadmin", "remove_sadmin"):
        if not is_developer(uid):
            return await callback.answer("Нет прав", show_alert=True)

    mapping = {
        "add_admin": (RolesEdit.add_admin, "Введите @username или user_id для добавления в Админы:"),
        "remove_admin": (RolesEdit.remove_admin, "Введите @username или user_id для удаления из Админов:"),
        "add_sadmin": (RolesEdit.add_sadmin, "Введите @username или user_id для добавления в Супер Админы:"),
        "remove_sadmin": (RolesEdit.remove_sadmin, "Введите @username или user_id для удаления из Супер Админов:"),
    }
    state_to_set, prompt = mapping[action]
    await state.set_state(state_to_set)
    await send_new_and_delete(callback, f"{prompt}", reply_markup=Keyboards.admin_back_to_city())
    await callback.answer()


# == Список администраторов ==
@router.callback_query(F.data == "roles:list_admins")
async def list_admins(callback: CallbackQuery):
    uid = callback.from_user.id
    if not (is_super_admin(uid) or is_developer(uid)):
        logger.warning("list_admins: no permissions uid=%d", uid)
        return await callback.answer("Нет прав", show_alert=True)
    roles = jobs_service.roles
    logger.debug(
        "list_admins opened by uid=%d (admins=%d, sadmins=%d, devs=%d)",
        uid, len(roles.get("admins", [])), len(roles.get("super_admins", [])), len(roles.get("developers", []))
    )
    text = "👥 Выберите пользователя для управления ролями"
    all_ids = set(roles.get("admins", [])) | set(roles.get("super_admins", [])) | set(roles.get("developers", []))
    buttons = []
    for tid in sorted(all_ids):
        name = await display_name(callback.message.bot, tid)
        tags = []
        if tid in roles.get("admins", []):
            tags.append("Админ")
        if tid in roles.get("super_admins", []):
            tags.append("Супер-Админ")
        if tid in roles.get("developers", []):
            tags.append("Разработчик")
        tag_str = ",".join(tags)
        label = f"{name} — {tag_str}" if tag_str else name
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"roles:manage_user:{tid}")])
    buttons.append([InlineKeyboardButton(text="⬅ Назад", callback_data="roles_menu")])
    markup = InlineKeyboardMarkup(inline_keyboard=buttons if buttons else [[InlineKeyboardButton(text="⬅ Назад", callback_data="roles_menu")]])
    await callback.message.edit_text(text, reply_markup=markup)
    await callback.answer()


@router.callback_query(F.data.startswith("roles:manage_user:"))
async def manage_user(callback: CallbackQuery):
    actor = callback.from_user.id
    if not (is_super_admin(actor) or is_developer(actor)):
        logger.warning("manage_user: no permissions actor=%d data=%s", actor, callback.data)
        return await callback.answer("Нет прав", show_alert=True)
    target_id = int(callback.data.split(":")[2])
    logger.debug("manage_user: actor=%d target=%d", actor, target_id)
    await render_manage_user(callback.message, actor, target_id)
    await callback.answer()


@router.callback_query(F.data.startswith("roles:toggle:"))
async def toggle_role(callback: CallbackQuery):
    actor = callback.from_user.id
    _, _, role, uid_str = callback.data.split(":")
    target_id = int(uid_str)
    if role == "admin":
        if not (is_super_admin(actor) or is_developer(actor)):
            logger.warning("toggle_role: deny actor=%d role=%s target=%d", actor, role, target_id)
            return await callback.answer("Нет прав", show_alert=True)
        if jobs_service.is_admin(target_id):
            jobs_service.remove_admin(target_id)
            logger.info("toggle_role: removed admin actor=%d target=%d", actor, target_id)
        else:
            jobs_service.add_admin(target_id)
            logger.info("toggle_role: added admin actor=%d target=%d", actor, target_id)
    elif role == "sadmin":
        if not is_developer(actor):
            logger.warning("toggle_role: deny actor=%d role=%s target=%d", actor, role, target_id)
            return await callback.answer("Нет прав", show_alert=True)
        if jobs_service.is_super_admin(target_id):
            jobs_service.remove_super_admin(target_id)
            logger.info("toggle_role: removed sadmin actor=%d target=%d", actor, target_id)
        else:
            jobs_service.add_super_admin(target_id)
            logger.info("toggle_role: added sadmin actor=%d target=%d", actor, target_id)
    elif role == "dev":
        if not is_developer(actor):
            logger.warning("toggle_role: deny actor=%d role=%s target=%d", actor, role, target_id)
            return await callback.answer("Нет прав", show_alert=True)
        if jobs_service.is_developer(target_id):
            jobs_service.remove_developer(target_id)
            logger.info("toggle_role: removed dev actor=%d target=%d", actor, target_id)
        else:
            jobs_service.add_developer(target_id)
            logger.info("toggle_role: added dev actor=%d target=%d", actor, target_id)
    else:
        logger.error("toggle_role: unknown role=%s by actor=%d data=%s", role, actor, callback.data)
        return await callback.answer("Неизвестная роль", show_alert=True)

    await render_manage_user(callback.message, actor, target_id)
    await callback.answer()


async def render_manage_user(message: Message, actor: int, target_id: int):
    logger.debug("render_manage_user: actor=%d target=%d", actor, target_id)
    name = await display_name(message.bot, target_id)
    tags = []
    if jobs_service.is_admin(target_id):
        tags.append("Админ")
    if jobs_service.is_super_admin(target_id):
        tags.append("Супер Админ")
    if jobs_service.is_developer(target_id):
        tags.append("Разработчик")
    info = ", ".join(tags) if tags else "без ролей"
    text = f"👤 {name}\nТекущие роли: {info}"

    kb_rows = []
    if is_super_admin(actor) or is_developer(actor):
        if jobs_service.is_admin(target_id):
            kb_rows.append([InlineKeyboardButton(text="➖ Удалить из Админов", callback_data=f"roles:toggle:admin:{target_id}")])
        else:
            kb_rows.append([InlineKeyboardButton(text="➕ Добавить в Админы", callback_data=f"roles:toggle:admin:{target_id}")])

    if is_developer(actor):
        if jobs_service.is_super_admin(target_id):
            kb_rows.append([InlineKeyboardButton(text="➖ Удалить из Супер Админов", callback_data=f"roles:toggle:sadmin:{target_id}")])
        else:
            kb_rows.append([InlineKeyboardButton(text="➕ Добавить в Супер Админы", callback_data=f"roles:toggle:sadmin:{target_id}")])
        if jobs_service.is_developer(target_id):
            kb_rows.append([InlineKeyboardButton(text="➖ Удалить из Разработчиков", callback_data=f"roles:toggle:dev:{target_id}")])
        else:
            kb_rows.append([InlineKeyboardButton(text="➕ Добавить в Разработчики", callback_data=f"roles:toggle:dev:{target_id}")])
    kb_rows.append([InlineKeyboardButton(text="⬅ К списку", callback_data="roles:list_admins")])
    await message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb_rows))

@router.message(RolesEdit.add_admin)
async def add_admin_finish(message: Message, state: FSMContext):
    if not (is_super_admin(message.from_user.id) or is_developer(message.from_user.id)):
        return await message.answer("Нет прав")
    uid = await resolve_to_user_id(message.text, message.bot)
    if uid is None:
        return await message.answer("⚠ Укажите корректный @username или числовой user_id")
    jobs_service.add_admin(int(uid))
    await state.clear()
    await message.answer(
        "✅ Администратор добавлен",
        reply_markup=Keyboards.admin(
            jobs_service.get_cities(),
            can_manage_roles=(is_super_admin(message.from_user.id) or is_developer(message.from_user.id)),
            can_manage_bot=is_developer(message.from_user.id)
        )
    )

@router.message(RolesEdit.remove_admin)
async def remove_admin_finish(message: Message, state: FSMContext):
    if not (is_super_admin(message.from_user.id) or is_developer(message.from_user.id)):
        return await message.answer("Нет прав")
    uid = await resolve_to_user_id(message.text, message.bot)
    if uid is None:
        return await message.answer("⚠ Укажите корректный @username или числовой user_id")
    jobs_service.remove_admin(int(uid))
    await state.clear()
    await message.answer(
        "✅ Администратор удалён",
        reply_markup=Keyboards.admin(
            jobs_service.get_cities(),
            can_manage_roles=(is_super_admin(message.from_user.id) or is_developer(message.from_user.id)),
            can_manage_bot=is_developer(message.from_user.id)
        )
    )

@router.message(RolesEdit.add_sadmin)
async def add_sadmin_finish(message: Message, state: FSMContext):
    if not is_developer(message.from_user.id):
        return await message.answer("Нет прав")
    uid = await resolve_to_user_id(message.text, message.bot)
    if uid is None:
        return await message.answer("⚠ Укажите корректный @username или числовой user_id")
    jobs_service.add_super_admin(int(uid))
    await state.clear()
    await message.answer(
        "✅ Супер администратор добавлен",
        reply_markup=Keyboards.admin(
            jobs_service.get_cities(),
            can_manage_roles=(is_super_admin(message.from_user.id) or is_developer(message.from_user.id)),
            can_manage_bot=is_developer(message.from_user.id)
        )
    )

@router.message(RolesEdit.remove_sadmin)
async def remove_sadmin_finish(message: Message, state: FSMContext):
    if not is_developer(message.from_user.id):
        return await message.answer("Нет прав")
    uid = await resolve_to_user_id(message.text, message.bot)
    if uid is None:
        return await message.answer("⚠ Укажите корректный @username или числовой user_id")
    jobs_service.remove_super_admin(int(uid))
    await state.clear()
    await message.answer(
        "✅ Супер администратор удалён",
        reply_markup=Keyboards.admin(
            jobs_service.get_cities(),
            can_manage_roles=(is_super_admin(message.from_user.id) or is_developer(message.from_user.id)),
            can_manage_bot=is_developer(message.from_user.id)
        )
    )

# === Управление ботом (только разработчик) ===
@router.callback_query(F.data == "dev_menu")
async def dev_menu(callback: CallbackQuery):
    if not is_developer(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    await callback.message.edit_text("🛠 Управление ботом", reply_markup=Keyboards.dev_controls())
    await callback.answer()

@router.callback_query(F.data == "dev:restart")
async def dev_restart(callback: CallbackQuery):
    if not is_developer(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    await callback.message.answer("🔄 Перезапуск бота...")
    await callback.answer()
    try:
        os.execl(sys.executable, sys.executable, *sys.argv)
    except Exception:
        os._exit(0)

@router.callback_query(F.data == "dev:stop")
async def dev_stop(callback: CallbackQuery):
    if not is_developer(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    await callback.message.answer("⏹ Остановка бота...")
    await callback.answer()
    os._exit(0)

# === Логи и уровни логирования (только разработчик) ===
@router.callback_query(F.data == "dev:logs_tail")
async def dev_logs_tail(callback: CallbackQuery):
    if not is_developer(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    log_path = os.path.join(os.path.dirname(__file__), "logs", "bot.log")
    if not os.path.exists(log_path):
        return await callback.answer("Файл логов ещё не создан", show_alert=True)
    try:
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
        tail = "".join(lines[-200:])
        if len(tail) > 3500:
            tail = tail[-3500:]
        text = "Последние строки логов:\n" + ("```\n" + tail + "\n```")
        await callback.message.edit_text(text, reply_markup=Keyboards.dev_controls(), parse_mode="Markdown")
    except Exception as e:
        logger.exception("Failed to read logs: %s", e)
        await callback.answer("Не удалось прочитать логи", show_alert=True)

@router.callback_query(F.data == "dev:logs_download")
async def dev_logs_download(callback: CallbackQuery):
    if not is_developer(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    log_path = os.path.join(os.path.dirname(__file__), "logs", "bot.log")
    if not os.path.exists(log_path):
        return await callback.answer("Файл логов ещё не создан", show_alert=True)
    try:
        await callback.message.answer_document(FSInputFile(log_path), caption="Файл логов")
        await callback.answer()
    except Exception as e:
        logger.exception("Failed to send log file: %s", e)
        await callback.answer("Не удалось отправить файл логов", show_alert=True)

@router.callback_query(F.data == "dev:loglevel")
async def dev_loglevel(callback: CallbackQuery):
    if not is_developer(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    current_level = logging.getLevelName(logging.getLogger().level)
    await callback.message.edit_text(f"Текущий уровень логирования: {current_level}", reply_markup=Keyboards.log_levels(current_level))
    await callback.answer()

@router.callback_query(F.data.startswith("dev:loglevel:set:"))
async def dev_set_loglevel(callback: CallbackQuery):
    if not is_developer(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    level_name = callback.data.split(":")[-1].upper()
    if level_name not in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
        return await callback.answer("Неизвестный уровень", show_alert=True)
    lvl = getattr(logging, level_name)
    root = logging.getLogger()
    root.setLevel(lvl)
    logging.getLogger("aiogram").setLevel(max(logging.INFO, lvl))
    logger.info("Log level changed to %s by uid=%d", level_name, callback.from_user.id)
    await callback.message.edit_text(f"Уровень логирования установлен: {level_name}", reply_markup=Keyboards.log_levels(level_name))
    await callback.answer()

# ==Навигация назад (админ FSM)==
@router.callback_query(F.data == "admin_back_to_city")
async def admin_back_city(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddJob.city_choise)
    try:
        await callback.message.edit_text(
            "📍 Выберите город или добавьте новый:",
            reply_markup=Keyboards.admin(
                jobs_service.get_cities(),
                can_manage_roles=(is_super_admin(callback.from_user.id) or is_developer(callback.from_user.id)),
                can_manage_bot=is_developer(callback.from_user.id)
            )
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.answer()

@router.callback_query(F.data == "admin_back_to_title")
async def admin_back_title(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddJob.title)
    try:
        await callback.message.edit_text("Введите название работы:", reply_markup=Keyboards.admin_back_to_city())
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.answer()

@router.callback_query(F.data == "admin_back_to_desc")
async def admin_back_desc(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddJob.desc)
    try:
        await callback.message.edit_text("📝 Введите описание работы:", reply_markup=Keyboards.admin_back_to_title())
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.answer()

@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    try:
        await callback.message.edit_text(
            "📍 Выберите город или добавьте новый:",
            reply_markup=Keyboards.admin(jobs_service.get_cities())
        )
    except TelegramBadRequest as e:
        if "message is not modified" not in str(e).lower():
            raise
    await callback.answer()