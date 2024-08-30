from loguru import logger

# укажите путь к файлу куда писать логи
logger.add('logs.log')

# укажите сколько профилей должно работать одновременно
workers = 1

# перемешивать ли профили перед началом работы
# True- перемешивать,  False - не перемешивать
shuffle_profiles = False

# укажите реферальный код
ref_code = ''

# укажите ключ от сервиса anti-captcha
anti_captcha_key = ''

