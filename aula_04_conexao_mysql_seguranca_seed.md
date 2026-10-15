# Aula 04 — Conectando Flask ao MySQL com Segurança e Carga Inicial (`seed_db.py`)

Na **Aula 03**, projetamos a arquitetura relacional do **SalaFácil** e escrevemos o arquivo `sql/schema.sql` com nossas 5 tabelas (`usuarios`, `permissoes`, `usuario_permissoes`, `salas` e `reservas`).

Agora surge a grande pergunta prática:
> *"Como fazemos o nosso código Python conversar com o servidor MySQL de forma rápida, sem deixar conexões abertas travando a memória e sem correr o risco de sofrer ataques de invasão?"*

Nesta **Aula 04**, você vai aprender:
1. Como funciona a dupla **Conexão (`Connection`)** e **Cursor (`Cursor`)** no Python.
2. O ciclo de vida de uma requisição no Flask: o que são os objetos **`g`**, **`current_app`** e o gancho **`teardown_appcontext`**.
3. O que é um ataque de **SQL Injection** e como evitá-lo 100% usando consultas parametrizadas (`%s`).
4. Como nunca salvar senhas abertas no banco de dados usando **Hash Criptográfico (`generate_password_hash`)**.
5. Como construir e executar o script **`seed_db.py`** para criar o banco e popular automaticamente permissões, usuários, salas e reservas de teste.

---

## 1. Como o Python Conversa com o MySQL? (Conexão vs. Cursor)

Quando usamos a biblioteca `mysql-connector-python` (que instalamos na Aula 01), a comunicação com o banco de dados acontece em duas etapas que podemos comparar a uma **ligação telefônica**:

1. **A Conexão (`conn = mysql.connector.connect(...)`):**  
   É como discar o número, digitar a senha do ramal e estabelecer a linha telefônica aberta entre o Python e o servidor MySQL. Abrir uma linha telefônica leva alguns milissegundos de trabalho pesado de rede.
2. **O Cursor (`cursor = conn.cursor()`):**  
   Depois que a linha telefônica (`conn`) está aberta, o **Cursor** é o "mensageiro" que fala na linha: ele leva o comando SQL (`cursor.execute("SELECT ...")`), busca a resposta lá no MySQL (`cursor.fetchall()`) e traz os dados de volta para o Python. Terminou a pergunta? Fechamos o cursor (`cursor.close()`).

### O Segredo do `cursor(dictionary=True)`
Por padrão, quando você faz um `SELECT id, nome, email FROM usuarios` no Python, o cursor devolve cada linha como uma **tupla numérica**:
* Sem `dictionary=True`: `(1, 'Ana Administradora', 'admin@salafacil.com')` $\rightarrow$ Para pegar o e-mail, você teria que lembrar de cabeça que ele está na posição `linha[2]`. Se alguém mudar a ordem das colunas no `SELECT`, o seu sistema inteiro quebra!
* **Com `dictionary=True`:** `{'id': 1, 'nome': 'Ana Administradora', 'email': 'admin@salafacil.com'}` $\rightarrow$ Cada linha vem como um **dicionário Python**! Podemos acessar `linha["email"]` no Python ou `{{ usuario.email }}` no HTML com total clareza.

---

## 2. O Ciclo de Vida da Requisição no Flask (`g` e `teardown_appcontext`)

Em um sistema iniciante mal projetado, o programador costuma abrir uma nova conexão com o MySQL no começo de cada função e fechar no final.
* **Qual é o perigo disso?**  
  Em uma única página do nosso sistema, podemos precisar fazer 3 consultas seguidas ao banco: (1) verificar quem é o usuário logado, (2) contar quantas salas existem e (3) buscar as 8 salas da página atual. Abrir e fechar 3 conexões de rede para mostrar uma única página deixaria o sistema lento. Pior: se acontecer um erro no meio da função antes da linha `conn.close()`, a conexão fica "pendurada" aberta no MySQL até travar o servidor!

### Como o Flask resolve isso de forma elegante?
O Flask possui dois objetos especiais que você verá no código de hoje:

1. **`current_app` (A Aplicação Atual):** Como usamos o padrão *Application Factory* (`create_app()`), a variável `app` não fica solta globalmente. Sempre que qualquer arquivo do projeto precisar ler uma configuração (como `DB_HOST` ou `DB_PASSWORD`), importamos o `current_app`, que aponta automaticamente para o servidor Flask em execução.
2. **`g` (A "Mochila Temporária" da Requisição):**  
   O objeto `g` (de *global* ao contexto da requisição) funciona como uma **mochila descartável** que nasce no instante em que o navegador faz um pedido HTTP e é jogada fora assim que o Flask entrega a resposta HTML:
   ```text
   [1. Pedido HTTP chega] -> Flask cria a mochila vazia "g"
   [2. Primeira consulta SQL] -> get_db() abre 1 conexão MySQL e guarda dentro de "g.db_conn"
   [3. Segunda consulta SQL] -> get_db() vê que "g.db_conn" já existe e REAPROVEITA a mesma conexão!
   [4. Resposta entregue] -> O gancho teardown_appcontext chama close_db() e fecha a conexão!
   ```
   Mesmo que ocorra um erro grave no meio do código Python, o `teardown_appcontext` do Flask garante que a função `close_db()` será chamada ao final, nunca deixando conexões vazarem!

### E entre uma requisição e outra? O Pool de Conexões

A mochila `g` resolve o problema **dentro de uma requisição**, mas há um custo escondido: no começo de **cada** clique, o Python ainda precisa "discar o número" do MySQL, autenticar e abrir uma conexão nova de rede. Com dezenas de usuários clicando ao mesmo tempo, isso vira um gargalo.

> **Analogia do bicicletário:** imagine uma empresa que, para cada funcionário que precisa sair, **compra uma bicicleta nova** e a **joga fora** na volta. Caro e lento! A solução é um **bicicletário com 10 bicicletas**: o funcionário pega uma que está livre, usa e a devolve. Esse bicicletário é o **pool de conexões** (*connection pool*): o `mysql-connector-python` abre algumas conexões **uma única vez**, as mantém prontas e as empresta a cada requisição. Quando `close_db()` "fecha" a conexão, na verdade ela **volta para o bicicletário**, aberta e pronta para o próximo.

Ativar isso exige apenas dois parâmetros extras na conexão (`pool_name` e `pool_size`), que você verá no código abaixo.

---

## 3. O Perigo do SQL Injection (e Por Que Nunca Usar `f-strings` no SQL!)

Antes de criarmos o nosso `app/database.py`, precisamos falar sobre a regra nº 1 de segurança em bancos de dados: **SQL Injection (Injeção de SQL)**.

Imagine que você escreva uma busca de login concatenando o texto digitado pelo usuário diretamente na string SQL usando `f-string`:

```python
# ❌ NUNCA FAÇA ISSO! (Código vulnerável a SQL Injection)
sql = f"SELECT * FROM usuarios WHERE email = '{email_digitado}'"
```

Se um invasor digitar no campo de e-mail da tela de login exatamente isto:
`qualquer@coisa.com' OR '1'='1`

A consulta montada pelo Python vai virar:
```sql
SELECT * FROM usuarios WHERE email = 'qualquer@coisa.com' OR '1'='1'
```
Como `'1'='1'` é sempre verdadeiro, o banco de dados devolverá o primeiro usuário da tabela (geralmente o **Administrador Geral**!) e o invasor entrará no sistema sem saber a senha!

### A Blindagem Definitiva: Consultas Parametrizadas (`%s`)
Para proteger 100% do nosso sistema, **nunca** misturamos variáveis dentro do texto SQL. No lugar do valor, colocamos o marcador **`%s`** e passamos os valores separadamente em uma **tupla** no segundo argumento do `cursor.execute(sql, params)`:

```python
# ✅ FORMA SEGURA PROFISSIONAL (Blindada contra SQL Injection)
sql = "SELECT * FROM usuarios WHERE email = %s"
params = (email_digitado,)
cursor.execute(sql, params)
```

Quando fazemos isso, o driver do MySQL trata o conteúdo de `email_digitado` estritamente como um **valor de texto literal**, neutralizando qualquer aspa ou comando malicioso!

> ⚠️ **Atenção à "Pegadinha da Tupla de 1 Elemento" no Python:**  
> Em Python, para criar uma tupla com **apenas 1 item**, é obrigatório colocar uma **vírgula no final** antes de fechar os parênteses: **`(email_digitado,)`**.  
> Se você escrever `(email_digitado)` sem a vírgula, o Python achará que são apenas parênteses matemáticos em volta de uma string comum, e o conector do MySQL dará erro! Já quando há 2 ou mais itens, basta separar normalmente: `(email, senha)`.

---

## 4. Criando o Gerenciador de Banco de Dados (`app/database.py`)

Primeiro, uma pequena atualização no `app/config.py` (Aula 02): adicione **uma linha** logo abaixo de `DB_NAME`, para definir o tamanho do "bicicletário":

```python
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 10))` | Lê do `.env` quantas conexões o pool mantém abertas (padrão: `10`). O `int(...)` converte o texto do `.env` em número. | Permite ajustar o tamanho do pool sem mexer no código. | O `get_db()` abaixo falha com `KeyError: 'DB_POOL_SIZE'`, pois a configuração não existe. |

Agora vamos criar o arquivo **`app/database.py`** com 5 funções utilitárias que deixarão todas as nossas próximas aulas incrivelmente simples:
* `get_db()`: Pega uma conexão do pool (ou reaproveita a que já está na mochila `g`).
* `query_all(sql, params)`: Para fazer `SELECT` que retorna **várias linhas** (lista de dicionários).
* `query_one(sql, params)`: Para fazer `SELECT` que retorna **apenas 1 linha** (um único dicionário ou `None`).
* `execute_write(sql, params)`: Para fazer **um** `INSERT`, `UPDATE` ou `DELETE` com proteção de transação (`commit` em caso de sucesso ou `rollback` em caso de falha).
* `transacao()`: Para fazer **vários** comandos de escrita em sequência de forma **atômica** (ou todos valem, ou nenhum vale). Será essencial nas Aulas 08 e 09.

Abra o arquivo **`app/database.py`** e digite o código abaixo:

```python
# app/database.py
from contextlib import contextmanager
import mysql.connector
from mysql.connector import Error
from flask import current_app, g


def get_db():
    """
    Retorna a conexão MySQL ativa para a requisição atual.
    A conexão é emprestada de um "pool" (estoque de conexões prontas)
    e devolvida a ele automaticamente no final da requisição.
    """
    if "db_conn" not in g or not g.db_conn.is_connected():
        g.db_conn = mysql.connector.connect(
            pool_name="salafacil_pool",
            pool_size=current_app.config["DB_POOL_SIZE"],
            host=current_app.config["DB_HOST"],
            port=current_app.config["DB_PORT"],
            user=current_app.config["DB_USER"],
            password=current_app.config["DB_PASSWORD"],
            database=current_app.config["DB_NAME"],
            charset="utf8mb4",
            autocommit=False,
            connection_timeout=10,
        )
    return g.db_conn


def query_all(sql, params=None):
    """Executa um SELECT e retorna uma lista de dicionários."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()


def query_one(sql, params=None):
    """Executa um SELECT e retorna apenas um dicionário (ou None)."""
    conn = get_db()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchone()
    finally:
        cursor.close()


def execute_write(sql, params=None, commit=True):
    """
    Executa INSERT, UPDATE ou DELETE.
    Retorna o lastrowid (útil em INSERTs) ou o número de linhas afetadas.
    """
    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute(sql, params or ())
        if commit:
            conn.commit()
        return cursor.lastrowid or cursor.rowcount
    except Error:
        conn.rollback()
        raise
    finally:
        cursor.close()


@contextmanager
def transacao():
    """
    Agrupa VÁRIOS comandos em uma única transação: ou todos valem, ou nenhum vale.
    Uso:
        with transacao() as cursor:
            cursor.execute("INSERT ...", (...))
            cursor.execute("UPDATE ...", (...))
    Se acontecer qualquer erro dentro do bloco 'with', tudo é desfeito (rollback).
    """
    conn = get_db()
    conn.commit()  # fecha leituras anteriores da requisição, para enxergar dados recém-gravados por outros
    cursor = conn.cursor(dictionary=True)
    try:
        yield cursor
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()


def close_db(exception=None):
    """Fecha a conexão MySQL ao final do ciclo de vida da requisição HTTP."""
    db_conn = g.pop("db_conn", None)
    if db_conn is not None and db_conn.is_connected():
        db_conn.close()


def init_db_app(app):
    """Registra o fechamento automático da conexão no Flask."""
    app.teardown_appcontext(close_db)
```

### Linha por linha do `app/database.py`

#### Bloco 1 — os `import`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `from contextlib import contextmanager` | Traz a ferramenta que permite criar blocos `with ...:` personalizados. | A função `transacao()` usa isso para virar um bloco `with`. | `NameError: name 'contextmanager' is not defined` ao abrir qualquer página que importe o arquivo. |
| `import mysql.connector` | O driver oficial do MySQL (instalado na Aula 01). | É quem fala a "língua" do MySQL. | Nenhuma conexão com o banco é possível. |
| `from mysql.connector import Error` | A classe-mãe de todos os erros do MySQL. | Permite capturar erros do banco no `except` de `execute_write`. | O `except Error` falha com `NameError` justamente na hora do erro. |
| `from flask import current_app, g` | A aplicação atual e a "mochila" da requisição (explicados nesta aula). | Para ler as configurações e guardar a conexão. | Erro de `NameError` ao pedir uma conexão. |

#### Bloco 2 — `get_db()` (pedir a conexão)

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `if "db_conn" not in g or not g.db_conn.is_connected():` | Pergunta: "a mochila ainda não tem conexão **ou** a que tem caiu?". | Evita pegar uma segunda conexão do pool na mesma requisição. | Cada consulta abriria uma conexão nova e o pool esgotaria rápido. |
| `pool_name="salafacil_pool"` | Dá um nome ao bicicletário. | Na primeira chamada o conector **cria** o pool com esse nome; nas seguintes, apenas **reaproveita** o mesmo. | Sem `pool_name` e sem `pool_size`, volta a abrir uma conexão nova a cada requisição (mais lento). |
| `pool_size=current_app.config["DB_POOL_SIZE"]` | Quantas conexões o bicicletário guarda (10 por padrão). | Limita o uso de memória do MySQL e atende vários usuários simultâneos. | Sem esse parâmetro, o conector usa o tamanho padrão dele (5), que pode ser pouco. |
| `host=`, `port=`, `user=`, `password=`, `database=` | Endereço, porta, usuário, senha e banco, lidos de `app.config` (que veio do `.env`). | Nada de senha escrita no código! | Sem eles o conector tenta valores padrão e, em geral, recebe `Access denied`. |
| `charset="utf8mb4"` | Combina com o `utf8mb4` do banco (Aula 03). | Garante que acentos e emojis viajem sem virar símbolos estranhos. | Textos como `Auditório` podem voltar corrompidos. |
| `autocommit=False` | Desliga a confirmação automática: cada escrita fica em "rascunho" até o `commit()`. | É o que permite o `rollback` se algo der errado. | Cada `INSERT`/`UPDATE` seria gravado na hora, sem possibilidade de desfazer. |
| `connection_timeout=10` | Espera no máximo 10 segundos pelo MySQL. | Se o banco estiver travado, a página falha rápido em vez de ficar "carregando" para sempre. | Sem limite de espera, uma requisição pode ficar pendurada por minutos. |
| `return g.db_conn` | Entrega a conexão a quem pediu. | É o objetivo da função. | `get_db()` devolveria `None` e as consultas falhariam. |

#### Bloco 3 — `query_all()` e `query_one()` (ler dados)

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `conn = get_db()` | Pega a conexão da requisição. | Sem conexão não há como perguntar nada ao banco. | `NameError` ou consulta impossível. |
| `cursor = conn.cursor(dictionary=True)` | Cria o "mensageiro" que devolve cada linha como **dicionário** (`linha["email"]`). | Deixa o código legível e à prova de mudanças na ordem das colunas. | As linhas voltam como tuplas (`linha[2]`) e todos os templates `{{ u.nome }}` deixam de funcionar. |
| `cursor.execute(sql, params or ())` | Envia o SQL com os valores **separados** (blindagem contra SQL Injection). `params or ()` usa uma tupla vazia se nada for informado. | É aqui que o `%s` é substituído de forma segura. | Sem o segundo argumento, `%s` seria enviado literalmente e a consulta falharia. |
| `return cursor.fetchall()` / `return cursor.fetchone()` | `fetchall` devolve **todas** as linhas; `fetchone` devolve **uma** (ou `None`). | Escolhemos entre "lista" e "registro único". | Sem o `return`, a função devolveria `None` e a tela ficaria sem dados. |
| `finally: cursor.close()` | Fecha o cursor **sempre**, até quando há erro. | Cursores abertos acumulam e consomem memória. | Cursores "vazam", e com o tempo o servidor fica lento. |

#### Bloco 4 — `execute_write()` (gravar **um** comando)

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `cursor = conn.cursor()` | Cursor comum (sem `dictionary`), pois escritas não devolvem linhas. | Mais leve para `INSERT`/`UPDATE`/`DELETE`. | Funcionaria também; é só uma escolha de economia. |
| `if commit: conn.commit()` | Confirma a gravação definitivamente no disco do MySQL. | Com `autocommit=False`, sem isso nada é salvo. | A tela diz "Salvo com sucesso!", mas ao recarregar os dados **não estão lá**. |
| `return cursor.lastrowid or cursor.rowcount` | Devolve o `id` recém-criado (em `INSERT`) ou, se não houver, quantas linhas foram afetadas (em `UPDATE`/`DELETE`). | Na Aula 08 usamos o `id`; na Aula 09, a contagem de linhas. | O código chamador não saberia o resultado da operação. |
| `except Error: conn.rollback(); raise` | Se o MySQL reclamar, **desfaz** o rascunho e repassa o erro adiante (`raise`). | Impede que uma gravação pela metade fique "esquecida" na conexão. | A conexão fica com um rascunho sujo e o erro some sem aviso. |

#### Bloco 5 — `transacao()` (gravar **vários** comandos de uma vez)

> **Analogia da transferência bancária:** para transferir R$ 100 da conta A para a conta B, o banco faz **dois** passos: tirar de A e colocar em B. Se o sistema cair entre os dois, o dinheiro sumiria! Por isso o banco trata os dois passos como **um bloco indivisível**: ou os dois acontecem, ou nenhum. Isso é uma **transação**. Quando criarmos um usuário **e** suas permissões (Aula 08) ou reservarmos uma sala **conferindo conflitos** (Aula 09), precisamos exatamente dessa garantia.

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `@contextmanager` | Transforma a função em algo que pode ser usado com `with transacao() as cursor:`. | Dá a sintaxe limpa de "abre, usa, fecha automaticamente". | Usar `with transacao()` gera `AttributeError`. |
| `conn.commit()` (logo no início) | Encerra qualquer transação de **leitura** aberta antes na requisição. | O MySQL tira uma "fotografia" dos dados na primeira leitura. Sem fechar essa foto, não enxergaríamos o que outro usuário gravou depois dela, o que é vital para evitar reservas duplicadas (Aula 09). | A verificação de conflito pode olhar uma "foto velha" e deixar passar uma reserva duplicada. |
| `cursor = conn.cursor(dictionary=True)` | Cria o cursor que será entregue ao bloco `with`. | Os comandos dentro do bloco usam esse mesmo cursor. | O bloco `with` não teria cursor para trabalhar. |
| `yield cursor` | "Pausa" a função e entrega o cursor ao bloco `with`; quando o bloco termina, a função **continua** daqui. | É o coração do `contextmanager`: o que está antes do `yield` é a "abertura", o que está depois é o "fechamento". | A função não entregaria o cursor e o `with` falharia. |
| `conn.commit()` (depois do `yield`) | Se o bloco terminou **sem erro**, confirma tudo de uma vez. | É o "carimbo final" da transferência bancária. | Nada do que foi feito dentro do bloco seria salvo. |
| `except Exception: conn.rollback(); raise` | Se **qualquer** erro acontecer dentro do bloco, desfaz tudo e repassa o erro. | Garante o "ou todos, ou nenhum". | Um erro no 3º comando deixaria os 2 primeiros gravados: dados pela metade. |
| `finally: cursor.close()` | Fecha o cursor de qualquer jeito. | Mesma razão dos blocos anteriores. | Cursor aberto vaza memória. |

#### Bloco 6 — `close_db()` e `init_db_app()`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `db_conn = g.pop("db_conn", None)` | Tira a conexão da mochila (ou `None` se não havia). | Evita erro caso a requisição nunca tenha usado o banco (ex.: arquivos estáticos). | `KeyError` em requisições que não consultaram o MySQL. |
| `if db_conn is not None and db_conn.is_connected(): db_conn.close()` | "Fecha" a conexão, que na prática **volta ao pool** (bicicleta devolvida). | Sem devolver, o pool esvazia e novos usuários recebem `pool exhausted`. | O sistema trava depois das primeiras 10 requisições. |
| `app.teardown_appcontext(close_db)` | Registra `close_db` para rodar ao final de **toda** requisição, mesmo com erro. | É a garantia de que nenhuma conexão é esquecida. | As conexões nunca voltam ao pool. |

### Detalhes extras que valem ouro:
* **Por que usamos `try ... finally: cursor.close()`?**  
  O bloco `finally` no Python tem uma garantia de ferro: ele **sempre** é executado, mesmo depois de um `return` ou se acontecer um erro na query SQL. Isso garante que cada cursor aberto seja fechado imediatamente após buscar os dados.
* **O que fazem `conn.commit()` e `conn.rollback()` em `execute_write`?**  
  Como configuramos `autocommit=False` na conexão, qualquer `INSERT`, `UPDATE` ou `DELETE` fica em um "rascunho temporário" (transação). Se tudo der certo, `conn.commit()` grava os dados definitivamente no disco do MySQL. Se ocorrer qualquer erro (`except Error:`), `conn.rollback()` desfaz a alteração pela metade, deixando o banco íntegro!
* **O que é `cursor.lastrowid`?**  
  Quando fazemos um `INSERT` para criar um usuário novo, o MySQL gera automaticamente o número do `id` dele (`AUTO_INCREMENT`). O `cursor.lastrowid` devolve exatamente qual foi o `id` recém-gerado! Usaremos isso na Aula 08 para vincular as permissões ao usuário que acabou de ser cadastrado.

---

## 5. Como Proteger Senhas no Banco de Dados? (`generate_password_hash`)

Antes de criarmos os nossos 3 usuários de teste no banco de dados, responda rápido:
> *"Se a senha de teste dos nossos usuários é `123456`, devemos gravar o texto `'123456'` na coluna `senha` do MySQL?"*

**Jamais!** Em qualquer sistema sério, nem mesmo o administrador do banco de dados pode conseguir ler a senha real dos usuários. Por isso, na nossa tabela `usuarios` (criada na Aula 03), a coluna se chama **`senha_hash`**, e não `senha`.

### O que é um Hash de Senha?
Um **Hash** (gerado pela função `generate_password_hash("123456")` do pacote `werkzeug.security` que vem com o Flask) é uma transformação matemática de **mão única**:
1. Você entrega `"123456"` para o `generate_password_hash("123456")`.
2. Ele adiciona um tempero aleatório (*Salt*) e aplica milhares de rodadas criptográficas (`scrypt` ou `pbkdf2`), devolvendo um código longo parecido com este:
   `scrypt:32768:8:1$k8Tz9mQpL$7f8a9d2e1b4c6f...`
3. É esse código longo que salvamos no MySQL! Como o algoritmo é de mão única, é matematicamente impossível "descriptografar" esse hash de volta para `"123456"`.
4. **E como conferimos a senha no Login (Aula 05)?** Quando o usuário digita a senha na tela de login, usamos a função irmã `check_password_hash(hash_do_banco, senha_digitada)`, que refaz o cálculo e responde `True` ou `False`!

---

## 6. Criando o Script de Carga Inicial (`seed_db.py`)

Em desenvolvimento de software, chamamos de **Seed (Semente)** um script automatizado que prepara o banco de dados do zero e planta registros iniciais de teste para que o programador não precise cadastrar salas e permissões manualmente toda vez que instalar o sistema em uma máquina nova.

Nosso arquivo **`seed_db.py`** (que fica na raiz `sistema_reservas_salas/seed_db.py`) fará **7 tarefas automáticas** em sequência:
1. Conectar ao seu servidor MySQL local lendo as credenciais do arquivo `.env`.
2. Ler e executar todos os comandos do arquivo `sql/schema.sql` (criando o banco `gestao_reservas_salas` e as 5 tabelas).
3. Inserir o catálogo oficial das **13 permissões personalizadas**.
4. Criar **3 contas de usuários** com perfis distintos (todos com a senha `123456` criptografada em hash):
   * **Ana Administradora (`admin@salafacil.com`):** Recebe todas as 13 permissões.
   * **Carlos Gestor (`gestor@salafacil.com`):** Recebe 9 permissões (Salas, Aprovação de Reservas e Relatórios).
   * **Beatriz Professora (`beatriz@salafacil.com`):** Recebe 3 permissões básicas de solicitante (`salas.visualizar`, `reservas.visualizar`, `reservas.criar`).
5. Vincular as permissões de cada usuário na tabela `usuario_permissoes`.
6. Cadastrar **10 salas e laboratórios realistas** (com códigos `LAB-101`, `AUD-201`, etc.) para podermos testar a paginação e a busca dinâmica.
7. Cadastrar **6 reservas de exemplo** (distribuídas entre ontem, hoje e os próximos dias, com status `aprovada`, `pendente` e `cancelada`).

Abra (ou crie) o arquivo **`seed_db.py`** na raiz do projeto e insira o código abaixo:

```python
# seed_db.py
import os
from datetime import date, timedelta
from pathlib import Path
import mysql.connector
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash

load_dotenv()

# Pasta onde este arquivo está (não importa de onde o aluno rode o comando)
RAIZ_DO_PROJETO = Path(__file__).resolve().parent
# Nome do banco que está escrito dentro do sql/schema.sql
NOME_PADRAO_NO_SCHEMA = "gestao_reservas_salas"


def executar_seed():
    # 0. Confere o nome do banco definido no .env (só letras, números e sublinhado)
    nome_do_banco = os.getenv("DB_NAME", NOME_PADRAO_NO_SCHEMA)
    if not nome_do_banco.replace("_", "").isalnum():
        raise SystemExit("DB_NAME inválido: use apenas letras, números e sublinhado (_).")

    # 1. Conecta ao servidor MySQL (sem especificar database inicialmente para criá-lo)
    conn = mysql.connector.connect(
        host=os.getenv("DB_HOST", "127.0.0.1"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER", "root"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    cursor = conn.cursor()

    # 2. Lê o sql/schema.sql, ajusta o nome do banco para o do .env e executa cada comando
    script_sql = (RAIZ_DO_PROJETO / "sql" / "schema.sql").read_text(encoding="utf-8")
    script_sql = script_sql.replace(NOME_PADRAO_NO_SCHEMA, nome_do_banco)
    for comando in script_sql.split(";"):
        if comando.strip():
            cursor.execute(comando)
    conn.commit()

    # 3. Insere o catálogo de 13 Permissões Personalizadas
    permissoes = [
        ("salas.visualizar", "Visualizar Salas", "Salas", "Permite listar e pesquisar salas"),
        ("salas.criar", "Cadastrar Salas", "Salas", "Permite criar novas salas no sistema"),
        ("salas.editar", "Editar Salas", "Salas", "Permite alterar dados e status de salas"),
        ("salas.excluir", "Excluir Salas", "Salas", "Permite remover salas sem vínculo"),
        ("reservas.visualizar", "Visualizar Reservas", "Reservas", "Permite consultar a agenda de reservas"),
        ("reservas.criar", "Solicitar Reserva", "Reservas", "Permite agendar salas"),
        ("reservas.aprovar", "Aprovar/Rejeitar Reservas", "Reservas", "Permite aprovar ou recusar pedidos"),
        ("reservas.cancelar_qualquer", "Cancelar Qualquer Reserva", "Reservas", "Permite cancelar reservas de terceiros"),
        ("usuarios.visualizar", "Visualizar Usuários", "Usuários", "Permite consultar a lista de usuários"),
        ("usuarios.gerenciar", "Cadastrar Usuários", "Usuários", "Permite cadastrar novos usuários"),
        ("usuarios.permissoes", "Configurar Permissões", "Usuários", "Permite alterar permissões granulares"),
        ("relatorios.visualizar", "Acessar Relatórios", "Relatórios", "Permite acessar painéis e relatórios"),
        ("relatorios.exportar", "Exportar Relatórios", "Relatórios", "Permite exportar CSV e imprimir relatórios"),
    ]

    cursor.executemany(
        """
        INSERT IGNORE INTO permissoes (codigo, nome, modulo, descricao)
        VALUES (%s, %s, %s, %s)
        """,
        permissoes,
    )

    # 4. Cria 3 usuários com diferentes conjuntos de permissões personalizadas
    #    (cada um recebe o seu próprio hash, mesmo sendo a mesma senha de demonstração)
    usuarios = [
        ("Ana Administradora", "admin@salafacil.com", generate_password_hash("123456"), "TI & Governança", "Administrador Geral"),
        ("Carlos Gestor", "gestor@salafacil.com", generate_password_hash("123456"), "Infraestrutura", "Gestor de Espaços"),
        ("Beatriz Professora", "beatriz@salafacil.com", generate_password_hash("123456"), "Docência", "Solicitante"),
    ]
    cursor.executemany(
        """
        INSERT IGNORE INTO usuarios (nome, email, senha_hash, setor, cargo_etiqueta)
        VALUES (%s, %s, %s, %s, %s)
        """,
        usuarios,
    )
    conn.commit()

    # 5. Atribui permissões personalizadas
    # Ana (Admin) recebe todas as 13 permissões
    cursor.execute(
        """
        INSERT IGNORE INTO usuario_permissoes (usuario_id, permissao_id)
        SELECT u.id, p.id FROM usuarios u CROSS JOIN permissoes p
        WHERE u.email = 'admin@salafacil.com'
        """
    )

    # Carlos (Gestor) recebe permissões de salas, aprovação de reservas e relatórios
    codigos_gestor = (
        "salas.visualizar", "salas.criar", "salas.editar",
        "reservas.visualizar", "reservas.criar", "reservas.aprovar", "reservas.cancelar_qualquer",
        "relatorios.visualizar", "relatorios.exportar",
    )
    formato_in = ",".join(["%s"] * len(codigos_gestor))
    cursor.execute(
        f"""
        INSERT IGNORE INTO usuario_permissoes (usuario_id, permissao_id)
        SELECT u.id, p.id FROM usuarios u
        JOIN permissoes p ON p.codigo IN ({formato_in})
        WHERE u.email = 'gestor@salafacil.com'
        """,
        codigos_gestor,
    )

    # Beatriz (Solicitante) recebe permissões de visualização e criação de reserva
    codigos_solicitante = ("salas.visualizar", "reservas.visualizar", "reservas.criar")
    formato_sol = ",".join(["%s"] * len(codigos_solicitante))
    cursor.execute(
        f"""
        INSERT IGNORE INTO usuario_permissoes (usuario_id, permissao_id)
        SELECT u.id, p.id FROM usuarios u
        JOIN permissoes p ON p.codigo IN ({formato_sol})
        WHERE u.email = 'beatriz@salafacil.com'
        """,
        codigos_solicitante,
    )

    # 6. Insere Salas de Exemplo (para testar busca dinâmica e paginação)
    salas = [
        ("LAB-101", "Laboratório de Informática I", "Bloco A - Térreo", 40, "40 PCs, Projetor Laser, Ar-condicionado"),
        ("LAB-102", "Laboratório de Redes e Servidores", "Bloco A - 1º Andar", 25, "Bancada Cisco, Rack, Projetor, Ar-condicionado"),
        ("AUD-201", "Auditório Principal Tiradentes", "Bloco Central", 180, "Sistema de Som, 2 Telões, Palco, Videoconferência"),
        ("REU-301", "Sala de Reuniões Executiva", "Bloco B - 3º Andar", 14, "TV 75 pol, Câmera 360, Quadro de Vidro, Café"),
        ("REU-302", "Sala de Brainstorming Criativo", "Bloco B - 3º Andar", 10, "Paredes Lousa, Puffs, TV 55 pol, Ar-condicionado"),
        ("SAL-401", "Sala de Aula Invertida 01", "Bloco C - 1º Andar", 50, "Mesas Redondas, 2 Projetores, Microfone Sem Fio"),
        ("SAL-402", "Sala de Aula Multimídia 02", "Bloco C - 1º Andar", 45, "Lousa Digital Interativa, Som Ambiente"),
        ("EST-501", "Estúdio de Gravação e Podcast", "Bloco D - Subsolo", 6, "Isolamento Acústico, 4 Microfones XLR, Iluminação LED"),
        ("LAB-103", "Laboratório de Robótica e IoT", "Bloco A - 2º Andar", 30, "Impressoras 3D, Kits Arduino, Bancadas de Solda"),
        ("MIN-202", "Mini Auditório Anexo", "Bloco Central", 75, "Projetor Full HD, Púlpito Digital, Ar-condicionado"),
    ]
    cursor.executemany(
        """
        INSERT IGNORE INTO salas (codigo, nome, bloco, capacidade, recursos)
        VALUES (%s, %s, %s, %s, %s)
        """,
        salas,
    )
    conn.commit()

    # 7. Insere Reservas de Exemplo (caso a tabela reservas ainda esteja vazia)
    cursor.execute("SELECT COUNT(*) FROM reservas")
    if cursor.fetchone()[0] == 0:
        hoje = date.today()
        # Cada tupla: (título, finalidade, data, início, fim, participantes, status, observações,
        #              e-mail do solicitante, e-mail do aprovador (ou None), código da sala)
        reservas_exemplo = [
            ("Aula Prática de Python Web", "Graduação ADS", (hoje - timedelta(days=2)).isoformat(), "08:00:00", "11:00:00", 35, "aprovada", "Laboratório configurado com Flask", "beatriz@salafacil.com", "gestor@salafacil.com", "LAB-101"),
            ("Simpósio de Tecnologia e Inovação", "Evento Institucional", (hoje - timedelta(days=1)).isoformat(), "19:00:00", "22:00:00", 150, "aprovada", "Necessário microfone de lapela", "gestor@salafacil.com", "gestor@salafacil.com", "AUD-201"),
            ("Reunião do Comitê de Governança", "Reunião Executiva", hoje.isoformat(), "09:00:00", "10:30:00", 10, "aprovada", "Link de videoconferência ativo", "admin@salafacil.com", "admin@salafacil.com", "REU-301"),
            ("Monitoria de Banco de Dados MySQL", "Reforço Acadêmico", (hoje + timedelta(days=1)).isoformat(), "14:00:00", "16:00:00", 28, "pendente", "Solicitação aguardando aprovação", "beatriz@salafacil.com", None, "LAB-101"),
            ("Gravação da Videoaula de Tailwind CSS", "Produção de Material", (hoje + timedelta(days=2)).isoformat(), "10:00:00", "12:00:00", 3, "aprovada", "Iluminação preparada", "beatriz@salafacil.com", "gestor@salafacil.com", "EST-501"),
            ("Oficina de Configuração de Redes", "Workshop Técnico", (hoje + timedelta(days=3)).isoformat(), "13:30:00", "17:30:00", 22, "cancelada", "Reagendado para a próxima semana", "beatriz@salafacil.com", "gestor@salafacil.com", "LAB-102"),
        ]
        # O INSERT ... SELECT descobre sozinho os ids da sala e dos usuários a partir do código e do e-mail
        cursor.executemany(
            """
            INSERT INTO reservas (
                sala_id, usuario_id, aprovador_id, titulo, finalidade,
                data_reserva, hora_inicio, hora_fim, participantes_estimados,
                status, observacoes
            )
            SELECT s.id, solicitante.id, aprovador.id, %s, %s, %s, %s, %s, %s, %s, %s
            FROM salas s
            INNER JOIN usuarios solicitante ON solicitante.email = %s
            LEFT JOIN usuarios aprovador ON aprovador.email = %s
            WHERE s.codigo = %s
            """,
            reservas_exemplo,
        )
        conn.commit()

    cursor.close()
    conn.close()
    print("Banco de dados criado e populado com sucesso!")
    print("Logins de teste (Senha para todos: 123456):")
    print(" - admin@salafacil.com (Todas as 13 permissões)")
    print(" - gestor@salafacil.com (Salas, Aprovação de Reservas e Relatórios)")
    print(" - beatriz@salafacil.com (Visualização e Solicitação de Reservas)")


if __name__ == "__main__":
    executar_seed()
```

---

## 7. Entendendo os Truques Inteligentes do `seed_db.py`

Vale a pena observar sete técnicas muito úteis empregadas no código acima (as quatro primeiras já existiam; as três últimas tornam o script mais robusto):

1. **Por que usamos `INSERT IGNORE INTO` em vez de apenas `INSERT INTO`?**  
   Como as colunas `permissoes.codigo`, `usuarios.email` e `salas.codigo` possuem a restrição `UNIQUE` (não permitem valores repetidos), se você rodar `python seed_db.py` duas ou três vezes seguidas, um `INSERT` comum travaria dizendo que o registro já existe. O `INSERT IGNORE` diz ao MySQL: *"Se este e-mail ou código de sala já estiver cadastrado, ignore silenciosamente e passe para o próximo!"*. Isso torna o nosso script **idempotente** (pode ser rodado quantas vezes você quiser sem duplicar dados nem dar erro).
2. **O que faz o `cursor.executemany(sql, lista_de_tuplas)`?**  
   Em vez de fazer um `for` no Python executando 13 comandos `INSERT` separados para cada permissão, o `executemany` envia a lista inteira de uma só vez para o MySQL, tornando a inserção em lote muito mais rápida.
3. **Como funciona o `CROSS JOIN` para a Administradora?**  
   Para dar todas as 13 permissões para a `admin@salafacil.com`, usamos `SELECT u.id, p.id FROM usuarios u CROSS JOIN permissoes p WHERE u.email = 'admin@salafacil.com'`. O `CROSS JOIN` cruza o ID da Ana com todas as linhas da tabela `permissoes` de uma só vez!
4. **Datas sempre atualizadas com `date.today() + timedelta(days=...)`:**  
   Repare que na etapa 7 não colocamos datas fixas como `'2026-01-10'`. Usamos `date.today()` do Python somando ou subtraindo dias (`timedelta`). Assim, não importa em que mês ou ano você execute o `seed_db.py`, o sistema sempre terá reservas fresquinhas na semana atual para exibir nos relatórios!
5. **Caminho do arquivo com `Path(__file__)` (em vez de `open("sql/schema.sql")`):**  
   Antes, o script procurava `sql/schema.sql` **a partir da pasta onde o terminal estava aberto**. Se o aluno rodasse o comando de outra pasta, dava `FileNotFoundError`.  
   > **Analogia:** dizer "a primeira porta à direita" só funciona se você souber onde a pessoa está parada. Dizer "a sala 12 do bloco B" funciona de qualquer lugar.

   | Linha | O que é | Por que está ali | O que acontece se tirar |
   | :--- | :--- | :--- | :--- |
   | `from pathlib import Path` | Ferramenta moderna do Python para trabalhar com caminhos de arquivos. | Permite montar caminhos que funcionam no Windows, Linux e macOS sem se preocupar com `\` ou `/`. | `NameError: name 'Path' is not defined`. |
   | `RAIZ_DO_PROJETO = Path(__file__).resolve().parent` | `__file__` é o caminho do próprio `seed_db.py`; `.resolve()` o torna completo; `.parent` sobe para a pasta que o contém. | Cria um "endereço fixo" da raiz do projeto, independente de onde o terminal está. | Voltamos ao erro `FileNotFoundError` quando o comando é rodado de fora da pasta. |
   | `(RAIZ_DO_PROJETO / "sql" / "schema.sql").read_text(encoding="utf-8")` | O operador `/` junta pedaços de caminho; `.read_text` lê o arquivo inteiro como texto. | Substitui `open(...)` e `read()` em uma única linha, já em UTF-8 (acentos corretos). | Sem `encoding="utf-8"`, o Windows pode ler os acentos de forma errada. |
6. **O nome do banco vem do `.env` (`DB_NAME`):**  
   Antes, o `schema.sql` sempre criava o banco `gestao_reservas_salas`, mas o Flask conectava no `DB_NAME` do `.env`. Se o aluno mudasse o nome no `.env`, o seed criava um banco e o sistema procurava **outro**.

   | Linha | O que é | Por que está ali | O que acontece se tirar |
   | :--- | :--- | :--- | :--- |
   | `NOME_PADRAO_NO_SCHEMA = "gestao_reservas_salas"` | Guarda o nome que está escrito dentro do `schema.sql`. | Precisamos saber *qual texto* trocar. | Sem a constante, o `replace` fica com um "número mágico" espalhado pelo código. |
   | `nome_do_banco = os.getenv("DB_NAME", NOME_PADRAO_NO_SCHEMA)` | Lê o nome do banco definido no `.env`. | Uma única fonte de verdade para o seed e para o Flask. | Mudanças no `.env` deixam de ter efeito no seed. |
   | `if not nome_do_banco.replace("_", "").isalnum(): raise SystemExit(...)` | Remove os sublinhados e confere se sobraram só letras e números; se não, encerra com uma mensagem. | O nome será colocado dentro de um comando SQL, então só aceitamos caracteres seguros. | Um `.env` com um nome estranho (aspas, ponto e vírgula) poderia gerar um SQL quebrado ou perigoso. |
   | `script_sql.replace(NOME_PADRAO_NO_SCHEMA, nome_do_banco)` | Troca o nome padrão pelo nome do `.env` em todo o texto do script. | Faz o `CREATE DATABASE` e o `USE` usarem o banco certo. | O seed e o Flask podem passar a usar bancos diferentes. |
7. **`INSERT ... SELECT` nas reservas (sem "números mágicos"):**  
   Antes, as reservas de exemplo diziam "sala `3`, usuário `2`". Esses números só estavam certos em um banco recém-criado; depois de apagar e recriar tabelas, os `id` mudam e as reservas apareciam na sala errada.  
   Agora cada reserva informa o **código da sala** (`"LAB-101"`) e o **e-mail** das pessoas, e o próprio MySQL descobre os `id` corretos:

   | Trecho do SQL | O que é | Por que está ali | O que acontece se tirar |
   | :--- | :--- | :--- | :--- |
   | `INSERT INTO reservas (...) SELECT s.id, solicitante.id, aprovador.id, %s, ...` | Em vez de `VALUES`, usa o resultado de um `SELECT` como fonte dos dados a inserir. | Mistura ids buscados no banco (`s.id`...) com valores vindos do Python (`%s`). | Voltaríamos a depender de números fixos. |
   | `INNER JOIN usuarios solicitante ON solicitante.email = %s` | Procura o usuário pelo e-mail e o apelida de `solicitante`. | Descobre o `usuario_id` do solicitante. | A reserva ficaria sem solicitante e o `INSERT` não grava nada. |
   | `LEFT JOIN usuarios aprovador ON aprovador.email = %s` | Procura o aprovador pelo e-mail; com `None` não encontra ninguém e devolve `NULL`. | Reservas `pendentes` ainda não têm aprovador; o `LEFT JOIN` preserva a linha mesmo assim (lembra da Aula 09?). | Com `INNER JOIN`, a reserva pendente **desapareceria** do seed. |
   | `WHERE s.codigo = %s` | Escolhe a sala pelo código. | Garante que só uma sala seja usada na inserção. | O `INSERT` criaria uma reserva para **cada** sala do banco. |

> ⚠️ **Limite honesto do script:** o `split(";")` corta o arquivo em cada ponto e vírgula. Funciona porque o nosso `schema.sql` não tem `;` dentro de textos ou comentários. Se você algum dia escrever um comentário como `-- cuidado; atenção`, o corte acontecerá no lugar errado.

---

## 8. Executando o `seed_db.py` e Plugando o Banco no Flask!

### Passo 8.1 — Rodar a carga inicial do banco
Antes de rodar, confira se o seu arquivo **`.env`** está com o usuário e senha corretos do seu MySQL local (`DB_USER` e `DB_PASSWORD`). Em seguida, no terminal com o `(venv)` ativo, execute:

```bash
python seed_db.py
```

Você verá a confirmação no terminal:

```text
Banco de dados criado e populado com sucesso!
Logins de teste (Senha para todos: 123456):
 - admin@salafacil.com (Todas as 13 permissões)
 - gestor@salafacil.com (Salas, Aprovação de Reservas e Relatórios)
 - beatriz@salafacil.com (Visualização e Solicitação de Reservas)
```

---

### Passo 8.2 — Conectando o `app/database.py` no `app/__init__.py`

Para fechar a Aula 04 com chave de ouro e provar que o nosso **Flask** já está lendo os dados reais do **MySQL**, vamos atualizar o arquivo **`app/__init__.py`** para registrar o `init_db_app(app)` e fazer os 4 cartões da página de boas-vindas exibirem a **contagem real de registros** direto do banco de dados!

Abra o arquivo **`app/__init__.py`** e atualize-o para ficar assim:

```python
# app/__init__.py
from flask import Flask, render_template
from app.config import Config
from app.database import init_db_app, query_one


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # 1. Registra o gerenciamento automático de conexão MySQL no ciclo de vida do Flask
    init_db_app(app)

    # 2. Rota inicial consultando contagens reais diretamente no banco MySQL!
    @app.route("/")
    def index():
        total_usuarios = query_one("SELECT COUNT(*) AS total FROM usuarios")["total"]
        total_permissoes = query_one("SELECT COUNT(*) AS total FROM permissoes")["total"]
        total_salas = query_one("SELECT COUNT(*) AS total FROM salas")["total"]
        total_reservas = query_one("SELECT COUNT(*) AS total FROM reservas")["total"]

        resumo_banco = [
            {
                "modulo": "Usuários Cadastrados",
                "status": f"{total_usuarios} contas prontas para login",
                "icone": "👥",
            },
            {
                "modulo": "Permissões Granulares",
                "status": f"{total_permissoes} chaves ativas no MySQL",
                "icone": "🔐",
            },
            {
                "modulo": "Catálogo de Salas",
                "status": f"{total_salas} salas e laboratórios no banco",
                "icone": "🏢",
            },
            {
                "modulo": "Agenda de Reservas",
                "status": f"{total_reservas} reservas de exemplo criadas",
                "icone": "📅",
            },
        ]
        return render_template("boas_vindas.html", modulos=resumo_banco)

    return app
```

### Teste agora no Navegador!
1. Inicie o servidor com `python run.py`.
2. Acesse `http://127.0.0.1:5000`.
3. Veja os 4 cartões mostrando os números reais vindos do seu banco MySQL: **3 contas prontas para login**, **13 chaves ativas no MySQL**, **10 salas e laboratórios no banco** e **6 reservas de exemplo criadas**!

---

## 9. Guia de Sobrevivência no Laboratório (Erros Comuns na Aula 04)

| Sintoma / Mensagem de Erro | Causa Mais Provável | Como Resolver Rapidamente |
| :--- | :--- | :--- |
| `mysql.connector.errors.ProgrammingError: 1045 (28000): Access denied for user 'root'@'localhost'` | A senha configurada em `DB_PASSWORD` no seu arquivo `.env` não bate com a senha do seu servidor MySQL local. | Abra o arquivo `.env`, ajuste `DB_PASSWORD=` (coloque a senha correta do seu MySQL ou deixe vazio após o `=` se usar XAMPP/Laragon sem senha) e rode `python seed_db.py` novamente. |
| `FileNotFoundError: [Errno 2] No such file or directory: '...\sql\schema.sql'` | O arquivo `schema.sql` não foi salvo dentro da pasta `sql/` (o seed agora acha a pasta sozinho, não importa de onde você rode o comando). | Certifique-se de que o arquivo está em `sistema_reservas_salas/sql/schema.sql`, com esse nome exato. |
| `SystemExit: DB_NAME inválido: use apenas letras, números e sublinhado (_).` | O `DB_NAME` do `.env` tem espaço, hífen, aspas ou outro símbolo. | Use um nome simples, como `gestao_reservas_salas`. |
| `mysql.connector.errors.PoolError: Failed getting connection; pool exhausted` | Mais requisições simultâneas do que conexões no pool, ou o `close_db` não está registrado e as conexões não voltam. | Confira `init_db_app(app)` no `create_app()` e, se necessário, aumente `DB_POOL_SIZE` no `.env`. |
| `KeyError: 'DB_POOL_SIZE'` | Faltou adicionar a linha `DB_POOL_SIZE = ...` na classe `Config`. | Volte ao início da seção 4 e inclua a linha no `app/config.py`. |
| `mysql.connector.errors.ProgrammingError: Could not process parameters` | Ao chamar `query_one` ou `query_all` passando apenas 1 parâmetro, faltou a vírgula no final da tupla: `(valor)` em vez de `(valor,)`. | Sempre escreva tuplas de um único elemento com vírgula no final: `query_one("SELECT * FROM salas WHERE id = %s", (sala_id,))`. |
| `RuntimeError: Working outside of application context` | Você tentou chamar `get_db()` ou `query_all()` fora de uma rota do Flask (por exemplo, solto no topo de um arquivo). | As funções de `app/database.py` usam `current_app` e `g`, portanto devem ser chamadas sempre **dentro** de funções executadas durante uma requisição HTTP do Flask. |

---

## 10. Exercícios Práticos de Fixação

Vamos praticar o uso das nossas novas funções `query_all` e `query_one` do arquivo `app/database.py`:

1. **Desafio 1 (Criando uma Rota JSON de Salas Reais):** Dentro de `create_app()` no arquivo `app/__init__.py`, importe também a função `query_all` de `app.database`. Crie uma rota temporária `@app.route("/api/salas-teste")` que use `query_all` para buscar `codigo`, `nome`, `bloco` e `capacidade` de todas as salas ativas ordenadas por `codigo ASC` e retorne o resultado (o Flask converterá a lista de dicionários em JSON automaticamente!).
2. **Desafio 2 (Buscando Uma Sala Específica com Parâmetro Seguro):** Crie uma rota `@app.route("/api/salas-teste/<codigo_sala>")` que use `query_one` com o marcador `%s` para buscar no MySQL os dados da sala cujo `codigo` seja igual ao `codigo_sala` digitado na URL. Se a sala existir, retorne o dicionário dela; se não existir (`if sala is None:`), retorne `{"erro": "Sala não encontrada"}, 404`.
3. **Desafio 3 (Inspecionando o Hash no Banco):** Abra o seu cliente MySQL (Workbench ou terminal) e execute `SELECT id, nome, email, senha_hash FROM gestao_reservas_salas.usuarios;`. Observe os valores da coluna `senha_hash`.

<details>
<summary><strong>💡 Clique aqui para ver o Gabarito Comentado dos Exercícios</strong></summary>

```python
# No arquivo app/__init__.py, atualize o import do topo:
from app.database import init_db_app, query_one, query_all

# E adicione estas duas rotas dentro de create_app() (antes do "return app"):

    # Resolução do Desafio 1:
    @app.route("/api/salas-teste")
    def api_salas_teste():
        salas = query_all(
            """
            SELECT codigo, nome, bloco, capacidade
            FROM salas
            WHERE ativa = 1
            ORDER BY codigo ASC
            """
        )
        return {"total": len(salas), "salas": salas}

    # Resolução do Desafio 2:
    @app.route("/api/salas-teste/<codigo_sala>")
    def api_detalhe_sala(codigo_sala):
        # Repare na vírgula obrigatória em (codigo_sala.upper(),) por ser tupla de 1 elemento!
        sala = query_one(
            "SELECT id, codigo, nome, bloco, capacidade, recursos FROM salas WHERE codigo = %s",
            (codigo_sala.upper(),),
        )
        if sala is None:
            return {"erro": "Sala não encontrada"}, 404
        return sala
```
*Teste no navegador acessando `http://127.0.0.1:5000/api/salas-teste` e `http://127.0.0.1:5000/api/salas-teste/LAB-101`!*

> ⚠️ **Estas rotas são só para exercício.** Elas entregam dados do banco para **qualquer pessoa**, sem exigir login. Na Aula 05 vamos criar o sistema de autenticação; assim que terminá-la, **apague** as duas rotas de teste (e a `/status` da Aula 02) do `app/__init__.py`.
</details>

---

## O Que Vem a Seguir?

Nosso banco de dados **MySQL** já está criado, populado com 13 permissões, 3 usuários, 10 salas e 6 reservas, e conectado com segurança ao **Flask**!

Na **Aula 05**, vamos construir o sistema completo de **Autenticação, Sessões, Blueprints e Controle de Acesso em Dupla Camada**: você aprenderá como criar a tela de Login real, como o Flask guarda quem está logado, como criar os decorators `@login_obrigatorio` e `@permissao_obrigatoria` e como montar nosso layout administrativo definitivo (`base.html`) com menu lateral inteligente em **Tailwind CSS**!

---
<!-- nav -->
| Anterior | Índice | Próxima |
| :--- | :---: | ---: |
| [← Aula 03 — Modelagem do Banco MySQL](./aula_03_modelagem_banco_mysql_permissoes.md) | [📚 Índice do Curso](./README.md) | [Aula 05 — Autenticação e Permissões →](./aula_05_autenticacao_sessoes_blueprints_acesso.md) |