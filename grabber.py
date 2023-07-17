from telethon import TelegramClient, events
import asyncio
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

my_channel_id = -1001977179457
channels = [-1001336550927]

# Access the environment variables using os.environ
api_id = int(os.environ.get("API_ID"))
api_hash = os.environ.get("API_HASH")

client = TelegramClient('myGrab', api_id, api_hash)
print("GRAB - Started")


@client.on(events.NewMessage(chats=channels))
async def my_event_handler(event):
    if event.message:
        await client.send_message(my_channel_id, event.message)


async def main():
    await client.start()
    print("GRAB - Running")
    await client.run_until_disconnected()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())
