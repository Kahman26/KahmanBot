import sqlite3


# Функция для подключения к базе данных
def get_db_connection():
    conn = sqlite3.connect("contacts.db")
    return conn


# Функция для создания таблицы (вызываем при старте бота)
def create_tables():
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS contacts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        telegram_id INTEGER NOT NULL,
        phone_number TEXT NOT NULL,
        last_name TEXT,
        first_name TEXT,
        username TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    conn.commit()
    conn.close()


# Функция для добавления контакта
def add_contact(user_id, telegram_id, phone_number, first_name=None, last_name=None, username=None):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    INSERT INTO contacts (user_id, telegram_id, phone_number, first_name, last_name, username)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (user_id, telegram_id, phone_number, first_name, last_name, username))

    conn.commit()
    conn.close()


# Функция для получения всех контактов пользователя
def get_contacts(user_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT phone_number, first_name, last_name, username FROM contacts WHERE user_id=?", (user_id,))
    contacts = cursor.fetchall()

    conn.close()
    return contacts


import sqlite3


def update_contact_username(phone_number: str, username: str):
    conn = sqlite3.connect("contacts.db")
    cur = conn.cursor()

    cur.execute("""
        UPDATE contacts 
        SET username = ? 
        WHERE phone_number = ?
    """, (username, phone_number))

    conn.commit()
    conn.close()


def delete_contact(phone_number: str, user_id: int):
    conn = sqlite3.connect("contacts.db")
    cur = conn.cursor()

    cur.execute("""
        DELETE FROM contacts 
        WHERE phone_number = ? AND user_id = ?
    """, (phone_number, user_id))

    conn.commit()
    conn.close()


"""я сейчас пишу телеграм бота используя библиотеку aiogram. суть бота заключается в том, чтобы хранить внутри себя контакты телефонов. можешь написать код на питоне для базы данных sqlite3, чтобы были такие поля как: id пользователя, телеграм id пользователя, номер телефона контакта, фамилия, имя контакта, ник в телеграмме. если вдруг я забыл какие то важные поля, можешь их тоже добавить"""