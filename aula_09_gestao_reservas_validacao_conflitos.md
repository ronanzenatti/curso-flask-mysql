# Aula 09 — Gestão de Reservas de Salas e Algoritmo SQL Anti-Conflito de Horários

Nas **Aulas 07 e 08**, construímos o **Catálogo de Salas** e o módulo de **Usuários & Permissões Personalizadas**. Agora temos salas cadastradas e usuários com diferentes níveis de acesso prontos para trabalhar.

Chegou a hora de construir o módulo principal do **SalaFácil**: a **Agenda e Gestão de Reservas de Salas** (`app/blueprints/reservas.py`, `app/templates/reservas/index.html` e `app/templates/reservas/form.html`).

Em um sistema de agendamentos do mundo real (seja para salas de aula, consultórios médicos, quadras esportivas ou salas de reunião), não basta simplesmente dar um `INSERT` no banco de dados. Nós precisamos garantir **Regras de Negócio Críticas**:
1. **Prevenção Matemática de Choques de Horário:** Duas pessoas jamais podem ocupar a mesma sala, no mesmo dia, em horários que se sobreponham.
2. **Validação de Lotação Física:** Não podemos permitir uma reserva para 60 alunos em uma sala que comporta apenas 25 lugares.
3. **Aprovação Inteligente por Permissão:** Se um professor solicitante pede uma sala, a reserva nasce como **`pendente`** aguardando avaliação. Mas se o próprio Gestor de Espaços ou Administrador (que já possui a chave `reservas.aprovar`) agenda uma sala, ela já nasce **`aprovada`** automaticamente!
4. **Regra de Propriedade (*Ownership*) no Cancelamento:** Qualquer usuário pode desistir e cancelar **a sua própria reserva**, mas cancelar a reserva de **outra pessoa** exige a permissão especial `reservas.cancelar_qualquer`.
5. **Proteção Contra Pedidos Simultâneos:** Se duas pessoas clicarem em "Confirmar" **no mesmo instante** para a mesma sala e horário, só uma pode ganhar. Usaremos uma **transação com trava** para garantir isso.
6. **Regras do Ciclo de Vida da Reserva (backend de verdade):** Uma reserva `cancelada` ou `rejeitada` **não pode ser "ressuscitada"** por um pedido manipulado: o servidor confere o estado atual antes de cada mudança.

---

## 1. A Regra de Ouro: Como Detectar Conflitos de Horário no SQL?

Imagine que a sala **`LAB-101`** já possui uma reserva agendada para amanhã das **`09:00` às `11:00`**.
De repente, outro professor abre o formulário e tenta reservar a mesma sala `LAB-101`, para o mesmo dia. Como o nosso código Python e o MySQL descobrirão se o novo horário escolhido bate com o horário que já está lá?

### Os 4 Cenários de Colisão na Linha do Tempo

Se desenharmos os horários em uma linha do tempo, veremos que um novo pedido (`Novo Início` até `Novo Fim`) pode colidir com uma reserva existente (`09:00` às `11:00`) de **4 jeitos diferentes**:

```text
Reserva Existente no Banco:          |------- 09:00 às 11:00 -------|

Cenário 1 (Invade o começo):   |--- 08:30 às 09:30 ---|
Cenário 2 (Invade o final):                        |--- 10:30 às 11:30 ---|
Cenário 3 (Dentro do horário):             |-- 09:30 às 10:30 --|
Cenário 4 (Engloba tudo):      |------------- 08:00 às 12:00 -------------|

Cenário Válido (Vizinho!):                                          |--- 11:00 às 13:00 ---|
```

Se você tentasse escrever um `WHERE` testando cada um desses 4 cenários separadamente com `OR` e `BETWEEN`, a sua consulta SQL ficaria enorme e fácil de errar!

### A Fórmula Matemática Universal da Interseção de Intervalos

Felizmente, na matemática, dois intervalos de tempo $[A_{\text{inicio}}, A_{\text{fim}}]$ e $[B_{\text{inicio}}, B_{\text{fim}}]$ se sobrepõem **se, e somente se**, duas condições muito simples acontecerem ao mesmo tempo:

$$\text{hora\_inicio\_existente} < \text{novo\_fim} \quad \text{E} \quad \text{hora\_fim\_existente} > \text{novo\_inicio}$$

Vamos traduzir essa fórmula para o português claro:
> *"Existe conflito se a reserva que já está no banco **começou antes** de a nova terminar **E** **termina depois** de a nova começar!"*

#### Por que usamos `<` e `>` estritos (e não `<=` ou `>=`)?
Veja o que acontece no **Cenário Válido (Vizinho)** do nosso desenho:
* Reserva existente no banco: **`09:00` às `11:00`**.
* Nova reserva solicitada: **`11:00` às `13:00`** (uma aula termina às 11h e a outra começa exatamente às 11h).
* Vamos aplicar nossa fórmula:
  1. `hora_inicio_existente (09:00) < novo_fim (13:00)` $\rightarrow$ Verdadeiro.
  2. `hora_fim_existente (11:00) > novo_inicio (11:00)` $\rightarrow$ **FALSO!** (Porque `11:00` não é maior que `11:00`, é igual!).
* Como a segunda metade deu **Falso**, o MySQL conclui que **NÃO há conflito** e permite que uma aula comece exatamente no minuto em que a anterior terminou!

---

## 2. A Consulta SQL Anti-Conflito e o Segredo do `'%%H:%%i'`

Veja como fica a nossa consulta SQL que procura se já existe alguma reserva ocupando a sala naquele horário:

```sql
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
  AND r.hora_fim > %s;
```

### Dois detalhes fundamentais desta Query SQL:

1. **Por que filtrar `AND r.status IN ('pendente', 'aprovada')`?**  
   Lembra que uma reserva pode ter 4 status (`pendente`, `aprovada`, `rejeitada`, `cancelada`)? Se alguém pediu uma sala para as `14:00`, mas depois **cancelou** (ou o gestor **rejeitou**), aquela sala voltou a ficar livre às `14:00`! Portanto, reservas canceladas ou rejeitadas continuam salvas para fins de histórico e auditoria, mas são ignoradas na verificação de conflito.
2. **Por que escrever `'%%H:%%i'` com DOIS símbolos de porcentagem no `TIME_FORMAT`?**  
   No MySQL, uma coluna do tipo `TIME` guarda os segundos (`'08:00:00'`). Para exibir apenas horas e minutos (`'08:00'`) direto da consulta, usamos a função `TIME_FORMAT(r.hora_inicio, '%H:%i')`.  
   Porém, quando executamos a consulta pelo Python usando `cursor.execute(sql, params)`, a biblioteca `mysql-connector-python` procura o símbolo **`%`** para substituir os marcadores **`%s`** pelos valores da tupla! Se você escrever apenas `'%H:%i'`, o Python achará que `%H` e `%i` são parâmetros faltantes e travará com o erro:  
   `ProgrammingError: Not enough parameters for the SQL statement`.  
   Ao escrever **`'%%H:%%i'`** (duplicado), o conector do Python entende que queremos escapar o símbolo `%` e envia `'%H:%i'` limpinho para o servidor MySQL!

---

## 2.1 O Problema do "Clique Simultâneo" (e a Trava de Sala)

### Contextualização: o caso dos dois professores
Segunda-feira, 7h59. A professora **Beatriz** e o professor **Rui** querem o `LAB-101` às 8h. Os dois abrem o formulário e clicam em **Confirmar** com poucos milissegundos de diferença. O que o nosso código faz, passo a passo, para cada um?

1. **Pergunta ao banco:** "a sala está livre?"
2. **Se sim, grava** a reserva.

O problema é o espaço **entre** o passo 1 e o passo 2. Veja a linha do tempo:

```text
Tempo →     |  t1                  |  t2                  |  t3                  |  t4
Beatriz     |  "Está livre?" → Sim |                      |  Grava a reserva ✔   |
Rui         |                      |  "Está livre?" → Sim |                      |  Grava a reserva ✔
Resultado   |  As DUAS reservas foram aceitas: a sala foi reservada duas vezes!
```

> **Analogia do último assento do ônibus:** dois passageiros olham ao mesmo tempo para o último assento, **ambos veem que está vazio** e ambos se sentam. A pergunta ("está vazio?") e a ação ("sentar") precisam acontecer **juntas e sem interrupção**. Esse tipo de bug se chama **condição de corrida** (*race condition*), e é um dos mais traiçoeiros: nos testes sozinhos tudo funciona; ele só aparece quando há muita gente usando.

### A solução: transação + trava (`SELECT ... FOR UPDATE`)
> **Analogia da chave do banheiro:** só entra quem pega a chave. Enquanto Beatriz está lá dentro, Rui espera na porta. Quando ela sai (e devolve a chave), ele entra e **já encontra o banheiro ocupado pela situação nova**.

No MySQL, a "chave" é a trava da linha da sala: `SELECT ... FOR UPDATE`. Ela diz: "estou trabalhando nesta sala; quem quiser mexer nela espere eu terminar". O fluxo fica assim, tudo dentro de **uma só transação**:

```text
Beatriz:  [pega a trava da sala] → "Está livre?" Sim → grava → [confirma e solta a trava]
Rui:                  (espera na porta...)                     [pega a trava] → "Está livre?" NÃO → recusa
```

O Rui recebe a mensagem de conflito, exatamente como se tivesse chegado um segundo depois. Nenhuma reserva duplicada!

> 🧠 **Por que a `transacao()` da Aula 04 faz um `commit()` logo no início?** O MySQL "tira uma fotografia" dos dados na primeira consulta de uma transação. Se Rui tivesse feito uma consulta antes (por exemplo, para listar as salas do formulário), ele enxergaria uma **foto antiga**, sem a reserva de Beatriz. O `commit()` inicial descarta a foto velha, e a trava garante que a próxima consulta já enxerga o que Beatriz gravou.

---

## 3. Entendendo o Duplo `JOIN` na Listagem de Reservas

Na rota `listar()` da agenda de reservas, cada linha da tabela precisa mostrar:
* O código e nome da **Sala** (vem da tabela `salas`);
* O nome e setor do **Solicitante** que pediu a sala (vem da tabela `usuarios`);
* E o nome do **Aprovador** que autorizou a reserva (que **também** vem da tabela `usuarios`!).

Veja como fazemos isso no SQL juntando a tabela `usuarios` **duas vezes** com apelidos diferentes (`u` para o solicitante e `ap` para o aprovador):

```sql
FROM reservas r
INNER JOIN salas s ON s.id = r.sala_id
INNER JOIN usuarios u ON u.id = r.usuario_id
LEFT JOIN usuarios ap ON ap.id = r.aprovador_id
```

> **Pergunta de prova: Por que usamos `INNER JOIN` para o solicitante (`u`), mas `LEFT JOIN` para o aprovador (`ap`)?**  
> Porque toda reserva tem obrigatoriamente um solicitante (`usuario_id NOT NULL`), mas uma reserva que acabou de ser criada por um professor nasce com status `pendente` e ainda **não foi aprovada por ninguém** (`aprovador_id` é `NULL`)! Se usássemos `INNER JOIN` para o aprovador, todas as reservas pendentes sumiriam da agenda! Com o `LEFT JOIN`, as reservas pendentes aparecem normalmente na lista com `aprovador_nome` vazio (`None`).

---

## 4. Codificando o Blueprint de Reservas (`app/blueprints/reservas.py`)

Antes do blueprint, vamos ensinar o `app/utils/validacao.py` (Aula 07) a conferir **datas e horários**. Acrescente `from datetime import datetime` logo abaixo de `import re` no topo do arquivo e, ao final dele, as três funções abaixo:

```python
from datetime import datetime  # (no topo do arquivo, abaixo de "import re")


def data_iso_valida(texto):
    """True se o texto for uma data real no formato AAAA-MM-DD (ex.: 2026-10-15)."""
    try:
        datetime.strptime(texto, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False
    return True


def hora_valida(texto):
    """True se o texto for um horário real no formato HH:MM (ex.: 08:30)."""
    try:
        datetime.strptime(texto, "%H:%M")
    except (TypeError, ValueError):
        return False
    return True


def horarios_se_sobrepoem(inicio_a, fim_a, inicio_b, fim_b):
    """A mesma regra do SQL: há conflito se A começa antes de B terminar E A termina depois de B começar."""
    return inicio_a < fim_b and fim_a > inicio_b
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `from datetime import datetime` | Traz a ferramenta de datas e horas do Python. | `strptime` lê um texto e o transforma em data/hora **conferindo se ele existe de verdade**. | `NameError: name 'datetime' is not defined`. |
| `datetime.strptime(texto, "%Y-%m-%d")` | "*String parse time*": tenta ler o texto no formato ano-mês-dia. Se for `2026-02-30` (dia que não existe) ou `abc`, gera `ValueError`. | Os campos `<input type="date">` enviam `AAAA-MM-DD`, mas um pedido adulterado pode mandar qualquer coisa. | Datas inválidas chegariam ao MySQL, que responderia com erro (tela 500). |
| `except (TypeError, ValueError): return False` | Se o texto for inválido (ou `None`), a função responde `False` em vez de quebrar. | Texto errado é um caso **esperado**, e não um defeito do programa. | A página inteira cairia ao receber um valor estranho. |
| `return True` (última linha) | Só é alcançado se o `try` terminou sem erro: o texto é válido. | Resposta direta: `True` ou `False`. | A função devolveria `None` sempre. |
| `"%H:%M"` | Formato de hora e minuto (`08:30`). | O campo `<input type="time">` envia nesse formato. | Horários como `25:99` seriam aceitos. |
| `horarios_se_sobrepoem(inicio_a, fim_a, inicio_b, fim_b)` | A fórmula matemática da seção 1, escrita em Python. | O SQL é quem decide de verdade no sistema, mas esta função "espelho" nos permite **testar a regra** com testes automáticos (Aula 10). | Não conseguiríamos provar a regra sem um banco de dados. |
| `inicio_a < fim_b and fim_a > inicio_b` | "A começou antes de B terminar **e** A terminou depois de B começar." | Os símbolos `<` e `>` estritos permitem reservas vizinhas (uma termina às 11h, outra começa às 11h). | Com `<=`/`>=`, reservas encostadas seriam consideradas conflito. |

Agora que toda a inteligência do módulo está clara, abra o arquivo **`app/blueprints/reservas.py`** (substituindo o esqueleto provisório da Aula 05/07) e digite o código completo abaixo:

```python
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
```

### Repare na ordem dos parâmetros em `verificar_conflito_horario`:
No SQL, escrevemos:
```sql
AND r.hora_inicio < %s
AND r.hora_fim > %s
```
E na lista `params` logo abaixo, passamos:
```python
params = [sala_id, data_reserva, hora_fim, hora_inicio]
```
Observe que o primeiro `%s` de horário compara `r.hora_inicio < hora_fim` (o início existente é menor que o **fim** novo), e o segundo `%s` compara `r.hora_fim > hora_inicio` (o fim existente é maior que o **início** novo). Por isso na lista `params` `hora_fim` vem antes de `hora_inicio`!

### Linha por linha das novidades do `reservas.py`

#### Imports e constante

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `from datetime import date` | Ferramenta para saber a data de hoje (`date.today()`). | Para recusar reservas no passado. | `NameError` ao cadastrar. |
| `from app.database import ..., transacao` | A transação com trava da Aula 04. | Confere e grava no mesmo bloco indivisível. | `ImportError`. |
| `from app.utils.validacao import data_iso_valida, hora_valida, inteiro_no_intervalo` | As conferências de data, hora e número. | Validação no servidor. | `ImportError`. |
| `STATUS_VALIDOS = ("pendente", "aprovada", "rejeitada", "cancelada")` | Lista dos 4 status do `ENUM` do banco. | Uma definição só, usada nos filtros. | Teríamos o mesmo texto repetido em vários lugares. |

#### Rota `listar()` (novidades)

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `if data_filtro and not data_iso_valida(data_filtro): data_filtro = ""` | Se a data da URL não existe (ex.: `?data=banana`), ignora o filtro. | O filtro de data é digitado/editável na barra de endereços. | Uma data inventada na URL poderia causar erro do MySQL (tela 500). |
| `if status_filtro in STATUS_VALIDOS:` | Só aplica o filtro se for um dos 4 status. | Mesma ideia: ignora valores inventados. | Funcionaria (o valor vai como parâmetro), mas listaria zero resultados sem explicação. |

#### Rota `criar()`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `participantes = inteiro_no_intervalo(request.form.get("participantes_estimados"), 1, 5000)` | Número de participantes ou `None`. | Evita `0`, negativos e números absurdos. | Reservas "fantasmas" de 0 pessoas (o `CHECK` do banco recusaria com um erro técnico). |
| `erros = []` e o conjunto de `if`/`elif` de validação | Junta **todos** os problemas dos campos em uma lista, sem tocar no banco. | O usuário recebe todas as correções de uma vez, e o banco só é acionado quando os dados já fazem sentido. | Um erro por vez e consultas desnecessárias. |
| `elif data_reserva < date.today().isoformat():` | Compara a data da reserva com a de hoje como texto `AAAA-MM-DD` (que se ordena corretamente). | Impede agendar no passado. | Reservas em datas passadas seriam aceitas. |
| `if not (hora_valida(hora_inicio) and hora_valida(hora_fim)): ... elif hora_inicio >= hora_fim:` | Primeiro confere se são horas reais; só depois compara a ordem. | Comparar `"banana" >= "25:99"` não faz sentido, então a ordem só é conferida com horas válidas. | O `elif` poderia dar uma mensagem errada ou aceitar horários sem sentido. |
| `render_template(..., dados=request.form)` | Devolve o formulário com os valores digitados. | Evita redigitar. | O formulário volta vazio. |
| `erro = None` | Variável que guardará a mensagem de falha **de dentro** do bloco `with`. | Não usamos `return` dentro do `with`, e assim o `commit`/`rollback` acontece de forma previsível. | Teríamos de espalhar `return` dentro do bloco. |
| `with transacao() as cursor:` | Inicia a transação (Aula 04): a partir daqui ou tudo vale, ou nada vale. | A conferência e a gravação formam um conjunto indivisível. | A condição de corrida (seção 2.1) volta. |
| `SELECT id, codigo, capacidade FROM salas WHERE id = %s AND ativa = 1 FOR UPDATE` | Busca a sala **e a tranca** (a "chave do banheiro"). Quem tentar reservar a mesma sala espera nossa transação acabar. | É o que evita que duas pessoas passem juntas pela checagem de conflito. | Duas reservas simultâneas poderiam ser gravadas no mesmo horário. |
| `sala = cursor.fetchone()` | Lê o resultado da consulta: um dicionário ou `None`. | Precisamos dos dados da sala. | `sala` não existiria. |
| `elif participantes > sala["capacidade"]` | Compara os participantes com a lotação da sala. | Regra de negócio de lotação. | Uma reserva para 60 pessoas seria aceita numa sala de 25 lugares. |
| `conflito = verificar_conflito_horario(...)` | Usa a consulta de sobreposição (seção 2) **dentro da transação** já com a sala trancada. | Agora a resposta "está livre?" é confiável, pois ninguém mais mexe naquela sala ao mesmo tempo. | Sem a trava, a resposta poderia mudar entre a pergunta e a gravação. |
| `cursor.execute("INSERT INTO reservas ...")` | Grava a reserva usando o **mesmo cursor** da transação. | Faz parte do bloco indivisível. | Seria gravada fora da proteção. |
| *(final do `with`)* | O `commit` automático confirma tudo e **solta a trava**; o próximo da fila entra e já enxerga esta reserva. | Garante a regra "um de cada vez". | A trava seria mantida por mais tempo do que o necessário. |
| `if erro: flash(erro, "erro"); return render_template(...)` | Fora do `with`, mostra o motivo da recusa e reexibe o formulário. | Resposta clara ao usuário. | A pessoa não saberia por que a reserva não foi feita. |

#### Rota `alterar_status()`

> **Analogia da catraca:** uma reserva já cancelada é como um bilhete usado: a catraca não deve aceitá-lo de novo. O botão "Aprovar" só **aparece** em reservas pendentes, mas esconder o botão não impede alguém de enviar o pedido manualmente. Quem barra de verdade é o servidor.

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `UPDATE reservas SET status = %s, aprovador_id = %s WHERE id = %s AND status = 'pendente'` | Só altera a reserva **se ela ainda estiver pendente** (a condição está dentro do próprio `UPDATE`). | Uma reserva cancelada ou rejeitada não volta à vida, o que evitaria uma reserva "ressuscitada" sem passar pela checagem de conflito (geraria reserva dupla). | Um pedido adulterado poderia aprovar uma reserva cancelada e criar choque de horário. |
| `linhas_afetadas = execute_write(...)` | O `execute_write` devolve quantas linhas mudaram (0 ou 1). | Assim sabemos se o `UPDATE` realmente aconteceu. | Não saberíamos se a ação foi aceita. |
| `if linhas_afetadas: ... else: flash("Só é possível decidir reservas que ainda estão pendentes.", "aviso")` | Mostra sucesso ou o motivo da recusa. | Dá retorno honesto. | Mostraríamos "sucesso" mesmo quando nada mudou. |
| `AND status IN ('pendente', 'aprovada')` no cancelamento | Só cancela reservas ainda ativas. | Cancelar o que já está cancelada ou rejeitada não faz sentido. | O histórico poderia ser reescrito por pedidos repetidos. |
| `else: flash("Ação inválida.", "erro")` | Trata qualquer valor desconhecido de `novo_status`. | Antes, um valor estranho era ignorado em silêncio. | O usuário não perceberia que a ação foi recusada. |

---

## 5. Criando o Template da Agenda de Reservas (`app/templates/reservas/index.html`)

Na tabela da Agenda de Reservas, veremos em ação uma técnica muito prática de formulários HTML para acionar mudanças de status (**Aprovar**, **Recusar** e **Cancelar**) com um único clique:

### Como funcionam os "Mini-Formulários Inline" com `<input type="hidden">`?
Na última coluna da tabela (`Ações`), cada botão (*✓ Aprovar*, *✕ Recusar* e *Cancelar*) é envolvido por um pequeno `<form method="POST" action="{{ url_for('reservas.alterar_status', reserva_id=r.id) }}" class="inline">`.
Dentro de cada mini-formulário, colocamos um campo invisível (`type="hidden"`):
* No botão Aprovar: `<input type="hidden" name="novo_status" value="aprovada">`
* No botão Recusar: `<input type="hidden" name="novo_status" value="rejeitada">`
* No botão Cancelar: `<input type="hidden" name="novo_status" value="cancelada">`

Assim, uma única rota Python (`alterar_status`) consegue atender os 3 botões lendo `request.form.get("novo_status")`! Cada mini-formulário também leva o campo escondido `csrf_token` (Aula 05), pois todo `POST` precisa da ficha numerada.

Abra o arquivo **`app/templates/reservas/index.html`** e digite o código abaixo:

```html
<!-- app/templates/reservas/index.html -->
{% extends layout %}
{% from "components/paginacao.html" import renderizar_paginacao %}
{% block titulo %}Agenda de Reservas — SalaFácil{% endblock %}

{% block conteudo %}
<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
    <div>
        <h2 class="text-2xl font-bold text-slate-900">Agenda de Reservas de Salas</h2>
        <p class="text-sm text-slate-500">Consulte horários, filtre por status e gerencie aprovações em tempo real</p>
    </div>
    {% if tem_permissao('reservas.criar') %}
    <a href="{{ url_for('reservas.criar') }}"
       class="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-sm transition">
        + Nova Reserva
    </a>
    {% endif %}
</div>

<!-- Barra de Pesquisa Dinâmica e Filtros -->
<form method="GET" action="{{ url_for('reservas.listar') }}"
      data-target="#container-tabela-reservas"
      class="js-form-filtro bg-white p-4 rounded-2xl shadow-sm border border-slate-200 mb-6 flex flex-col lg:flex-row gap-4">
    <div class="flex-1">
        <input type="text" name="q" value="{{ busca }}"
               placeholder="Pesquisar por evento, finalidade, código da sala, nome da sala ou solicitante..."
               class="js-busca-dinamica w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 outline-none text-sm">
    </div>
    <input type="date" name="data" value="{{ data_filtro }}"
           class="js-filtro-imediato px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white">
    <select name="status" class="js-filtro-imediato px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white">
        <option value="">Todos os Status</option>
        <option value="pendente" {% if status_filtro == 'pendente' %}selected{% endif %}>Pendentes</option>
        <option value="aprovada" {% if status_filtro == 'aprovada' %}selected{% endif %}>Aprovadas</option>
        <option value="rejeitada" {% if status_filtro == 'rejeitada' %}selected{% endif %}>Rejeitadas</option>
        <option value="cancelada" {% if status_filtro == 'cancelada' %}selected{% endif %}>Canceladas</option>
    </select>
    <select name="per_page" class="js-filtro-imediato px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white">
        {% for qtd in [5, 8, 10, 20] %}
        <option value="{{ qtd }}" {% if paginacao.por_pagina == qtd %}selected{% endif %}>{{ qtd }} por página</option>
        {% endfor %}
    </select>
</form>

<!-- Tabela Paginada de Reservas -->
<div id="container-tabela-reservas" class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase">
                    <th class="py-3.5 px-6">Data e Horário</th>
                    <th class="py-3.5 px-6">Sala</th>
                    <th class="py-3.5 px-6">Evento / Finalidade</th>
                    <th class="py-3.5 px-6">Solicitante</th>
                    <th class="py-3.5 px-6 text-center">Status</th>
                    <th class="py-3.5 px-6 text-right">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 text-sm">
                {% for r in paginacao.itens %}
                <tr class="hover:bg-slate-50/80 transition">
                    <td class="py-4 px-6 whitespace-nowrap">
                        <p class="font-bold text-slate-900">{{ r.data_reserva.strftime('%d/%m/%Y') }}</p>
                        <p class="text-xs font-mono text-indigo-600">{{ r.hora_inicio_fmt }} às {{ r.hora_fim_fmt }}</p>
                    </td>
                    <td class="py-4 px-6">
                        <span class="font-mono text-xs font-bold bg-slate-100 text-slate-800 px-2 py-0.5 rounded">{{ r.sala_codigo }}</span>
                        <p class="font-medium text-slate-900 mt-0.5">{{ r.sala_nome }}</p>
                    </td>
                    <td class="py-4 px-6">
                        <p class="font-semibold text-slate-900">{{ r.titulo }}</p>
                        <p class="text-xs text-slate-500">{{ r.finalidade }} • {{ r.participantes_estimados }} pessoas</p>
                        {% if r.observacoes %}
                        <p class="text-[11px] text-slate-400 italic mt-0.5">{{ r.observacoes }}</p>
                        {% endif %}
                    </td>
                    <td class="py-4 px-6">
                        <p class="font-medium text-slate-800">{{ r.solicitante_nome }}</p>
                        <p class="text-xs text-slate-500">{{ r.solicitante_setor }}</p>
                    </td>
                    <td class="py-4 px-6 text-center">
                        {% if r.status == 'aprovada' %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">Aprovada</span>
                        {% elif r.status == 'pendente' %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">Pendente</span>
                        {% elif r.status == 'rejeitada' %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">Rejeitada</span>
                        {% else %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-200 text-slate-700">Cancelada</span>
                        {% endif %}
                    </td>
                    <td class="py-4 px-6 text-right whitespace-nowrap space-x-1">
                        {% if r.status == 'pendente' and tem_permissao('reservas.aprovar') %}
                        <form method="POST" action="{{ url_for('reservas.alterar_status', reserva_id=r.id) }}" class="inline">
                            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                            <input type="hidden" name="novo_status" value="aprovada">
                            <button type="submit" class="px-2.5 py-1 rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold">
                                ✓ Aprovar
                            </button>
                        </form>
                        <form method="POST" action="{{ url_for('reservas.alterar_status', reserva_id=r.id) }}" class="inline">
                            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                            <input type="hidden" name="novo_status" value="rejeitada">
                            <button type="submit" class="px-2.5 py-1 rounded-lg bg-rose-600 hover:bg-rose-700 text-white text-xs font-semibold">
                                ✕ Recusar
                            </button>
                        </form>
                        {% endif %}

                        {% if r.status in ('pendente', 'aprovada') and (r.usuario_id == g.usuario.id or tem_permissao('reservas.cancelar_qualquer')) %}
                        <form method="POST" action="{{ url_for('reservas.alterar_status', reserva_id=r.id) }}" class="inline">
                            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                            <input type="hidden" name="novo_status" value="cancelada">
                            <button type="submit" class="px-2.5 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold">
                                Cancelar
                            </button>
                        </form>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="py-10 text-center text-slate-500">
                        Nenhuma reserva encontrada para os filtros selecionados.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    {{ renderizar_paginacao(paginacao, '#container-tabela-reservas') }}
</div>
{% endblock %}
```

---

## 6. Criando o Formulário de Solicitação de Reserva (`app/templates/reservas/form.html`)

Repare como o campo `<select name="sala_id">` deste formulário conversa com o botão **Reservar** que colocamos lá no Catálogo de Salas (Aula 07):
* Se o usuário veio do Catálogo de Salas clicando em **Reservar** na sala de ID `3` (`/reservas/nova?sala_id=3`), a variável `sala_selecionada` vale `3` e a opção `{% if sala_selecionada == s.id %}selected{% endif %}` já deixa aquela sala selecionada automaticamente!
* Além disso, se o usuário cometer um erro ao preencher o formulário (por exemplo, escolher uma capacidade maior do que a sala comporta ou cair em conflito de horário), o Python devolve `sala_selecionada=sala_id` para que ele não precise selecionar a sala novamente.

Abra o arquivo **`app/templates/reservas/form.html`** e digite o código abaixo:

```html
<!-- app/templates/reservas/form.html -->
{% extends "base.html" %}
{% block titulo %}Nova Reserva de Sala — SalaFácil{% endblock %}

{% block conteudo %}
<div class="max-w-3xl mx-auto">
    <div class="mb-6 flex items-center justify-between">
        <div>
            <h2 class="text-2xl font-bold text-slate-900">Solicitar Reserva de Sala</h2>
            <p class="text-sm text-slate-500">O sistema verificará automaticamente a capacidade e conflitos de horário</p>
        </div>
        <a href="{{ url_for('reservas.listar') }}" class="text-sm text-slate-600 hover:text-slate-900 font-medium">
            ← Voltar para a Agenda
        </a>
    </div>

    <form method="POST" class="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 space-y-5">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-slate-700 mb-1">Sala Desejada</label>
                <select name="sala_id" required class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm bg-white">
                    <option value="">Selecione uma sala disponível...</option>
                    {% for s in salas %}
                    <option value="{{ s.id }}" {% if sala_selecionada == s.id %}selected{% endif %}>
                        {{ s.codigo }} — {{ s.nome }} (Até {{ s.capacidade }} lugares • {{ s.bloco }})
                    </option>
                    {% endfor %}
                </select>
            </div>

            <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-slate-700 mb-1">Título do Evento / Aula / Reunião</label>
                <input type="text" name="titulo" required maxlength="150" value="{{ dados.get('titulo', '') }}"
                       placeholder="Ex: Defesa de TCC / Reunião de Planejamento"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">Finalidade</label>
                <input type="text" name="finalidade" required maxlength="255" value="{{ dados.get('finalidade', '') }}"
                       placeholder="Ex: Aula Prática, Workshop, Entrevista"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">Nº Estimado de Participantes</label>
                <input type="number" name="participantes_estimados" min="1" max="5000" required
                       value="{{ dados.get('participantes_estimados', 10) }}"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">Data da Reserva</label>
                <input type="date" name="data_reserva" required value="{{ dados.get('data_reserva', '') }}"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div class="grid grid-cols-2 gap-3">
                <div>
                    <label class="block text-sm font-semibold text-slate-700 mb-1">Início</label>
                    <input type="time" name="hora_inicio" required value="{{ dados.get('hora_inicio', '') }}"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
                </div>
                <div>
                    <label class="block text-sm font-semibold text-slate-700 mb-1">Término</label>
                    <input type="time" name="hora_fim" required value="{{ dados.get('hora_fim', '') }}"
                           class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
                </div>
            </div>

            <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-slate-700 mb-1">Observações / Necessidades Específicas (Opcional)</label>
                <textarea name="observacoes" rows="3"
                          placeholder="Ex: Solicito adaptador HDMI e liberação da chave 15 minutos antes."
                          class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">{{ dados.get('observacoes', '') }}</textarea>
            </div>
        </div>

        <div class="pt-4 flex justify-end gap-3">
            <a href="{{ url_for('reservas.listar') }}"
               class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold transition">
                Cancelar
            </a>
            <button type="submit"
                    class="px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-sm text-sm transition">
                Confirmar Agendamento
            </button>
        </div>
    </form>
</div>
{% endblock %}
```

### Linha por linha das novidades dos templates de reservas

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `{% extends layout %}` (no `index.html`) | Escolhe o molde completo ou parcial conforme o pedido (Aula 06, seção 8.1). | Buscas dinâmicas mais leves. | Funciona, só que mais pesado. |
| `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` (nos 3 mini-formulários e no formulário de nova reserva) | A ficha numerada da Aula 05. | Cada botão (Aprovar, Recusar, Cancelar) é um `POST` e precisa dela. | Os botões respondem *"formulário inválido"* e nada acontece. |
| `value="{{ dados.get('titulo', '') }}"` (e os demais campos) | Reexibe o que a pessoa digitou quando a reserva é recusada. | Após um conflito de horário, a pessoa só precisa ajustar a hora, e não redigitar tudo. | Todos os campos voltariam vazios a cada recusa. |
| `<textarea ...>{{ dados.get('observacoes', '') }}</textarea>` | No `<textarea>` o texto vai **entre** as tags (ele não tem atributo `value`). | Mantém as observações digitadas. | O campo de observações sempre voltaria vazio. |
| `max="5000"`, `maxlength="150"` etc. | Limites de tamanho espelhando a validação do Python e as colunas do banco. | Avisam o usuário antes do envio. | O aviso só apareceria depois do envio (a proteção real continua no servidor). |

---

## 7. Roteiro Completo de Testes na Prática!

Com o servidor rodando (`python run.py`), vamos testar todas as regras de negócio da Agenda de Reservas:

1. **Teste 1 (Solicitação como Professora $\rightarrow$ Nasce `Pendente`):**  
   Faça login com **`beatriz@salafacil.com`** (senha `123456`). Na **📅 Agenda de Reservas**, observe que a Beatriz só vê o botão **Cancelar** nas reservas que foram criadas por ela mesma!  
   Clique em **+ Nova Reserva** e agende a sala **`LAB-101`** para amanhã das **`08:00` às `10:00`** com 25 participantes. Ao salvar, veja a mensagem *"Solicitação enviada! Aguardando aprovação do gestor."* e o status amarelo **Pendente**.
2. **Teste 2 (Tentativa de Conflito de Horário):**  
   Clique novamente em **+ Nova Reserva**, selecione a mesma sala **`LAB-101`**, a mesma data de amanhã e tente agendar das **`09:00` às `11:00`**.  
   **Resultado:** O sistema bloqueia o agendamento na hora e exibe um alerta vermelho informando exatamente qual evento já está ocupando aquela sala das `08:00` às `10:00` e quem é o solicitante!
3. **Teste 3 (Horário Adjacente / Vizinho Permitido):**  
   Na mesma tela, mude o horário de início para **`10:00`** e o término para **`12:00`**. Clique em **Confirmar Agendamento** e veja que a reserva é aceita normalmente, pois começa exatamente quando a anterior termina!
4. **Teste 4 (Validação de Lotação da Sala):**  
   Tente criar uma reserva no **`EST-501 — Estúdio de Gravação e Podcast`** (que comporta até **6 lugares**) informando **15 participantes**. Veja o bloqueio imediato informando o limite da sala!
5. **Teste 5 (Aprovação pelo Gestor):**  
   Saia da conta da Beatriz e faça login com **`gestor@salafacil.com`** (senha `123456`). Filtre a agenda pelo status **Pendentes** e clique em **✓ Aprovar** nas reservas da Beatriz!
6. **Teste 6 (Decisão sobre uma reserva que já não está pendente):**  
   Como Carlos, abra a agenda filtrada por **Pendentes** em **duas abas**. Na aba 1, clique em **✕ Recusar** em uma reserva. Volte à aba 2 (que ainda mostra o botão **✓ Aprovar**, pois não foi atualizada) e clique em **Aprovar** na mesma reserva. O sistema responde *"Só é possível decidir reservas que ainda estão pendentes"*: o servidor confere o estado **atual** e não deixa uma reserva recusada voltar à vida (o que poderia causar conflito de horário). Esconder o botão não bastava; a regra mora no `WHERE ... AND status = 'pendente'` do `UPDATE`.
7. **Teste 7 (Data no passado e horário inválido):**  
   Tente criar uma reserva com data de ontem: *"Não é permitido cadastrar reservas em datas passadas."* O formulário volta **com todos os outros campos preenchidos**.
8. **Teste 8 (O clique simultâneo — opcional, para quem quer ver a trava funcionando):**  
   Abra **duas abas** do navegador (mesma conta), preencha em ambas o **mesmo** formulário (mesma sala, data e horário livres) e clique em **Confirmar Agendamento** quase juntas. Apenas **uma** reserva é criada; a outra aba recebe a mensagem de conflito. Sem a transação com `FOR UPDATE`, as duas poderiam ser gravadas.

---

## 8. Guia de Sobrevivência no Laboratório (Erros Comuns na Aula 09)

| Sintoma / Mensagem de Erro | Causa Mais Provável | Como Resolver Rapidamente |
| :--- | :--- | :--- |
| `mysql.connector.errors.ProgrammingError: Not enough parameters for the SQL statement` | Na função `TIME_FORMAT`, o símbolo `%` foi escrito simples (`'%H:%i'`) em vez de duplicado (`'%%H:%%i'`). | Sempre que uma query SQL tiver marcadores `%s`, duplique qualquer `%` literal da query para **`%%`** (`'%%H:%%i'`). |
| `AttributeError: 'str' object has no attribute 'strftime'` ao abrir `/reservas/` | A coluna `data_reserva` na tabela `reservas` não foi criada com o tipo `DATE` no `sql/schema.sql`. | Como a coluna `data_reserva` é do tipo `DATE`, o `mysql-connector-python` já a converte automaticamente para um objeto `datetime.date` do Python, permitindo chamar `.strftime('%d/%m/%Y')` direto no Jinja2! |
| `mysql.connector.errors.DatabaseError: 1205 (HY000): Lock wait timeout exceeded` | Uma transação anterior ficou "aberta" segurando a trava da sala (por exemplo, um `return` ou erro dentro do `with` que impediu o fim normal do bloco, ou uma aba travada em depuração). | Pare e reinicie o servidor (`CTRL + C`, `python run.py`); as travas são soltas. Garanta que o código dentro do `with transacao()` termine sempre. |
| `jinja2.exceptions.UndefinedError: 'dados' is undefined` ao abrir `/reservas/nova` | Algum `render_template("reservas/form.html", ...)` não passa `dados=request.form`. | Confira os 3 `render_template` do formulário na rota `criar` (erros de validação, erro de sala/conflito e primeira abertura). |
| `mysql.connector.errors.IntegrityError: 3819 ... Check constraint 'ck_reserva_horario' is violated` | A validação do Python foi removida ou burlada e o banco (o "segundo porteiro") barrou a reserva com término antes do início. | Restaure a conferência `hora_inicio >= hora_fim` na rota `criar`. |
| Tento agendar das `14:00` às `13:00` e não salva. | A validação cronológica `if hora_inicio >= hora_fim:` detectou que o horário de término é menor ou igual ao início. | Informe sempre um horário de término posterior ao horário de início no mesmo dia. |

---

## 9. Exercícios Práticos de Fixação

1. **Desafio 1 (Exibindo o Nome do Aprovador na Tabela):**  
   Repare que na query SQL da rota `listar()` nós já trouxemos a coluna `ap.nome AS aprovador_nome`, mas na tabela HTML (`reservas/index.html`) ainda não estamos exibindo quem aprovou a reserva!  
   Edite a coluna **Status** do `app/templates/reservas/index.html` para que, logo abaixo do badge verde `Aprovada` (ou vermelho `Rejeitada`), apareça em letras pequenas `por {{ r.aprovador_nome }}` caso `r.aprovador_nome` exista.
2. **Desafio 2 (Horário de Funcionamento da Instituição):**  
   A instituição só funciona das **07:00 às 22:30**. Hoje o sistema aceita uma reserva às 03:00 da madrugada. Crie duas constantes no topo de `app/blueprints/reservas.py` (`HORA_ABERTURA = "07:00"` e `HORA_FECHAMENTO = "22:30"`) e acrescente na lista `erros` da rota `criar()` uma validação que recuse reservas fora desse intervalo. *(Dica: como o formato `HH:MM` com dois dígitos se ordena como texto, você pode comparar `hora_inicio < HORA_ABERTURA` diretamente, só depois de `hora_valida` ter confirmado que são horas reais.)*

<details>
<summary><strong>💡 Clique aqui para ver o Gabarito Comentado dos Exercícios</strong></summary>

**1. Resolução do Desafio 1 (em `app/templates/reservas/index.html`, na célula `<td>` do Status):**
```html
                    <td class="py-4 px-6 text-center">
                        {% if r.status == 'aprovada' %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">Aprovada</span>
                        {% elif r.status == 'pendente' %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">Pendente</span>
                        {% elif r.status == 'rejeitada' %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">Rejeitada</span>
                        {% else %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-200 text-slate-700">Cancelada</span>
                        {% endif %}

                        {% if r.aprovador_nome and r.status in ('aprovada', 'rejeitada') %}
                        <p class="text-[11px] text-slate-400 mt-1">por {{ r.aprovador_nome }}</p>
                        {% endif %}
                    </td>
```

**2. Resolução do Desafio 2 (em `app/blueprints/reservas.py`):**
Adicione abaixo de `STATUS_VALIDOS`:
```python
HORA_ABERTURA = "07:00"
HORA_FECHAMENTO = "22:30"
```
E, na rota `criar()`, troque o bloco das horas por:
```python
        if not (hora_valida(hora_inicio) and hora_valida(hora_fim)):
            erros.append("Informe horários válidos de início e término.")
        elif hora_inicio >= hora_fim:
            erros.append("O horário de término deve ser posterior ao horário de início.")
        elif hora_inicio < HORA_ABERTURA or hora_fim > HORA_FECHAMENTO:
            erros.append(f"As reservas devem ficar entre {HORA_ABERTURA} e {HORA_FECHAMENTO}.")
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `HORA_ABERTURA = "07:00"` / `HORA_FECHAMENTO = "22:30"` | Constantes com os limites do funcionamento. | Mudar o horário é editar **um** lugar. | Os horários ficariam "escondidos" dentro do `if`. |
| `elif hora_inicio < HORA_ABERTURA or hora_fim > HORA_FECHAMENTO:` | Recusa se começa antes de abrir **ou** termina depois de fechar. | A ordem dos `elif` garante que só comparamos horas válidas e já conferidas. | Reservas de madrugada seriam aceitas. |
| `f"...entre {HORA_ABERTURA} e {HORA_FECHAMENTO}."` | Mensagem que mostra os limites reais. | O usuário sabe exatamente o que corrigir. | A mensagem seria genérica ou ficaria desatualizada se os horários mudassem. |
</details>

---

## O Que Vem a Seguir?

O coração operacional do **SalaFácil** está pulsando! Já temos autenticação, controle de permissões personalizadas, catálogo de salas, gestão de usuários e agenda inteligente de reservas com prevenção de conflitos!

Na **Aula 10 (Nossa Aula Final!)**, construiremos o módulo de **Relatórios Gerenciais, Indicadores (KPIs), Paginação Dupla Independente e Exportação CSV para Excel**: você aprenderá a fazer cálculos analíticos de horas ocupadas diretamente no MySQL (`TIMESTAMPDIFF` e `CASE WHEN`), controlar duas tabelas paginadas na mesma tela sem que uma interfira na outra e gerar arquivos `.csv` com codificação UTF-8 BOM!

---
<!-- nav -->
| Anterior | Índice | Próxima |
| :--- | :---: | ---: |
| [← Aula 08 — Usuários e Matriz de Permissões](./aula_08_modulo_usuarios_matriz_permissoes.md) | [📚 Índice do Curso](./README.md) | [Aula 10 — Relatórios e Exportação CSV →](./aula_10_relatorios_gerenciais_exportacao_csv.md) |