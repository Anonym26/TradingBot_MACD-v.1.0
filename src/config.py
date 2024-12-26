import os
from dotenv import load_dotenv

# Загрузка .env файла
load_dotenv()

# Конфигурация API
API_KEY = os.getenv("BYBIT_API_KEY_TEST")
API_SECRET = os.getenv("BYBIT_API_SECRET_TEST")
USE_TESTNET = os.getenv("USE_TESTNET", "True") == "True"
