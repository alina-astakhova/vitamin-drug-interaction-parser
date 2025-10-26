"""
Конфигурационный файл для парсера Vitamin-Drug-Interactions-Parser (Drugs.com)

"""

# Настройки запросов
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Safari/537.36',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cookie': 'YOUR_ACTUAL_COOKIE_HERE'  # Замените на актуальную куку
}

# Настройки парсера
REQUEST_DELAY = (2, 4)  # Случайная задержка между запросами (min, max) в секундах
TRANSLATE_TO_RUSSIAN = True  # Включить/выключить перевод на русский
