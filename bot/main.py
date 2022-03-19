import telebot
import os
import config

bot = telebot.TeleBot(config.TOKEN)

@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    user = message.from_user
    bot.reply_to(message, f"Йоу {user.first_name}, как дела?")

# @bot.message_handler(func=lambda message: True) #on_message
# def echo_all(message):
#     bot.reply_to(message, message.text)

print(f'Бот запущен!')
bot.infinity_polling()
