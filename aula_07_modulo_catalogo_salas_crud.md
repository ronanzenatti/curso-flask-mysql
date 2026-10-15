# Aula 07 — Módulo de Catálogo de Salas (CRUD Completo com Busca Dinâmica e Paginação)

Na **Aula 06**, construímos as três peças do nosso motor universal de listagens: o paginador SQL no Python (`app/utils/pagination.py`), a macro visual de botões (`app/templates/components/paginacao.html`) e o controlador de busca em tempo real (`app/static/js/tabela_dinamica.js`).

Agora chegou a hora de ver esse motor brilhando na prática! Nesta **Aula 07**, vamos construir nosso primeiro módulo operacional completo: o **Catálogo de Salas e Laboratórios**.

Escolhemos começar pelo módulo de **Salas** por um motivo didático muito importante: ele é o exemplo perfeito de um **CRUD completo** sobre uma tabela, permitindo que você domine:
1. O que significa a sigla **CRUD** e como cada operação se conecta a uma rota Flask e a uma permissão personalizada.
2. O truque do **`WHERE 1=1`** e do operador **`LIKE %s`** para montar filtros dinâmicos em múltiplas colunas no MySQL.
3. Como construir um **Formulário Unificado (`salas/form.html`)** que serve tanto para **Cadastrar** uma sala nova quanto para **Editar** uma sala existente.
4. Por que rotas de exclusão devem usar obrigatoriamente o método **`POST`** e como impedir que uma sala com histórico de reservas seja apagada por engano.

---

## 1. O Que é um CRUD e Como Ele se Conecta às Permissões?

No mercado de desenvolvimento de software, você ouvirá a sigla **CRUD** todos os dias. Ela representa as **4 operações fundamentais** de qualquer cadastro em um banco de dados:

| Letra | Operação | Comando SQL | Rota no nosso `salas.py` | Permissão Exigida |
| :---: | :--- | :--- | :--- | :--- |
| **C** | **Create** (Criar) | `INSERT INTO salas ...` | `GET/POST /salas/nova` (`salas.criar`) | `salas.criar` |
| **R** | **Read** (Ler / Listar) | `SELECT * FROM salas ...` | `GET /salas/` (`salas.listar`) | `salas.visualizar` |
| **U** | **Update** (Atualizar) | `UPDATE salas SET ...` | `GET/POST /salas/<id>/editar` (`salas.editar`) | `salas.editar` |
| **D** | **Delete** (Excluir) | `DELETE FROM salas ...` | `POST /salas/<id>/excluir` (`salas.excluir`) | `salas.excluir` |

Repare como a nossa modelagem da Aula 03 se encaixa como uma luva aqui: cada uma das 4 rotas do CRUD de Salas é protegida por sua própria chave de permissão individual! Assim:
* A professora **Beatriz (`beatriz@salafacil.com`)** tem apenas `salas.visualizar`: ela consulta o catálogo e clica em **Reservar**, mas não vê os botões de criar, editar ou excluir salas.
* O **Carlos Gestor (`gestor@salafacil.com`)** tem `salas.visualizar`, `salas.criar` e `salas.editar`, mas **não** tem `salas.excluir`: ele pode cadastrar salas novas e colocar salas em manutenção, mas o botão **Excluir** não aparece para ele.
* A **Ana Administradora (`admin@salafacil.com`)** possui todas as 4 chaves do módulo de salas.

---

## 2. Entendendo a Lógica das Consultas antes de Codificar

Antes de substituirmos o esqueleto provisório de `app/blueprints/salas.py` pelo código definitivo, vamos entender três técnicas muito elegantes que usaremos dentro dele:

### 2.1 — O Truque do `WHERE 1=1` nas Buscas Dinâmicas
Na rota `listar()`, o usuário pode:
* Não digitar nada (quer ver todas as salas);
* Digitar apenas um texto na busca (`?q=Projetor`);
* Digitar apenas uma capacidade mínima (`?capacidade_min=30`);
* Ou preencher **os dois filtros ao mesmo tempo** (`?q=Projetor&capacidade_min=30`)!

Se começássemos a query apenas com `"SELECT * FROM salas"`, teríamos que ficar fazendo vários `if/else` complicados no Python para descobrir se o próximo filtro deve começar com a palavra `WHERE` ou com a palavra `AND`.

Ao iniciar a consulta escrevendo:
```python
sql = "SELECT * FROM salas WHERE 1=1"
```
Como `1=1` é sempre verdadeiro no SQL, a cláusula `WHERE` já está aberta! A partir daí, qualquer filtro opcional que o usuário preencher pode ser simplesmente colado no final começando com **`AND`**:
```python
if busca:
    sql += " AND (codigo LIKE %s OR nome LIKE %s OR bloco LIKE %s OR recursos LIKE %s)"
if capacidade_min.isdigit():
    sql += " AND capacidade >= %s"
```

### 2.2 — Como Funciona o Operador `LIKE` com `%` no MySQL?
No SQL, o sinal de igual (`=`) exige uma correspondência exata (`nome = 'Auditório'` não encontraria `'Auditório Principal Tiradentes'`).
Já o operador **`LIKE`** combinado com o curinga **`%`** (que significa *"qualquer texto antes ou depois"*) permite buscar **pedaços de palavras**:
* No Python, montamos `termo = f"%{busca}%"`. Se o usuário digitar `"Laser"`, a variável `termo` vira `"%Laser%"`.
* Como queremos que uma única caixa de pesquisa encontre o termo caso ele esteja no **código** (`LAB-101`), no **nome** (`Laboratório`), no **bloco** (`Bloco A`) **OU** nos **recursos** (`Projetor Laser`), passamos o `termo` 4 vezes para a lista `params`:
  `params.extend([termo, termo, termo, termo])`.
* **Um cuidado:** o `%` dentro de `termo` é só um texto comum enviado como **parâmetro** (`%s`); por isso não conflita com os marcadores. Mas, se o usuário digitar `%` ou `_` na busca, eles funcionam como curingas do `LIKE` (isto traz resultados a mais, não é uma falha de segurança). Também lembre da Aula 03: `LIKE '%termo%'` não usa índice. Para o catálogo de uma faculdade isso é imperceptível.

### 2.3 — Exclusão Segura: Por Que Testar `reservas` Antes do `DELETE`?
Lembra que na Aula 03 configuramos a chave estrangeira `fk_reserva_sala` com a regra **`ON DELETE RESTRICT`**?
Se uma sala já tiver reservas registradas no banco e tentarmos rodar `DELETE FROM salas WHERE id = %s` direto, o MySQL recusará a operação lançando uma exceção técnica.
Em vez de deixar um erro estourar, na rota `excluir(sala_id)` nós primeiro fazemos uma pergunta educada ao MySQL:
```python
vinculo = query_one("SELECT COUNT(*) AS total FROM reservas WHERE sala_id = %s", (sala_id,))
```
* Se `vinculo["total"] > 0`, nós avisamos o usuário com uma mensagem amigável (`flash(..., "aviso")`) explicando quantas reservas aquela sala possui no histórico e orientando a alterar o status dela para **"Em Manutenção / Indisponível"**!
* Se `vinculo["total"] == 0` (uma sala recém-criada que nunca foi usada), o `DELETE` é executado com sucesso!

### 2.4 — Nunca Confie no Que Vem do Formulário: o Fiscal de Dados (`app/utils/validacao.py`)

Até aqui, os formulários tinham atributos como `required` e `min="1"`. Eles são úteis para o **usuário** (o navegador avisa na hora), mas **não protegem o sistema**: qualquer pessoa pode abrir o *Inspecionar Elemento*, apagar o `required` ou enviar um pedido sem passar pelo formulário (por exemplo, com um programa). Pense assim:

> **Analogia da portaria do prédio:** o aviso "Entrada somente com crachá", colado na porta, orienta os moradores honestos. Mas quem realmente barra um intruso é o **porteiro conferindo o crachá**. O `required` do HTML é o aviso na porta; a validação no Python é o porteiro. **Toda conferência importante precisa existir no servidor.**

Vamos criar um arquivo pequeno com as conferências que usaremos em vários módulos. Abra **`app/utils/validacao.py`** e digite:

```python
# app/utils/validacao.py
import re

# Código de sala: 2 a 25 caracteres; letras MAIÚSCULAS, números e hífen (ex.: LAB-101)
PADRAO_CODIGO_SALA = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,24}$")


def inteiro_no_intervalo(texto, minimo, maximo):
    """Converte o texto em número inteiro e confere o intervalo. Devolve o número ou None."""
    try:
        valor = int(texto)
    except (TypeError, ValueError):
        return None
    if minimo <= valor <= maximo:
        return valor
    return None
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `import re` | Traz o módulo de **expressões regulares**: "moldes" para conferir se um texto tem o formato certo. | Precisamos dele para o formato do código da sala. | `NameError: name 're' is not defined`. |
| `re.compile(r"^[A-Z0-9][A-Z0-9-]{1,24}$")` | Cria o molde uma vez e o guarda. Leitura: `^` = começo do texto; `[A-Z0-9]` = um caractere que seja letra maiúscula ou número; `[A-Z0-9-]{1,24}` = de 1 a 24 caracteres que sejam letras maiúsculas, números ou hífen; `$` = fim do texto. O `r` antes das aspas diz ao Python para não interpretar as barras. | Garante códigos curtos e padronizados (`LAB-104`), sem espaços, aspas ou símbolos estranhos. Total de 2 a 25 caracteres, o limite da coluna `codigo` do banco. | Sem o molde, o código poderia ter 80 caracteres (erro do MySQL, tela de erro 500) ou conter símbolos que quebrariam o JavaScript e o HTML. |
| `def inteiro_no_intervalo(texto, minimo, maximo)` | Função que transforma texto em número **e** confere o intervalo permitido. | Ex.: capacidade de sala entre 1 e 2000. | Teríamos que repetir o mesmo `try/except` em todo formulário. |
| `try: valor = int(texto)` / `except (TypeError, ValueError): return None` | Tenta converter. Se vier vazio (`None`) ou texto como `"abc"` ou `"3,5"`, em vez de quebrar a página devolve `None`. | Um valor inválido é um caso **esperado**, e não um erro do programa. | Um `int("abc")` derrubaria a página com erro 500. |
| `if minimo <= valor <= maximo: return valor` | Em Python é possível encadear comparações: "valor está entre mínimo e máximo?". | Rejeita `0`, `-5` e números gigantes como `99999999999`. | Capacidades absurdas chegariam ao banco, e valores negativos seriam recusados apenas pelo `CHECK`, com erro técnico. |
| `return None` (final) | Sinaliza "valor inválido". | O chamador testa `if capacidade is None`. | A função devolveria `None` mesmo para valores válidos fora do `if`. |

---

## 3. Codificando o Blueprint Completo de Salas (`app/blueprints/salas.py`)

Abra o arquivo **`app/blueprints/salas.py`** (substituindo o esqueleto provisório da Aula 05) e digite o código completo abaixo:

```python
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
```

### Detalhes técnicos do `salas.py` que valem ouro:
* **`.strip().upper()` no código da sala:** Se o usuário digitar `" lab-104 "` com espaços ou letras minúsculas, `.strip()` remove os espaços das pontas e `.upper()` converte para `"LAB-104"`, mantendo o banco padronizado!
* **`inteiro_no_intervalo(request.form.get("capacidade"), 1, 2000)`**: Antes usávamos `request.form.get("capacidade", 10, type=int) or 10`, um truque com defeito: quem digitava `0` recebia silenciosamente `10`, pois `0 or 10` vale `10` em Python. Agora o valor inválido (`0`, `-5`, `abc`, `99999`) resulta em `None` e a pessoa recebe uma **mensagem de erro clara** em vez de uma capacidade que ela não pediu.
* **Por que `excluir` aceita apenas `methods=["POST"]`?**  
  Nunca crie uma rota de exclusão que aceite `GET` (um link comum `<a href="...">`). Se um link `GET` apagasse dados do banco, um navegador pré-carregando links em segundo plano poderia apagar salas acidentalmente! Operações destrutivas (`DELETE`) ou que alteram dados (`INSERT`/`UPDATE`) devem ser disparadas sempre via formulário **`POST`** (e, desde a Aula 05, com a ficha `csrf_token`).

### Linha por linha das novidades do `salas.py`

#### A função auxiliar `_ler_dados_formulario(exige_codigo)`

> **Por que uma função à parte?** Criar e editar uma sala usam **as mesmas regras**. Em vez de escrevê-las duas vezes (e esquecer de atualizar uma delas depois), escrevemos uma vez e chamamos nos dois lugares. O `_` no início do nome é uma convenção: "função de uso interno deste arquivo".

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `dados = {"codigo": request.form.get("codigo", "").strip().upper(), ...}` | Monta um dicionário com tudo que veio do formulário, já "limpo" (`strip` tira espaços das pontas, `upper` põe o código em maiúsculas). | Um único lugar lê o formulário. O segundo argumento `""` evita `None` se o campo não vier. | Cada rota teria sua própria cópia, e as cópias acabariam diferentes. |
| `"capacidade": inteiro_no_intervalo(...)` | Já converte a capacidade para número ou `None`. | A conversão e a conferência acontecem juntas. | Teríamos `try/except` espalhado. |
| `erros = []` | Uma lista vazia para juntar **todas** as mensagens de problema. | O usuário vê todos os erros de uma vez, e não um por tentativa. | Ele corrigiria um erro, enviaria de novo e descobriria o próximo. |
| `if exige_codigo and not PADRAO_CODIGO_SALA.match(...)` | Só confere o código na **criação** (na edição o código não muda). `.match` devolve algo "verdadeiro" se o texto segue o molde. | O código é a identidade da sala e precisa estar no formato certo. | Códigos como `' OR 1=1` ou textos de 200 letras seriam aceitos. |
| `if not dados["nome"] or len(dados["nome"]) > 120` | Rejeita nome vazio ou maior que a coluna do banco (120). | Sem isso, nome vazio passaria; nome grande geraria erro técnico do MySQL (tela 500). | Salas sem nome ou erro 500 com textos longos. |
| `return dados, erros` | Devolve **dois** valores de uma vez (uma tupla). | Quem chama recebe os dados limpos e a lista de erros. | A rota não saberia se pode ou não gravar. |

#### A rota `criar()`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `dados, erros = _ler_dados_formulario(exige_codigo=True)` | Chama a função auxiliar e "desembrulha" os dois valores. | Valida antes de tocar no banco. | Dados inválidos chegariam ao MySQL. |
| `if not erros and query_one("SELECT id FROM salas WHERE codigo = %s", ...)` | Só vai ao banco checar duplicidade se o resto está certo (`and` não avalia o lado direito quando o esquerdo é falso). | Economiza uma consulta e evita mensagens redundantes. | Funcionaria, mas consultaria o banco à toa. |
| `for erro in erros: flash(erro, "erro")` | Mostra cada problema numa caixinha vermelha. | Retorno claro ao usuário. | O usuário não saberia o que corrigir. |
| `render_template("salas/form.html", sala=None, dados=request.form)` | Devolve o formulário e **reenvia o que a pessoa digitou** em `dados`. | Antes, qualquer erro apagava todos os campos e a pessoa tinha que digitar tudo de novo. | Os campos voltam vazios a cada erro. |

#### A rota `editar()` (novidades)

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `SELECT COUNT(*) AS total, COALESCE(MAX(participantes_estimados), 0) AS maior_grupo FROM reservas WHERE ... data_reserva >= CURDATE() AND status IN ('pendente','aprovada')` | Conta as reservas **futuras** ainda ativas da sala e descobre o maior grupo previsto. `CURDATE()` é a data de hoje no MySQL; `COALESCE(..., 0)` troca `NULL` por `0` quando não há reservas. | Precisamos saber se mudar a sala vai prejudicar reservas que já existem. | Seria possível reduzir a capacidade para 5 lugares com uma reserva de 40 pessoas já aprovada. |
| `if dados["capacidade"] < futuras["maior_grupo"]` | Bloqueia a redução de capacidade abaixo do maior grupo já reservado. | Mantém o banco coerente. | Reservas aprovadas ficariam "impossíveis" de acontecer. |
| `if ativa == 0 and futuras["total"] > 0: flash(..., "aviso")` | Ao colocar a sala em manutenção, **avisa** quantas reservas futuras continuam valendo. | O gestor decide a quem avisar, em vez de a sala "sumir" silenciosamente. | Reservas continuariam em sala em manutenção sem ninguém perceber. |

---

## 4. Criando o Template da Listagem de Salas (`app/templates/salas/index.html`)

Agora vamos criar a tela do Catálogo de Salas conectada ao nosso motor da Aula 06. Repare em três conexões importantes neste HTML:
1. Na linha 2, importamos a nossa macro de paginação:
   `{% from "components/paginacao.html" import renderizar_paginacao %}`
2. No `<form>`, colocamos `class="js-form-filtro"` e `data-target="#container-tabela-salas"`.
3. Nos campos de busca (`q`) e capacidade mínima (`capacidade_min`), colocamos `class="js-busca-dinamica"`, e no seletor de itens por página (`per_page`), colocamos `class="js-filtro-imediato"`.

Abra o arquivo **`app/templates/salas/index.html`** e digite o código abaixo:

```html
<!-- app/templates/salas/index.html -->
{% extends layout %}
{% from "components/paginacao.html" import renderizar_paginacao %}
{% block titulo %}Catálogo de Salas — SalaFácil{% endblock %}

{% block conteudo %}
<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
    <div>
        <h2 class="text-2xl font-bold text-slate-900">Catálogo de Salas e Laboratórios</h2>
        <p class="text-sm text-slate-500">Pesquise salas por código, bloco, capacidade ou equipamentos disponíveis</p>
    </div>
    {% if tem_permissao('salas.criar') %}
    <a href="{{ url_for('salas.criar') }}"
       class="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-sm transition">
        + Cadastrar Sala
    </a>
    {% endif %}
</div>

<form method="GET" action="{{ url_for('salas.listar') }}"
      data-target="#container-tabela-salas"
      class="js-form-filtro bg-white p-4 rounded-2xl shadow-sm border border-slate-200 mb-6 flex flex-col md:flex-row gap-4">
    <div class="flex-1">
        <input type="text" name="q" value="{{ busca }}"
               placeholder="Pesquisar sala por código (ex: LAB-101), nome, bloco ou recurso (ex: Projetor)..."
               class="js-busca-dinamica w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 outline-none text-sm">
    </div>
    <div class="w-full md:w-48">
        <input type="number" name="capacidade_min" value="{{ capacidade_min }}" min="1"
               placeholder="Capacidade mín."
               class="js-busca-dinamica w-full px-4 py-2 rounded-xl border border-slate-300 text-sm">
    </div>
    <select name="per_page" class="js-filtro-imediato px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white">
        {% for qtd in [5, 8, 10, 20] %}
        <option value="{{ qtd }}" {% if paginacao.por_pagina == qtd %}selected{% endif %}>{{ qtd }} por página</option>
        {% endfor %}
    </select>
</form>

<div id="container-tabela-salas" class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase">
                    <th class="py-3.5 px-6">Código</th>
                    <th class="py-3.5 px-6">Sala / Localização</th>
                    <th class="py-3.5 px-6 text-center">Capacidade</th>
                    <th class="py-3.5 px-6">Recursos e Equipamentos</th>
                    <th class="py-3.5 px-6 text-center">Status</th>
                    <th class="py-3.5 px-6 text-right">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 text-sm">
                {% for s in paginacao.itens %}
                <tr class="hover:bg-slate-50/80 transition">
                    <td class="py-4 px-6 font-mono font-bold text-indigo-700">{{ s.codigo }}</td>
                    <td class="py-4 px-6">
                        <p class="font-semibold text-slate-900">{{ s.nome }}</p>
                        <p class="text-xs text-slate-500">{{ s.bloco }}</p>
                    </td>
                    <td class="py-4 px-6 text-center font-semibold text-slate-800">{{ s.capacidade }} lugares</td>
                    <td class="py-4 px-6 text-slate-600 text-xs">{{ s.recursos }}</td>
                    <td class="py-4 px-6 text-center">
                        {% if s.ativa %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">Disponível</span>
                        {% else %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-100 text-amber-800">Manutenção</span>
                        {% endif %}
                    </td>
                    <td class="py-4 px-6 text-right whitespace-nowrap space-x-1.5">
                        {% if tem_permissao('reservas.criar') and s.ativa %}
                        <a href="{{ url_for('reservas.criar', sala_id=s.id) }}"
                           class="px-3 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold transition">
                            Reservar
                        </a>
                        {% endif %}
                        {% if tem_permissao('salas.editar') %}
                        <a href="{{ url_for('salas.editar', sala_id=s.id) }}"
                           class="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold transition">
                            Editar
                        </a>
                        {% endif %}
                        {% if tem_permissao('salas.excluir') %}
                        <form method="POST" action="{{ url_for('salas.excluir', sala_id=s.id) }}" class="inline"
                              data-mensagem="Deseja realmente excluir a sala {{ s.codigo }}?"
                              onsubmit="return confirm(this.dataset.mensagem);">
                            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                            <button type="submit"
                                    class="px-2.5 py-1.5 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold transition">
                                Excluir
                            </button>
                        </form>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="py-10 text-center text-slate-500">
                        Nenhuma sala encontrada com os critérios informados.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    {{ renderizar_paginacao(paginacao, '#container-tabela-salas') }}
</div>
{% endblock %}
```

### Linha por linha das novidades do `salas/index.html`

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `{% extends layout %}` (sem aspas) | Herda do molde indicado pela **variável** `layout`: `base.html` quando o navegador abre a página, `base_parcial.html` quando é a busca dinâmica (Aula 06, seção 8.1). | Devolve só o recheio nas buscas, sem refazer menu, scripts e mensagens. | Com `"base.html"` fixo tudo continua funcionando, mas cada letra digitada baixa a página completa e consome as mensagens flash. |
| `data-mensagem="Deseja realmente excluir a sala {{ s.codigo }}?"` | Guarda o texto da pergunta num atributo `data-` do formulário. O Jinja2 escapa o valor corretamente dentro de um atributo HTML. | Antes, o código da sala era colado **dentro de um trecho de JavaScript** (`confirm('...{{ s.codigo }}...')`). Se o texto tivesse uma aspa simples, ele poderia "fechar" o texto e executar comandos inesperados. | Voltaríamos a misturar dados do usuário com código JavaScript, uma porta aberta para XSS. |
| `onsubmit="return confirm(this.dataset.mensagem);"` | Ao enviar o formulário, abre a caixa "OK/Cancelar" com o texto guardado. `this` é o próprio formulário; `return false` (Cancelar) impede o envio. | A confirmação evita exclusões por clique acidental. | A exclusão aconteceria sem confirmação. |
| `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` | A ficha numerada da Aula 05. | Sem ela, `validar_csrf` bloqueia a exclusão. | O botão **Excluir** só mostra *"Sua sessão expirou ou o formulário é inválido"*. |

### Observe dois detalhes importantes na coluna de Ações da tabela acima:
1. **O botão `Reservar` (`{% if tem_permissao('reservas.criar') and s.ativa %}`):**  
   Ele verifica duas coisas ao mesmo tempo: se o usuário tem a permissão de solicitar reservas **E** se a sala está ativa (`s.ativa == 1`). Se uma sala for colocada em **Manutenção**, o botão **Reservar** some automaticamente da linha dela! Além disso, repare em `url_for('reservas.criar', sala_id=s.id)`: quando construirmos a tela de Nova Reserva na Aula 09, clicar nesse botão já abrirá o formulário com aquela sala pré-selecionada!
2. **A cláusula `{% else %}` dentro do `{% for s in paginacao.itens %}`:**  
   No Jinja2, todo laço `{% for %}` pode ter um bloco `{% else %}` antes do `{% endfor %}`. Esse bloco `{% else %}` só é desenhado se a lista `paginacao.itens` vier **vazia** (0 resultados), exibindo a linha *"Nenhuma sala encontrada com os critérios informados"*!

---

## 5. Formulário Unificado de Cadastro e Edição (`app/templates/salas/form.html`)

Em vez de criarmos dois arquivos quase idênticos (`criar_sala.html` e `editar_sala.html`), usamos um único template inteligente: **`app/templates/salas/form.html`**.

### Como o template sabe se está "Criando" ou "Editando"?
* Na rota `criar()`, chamamos `render_template("salas/form.html", sala=None)`. Logo, a variável `sala` vale `None` (Falso).
* Na rota `editar(sala_id)`, chamamos `render_template("salas/form.html", sala=sala)`. Logo, a variável `sala` contém o dicionário da sala vindo do MySQL (Verdadeiro)!

Dentro do HTML, usamos duas ferramentas do Jinja2:
1. **O Operador de Concatenação `~` (Til):** No Jinja2, o símbolo `~` junta textos como o `+` das strings: `'Editar Sala: ' ~ sala.codigo` gera `'Editar Sala: LAB-101'`.
2. **Expressão Ternária (`valor_se_verdadeiro if condicao else valor_se_falso`):**  
   Por exemplo, no atributo `value="{{ sala.nome if sala else '' }}"`: se estivermos editando uma sala, o campo já vem preenchido com o nome atual dela (`sala.nome`); se estivermos criando uma sala nova, o campo vem em branco (`''`)!

Abra o arquivo **`app/templates/salas/form.html`** e digite o código abaixo:

```html
<!-- app/templates/salas/form.html -->
{% extends "base.html" %}
{% block titulo %}{{ 'Editar Sala ' ~ sala.codigo if sala else 'Cadastrar Nova Sala' }} — SalaFácil{% endblock %}

{% block conteudo %}
<div class="max-w-3xl mx-auto">
    <div class="mb-6 flex items-center justify-between">
        <div>
            <h2 class="text-2xl font-bold text-slate-900">
                {{ 'Editar Sala: ' ~ sala.codigo if sala else 'Cadastrar Nova Sala' }}
            </h2>
            <p class="text-sm text-slate-500">
                {{ 'Atualize a capacidade, equipamentos ou status operacional da sala' if sala else 'Preencha as informações de identificação e infraestrutura do espaço' }}
            </p>
        </div>
        <a href="{{ url_for('salas.listar') }}" class="text-sm text-slate-600 hover:text-slate-900 font-medium">
            ← Voltar para o Catálogo
        </a>
    </div>

    <form method="POST" class="bg-white p-8 rounded-2xl shadow-sm border border-slate-200 space-y-5">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">Código Identificador</label>
                {% if sala %}
                <input type="text" value="{{ sala.codigo }}" disabled
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-100 text-slate-500 font-mono text-sm cursor-not-allowed">
                {% else %}
                <input type="text" name="codigo" required maxlength="25" placeholder="Ex: LAB-104 ou AUD-301"
                       value="{{ dados.get('codigo', '') }}"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 font-mono uppercase text-sm">
                {% endif %}
            </div>

            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">Capacidade Máxima (Lugares)</label>
                <input type="number" name="capacidade" min="1" max="2000" required
                       value="{{ dados.get('capacidade', sala.capacidade if sala else 30) }}"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-slate-700 mb-1">Nome da Sala / Espaço</label>
                <input type="text" name="nome" required maxlength="120"
                       value="{{ dados.get('nome', sala.nome if sala else '') }}"
                       placeholder="Ex: Laboratório de Engenharia de Software"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-slate-700 mb-1">Bloco / Andar / Localização</label>
                <input type="text" name="bloco" required maxlength="60"
                       value="{{ dados.get('bloco', sala.bloco if sala else '') }}"
                       placeholder="Ex: Bloco B - 2º Andar"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-slate-700 mb-1">Recursos Multimídia e Equipamentos</label>
                <input type="text" name="recursos" maxlength="255"
                       value="{{ dados.get('recursos', sala.recursos if sala else '') }}"
                       placeholder="Ex: 30 PCs, Projetor Full HD, Lousa de Vidro, Ar-condicionado"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            {% if sala %}
            {% set ativa_atual = dados.get('ativa', '1' if sala.ativa else '0') %}
            <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-slate-700 mb-1">Status Operacional da Sala</label>
                <select name="ativa" class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm bg-white">
                    <option value="1" {% if ativa_atual == '1' %}selected{% endif %}>Disponível para Reservas</option>
                    <option value="0" {% if ativa_atual == '0' %}selected{% endif %}>Em Manutenção / Indisponível</option>
                </select>
            </div>
            {% endif %}
        </div>

        <div class="pt-4 flex justify-end gap-3">
            <a href="{{ url_for('salas.listar') }}"
               class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold transition">
                Cancelar
            </a>
            <button type="submit"
                    class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-sm text-sm transition">
                {{ 'Salvar Alterações' if sala else 'Cadastrar Sala' }}
            </button>
        </div>
    </form>
</div>
{% endblock %}
```

### Linha por linha das novidades do `salas/form.html`

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` | A ficha numerada da Aula 05. | Todo formulário `POST` precisa dela. | Cadastrar e editar passam a responder *"formulário inválido"*. |
| `value="{{ dados.get('nome', sala.nome if sala else '') }}"` | Lê o texto que a pessoa **acabou de enviar** (`dados`, que é o `request.form`). Se não houver (primeira abertura), usa o valor da sala (na edição) ou vazio (no cadastro). | **Um campo, três situações:** formulário novo (vazio), edição (valor salvo) e correção após erro (o que a pessoa digitou). | Depois de um erro de validação, a pessoa teria de preencher todos os campos de novo. |
| `maxlength="120"`, `maxlength="60"`, `maxlength="25"`, `maxlength="255"` | Limita o tamanho que o navegador deixa digitar, igual ao tamanho das colunas do banco. | Evita erros por excesso de texto antes mesmo do envio. | O usuário só descobre o limite depois de enviar. *(Lembre: isso é conforto; quem garante é o Python.)* |
| `min="1" max="2000"` na capacidade | O navegador impede números fora do intervalo. | Espelha a regra de `inteiro_no_intervalo(..., 1, 2000)`. | O aviso aparece só depois do envio. |
| `{% set ativa_atual = dados.get('ativa', '1' if sala.ativa else '0') %}` | Cria uma variável do template com o status a mostrar: o que foi enviado ou, se nada, o status salvo na sala. | Mantém o `<select>` correto também após um erro de validação. | O seletor "voltaria" ao valor antigo depois de um erro. |

---

## 6. Testando o Catálogo de Salas Completo no Navegador!

Com o servidor rodando (`python run.py`), faça login como **`admin@salafacil.com`** (senha `123456`), clique em **🏢 Catálogo de Salas** no menu lateral esquerdo e execute este roteiro prático de validação:

1. **Teste 1 (Paginação Assíncrona):**  
   Como temos 10 salas no banco e o padrão é 8 por página, repare no rodapé da tabela: *"Exibindo 1 a 8 de 10 registros"*. Clique no botão **2** ou **Próxima →** e veja as 2 salas restantes carregarem instantaneamente sem piscar a página!
2. **Teste 2 (Pesquisa Dinâmica com Debounce):**  
   Clique na caixa de busca e digite **`Arduino`** (ou **`Podcast`**, ou **`Bloco B`**). Pare de digitar por meio segundo e veja a tabela filtrar sozinha para mostrar apenas as salas que possuem aquele equipamento ou bloco! Depois apague o texto e digite **`50`** no campo **Capacidade mín.** para ver apenas as salas que comportam 50 ou mais pessoas.
3. **Teste 3 (Cadastrando e Editando uma Sala):**  
   Clique em **+ Cadastrar Sala** e crie a sala **`LAB-999`** (*Laboratório de Testes*, *Bloco Z*, *Capacidade 20*, *Recursos: 20 PCs*). Ao salvar, veja ela aparecer na listagem! Em seguida, clique em **Editar** na `LAB-999` e mude o status dela para **Em Manutenção / Indisponível**. Repare que o badge dela muda para amarelo (*Manutenção*) e o botão **Reservar** some daquela linha!
4. **Teste 4 (Proteção contra Exclusão de Sala com Histórico vs. Exclusão Permitida):**  
   * Tente clicar em **Excluir** na sala **`LAB-101`** (que já possui reservas criadas pelo `seed_db.py`). O sistema bloqueará a exclusão e mostrará o aviso amarelo informando quantas reservas ela possui no histórico!
   * Agora clique em **Excluir** na sala **`LAB-999`** (que acabamos de criar e não tem reservas). Ela será removida do banco com sucesso!
5. **Teste 5 (Validação no servidor e formulário que "lembra"):**  
   Clique em **+ Cadastrar Sala**, preencha tudo, mas digite o código `lab 104!` (com espaço e símbolo) e salve. O sistema recusa com a mensagem sobre o formato do código **e mantém todos os outros campos preenchidos**. Corrija o código e salve.
6. **Teste 6 (Provando que a validação não depende do navegador):**  
   Edite `LAB-999`, abra o *Inspecionar Elemento* (`F12`), troque `min="1"` do campo capacidade por `min="-10"`, digite `-5` e salve. Mesmo sem a barreira do HTML, o Python recusa: *"A capacidade deve ser um número inteiro entre 1 e 2000"*.
7. **Teste 7 (Proteção das reservas futuras):**  
   Edite a sala `LAB-101` (que tem reservas futuras do seed) e tente reduzir a capacidade para `10`. O sistema bloqueia, pois já existe reserva futura para mais pessoas que isso.

---

## 7. Guia de Sobrevivência no Laboratório (Erros Comuns na Aula 07)

| Sintoma / Mensagem de Erro | Causa Mais Provável | Como Resolver Rapidamente |
| :--- | :--- | :--- |
| `BuildError: Could not build url for endpoint 'reservas.criar'` ao abrir `/salas/` | Na coluna de ações do `salas/index.html`, o botão *Reservar* chama `url_for('reservas.criar', sala_id=s.id)`, que só existirá se a rota `criar` estiver declarada em `reservas.py`. | Adicione uma rota provisória `@reservas_bp.route("/nova")` com `def criar(): return redirect(url_for("salas.listar"))` no seu esqueleto de `app/blueprints/reservas.py` até chegarmos na Aula 09! |
| Digito na busca de salas, mas quando clico na página 2 da paginação, a tabela não muda. | O atributo `data-target` do `<form>` (`#container-tabela-salas`) está diferente do `id` da `<div>` da tabela ou do segundo argumento de `renderizar_paginacao(paginacao, '#container-tabela-salas')`. | Os três lugares devem usar exatamente o mesmo seletor `#container-tabela-salas`. |
| `jinja2.exceptions.UndefinedError: 'dados' is undefined` ao abrir o formulário de sala. | Alguma rota (`criar` ou `editar`) chama `render_template("salas/form.html", ...)` sem o argumento `dados=request.form`. | Confira os **quatro** `render_template` do formulário em `salas.py`: todos precisam de `dados=request.form`. |
| `ModuleNotFoundError: No module named 'app.utils.validacao'` | O arquivo `app/utils/validacao.py` não foi criado ou está com outro nome. | Crie o arquivo exatamente em `app/utils/validacao.py` (seção 2.4). |
| Ao salvar o formulário aparece *"Sua sessão expirou ou o formulário é inválido"*. | Faltou `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` no formulário. | Adicione a linha logo abaixo da tag `<form method="POST">`. |
| Ao editar uma sala, o `codigo` não é alterado. | Por segurança de catálogo, no `salas/form.html` o campo `codigo` fica `disabled` (somente leitura) durante a edição para que o código patrimonial da sala não mude após criada. | Isso é intencional no projeto! Nome, bloco, capacidade, recursos e status `ativa` são editáveis normalmente. |

> 💡 **Dica importante sobre o botão "Reservar":**  
> Como o template `salas/index.html` já traz o botão `Reservar` apontando para `url_for('reservas.criar', sala_id=s.id)`, abra rapidinho o seu esqueleto provisório de **`app/blueprints/reservas.py`** (criado na Aula 05) e adicione estas 4 linhas no final dele para que o Flask já conheça o endereço `reservas.criar` antes da Aula 09:
> ```python
> @reservas_bp.route("/nova")
> def criar():
>     return redirect(url_for("salas.listar"))
> ```

---

## 8. Exercícios Práticos de Fixação

1. **Desafio 1 (Filtro por Status da Sala na Listagem):** Na tela `salas/index.html` e na função `listar()` de `app/blueprints/salas.py`, adicione um campo `<select name="ativa" class="js-filtro-imediato ...">` ao lado do campo de capacidade mínima permitindo filtrar entre **"Todos os Status"**, **"Somente Disponíveis (`1`)"** e **"Somente em Manutenção (`0`)"**.
2. **Desafio 2 (Testando Permissões do Gestor vs. Solicitante):** Faça logout da conta de Administrador e entre com **`gestor@salafacil.com`** (senha `123456`). Abra o **Catálogo de Salas** e verifique quais botões de ação aparecem para ele. Depois faça o mesmo teste com **`beatriz@salafacil.com`**.

<details>
<summary><strong>💡 Clique aqui para ver o Gabarito Comentado do Desafio 1</strong></summary>

**1. Em `app/blueprints/salas.py` (dentro da função `listar()`):**
```python
    status_ativa = request.args.get("ativa", "").strip()

    if status_ativa in ("0", "1"):
        sql += " AND ativa = %s"
        params.append(int(status_ativa))
```
*(E passe `status_ativa=status_ativa` no `render_template` final da função `listar()`).*

**2. Em `app/templates/salas/index.html` (dentro do `<form>`, antes do `<select name="per_page">`):**
```html
    <select name="ativa" class="js-filtro-imediato px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white">
        <option value="">Todos os Status</option>
        <option value="1" {% if status_ativa == '1' %}selected{% endif %}>Disponíveis</option>
        <option value="0" {% if status_ativa == '0' %}selected{% endif %}>Em Manutenção</option>
    </select>
```
</details>

---

## O Que Vem a Seguir?

Você acabou de construir seu primeiro CRUD completo no Flask com busca dinâmica em múltiplas colunas, paginação no servidor e controle de permissões!

Na **Aula 08**, vamos dar um passo além e construir o **Módulo de Usuários e a Matriz Visual de Permissões Personalizadas**: você aprenderá como usar `LEFT JOIN` com `COUNT` e `GROUP BY` na listagem de usuários, como agrupar permissões por módulo no Jinja2 (`|groupby('modulo')`) e como capturar múltiplos *checkboxes* marcados no HTML usando `request.form.getlist()` para gravar permissões granulares em tempo real!

---
<!-- nav -->
| Anterior | Índice | Próxima |
| :--- | :---: | ---: |
| [← Aula 06 — Motor de Paginação e Busca](./aula_06_motor_paginacao_pesquisa_dinamica.md) | [📚 Índice do Curso](./README.md) | [Aula 08 — Usuários e Matriz de Permissões →](./aula_08_modulo_usuarios_matriz_permissoes.md) |