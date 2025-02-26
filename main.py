#👤
import os
from dotenv import load_dotenv

import asyncio
import logging

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# from api_token import API_TOKEN
from database import create_tables, add_contact, get_contacts, update_contact_username, delete_contact

# Загружаем переменные из .env
load_dotenv()

# Получаем токен из переменных среды
API_TOKEN = os.getenv("API_TOKEN")

if not API_TOKEN:
    raise ValueError("⚠️ Токен не найден! Убедись, что в файле .env есть API_TOKEN.")


logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher()


class AddUsername(StatesGroup):
    waiting_for_username = State()


class ContactForm(StatesGroup):
    last_name = State()
    first_name = State()
    phone_number = State()
    username = State()


# Машина состояний для поочередного запроса данных
main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Добавить контакт")],
        [KeyboardButton(text="Мои контакты")],
        [KeyboardButton(text="📎 Импорт контакта")]
    ],
    resize_keyboard=True
)

# Клавиатура отмены
cancel_keyboard = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="🚫 Отмена")]],
    resize_keyboard=True
)

# Вызываем создание таблиц при запуске
create_tables()


# Обработчик команды /start
@dp.message(Command("start"))
async def start(message: Message):
    await message.answer("Привет! Я бот для хранения контактов.\nВыберите действие:", reply_markup=main_keyboard)


# ✅ 1. Начало ввода контакта
@dp.message(F.text == "Добавить контакт")
async def add_contact_start(message: Message, state: FSMContext):
    await state.clear()  # Очищаем возможные прошлые состояния
    await state.set_state(ContactForm.last_name)
    await message.answer("Введите фамилию контакта:", reply_markup=cancel_keyboard)


# ✅ 2. Последовательный ввод данных
@dp.message(ContactForm.last_name)
async def process_last_name(message: Message, state: FSMContext):
    if message.text == "🚫 Отмена":
        return await cancel_add_contact(message, state)

    await state.update_data(last_name=message.text)
    await state.set_state(ContactForm.first_name)
    await message.answer("Теперь введите имя контакта:")


@dp.message(ContactForm.first_name)
async def process_first_name(message: Message, state: FSMContext):
    if message.text == "🚫 Отмена":
        return await cancel_add_contact(message, state)

    await state.update_data(first_name=message.text)
    await state.set_state(ContactForm.phone_number)
    await message.answer("Введите номер телефона контакта:")


@dp.message(ContactForm.phone_number)
async def process_phone_number(message: Message, state: FSMContext):
    if message.text == "🚫 Отмена":
        return await cancel_add_contact(message, state)

    await state.update_data(phone_number=message.text)
    await state.set_state(ContactForm.username)
    await message.answer("Введите ник в Telegram (если нет, напишите '-'):")


@dp.message(ContactForm.username)
async def process_username(message: Message, state: FSMContext):
    if message.text == "🚫 Отмена":
        return await cancel_add_contact(message, state)

    user_data = await state.get_data()

    last_name = user_data["last_name"]
    first_name = user_data["first_name"]
    phone_number = user_data["phone_number"]
    username = message.text if message.text != "-" else None

    add_contact(
        user_id=message.from_user.id,
        telegram_id=message.from_user.id,
        phone_number=phone_number,
        first_name=first_name,
        last_name=last_name,
        username=username
    )

    await message.answer(f"✅ Контакт сохранен!\n\n"
                         f"📞 {phone_number}\n"
                         f"👤 {first_name} {last_name or ''}\n"
                         f"🔗 {username if username else 'Нет ника'}",
                         reply_markup=main_keyboard)

    await state.clear()  # Завершаем процесс


# ✅ 3. Отмена ввода контакта
async def cancel_add_contact(message: Message, state: FSMContext):
    await state.clear()  # Полностью очищаем состояние
    await state.update_data({})  # Удаляем все данные, если были введены
    await message.answer("❌ Добавление контакта отменено.", reply_markup=main_keyboard)


# ✅ 4. Автоматический импорт контакта по 📎
@dp.message(F.text == "📎 Импорт контакта")
async def ask_for_contact(message: Message):
    await message.answer("Отправьте контакт через скрепку \n(📎 -> Контакт).")


@dp.message(F.contact)
async def import_contact(message: Message, state: FSMContext):
    contact = message.contact
    telegram_id = contact.user_id if contact.user_id else None

    # Сохраняем контакт без ника
    add_contact(
        user_id=message.from_user.id,
        telegram_id=telegram_id,
        phone_number=contact.phone_number,
        first_name=contact.first_name,
        last_name=contact.last_name if contact.last_name else None,
        username=None  # Ник пока пустой
    )

    # Создаем кнопку для добавления ника
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✏️ Добавить ник", callback_data=f"add_username_{contact.phone_number}")]
    ])

    await message.answer(f"✅ Контакт {contact.first_name} сохранен!\nХотите добавить ник?", reply_markup=keyboard)


@dp.callback_query(F.data.startswith("add_username_"))
async def ask_username(callback: types.CallbackQuery, state: FSMContext):
    phone_number = callback.data.split("_")[2]
    await state.update_data(phone_number=phone_number)

    await state.set_state(AddUsername.waiting_for_username)  # Устанавливаем состояние

    await callback.message.answer("Введите ник в формате @username:")
    await callback.answer()  # Закрываем инлайн-кнопку


@dp.message(AddUsername.waiting_for_username)
async def save_username(message: Message, state: FSMContext):
    data = await state.get_data()
    phone_number = data.get("phone_number")

    if not message.text.startswith("@"):
        return await message.answer("❌ Ник должен начинаться с @. Попробуйте снова.")

    # Обновляем контакт в базе
    update_contact_username(phone_number, message.text)

    await message.answer(f"✅ Ник {message.text} сохранен!")
    await state.clear()  # Сбрасываем состояние


# ✅ 5. Вывод списка контактов
@dp.message(F.text == "Мои контакты")
async def show_contacts(message: Message):
    contacts = get_contacts(message.from_user.id)

    if not contacts:
        await message.answer("❌ У вас пока нет сохраненных контактов.")
    else:
        response = "📜 *Ваши контакты:*\n"
        for i, (phone, first_name, last_name, username) in enumerate(contacts, 1):
            response += f"\n👤 {i}. {first_name} {last_name or ''}\n📞 {phone}\n"
            if username:
                response += f"🔗 {username}\n"

        # Кнопка для перехода к удалению
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить контакт", callback_data="start_delete_contact")]
        ])

        await message.answer(response, reply_markup=keyboard, parse_mode="Markdown")


@dp.callback_query(F.data == "start_delete_contact")
async def start_deleting_contacts(callback: types.CallbackQuery):
    contacts = get_contacts(callback.from_user.id)

    if not contacts:
        await callback.message.answer("❌ У вас нет контактов для удаления.")
        return

    await callback.message.answer("Выберите контакт для удаления:")

    # Отправляем каждый контакт с кнопкой удаления
    for phone, first_name, last_name, username in contacts:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_contact_{phone}")]
        ])

        text = (f"👤 {first_name} {last_name or ''}\n"
                f"📞 {phone}\n"
                f"🔗 {username if username else 'Нет ника'}")

        await callback.message.answer(text, reply_markup=keyboard)

    await callback.answer()  # Закрываем инлайн-кнопку


@dp.callback_query(F.data.startswith("delete_contact_"))
async def delete_contact_callback(callback: types.CallbackQuery):
    phone_number = callback.data.split("_")[2]

    delete_contact(phone_number, callback.from_user.id)

    await callback.message.edit_text("✅ Контакт удален!")  # Меняем текст контакта
    await callback.answer()  # Закрываем инлайн-кнопку


# Функция запуска бота
async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)


# Запуск бота
if __name__ == "__main__":
    asyncio.run(main())
