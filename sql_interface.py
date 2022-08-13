import sqlite3
import json
import os

db_path = os.environ["db_path"]

conn = sqlite3.connect(db_path)
cursor = conn.cursor()


def create_table():
    cursor.execute('CREATE TABLE progress(user_id INTEGER, user_name TEXT, user_username TEXT,'
                   ' stray_kids TEXT, enhypen TEXT, last_data TEXT)')


def db_row_exists(user_id, table="progress"):
    #   True if exists False if not

    cursor.execute(f"SELECT 1 FROM {table} WHERE user_id = {user_id}")
    return True if len(cursor.fetchall()) >= 1 else False


def db_select(user_id, column, table="progress"):
    cursor.execute(f"SELECT {column} FROM {table} WHERE user_id = {user_id}")
    return cursor.fetchall()[0][0]


def db_select_column(column, table="progress"):
    cursor.execute(f"SELECT {column} FROM {table}")
    return cursor.fetchall()


def db_update(user_id, column, value, data, table="progress"):
    cursor.execute(f"UPDATE {table} SET {column} = ? WHERE user_id = {user_id}", (value,))
    cursor.execute(f"UPDATE {table} SET last_data = ? WHERE user_id = {user_id}", (data,))
    conn.commit()


def db_create_new_row(user_id, name, username, table="progress"):
    #   {MEMBER: [TOTAL_GUESSES, CORRECT_GUESSES], ...}

    zero_stray_kids_dict = {"Lee Know": [0, 0], "Han": [0, 0], "I.N": [0, 0], "Felix": [0, 0],
                            "Bang Chan": [0, 0], "Hyunjin": [0, 0], "Seungmin": [0, 0], "Changbin": [0, 0]}
    zero_enhypen_dict = {"Jake": [0, 0], "Sunoo": [0, 0], "Ni-ki": [0, 0], "Jay": [0, 0],
                         "Heeseung": [0, 0], "Jungwon": [0, 0], "Sunghoon": [0, 0]}

    zero_stray_kids_jsons = json.dumps(zero_stray_kids_dict)
    zero_enhypen_jsons = json.dumps(zero_enhypen_dict)

    cursor.execute(f"INSERT INTO {table} (user_id, stray_kids, enhypen, user_name, user_username) "
                   f"VALUES ({user_id}, ?, ?, ?, ?)", (zero_stray_kids_jsons, zero_enhypen_jsons, name, username))
    conn.commit()
