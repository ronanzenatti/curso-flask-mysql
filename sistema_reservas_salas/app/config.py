# app/config.py
import os
from dotenv import load_dotenv

# 1. Lê o arquivo .env da raiz do projeto e carrega seus valores na memória do sistema
load_dotenv()


# 2. Centraliza todas as configurações da aplicação em uma classe organizada
class Config:
    # Sem valor padrão de propósito: se esquecermos a chave, o sistema NÃO inicia (veja create_app)
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    # Modo de depuração controlado pelo .env ("1" liga, qualquer outra coisa desliga)
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "gestao_reservas_salas")
    ITEMS_PER_PAGE = 8
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
