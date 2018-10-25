#--ignore
import telegram, telegram.ext
from src import utils

import json
from datetime import datetime
from threading import Thread

class Module(Thread):
    _name = "telegram"

    def on_load(self):
        key = self.bot.config.get("telegram-api-key")
        if not key: return

        self.updater = telegram.ext.Updater(key)
        self.dispatcher = self.updater.dispatcher

        start_handler = telegram.ext.CommandHandler("start", self.start)
        command_handler = telegram.ext.MessageHandler(
            telegram.ext.Filters.command, self.handle)
        self.dispatcher.add_handler(start_handler)
        self.dispatcher.add_handler(command_handler)

        self.updater.start_polling()

    def start(self, bot, update):
        bot.send_message(chat_id=update.message.chat_id, text="`Dolphin, but Telegram`", parse_mode="Markdown")

    def handle(self, bot, update):
        message, text = update.message, update.message.text
        text = text.replace("\r", '').replace("\n", " ")
        command = text.split(" ")[0][1:]
        command = command.split("@")[0]
        args = text.split(" ", 1)[1:][0] if " " in text else ""
        data = {
            "chat_id": message.chat_id,
            "message_id": message.message_id,
            "line": text,
            "command": command,
            "args": args,
            "args_split": text.split(" ")[1:],
            "stdout": IOWrapper(bot, message.chat_id, message.message_id),
            "stderr": IOWrapper(bot, message.chat_id, message.message_id),
            "external": True,
            }
        self.events.on("telegram.command").on(command).call(**data)

    @utils.hook("signal.interrupt")
    def sigint(self, event):
        self.updater.stop()

class IOWrapper:
    def __init__(self, bot, chat_id, message_id):
        self.bot = bot
        self.chat_id = chat_id
        self.message_id = message_id
    def write(self, text):
        if len(text)>4096-10:
            text = text[:4086] + "…"
        self.bot.send_message(chat_id=self.chat_id, text="```\n" + text + "\n```",
            reply_to_message_id=self.message_id, parse_mode="Markdown")
