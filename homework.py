import telegram
import requests
import os
import logging
import time
from dotenv import load_dotenv
from http import HTTPStatus

load_dotenv()

PRACTICUM_TOKEN = os.getenv('PR_TOKEN')
TELEGRAM_TOKEN = os.getenv('TG_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('CHAT_ID')


RETRY_PERIOD = 600
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}


logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler(stream='sys.stdout')
logger.addHandler(handler)


def check_tokens():
    """Проверка токенов окружения"""
    logging.info('Проверяем доступность переменных окружения.')
    return all((PRACTICUM_TOKEN, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID))


def send_message(bot, message):
    """Бот отправляет сообщения"""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.debug('сообщение успешно отправлено')
    except Exception as error:
        logging.error(f'Ошибка при отправке сообщения {error}', exc_info=True)


def get_api_answer(timestamp):
    """запрос к единственному эндпоинту"""
    timestamp = int(time.time())
    payload = {'from_date': timestamp}
    try:
        response = requests.get(ENDPOINT, headers=HEADERS, params=payload)
    except requests.exceptions.RequestException as error:
        send_report = (f'Error {error}')
        raise error(send_report)
    if response.status_code != HTTPStatus.OK:
        logging.error('Код ответ от сервера API не 200')
        raise ValueError('Код ответ от сервера API не 200')
    return response.json()


def check_response(response):
    """проверяет ответ API на соответствие документации"""
    if type(response) != dict:
        raise TypeError('получен список вместо ожидаемого словаря')
    if 'homeworks' not in response:
        raise KeyError('в ответе API домашки нет ключа')
    if type(response['homeworks']) != list:
        raise TypeError('данные приходят не в виде списка')
    homeworks = response.get('homeworks')
    return homeworks


def parse_status(homework):
    """извлекает из информации статус работы"""
    homework_name = homework.get('homework_name')
    status = homework.get('status')
    if status not in HOMEWORK_VERDICTS:
        logging.error('unknown status')
        raise KeyError('unknown status')
    if homework_name is None:
        logging.error('Unknown name')
        raise KeyError('Unknown name')
    verdict = HOMEWORK_VERDICTS[status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        logging.critical('Отсутсвуют переменные окружения')
        raise KeyError('Отсутсвуют переменные окружения')

    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    timestamp = int(time.time())
    while True:
        try:
            response = get_api_answer(timestamp)
            timestamp = response.get('current_date')
            homeworks = check_response(response)
            for homework in homeworks:
                homework_status = parse_status(homework)
                send_message(bot, homework_status)
            else:
                logging.debug('статус работы не изменился')

        except Exception as error:
            message = f'Сбой в работе программы: {error}'
            send_message(bot, message)
            raise error
        finally:
            time.sleep(RETRY_PERIOD)


if __name__ == '__main__':
    main()
