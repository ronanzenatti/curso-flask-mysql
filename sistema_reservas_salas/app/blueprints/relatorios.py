# app/blueprints/relatorios.py
import csv
import io
from datetime import date, timedelta
from flask import Blueprint, render_template, request, Response, stream_with_context
from app.database import query_one, get_db
from app.utils.security import permissao_obrigatoria
from app.utils.pagination import paginar_consulta, validar_por_pagina
from app.utils.validacao import data_iso_valida, neutralizar_formula

relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")

STATUS_VALIDOS = ("pendente", "aprovada", "rejeitada", "cancelada")
LIMITE_IMPRESSAO = 500  # no modo de impressão, mostramos tudo em uma página só (até este limite)

# Trecho SQL compartilhado pela Tabela 2 (na tela) e pela exportação CSV: os dois sempre filtram igual
FROM_ANALITICO = """
    FROM reservas r
    INNER JOIN salas s ON s.id = r.sala_id
    INNER JOIN usuarios u ON u.id = r.usuario_id
    LEFT JOIN usuarios ap ON ap.id = r.aprovador_id
    WHERE r.data_reserva BETWEEN %s AND %s
"""


def _obter_periodo_padrao():
    hoje = date.today()
    inicio_padrao = (hoje - timedelta(days=30)).isoformat()
    fim_padrao = (hoje + timedelta(days=30)).isoformat()

    data_inicio = request.args.get("data_inicio", "").strip()
    data_fim = request.args.get("data_fim", "").strip()
    if not data_iso_valida(data_inicio):
        data_inicio = inicio_padrao
    if not data_iso_valida(data_fim):
        data_fim = fim_padrao
    if data_inicio > data_fim:
        data_inicio, data_fim = data_fim, data_inicio  # período invertido: troca as pontas
    return data_inicio, data_fim


def _filtros_analiticos(data_inicio, data_fim, busca, status):
    """Monta os filtros opcionais da Tabela 2. Devolve (trecho_sql, lista_de_parametros)."""
    sql = ""
    params = [data_inicio, data_fim]
    if busca:
        sql += """
            AND (
                r.titulo LIKE %s
                OR s.codigo LIKE %s
                OR s.nome LIKE %s
                OR u.nome LIKE %s
                OR u.setor LIKE %s
            )
        """
        termo = f"%{busca}%"
        params.extend([termo, termo, termo, termo, termo])
    if status in STATUS_VALIDOS:
        sql += " AND r.status = %s"
        params.append(status)
    return sql, params


def _responder_csv(nome_arquivo, cabecalho, sql, params, montar_linha):
    """Envia o CSV 'aos poucos' (streaming): o servidor não precisa guardar o arquivo inteiro na memória."""

    def gerar():
        conn = get_db()
        cursor = conn.cursor(dictionary=True)
        buffer = io.StringIO()
        escritor = csv.writer(buffer, delimiter=";")
        try:
            cursor.execute(sql, params)

            # Primeiro pedaço: assinatura UTF-8 BOM (para o Excel) + linha de cabeçalho
            buffer.write("﻿")
            escritor.writerow(cabecalho)
            yield buffer.getvalue()
            buffer.seek(0)
            buffer.truncate(0)

            # Demais pedaços: uma linha do banco por vez
            for linha in cursor:
                escritor.writerow([neutralizar_formula(campo) for campo in montar_linha(linha)])
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate(0)
        finally:
            cursor.close()

    return Response(
        stream_with_context(gerar()),
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{nome_arquivo}"'},
    )


@relatorios_bp.route("/")
@permissao_obrigatoria("relatorios.visualizar")
def painel():
    data_inicio, data_fim = _obter_periodo_padrao()
    imprimir = request.args.get("imprimir") == "1"

    # Parâmetros independentes para a Tabela 1 (Ocupação Consolidada por Sala)
    q_salas = "" if imprimir else request.args.get("q_salas", "").strip()
    pag_salas_num = max(1, request.args.get("page_salas", 1, type=int) or 1)
    por_pagina_salas = LIMITE_IMPRESSAO if imprimir else 5

    # Parâmetros independentes para a Tabela 2 (Auditoria Analítica de Reservas)
    q_analitico = request.args.get("q", "").strip()
    status_filtro = request.args.get("status", "").strip()
    pag_analitico_num = max(1, request.args.get("page", 1, type=int) or 1)
    por_pagina = LIMITE_IMPRESSAO if imprimir else validar_por_pagina()

    if imprimir:
        pag_salas_num = pag_analitico_num = 1

    # 1. KPIs Gerais do Período
    kpis = query_one(
        """
        SELECT
            COUNT(*) AS total_reservas,
            COALESCE(SUM(CASE WHEN status = 'aprovada' THEN 1 ELSE 0 END), 0) AS total_aprovadas,
            COALESCE(SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END), 0) AS total_pendentes,
            ROUND(
                COALESCE(
                    SUM(CASE WHEN status = 'aprovada' THEN TIMESTAMPDIFF(MINUTE, hora_inicio, hora_fim) ELSE 0 END) / 60.0,
                    0
                ),
                1
            ) AS total_horas
        FROM reservas
        WHERE data_reserva BETWEEN %s AND %s
        """,
        (data_inicio, data_fim),
    )

    # 2. Tabela 1 — Consolidado de Ocupação por Sala (Paginada e com Pesquisa Dinâmica)
    sql_salas = """
        SELECT
            s.id, s.codigo, s.nome, s.bloco, s.capacidade,
            COUNT(r.id) AS total_reservas,
            COALESCE(SUM(CASE WHEN r.status = 'aprovada' THEN 1 ELSE 0 END), 0) AS aprovadas,
            COALESCE(SUM(CASE WHEN r.status = 'cancelada' THEN 1 ELSE 0 END), 0) AS canceladas,
            ROUND(
                COALESCE(
                    SUM(CASE WHEN r.status = 'aprovada' THEN TIMESTAMPDIFF(MINUTE, r.hora_inicio, r.hora_fim) ELSE 0 END) / 60.0,
                    0
                ),
                1
            ) AS horas_ocupadas
        FROM salas s
        LEFT JOIN reservas r
            ON r.sala_id = s.id
           AND r.data_reserva BETWEEN %s AND %s
        WHERE 1=1
    """
    params_salas = [data_inicio, data_fim]
    if q_salas:
        sql_salas += " AND (s.codigo LIKE %s OR s.nome LIKE %s OR s.bloco LIKE %s)"
        termo_s = f"%{q_salas}%"
        params_salas.extend([termo_s, termo_s, termo_s])

    sql_salas += " GROUP BY s.id, s.codigo, s.nome, s.bloco, s.capacidade"

    paginacao_salas = paginar_consulta(
        sql_base=sql_salas,
        params=params_salas,
        pagina=pag_salas_num,
        por_pagina=por_pagina_salas,
        ordenacao="horas_ocupadas DESC, total_reservas DESC",
    )

    # 3. Tabela 2 — Relatório Analítico Detalhado (mesmos filtros usados na exportação CSV)
    filtros_sql, params_analitico = _filtros_analiticos(data_inicio, data_fim, q_analitico, status_filtro)
    sql_analitico = (
        """
        SELECT
            r.id, r.titulo, r.finalidade, r.data_reserva,
            TIME_FORMAT(r.hora_inicio, '%%H:%%i') AS inicio_fmt,
            TIME_FORMAT(r.hora_fim, '%%H:%%i') AS fim_fmt,
            TIMESTAMPDIFF(MINUTE, r.hora_inicio, r.hora_fim) AS duracao_min,
            r.participantes_estimados, r.status,
            s.codigo AS sala_codigo, s.nome AS sala_nome, s.bloco AS sala_bloco,
            u.nome AS solicitante_nome, u.setor AS solicitante_setor,
            COALESCE(ap.nome, '—') AS aprovador_nome
        """
        + FROM_ANALITICO
        + filtros_sql
    )

    paginacao_analitico = paginar_consulta(
        sql_base=sql_analitico,
        params=params_analitico,
        pagina=pag_analitico_num,
        por_pagina=por_pagina,
        ordenacao="r.data_reserva DESC, r.hora_inicio ASC",
    )

    return render_template(
        "relatorios/painel.html",
        data_inicio=data_inicio,
        data_fim=data_fim,
        imprimir=imprimir,
        kpis=kpis,
        q_salas=q_salas,
        paginacao_salas=paginacao_salas,
        q_analitico=q_analitico,
        status_filtro=status_filtro,
        paginacao_analitico=paginacao_analitico,
    )


@relatorios_bp.route("/exportar-csv")
@permissao_obrigatoria("relatorios.exportar")
def exportar_csv():
    data_inicio, data_fim = _obter_periodo_padrao()
    busca = request.args.get("q", "").strip()
    status = request.args.get("status", "").strip()

    filtros_sql, params = _filtros_analiticos(data_inicio, data_fim, busca, status)
    sql = (
        """
        SELECT
            r.id, r.data_reserva,
            TIME_FORMAT(r.hora_inicio, '%%H:%%i') AS inicio,
            TIME_FORMAT(r.hora_fim, '%%H:%%i') AS fim,
            s.codigo AS sala_codigo, s.nome AS sala_nome, s.bloco,
            r.titulo, r.finalidade, r.participantes_estimados,
            u.nome AS solicitante, u.setor,
            r.status, COALESCE(ap.nome, 'Pendente') AS aprovado_por
        """
        + FROM_ANALITICO
        + filtros_sql
        + " ORDER BY r.data_reserva DESC, r.hora_inicio ASC"
    )

    cabecalho = [
        "ID", "Data", "Início", "Término", "Código Sala", "Nome da Sala",
        "Bloco", "Evento", "Finalidade", "Participantes", "Solicitante",
        "Setor", "Status", "Aprovador",
    ]

    def montar_linha(l):
        return [
            l["id"], l["data_reserva"], l["inicio"], l["fim"],
            l["sala_codigo"], l["sala_nome"], l["bloco"],
            l["titulo"], l["finalidade"], l["participantes_estimados"],
            l["solicitante"], l["setor"], l["status"].upper(), l["aprovado_por"],
        ]

    nome_arquivo = f"relatorio_reservas_{data_inicio}_a_{data_fim}.csv"
    return _responder_csv(nome_arquivo, cabecalho, sql, tuple(params), montar_linha)
