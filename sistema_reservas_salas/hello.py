# hello.py
from flask import Flask
from markupsafe import escape

# 1. Criamos a instância da nossa aplicação Flask
app = Flask(__name__)


# 2. Rota Principal ("/") -> Retorna HTML simples para o navegador
@app.route("/")
def pagina_inicial():
    return """
    <h1>Olá, Mundo! Nosso servidor Flask está no ar! 🚀</h1>
    <p>Bem-vindo ao primeiro teste do sistema <strong>SalaFácil</strong>.</p>
    <ul>
        <li><a href="/sobre">Ver informações do sistema (Formato JSON)</a></li>
        <li><a href="/saudacao/Visitante">Testar rota dinâmica com parâmetro</a></li>
    </ul>
    """


# 3. Rota "/sobre" -> Retorna um Dicionário Python (O Flask converte para JSON!)
@app.route("/sobre")
def sobre_o_sistema():
    dados_do_projeto = {
        "sistema": "SalaFácil — Gestão de Reservas de Salas",
        "versao": "1.0-aula01",
        "tecnologias": ["Python", "Flask", "MySQL", "Tailwind CSS"],
        "servidor_ativo": True,
    }
    return dados_do_projeto


# 4. Rota Dinâmica com Variável na URL ("/saudacao/<nome>")
@app.route("/saudacao/<nome>")
def saudar_usuario(nome):
    return f"<h2>Olá, {escape(nome)}!</h2><p>O Flask capturou seu nome diretamente da barra de endereços!</p>"


# 5. Bloco de Inicialização do Servidor de Desenvolvimento
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
