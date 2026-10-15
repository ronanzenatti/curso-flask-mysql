# app/blueprints/auth.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import check_password_hash
from app.database import query_one, query_all
from app.utils.security import (
    login_obrigatorio, caminho_seguro,
    login_bloqueado, registrar_falha_login, limpar_falhas_login,
)

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if g.usuario is not None:
        return redirect(url_for("index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")

        # Chave do "porteiro": mesmo computador (IP) tentando o mesmo e-mail
        chave_tentativas = f"{request.remote_addr}|{email}"
        if login_bloqueado(chave_tentativas):
            flash("Muitas tentativas incorretas. Aguarde 5 minutos e tente novamente.", "erro")
            return render_template("auth/login.html"), 429

        usuario = query_one(
            "SELECT id, nome, senha_hash, ativo FROM usuarios WHERE email = %s",
            (email,),
        )

        if usuario is None or not check_password_hash(usuario["senha_hash"], senha):
            registrar_falha_login(chave_tentativas)
            flash("E-mail ou senha inválidos. Verifique suas credenciais.", "erro")
        elif not usuario["ativo"]:
            flash("Sua conta está desativada. Contate o administrador.", "erro")
        else:
            limpar_falhas_login(chave_tentativas)
            session.clear()
            session["usuario_id"] = usuario["id"]
            flash(f"Bem-vindo(a), {usuario['nome']}!", "sucesso")
            proximo = caminho_seguro(request.args.get("proximo"))
            return redirect(proximo or url_for("index"))

    return render_template("auth/login.html")


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    flash("Você saiu do sistema com segurança.", "info")
    return redirect(url_for("auth.login"))


@auth_bp.route("/meu-perfil")
@login_obrigatorio
def meu_perfil():
    minhas_permissoes = query_all(
        """
        SELECT p.codigo, p.nome, p.modulo, p.descricao, up.concedido_em
        FROM permissoes p
        INNER JOIN usuario_permissoes up ON up.permissao_id = p.id
        WHERE up.usuario_id = %s
        ORDER BY p.modulo, p.nome
        """,
        (g.usuario["id"],),
    )
    return render_template("auth/perfil.html", permissoes=minhas_permissoes)
