from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart
from aiogram.exceptions import TelegramBadRequest
from keyboards import Keyboards
from services import Jobservice
from urllib.parse import urlparse

router = Router()
jobs_service = Jobservice()


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


#==Пользователь==
@router.message(CommandStart())
async def start_cmd(message: Message):
    cities = jobs_service.get_cities()
    if not cities:
        return await message.answer("⚠ В базе пока нет городов.")
    await message.answer(
        "Главное меню",
        reply_markup=Keyboards.reply_menu(is_admin(message.from_user.id))
    )
    await message.answer("👋Здравствуйте! Это бот по поиску работы. Скорее выбирай город. Выберите город:", reply_markup=Keyboards.cities(cities))

@router.message(F.text.casefold() == "главное меню")
async def back_to_start(message: Message):
    await start_cmd(message)

@router.message(F.text.casefold() == "админка")
async def open_admin_panel(message: Message, state: FSMContext):
    if not is_admin(message.from_user.id):
        return await message.answer("⚠ У вас нет прав администратора.")
    await state.set_state(AddJob.city_choise)
    await message.answer(
        "📍 Выберите город или добавьте новый:",
        reply_markup=Keyboards.admin(jobs_service.get_cities())
    )

# == Админ: управление городом и работами ==
@router.callback_query(F.data.startswith("manage_city:"))
async def admin_manage_city(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    city = callback.data.split(":")[1]
    await state.update_data(city=city)
    await callback.message.edit_text(f"⚙️ Настройка города: {city}", reply_markup=Keyboards.admin_city_menu(city))
    await callback.answer()

@router.callback_query(F.data.startswith("admin_jobs:"))
async def admin_list_jobs(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    city = callback.data.split(":")[1]
    await state.update_data(city=city)
    vacancies = jobs_service.get_jobs(city)
    text = f"📋 Работы в городе: {city}"
    await callback.message.edit_text(text, reply_markup=Keyboards.admin_jobs(city, vacancies))
    await callback.answer()

@router.callback_query(F.data.startswith("admin_job:"))
async def admin_job_menu(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id):
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
    await message.answer("✅ Город переименован", reply_markup=Keyboards.admin(jobs_service.get_cities()))

@router.callback_query(F.data.startswith("admin_city_delete:"))
async def admin_city_delete(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
        return await callback.answer("Нет прав", show_alert=True)
    city = callback.data.split(":")[1]
    ok = jobs_service.delete_city(city)
    text = "✅ Город удалён" if ok else "⚠ Не удалось удалить город"
    await state.set_state(AddJob.city_choise)
    await callback.message.edit_text(text, reply_markup=Keyboards.admin(jobs_service.get_cities()))
    await callback.answer()

@router.callback_query(F.data.startswith("admin_job_edit_title:"))
async def admin_job_edit_title_start(callback: CallbackQuery, state: FSMContext):
    if not is_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id):
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
    if not is_admin(callback.from_user.id):
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
    if not is_admin(message.from_user.id):
        return await message.answer("⚠ У вас нет прав администратора.")
    await state.set_state(AddJob.city_choise)
    await message.answer("📍 Выберите город или добавьте новый:", reply_markup=Keyboards.admin(jobs_service.get_cities()))

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

# ==Навигация назад (админ FSM)==
@router.callback_query(F.data == "admin_back_to_city")
async def admin_back_city(callback: CallbackQuery, state: FSMContext):
    await state.set_state(AddJob.city_choise)
    try:
        await callback.message.edit_text(
            "📍 Выберите город или добавьте новый:",
            reply_markup=Keyboards.admin(jobs_service.get_cities())
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