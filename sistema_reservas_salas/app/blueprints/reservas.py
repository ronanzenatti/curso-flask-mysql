# app/blueprints/reservas.py
from datetime import date
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from app.database import query_all, query_one, execute_write, transacao
from app.utils.security import permissao_obrigatoria, tem_permissao
from app.utils.pagination import obter_parametros_listagem, paginar_consulta
from app.utils.validacao import data_iso_valida, hora_valida, inteiro_no_intervalo

reservas_bp = Blueprint("reservas", __name__, url_prefix="/reservas")

STATUS_VALIDOS = ("pendente", "aprovada", "rejeitada", "cancelada")


def verificar_conflito_horario(sala_id, data_reserva, hora_inicio, hora_fim, ignorar_reserva_id=None):
    """Retorna a reserva conflitante caso haja sobreposição de horário na mesma sala e data."""
    sql = """
        SELECT r.id, r.titulo,
               TIME_FORMAT(r.hora_inicio, '%%H:%%i') AS inicio_fmt,
               TIME_FORMAT(r.hora_fim, '%%H:%%i') AS fim_fmt,
               u.nome AS solicitante
        FROM reservas r
        INNER JOIN usuarios u ON u.id = r.usuario_id
        WHERE r.sala_id = %s
          AND r.data_reserva = %s
          AND r.status IN ('pendente', 'aprovada')
          AND r.hora_inicio < %s
          AND r.hora_fim > %s
    """
    params = [sala_id, data_reserva, hora_fim, hora_inicio]
    if ignorar_reserva_id:
        sql += " AND r.id != %s"
        params.append(ignorar_reserva_id)

    return query_one(sql, tuple(params))


@reservas_bp.route("/")
@permissao_obrigatoria("reservas.visualizar")
def listar():
    busca, pagina, por_pagina = obter_parametros_listagem()
    status_filtro = request.args.get("status", "").strip()
    data_filtro = request.args.get("data", "").strip()
    if data_filtro and not data_iso_valida(data_filtro):
        data_filtro = ""  # data inventada na URL: ignora o filtro em vez de causar erro

    sql = """
        SELECT r.id, r.titulo, r.finalidade, r.data_reserva,
               TIME_FORMAT(r.hora_inicio, '%%H:%%i') AS hora_inicio_fmt,
               TIME_FORMAT(r.hora_fim, '%%H:%%i') AS hora_fim_fmt,
               r.participantes_estimados, r.status, r.usuario_id, r.observacoes,
               s.codigo AS sala_codigo, s.nome AS sala_nome, s.bloco AS sala_bloco,
               u.nome AS solicitante_nome, u.setor AS solicitante_setor,
               ap.nome AS aprovador_nome
        FROM reservas r
        INNER JOIN salas s ON s.id = r.sala_id
        INNER JOIN usuarios u ON u.id = r.usuario_id
        LEFT JOIN usuarios ap ON ap.id = r.aprovador_id
        WHERE 1=1
    """
    params = []

    if busca:
        sql += """
            AND (
                r.titulo LIKE %s
                OR r.finalidade LIKE %s
                OR s.codigo LIKE %s
                OR s.nome LIKE %s
                OR u.nome LIKE %s
                OR u.setor LIKE %s
            )
        """
        termo = f"%{busca}%"
        params.extend([termo, termo, termo, termo, termo, termo])

    if status_filtro in STATUS_VALIDOS:
        sql += " AND r.status = %s"
        params.append(status_filtro)

    if data_filtro:
        sql += " AND r.data_reserva = %s"
        params.append(data_filtro)

    paginacao = paginar_consulta(
        sql_base=sql,
        params=params,
        pagina=pagina,
        por_pagina=por_pagina,
        ordenacao="r.data_reserva DESC, r.hora_inicio ASC",
    )

    return render_template(
        "reservas/index.html",
        paginacao=paginacao,
        busca=busca,
        status_filtro=status_filtro,
        data_filtro=data_filtro,
    )


@reservas_bp.route("/nova", methods=["GET", "POST"])
@permissao_obrigatoria("reservas.criar")
def criar():
    salas_ativas = query_all("SELECT * FROM salas WHERE ativa = 1 ORDER BY codigo ASC")
    sala_pre_selecionada = request.args.get("sala_id", type=int)

    if request.method == "POST":
        sala_id = request.form.get("sala_id", 0, type=int) or 0
        titulo = request.form.get("titulo", "").strip()
        finalidade = request.form.get("finalidade", "").strip()
        data_reserva = request.form.get("data_reserva", "").strip()
        hora_inicio = request.form.get("hora_inicio", "").strip()
        hora_fim = request.form.get("hora_fim", "").strip()
        participantes = inteiro_no_intervalo(request.form.get("participantes_estimados"), 1, 5000)
        observacoes = request.form.get("observacoes", "").strip()

        # 1. Valida o formato e o sentido dos dados (ainda sem tocar no banco)
        erros = []
        if not titulo or len(titulo) > 150:
            erros.append("Informe o título do evento (até 150 caracteres).")
        if not finalidade or len(finalidade) > 255:
            erros.append("Informe a finalidade (até 255 caracteres).")
        if participantes is None:
            erros.append("O número de participantes deve ser um inteiro entre 1 e 5000.")
        if not data_iso_valida(data_reserva):
            erros.append("Informe uma data válida.")
        elif data_reserva < date.today().isoformat():
            erros.append("Não é permitido cadastrar reservas em datas passadas.")
        if not (hora_valida(hora_inicio) and hora_valida(hora_fim)):
            erros.append("Informe horários válidos de início e término.")
        elif hora_inicio >= hora_fim:
            erros.append("O horário de término deve ser posterior ao horário de início.")

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template(
                "reservas/form.html", salas=salas_ativas, sala_selecionada=sala_id, dados=request.form
            )

        # 2. Define o status inicial com base nas permissões personalizadas do usuário
        aprovacao_automatica = tem_permissao("reservas.aprovar")
        status_inicial = "aprovada" if aprovacao_automatica else "pendente"
        aprovador_id = g.usuario["id"] if aprovacao_automatica else None

        # 3. Confere sala, lotação e conflito E grava, tudo dentro de UMA transação com trava
        erro = None
        with transacao() as cursor:
            # Trava a linha da sala: se outra pessoa estiver reservando a MESMA sala agora, esperamos a vez
            cursor.execute(
                "SELECT id, codigo, capacidade FROM salas WHERE id = %s AND ativa = 1 FOR UPDATE",
                (sala_id,),
            )
            sala = cursor.fetchone()

            if not sala:
                erro = "A sala selecionada não está disponível."
            elif participantes > sala["capacidade"]:
                erro = (
                    f"A sala {sala['codigo']} comporta no máximo {sala['capacidade']} pessoas "
                    f"(você informou {participantes})."
                )
            else:
                conflito = verificar_conflito_horario(sala_id, data_reserva, hora_inicio, hora_fim)
                if conflito:
                    erro = (
                        f"Conflito de horário! Esta sala já está reservada das {conflito['inicio_fmt']} "
                        f"às {conflito['fim_fmt']} para '{conflito['titulo']}' ({conflito['solicitante']})."
                    )
                else:
                    cursor.execute(
                        """
                        INSERT INTO reservas (
                            sala_id, usuario_id, aprovador_id, titulo, finalidade,
                            data_reserva, hora_inicio, hora_fim, participantes_estimados,
                            status, observacoes
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            sala_id, g.usuario["id"], aprovador_id, titulo, finalidade,
                            data_reserva, hora_inicio, hora_fim, participantes,
                            status_inicial, observacoes,
                        ),
                    )

        if erro:
            flash(erro, "erro")
            return render_template(
                "reservas/form.html", salas=salas_ativas, sala_selecionada=sala_id, dados=request.form
            )

        msg = "Reserva cadastrada e aprovada automaticamente!" if aprovacao_automatica else "Solicitação enviada! Aguardando aprovação do gestor."
        flash(msg, "sucesso")
        return redirect(url_for("reservas.listar"))

    return render_template(
        "reservas/form.html", salas=salas_ativas, sala_selecionada=sala_pre_selecionada, dados=request.form
    )


@reservas_bp.route("/<int:reserva_id>/status", methods=["POST"])
@permissao_obrigatoria("reservas.visualizar")
def alterar_status(reserva_id):
    novo_status = request.form.get("novo_status", "")
    reserva = query_one("SELECT id, usuario_id, status FROM reservas WHERE id = %s", (reserva_id,))
    if not reserva:
        flash("Reserva não encontrada.", "erro")
        return redirect(url_for("reservas.listar"))

    # Aprovar ou rejeitar exige a permissão 'reservas.aprovar' E que a reserva ainda esteja PENDENTE
    if novo_status in ("aprovada", "rejeitada"):
        if not tem_permissao("reservas.aprovar"):
            flash("Você não possui a permissão 'reservas.aprovar'.", "erro")
            return redirect(url_for("reservas.listar"))

        linhas_afetadas = execute_write(
            "UPDATE reservas SET status = %s, aprovador_id = %s WHERE id = %s AND status = 'pendente'",
            (novo_status, g.usuario["id"], reserva_id),
        )
        if linhas_afetadas:
            flash(f"Reserva #{reserva_id} marcada como {novo_status.upper()}.", "sucesso")
        else:
            flash("Só é possível decidir reservas que ainda estão pendentes.", "aviso")

    # Cancelar permite ao próprio dono OU a quem tem 'reservas.cancelar_qualquer'
    elif novo_status == "cancelada":
        eh_dono = reserva["usuario_id"] == g.usuario["id"]
        if not (eh_dono or tem_permissao("reservas.cancelar_qualquer")):
            flash("Você só pode cancelar suas próprias reservas.", "erro")
            return redirect(url_for("reservas.listar"))

        linhas_afetadas = execute_write(
            "UPDATE reservas SET status = 'cancelada' WHERE id = %s AND status IN ('pendente', 'aprovada')",
            (reserva_id,),
        )
        if linhas_afetadas:
            flash(f"Reserva #{reserva_id} cancelada com sucesso.", "aviso")
        else:
            flash("Esta reserva já foi encerrada e não pode mais ser cancelada.", "aviso")

    else:
        flash("Ação inválida.", "erro")

    return redirect(url_for("reservas.listar"))
