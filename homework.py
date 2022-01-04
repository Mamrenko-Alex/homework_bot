import logging
import os
import time

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    filename='main.log',
    level=logging.INFO,
)

PRACTICUM_TOKEN = os.getenv('TOKEN_PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 60 * 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения о изменении статуса."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info(
            'Сообщение успешно отправлено. '
            f'\nChat - {TELEGRAM_CHAT_ID} \nMessage - {message}'
        )
    except Exception:
        logging.error('Ошибка при отправке сообщения в телеграм')


def get_api_answer(current_timestamp):
    """Отправка запроса к API практикума."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    try:
        response = requests.get(
            ENDPOINT,
            headers=HEADERS,
            params=params
        )
    except Exception as error:
        logging.error(f'ENDPOINT недоступен - {error}')
    return response.json()


def check_response(response):
    """Проверка статуса домашнего задания."""
    try:
        list_homeworks = response['homeworks']
    except KeyError:
        logging.error('В словаре нет ключа \'homeworks\'')
    try:
        homework = list_homeworks[0]
    except IndexError:
        logging.error('Нет домашних работ за этот период')
    return homework


def parse_status(homework):
    """Извлекает статус о конкретной домашней работе."""
    try:
        homework_name = homework['homework_name']
    except KeyError:
        logging.error('В словаре нет ключа \'homework_name\'')
    try:
        homework_status = homework['status']
    except KeyError:
        logging.error('В словаре нет ключа \'status\'')
    if homework_status not in HOMEWORK_STATUSES:
        logging.error(
            'Недокументированный статус домашней работы'
        )
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия всех токенов."""
    if PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID:
        return True
    return False


def main():
    """Основная логика работы бота."""
    check_tokens()
    if check_tokens() is False:
        logging.critical(
            'Отсутствет одна или несоколько обязательных '
            'переменных окружения во время запуска бота'
        )
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(current_timestamp)
            current_timestamp = response.get('current_date')
            homework = check_response(response)
            message = parse_status(homework)
            send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logging.error(message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
