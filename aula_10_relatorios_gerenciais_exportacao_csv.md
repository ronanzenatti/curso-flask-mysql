# Aula 10 — Relatórios Gerenciais com Tailwind CSS, Paginação Dupla Independente e Exportação CSV

Chegamos à décima e última aula do nosso curso prático! Ao longo das **Aulas 01 a 09**, nós saímos de um simples `hello.py` e construímos um sistema corporativo completo: com arquitetura **Application Factory**, banco de dados **MySQL**, **13 permissões personalizadas**, login seguro, motor universal de paginação/busca dinâmica, **Catálogo de Salas**, **Matriz de Permissões de Usuários** e **Agenda de Reservas anti-conflito**.

Agora falta apenas a cereja do bolo para a direção e os gestores da instituição: o módulo de **Relatórios Gerenciais, Indicadores (KPIs) e Exportação de Dados** (`app/blueprints/relatorios.py` e `app/templates/relatorios/painel.html`).

Nesta **Aula 10**, você vai aprender técnicas avançadas que destacam qualquer desenvolvedor(a) no mercado:
1. Como fazer **Agregação Condicional no SQL** (`SUM(CASE WHEN ...)`, `COALESCE` e `ROUND`) para calcular indicadores em uma única consulta.
2. Como somar tempos com precisão decimal usando **`TIMESTAMPDIFF(MINUTE, ...) / 60.0`**.
3. O segredo do **`LEFT JOIN` com filtro no `ON`** para descobrir salas ociosas (que tiveram zero reservas no mês).
4. Como controlar **duas tabelas paginadas independentes na mesma tela** (`page_salas` vs. `page`).
5. Como gerar arquivos **CSV em *streaming*** (linha por linha, sem encher a memória do servidor) com assinatura **UTF-8 BOM (`﻿`)** para abrir com acentuação perfeita no Excel, protegidos contra **injeção de fórmulas**, além de preparar uma impressão limpa e completa com **`@media print`**.
6. Como escrever **testes automáticos** para as funções de segurança e validação, e o que mudar antes de **publicar** o sistema de verdade.

---

## 1. A Estrutura do Nosso Painel de Relatórios

O módulo de relatórios é protegido por duas chaves de permissão personalizadas:
* **`relatorios.visualizar`**: Permite abrir a tela `/relatorios/` e consultar os indicadores e tabelas.
* **`relatorios.exportar`**: Libera os botões **🖨️ Imprimir Relatório Completo** e **📥 Exportar CSV (Excel)**, que ficam junto dos filtros da Tabela 2.

Quando o gestor abre `/relatorios/`, a tela é dividida em **um seletor de período e 3 blocos analíticos**:

```text
+-----------------------------------------------------------------------------------+
| PERÍODO (recarrega a página): [ data_inicio ] [ data_fim ] [Aplicar período]      |
+-----------------------------------------------------------------------------------+
| [KPI 1: Solicitações]  [KPI 2: Aprovadas]  [KPI 3: Pendentes]  [KPI 4: Horas (h)] |
+-----------------------------------------------------------------------------------+
| TABELA 1: Desempenho e Ocupação Consolidada por Sala                              |
| Busca própria: [ q_salas ]                     Paginação própria: [ page_salas ]  |
+-----------------------------------------------------------------------------------+
| TABELA 2: Relatório Analítico de Auditoria de Reservas no Período                 |
| Busca própria: [ q ] [ status ]  Paginação: [ page ]  [Imprimir] [Exportar CSV]   |
+-----------------------------------------------------------------------------------+
```

---

## 2. Dominando as Consultas SQL Analíticas (Antes de Codificar!)

Antes de criarmos o arquivo `app/blueprints/relatorios.py`, vamos entender os quatro recursos de SQL que fazem os cálculos pesados diretamente dentro do servidor MySQL:

### 2.1 — Agregação Condicional: Como contar vários status em um único `SELECT`?
No topo do painel, queremos mostrar 4 cartões de indicadores (**KPIs** — *Key Performance Indicators*):
1. Total geral de solicitações no período;
2. Quantas estão **aprovadas**;
3. Quantas estão **pendentes**;
4. Total de **horas ocupadas** pelas reservas aprovadas.

Um programador iniciante faria **4 consultas `SELECT COUNT(*)` separadas** no banco de dados. Um programador profissional resolve tudo em **1 única viagem ao MySQL** combinando `SUM` com `CASE WHEN`:

```sql
COUNT(*) AS total_reservas,
COALESCE(SUM(CASE WHEN status = 'aprovada' THEN 1 ELSE 0 END), 0) AS total_aprovadas,
COALESCE(SUM(CASE WHEN status = 'pendente' THEN 1 ELSE 0 END), 0) AS total_pendentes
```

* **Como funciona o `SUM(CASE WHEN status = 'aprovada' THEN 1 ELSE 0 END)`?**  
  O MySQL passa linha por linha das reservas do período: se a linha for `'aprovada'`, o `CASE WHEN` vale **`1`**; se for qualquer outro status, vale **`0`**. Ao somar (`SUM`) todos esses `1` e `0`, temos exatamente o total de reservas aprovadas!

### 2.2 — Por que envolver o `SUM(...)` com `COALESCE(..., 0)`?
Imagine que o usuário filtre um período de férias em que há **0 reservas** no banco.
* No SQL, `COUNT(*)` de zero linhas devolve `0`. Porém, `SUM(...)` de zero linhas devolve **`NULL`** (`None` no Python)!
* Se não tratássemos isso, o cartão no HTML mostraria a palavra inglesa `None` em vez de `0`.
* A função **`COALESCE(valor, 0)`** significa: *"Se o resultado do cálculo for `NULL`, troque automaticamente por `0`!"*.

### 2.3 — Calculando Horas Exatas com `TIMESTAMPDIFF(MINUTE, ...)`
Na tabela `reservas`, temos `hora_inicio` (ex.: `'09:00:00'`) e `hora_fim` (ex.: `'10:30:00'`). Como descobrir quantas horas essa reserva durou?

```sql
ROUND(
    COALESCE(
        SUM(
            CASE WHEN r.status = 'aprovada'
            THEN TIMESTAMPDIFF(MINUTE, r.hora_inicio, r.hora_fim)
            ELSE 0 END
        ) / 60.0,
        0
    ),
    1
) AS horas_ocupadas
```

* **Por que pedimos a diferença em `MINUTE` (minutos) e dividimos por `60.0`, em vez de pedir direto em `HOUR` (horas)?**  
  Porque se uma reunião durou das `09:00` às `10:30` (1 hora e meia = **90 minutos**), `TIMESTAMPDIFF(HOUR, '09:00', '10:30')` cortaria a fração e devolveria apenas `1` hora!  
  Ao calcular em minutos (`90`) e dividir por `60.0`, obtemos **`1.5` horas** com precisão total! E a função `ROUND(..., 1)` arredonda o resultado final para 1 casa decimal (ex.: `4.5 h`).

### 2.4 — O Segredo do `LEFT JOIN` com Datas no `ON` (Para Mostrar Salas Ociosas!)
Na **Tabela 1 (Ocupação Consolidada por Sala)**, o diretor da instituição quer ver o ranking de uso de **todas as 10 salas** — inclusive aquelas que tiveram **`0` reservas** no mês (para saber quais salas estão subutilizadas!).

Observe com muita atenção onde colocamos o filtro `AND r.data_reserva BETWEEN %s AND %s` nesta consulta:

```sql
FROM salas s
LEFT JOIN reservas r
    ON r.sala_id = s.id
   AND r.data_reserva BETWEEN %s AND %s
WHERE 1=1
GROUP BY s.id, s.codigo, s.nome, s.bloco, s.capacidade
```

> ⚠️ **Por que `r.data_reserva BETWEEN %s AND %s` está dentro do `ON` do `LEFT JOIN` e NÃO no `WHERE`?**  
> * Se uma sala (como o `EST-501`) não teve nenhuma reserva no mês, o `LEFT JOIN` traz a sala preenchendo todas as colunas de `r` (`r.id`, `r.data_reserva`) com **`NULL`**.
> * Se você colocasse `WHERE r.data_reserva BETWEEN '2026-10-01' AND '2026-10-31'`, o MySQL testaria se `NULL` está entre essas datas. Como `NULL` falha no teste do `WHERE`, **todas as salas com 0 reservas seriam eliminadas do relatório**!
> * Ao colocar a condição de data dentro do **`ON` do `LEFT JOIN`**, o MySQL filtra as reservas do período **antes** de juntar com a sala, mantendo 100% das salas visíveis no relatório (exibindo `0` pedidos e `0.0 h` para as salas sem uso)!

---

## 3. Como Funcionam Duas Tabelas Paginadas na Mesma Tela?

Nas Aulas 07, 08 e 09, tínhamos apenas **uma** tabela por página. Mas no nosso Painel de Relatórios temos **duas tabelas paginadas** na mesma tela:
* **Tabela 1:** Ocupação Consolidada por Sala (`#container-relatorio-salas`)
* **Tabela 2:** Auditoria Analítica de Reservas (`#container-relatorio-analitico`)

### O que aconteceria se as duas tabelas usassem os mesmos nomes `name="q"` e `?page=`?
Se você estivesse na **página 2** da Tabela 1 e resolvesse clicar na **página 3** da Tabela 2, as duas leriam o mesmo parâmetro `?page=3` da URL e mudariam juntas! Pior: digitar o nome de um professor na busca da Tabela 2 tentaria filtrar as salas da Tabela 1 pelo nome do professor!

### Nossa Solução de Isolamento de Parâmetros:
Lembra que na Aula 06 programamos o `tabela_dinamica.js` para ler o atributo `data-page-param` do formulário (`const paramPagina = form.dataset.pageParam || "page"`)? Veja como separamos os parâmetros de cada tabela:

| Recurso | Tabela 1 (Ocupação por Sala) | Tabela 2 (Auditoria de Reservas) |
| :--- | :--- | :--- |
| **Container HTML (`data-target`)** | `#container-relatorio-salas` | `#container-relatorio-analitico` |
| **Campo de Busca (`name`)** | `name="q_salas"` | `name="q"` |
| **Parâmetro de Página (`data-page-param`)** | `data-page-param="page_salas"` | `data-page-param="page"` |
| **Exemplo na URL do Navegador** | `?q_salas=LAB&page_salas=2` | `&q=Beatriz&page=3` |

Como o `tabela_dinamica.js` parte sempre da URL atual (`new URL(window.location.href)`) e altera apenas os parâmetros do formulário que você mexeu, você pode estar na página 2 da Tabela 1 e paginar ou filtrar a Tabela 2 à vontade sem que a Tabela 1 perca a posição dela!

---

## 4. Codificando o Blueprint de Relatórios (`app/blueprints/relatorios.py`)

### 4.1 — Primeiro, mais uma ferramenta no `validacao.py`: proteção contra "injeção de fórmula"

#### Contextualização
Quando o gestor baixa o CSV e dá dois cliques, o **Excel interpreta cada célula**. Se uma célula começar com `=`, `+`, `-` ou `@`, o Excel entende que é uma **fórmula** e a executa!

> **Analogia do bilhete com ordem escondida:** imagine que cada pessoa pode deixar um bilhete na caixa de sugestões, e a secretária lê os bilhetes **em voz alta e cumpre qualquer ordem** que estiver escrita. Alguém pode escrever "`=HYPERLINK(...)`" como título de uma reserva, e quando o gestor abrir o relatório, o Excel vai obedecer. É o ataque de **CSV Injection**.

A defesa é simples: se um texto começar com um desses símbolos, colocamos um **apóstrofo (`'`) na frente**, que transforma o conteúdo em texto comum.

Acrescente **ao final** do arquivo `app/utils/validacao.py`:

```python
CARACTERES_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def neutralizar_formula(valor):
    """Evita 'injeção de fórmula' em planilhas: textos iniciados por = + - @ ganham um apóstrofo na frente."""
    if isinstance(valor, str) and valor.startswith(CARACTERES_DE_FORMULA):
        return "'" + valor
    return valor
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `CARACTERES_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")` | Uma tupla com os caracteres que o Excel considera "início de fórmula" (inclui tabulação e retorno de linha, usados em truques). | Lista única e fácil de revisar. | Teríamos de repetir os símbolos dentro do `if`. |
| `isinstance(valor, str)` | Pergunta: "isto é um texto?". | Números (`35`) e datas não são texto e não devem ser alterados. Em especial, números negativos como `-5` **não** devem ganhar apóstrofo. | Aplicar `.startswith` num número daria `AttributeError`. |
| `valor.startswith(CARACTERES_DE_FORMULA)` | Verdadeiro se o texto começa com **qualquer** um dos símbolos da tupla. | O método `startswith` aceita uma tupla de opções. | Nenhum texto perigoso seria detectado. |
| `return "'" + valor` | Devolve o texto com um apóstrofo na frente. | O apóstrofo faz o Excel tratar o conteúdo como texto literal, sem executar nada. | Um título como `=HYPERLINK("http://site-falso.com","clique")` viraria um link clicável dentro da planilha do gestor. |
| `return valor` | Devolve o valor sem mudanças. | A grande maioria dos campos é inofensiva. | A função devolveria `None` e as células ficariam vazias. |

### 4.2 — O Blueprint completo

Abra o arquivo **`app/blueprints/relatorios.py`** (substituindo o esqueleto provisório da Aula 05) e digite o código completo abaixo:

```python
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
```

### 4.3 — Linha por linha das novidades do `relatorios.py`

#### Imports e constantes

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `import csv` e `import io` | `csv` escreve linhas no formato de planilha; `io.StringIO` é um "arquivo de mentirinha" na memória. | Base da exportação. | `NameError` na rota de exportação. |
| `from flask import ..., Response, stream_with_context` | `Response` monta a resposta HTTP manualmente; `stream_with_context` mantém a requisição "viva" enquanto enviamos o arquivo aos poucos. | Necessários para o streaming. | Sem o `stream_with_context`, o banco de dados e a sessão deixam de estar disponíveis no meio do envio e dá erro. |
| `from app.database import query_one, get_db` | `query_one` para os KPIs; `get_db` para o cursor do streaming. | O streaming precisa controlar o cursor diretamente. | `ImportError`. |
| `from app.utils.validacao import data_iso_valida, neutralizar_formula` | As defesas de data e de fórmula. | Veja as seções 4.1 e `_obter_periodo_padrao`. | `ImportError`. |
| `STATUS_VALIDOS` | Os 4 status possíveis. | Evita repetir a lista. | Texto repetido em vários lugares. |
| `LIMITE_IMPRESSAO = 500` | Máximo de linhas no modo "imprimir tudo". | Evita montar uma página gigantesca. | Uma tabela de 100 mil linhas travaria o navegador. |
| `FROM_ANALITICO = """FROM reservas r ... WHERE r.data_reserva BETWEEN %s AND %s"""` | O trecho `FROM ... WHERE` das reservas, escrito **uma única vez**. | Tela e CSV usam exatamente a mesma base: o que aparece é o que é exportado. Antes havia duas cópias e elas divergiram (a busca por setor existia só na tela). | Duas cópias do SQL podem ficar diferentes e o CSV não bater com a tabela. |

#### `_obter_periodo_padrao()`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `inicio_padrao`/`fim_padrao` com `timedelta(days=30)` | Hoje menos 30 dias e hoje mais 30 dias, em texto `AAAA-MM-DD` (`isoformat()`). | Período sugerido quando a pessoa não escolhe nada. | A primeira abertura da página não teria período. |
| `if not data_iso_valida(data_inicio): data_inicio = inicio_padrao` | Se a data da URL é inválida (ou ausente), usa a padrão. | Datas inventadas na barra de endereços não causam erro e **nunca chegam ao nome do arquivo** do download. | Uma data estranha poderia gerar erro do MySQL ou um nome de arquivo malicioso. |
| `if data_inicio > data_fim: data_inicio, data_fim = data_fim, data_inicio` | Se o período está invertido, troca as pontas (em Python, `a, b = b, a` troca os valores). | O relatório sempre faz sentido. | O período invertido devolveria resultados vazios sem explicação. |

#### `_filtros_analiticos()`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `params = [data_inicio, data_fim]` | Os dois primeiros parâmetros: os do `BETWEEN` do `FROM_ANALITICO`. | A **ordem** dos `%s` precisa bater com a ordem da lista. | Datas e filtros trocariam de lugar. |
| `if busca: sql += " AND (...5 colunas...)"` | Acrescenta a pesquisa de texto em 5 colunas, incluindo o setor. | Tela e CSV usam o mesmo filtro. | O CSV teria menos filtros que a tela. |
| `if status in STATUS_VALIDOS:` | Só filtra por status se for um dos 4 válidos. | Ignora valores inventados. | Um status inválido filtraria tudo e deixaria a tabela vazia. |
| `return sql, params` | Devolve o texto SQL e a lista de parâmetros. | Quem chama monta a consulta final. | A função não teria resultado. |

#### `_responder_csv()` — o streaming (leia com atenção!)

> **Analogia da esteira x caminhão de mudança:** o jeito antigo era carregar **o caminhão inteiro** (todas as linhas do relatório na memória) e só então mandar. O jeito novo é uma **esteira**: cada linha sai do banco, passa pela esteira e chega ao navegador, uma de cada vez. A memória usada é sempre pequena, não importa se o relatório tem 100 ou 1 milhão de linhas.

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `def gerar():` (função dentro de função) | Define um **gerador**: uma função que usa `yield` e produz o resultado em pedaços. | É a "esteira". | Sem gerador, voltamos a montar o arquivo todo de uma vez. |
| `conn = get_db()` / `cursor = conn.cursor(dictionary=True)` | Pega a conexão e cria o cursor. | Precisamos ler as linhas **uma a uma**. | Sem cursor não há leitura. |
| `buffer = io.StringIO()` | Uma "folha de rascunho" na memória onde o `csv.writer` escreve **uma linha por vez**. | O `csv.writer` só sabe escrever em arquivos (ou parecidos). | Teríamos que criar arquivos reais no disco. |
| `csv.writer(buffer, delimiter=";")` | O escritor de CSV com ponto e vírgula. | No Brasil o Excel separa colunas por `;`. | O Excel abriria tudo em uma única coluna. |
| `buffer.write("﻿")` | Escreve o caractere invisível BOM. | Faz o Excel reconhecer UTF-8 e exibir acentos corretamente. | `Início` apareceria como `InÃ­cio`. |
| `yield buffer.getvalue()` | "Entrega" o que está no rascunho ao navegador **e pausa** a função. | É o momento em que o pedaço vai pela esteira. | Nada seria enviado até o fim. |
| `buffer.seek(0)` e `buffer.truncate(0)` | Volta ao início do rascunho e apaga o conteúdo. | Prepara a folha limpa para a próxima linha, mantendo a memória constante. | O rascunho cresceria até virar o arquivo inteiro na memória. |
| `for linha in cursor:` | Percorre as linhas do banco aos poucos. | A leitura também acontece em pedaços. | `fetchall()` carregaria tudo de uma vez. |
| `[neutralizar_formula(campo) for campo in montar_linha(linha)]` | Para cada campo da linha, aplica a proteção contra fórmula. `montar_linha` é uma função recebida como argumento que diz **quais campos** vão em cada linha. | Defesa contra CSV Injection, para qualquer relatório. | Títulos maliciosos executariam fórmulas no Excel. |
| `finally: cursor.close()` | Fecha o cursor mesmo se o download for interrompido. | Evita vazamentos. | Cursores abertos acumulam. |
| `Response(stream_with_context(gerar()), mimetype="text/csv", headers={...})` | Monta a resposta HTTP a partir do gerador. O Flask acrescenta `charset=utf-8` ao `text/csv`. | É o que de fato envia o arquivo ao navegador. | O navegador não receberia nada. |
| `Content-Disposition: attachment; filename="..."` | Avisa ao navegador: "baixe como arquivo, com este nome". As aspas protegem nomes com caracteres especiais. | Sem isso, o CSV seria mostrado na tela. | O navegador tentaria exibir o texto em vez de baixar. |

#### `painel()` — novidades

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `imprimir = request.args.get("imprimir") == "1"` | `True` quando a URL tem `?imprimir=1`. | Ativa o "modo impressão" (tudo numa página). | Só a página atual da tabela seria impressa. |
| `por_pagina_salas = LIMITE_IMPRESSAO if imprimir else 5` | No modo impressão, usa 500; senão, 5. | A impressão mostra **todas** as linhas. | O papel sairia com 5 linhas apenas. |
| `q_salas = "" if imprimir else ...` | No modo impressão, ignora a busca da Tabela 1. | O relatório impresso sempre lista **todas** as salas. | A impressão dependeria de um filtro invisível. |
| `if imprimir: pag_salas_num = pag_analitico_num = 1` | Força a página 1. | Com 500 linhas por página, só existe a página 1. | Poderia abrir uma página vazia. |
| `sql_analitico = ("""SELECT ...""" + FROM_ANALITICO + filtros_sql)` | Junta três pedaços de texto SQL: colunas, base e filtros. | Reaproveita o trecho compartilhado. | Voltaríamos a duplicar o SQL. |

#### `exportar_csv()` — novidades

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `def montar_linha(l): return [...]` | Uma função que diz quais campos (e em qual ordem) compõem cada linha do CSV. | A `_responder_csv` é genérica; esta parte é específica deste relatório. | A função genérica não saberia o que escrever. |
| `return _responder_csv(nome_arquivo, cabecalho, sql, tuple(params), montar_linha)` | Chama o gerador de CSV. | Toda a lógica de download fica em um único lugar. | Cada relatório teria que repetir o código de streaming. |

---

## 5. Entendendo a Exportação CSV Profissional (`exportar_csv`)

Olhe para a função `_responder_csv` acima e veja por que cada detalhe importa:

1. **Streaming em vez de arquivo na memória (`yield`):**  
   Na versão anterior usávamos `io.StringIO()` e `query_all()` para montar **o arquivo inteiro** na memória antes de enviar. Para centenas de linhas funciona, mas para dezenas de milhares o servidor consumiria muita memória por download e poderia travar com vários gestores exportando juntos. Agora o servidor lê uma linha, escreve uma linha e envia; o consumo de memória é praticamente constante.
2. **O Caractere Mágico `"﻿"` (UTF-8 BOM):**  
   Se você gerar um CSV comum em UTF-8 e der dois cliques nele no Windows para abrir no Microsoft Excel, palavras como `Início`, `Código` e `Auditório` aparecerão estragadas (`InÃ­cio`, `CÃ³digo`). Isso acontece porque o Excel no Windows espera uma assinatura invisível de 3 bytes no começo do arquivo chamada **BOM (*Byte Order Mark*)**, representada em Python por `"﻿"`. Ao escrever essa assinatura **no primeiro pedaço**, o Excel reconhece o UTF-8 na hora e mostra todos os acentos perfeitos!
3. **Por que `delimiter=";"` (Ponto e Vírgula)?**  
   No Brasil e em Portugal, a vírgula (`,`) é usada para separar casas decimais (`1,5`). Por isso, o Excel em português usa o **ponto e vírgula (`;`)** para separar as colunas do CSV! Com `delimiter=";"`, cada coluna já abre separadinha na sua própria célula do Excel.
4. **O Cabeçalho HTTP `Content-Disposition: attachment; filename=...`:**  
   A palavra `attachment` avisa ao navegador: *"Não mostre esse texto na tela; baixe-o imediatamente como um arquivo na pasta Downloads do usuário!"*.
5. **Proteção contra CSV Injection (`neutralizar_formula`):**  
   Todo campo de texto passa pela função da seção 4.1 antes de ir para o arquivo. Sem isso, o relatório se tornaria um canal para executar fórmulas maliciosas no computador do gestor.
6. **O nome do arquivo é seguro:**  
   As datas que formam o nome (`relatorio_reservas_2026-09-01_a_2026-10-31.csv`) passam por `data_iso_valida` em `_obter_periodo_padrao`. Assim, ninguém consegue colocar caracteres estranhos no cabeçalho HTTP pela barra de endereços.

---

## 6. Criando o Template do Painel de Relatórios (`app/templates/relatorios/painel.html`)

### 6.1 — O que muda no layout

Antes, os botões de **Imprimir** e **Exportar CSV** ficavam no topo da página, com um link fixo montado quando a página foi carregada. Quando a pessoa digitava na busca da Tabela 2, o JavaScript atualizava a tabela, mas **o link continuava com os filtros antigos**: o CSV baixado não correspondia ao que estava na tela!

A solução tem duas partes:
1. Os botões agora vivem **dentro do formulário de filtros da Tabela 2** e, ao serem clicados, o JavaScript monta o endereço usando **os valores atuais dos campos**.
2. O **período** (data inicial e final) ganhou um formulário próprio, que **recarrega a página inteira**. Isso é proposital: o período altera os KPIs, a Tabela 1 e a Tabela 2 ao mesmo tempo, e a busca dinâmica só atualiza uma tabela por vez.

### 6.2 — O JavaScript dos botões de ação

Abra `app/static/js/tabela_dinamica.js` e acrescente o bloco abaixo **no final do arquivo, logo antes da linha `});` que fecha o `DOMContentLoaded`**:

```javascript
    // 5. Botões de ação (exportar CSV, imprimir) que levam os filtros ATUAIS do formulário
    document.body.addEventListener("click", (evento) => {
        const botao = evento.target.closest(".js-acao-com-filtros");
        if (!botao) return;

        const form = botao.closest(".js-form-filtro");
        if (!form) return;

        const destino = new URL(botao.dataset.url, window.location.origin);
        new FormData(form).forEach((valor, chave) => {
            if (valor !== "") {
                destino.searchParams.set(chave, valor);
            }
        });

        if (botao.dataset.novaAba === "1") {
            window.open(destino.toString(), "_blank");
        } else {
            window.location.href = destino.toString();
        }
    });
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `evento.target.closest(".js-acao-com-filtros")` | Descobre se o clique foi num botão marcado com essa classe. É a mesma técnica de *delegação de eventos* da Aula 06. | Um único "ouvido" atende todos os botões de ação. | Os botões não fariam nada. |
| `const form = botao.closest(".js-form-filtro")` | Encontra o formulário de filtros que contém o botão. | É dele que leremos os valores atuais (busca, status, período). | Não saberíamos quais filtros estão ativos. |
| `new URL(botao.dataset.url, window.location.origin)` | Cria o endereço de destino a partir do `data-url` do botão (por exemplo, `/relatorios/exportar-csv`). | Cada botão informa para onde ir. | Sem destino, não há para onde enviar. |
| `new FormData(form).forEach(... destino.searchParams.set(chave, valor))` | Copia os valores atuais dos campos do formulário para o endereço. | Garante que o CSV e a impressão usem **os filtros que estão na tela agora**. | Voltaria o defeito de baixar o relatório com filtros antigos. |
| `if (valor !== "")` | Ignora campos vazios. | Mantém o endereço limpo. | Endereços cheios de `q=&status=`. |
| `window.open(..., "_blank")` / `window.location.href = ...` | Abre numa **nova aba** (impressão) ou navega na mesma (download de arquivo, que não troca a página). | A impressão não deve tirar o usuário da tela; o download também não a troca. | A impressão substituiria o painel atual. |

### 6.3 — O template

Abra o arquivo **`app/templates/relatorios/painel.html`** e digite o código completo abaixo:

```html
<!-- app/templates/relatorios/painel.html -->
{% extends layout %}
{% from "components/paginacao.html" import renderizar_paginacao %}
{% block titulo %}Relatórios Gerenciais — SalaFácil{% endblock %}

{% block conteudo %}
<div class="mb-6">
    <h2 class="text-2xl font-bold text-slate-900">Relatórios Gerenciais e Indicadores de Ocupação</h2>
    <p class="text-sm text-slate-500">Período analisado: {{ data_inicio }} até {{ data_fim }}</p>
</div>

<!-- Período: formulário comum (recarrega a página inteira, atualizando KPIs e as duas tabelas) -->
<form method="GET" action="{{ url_for('relatorios.painel') }}"
      class="bg-white p-4 rounded-2xl shadow-sm border border-slate-200 mb-6 flex flex-col sm:flex-row sm:items-end gap-3 no-print">
    <div>
        <label class="block text-xs font-semibold text-slate-500 mb-1">Data inicial</label>
        <input type="date" name="data_inicio" value="{{ data_inicio }}" required
               class="px-3 py-2 rounded-xl border border-slate-300 text-sm">
    </div>
    <div>
        <label class="block text-xs font-semibold text-slate-500 mb-1">Data final</label>
        <input type="date" name="data_fim" value="{{ data_fim }}" required
               class="px-3 py-2 rounded-xl border border-slate-300 text-sm">
    </div>
    <button type="submit"
            class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-sm transition">
        Aplicar período
    </button>
</form>

<!-- Cards de Indicadores (KPIs) -->
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5 mb-8">
    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <p class="text-xs font-bold uppercase text-slate-400">Total de Solicitações</p>
        <p class="text-3xl font-extrabold text-slate-900 mt-2">{{ kpis.total_reservas }}</p>
        <p class="text-xs text-slate-500 mt-1">Reservas registradas no período</p>
    </div>
    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <p class="text-xs font-bold uppercase text-emerald-600">Reservas Aprovadas</p>
        <p class="text-3xl font-extrabold text-emerald-700 mt-2">{{ kpis.total_aprovadas }}</p>
        <p class="text-xs text-slate-500 mt-1">Horários confirmados em salas</p>
    </div>
    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <p class="text-xs font-bold uppercase text-amber-600">Pendentes de Aprovação</p>
        <p class="text-3xl font-extrabold text-amber-600 mt-2">{{ kpis.total_pendentes }}</p>
        <p class="text-xs text-slate-500 mt-1">Aguardando decisão de gestor</p>
    </div>
    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <p class="text-xs font-bold uppercase text-indigo-600">Horas Totais Alocadas</p>
        <p class="text-3xl font-extrabold text-indigo-700 mt-2">{{ kpis.total_horas }}h</p>
        <p class="text-xs text-slate-500 mt-1">Soma das reservas aprovadas</p>
    </div>
</div>

<!-- TABELA 1: Consolidado de Ocupação por Sala (Com Pesquisa Dinâmica e Paginação) -->
<section class="mb-10">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
        <h3 class="text-lg font-bold text-slate-900">1. Desempenho e Ocupação Consolidada por Sala</h3>
        <form method="GET" action="{{ url_for('relatorios.painel') }}"
              data-target="#container-relatorio-salas"
              data-page-param="page_salas"
              class="js-form-filtro flex gap-2 no-print">
            <input type="text" name="q_salas" value="{{ q_salas }}"
                   placeholder="Filtrar sala por código, nome ou bloco..."
                   class="js-busca-dinamica px-4 py-2 rounded-xl border border-slate-300 text-sm w-72 bg-white">
        </form>
    </div>

    <div id="container-relatorio-salas" class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase">
                        <th class="py-3.5 px-6">Código</th>
                        <th class="py-3.5 px-6">Sala / Bloco</th>
                        <th class="py-3.5 px-6 text-center">Capacidade</th>
                        <th class="py-3.5 px-6 text-center">Total Pedidos</th>
                        <th class="py-3.5 px-6 text-center">Aprovadas</th>
                        <th class="py-3.5 px-6 text-center">Canceladas</th>
                        <th class="py-3.5 px-6 text-right">Horas Ocupadas</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-200 text-sm">
                    {% for item in paginacao_salas.itens %}
                    <tr class="hover:bg-slate-50/80">
                        <td class="py-3.5 px-6 font-mono font-bold text-indigo-700">{{ item.codigo }}</td>
                        <td class="py-3.5 px-6">
                            <span class="font-semibold text-slate-900">{{ item.nome }}</span>
                            <span class="text-xs text-slate-500 block">{{ item.bloco }}</span>
                        </td>
                        <td class="py-3.5 px-6 text-center">{{ item.capacidade }}</td>
                        <td class="py-3.5 px-6 text-center font-semibold">{{ item.total_reservas }}</td>
                        <td class="py-3.5 px-6 text-center text-emerald-700 font-semibold">{{ item.aprovadas }}</td>
                        <td class="py-3.5 px-6 text-center text-rose-600">{{ item.canceladas }}</td>
                        <td class="py-3.5 px-6 text-right font-mono font-bold text-slate-900">{{ item.horas_ocupadas }} h</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="7" class="py-8 text-center text-slate-500">
                            Nenhuma sala encontrada para "{{ q_salas }}".
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {{ renderizar_paginacao(paginacao_salas, '#container-relatorio-salas') }}
    </div>
</section>

<!-- TABELA 2: Relatório Analítico de Reservas (Com Pesquisa Dinâmica e Paginação) -->
<section>
    <h3 class="text-lg font-bold text-slate-900 mb-4">2. Relatório Analítico de Reservas no Período</h3>

    <form method="GET" action="{{ url_for('relatorios.painel') }}"
          data-target="#container-relatorio-analitico"
          data-page-param="page"
          class="js-form-filtro bg-white p-4 rounded-2xl shadow-sm border border-slate-200 mb-4 flex flex-col gap-3 no-print">
        <!-- O período vem do formulário de cima; aqui ele só "acompanha" a busca -->
        <input type="hidden" name="data_inicio" value="{{ data_inicio }}">
        <input type="hidden" name="data_fim" value="{{ data_fim }}">

        <div class="flex flex-col lg:flex-row gap-3">
            <input type="text" name="q" value="{{ q_analitico }}"
                   placeholder="Pesquisar dinamicamente por evento, sala, solicitante ou setor..."
                   class="js-busca-dinamica flex-1 px-4 py-2 rounded-xl border border-slate-300 text-sm">
            <select name="status" class="js-filtro-imediato px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white">
                <option value="">Todos os Status</option>
                <option value="aprovada" {% if status_filtro == 'aprovada' %}selected{% endif %}>Aprovadas</option>
                <option value="pendente" {% if status_filtro == 'pendente' %}selected{% endif %}>Pendentes</option>
                <option value="rejeitada" {% if status_filtro == 'rejeitada' %}selected{% endif %}>Rejeitadas</option>
                <option value="cancelada" {% if status_filtro == 'cancelada' %}selected{% endif %}>Canceladas</option>
            </select>
            <select name="per_page" class="js-filtro-imediato px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white">
                {% for qtd in [5, 8, 10, 20] %}
                <option value="{{ qtd }}" {% if paginacao_analitico.por_pagina == qtd %}selected{% endif %}>{{ qtd }} por página</option>
                {% endfor %}
            </select>
        </div>

        {% if tem_permissao('relatorios.exportar') %}
        <div class="flex flex-wrap items-center gap-3">
            <button type="button"
                    data-url="{{ url_for('relatorios.painel', imprimir=1) }}" data-nova-aba="1"
                    class="js-acao-com-filtros px-4 py-2 bg-slate-800 hover:bg-slate-900 text-white text-sm font-semibold rounded-xl shadow-sm transition">
                🖨️ Imprimir Relatório Completo
            </button>
            <button type="button"
                    data-url="{{ url_for('relatorios.exportar_csv') }}"
                    class="js-acao-com-filtros px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-sm font-semibold rounded-xl shadow-sm transition">
                📥 Exportar CSV (Excel)
            </button>
            <span class="text-xs text-slate-500">Os dois botões usam o período e os filtros que estão na tela agora.</span>
        </div>
        {% endif %}
    </form>

    <div id="container-relatorio-analitico" class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
        <div class="overflow-x-auto">
            <table class="w-full text-left border-collapse">
                <thead>
                    <tr class="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase">
                        <th class="py-3.5 px-6">Data / Horário</th>
                        <th class="py-3.5 px-6">Sala</th>
                        <th class="py-3.5 px-6">Evento / Finalidade</th>
                        <th class="py-3.5 px-6">Solicitante / Setor</th>
                        <th class="py-3.5 px-6">Aprovador</th>
                        <th class="py-3.5 px-6 text-right">Duração</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-slate-200 text-sm">
                    {% for r in paginacao_analitico.itens %}
                    <tr class="hover:bg-slate-50/80">
                        <td class="py-3.5 px-6 whitespace-nowrap">
                            <p class="font-semibold text-slate-900">{{ r.data_reserva.strftime('%d/%m/%Y') }}</p>
                            <p class="text-xs font-mono text-slate-500">{{ r.inicio_fmt }} - {{ r.fim_fmt }}</p>
                        </td>
                        <td class="py-3.5 px-6">
                            <span class="font-mono text-xs font-bold text-indigo-700">{{ r.sala_codigo }}</span>
                            <p class="text-xs text-slate-600">{{ r.sala_nome }}</p>
                        </td>
                        <td class="py-3.5 px-6">
                            <p class="font-semibold text-slate-900">{{ r.titulo }}</p>
                            <p class="text-xs text-slate-500">{{ r.finalidade }} ({{ r.status|upper }})</p>
                        </td>
                        <td class="py-3.5 px-6">
                            <p class="font-medium text-slate-800">{{ r.solicitante_nome }}</p>
                            <p class="text-xs text-slate-500">{{ r.solicitante_setor }}</p>
                        </td>
                        <td class="py-3.5 px-6 text-xs text-slate-600">{{ r.aprovador_nome }}</td>
                        <td class="py-3.5 px-6 text-right font-mono font-semibold text-slate-800">{{ r.duracao_min }} min</td>
                    </tr>
                    {% else %}
                    <tr>
                        <td colspan="6" class="py-10 text-center text-slate-500">
                            Nenhum registro encontrado no relatório para os filtros atuais.
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        {{ renderizar_paginacao(paginacao_analitico, '#container-relatorio-analitico') }}
    </div>
</section>
{% endblock %}

{% block scripts %}
{% if imprimir %}
<script>
    // Modo impressão: abre a janela de impressão assim que a página terminar de carregar
    window.addEventListener("load", () => window.print());
</script>
{% endif %}
{% endblock %}
```

### 6.4 — Linha por linha das novidades do `painel.html`

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `{% extends layout %}` | Molde completo ou parcial conforme o pedido (Aula 06, seção 8.1). | As buscas dinâmicas recebem só o recheio. | Funciona, mas é mais pesado. |
| `<form method="GET" ...>` do **período** (sem a classe `js-form-filtro`) | Formulário comum: ao enviar, o navegador recarrega a página inteira com `?data_inicio=...&data_fim=...`. | Período afeta KPIs, Tabela 1 e Tabela 2 ao mesmo tempo. | Se virasse "dinâmico", só uma tabela seria atualizada e a tela ficaria inconsistente. |
| `required` nas datas | O navegador exige o preenchimento. | Evita enviar período vazio (o Python também protege). | Aceitaria campos vazios, que cairiam no período padrão. |
| `<input type="hidden" name="data_inicio" value="{{ data_inicio }}">` (e `data_fim`) dentro do formulário da Tabela 2 | Campos escondidos que "acompanham" os filtros com o período atual. | Quando o JavaScript monta a URL da busca, o período entra junto, e a Tabela 2 usa o mesmo período dos KPIs. | A busca poderia usar um período diferente do mostrado no topo. |
| `<button type="button" ... class="js-acao-com-filtros" data-url="...">` | Botões **que não enviam o formulário** (`type="button"`); o JavaScript da seção 6.2 faz o trabalho. `data-url` é o destino; `data-nova-aba="1"` pede nova aba. | O endereço é montado no momento do clique, com os filtros atuais. | Se fosse `type="submit"`, o clique enviaria o formulário normalmente e recarregaria a página. |
| `url_for('relatorios.painel', imprimir=1)` | Gera `/relatorios/?imprimir=1`. | O painel entra no "modo impressão" (500 linhas por página). | A impressão sairia com 5 ou 8 linhas apenas. |
| `{% if tem_permissao('relatorios.exportar') %}` | Só quem tem a chave vê os botões. | Camada de interface (a de segurança real está nas rotas). | Todos veriam os botões, mas receberiam erro 403 ao clicar. |
| `{% block scripts %}{% if imprimir %}<script>window.addEventListener("load", () => window.print());</script>{% endif %}{% endblock %}` | Só no modo impressão, abre a janela de impressão quando a página termina de carregar. | Automatiza o passo "Ctrl+P". | A pessoa teria que apertar `Ctrl + P` manualmente. |

### Como funciona o modo de impressão (`@media print` e `.no-print`)
Lembra que lá na Aula 05 nós colocamos esta regra CSS no topo do `app/templates/base.html`?
```css
@media print {
    .no-print { display: none !important; }
    body { background: white !important; }
}
```
Quando a janela de impressão abre (ou "Salvar como PDF"), graças ao `@media print`, todos os elementos que têm a classe **`no-print`** (a barra lateral escura, as caixas de pesquisa, os botões de exportar, o formulário de período e os botões de paginação) desaparecem automaticamente do papel, imprimindo apenas os cartões de KPIs e as tabelas em fundo branco limpo. Como o modo impressão carrega até 500 linhas, **o papel mostra o relatório inteiro**, e não só a página que estava na tela.

---

### 6.5 — Testes práticos do módulo de relatórios

1. **Teste 1 (O CSV bate com a tela):** Como Ana, abra `/relatorios/`, digite `Python` na busca da Tabela 2 e escolha o status `Aprovadas`. Clique em **📥 Exportar CSV**. Abra o arquivo no Excel: ele contém **somente** as linhas filtradas que estão na tela (antes, o arquivo saía com os filtros do momento em que a página abriu).
2. **Teste 2 (O período atualiza tudo):** Mude a **Data inicial** para a de hoje, clique em **Aplicar período**. A página recarrega e os **KPIs, a Tabela 1 e a Tabela 2** mudam juntos.
3. **Teste 3 (Impressão completa):** Clique em **🖨️ Imprimir Relatório Completo**. Abre uma nova aba com todas as linhas das duas tabelas e a janela de impressão. Na pré-visualização, não aparecem menu lateral, filtros nem botões.
4. **Teste 4 (A proteção contra fórmulas):** Crie uma reserva com o título `=1+1`, exporte o CSV e abra no Excel. A célula mostra o texto `'=1+1` e **não** o resultado `2`: a fórmula foi neutralizada.
5. **Teste 5 (Datas inventadas):** Acesse `/relatorios/?data_inicio=banana`. A página abre normalmente com o período padrão; nenhum erro 500.

### 6.6 — Guia de Sobrevivência no Laboratório (Erros Comuns na Aula 10)

| Sintoma / Mensagem de Erro | Causa Mais Provável | Como Resolver Rapidamente |
| :--- | :--- | :--- |
| Clico em **Exportar CSV** ou **Imprimir** e nada acontece. | O bloco 5 do JavaScript (seção 6.2) não foi colado, ou foi colado **depois** do `});` final. | Cole o bloco dentro da função do `DOMContentLoaded`, antes do último `});`. Confira o Console (`F12`) por erros. |
| `RuntimeError: Working outside of request context` ao exportar. | A `_responder_csv` não usa `stream_with_context(gerar())` e o gerador perde acesso ao banco no meio do envio. | Envolva o gerador: `Response(stream_with_context(gerar()), ...)`. |
| `mysql.connector.errors.InternalError: Unread result found` | O cursor foi fechado antes de ler todas as linhas. | Mantenha o `for linha in cursor:` completo antes do `cursor.close()` (no `finally`). |
| O Excel mostra `InÃ­cio` em vez de `Início`. | Faltou escrever o `"﻿"` (BOM) no primeiro pedaço. | Confira o `buffer.write("﻿")` antes do cabeçalho. |
| O Excel abre tudo em **uma só coluna**. | Falta o `delimiter=";"` no `csv.writer`. | Use `csv.writer(buffer, delimiter=";")`. |
| `jinja2.exceptions.UndefinedError: 'imprimir' is undefined` | O `render_template` do `painel` não passa `imprimir=imprimir`. | Confira os argumentos do `render_template` ao final da função `painel`. |
| A impressão sai com poucas linhas. | O botão está apontando para `/relatorios/` sem `imprimir=1`. | Confira o `data-url="{{ url_for('relatorios.painel', imprimir=1) }}"`. |
| Ao trocar o período, a Tabela 1 e os KPIs não mudam. | O período está sendo enviado pelo formulário dinâmico (com a classe `js-form-filtro`) em vez do formulário comum. | O formulário de período **não** deve ter a classe `js-form-filtro`. |

---

## 7. Checklist Geral de Validação do Projeto Completo (Aulas 01 a 10)

Parabéns! Você concluiu a codificação de todos os arquivos do **SalaFácil**. Antes de apresentar seu projeto ou publicá-lo no seu portfólio, utilize este guia de verificação para testar cada requisito:

| Etapa / Requisito do Sistema | Onde Foi Construído | Como Testar na Prática |
| :--- | :--- | :--- |
| **1. Ambiente Virtual e Dependências** | **Aula 01** (`venv`, `requirements.txt`, `hello.py`) | Ativar o `(venv)` no terminal e verificar os pacotes instalados com `pip list`. |
| **2. Application Factory e `.env`** | **Aula 02** (`.env`, `app/config.py`, `app/__init__.py`, `run.py`) | Executar `python run.py` e confirmar leitura segura das variáveis do `.env`. |
| **3. Esquema Relacional MySQL** | **Aula 03** (`sql/schema.sql`) | Verificar as 5 tabelas (`usuarios`, `permissoes`, `usuario_permissoes`, `salas`, `reservas`) e índices criados. |
| **4. Conexão Segura e Carga Inicial (`Seed`)** | **Aula 04** (`app/database.py`, `seed_db.py`) | Executar `python seed_db.py` e confirmar a criação das 13 permissões, 3 usuários, 10 salas e 6 reservas. |
| **5. Autenticação e Dupla Camada de Acesso** | **Aula 05** (`security.py`, `auth.py`, `base.html`, `login.html`, `perfil.html`, `403.html`) | Logar com `beatriz@salafacil.com`, ver `/auth/meu-perfil` e tentar abrir `/usuarios/` (deve exibir a página `403`). |
| **6. Motor de Paginação e Busca AJAX** | **Aula 06** (`pagination.py`, `paginacao.html`, `tabela_dinamica.js`) | Digitar nas barras de busca e trocar de página sem recarregar a tela inteira. |
| **7. CRUD Completo do Catálogo de Salas** | **Aula 07** (`salas.py`, `salas/index.html`, `salas/form.html`) | Cadastrar uma sala nova, editar seus equipamentos e testar a exclusão protegida (`salas.excluir`). |
| **8. Gestão de Usuários e Matriz `N:M`** | **Aula 08** (`usuarios.py`, `usuarios/index.html`, `form.html`, `permissoes.html`) | Alterar permissões de um usuário pelos checkboxes e ver o efeito imediato na sessão dele. |
| **9. Reservas e Algoritmo Anti-Conflito** | **Aula 09** (`reservas.py`, `reservas/index.html`, `reservas/form.html`) | Tentar agendar dois eventos no mesmo horário e sala e confirmar o bloqueio matemático. |
| **10. Relatórios, KPIs e Exportação CSV** | **Aula 10** (`relatorios.py`, `relatorios/painel.html`) | Paginar as duas tabelas de forma independente, filtrar a Tabela 2, clicar em `Exportar CSV` e conferir que o arquivo contém **exatamente** o que está na tela; acionar `Imprimir Relatório Completo`. |
| **11. Defesas de Segurança** | **Aulas 01, 05, 07, 08, 09 e 10** (`escape`, `csrf_token`, `caminho_seguro`, limite de tentativas, `neutralizar_formula`, validações no servidor) | Repetir os testes de segurança das aulas: formulário sem ficha CSRF, `?proximo=//site-falso.com`, 5 senhas erradas, criação de usuário sem `usuarios.permissoes`. |
| **12. Testes Automáticos** | **Aula 10** (`tests/test_utilitarios.py`) | Rodar `python -m pytest` e ver todos os testes passando (seção 7.1). |

---

## 7.1 Testes Automáticos: um "Corretor Ortográfico" Para o Seu Código

### Contextualização
Até aqui, todo teste foi **manual**: você clicava, olhava a tela e concluía "parece certo". Isso funciona, mas tem um problema: depois de alterar o sistema, ninguém vai repetir de cabeça os 40 testes de todas as aulas.

> **Analogia do corretor ortográfico:** você não relê o livro inteiro toda vez que muda uma frase; o corretor sublinha os erros na hora. Um **teste automático** é um pequeno programa que chama uma função do seu código com entradas conhecidas e **confere se a resposta é a esperada**. Rodá-los leva segundos.

Vamos testar as funções "puras" (que não dependem do banco de dados): as de segurança e as de validação. Primeiro instale a ferramenta de testes (ela é só para desenvolvimento, por isso **não** entra no `requirements.txt`):

```bash
pip install pytest
```

Depois, abra **`tests/test_utilitarios.py`** e digite:

```python
# tests/test_utilitarios.py
from app.utils.security import caminho_seguro
from app.utils.validacao import (
    PADRAO_CODIGO_SALA, PADRAO_EMAIL, data_iso_valida, hora_valida,
    horarios_se_sobrepoem, inteiro_no_intervalo, lista_de_inteiros, neutralizar_formula,
)


def test_caminho_seguro_aceita_apenas_caminhos_internos():
    assert caminho_seguro("/salas/") == "/salas/"
    assert caminho_seguro("//site-falso.com") is None
    assert caminho_seguro("http://site-falso.com") is None
    assert caminho_seguro("/\\site-falso.com") is None
    assert caminho_seguro("") is None
    assert caminho_seguro(None) is None


def test_horarios_se_sobrepoem_nos_cenarios_da_aula_09():
    # Reserva existente: 09:00 às 11:00
    assert horarios_se_sobrepoem("09:00", "11:00", "08:30", "09:30")   # invade o começo
    assert horarios_se_sobrepoem("09:00", "11:00", "10:30", "11:30")   # invade o final
    assert horarios_se_sobrepoem("09:00", "11:00", "09:30", "10:30")   # dentro do horário
    assert horarios_se_sobrepoem("09:00", "11:00", "08:00", "12:00")   # engloba tudo
    assert not horarios_se_sobrepoem("09:00", "11:00", "11:00", "13:00")  # vizinho depois: permitido
    assert not horarios_se_sobrepoem("09:00", "11:00", "07:00", "09:00")  # vizinho antes: permitido


def test_inteiro_no_intervalo():
    assert inteiro_no_intervalo("5", 1, 10) == 5
    assert inteiro_no_intervalo("0", 1, 10) is None
    assert inteiro_no_intervalo("11", 1, 10) is None
    assert inteiro_no_intervalo("abc", 1, 10) is None
    assert inteiro_no_intervalo(None, 1, 10) is None


def test_lista_de_inteiros_ignora_valores_estranhos():
    assert lista_de_inteiros(["1", "5", "abc", "²", "-3"]) == {1, 5}


def test_formato_do_codigo_da_sala_e_do_email():
    assert PADRAO_CODIGO_SALA.match("LAB-101")
    assert not PADRAO_CODIGO_SALA.match("lab 104!")
    assert not PADRAO_CODIGO_SALA.match("A")
    assert PADRAO_EMAIL.match("ana@salafacil.com")
    assert not PADRAO_EMAIL.match("ana@salafacil")
    assert not PADRAO_EMAIL.match("ana salafacil.com")


def test_datas_e_horas_validas():
    assert data_iso_valida("2026-10-15")
    assert not data_iso_valida("2026-02-30")
    assert not data_iso_valida("banana")
    assert not data_iso_valida(None)
    assert hora_valida("08:30")
    assert not hora_valida("25:99")


def test_neutralizar_formula_protege_o_excel():
    assert neutralizar_formula("=1+1") == "'=1+1"
    assert neutralizar_formula("@cmd") == "'@cmd"
    assert neutralizar_formula("-5 pessoas") == "'-5 pessoas"
    assert neutralizar_formula("Aula de Python") == "Aula de Python"
    assert neutralizar_formula(35) == 35
    assert neutralizar_formula(-5) == -5
```

Para executar, no terminal com o `(venv)` ativo e na pasta raiz do projeto:

```bash
python -m pytest
```

Você deve ver algo como `7 passed`.

### Linha por linha

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `from app.utils.security import caminho_seguro` | Importa a função que será testada. | Os testes chamam o código real do sistema, e não uma cópia. | `ImportError` ao rodar os testes. |
| `def test_...():` | Qualquer função cujo nome comece com `test_` é encontrada e executada automaticamente pelo `pytest`. | É a convenção da ferramenta. | O `pytest` não executa a função. |
| `assert condição` | "Afirmo que isto é verdadeiro." Se for falso, o teste **falha** e o pytest mostra qual `assert` quebrou. | É o coração do teste: a conferência. | Sem `assert`, o teste nunca falha, e fica inútil. |
| `assert caminho_seguro("//site-falso.com") is None` | Afirma que o endereço malicioso foi rejeitado (`None`). | Prova que a defesa contra *open redirect* funciona. | Se alguém "simplificar" a função e quebrar a defesa, este teste avisa na hora. |
| `assert not horarios_se_sobrepoem("09:00", "11:00", "11:00", "13:00")` | Afirma que reservas vizinhas **não** conflitam. | Prova a regra mais sutil da Aula 09 (`<` e `>` estritos). | Trocar por `<=` passaria despercebido até alguém reclamar de uma reserva recusada injustamente. |
| `assert lista_de_inteiros([...]) == {1, 5}` | Compara com o conjunto esperado. | Garante que `"abc"`, `"²"` e `"-3"` são descartados. | Um valor estranho voltaria a causar erro 500. |
| `assert neutralizar_formula(-5) == -5` | Afirma que números negativos **não** ganham apóstrofo. | Evita que a proteção estrague números válidos. | Números negativos virariam texto no relatório. |

> 📌 **O que estes testes não cobrem:** consultas ao banco, rotas e formulários. Para isso existem testes de integração com um banco de teste, um assunto para o próximo nível do seu estudo. O importante é o hábito: **toda regra que protege o sistema merece um teste**.

---

## 7.2 Antes de Publicar: O Que Muda em Produção

Tudo que fizemos funciona no seu computador. Para colocar o SalaFácil na internet de verdade, revise esta lista (cada item tem uma razão de ser):

| Item | O que fazer | Por quê |
| :--- | :--- | :--- |
| **Modo debug** | No `.env` do servidor: `FLASK_DEBUG=0`. | A tela de debug permite executar comandos no servidor (Aula 01). |
| **`SECRET_KEY` nova** | Gere uma com `python -c "import secrets; print(secrets.token_hex(32))"` e coloque no `.env` do servidor. | A chave do curso é pública. Quem a conhece forja cookies de login. |
| **Cookies só por HTTPS** | Acrescente `SESSION_COOKIE_SECURE = True` na classe `Config`. | Impede que o cookie de login viaje por conexões sem criptografia. |
| **Servidor de verdade** | Use `gunicorn` (Linux/macOS) ou `waitress` (Windows) em vez de `python run.py`. | O servidor do Flask é só para desenvolvimento (o próprio terminal avisa). |
| **Usuário do banco** | Crie um usuário MySQL só para o sistema, com permissão apenas no banco `gestao_reservas_salas`, em vez de `root`. | Se alguém invadir o app, não consegue mexer em outros bancos. |
| **Contas de demonstração** | Apague (ou troque a senha de) `admin@salafacil.com` e os demais usuários do `seed_db.py`. | A senha `123456` está escrita neste curso. |
| **Tailwind** | Troque o Play CDN pelo arquivo `.css` gerado pela *Tailwind CLI* (Aula 02). | Carregamento muito mais rápido. |
| **Limite de tentativas** | Troque o contador em memória por *Flask-Limiter* com Redis. | O contador da Aula 05 zera ao reiniciar e não é compartilhado entre processos. |

Comandos para subir o sistema com um servidor de verdade (instale antes o pacote indicado):

```bash
# Linux ou macOS:
pip install gunicorn
gunicorn "app:create_app()" --workers 3 --bind 0.0.0.0:8000
```

```powershell
# Windows:
pip install waitress
waitress-serve --port=8000 --call app:create_app
```

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `gunicorn` / `waitress-serve` | Servidores web profissionais (WSGI, lembra da Aula 01?) que atendem muitas pessoas ao mesmo tempo. | O servidor do `python run.py` é feito para uma pessoa só, testando. | Em produção, ele trava com poucos usuários e é mais fácil de atacar. |
| `"app:create_app()"` (gunicorn) / `--call app:create_app` (waitress) | Diz onde está a "fábrica": no pacote `app`, a função `create_app`. | É por isso que usamos o padrão Application Factory (Aula 02). | O servidor não sabe como montar a aplicação. |
| `--workers 3` | Três processos atendendo em paralelo. | Aproveita vários núcleos do processador. | Um só processo atende uma requisição pesada de cada vez. |
| `--bind 0.0.0.0:8000` / `--port=8000` | Endereço e porta de escuta. `0.0.0.0` significa "aceitar conexões de qualquer computador da rede". | Em produção, o servidor precisa ser visível para os usuários (geralmente por trás de um proxy como Nginx com HTTPS). | Com `127.0.0.1`, só o próprio servidor acessaria. |

---

## 8. Exercícios Práticos de Fixação da Aula 10

1. **Desafio 1 (5º Card de KPI — Taxa de Aprovação %):**  
   Adicione no SQL de `kpis` (em `app/blueprints/relatorios.py`) e no topo de `app/templates/relatorios/painel.html` um 5º indicador exibindo a **Taxa de Aprovação (%)** do período:  
   `ROUND(COALESCE((SUM(CASE WHEN status = 'aprovada' THEN 1 ELSE 0 END) / NULLIF(COUNT(*), 0)) * 100, 0), 1) AS taxa_aprovacao`.  
   *(Dica: `NULLIF(COUNT(*), 0)` evita erro de divisão por zero caso `COUNT(*)` seja `0`!).*
2. **Desafio 2 (Exportação CSV da Tabela 1 — Ocupação por Sala):**  
   Crie uma nova rota `@relatorios_bp.route("/exportar-ocupacao-csv")` protegida por `@permissao_obrigatoria("relatorios.exportar")` que exporte para Excel os dados consolidados da **Tabela 1** (Código, Nome da Sala, Bloco, Capacidade, Total Pedidos, Aprovadas, Canceladas e Horas Ocupadas).
3. **Desafio 3 (Teste de Permissão `relatorios.exportar`):**  
   Faça login como Administradora (`admin@salafacil.com`), abra as permissões do `Carlos Gestor` (`gestor@salafacil.com`) e desmarque apenas a chave **`relatorios.exportar`** (mantendo `relatorios.visualizar` marcada). Em uma janela anônima logada com o Carlos Gestor, abra `/relatorios/` e confirme que ele continua vendo os gráficos e tabelas normalmente, mas os botões **Imprimir Relatório** e **Exportar CSV** desapareceram!
4. **Desafio 4 (Laboratório de Paginação Independente):**  
   Navegue para a **página 2** da Tabela 1 (Ocupação por Sala) e observe que a barra de endereços do navegador passa a conter `page_salas=2`. Em seguida, digite `"Aula"` na busca da Tabela 2 e veja que a Tabela 1 permanece intacta na página 2!

<details>
<summary><strong>💡 Clique aqui para ver o Gabarito Comentado dos Desafios 1 e 2</strong></summary>

**1. Resolução do Desafio 1 (5º KPI — Taxa de Aprovação):**  
No dicionário SQL `kpis` de `app/blueprints/relatorios.py`, adicione mais uma linha no `SELECT`:
```sql
            ROUND(
                COALESCE(
                    (SUM(CASE WHEN status = 'aprovada' THEN 1 ELSE 0 END) * 100.0) / NULLIF(COUNT(*), 0),
                    0
                ),
                1
            ) AS taxa_aprovacao
```
E no `app/templates/relatorios/painel.html`, mude a grade de KPIs para `lg:grid-cols-5` e adicione o card:
```html
    <div class="bg-white p-6 rounded-2xl border border-slate-200 shadow-sm">
        <p class="text-xs font-bold uppercase text-violet-600">Taxa de Aprovação</p>
        <p class="text-3xl font-extrabold text-violet-700 mt-2">{{ kpis.taxa_aprovacao }}%</p>
        <p class="text-xs text-slate-500 mt-1">Sobre o total solicitado</p>
    </div>
```

**2. Resolução do Desafio 2 (Rota `/relatorios/exportar-ocupacao-csv` em `app/blueprints/relatorios.py`):**
```python
@relatorios_bp.route("/exportar-ocupacao-csv")
@permissao_obrigatoria("relatorios.exportar")
def exportar_ocupacao_csv():
    data_inicio, data_fim = _obter_periodo_padrao()
    q_salas = request.args.get("q_salas", "").strip()

    sql = """
        SELECT
            s.codigo, s.nome, s.bloco, s.capacidade,
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
    params = [data_inicio, data_fim]
    if q_salas:
        sql += " AND (s.codigo LIKE %s OR s.nome LIKE %s OR s.bloco LIKE %s)"
        termo = f"%{q_salas}%"
        params.extend([termo, termo, termo])

    sql += " GROUP BY s.id, s.codigo, s.nome, s.bloco, s.capacidade ORDER BY horas_ocupadas DESC"

    cabecalho = ["Código", "Sala", "Bloco", "Capacidade", "Total Pedidos", "Aprovadas", "Canceladas", "Horas Ocupadas"]

    def montar_linha(item):
        return [
            item["codigo"], item["nome"], item["bloco"], item["capacidade"],
            item["total_reservas"], item["aprovadas"], item["canceladas"], item["horas_ocupadas"],
        ]

    nome_arquivo = f"ocupacao_salas_{data_inicio}_a_{data_fim}.csv"
    return _responder_csv(nome_arquivo, cabecalho, sql, tuple(params), montar_linha)
```

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `@permissao_obrigatoria("relatorios.exportar")` | Exige a chave de exportação. | Segurança no backend: esconder o botão não bastaria. | Qualquer usuário com `relatorios.visualizar` baixaria o arquivo digitando a URL. |
| `LEFT JOIN reservas r ON ... AND r.data_reserva BETWEEN %s AND %s` | O filtro de datas dentro do `ON` (seção 2.4). | Salas sem reservas continuam aparecendo com `0`. | Salas ociosas sumiriam do arquivo. |
| `def montar_linha(item): return [...]` | Diz quais campos formam cada linha, na ordem das colunas do `cabecalho`. | A `_responder_csv` é genérica e só precisa dessa receita. | O gerador não saberia o que escrever. |
| `return _responder_csv(...)` | Reaproveita o streaming, o BOM, o `;` e a proteção contra fórmulas. | Escrevemos a lógica de download **uma vez** e usamos em todos os relatórios. | Teríamos de copiar 25 linhas de código a cada relatório novo. |
</details>

---
<!-- nav -->
| Anterior | Índice | Próxima |
| :--- | :---: | ---: |
| [← Aula 09 — Gestão de Reservas e Anti-Conflito](./aula_09_gestao_reservas_validacao_conflitos.md) | [📚 Índice do Curso](./README.md) | &nbsp; |