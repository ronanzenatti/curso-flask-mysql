# app/blueprints/salas.py
from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.database import query_one, execute_write
from app.utils.security import permissao_obrigatoria
from app.utils.pagination import obter_parametros_listagem, paginar_consulta
from app.utils.validacao import PADRAO_CODIGO_SALA, inteiro_no_intervalo

salas_bp = Blueprint("salas", __name__, url_prefix="/salas")


def _ler_dados_formulario(exige_codigo):
    """Lê o formulário de sala, limpa os textos e confere as regras. Devolve (dados, erros)."""
    dados = {
        "codigo": request.form.get("codigo", "").strip().upper(),
        "nome": request.form.get("nome", "").strip(),
        "bloco": request.form.get("bloco", "").strip(),
        "recursos": request.form.get("recursos", "").strip(),
        "capacidade": inteiro_no_intervalo(request.form.get("capacidade"), 1, 2000),
    }
    erros = []
    if exige_codigo and not PADRAO_CODIGO_SALA.match(dados["codigo"]):
        erros.append("O código deve ter de 2 a 25 caracteres (letras, números e hífen), como LAB-104.")
    if not dados["nome"] or len(dados["nome"]) > 120:
        erros.append("Informe o nome da sala (até 120 caracteres).")
    if not dados["bloco"] or len(dados["bloco"]) > 60:
        erros.append("Informe o bloco/localização (até 60 caracteres).")
    if len(dados["recursos"]) > 255:
        erros.append("Os recursos podem ter no máximo 255 caracteres.")
    if dados["capacidade"] is None:
        erros.append("A capacidade deve ser um número inteiro entre 1 e 2000.")
    return dados, erros


@salas_bp.route("/")
@permissao_obrigatoria("salas.visualizar")
def listar():
    busca, pagina, por_pagina = obter_parametros_listagem()
    capacidade_min = request.args.get("capacidade_min", "").strip()

    sql = "SELECT * FROM salas WHERE 1=1"
    params = []

    if busca:
        sql += " AND (codigo LIKE %s OR nome LIKE %s OR bloco LIKE %s OR recursos LIKE %s)"
        termo = f"%{busca}%"
        params.extend([termo, termo, termo, termo])

    if capacidade_min.isdigit():
        sql += " AND capacidade >= %s"
        params.append(int(capacidade_min))

    paginacao = paginar_consulta(
        sql_base=sql,
        params=params,
        pagina=pagina,
        por_pagina=por_pagina,
        ordenacao="codigo ASC",
    )

    return render_template(
        "salas/index.html",
        paginacao=paginacao,
        busca=busca,
        capacidade_min=capacidade_min,
    )


@salas_bp.route("/nova", methods=["GET", "POST"])
@permissao_obrigatoria("salas.criar")
def criar():
    if request.method == "POST":
        dados, erros = _ler_dados_formulario(exige_codigo=True)

        if not erros and query_one("SELECT id FROM salas WHERE codigo = %s", (dados["codigo"],)):
            erros.append(f"Já existe uma sala cadastrada com o código {dados['codigo']}.")

        if erros:
            for erro in erros:
                flash(erro, "erro")
            # Devolve o formulário com o que a pessoa já tinha digitado (dados=request.form)
            return render_template("salas/form.html", sala=None, dados=request.form)

        execute_write(
            """
            INSERT INTO salas (codigo, nome, bloco, capacidade, recursos, ativa)
            VALUES (%s, %s, %s, %s, %s, 1)
            """,
            (dados["codigo"], dados["nome"], dados["bloco"], dados["capacidade"], dados["recursos"]),
        )
        flash(f"Sala {dados['codigo']} ({dados['nome']}) cadastrada com sucesso!", "sucesso")
        return redirect(url_for("salas.listar"))

    return render_template("salas/form.html", sala=None, dados=request.form)


@salas_bp.route("/<int:sala_id>/editar", methods=["GET", "POST"])
@permissao_obrigatoria("salas.editar")
def editar(sala_id):
    sala = query_one("SELECT * FROM salas WHERE id = %s", (sala_id,))
    if not sala:
        flash("Sala não encontrada.", "erro")
        return redirect(url_for("salas.listar"))

    if request.method == "POST":
        dados, erros = _ler_dados_formulario(exige_codigo=False)
        ativa = 1 if request.form.get("ativa") == "1" else 0

        # Reservas que ainda vão acontecer nesta sala (pendentes ou aprovadas)
        futuras = query_one(
            """
            SELECT COUNT(*) AS total, COALESCE(MAX(participantes_estimados), 0) AS maior_grupo
            FROM reservas
            WHERE sala_id = %s AND data_reserva >= CURDATE() AND status IN ('pendente', 'aprovada')
            """,
            (sala_id,),
        )
        if dados["capacidade"] is not None and dados["capacidade"] < futuras["maior_grupo"]:
            erros.append(
                f"Já existe reserva futura para {futuras['maior_grupo']} pessoas. "
                "A capacidade não pode ficar menor que isso."
            )

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template("salas/form.html", sala=sala, dados=request.form)

        execute_write(
            """
            UPDATE salas
            SET nome = %s, bloco = %s, capacidade = %s, recursos = %s, ativa = %s
            WHERE id = %s
            """,
            (dados["nome"], dados["bloco"], dados["capacidade"], dados["recursos"], ativa, sala_id),
        )
        if ativa == 0 and futuras["total"] > 0:
            flash(
                f"Atenção: {futuras['total']} reserva(s) futura(s) continuam ativas nesta sala. "
                "Avise os solicitantes.",
                "aviso",
            )
        flash(f"Sala {sala['codigo']} atualizada com sucesso!", "sucesso")
        return redirect(url_for("salas.listar"))

    return render_template("salas/form.html", sala=sala, dados=request.form)


@salas_bp.route("/<int:sala_id>/excluir", methods=["POST"])
@permissao_obrigatoria("salas.excluir")
def excluir(sala_id):
    sala = query_one("SELECT * FROM salas WHERE id = %s", (sala_id,))
    if not sala:
        flash("Sala não encontrada.", "erro")
        return redirect(url_for("salas.listar"))

    vinculo = query_one("SELECT COUNT(*) AS total FROM reservas WHERE sala_id = %s", (sala_id,))
    if vinculo and vinculo["total"] > 0:
        flash(
            f"A sala {sala['codigo']} possui {vinculo['total']} reserva(s) no histórico e não pode ser excluída. "
            "Altere o status dela para 'Em Manutenção / Inativa'.",
            "aviso",
        )
        return redirect(url_for("salas.listar"))

    execute_write("DELETE FROM salas WHERE id = %s", (sala_id,))
    flash(f"Sala {sala['codigo']} excluída com sucesso.", "sucesso")
    return redirect(url_for("salas.listar"))
