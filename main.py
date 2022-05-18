import config
import telebot
from telebot import types
import datetime
import requests

bot = telebot.TeleBot(config.TOKEN)
user_dict = {}

gosAPI = None
cryptAPI = None
flag = True
ost = int(datetime.datetime.now().strftime("%H")) % 8


def updateApi():
    global cryptAPI, gosAPI, flag, ost
    dt = datetime.datetime.now()
    date = dt.strftime("%Y-%m-%d")
    time = int(dt.strftime("%H"))
    if (time % 8) == (ost + 1) % 8:
        flag = True
    if (time % 8 == ost and flag):
        config.internationalCurrencyAPI = f"https://api.apilayer.com/currency_data/change?start_date={date}&end_date={date}"
        flag = False
        gosAPI = requests.request("GET", config.internationalCurrencyAPI, headers=config.headers,
                                  data=config.payload).json()
        cryptAPI = requests.get(config.cryptoCurrencyAPI).json()


class Info:
    def __init__(self, id):
        # self.typeCurrency = None
        self.typeAction = None
        self.id = id
        self.money = None
        self.home_valute = None
        self.v_from = None
        self.v_to = None
        self.rate_from = None
        self.rate_to = None
        self.rate = None


@bot.message_handler(commands=['start'])
def start(message):
    user = Info(message.chat.id)
    user_dict[message.chat.id] = user

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    button_exchange = types.KeyboardButton("Перевести в другую валюту")
    button_rate = types.KeyboardButton("Узнать курс")
    markup.add(button_rate, button_exchange)
    msg = bot.send_message(message.chat.id,
                           "Привет! У меня есть 2 опции: узнать курс и перевести из одной валюты в другую.",
                           reply_markup=markup)
    bot.register_next_step_handler(msg, type_action)


def type_action(message):
    id = message.chat.id
    user_dict[id].typeAction = choose_action(message)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    button_RUBUSD = types.KeyboardButton("USD/RUB")
    button_RUBEUR = types.KeyboardButton("EUR/RUB")
    button_USDBTC = types.KeyboardButton("BTC/USD")
    button_USDETH = types.KeyboardButton("ETH/USD")
    button_BACK = types.KeyboardButton("Назад")
    markup.add(button_RUBUSD, button_RUBEUR, button_USDBTC, button_USDETH, button_BACK)
    msg = bot.send_message(message.chat.id,
                           "Выберите пару валют, если нужного соотношения не имеется то напишите через пробел, какие валюты вы хотели бы ввести",
                           reply_markup=markup)
    bot.register_next_step_handler(msg, values)


def values(message):
    if (message.text.lower() == "назад"):
        start(message)
    else:
        try:
            id = message.chat.id
            user = user_dict[id]
            if ("/" in message.text):
                text = message.text.split('/')
            else:
                text = message.text.split()
            user.v_from = text[0]
            user.v_to = text[1]
            updateApi()
            user.rate_from = find_value(user.v_from)
            user.rate_to = find_value(user.v_to)
            if (user.rate_from is None):
                msg = bot.send_message(message.chat.id, f"Нет валюты {user.v_from}")
                bot.register_next_step_handler(msg, values)
            if (user.rate_from is None):
                msg = bot.send_message(message.chat.id, f"Нет валюты {user.v_to}")
                bot.register_next_step_handler(msg, values)
            user.rate = user.rate_from / user.rate_to
            if (user.typeAction == "rate"):
                msg = bot.send_message(message.chat.id, user.v_from + '/' + user.v_to + ":" + (
                        "%.4f" % (user.rate_from / user.rate_to)) + "  ")
                bot.register_next_step_handler(msg, values)
            if (user.typeAction == "exchange"):
                msg = bot.send_message(message.chat.id,
                                       "Введите сумму денег, которую вы хотете перевести в " + user.v_to)
                bot.register_next_step_handler(msg, count)
        except:
            bot.register_next_step_handler(message, values)


def count(message):
    try:
        user = user_dict[message.chat.id]
        user.money = float(message.text)
        msg = bot.send_message(message.chat.id, "%.4f" % (user.money * user.rate))
        bot.register_next_step_handler(msg, values)
    except:
        bot.register_next_step_handler(message, values)


def find_value(name):
    global cryptAPI, gosAPI
    for coin in cryptAPI:
        if (coin['symbol'] == name):
            return float(coin['price_usd'])
    if ("USD" + name) in gosAPI['quotes']:
        return float(1 / gosAPI['quotes']["USD" + name]["start_rate"])
    return None


def choose_action(message):
    if ("перевести" in message.text.lower()):
        return "exchange"
    if ("узнать" in message.text.lower() or "курс" in message.text.lower()):
        return "rate"


bot.polling(none_stop=True)

