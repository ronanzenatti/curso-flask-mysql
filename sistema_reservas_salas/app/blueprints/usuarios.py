# app/blueprints/usuarios.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash
from app.database import query_all, query_one, transacao
from app.utils.security import permissao_obrigatoria, tem_permissao
from app.utils.pagination import obter_parametros_listagem, paginar_consulta
from app.utils.validacao import PADRAO_EMAIL, lista_de_inteiros

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

# Perfil básico "Solicitante": é o que recebe quem cadastra um usuário sem poder dar permissões
PERMISSOES_PADRAO_SOLICITANTE = ("salas.visualizar", "reservas.visualizar", "reservas.criar")


@usuarios_bp.route("/")
@permissao_obrigatoria("usuarios.visualizar")
def listar():
    busca, pagina, por_pagina = obter_parametros_listagem()
    status_filtro = request.args.get("ativo", "")

    sql = """
        SELECT u.id, u.nome, u.email, u.setor, u.cargo_etiqueta, u.ativo, u.criado_em,
               COUNT(up.permissao_id) AS total_permissoes
        FROM usuarios u
        LEFT JOIN usuario_permissoes up ON up.usuario_id = u.id
        WHERE 1=1
    """
    params = []

    if busca:
        sql += " AND (u.nome LIKE %s OR u.email LIKE %s OR u.setor LIKE %s OR u.cargo_etiqueta LIKE %s)"
        termo = f"%{busca}%"
        params.extend([termo, termo, termo, termo])

    if status_filtro in ("0", "1"):
        sql += " AND u.ativo = %s"
        params.append(int(status_filtro))

    sql += " GROUP BY u.id"

    paginacao = paginar_consulta(
        sql_base=sql,
        params=params,
        pagina=pagina,
        por_pagina=por_pagina,
        ordenacao="u.nome ASC",
    )

    return render_template(
        "usuarios/index.html",
        paginacao=paginacao,
        busca=busca,
        status_filtro=status_filtro,
    )


@usuarios_bp.route("/novo", methods=["GET", "POST"])
@permissao_obrigatoria("usuarios.gerenciar")
def criar():
    todas_permissoes = query_all("SELECT * FROM permissoes ORDER BY modulo, nome")
    # Só quem TAMBÉM tem 'usuarios.permissoes' pode escolher as permissões iniciais
    pode_definir_permissoes = tem_permissao("usuarios.permissoes")

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        setor = request.form.get("setor", "").strip()
        cargo_etiqueta = request.form.get("cargo_etiqueta", "").strip()

        erros = []
        if not nome or len(nome) > 120:
            erros.append("Informe o nome completo (até 120 caracteres).")
        if not PADRAO_EMAIL.match(email) or len(email) > 150:
            erros.append("Informe um e-mail válido (até 150 caracteres).")
        if len(senha) < 6 or len(senha) > 128:
            erros.append("A senha deve ter entre 6 e 128 caracteres.")
        if not setor or len(setor) > 80:
            erros.append("Informe o setor (até 80 caracteres).")
        if not cargo_etiqueta or len(cargo_etiqueta) > 60:
            erros.append("Informe a etiqueta de cargo (até 60 caracteres).")

        # O SERVIDOR decide quais permissões o novo usuário recebe (nunca confie só no formulário)
        if pode_definir_permissoes:
            ids_validos = {p["id"] for p in todas_permissoes}
            marcados = lista_de_inteiros(request.form.getlist("permissoes_ids"))
            permissoes_ids = sorted(marcados & ids_validos)
        else:
            permissoes_ids = [p["id"] for p in todas_permissoes if p["codigo"] in PERMISSOES_PADRAO_SOLICITANTE]

        if not erros and query_one("SELECT id FROM usuarios WHERE email = %s", (email,)):
            erros.append("Já existe um usuário cadastrado com este e-mail.")

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template(
                "usuarios/form.html", permissoes=todas_permissoes, dados=request.form,
                reenviado=True, pode_definir_permissoes=pode_definir_permissoes,
            )

        # Usuário + permissões na MESMA transação: ou grava tudo, ou não grava nada
        with transacao() as cursor:
            cursor.execute(
                """
                INSERT INTO usuarios (nome, email, senha_hash, setor, cargo_etiqueta, ativo)
                VALUES (%s, %s, %s, %s, %s, 1)
                """,
                (nome, email, generate_password_hash(senha), setor, cargo_etiqueta),
            )
            novo_id = cursor.lastrowid
            for pid in permissoes_ids:
                cursor.execute(
                    "INSERT INTO usuario_permissoes (usuario_id, permissao_id) VALUES (%s, %s)",
                    (novo_id, pid),
                )

        flash(f"Usuário '{nome}' criado com {len(permissoes_ids)} permissões!", "sucesso")
        return redirect(url_for("usuarios.listar"))

    return render_template(
        "usuarios/form.html", permissoes=todas_permissoes, dados=request.form,
        reenviado=False, pode_definir_permissoes=pode_definir_permissoes,
    )


@usuarios_bp.route("/<int:usuario_id>/permissoes", methods=["GET", "POST"])
@permissao_obrigatoria("usuarios.permissoes")
def gerenciar_permissoes(usuario_id):
    usuario = query_one("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    if not usuario:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("usuarios.listar"))

    todas_permissoes = query_all("SELECT * FROM permissoes ORDER BY modulo, nome")
    atuais = query_all(
        "SELECT permissao_id FROM usuario_permissoes WHERE usuario_id = %s",
        (usuario_id,),
    )
    ids_atuais = {linha["permissao_id"] for linha in atuais}

    if request.method == "POST":
        ids_validos = {p["id"] for p in todas_permissoes}
        novos_ids = lista_de_inteiros(request.form.getlist("permissoes_ids")) & ids_validos
        cargo_etiqueta = request.form.get("cargo_etiqueta", "").strip()
        ativo = 1 if request.form.get("ativo") == "1" else 0

        if not cargo_etiqueta or len(cargo_etiqueta) > 60:
            flash("Informe a etiqueta de cargo (até 60 caracteres).", "erro")
            return redirect(url_for("usuarios.gerenciar_permissoes", usuario_id=usuario_id))

        # Trava anti-autoexclusão: ninguém pode se trancar para fora do próprio painel
        if usuario_id == g.usuario["id"]:
            id_chave_mestra = next(p["id"] for p in todas_permissoes if p["codigo"] == "usuarios.permissoes")
            if ativo == 0 or id_chave_mestra not in novos_ids:
                flash(
                    "Por segurança, você não pode bloquear a sua própria conta "
                    "nem retirar de si a permissão 'usuarios.permissoes'.",
                    "aviso",
                )
                return redirect(url_for("usuarios.gerenciar_permissoes", usuario_id=usuario_id))

        # Só mexe no que mudou: assim o 'concedido_em' das permissões antigas é preservado
        para_remover = ids_atuais - novos_ids
        para_adicionar = novos_ids - ids_atuais

        with transacao() as cursor:
            cursor.execute(
                "UPDATE usuarios SET cargo_etiqueta = %s, ativo = %s WHERE id = %s",
                (cargo_etiqueta, ativo, usuario_id),
            )
            if para_remover:
                marcadores = ",".join(["%s"] * len(para_remover))
                cursor.execute(
                    f"DELETE FROM usuario_permissoes WHERE usuario_id = %s AND permissao_id IN ({marcadores})",
                    (usuario_id, *para_remover),
                )
            for pid in para_adicionar:
                cursor.execute(
                    "INSERT INTO usuario_permissoes (usuario_id, permissao_id) VALUES (%s, %s)",
                    (usuario_id, pid),
                )

        flash(f"Permissões personalizadas de {usuario['nome']} atualizadas com sucesso!", "sucesso")
        return redirect(url_for("usuarios.listar"))

    # Agrupa permissões por módulo para exibir em cards organizados no Tailwind CSS
    permissoes_por_modulo = {}
    for p in todas_permissoes:
        permissoes_por_modulo.setdefault(p["modulo"], []).append(p)

    return render_template(
        "usuarios/permissoes.html",
        usuario=usuario,
        permissoes_por_modulo=permissoes_por_modulo,
        ids_atuais=ids_atuais,
    )
