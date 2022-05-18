import config
import telebot
from telebot import types
import datetime
import requests
from threading import Thread
import time

bot = telebot.TeleBot(config.TOKEN)
user_dict = {}

gosAPI = None
cryptAPI = None


class ThreadUpdate(Thread):
    def run(self):
        flag_for_API = False
        while True:
            global cryptAPI, gosAPI
            dt = datetime.datetime.now()
            date = dt.strftime("%Y-%m-%d")

            if flag_for_API:
                time.sleep(config.request_frequency)
            config.internationalCurrencyAPI = f"https://api.apilayer.com/currency_data/change?start_date={date}&end_date={date}"
            gosAPI = requests.request("GET", config.internationalCurrencyAPI, headers=config.headers,
                                      data=config.payload).json()
            cryptAPI = requests.get(config.cryptoCurrencyAPI).json()
            if flag_for_API:
                for id, user in user_dict.items():
                    if len(user.tracked_currency) != 0:
                        for currency, pair in user.tracked_currency.items():
                            newPrice = find_value(currency)
                            if abs(newPrice - pair[1]) > (float(pair[0]) * pair[1] / 100):
                                bot.send_message(id,
                                                 f"Валюта {currency} изменилась не менее, чем на {pair[0]}%!\n {currency}/USD: {'.4f' % newPrice}  ")
                                pair[1] = newPrice
            flag_for_API = True


thread_update = ThreadUpdate()
thread_update.start()


class Info:
    def __init__(self, id):
        self.typeAction = None
        self.action_tracked = None
        self.id = id
        self.money = None
        self.home_valute = None
        self.v_from = None
        self.v_to = None
        self.rate_from = None
        self.rate_to = None
        self.rate = None
        self.tracked_currency = dict()


@bot.message_handler(commands=['start'])
def start(message):
    user = Info(message.chat.id)
    user_dict[message.chat.id] = user

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    button_exchange = types.KeyboardButton("Перевести в другую валюту")
    button_rate = types.KeyboardButton("Узнать курс")
    button_tracked_currencies = types.KeyboardButton("Отслеживание валют")
    markup.add(button_rate, button_exchange, button_tracked_currencies)
    msg = bot.send_message(message.chat.id,
                           "Привет! У меня есть 3 опции: узнать курс и перевести из одной валюты в другую, и добавить отслеживание изменения курса валюты",
                           reply_markup=markup)
    bot.register_next_step_handler(msg, type_action)


def type_action(message):
    try:
        id = message.chat.id
        user_dict[id].typeAction = choose_action_from_main_menu(message)
        if user_dict[id].typeAction != "track":
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
        else:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
            button_ADD = types.KeyboardButton("Добавить валюту")
            button_DELETE = types.KeyboardButton("Удалить валюту")
            button_SHOW = types.KeyboardButton("Показать список отслеживаемых валют")
            button_BACK = types.KeyboardButton("Назад")
            markup.add(button_ADD, button_DELETE, button_SHOW, button_BACK)
            msg = bot.send_message(message.chat.id,
                                   "Вы хотите сделать: ",
                                   reply_markup=markup)
            bot.register_next_step_handler(msg, track)
    except:
        bot.register_next_step_handler(message, type_action)


def values(message):
    if message.text.lower() == "назад":
        start(message)
    else:
        try:
            tmp_flag = True
            id = message.chat.id
            user = user_dict[id]
            if ("/" in message.text):
                text = message.text.split('/')
            else:
                text = message.text.split()
            user.v_from = text[0]
            user.v_to = text[1]
            user.rate_from = find_value(user.v_from)
            user.rate_to = find_value(user.v_to)
            if user.rate_from is None:
                msg = bot.send_message(message.chat.id, f"Нет валюты {user.v_from}")
                bot.register_next_step_handler(msg, values)
                tmp_flag = False
            if user.rate_to is None:
                msg = bot.send_message(message.chat.id, f"Нет валюты {user.v_to}")
                bot.register_next_step_handler(msg, values)
                tmp_flag = False
            if tmp_flag:
                user.rate = user.rate_from / user.rate_to
                if user.typeAction == "rate":
                    msg = bot.send_message(message.chat.id, user.v_from + '/' + user.v_to + ":" + (
                            "%.4f" % (user.rate)) + "  ")
                    bot.register_next_step_handler(msg, values)
                elif user.typeAction == "exchange":
                    msg = bot.send_message(message.chat.id,
                                           "Введите сумму денег, которую вы хотете перевести в " + user.v_to)
                    bot.register_next_step_handler(msg, count)
                else:
                    bot.register_next_step_handler(message, track)
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


def track(message):
    if message.text.lower() == "назад":
        start(message)
    else:
        try:
            id = message.chat.id
            user = user_dict[id]
            user.action_tracked = choose_action_tracked_menu(message)
            if user.action_tracked == "add":
                msg = bot.send_message(message.chat.id,
                                       f"Введите сокращенное название валюты, которую хотите добавить и ту величину(в %) изменения курса валюты, при которой необходимо отправить уведомление")
                bot.register_next_step_handler(msg, add_currency)
            elif user.action_tracked == "delete":
                msg = bot.send_message(message.chat.id, f"Введите сокращенное название валюты, которую хотите удалить")
                bot.register_next_step_handler(msg, delete_currency)
            elif user.action_tracked == "show":
                if len(user.tracked_currency) == 0:
                    msg = bot.send_message(message.chat.id, "Нет отслеживаемых валют")
                    bot.register_next_step_handler(msg, track)
                else:
                    list_currency = ""
                    for currencies in user.tracked_currency.keys():
                        list_currency += currencies + '\n'
                    msg = bot.send_message(message.chat.id, list_currency)
                    bot.register_next_step_handler(msg, track)
            else:
                bot.register_next_step_handler(message, track)
        except:
            bot.register_next_step_handler(message, track)


def add_currency(message):
    try:
        id = message.chat.id
        user = user_dict[id]
        currency = message.text.split()[0]
        change = message.text.split()[1]
        price = find_value(currency)
        if find_value(currency) is None:
            msg = bot.send_message(message.chat.id, "Нет такой валюты")
            bot.register_next_step_handler(msg, track)
        else:
            user.tracked_currency[currency] = [change, price]
            msg = bot.send_message(message.chat.id, f"Валюта {currency} добавлена!")
            bot.register_next_step_handler(msg, track)
    except:
        bot.register_next_step_handler(message, track)


def delete_currency(message):
    try:
        id = message.chat.id
        user = user_dict[id]
        if message.text in user.tracked_currency:
            user.tracked_currency.pop(message.text)
            msg = bot.send_message(message.chat.id, f"Валюта {message.text} удалена из отслеживания")
            bot.register_next_step_handler(msg, track)
        else:
            msg = bot.send_message(message.chat.id, f"Валюта {message.text} и так не отслеживается")
            bot.register_next_step_handler(msg, track)
    except:
        bot.register_next_step_handler(message, track)


def find_value(name):
    global cryptAPI, gosAPI
    for coin in cryptAPI:
        if (coin['symbol'] == name):
            return float(coin['price_usd'])
    if ("USD" + name) in gosAPI['quotes']:
        return float(1 / gosAPI['quotes']["USD" + name]["start_rate"])
    return None


def choose_action_from_main_menu(message):
    if ("перевести" in message.text.lower()):
        return "exchange"
    if ("узнать" in message.text.lower() or "курс" in message.text.lower()):
        return "rate"
    if ("добавить" in message.text.lower() or "отслеживание" in message.text.lower()):
        return "track"


def choose_action_tracked_menu(message):
    if ("добавить" in message.text.lower()):
        return "add"
    if ("удалить" in message.text.lower()):
        return "delete"
    if ("показать" in message.text.lower() or "список" in message.text.lower()):
        return "show"


bot.polling(none_stop=True)

