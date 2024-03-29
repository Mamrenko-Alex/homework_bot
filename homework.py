import logging
import os
import time
from http import HTTPStatus
from logging.handlers import RotatingFileHandler

import requests
import telegram
from dotenv import load_dotenv

load_dotenv()

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    filename='main.log',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    'main.log',
    maxBytes=50000000,
    backupCount=5
)
logger.addFilter(handler)
formatter = logging.Formatter(
    '%(asctime)s %(levelname)s %(message)s'
)
handler.setFormatter(formatter)

PRACTICUM_TOKEN = os.getenv('TOKEN_PRACTICUM')
TELEGRAM_TOKEN = os.getenv('TOKEN_TELEGRAM')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')

RETRY_TIME = 60 * 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}

HOMEWORK_VERDIKTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


def send_message(bot, message):
    """Отправка сообщения о изменении статуса."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logger.info(
            'Сообщение успешно отправлено. '
            f'\nChat - {TELEGRAM_CHAT_ID} \nMessage - {message}'
        )
    except Exception:
        logger.error('Ошибка при отправке сообщения в телеграм')
        raise('Ошибка при отправке сообщения в телеграм')


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
        if response.status_code != HTTPStatus.OK:
            logger.error('Статус ответа response не равен 200. '
                         f'response.status_code={response.status_code}')
            raise Exception('ENDPOINT недоступен.'
                            f' Код ответа {response.status_code}')
    except Exception as error:
        logger.error(f'ENDPOINT недоступен - {error}')
        raise Exception('ENDPOINT недоступен.'
                        f'Код ответа {response.status_code}')
    try:
        return response.json()
    except Exception:
        logger.error('Ответ API не соответствует ожиданию')
        raise Exception('Ответ API не соответствует ожиданию')


def check_response(response):
    """Извлекает информацию о последней домашней работе."""
    try:
        list_homeworks = response['homeworks']
        homework = list_homeworks[0]
    except KeyError:
        logger.error('В словаре нет нужного ключа')
        raise KeyError('В словаре нет нужного ключа')
    except IndexError:
        logger.error('Список домашних работ пуст')
        raise IndexError('Список домашних работ пуст')
    return homework


def parse_status(homework):
    """Извлекает статус о конкретной домашней работе."""
    if 'homework_name' not in homework:
        raise KeyError('Отсутствует ключ homework_name')
    if 'status' not in homework:
        raise KeyError('Отсутствует ключ status')
    homework_name = homework['homework_name']
    homework_status = homework['status']
    try:
        verdict = HOMEWORK_VERDIKTS[homework_status]
    except KeyError:
        logger.error('Недокументированный статус домашней работы')
        raise Exception('Недокументированный статус домашней работы')
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка наличия всех токенов."""
    return PRACTICUM_TOKEN and TELEGRAM_TOKEN and TELEGRAM_CHAT_ID


def main():
    """Основная логика работы бота."""
    msg = ''
    msg_error = ''
    if not check_tokens():
        logger.critical(
            'Отсутствет одна или несоколько обязательных '
            'переменных окружения во время запуска бота'
        )
        raise Exception(
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
            if msg != message:
                msg = message
                send_message(bot, message)
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            logger.error(message)
            if msg_error != message:
                msg_error = message
                send_message(bot, message)
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    main()
