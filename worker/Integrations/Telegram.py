import asyncio
from telegram import Bot
import time
import pytz
ist = pytz.timezone('Asia/Kolkata')
from datetime import datetime

class Telegram:
    sent_messages = []
    MAX_MESSAGES_TO_STORE = 20

    async def send_telegram_message(self,user_id, message):
        bot = Bot(token='REMOVED_CREDENTIAL')
        await bot.send_message(chat_id=user_id, text=message)

    def send_message(self, user_id, message, identifier=""):
        timestamp = datetime.now(ist)
        sent_message_dict = {
            'to': user_id,
            'message': message,
            'identifier': identifier,
            'timestamp': timestamp
        }
        self.sent_messages.append(sent_message_dict)

        asyncio.run(self.send_telegram_message(user_id,message))

    def fetch_recent_messages(self):
        return self.sent_messages

# Integration code:
from Integrations.Telegram import Telegram
telegram = Telegram()

##Usage
# telegram.send_message(user_id, message, identifier)

## Fetch recent emails
# telegram.fetch_recent_messages()









