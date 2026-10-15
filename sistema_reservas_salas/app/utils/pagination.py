# app/utils/pagination.py
import math
from flask import request, current_app
from app.database import query_one, query_all

VALORES_POR_PAGINA_PERMITIDOS = (5, 8, 10, 20, 50)


def validar_por_pagina(valor=None):
    """Garante que o número de registros por página seja um inteiro positivo válido."""
    padrao_por_pagina = current_app.config.get("ITEMS_PER_PAGE", 8)
    try:
        bruto = valor if valor is not None else request.args.get("per_page", padrao_por_pagina)
        por_pagina = int(bruto)
        if por_pagina not in VALORES_POR_PAGINA_PERMITIDOS:
            return padrao_por_pagina
        return por_pagina
    except (ValueError, TypeError):
        return padrao_por_pagina


def obter_parametros_listagem():
    """
    Extrai da query string (?q=...&page=...&per_page=...) os parâmetros
    padronizados usados em todas as tabelas do sistema.
    """
    busca = request.args.get("q", "").strip()
    try:
        pagina = max(1, int(request.args.get("page", 1)))
    except (ValueError, TypeError):
        pagina = 1

    por_pagina = validar_por_pagina()
    return busca, pagina, por_pagina


def paginar_consulta(sql_base, params=None, pagina=1, por_pagina=8, ordenacao=""):
    """
    Executa a contagem total e a busca paginada no MySQL a partir de uma query SQL base.
    Retorna um dicionário com os itens e todos os metadados de paginação.
    """
    parametros = list(params or [])
    por_pagina = max(1, int(por_pagina or 8))
    pagina = max(1, int(pagina or 1))

    # 1. Conta o total de registros que atendem ao filtro da pesquisa dinâmica
    sql_contagem = f"SELECT COUNT(*) AS total FROM ({sql_base}) AS subconsulta_total"
    resultado_total = query_one(sql_contagem, tuple(parametros))
    total_registros = resultado_total["total"] if resultado_total else 0

    total_paginas = max(1, math.ceil(total_registros / por_pagina))
    if pagina > total_paginas:
        pagina = total_paginas

    offset = (pagina - 1) * por_pagina

    # 2. Busca apenas a fatia (página) solicitada
    clausula_ordem = f" ORDER BY {ordenacao} " if ordenacao else " "
    sql_paginado = f"{sql_base}{clausula_ordem}LIMIT %s OFFSET %s"
    itens = query_all(sql_paginado, tuple(parametros + [por_pagina, offset]))

    inicio_item = offset + 1 if total_registros > 0 else 0
    fim_item = min(offset + por_pagina, total_registros)

    # 3. Calcula janela de páginas visíveis nos botões (ex: [1, 2, 3, 4, 5])
    inicio_janela = max(1, pagina - 2)
    fim_janela = min(total_paginas, pagina + 2)
    paginas_visiveis = list(range(inicio_janela, fim_janela + 1))

    return {
        "itens": itens,
        "pagina": pagina,
        "por_pagina": por_pagina,
        "total_registros": total_registros,
        "total_paginas": total_paginas,
        "tem_anterior": pagina > 1,
        "tem_proxima": pagina < total_paginas,
        "pagina_anterior": pagina - 1,
        "proxima_pagina": pagina + 1,
        "inicio_item": inicio_item,
        "fim_item": fim_item,
        "paginas_visiveis": paginas_visiveis,
    }
