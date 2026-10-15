# app/__init__.py
from flask import Flask, render_template, redirect, url_for, request
from app.config import Config
from app.database import init_db_app
from app.utils.security import (
    carregar_usuario_logado, validar_csrf,
    tem_permissao, obter_token_csrf, rota_inicial,
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY não definida. Crie o arquivo .env conforme a Aula 02.")

    # Inicializa o gerenciamento de conexão MySQL
    init_db_app(app)

    # Antes de cada request: 1º confere a ficha CSRF, 2º carrega o usuário e suas permissões
    app.before_request(validar_csrf)
    app.before_request(carregar_usuario_logado)

    # Torna estas funções acessíveis em qualquer template HTML
    @app.context_processor
    def injetar_utilitarios():
        # O nosso JavaScript avisa que é uma busca dinâmica com este cabeçalho
        requisicao_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        return {
            "tem_permissao": tem_permissao,
            "csrf_token": obter_token_csrf,
            "rota_inicial": rota_inicial,
            "layout": "base_parcial.html" if requisicao_ajax else "base.html",
        }

    # Páginas de erro amigáveis
    @app.errorhandler(403)
    def acesso_negado(erro):
        return render_template("auth/403.html"), 403

    @app.errorhandler(404)
    def nao_encontrado(erro):
        return render_template(
            "erro.html", codigo=404, titulo="Página não encontrada",
            mensagem="O endereço que você digitou não existe ou foi removido.",
        ), 404

    @app.errorhandler(500)
    def erro_interno(erro):
        # O Flask já grava o erro completo no terminal; o usuário vê só uma mensagem simples
        return render_template(
            "erro.html", codigo=500, titulo="Algo deu errado",
            mensagem="Tivemos um problema interno. Tente novamente em instantes.",
        ), 500

    # Registro dos Blueprints do sistema
    from app.blueprints.auth import auth_bp
    from app.blueprints.usuarios import usuarios_bp
    from app.blueprints.salas import salas_bp
    from app.blueprints.reservas import reservas_bp
    from app.blueprints.relatorios import relatorios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(salas_bp)
    app.register_blueprint(reservas_bp)
    app.register_blueprint(relatorios_bp)

    @app.route("/")
    def index():
        # Cada pessoa vai para a primeira página que tem permissão de abrir
        return redirect(url_for(rota_inicial()))

    return app
