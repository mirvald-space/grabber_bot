import asyncio
import os
import pickle
import re
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Command
from aiogram.dispatcher.filters.state import State, StatesGroup
from dotenv import load_dotenv
from telethon.sync import TelegramClient
from telethon import events
from telethon.tl.types import InputMessagesFilterPhotos, MessageMediaPhoto, MessageMediaDocument

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)

# Telegram API credentials
api_id = os.getenv("API_ID")
api_hash = os.getenv("API_HASH")
bot_token = os.getenv("BOT_TOKEN")

# Initialize Telegram client and bot
client = TelegramClient('erwerber77', api_id, api_hash)
bot = Bot(token=bot_token)
dp = Dispatcher(bot)
dp.middleware.setup(LoggingMiddleware())

# Load channel data from pickle files
new_link = os.getenv("NEW_LINK")


class AuthState(StatesGroup):
    waiting_for_phone_number = State()
    waiting_for_code = State()


def load_channels(file_name):
    try:
        with open(file_name, 'rb') as f:
            return pickle.load(f)
    except FileNotFoundError:
        return set()


def save_channels(file_name, data):
    with open(file_name, 'wb') as f:
        pickle.dump(data, f)


# Channel sets
channels = load_channels('channels.pickle')
destination_channels = load_channels('destination_channels.pickle')

# Channel mapping dictionary
try:
    with open('channel_mapping.pickle', 'rb') as f:
        channel_mapping = pickle.load(f)
except FileNotFoundError:
    channel_mapping = {}


# Utility functions

def replace_link(text, new_link):
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    )
    return url_pattern.sub(new_link, text)


def replace_at_word(text, new_word):
    if not text:
        return text
    return re.sub(r'@(\w+)', new_word, text)


# Handler for sending media

async def send_media(message, destination_channel_id):
    if message.media and isinstance(message.media, (MessageMediaPhoto, MessageMediaDocument)):
        return await client.send_message(destination_channel_id, message.text, file=message.media.photo)
    else:
        return await client.send_message(destination_channel_id, message.text)


# Register event handlers

@client.on(events.NewMessage(chats=channels))
async def my_event_handler(event):
    if event.message.grouped_id:
        return

    original_text = event.message.text
    updated_text = replace_link(
        replace_at_word(original_text, "@test"), new_link)

    for destination_channel_id in destination_channels:
        if event.message.media:
            sent_message = await send_media(event.message, destination_channel_id)
        else:
            sent_message = await client.send_message(destination_channel_id, updated_text)


@client.on(events.Album(chats=channels))
async def album_event_handler(event):
    grouped_media = event.messages
    updated_texts = []
    media_list = []

    for message in grouped_media:
        original_text = message.text
        updated_text = replace_link(
            replace_at_word(original_text, "@test"), new_link)
        updated_texts.append(updated_text)
        media_list.append(message.media.photo)

    updated_caption = "\n".join([text for text in updated_texts if text])

    for destination_channel_id in destination_channels:
        await client.send_file(destination_channel_id, media_list, caption=updated_caption)


# Command handlers

@dp.message_handler(commands=['start'])
async def start(message: types.Message, state: FSMContext):
    await message.reply("Для авторизации, пожалуйста, отправьте свой номер телефона", reply_markup=types.ReplyKeyboardRemove())
    await AuthState.waiting_for_phone_number.set()


@dp.message_handler(state=AuthState.waiting_for_phone_number)
async def process_phone_number(message: types.Message, state: FSMContext):
    phone_number = message.text

    # Implement the logic to send SMS with the confirmation code to the provided phone number
    # You may need to use third-party services for sending SMS, such as Twilio

    await message.reply("Мы отправили вам SMS с кодом подтверждения. Пожалуйста, введите код из SMS", reply_markup=types.ReplyKeyboardRemove())
    await AuthState.waiting_for_code.set()
    await state.update_data(phone_number=phone_number)


@dp.message_handler(state=AuthState.waiting_for_code)
async def process_code(message: types.Message, state: FSMContext):
    code = message.text

    async with state.proxy() as data:
        phone_number = data['phone_number']

    # Implement the logic to verify the code that was sent to the user
    # For example, you can use Telethon methods to sign in with the provided phone number and code

    await client.sign_in(phone_number, code)

    await message.reply("Вы успешно авторизованы! Теперь вы можете использовать бота.", reply_markup=types.ReplyKeyboardRemove())
    await state.finish()


@dp.message_handler(commands=['help'])
async def help(message: types.Message):
    help_message = (
        "Список доступных команд:\n"
        "/start - Начало работы с ботом\n"
        "/help - Получить список доступных команд\n"
        "/add_channel - Добавить канал для работы\n"
        "/remove_channel - Удалить канал из списка\n"
        "/list_channels - Показать список добавленных каналов\n"
        "/add_destination_channel - Добавить канал-получатель\n"
        "/remove_destination_channel - Удалить канал-получатель из списка\n"
        "/list_destination_channels - Показать список каналов-получателей\n"
        "/set_channel_mapping - Установить соответствие между каналами\n"
        "/last_messages (ко-во сообщений или all, если все) - Отправить последние сообщения с каналов\n"
    )
    await message.reply(help_message)


# Add the AuthState class to handle the state

class AuthState(StatesGroup):
    waiting_for_phone_number = State()
    waiting_for_code = State()


async def main():
    await client.start()
    await client.connect()

    dp.register_message_handler(start, commands=['start'], commands_prefix='/')
    dp.register_message_handler(help, commands=['help'], commands_prefix='/')

    await dp.start_polling()
    await client.run_until_disconnected()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
