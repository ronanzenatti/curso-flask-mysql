# run.py
from app import create_app

# Chama a nossa Application Factory para montar o servidor Flask
app = create_app()

if __name__ == "__main__":
    # O modo debug NÃO é escrito aqui: ele vem do .env (FLASK_DEBUG) via app.config["DEBUG"]
    app.run(host="127.0.0.1", port=5000)
