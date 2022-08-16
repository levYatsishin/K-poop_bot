import json
import logging
from aiogram import Bot, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import Dispatcher
from aiogram.utils.executor import start_webhook
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.dispatcher import FSMContext
from datetime import timedelta

import os
import subprocess
import random

from sql_interface import db_select, db_create_new_row, db_update, db_row_exists, db_select_column
from sql_interface import db_path

root_dir = os.environ["root_dir"]
photo_dir = f"{root_dir}bands_photos"
API_TOKEN = os.environ["API_TOKEN"]
WEBHOOK_PATH = ""
WEBHOOK_URL = subprocess.check_output("curl -s localhost:4040/api/tunnels | jq -r .tunnels[0].public_url",
                                      shell=True).decode('utf-8')[:-1]
WEBAPP_HOST = '127.0.0.1'
WEBAPP_PORT = 5000

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())


def real_choice(l):
    random.shuffle(l)
    return l[random.randint(0, len(l)-1)]


lose_messages_1 = ["увы, ты не угадал((", "ты залажал(", " не-а(( близко, но"]
lose_messages_2 = [" это был <u>%s</u>", " его зовут <u>%s</u>", " на фото был <u>%s</u>"]
win_messages = ["ура!! ты угадал правильно", "молодец! это верно", "угадал! ты быстро учишься!",
                "правильно! можешь даже съесть за это печеньку"]
good_messages = ["у тебя все получится! не опускай руки", "ты справишься, я это знаю!", "ты очень красивый!"]

generate_win_message = lambda: real_choice(win_messages)
generate_lose_message = lambda name: real_choice(lose_messages_1) + real_choice(lose_messages_2) % name
generate_good_message = lambda: real_choice(good_messages)

str2button = lambda l: [KeyboardButton(x) for x in l]
nicknames = {"Stray Kids": "бродячие дети",
             "Lee Know": "минхо",
             "Han": "джисон",
             "I.N": "чонин",
             "Felix": "феликс",
             "Bang Chan": "чан",
             "Hyunjin": "хенджин",
             "Seungmin": "сынмин",
             "Changbin": "чанбин",
             "Jake": "джейк",
             "Sunoo": "сону",
             "Ni-ki": "ники",
             "Jay": "джей",
             "Heeseung": "хисын",
             "Jungwon": "чонвон",
             "Sunghoon": "сонхун",
             "Enhypen": "энхайпен"}
band_nicknames = {"Stray Kids": "бродячие дети",
                  "Enhypen": "энхайпен"}


def map_name(name: str) -> str:
    if name in nicknames.keys():
        return nicknames[name]
    elif name in nicknames.values():
        return {v: k for k, v in nicknames.items()}[name]
    else:
        return "ERROR"


def map_list_of_names(list_of_names: list) -> list:
    return [map_name(name) for name in list_of_names]


bands = ["Stray Kids", "Enhypen"]
bands_keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
    *str2button(map_list_of_names(bands))).add("📈 моя статистика")

band_members = {"stray_kids": ["Lee Know", "Han", "I.N", "Felix", "Bang Chan", "Hyunjin", "Seungmin", "Changbin"],
                "enhypen": ["Jake", "Sunoo", "Ni-ki", "Jay", "Heeseung", "Jungwon", "Sunghoon"]}


# states
class Form(StatesGroup):
    choose_band = State()
    learn = State()
    choose_guy = State()
    feedback = State()


def choose_member_and_create_keyboard(user_data):
    band = user_data["current_learning_band"]
    member = real_choice(band_members[band])

    mini_band = band_members[band][:]
    mini_band.remove(member)
    band_for_keyboard = list(random.sample(mini_band, 2))
    band_for_keyboard.append(member)
    random.shuffle(band_for_keyboard)

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=True).add(
        *str2button(map_list_of_names(band_for_keyboard))).add(KeyboardButton("выйти"))

    return member, keyboard


def generate_statistics(user_id):
    statistics = "ты правильно угадал: \n\n"

    for band in bands:
        members = "\n".join([f"☆{map_name(x[0])}: {x[1][1]} из {x[1][0]}"
                             if (round(x[1][1] * 0.4) >= x[1][0]-x[1][1]) and (x[1][0] >= 10)
                             else
                             f"{map_name(x[0])}: {x[1][1]} из {x[1][0]}"
                             for x in json.loads(db_select(user_id, band.lower().replace(" ", "_"))).items()])
        statistics += f"*{band}*\n{members}\n\n"

    statistics += "\nты увидишь красивую звёздочку ☆ рядом с хорошо запомнившимся мальчиками!"
    return statistics


@dp.message_handler(state=None)
async def start(message: types.Message):
    await Form.choose_band.set()
    await bot.send_message(message.chat.id, "приветик! кого ты хочешь запомнить?\n(секретные опции по кнопочке «меню»,"
                                            " слева от окошка ввода текста)", reply_markup=bands_keyboard, )
    if not db_row_exists(message.chat.id):
        name = "None" if not message.chat.first_name else message.chat.first_name
        username = "None" if not message.chat.username else message.chat.username

        db_create_new_row(message.chat.id, name, username)


@dp.message_handler(commands=['feel_better'], state="*")
async def get_statistics(message: types.Message):
    if message.chat.id == 186167695:
        with open(db_path, 'rb') as file:
            await bot.send_document(message.chat.id, ('db.sqlite', file))
            names = db_select_column("user_name")
            usernames = db_select_column("user_username")
            data = db_select_column("last_data")
            users = "\n".join([f"{x[0][0]} – @{x[1][0]} {x[2][0]}" if x[1][0] != "None"
                               else f"{x[0][0]} – no username {x[2][0]}"
                               for x in list(zip(names, usernames, data))])
            await bot.send_message(message.chat.id, users)
    else:
        reply = generate_good_message()
        path = f'{photo_dir}/cats/other'
        filename = real_choice(os.listdir(path))
        with open(f"{path}/{filename}", 'rb') as photo:
            await message.answer_photo(photo, caption=reply)


@dp.message_handler(commands=['spasibo'], state=Form.choose_band)
async def get_statistics(message: types.Message):
    await Form.feedback.set()
    await bot.send_message(message.chat.id, "можешь анонимно написать автору спасибо или просто что-то милое"
                                            "(только милое!!)\n\nесли ты злой или просто передумал нажимай /exit")


@dp.message_handler(state=Form.feedback)
async def feedback(message: types.Message):
    if message.text == "/exit":
        await bot.send_message(message.chat.id, "ничего! можешь писать, когда захочешь")
    else:
        await bot.send_message(message.chat.id, "переслал автору\n\nне знаю, что ты написал(не смотрю,"
                                                " чтобы не испортить анонимность) но даже мне приятно, спасибо!")
        await bot.send_message(186167695, f"пришел фидбек\n\n{message.text}")

    await bot.send_message(message.chat.id, f"кого хочешь поучить?", reply_markup=bands_keyboard)
    await Form.choose_band.set()


@dp.message_handler(state=Form.choose_band)
async def choose_band(message: types.Message, state: FSMContext):
    if message.text == "📈 моя статистика":
        await bot.send_message(message.chat.id, generate_statistics(message.chat.id), reply_markup=bands_keyboard,
                               parse_mode="markdown")
        await bot.send_message(message.chat.id, "а теперь за работу! совершенству нет предела\n(секретные опции"
                                                " по кнопочке «меню», слева от окошка ввода текста)",
                               reply_markup=bands_keyboard)
    elif message.text not in band_nicknames.values():
        await bot.send_message(message.chat.id, "я таких пока не знаю(( только этих", reply_markup=bands_keyboard)
    else:
        await bot.send_message(message.chat.id, "сейчас всё мигом выучишь!")
        await state.update_data(current_learning_band=map_name(message.text).lower().replace(" ", "_"))
        user_data = await state.get_data()

        #   choose member to learn and create keyboard
        member, keyboard = choose_member_and_create_keyboard(user_data)
        await state.update_data(current_learning_member=member)
        await state.update_data(keyboard=keyboard)

        #   send photo
        path = f'{photo_dir}/{user_data["current_learning_band"]}/{member.lower().replace(" ", "_")}'
        filename = real_choice(os.listdir(path))
        with open(f"{path}/{filename}", 'rb') as photo:
            await message.answer_photo(photo, caption='как ты думашь, кто это?', reply_markup=keyboard)

        await Form.choose_guy.set()


@dp.message_handler(state=Form.choose_guy)
async def start(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    chosen_member = message.text

    keyboard = user_data["keyboard"]
    member = user_data["current_learning_member"]
    band = user_data["current_learning_band"]

    if message.text == "/spasibo":
        await bot.send_message(message.chat.id, f"чтобы написать что-то милое автору, сначала нажми на ктопочку выйти."
                                                f" а пока продолжай угадывать красавчика выше", reply_markup=keyboard)

    #   exit to choose band
    elif message.text == 'выйти':
        await bot.send_message(message.chat.id, "окей, давай запоминать других!", reply_markup=bands_keyboard)
        await Form.choose_band.set()

    #   shit filter
    elif chosen_member not in nicknames.values():
        await bot.send_message(message.chat.id, f"ты странный(", reply_markup=keyboard)

    #   OK
    else:
        #   win. correct!
        if chosen_member == map_name(member):
            await bot.send_message(message.chat.id, generate_win_message())
            win = True

        #   lose. incorrect
        else:
            await bot.send_message(message.chat.id, generate_lose_message(map_name(member)), parse_mode='html')
            win = False

        old_user_data = json.loads(db_select(message.chat.id, band))
        old_user_data[member][0] += 1
        if win:
            old_user_data[member][1] += 1
        db_update(message.chat.id, band, json.dumps(old_user_data),
                  message.date + timedelta(hours=3))

        member, keyboard = choose_member_and_create_keyboard(user_data)
        await state.update_data(current_learning_member=member)
        await state.update_data(keyboard=keyboard)

        path = f'{photo_dir}/{user_data["current_learning_band"]}/{member.lower().replace(" ", "_")}'
        filename = real_choice(os.listdir(path))
        with open(f"{path}/{filename}", 'rb') as photo:
            await message.answer_photo(photo, caption='как ты думашь, кто это?', reply_markup=keyboard)

        await Form.choose_guy.set()
    return


async def on_startup(dp):
    await bot.set_webhook(WEBHOOK_URL)
    # insert code here to run it after start


async def on_shutdown(dp):
    logging.warning('Shutting down ..')
    # insert code here to run it before shutdown
    # Remove webhook(not acceptable in some cases)
    await bot.delete_webhook()
    # Close DB connection(if used)
    await dp.storage.close()
    await dp.storage.wait_closed()
    logging.warning('Bye!')


if __name__ == '__main__':
    start_webhook(
        dispatcher=dp,
        webhook_path=WEBHOOK_PATH,
        on_startup=on_startup,
        on_shutdown=on_shutdown,
        skip_updates=True,
        host=WEBAPP_HOST,
        port=WEBAPP_PORT,
    )
