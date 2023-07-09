import firebase_admin
from firebase_admin import credentials
from firebase_admin import db
import telebot
import random
import threading
import os

# Инициализируйте Firebase Admin SDK с нашими учетными данными
cred = credentials.Certificate(r"C:\Users\*********.json")
firebase_admin.initialize_app(cred, {
    'databaseURL': 'https://*************.firebasedatabase.app/'
})


TOKEN = "*******************"
bot = telebot.TeleBot(TOKEN)

# Подключение к Firebase Realtime Database
ref = db.reference('users')

# Запись данных в базу данных
#ref.child('chat_id').set('0')
#ref.child('city').set('Томск')

# Чтение данных из базы данных
user = ref.get()

# Определяем функцию find_user()
def get_user(chat_id):
    try:
        if chat_id:
            user = ref.child('users').child(str(chat_id)).get()
            return user
        else:
            return None
    except Exception as e:
        print(e)
        return None

# Регистрация пользователя в базе данных
def register_user(chat_id, city, interests):
    ref.child('users').child(str(chat_id)).set({"city": city, "chat_id": str(chat_id), "interests": interests})


# Поиск случайного пользователя по интересам
def find_random_user(interests, chat_id):
    users = ref.child('users').get()
    if not users:
        return None
    for user_id, user_data in users.items():
        if user_id != str(chat_id) and 'interests' in user_data and set(interests).intersection(set(user_data['interests'])):
            return user_data
    return None

# Поиск случайного пользователя без учета интересов и города
def find_random_user_without_filters(chat_id):

        users = ref.child('users').get()  # Получаем всех пользователей

        if not users:
            return None

        user_ids = list(users.keys())  # Получаем список всех user_id

        # Удаляем chat_id из списка user_id
        user_ids.remove(str(chat_id))

        if not user_ids:
            return None

        random_user_id = random.choice(user_ids)  # Выбираем случайного user_id

        random_user = users[random_user_id]  # Получаем данные случайного пользователя

        return random_user
# Обработка команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "Привет! Напиши свой город, чтобы найти новых друзей.")

    # Добавляем обработчик сообщения пользователя
    bot.register_next_step_handler(message, process_city_step)

    # Обработчик сообщения пользователя с городом


def process_city_step(message):
    chat_id = message.chat.id
    city = message.text
    bot.send_message(chat_id, "Теперь напиши свои интересы через запятую (например, спорт, кино, музыка).")

    # Добавляем обработчик сообщения пользователя
    bot.register_next_step_handler(message, process_interests_step, city)

    # Обработчик сообщения пользователя с интересами


def process_interests_step(message, city):
    chat_id = message.chat.id
    interests = [interest.strip() for interest in message.text.split(',')]
    register_user(chat_id, city, interests)
    bot.send_message(chat_id, f"Регистрация прошла успешно!\nГород: {city}\nИнтересы: {', '.join(interests)}")
    print(chat_id)
    bot.send_message(chat_id, f"для поиска случайного собеседника нажмите /random")
    bot.send_message(chat_id, f"для поиска собеседника по интересам нажмите /find")


# Обработка команды /random
@bot.message_handler(commands=['random'])
def find_random_user_command(message):
    chat_id = message.chat.id
    user = get_user(str(chat_id))
    if user is None:
        bot.send_message(chat_id, "Сначала зарегистрируйтесь с помощью команды /start.")
        return
    # Сохраняем chat_id пользователя, который ищет собеседника
    ref.child('users').child(str(chat_id)).update({"looking_for_user": True})

    # Ищем случайного пользователя без фильтров
    random_user = find_random_user_without_filters(chat_id)
    if random_user is None:
        bot.send_message(chat_id, "К сожалению, подходящих пользователей не найдено.")
    else:
        # Сохраняем chat_id обоих пользователей
        user_id = random_user['chat_id']
        ref.child('users').child(str(chat_id)).update({"interlocutor_id": user_id})
        ref.child('users').child(user_id).update({"interlocutor_id": str(chat_id)})

        # Предлагаем начать общение
        bot.send_message(chat_id, f"Найден подходящий пользователь с id {user_id}! Напишите /start_conversation, чтобы начать общение.")



# Обработка команды /start_conversation
@bot.message_handler(commands=['start_conversation'])
def start_conversation(message):
    chat_id = message.chat.id
    user = get_user(str(chat_id))
    if user is None:
        bot.send_message(chat_id, "Сначала зарегистрируйтесь с помощью команды /start.")
        return

    # Получаем chat_id собеседника
    interlocutor_id = user['interlocutor_id']

    # Регистрируем обработчик сообщений для общения двух пользователей
    bot.register_next_step_handler(message, lambda m: send_message_to_interlocutor(m, chat_id, interlocutor_id))

def send_message_to_interlocutor(message, chat_id, interlocutor_id):
    # Отправляем сообщение собеседнику
    bot.send_message(interlocutor_id, f"Сообщение от пользователя {chat_id}:\n{message.text}")



# Обработка команды /find
@bot.message_handler(commands=['find'])
def find_user(message):
    chat_id = message.chat.id
    user = get_user(chat_id)
    if user is None:
        bot.send_message(chat_id, "Сначала зарегистрируйтесь с помощью команды /start.")
        return
    interests = user.get('interests')
    if not interests:
        bot.send_message(chat_id, "Вы не указали свои интересы. Пожалуйста, укажите интересы с помощью команды /start.")
        return

    random_user = find_random_user(interests, chat_id)

    if random_user is None:
        bot.send_message(chat_id, "К сожалению, не удалось найти подходящего собеседника по интересам.")
        return

    random_user_id = random_user['chat_id']
    random_user_interlocutor_id = random_user.get('interlocutor_id')

    if random_user_interlocutor_id:
        bot.send_message(chat_id, "К сожалению, в данный момент все собеседники заняты. Попробуйте позже.")
    else:
        # Устанавливаем связь между пользователями
        ref.child('users').child(str(chat_id)).update({'interlocutor_id': random_user_id})
        ref.child('users').child(random_user_id).update({'interlocutor_id': str(chat_id)})

        bot.send_message(chat_id, "Вы успешно связаны с новым собеседником. Начинайте общение! (используйте /start_conversation !!)")
        bot.send_message(random_user_id, "Вы успешно связаны с новым собеседником. Начинайте общение! (используйте /start_conversation !!)")

# Обработка команды /help
@bot.message_handler(commands=['help'])
def start_conversation(message):
    chat_id = message.chat.id
    bot.send_message(chat_id, "/start - начало работы с ботом")
    bot.send_message(chat_id, "/find - поиск собеседника по вашим интересам")
    bot.send_message(chat_id, "/random - найти любого случайного собеседника")
    bot.send_message(chat_id, "/start_conversation - перед отправкой сообщения пользователю, используйте это")




# Запуск бота
if __name__ == '__main__':
    bot.polling()
