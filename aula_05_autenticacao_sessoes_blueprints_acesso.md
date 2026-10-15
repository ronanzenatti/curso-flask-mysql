# Aula 05 — Autenticação, Sessões, Blueprints e Controle de Acesso em Dupla Camada

Nas **Aulas 03 e 04**, construímos nosso banco de dados **MySQL** (`gestao_reservas_salas`) e executamos o script `seed_db.py`, que cadastrou nossas **13 permissões personalizadas** e criou **3 contas de usuários** com senhas criptografadas:
* **Ana Administradora (`admin@salafacil.com`):** 13 permissões.
* **Carlos Gestor (`gestor@salafacil.com`):** 9 permissões.
* **Beatriz Professora (`beatriz@salafacil.com`):** 3 permissões.

Agora chegou o momento de dar vida a esses usuários! Nesta **Aula 05**, vamos construir todo o sistema de **Segurança, Login e Layout Administrativo** do **SalaFácil**. Você vai aprender na prática:
1. A diferença entre **Autenticação** (*Quem é você?*) e **Autorização** (*O que você pode fazer?*).
2. Como o Flask lembra quem está logado usando **Sessões Criptografadas (`session`)**.
3. Como proteger o sistema em **Dupla Camada** (bloqueando rotas no Python e escondendo botões no HTML).
4. Como funcionam os **Decorators de Segurança** (`@login_obrigatorio` e `@permissao_obrigatoria`).
5. O que são **Blueprints** (e como organizar rotas em módulos independentes).
6. Como usar **Herança de Templates (`{% extends "base.html" %}`)** e **Flash Messages** com **Tailwind CSS**.
7. Como se defender de 4 ataques comuns da Web: **CSRF** (formulários forjados), **redirecionamento malicioso** (*open redirect*), **força bruta** no login e telas de erro que vazam informação.

---

## 1. Conceitos Fundamentais: Autenticação, Autorização e Sessões HTTP

Antes de escrevermos o código de segurança, precisamos compreender três conceitos que sustentam qualquer aplicação web moderna:

### 1.1 — Autenticação vs. Autorização
Embora pareçam palavras parecidas, elas resolvem problemas diferentes:
* **Autenticação (*Authentication*):** É o ato de provar **quem você é**. Acontece na tela de **Login**, quando você digita seu e-mail e sua senha e o Flask confere se eles batem com o registro da tabela `usuarios`.
* **Autorização (*Authorization*):** Depois que o sistema já sabe quem você é, a autorização verifica **quais ações você tem direito de executar**. Acontece quando a professora Beatriz (já logada!) tenta acessar a tela de criar um novo usuário e o sistema responde: *"Eu sei que você é a Beatriz, mas você não possui a chave `usuarios.gerenciar`!"*.

### 1.2 — Como o Navegador "Lembra" que Você Fez Login? (O Objeto `session`)
O protocolo HTTP tem uma característica curiosa: por padrão, ele é **Stateless (Sem Memória)**. Isso significa que, se você fizer login na página 1 e, dois segundos depois, clicar em um link para abrir a página 2, o servidor HTTP não faz a menor ideia de que os dois cliques vieram da mesma pessoa!

Para resolver isso, o Flask utiliza um recurso chamado **`session` (Sessão)**:
1. Quando o usuário acerta o e-mail e a senha na rota de login, nós guardamos o número do `id` dele dentro do dicionário `session` do Flask:
   ```python
   session["usuario_id"] = usuario["id"]
   ```
2. O Flask pega esse dicionário, **assina digitalmente com a nossa `SECRET_KEY`** (aquela que configuramos no `.env` na Aula 02!) e envia para o navegador guardar em um pequeno arquivo chamado **Cookie de Sessão**.
3. A partir desse instante, a cada novo clique que o usuário der no sistema, o navegador envia automaticamente esse Cookie de volta para o Flask. O Flask confere a assinatura digital e descobre na hora: *"Ah! Quem está clicando agora é o usuário de ID 1!"*.
4. Quando o usuário clica em **Sair do Sistema (Logout)**, nós rodamos `session.clear()`, destruindo o crachá de acesso!

---

## 2. Controle de Acesso em Dupla Camada (Backend + Frontend)

Na Aula 03, criamos 13 códigos de permissão (como `salas.criar`, `reservas.aprovar`, `usuarios.permissoes`). Onde devemos verificar se o usuário logado possui essas chaves?

Em um sistema profissional, fazemos a verificação em **duas camadas complementares**:

```text
[ Camada 1: Frontend (Jinja2 + Tailwind CSS) ]
   └─ Função tem_permissao('salas.criar') no HTML
   └─ Papel: Esconder links do menu e botões que o usuário não pode usar (Boa Experiência / UX).

[ Camada 2: Backend (Rotas Python no Flask) ]
   └─ Decorator @permissao_obrigatoria('salas.criar') na rota Python
   └─ Papel: Segurança Real! Se alguém digitar a URL "/salas/nova" direto no navegador,
             o Python bloqueia a invasão e devolve o Erro HTTP 403 (Acesso Negado).
```

> ⚠️ **Por que nunca confiar apenas em esconder o botão no HTML?**  
> Se você apenas esconder o botão **"+ Nova Sala"** na tela, um usuário curioso ainda pode ir até a barra de endereços do navegador e digitar manualmente `http://127.0.0.1:5000/salas/nova`. Por isso, o HTML cuida da **organização visual**, mas quem garante a **segurança de verdade** é o decorator Python na rota!

---

## 2.1 Os 4 Ataques Que Vamos Bloquear Nesta Aula (Contextualização)

Ter login e permissões é essencial, mas **não basta**. Um sistema com tela de login ainda pode ser enganado de formas bem criativas. Conheça os quatro golpes que vamos barrar, cada um com uma analogia do dia a dia:

| Ataque | Analogia | Como funciona | Nossa defesa |
| :--- | :--- | :--- | :--- |
| **CSRF** (*Cross-Site Request Forgery*, "pedido forjado entre sites") | Alguém imita a sua assinatura num cheque em branco **enquanto você está com o talão aberto** no banco. | Você está logado no SalaFácil. Em outra aba, um site malicioso esconde um formulário que envia um `POST` para `/salas/7/excluir`. O seu navegador, **obediente**, anexa o cookie de login e o sistema acha que foi você. | Cada formulário leva uma **ficha numerada secreta** (token). Pedidos sem a ficha correta são recusados. |
| **Open Redirect** (*redirecionamento aberto*) | Trocar a placa de uma rua: o motorista confia na placa e vai parar no lugar errado. | O link `.../auth/login?proximo=http://site-falso.com` leva a vítima, após logar de verdade, para um site-clone que pede a senha de novo. | Só aceitamos destinos que sejam **caminhos internos** do nosso próprio site. |
| **Força bruta** | Um ladrão testando todas as combinações de um cadeado de 4 dígitos. | Um programa tenta milhares de senhas por minuto no login. | Um "porteiro" **conta as tentativas erradas** e bloqueia temporariamente quem passar do limite. |
| **Vazamento por erro** | Um funcionário que, ao errar, lê em voz alta o manual interno para o cliente. | Uma tela de erro técnica mostra caminhos de arquivos e trechos do código. | Páginas de erro **amigáveis** (404 e 500) que não revelam nada. |

---

## 3. Construindo o Motor de Segurança (`app/utils/security.py`)

Vamos criar o arquivo **`app/utils/security.py`**. Ele reunirá as funções essenciais que trabalharão em todas as páginas do sistema:
1. `carregar_usuario_logado()`: Roda automaticamente **antes de cada requisição** para buscar no MySQL os dados do usuário logado e suas permissões ativas **com uma única consulta**.
2. `tem_permissao(codigo)`: Responde `True` ou `False` se o usuário tiver a chave solicitada.
3. `rota_inicial()`: Escolhe a primeira página que o usuário realmente tem permissão de abrir.
4. `obter_token_csrf()` e `validar_csrf()`: A "ficha numerada" que protege os formulários contra CSRF.
5. `caminho_seguro(destino)`: Filtra o parâmetro `proximo` contra redirecionamentos maliciosos.
6. `login_bloqueado()`, `registrar_falha_login()` e `limpar_falhas_login()`: O "porteiro" contra força bruta.
7. `@login_obrigatorio`: Decorator que barra visitantes não logados e os envia para a tela de Login.
8. `@permissao_obrigatoria(*codigos)`: Decorator que exige uma ou mais chaves de permissão para acessar uma rota.

Abra o arquivo **`app/utils/security.py`** e digite o código abaixo:

```python
# app/utils/security.py
import hmac
import secrets
import time
from functools import wraps
from urllib.parse import urlparse
from flask import session, redirect, url_for, flash, g, abort, request, jsonify
from app.database import query_all

# Páginas iniciais possíveis, em ordem de preferência: (permissão exigida, rota)
PAGINAS_INICIAIS = (
    ("reservas.visualizar", "reservas.listar"),
    ("salas.visualizar", "salas.listar"),
    ("usuarios.visualizar", "usuarios.listar"),
    ("relatorios.visualizar", "relatorios.painel"),
)

# Proteção contra força bruta: no máximo 5 erros de senha a cada 5 minutos
TENTATIVAS_MAXIMAS = 5
JANELA_EM_SEGUNDOS = 300
_falhas_de_login = {}  # {"ip|email": [horário_da_falha, horário_da_falha, ...]}


def carregar_usuario_logado():
    """
    Executa antes de cada requisição HTTP.
    Busca o usuário da sessão e o conjunto (set) de códigos de permissão em UMA só consulta.
    """
    g.usuario = None
    g.permissoes = set()

    # Arquivos estáticos (CSS, JS) não precisam saber quem está logado
    if request.endpoint == "static":
        return

    usuario_id = session.get("usuario_id")
    if usuario_id is None:
        return

    linhas = query_all(
        """
        SELECT u.id, u.nome, u.email, u.setor, u.cargo_etiqueta, p.codigo
        FROM usuarios u
        LEFT JOIN usuario_permissoes up ON up.usuario_id = u.id
        LEFT JOIN permissoes p ON p.id = up.permissao_id
        WHERE u.id = %s AND u.ativo = 1
        """,
        (usuario_id,),
    )

    if not linhas:
        # Usuário apagado ou desativado enquanto navegava: derruba a sessão
        session.clear()
        return

    primeira = linhas[0]
    g.usuario = {
        "id": primeira["id"],
        "nome": primeira["nome"],
        "email": primeira["email"],
        "setor": primeira["setor"],
        "cargo_etiqueta": primeira["cargo_etiqueta"],
    }
    g.permissoes = {linha["codigo"] for linha in linhas if linha["codigo"] is not None}


def tem_permissao(codigo_permissao):
    """Retorna True se o usuário logado possuir a permissão informada."""
    if not getattr(g, "usuario", None):
        return False
    return codigo_permissao in getattr(g, "permissoes", set())


def rota_inicial():
    """Devolve o nome da primeira página que o usuário tem permissão de abrir."""
    for permissao, rota in PAGINAS_INICIAIS:
        if tem_permissao(permissao):
            return rota
    return "auth.meu_perfil"


def obter_token_csrf():
    """Devolve a 'ficha numerada' desta sessão, criando uma se ainda não existir."""
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
    return session["csrf_token"]


def validar_csrf():
    """Executa antes de cada requisição: recusa POSTs sem a ficha correta."""
    if request.method not in ("POST", "PUT", "PATCH", "DELETE"):
        return None

    esperado = session.get("csrf_token", "")
    enviado = request.form.get("csrf_token", "")
    if not esperado or not hmac.compare_digest(esperado.encode(), enviado.encode()):
        flash("Sua sessão expirou ou o formulário é inválido. Tente novamente.", "aviso")
        return redirect(url_for("index"))
    return None


def caminho_seguro(destino):
    """Aceita apenas caminhos internos do nosso site (ex.: /salas/). Qualquer outra coisa vira None."""
    if not destino or not destino.startswith("/"):
        return None
    if destino.startswith("//") or "\\" in destino:
        return None
    partes = urlparse(destino)
    if partes.scheme or partes.netloc:
        return None
    return destino


def login_bloqueado(chave):
    """True se esta chave (IP + e-mail) já errou a senha vezes demais nos últimos 5 minutos."""
    agora = time.time()
    recentes = [t for t in _falhas_de_login.get(chave, []) if agora - t < JANELA_EM_SEGUNDOS]
    _falhas_de_login[chave] = recentes
    return len(recentes) >= TENTATIVAS_MAXIMAS


def registrar_falha_login(chave):
    """Anota que houve mais uma tentativa errada para esta chave."""
    _falhas_de_login.setdefault(chave, []).append(time.time())


def limpar_falhas_login(chave):
    """Apaga o histórico de erros depois de um login bem-sucedido."""
    _falhas_de_login.pop(chave, None)


def login_obrigatorio(view_func):
    """Decorator que exige que o usuário esteja autenticado."""
    @wraps(view_func)
    def wrapper(*args, **kwargs):
        if g.usuario is None:
            if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                return jsonify({"erro": "Sessão expirada. Faça login novamente."}), 401
            flash("Por favor, faça login para acessar esta página.", "aviso")
            return redirect(url_for("auth.login", proximo=request.path))
        return view_func(*args, **kwargs)
    return wrapper


def permissao_obrigatoria(*codigos_necessarios):
    """
    Decorator que exige que o usuário logado possua TODAS as permissões
    passadas como argumento. Exemplo:
    @permissao_obrigatoria('reservas.visualizar', 'reservas.aprovar')
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_obrigatorio
        def wrapper(*args, **kwargs):
            faltantes = [c for c in codigos_necessarios if not tem_permissao(c)]
            if faltantes:
                if request.headers.get("X-Requested-With") == "XMLHttpRequest":
                    return jsonify({
                        "erro": "Você não possui permissão para realizar esta ação.",
                        "permissoes_faltantes": faltantes,
                    }), 403
                abort(403)
            return view_func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 4. Dissecando o `app/utils/security.py` (Entendendo Cada Detalhe!)

Este arquivo é uma verdadeira aula de programação profissional em Python. Vamos entender por que cada peça foi escrita dessa forma:

### 4.1 — Por que recarregar as permissões do MySQL a cada clique em `carregar_usuario_logado()`?
Imagine que o administrador descubra que um funcionário mudou de setor e remova imediatamente a permissão `reservas.aprovar` dele (ou bloqueie a conta dele mudando `ativo = 0`).
* Se nós tivéssemos guardado as permissões dentro do cookie `session` no momento do login, o funcionário continuaria aprovando reservas até decidir fazer logout!
* Como `carregar_usuario_logado()` consulta o MySQL a cada clique (`WHERE id = %s AND ativo = 1`), se o administrador revogar uma permissão ou desativar um usuário, **o efeito é instantâneo no próximo clique**, derrubando a sessão na hora (`session.clear()`) se a conta estiver inativa!

### 4.2 — Por que guardar `g.permissoes` em um Conjunto (`set`) e não em uma Lista (`list`)?
Repare na linha:
```python
g.permissoes = {linha["codigo"] for linha in linhas}
```
Usar chaves `{ ... }` sem dois-pontos cria um **Conjunto (`set`)** em Python (uma *Set Comprehension*). Em uma página HTML com 30 botões, chamaremos `tem_permissao(...)` dezenas de vezes. Buscar um item dentro de um `set` em Python usa uma tabela *hash* com tempo de busca constante $O(1)$ (instantâneo!), além de nunca permitir códigos duplicados.

### 4.3 — Como funciona um Decorator por dentro (`@wraps`, `*args`, `**kwargs`)?
Olhe para a estrutura do `@login_obrigatorio`:
1. Ele recebe a função da rota original (`view_func`) e cria uma função "envelope" (`wrapper`) em volta dela.
2. O comando `@wraps(view_func)` (importado de `functools`) preserva o nome original da sua função para o Flask não se confundir ao registrar várias rotas protegidas.
3. Os parâmetros `*args, **kwargs` permitem que o decorator funcione em **qualquer rota**, tanto naquelas que não recebem parâmetros (`def listar():`) quanto nas que recebem variáveis da URL (`def editar(sala_id):`).
4. Se `g.usuario is None` (ninguém está logado), o envelope interrompe o caminho, cria um aviso com `flash(...)` e redireciona a pessoa para a tela de login guardando o endereço que ela tentou acessar (`proximo=request.path`). Se o usuário estiver logado, ele executa normalmente a rota original (`return view_func(*args, **kwargs)`)!

### 4.4 — O que faz o `abort(403)` em `@permissao_obrigatoria`?
Quando o usuário está logado, mas não possui alguma das permissões exigidas (`if faltantes:`), chamamos `abort(403)`. Essa função do Flask interrompe imediatamente a execução da rota e aciona a nossa página personalizada de **Acesso Negado (Erro HTTP 403)**!
*(Nota: se a requisição vier do nosso JavaScript de busca dinâmica das próximas aulas — identificada pelo cabeçalho `"XMLHttpRequest"` —, devolvemos um JSON com status `401` ou `403`).*

### 4.5 — Linha por linha de `carregar_usuario_logado()` (agora com **uma única** consulta)

> **Por que mudamos?** A versão anterior fazia **duas** consultas (uma para o usuário, outra para as permissões) em **todo** clique, inclusive quando o navegador pedia um simples arquivo `.js`. Em um laboratório com 30 alunos isso são milhares de consultas desnecessárias por minuto. Agora fazemos **uma só** e ignoramos os arquivos estáticos.
>
> **Analogia:** em vez de ir duas vezes ao balcão da secretaria (uma para pegar o crachá, outra para pegar a lista de chaves), você faz **um pedido só**: "me entregue o crachá com a lista de chaves já grampeada".

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `g.usuario = None` / `g.permissoes = set()` | Coloca valores "vazios" na mochila `g`. | Garante que `g.usuario` **sempre existe**, mesmo para visitantes não logados. | Páginas que perguntam `g.usuario` quebrariam com `AttributeError` para quem não está logado. |
| `if request.endpoint == "static": return` | Se o pedido é para um arquivo estático (CSS/JS), encerra a função aqui. | Evita consultar o MySQL à toa a cada arquivo baixado. | Cada carregamento de página dispara consultas extras, e se o banco cair até o CSS deixa de carregar. |
| `usuario_id = session.get("usuario_id")` / `if usuario_id is None: return` | Lê o crachá da sessão; se não há crachá, o visitante é anônimo e paramos. | Quem não fez login não precisa de consulta alguma. | Seria feita uma consulta com `NULL` a cada visita anônima. |
| `SELECT u.id, ..., p.codigo FROM usuarios u LEFT JOIN usuario_permissoes up ... LEFT JOIN permissoes p ...` | Junta usuário, tabela pivô e catálogo: devolve **uma linha por permissão** do usuário, repetindo os dados dele. | Traz tudo de uma vez. O `LEFT JOIN` garante que um usuário **sem nenhuma permissão** ainda apareça (com `p.codigo` vazio). | Com `INNER JOIN`, um usuário com zero permissões pareceria "inexistente" e seria deslogado. |
| `WHERE u.id = %s AND u.ativo = 1` | Só considera contas ativas, usando `%s` (blindagem contra SQL Injection). | Se o administrador bloquear a conta, o próximo clique já derruba a sessão. | Contas bloqueadas continuariam navegando. |
| `if not linhas: session.clear(); return` | Se nada voltou (conta apagada ou inativa), destrói o crachá. | Derrubada imediata da sessão. | O usuário bloqueado manteria o cookie e continuaria dentro. |
| `primeira = linhas[0]` / `g.usuario = {...}` | Todas as linhas repetem os dados do usuário, então basta olhar a primeira para montar o dicionário. | Guardamos só os campos necessários (sem a senha). | Se montássemos com `**primeira`, o campo `codigo` iria junto sem necessidade. |
| `g.permissoes = {linha["codigo"] for linha in linhas if linha["codigo"] is not None}` | Cria o conjunto (`set`) de códigos, ignorando o `None` do usuário sem permissões. | `set` oferece busca instantânea e sem duplicados. | Sem o filtro `is not None`, um usuário sem permissões ficaria com `{None}` no conjunto. |

### 4.6 — Linha por linha da proteção **CSRF** (`obter_token_csrf` e `validar_csrf`)

> **Analogia da ficha numerada:** na entrada de um show você recebe uma **pulseira com número único**. Para entrar na área VIP, o segurança confere se a sua pulseira bate com a lista. Um golpista que "empurra" você para dentro da fila não consegue **adivinhar** o número da sua pulseira. Aqui, o servidor entrega uma ficha secreta a cada navegador (guardada na `session`) e exige que **todo formulário `POST` a devolva**. Um site malicioso consegue fazer o navegador enviar o cookie, mas **não consegue ler** a ficha para incluí-la no formulário falso.

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `import secrets` | Módulo do Python para gerar números realmente imprevisíveis. | O `random` comum é previsível demais para segurança. | Teríamos de usar algo fraco, e um atacante poderia adivinhar a ficha. |
| `if "csrf_token" not in session:` | "Esta sessão ainda não tem ficha?" | Cria a ficha uma única vez por sessão. | Uma ficha nova a cada página invalidaria formulários abertos em outras abas. |
| `session["csrf_token"] = secrets.token_hex(32)` | Gera 32 bytes aleatórios em texto hexadecimal (64 caracteres) e guarda na sessão. | É a "pulseira numerada": impossível de adivinhar. | Sem ficha, não há o que conferir. |
| `if request.method not in ("POST", "PUT", "PATCH", "DELETE"): return None` | Só confere pedidos que **alteram** dados. `return None` significa "pode seguir". | Pedidos `GET` só leem (nossas buscas dinâmicas usam `GET`). | Até as buscas exigiriam ficha, e as listagens deixariam de abrir. |
| `esperado = session.get("csrf_token", "")` / `enviado = request.form.get("csrf_token", "")` | `esperado` é a ficha guardada; `enviado` é a que veio no formulário (campo escondido). | Duas pontas que precisam coincidir. | Nada para comparar. |
| `hmac.compare_digest(esperado.encode(), enviado.encode())` | Compara os dois textos de forma "segura em tempo constante". O `.encode()` converte em bytes. | Uma comparação comum (`==`) para na primeira letra diferente, e a diferença de tempo pode vazar pistas. Sem o `.encode()`, caracteres com acento no campo enviado causariam erro 500. | Usar `==` funciona, mas é vulnerável a ataques de tempo. |
| `if not esperado or not ...:` | Se não há ficha na sessão **ou** se ela não bate, recusa. | Cobre sessão expirada e formulário forjado. | Formulários forjados passariam. |
| `flash(...)` / `return redirect(url_for("index"))` | Avisa o usuário e o manda para a página inicial. Como o `before_request` devolveu uma resposta, **a rota nunca executa**. | O dano é evitado antes de qualquer código sensível rodar. | A ação (por exemplo, excluir uma sala) seria executada normalmente. |

### 4.7 — Linha por linha de `caminho_seguro()` (contra *open redirect*)

Lembra da "placa trocada"? Quando o `login_obrigatorio` manda o visitante para o login, ele guarda a página desejada em `proximo`. Depois do login, redirecionamos para lá. Mas esse valor vem da **barra de endereços**, que qualquer um pode editar.

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `if not destino or not destino.startswith("/"): return None` | Rejeita valores vazios e qualquer coisa que não comece com `/` (como `http://...`). | Caminhos internos sempre começam com `/`. | `proximo=http://site-falso.com` seria aceito. |
| `if destino.startswith("//") or "\\" in destino: return None` | Rejeita `//site-falso.com` (que o navegador interpreta como endereço externo) e barras invertidas. | Truques clássicos para burlar o filtro anterior. | O endereço `//site-falso.com` passaria pelo filtro e levaria a vítima para fora. |
| `partes = urlparse(destino)` / `if partes.scheme or partes.netloc: return None` | Decompõe o endereço e recusa se houver protocolo (`http:`) ou domínio. | Segunda camada de defesa. | Variações estranhas poderiam escapar da checagem de texto. |
| `return destino` | Devolve o caminho aprovado. | O chamador usa o resultado diretamente. | A função devolveria `None` sempre. |

### 4.8 — Linha por linha do "porteiro" contra força bruta

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `TENTATIVAS_MAXIMAS = 5` / `JANELA_EM_SEGUNDOS = 300` | Constantes: 5 erros em 300 segundos (5 minutos). | Fácil de ajustar num lugar só. | Os números ficariam espalhados pelo código. |
| `_falhas_de_login = {}` | Dicionário na memória do servidor: cada chave (`"ip\|email"`) guarda a lista de horários dos erros. | Precisamos lembrar dos erros entre uma requisição e outra. | Sem memória, não há como contar tentativas. |
| `recentes = [t for t in ... if agora - t < JANELA_EM_SEGUNDOS]` | Mantém só os erros dos últimos 5 minutos (os mais antigos "expiram"). | Quem errou há 1 hora merece nova chance. | O bloqueio nunca terminaria. |
| `return len(recentes) >= TENTATIVAS_MAXIMAS` | `True` se já atingiu o limite. | É o veredito do porteiro. | O login nunca seria bloqueado. |
| `registrar_falha_login(chave)` | Acrescenta o horário atual à lista. | Alimenta a contagem. | Os erros nunca seriam contados. |
| `limpar_falhas_login(chave)` | Apaga o histórico quando o login dá certo. | Quem acertou a senha não deve ficar "marcado". | Um usuário honesto que errou 4 vezes seria bloqueado no quinto erro de outro dia. |

> ⚠️ **Limite honesto desta solução:** a lista vive na memória do processo. Se o servidor reiniciar, ela zera; se houver vários processos, cada um tem a sua. Para um sistema real usa-se uma ferramenta como *Flask-Limiter* com Redis. Para aprender o conceito (e proteger um laboratório), esta versão simples é suficiente.

### 4.9 — Linha por linha de `rota_inicial()` e `PAGINAS_INICIAIS`

Antes, após o login todos iam para a Agenda de Reservas. Mas e um usuário **sem** `reservas.visualizar`? Cairia na tela de "Acesso Negado" logo na entrada!

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `PAGINAS_INICIAIS = ((permissão, rota), ...)` | Uma tupla de pares "permissão exigida → página". A ordem é a preferência. | Dados organizados num só lugar. | Os `if` teriam de ser repetidos em vários arquivos. |
| `for permissao, rota in PAGINAS_INICIAIS:` | Percorre os pares do primeiro ao último. | Escolhe a **primeira** página liberada. | Sem laço, só olharíamos uma opção. |
| `if tem_permissao(permissao): return rota` | Se o usuário tem a chave, devolve o nome da rota. | O usuário entra numa página que ele pode abrir. | Quem não tem acesso à agenda veria o erro 403 ao entrar. |
| `return "auth.meu_perfil"` | Plano B: a página de perfil sempre abre para quem está logado. | Nunca deixa o usuário sem destino. | A função devolveria `None` e o `url_for` quebraria. |

---

## 5. O Que é um Blueprint? Criando o Módulo de Autenticação (`app/blueprints/auth.py`)

Até a Aula 04, criávamos rotas usando `@app.route(...)` diretamente dentro de `app/__init__.py`. Mas como dividir as rotas em **5 arquivos separados** (`auth.py`, `salas.py`, `usuarios.py`, `reservas.py`, `relatorios.py`)?

Para isso, o Flask possui o conceito de **Blueprint (Planta Baixa / Módulo de Rotas)**.
Pense em um Blueprint como um "mini-aplicativo destacável": você cria todas as rotas de autenticação dentro do arquivo `app/blueprints/auth.py` usando `@auth_bp.route(...)` e, depois, "pluga" esse módulo inteiro no `app/__init__.py` com uma única linha (`app.register_blueprint(auth_bp)`)!

### Como funciona o `url_prefix="/auth"` e o `url_for` com Blueprints?
Quando criamos:
```python
auth_bp = Blueprint("auth", __name__, url_prefix="/auth")
```
* Todas as rotas desse arquivo ganham automaticamente o prefixo `/auth` na URL! Assim, `@auth_bp.route("/login")` responderá no endereço `http://127.0.0.1:5000/auth/login`.
* E sempre que quisermos gerar um link para uma rota usando a função `url_for(...)` do Flask, usamos o formato **`"nome_do_blueprint.nome_da_funcao"`** (por exemplo: `url_for("auth.login")`, `url_for("auth.logout")`, `url_for("reservas.listar")`).
* **Por que usar `url_for("auth.login")` em vez de escrever `"/auth/login"` fixo no HTML?**  
  Porque se amanhã você decidir mudar o endereço da rota no Python, o `url_for` atualiza todos os links e redirecionamentos do sistema automaticamente!

---

### Passo 5.1 — Codificando o `app/blueprints/auth.py`

Abra o arquivo **`app/blueprints/auth.py`** e digite o código completo das 3 rotas de autenticação (`/auth/login`, `/auth/logout` e `/auth/meu-perfil`):

```python
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
```

### Entendendo o fluxo da rota `login()` acima:
1. **`methods=["GET", "POST"]`**: Por padrão, uma rota no Flask só aceita pedidos `GET` (abrir a página). Ao passar `methods=["GET", "POST"]`, a mesma rota `/auth/login` faz duas coisas:
   * Quando o usuário **abre a tela** no navegador (`GET`), ela vai direto para a última linha e exibe o formulário (`return render_template("auth/login.html")`).
   * Quando o usuário **preenche e envia o formulário** (`if request.method == "POST":`), ela captura os campos `request.form.get("email")` e `request.form.get("senha")` e valida no banco!
2. **`check_password_hash(usuario["senha_hash"], senha)`**: Lembra que na Aula 04 salvamos a senha como um hash criptográfico? Aqui a função `check_password_hash` compara o hash do banco com a senha digitada sem jamais expor a senha em texto puro.
3. **`flash("...", "sucesso")` (Mensagens Flash):** A função `flash()` guarda uma mensagem rápida que será exibida **apenas uma única vez** no topo da próxima página carregada e depois sumirá sozinha! O segundo argumento (`"sucesso"`, `"erro"`, `"aviso"`, `"info"`) é a categoria que usaremos no HTML para pintar a caixa de verde, vermelho, amarelo ou azul!

### Linha por linha das novidades do `auth.py`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `from app.utils.security import (login_obrigatorio, caminho_seguro, login_bloqueado, ...)` | Importa as ferramentas de segurança que criamos neste arquivo `security.py`. Os parênteses permitem quebrar a lista em várias linhas. | O `auth.py` é o único lugar que decide quem pode entrar. | `ImportError` ao iniciar o servidor. |
| `if g.usuario is not None: return redirect(url_for("index"))` | Quem já está logado e abre a tela de login é mandado para a página inicial dele. | Evita mostrar um formulário de login desnecessário. | Um usuário logado veria o formulário de login de novo (não é grave, mas é confuso). |
| `chave_tentativas = f"{request.remote_addr}\|{email}"` | Junta o endereço IP de quem está acessando com o e-mail digitado. | O limite vale para "este computador tentando esta conta", e não derruba todo mundo se alguém errar. | Um único contador global bloquearia todos os usuários por causa de um atacante. |
| `if login_bloqueado(chave_tentativas): ... return render_template(...), 429` | Se já errou demais, nem consulta o banco: mostra o aviso e responde com o status HTTP **429** (*Too Many Requests*, "pedidos demais"). | Interrompe o ataque de força bruta **antes** de gastar processamento verificando senhas. | O atacante poderia testar milhares de senhas por minuto. |
| `"SELECT id, nome, senha_hash, ativo FROM usuarios WHERE email = %s"` | Busca apenas as 4 colunas de que o login precisa (antes era `SELECT *`). | Menos dados trafegando e menos chance de vazar colunas sem querer. | Funcionaria também; é uma boa prática de economia e segurança. |
| `registrar_falha_login(chave_tentativas)` | Anota um erro de senha (ou de e-mail inexistente) para essa chave. | Alimenta o contador do porteiro. | Nunca haveria bloqueio, pois nenhum erro seria contado. |
| `limpar_falhas_login(chave_tentativas)` | Zera os erros após um login correto. | Quem acertou não deve ser punido por erros antigos. | Um usuário honesto seria bloqueado por erros de digitação acumulados. |
| `session.clear()` seguido de `session["usuario_id"] = ...` | Destrói qualquer sessão antiga e cria o crachá novo. | Evita que um cookie antigo ou de outra pessoa continue valendo (*session fixation*). | Dados da sessão anterior (como flash e tokens) ficariam misturados com a nova. |
| `proximo = caminho_seguro(request.args.get("proximo"))` | Lê o `?proximo=` da URL e o filtra pela função de segurança. `request.args` é o dicionário da query string. | Só seguimos para destinos **internos**; o resto vira `None`. | Qualquer link malicioso `?proximo=http://site-falso.com` redirecionaria a vítima para fora do sistema. |
| `redirect(proximo or url_for("index"))` | Vai para o destino pedido; se não houver (ou foi rejeitado), vai para `index`. | O `index` decide a melhor página inicial, de acordo com as permissões do usuário. | Sem o plano B, `redirect(None)` causa erro. |
| `methods=["POST"]` no `logout` | Aceita **apenas** `POST` (um clique em botão de formulário). | Se o logout aceitasse `GET`, um site malicioso poderia deslogar você com uma simples imagem `<img src=".../logout">`. | Qualquer link ou imagem de terceiros poderia encerrar a sua sessão. |

> **Por que a mensagem do login diz só "E-mail ou senha inválidos"?** Se disséssemos "e-mail não encontrado", o atacante descobriria quais e-mails existem. A frase única não entrega essa pista.

---

## 6. Herança de Templates e Layout Base em Tailwind CSS (`app/templates/base.html`)

Todas as telas internas do nosso sistema terão a mesma estrutura ao redor:
* O `<head>` carregando o Tailwind CSS;
* O **Menu Lateral (*Sidebar*)** escuro à esquerda com os links dos módulos e os dados do usuário logado;
* A barra de **Mensagens Flash** no topo;
* A área central onde entra o conteúdo específico de cada página.

Para não termos que copiar e colar o menu lateral em 12 arquivos HTML diferentes, o Jinja2 oferece a **Herança de Templates**:
1. Criamos um arquivo **"Molde Pai"** chamado **`app/templates/base.html`** contendo toda a estrutura fixa e deixamos "janelas abertas" marcadas com **`{% block conteudo %}{% endblock %}`**.
2. Nas outras páginas (as **"Páginas Filhas"**, como `login.html` e `perfil.html`), basta escrever **`{% extends "base.html" %}`** na primeira linha e preencher apenas o recheio dentro de `{% block conteudo %} ... {% endblock %}`!

Abra o arquivo **`app/templates/base.html`** e insira o código abaixo:

```html
<!-- app/templates/base.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block titulo %}SalaFácil — Gestão de Reservas{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @media print {
            .no-print { display: none !important; }
            body { background: white !important; }
        }
    </style>
</head>
<body class="bg-slate-100 text-slate-800 min-h-screen flex flex-col md:flex-row">

    {% if g.usuario %}
    <!-- Menu Lateral (Sidebar) -->
    <aside class="w-full md:w-64 bg-slate-900 text-slate-100 flex-shrink-0 flex flex-col justify-between no-print">
        <div>
            <div class="p-6 border-b border-slate-800 flex items-center gap-3">
                <span class="bg-indigo-600 text-white font-extrabold px-3 py-1.5 rounded-lg text-lg">SF</span>
                <div>
                    <h1 class="font-bold text-lg leading-none">SalaFácil</h1>
                    <span class="text-xs text-slate-400">Reservas & Espaços</span>
                </div>
            </div>

            <nav class="p-4 space-y-1">
                {% if tem_permissao('reservas.visualizar') %}
                <a href="{{ url_for('reservas.listar') }}"
                   class="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition
                          {% if request.blueprint == 'reservas' %}bg-indigo-600 text-white{% else %}text-slate-300 hover:bg-slate-800{% endif %}">
                    <span>📅</span> Agenda de Reservas
                </a>
                {% endif %}

                {% if tem_permissao('salas.visualizar') %}
                <a href="{{ url_for('salas.listar') }}"
                   class="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition
                          {% if request.blueprint == 'salas' %}bg-indigo-600 text-white{% else %}text-slate-300 hover:bg-slate-800{% endif %}">
                    <span>🏢</span> Catálogo de Salas
                </a>
                {% endif %}

                {% if tem_permissao('usuarios.visualizar') %}
                <a href="{{ url_for('usuarios.listar') }}"
                   class="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition
                          {% if request.blueprint == 'usuarios' %}bg-indigo-600 text-white{% else %}text-slate-300 hover:bg-slate-800{% endif %}">
                    <span>👥</span> Usuários & Permissões
                </a>
                {% endif %}

                {% if tem_permissao('relatorios.visualizar') %}
                <a href="{{ url_for('relatorios.painel') }}"
                   class="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition
                          {% if request.blueprint == 'relatorios' %}bg-indigo-600 text-white{% else %}text-slate-300 hover:bg-slate-800{% endif %}">
                    <span>📊</span> Relatórios Gerenciais
                </a>
                {% endif %}
            </nav>
        </div>

        <div class="p-4 border-t border-slate-800 bg-slate-950/50">
            <a href="{{ url_for('auth.meu_perfil') }}" class="block hover:bg-slate-800 p-2 rounded-lg transition">
                <p class="text-sm font-semibold text-white truncate">{{ g.usuario.nome }}</p>
                <p class="text-xs text-indigo-400 truncate">{{ g.usuario.cargo_etiqueta }} • {{ g.usuario.setor }}</p>
                <p class="text-[11px] text-slate-400 mt-1">{{ g.permissoes|length }} permissões ativas</p>
            </a>
            <form method="POST" action="{{ url_for('auth.logout') }}">
                <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
                <button type="submit"
                        class="mt-3 w-full block text-center py-2 px-3 rounded-lg bg-rose-600/20 text-rose-300 hover:bg-rose-600 hover:text-white text-xs font-semibold transition">
                    Sair do Sistema
                </button>
            </form>
        </div>
    </aside>
    {% endif %}

    <!-- Área de Conteúdo Principal -->
    <div class="flex-1 flex flex-col min-w-0">
        <!-- Mensagens Flash -->
        {% with mensagens = get_flashed_messages(with_categories=true) %}
        {% if mensagens %}
        <div class="max-w-7xl w-full mx-auto px-6 pt-6 space-y-2 no-print">
            {% for categoria, texto in mensagens %}
            <div class="p-4 rounded-xl border text-sm font-medium flex items-center justify-between shadow-sm
                {% if categoria == 'sucesso' %}bg-emerald-50 border-emerald-200 text-emerald-800
                {% elif categoria == 'erro' %}bg-rose-50 border-rose-200 text-rose-800
                {% elif categoria == 'aviso' %}bg-amber-50 border-amber-200 text-amber-800
                {% else %}bg-indigo-50 border-indigo-200 text-indigo-800{% endif %}">
                <span>{{ texto }}</span>
                <button onclick="this.parentElement.remove()" class="text-xs font-bold opacity-60 hover:opacity-100">✕</button>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        {% endwith %}

        <main class="flex-1 max-w-7xl w-full mx-auto px-6 py-8">
            {% block conteudo %}{% endblock %}
        </main>
    </div>

    <script src="{{ url_for('static', filename='js/tabela_dinamica.js') }}"></script>
    {% block scripts %}{% endblock %}
</body>
</html>
```

### Quatro detalhes inteligentes do `base.html` para você reparar:
1. **`{% if g.usuario %}` em volta do `<aside>`:** Quando ninguém está logado (na tela de Login), `g.usuario` é `None`, então a barra lateral inteira fica oculta automaticamente!
2. **`{% if tem_permissao('usuarios.visualizar') %}` em cada item do menu:** O menu lateral só desenha os botões dos módulos que o usuário logado tem direito de ver!
3. **`{% if request.blueprint == 'salas' %}bg-indigo-600 text-white...`:** O Flask sabe qual Blueprint está aberto no momento (`request.blueprint`). Usamos isso para deixar o botão do menu atual destacado em azul-índigo!
4. **O botão "Sair do Sistema" virou um pequeno formulário `POST`:**

   | Trecho | O que é | Por que está ali | O que acontece se tirar |
   | :--- | :--- | :--- | :--- |
   | `<form method="POST" action="{{ url_for('auth.logout') }}">` | Um formulário de uma só ação: enviar um `POST` para a rota de logout. | A rota `logout` só aceita `POST` (veja a explicação do `auth.py`). | Com um link `<a>` comum, o navegador faria `GET` e receberia o erro **405 Method Not Allowed**. |
   | `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` | Campo **invisível** que carrega a "ficha numerada" da sessão. `csrf_token()` é a função `obter_token_csrf` que vamos liberar para os templates no `__init__.py`. | O `validar_csrf` exige essa ficha em todo `POST`. | O servidor responde "Sua sessão expirou ou o formulário é inválido" e **o usuário não consegue sair**. |
   | `<button type="submit" ...>Sair do Sistema</button>` | Botão que envia o formulário. As classes do Tailwind mantêm o visual de antes. | Substitui o `<a>`; é o que o usuário clica. | Sem botão, o formulário não tem como ser enviado. |

> 📌 **Regra de ouro daqui até o fim do curso:** **todo `<form method="POST">` precisa ter o campo escondido `csrf_token`**. Formulários `GET` (as buscas) não precisam.

---

## 7. Criando os 3 Templates do Módulo de Autenticação

Agora vamos criar as 3 páginas filhas que herdam de `base.html`:

### Passo 7.1 — Tela de Login (`app/templates/auth/login.html`)

Abra o arquivo **`app/templates/auth/login.html`** e insira o código abaixo:

```html
<!-- app/templates/auth/login.html -->
{% extends "base.html" %}
{% block titulo %}Login — SalaFácil{% endblock %}

{% block conteudo %}
<div class="min-h-[80vh] flex items-center justify-center">
    <div class="bg-white w-full max-w-md rounded-2xl shadow-lg border border-slate-200 p-8">
        <div class="text-center mb-8">
            <span class="inline-block bg-indigo-600 text-white font-extrabold px-4 py-2 rounded-xl text-xl mb-3">SF</span>
            <h2 class="text-2xl font-bold text-slate-900">Acesso ao SalaFácil</h2>
            <p class="text-sm text-slate-500 mt-1">Entre com suas credenciais para gerenciar reservas de salas</p>
        </div>

        <form method="POST" class="space-y-5">
            <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">E-mail Institucional</label>
                <input type="email" name="email" required placeholder="exemplo@salafacil.com"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none text-sm">
            </div>

            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">Senha</label>
                <input type="password" name="senha" required placeholder="••••••••"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none text-sm">
            </div>

            <button type="submit"
                    class="w-full py-3 px-4 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-sm transition text-sm">
                Entrar no Sistema
            </button>
        </form>

        {% if config.DEBUG %}
        <div class="mt-6 pt-5 border-t border-slate-100 text-xs text-slate-500 space-y-1">
            <p class="font-semibold text-slate-700">Contas de demonstração (Senha: <code>123456</code>):</p>
            <p>• <strong>Admin:</strong> admin@salafacil.com</p>
            <p>• <strong>Gestor:</strong> gestor@salafacil.com</p>
            <p>• <strong>Solicitante:</strong> beatriz@salafacil.com</p>
        </div>
        {% endif %}
    </div>
</div>
{% endblock %}
```

#### Linha por linha das novidades do `login.html`

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `<form method="POST" class="space-y-5">` (**sem** atributo `action`) | Um formulário que, sem `action`, envia os dados para **o mesmo endereço em que a página está**, incluindo o que vem depois do `?`. | Quando o visitante chega por `/auth/login?proximo=/salas/`, o `proximo` continua na URL no momento do envio. Antes, o `action="{{ url_for('auth.login') }}"` apagava essa parte e o `proximo` **nunca funcionava**. | Se você recolocar o `action` com `url_for`, o redirecionamento para a página que o usuário queria abrir deixa de funcionar. |
| `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` | A ficha numerada em campo invisível. | Sem ela, `validar_csrf` recusa o login. | O login mostra "Sua sessão expirou ou o formulário é inválido" para todo mundo. |
| `{% if config.DEBUG %} ... {% endif %}` | Mostra o quadro de contas de demonstração **apenas** quando o modo debug está ligado. O Flask libera o objeto `config` para os templates automaticamente. | Num servidor real, exibir logins e senha padrão na tela é um convite para invasores. | O quadro apareceria também em produção, entregando as contas de teste. |

---

### Passo 7.2 — Tela de Meu Perfil e Permissões Ativas (`app/templates/auth/perfil.html`)

Quando o usuário clicar sobre o próprio nome no canto inferior esquerdo da barra lateral, ele verá seus dados cadastrais e a tabela detalhada de todas as permissões personalizadas vinculadas à sua conta.

Abra o arquivo **`app/templates/auth/perfil.html`** e insira o código abaixo:

```html
<!-- app/templates/auth/perfil.html -->
{% extends "base.html" %}
{% block titulo %}Meu Perfil e Permissões — SalaFácil{% endblock %}

{% block conteudo %}
<div class="mb-6 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
    <div>
        <h2 class="text-2xl font-bold text-slate-900">Meu Perfil de Acesso</h2>
        <p class="text-sm text-slate-500">Consulte seus dados institucionais e suas permissões personalizadas ativas</p>
    </div>
    <a href="{{ url_for('reservas.listar') }}" class="text-sm text-indigo-600 hover:text-indigo-800 font-semibold">
        ← Ir para a Agenda de Reservas
    </a>
</div>

<div class="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-8 grid grid-cols-1 md:grid-cols-4 gap-6">
    <div>
        <p class="text-xs font-bold uppercase text-slate-400">Nome Completo</p>
        <p class="text-base font-bold text-slate-900 mt-1">{{ g.usuario.nome }}</p>
    </div>
    <div>
        <p class="text-xs font-bold uppercase text-slate-400">E-mail Institucional</p>
        <p class="text-sm font-medium text-slate-700 mt-1">{{ g.usuario.email }}</p>
    </div>
    <div>
        <p class="text-xs font-bold uppercase text-slate-400">Setor</p>
        <p class="text-sm font-medium text-slate-700 mt-1">{{ g.usuario.setor }}</p>
    </div>
    <div>
        <p class="text-xs font-bold uppercase text-slate-400">Perfil Base / Chaves Ativas</p>
        <div class="mt-1 flex items-center gap-2">
            <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700">
                {{ g.usuario.cargo_etiqueta }}
            </span>
            <span class="px-2.5 py-1 rounded-lg bg-emerald-50 text-emerald-700 font-bold text-xs">
                {{ permissoes|length }} permissões
            </span>
        </div>
    </div>
</div>

<div class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
    <div class="px-6 py-4 border-b border-slate-200 bg-slate-50">
        <h3 class="text-sm font-bold text-slate-700 uppercase">Permissões Personalizadas Concedidas à Sua Conta</h3>
    </div>
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="border-b border-slate-200 text-xs font-bold text-slate-500 uppercase bg-white">
                    <th class="py-3.5 px-6">Módulo</th>
                    <th class="py-3.5 px-6">Código da Chave</th>
                    <th class="py-3.5 px-6">Permissão</th>
                    <th class="py-3.5 px-6">Descrição</th>
                    <th class="py-3.5 px-6 text-right">Concedida em</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 text-sm">
                {% for p in permissoes %}
                <tr class="hover:bg-slate-50/80">
                    <td class="py-3.5 px-6 font-semibold text-indigo-700">{{ p.modulo }}</td>
                    <td class="py-3.5 px-6">
                        <code class="text-xs bg-slate-100 text-slate-800 px-2 py-0.5 rounded font-mono">{{ p.codigo }}</code>
                    </td>
                    <td class="py-3.5 px-6 font-medium text-slate-900">{{ p.nome }}</td>
                    <td class="py-3.5 px-6 text-slate-600 text-xs">{{ p.descricao }}</td>
                    <td class="py-3.5 px-6 text-right text-xs text-slate-500">
                        {{ p.concedido_em.strftime('%d/%m/%Y %H:%M') if p.concedido_em else '—' }}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="5" class="py-8 text-center text-slate-500">
                        Nenhuma permissão personalizada vinculada ao seu usuário.
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
```

---

### Passo 7.3 — Tela de Acesso Negado — Erro 403 (`app/templates/auth/403.html`)

Sempre que um usuário tentar acessar uma rota sem possuir a chave de permissão necessária, o decorator `@permissao_obrigatoria` acionará `abort(403)`, exibindo esta tela amigável:

Abra o arquivo **`app/templates/auth/403.html`** e insira o código abaixo:

```html
<!-- app/templates/auth/403.html -->
{% extends "base.html" %}
{% block titulo %}Acesso Negado (403) — SalaFácil{% endblock %}

{% block conteudo %}
<div class="bg-white rounded-2xl border border-rose-200 p-10 text-center max-w-lg mx-auto mt-12 shadow-sm">
    <div class="w-16 h-16 bg-rose-100 text-rose-600 rounded-full flex items-center justify-center text-3xl mx-auto mb-4">
        🔒
    </div>
    <h2 class="text-2xl font-bold text-slate-900">Permissão Insuficiente</h2>
    <p class="text-slate-600 text-sm mt-2">
        Seu perfil atual (<strong>{{ g.usuario.cargo_etiqueta }}</strong>) não possui a permissão personalizada necessária para executar esta operação.
    </p>
    <div class="mt-6 flex justify-center gap-3">
        <a href="{{ url_for('auth.meu_perfil') }}" class="px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-medium">
            Ver Minhas Permissões
        </a>
        <a href="{{ url_for(rota_inicial()) }}" class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium">
            Voltar para a Página Inicial
        </a>
    </div>
</div>
{% endblock %}
```

> **O que mudou?** O botão "Voltar" apontava sempre para a Agenda. Se o usuário **não** tivesse `reservas.visualizar`, ele cairia em outro 403 e ficaria preso num ciclo de "Acesso Negado". Agora `url_for(rota_inicial())` leva à primeira página que ele realmente pode abrir. Se tirar essa mudança, o ciclo volta.

---

### Passo 7.4 — Tela de Erro Amigável (`app/templates/erro.html`)

Quando ocorre um erro inesperado (um bug nosso, o banco fora do ar) ou alguém digita um endereço que não existe, o Flask mostra uma página técnica cinza. Em modo debug isso ajuda o programador, mas **em um sistema real** essa página pode revelar caminhos de pastas e trechos do código. Vamos criar uma tela amigável, usada para os erros **404** (página não encontrada) e **500** (erro interno).

Abra o arquivo **`app/templates/erro.html`** e insira o código abaixo:

```html
<!-- app/templates/erro.html -->
{% extends "base.html" %}
{% block titulo %}Erro {{ codigo }} — SalaFácil{% endblock %}

{% block conteudo %}
<div class="bg-white rounded-2xl border border-slate-200 p-10 text-center max-w-lg mx-auto mt-12 shadow-sm">
    <p class="text-5xl font-extrabold text-indigo-600">{{ codigo }}</p>
    <h2 class="text-2xl font-bold text-slate-900 mt-3">{{ titulo }}</h2>
    <p class="text-slate-600 text-sm mt-2">{{ mensagem }}</p>
    <div class="mt-6">
        <a href="{{ url_for('index') }}" class="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium">
            Voltar para o Início
        </a>
    </div>
</div>
{% endblock %}
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `{% extends "base.html" %}` | Herda o layout padrão (menu lateral e mensagens). | A tela de erro mantém a identidade visual do sistema. | A página de erro ficaria "pelada", sem estilo e sem o Tailwind. |
| `Erro {{ codigo }}` e `{{ codigo }}` | Mostram o número do erro (404, 500) enviado pelo Python. | O usuário e o suporte técnico precisam saber qual erro ocorreu. | Todas as telas de erro pareceriam iguais. |
| `{{ titulo }}` e `{{ mensagem }}` | Textos que o Python define para cada tipo de erro. | Um único template atende vários erros (reaproveitamento). | Você precisaria de um arquivo HTML diferente para cada erro. |
| `url_for('index')` | Link para a página inicial. | Dá ao usuário uma saída. | O usuário fica numa "rua sem saída". |

---

## 8. Preparando os Esqueletos dos Demais Blueprints e o `app/__init__.py` Definitivo

Repare que o nosso menu lateral em `base.html` já aponta para os links dos 4 módulos operacionais (`reservas.listar`, `salas.listar`, `usuarios.listar` e `relatorios.painel`), que implementaremos em detalhes nas **Aulas 07, 08, 09 e 10**.

Se tentarmos registrar `salas_bp`, `usuarios_bp`, `reservas_bp` e `relatorios_bp` no `app/__init__.py` enquanto esses 4 arquivos estiverem completamente em branco (0 bytes), o Python reclamaria dizendo que não encontrou as variáveis `*_bp`.

### Como resolver isso como um desenvolvedor esperto?
Vamos colocar um **esqueleto inicial de 8 linhas** em cada um desses 4 arquivos (`salas.py`, `usuarios.py`, `reservas.py` e `relatorios.py`) já protegidos por `@permissao_obrigatoria`! Assim:
1. O seu `app/__init__.py` e o seu `base.html` já ficam **100% prontos na versão final** hoje mesmo;
2. Você já consegue fazer login, navegar pelo menu lateral e testar o bloqueio da **Tela 403** agora mesmo na Aula 05;
3. Nas Aulas 07, 08, 09 e 10, bastará substituir o esqueleto de cada arquivo pelo código completo do respectivo módulo!

### Passo 8.1 — Esqueletos Provisórios dos 4 Módulos Operacionais

Coloque os pequenos blocos abaixo nos respectivos arquivos dentro de `app/blueprints/`:

**1. Em `app/blueprints/salas.py` (Será expandido na Aula 07):**
```python
# app/blueprints/salas.py (Esqueleto provisório para teste na Aula 05/06)
from flask import Blueprint, redirect, url_for, flash
from app.utils.security import permissao_obrigatoria

salas_bp = Blueprint("salas", __name__, url_prefix="/salas")

@salas_bp.route("/")
@permissao_obrigatoria("salas.visualizar")
def listar():
    flash("O Catálogo de Salas completo será implementado na Aula 07! Exibindo seu perfil de acesso:", "info")
    return redirect(url_for("auth.meu_perfil"))
```

**2. Em `app/blueprints/usuarios.py` (Será expandido na Aula 08):**
```python
# app/blueprints/usuarios.py (Esqueleto provisório para teste na Aula 05/06)
from flask import Blueprint, redirect, url_for, flash
from app.utils.security import permissao_obrigatoria

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

@usuarios_bp.route("/")
@permissao_obrigatoria("usuarios.visualizar")
def listar():
    flash("O Módulo de Usuários e Matriz de Permissões será implementado na Aula 08!", "info")
    return redirect(url_for("auth.meu_perfil"))
```

**3. Em `app/blueprints/reservas.py` (Será expandido na Aula 09):**
```python
# app/blueprints/reservas.py (Esqueleto provisório para teste na Aula 05/06)
from flask import Blueprint, redirect, url_for
from app.utils.security import permissao_obrigatoria

reservas_bp = Blueprint("reservas", __name__, url_prefix="/reservas")

@reservas_bp.route("/")
@permissao_obrigatoria("reservas.visualizar")
def listar():
    return redirect(url_for("auth.meu_perfil"))
```

**4. Em `app/blueprints/relatorios.py` (Será expandido na Aula 10):**
```python
# app/blueprints/relatorios.py (Esqueleto provisório para teste na Aula 05/06)
from flask import Blueprint, redirect, url_for, flash
from app.utils.security import permissao_obrigatoria

relatorios_bp = Blueprint("relatorios", __name__, url_prefix="/relatorios")

@relatorios_bp.route("/")
@permissao_obrigatoria("relatorios.visualizar")
def painel():
    flash("O Painel de Relatórios Gerenciais será implementado na Aula 10!", "info")
    return redirect(url_for("auth.meu_perfil"))
```

---

### Passo 8.2 — Atualizando o `app/__init__.py` para a Versão Definitiva

Antes, uma pequena atualização no `app/config.py`: adicione **duas linhas** dentro da classe `Config` (por exemplo, logo abaixo de `DEBUG`) para endurecer o cookie de login:

```python
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `SESSION_COOKIE_HTTPONLY = True` | Proíbe que scripts JavaScript da página leiam o cookie de login. | Se um dia alguém conseguir injetar um script malicioso (XSS), ele não consegue roubar o cookie. | O cookie ficaria legível por JavaScript. *(O Flask já usa `True` por padrão; deixamos explícito para você enxergar a proteção.)* |
| `SESSION_COOKIE_SAMESITE = "Lax"` | Diz ao navegador para **não enviar** o cookie em pedidos `POST` disparados por outros sites. | É uma segunda barreira contra CSRF, somada à ficha numerada. | O navegador enviaria o cookie também em formulários de sites estranhos. *(O padrão do Flask é "sem restrição", por isso precisamos escrever.)* |

> 🔒 Na hospedagem real, com HTTPS, adicione também `SESSION_COOKIE_SECURE = True` (o cookie só viaja em conexões criptografadas). Não ligamos agora porque o laboratório usa `http://` simples.

Agora atualize o arquivo **`app/__init__.py`** para conectar nosso motor de segurança (`before_request`), injetar `tem_permissao` e o token CSRF em todos os templates HTML (`context_processor`), configurar as páginas de erro e registrar os 5 Blueprints:

```python
# app/__init__.py
from flask import Flask, render_template, redirect, url_for
from app.config import Config
from app.database import init_db_app
from app.utils.security import (
    carregar_usuario_logado, validar_csrf,
    tem_permissao, obter_token_csrf, rota_inicial,
)


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY não definida. Crie o arquivo .env conforme a Aula 02.")

    # Inicializa o gerenciamento de conexão MySQL
    init_db_app(app)

    # Antes de cada request: 1º confere a ficha CSRF, 2º carrega o usuário e suas permissões
    app.before_request(validar_csrf)
    app.before_request(carregar_usuario_logado)

    # Torna estas funções acessíveis em qualquer template HTML
    @app.context_processor
    def injetar_utilitarios():
        return {
            "tem_permissao": tem_permissao,
            "csrf_token": obter_token_csrf,
            "rota_inicial": rota_inicial,
        }

    # Páginas de erro amigáveis
    @app.errorhandler(403)
    def acesso_negado(erro):
        return render_template("auth/403.html"), 403

    @app.errorhandler(404)
    def nao_encontrado(erro):
        return render_template(
            "erro.html", codigo=404, titulo="Página não encontrada",
            mensagem="O endereço que você digitou não existe ou foi removido.",
        ), 404

    @app.errorhandler(500)
    def erro_interno(erro):
        # O Flask já grava o erro completo no terminal; o usuário vê só uma mensagem simples
        return render_template(
            "erro.html", codigo=500, titulo="Algo deu errado",
            mensagem="Tivemos um problema interno. Tente novamente em instantes.",
        ), 500

    # Registro dos Blueprints do sistema
    from app.blueprints.auth import auth_bp
    from app.blueprints.usuarios import usuarios_bp
    from app.blueprints.salas import salas_bp
    from app.blueprints.reservas import reservas_bp
    from app.blueprints.relatorios import relatorios_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(usuarios_bp)
    app.register_blueprint(salas_bp)
    app.register_blueprint(reservas_bp)
    app.register_blueprint(relatorios_bp)

    @app.route("/")
    def index():
        # Cada pessoa vai para a primeira página que tem permissão de abrir
        return redirect(url_for(rota_inicial()))

    return app
```

### Linha por linha das novidades do `app/__init__.py`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `from app.utils.security import (carregar_usuario_logado, validar_csrf, ...)` | Traz as ferramentas de segurança para dentro da fábrica. | O `create_app` é quem as conecta ao Flask. | `ImportError` na inicialização. |
| `app.before_request(validar_csrf)` | Registra uma função para rodar **antes de toda rota**. Se ela devolver uma resposta (nosso redirecionamento), a rota nem chega a executar. | É o "segurança da portaria": confere a ficha numerada antes de qualquer coisa. | Todos os `POST` passam sem conferir a ficha, e o CSRF volta a funcionar. |
| `app.before_request(carregar_usuario_logado)` | Segundo "segurança": descobre quem é o usuário e quais chaves ele tem. | Abastece `g.usuario` e `g.permissoes`. | Os decorators e templates não sabem quem está logado. |
| *(a ordem: CSRF primeiro, usuário depois)* | O Flask executa os `before_request` na ordem em que foram registrados. | Se a ficha é inválida, nem gastamos consultas ao MySQL. | Funcionaria, mas faria consultas inúteis em pedidos que serão recusados. |
| `@app.context_processor def injetar_utilitarios(): return {...}` | Qualquer dicionário devolvido vira variável global em todos os templates. | Assim o HTML pode usar `tem_permissao(...)`, `csrf_token()` e `rota_inicial()` sem passar nada manualmente. | `UndefinedError: 'csrf_token' is undefined` em toda página com formulário. |
| `"csrf_token": obter_token_csrf` | Entrega a **função** (sem parênteses); o template a chama com `csrf_token()`. | Cada formulário pede a ficha na hora de ser desenhado. | Sem ela, nenhum formulário consegue carregar a ficha. |
| `@app.errorhandler(403)` | Intercepta `abort(403)` e mostra a nossa tela de "Permissão Insuficiente", mantendo o status HTTP 403. | Mensagem clara para quem tentou entrar onde não pode. | Aparece a tela técnica padrão do Flask. |
| `@app.errorhandler(404)` | Intercepta "página inexistente" (URL digitada errada). | Substitui a página cinza padrão por uma tela amigável. | O usuário vê um texto técnico e sem saída. |
| `@app.errorhandler(500)` | Intercepta qualquer erro interno não tratado. | Esconde detalhes técnicos do usuário (o erro completo continua no terminal para o programador). Os dados que estavam sendo gravados são desfeitos, pois a conexão volta ao pool. | Em produção o visitante poderia ver informações internas do sistema. |
| `return redirect(url_for(rota_inicial()))` na rota `/` | Manda cada pessoa para a primeira página liberada para ela. | Quem não tem acesso à Agenda não cai mais em "Acesso Negado". | Todos iriam para `reservas.listar` e usuários sem essa chave veriam o erro 403. |

* **`@app.context_processor` (resumo):** Graças a ele podemos escrever `{% if tem_permissao('salas.criar') %}` em qualquer HTML sem precisar passar `tem_permissao` manualmente em cada `render_template(...)`.
* **`@app.errorhandler(403)`:** Intercepta o comando `abort(403)` disparado pelo nosso decorator `@permissao_obrigatoria` e desenha a nossa página estilizada `auth/403.html` mantendo o código de status HTTP `403`!

> 🧹 **Faxina de segurança:** se você criou as rotas de teste `/status` (Aula 02) e `/api/salas-teste` (Aula 04), **apague-as agora**: elas mostram dados para qualquer visitante, sem login. A versão final do `create_app()` acima já não as contém.

---

## 9. Testando o Sistema de Login, Permissões e Erro 403 na Prática!

Inicie (ou reinicie) o servidor no terminal com `python run.py` e faça esta bateria de testes guiados no navegador:

1. **Teste 1 (Redirecionamento Automático para Login):**  
   Acesse `http://127.0.0.1:5000/`. Como você ainda não está logado, o decorator `@login_obrigatorio` vai interceptar seu acesso, exibir a mensagem amarela *"Por favor, faça login para acessar esta página."* e abrir `/auth/login`.
2. **Teste 2 (Login como Administradora — 13 Permissões):**  
   Entre com **`admin@salafacil.com`** e senha **`123456`**. Observe:
   * A barra lateral esquerda (*Sidebar*) exibe todos os **4 módulos** (Agenda de Reservas, Catálogo de Salas, Usuários & Permissões e Relatórios Gerenciais).
   * A tabela de **Meu Perfil** lista as **13 permissões** concedidas à Ana Administradora.
3. **Teste 3 (Login como Professora Solicitante — 3 Permissões):**  
   Clique em **Sair do Sistema** na barra lateral inferior e faça login agora com **`beatriz@salafacil.com`** (senha `123456`). Observe a diferença imediata:
   * No menu lateral esquerdo, os botões **Usuários & Permissões** e **Relatórios Gerenciais** desapareceram sozinhos (Camada Frontend funcionando!).
   * Na tabela de **Meu Perfil**, aparecem apenas as **3 permissões** dela (`salas.visualizar`, `reservas.visualizar`, `reservas.criar`).
4. **Teste 4 (Tentativa de Invasão pela URL — Testando a Tela 403!):**  
   Ainda logado com a **`beatriz@salafacil.com`**, vá até a barra de endereços do navegador e digite manualmente `http://127.0.0.1:5000/usuarios/` ou `http://127.0.0.1:5000/relatorios/`.  
   **Resultado:** O decorator `@permissao_obrigatoria` bloqueia a tentativa no Backend e exibe imediatamente a nossa tela de **Permissão Insuficiente (Erro 403)**! 🔒
5. **Teste 5 (Voltando para onde você estava — o `proximo` funcionando):**  
   Saia do sistema. Depois acesse `http://127.0.0.1:5000/auth/meu-perfil` (sem estar logado). Você será levado para `/auth/login?proximo=/auth/meu-perfil`. Faça login: em vez de ir para a página inicial, você cai **direto no Meu Perfil**, a página que queria abrir!
6. **Teste 6 (O filtro contra redirecionamento malicioso):**  
   Saia novamente e abra `http://127.0.0.1:5000/auth/login?proximo=//site-falso.com`. Faça login normalmente. O sistema **ignora** o destino suspeito e leva você à página inicial do sistema, nunca ao site externo.
7. **Teste 7 (Provando a proteção CSRF):**  
   Logado, abra o *Inspecionar Elemento* (`F12`) na tela de Meu Perfil, localize no menu lateral o campo `<input type="hidden" name="csrf_token" ...>` do botão **Sair** e clique com o botão direito → *Delete element* (apagando a ficha). Agora clique em **Sair do Sistema**. Resultado: a mensagem amarela *"Sua sessão expirou ou o formulário é inválido"* aparece e você **continua logado**: o pedido sem ficha foi recusado!
8. **Teste 8 (O porteiro contra força bruta):**  
   Na tela de login, digite um e-mail válido com a senha errada **5 vezes seguidas**. Na sexta tentativa, até a senha **correta** é recusada com *"Muitas tentativas incorretas. Aguarde 5 minutos..."*. Para liberar sem esperar, pare e reinicie o servidor (`CTRL + C` e `python run.py`), já que o contador vive na memória.
9. **Teste 9 (Página de erro amigável):**  
   Acesse `http://127.0.0.1:5000/pagina-que-nao-existe`. Em vez da tela cinza padrão do Flask, aparece o cartão **"Erro 404 — Página não encontrada"**, no visual do sistema.

---

## 10. Guia de Sobrevivência no Laboratório (Erros Comuns na Aula 05)

| Sintoma / Mensagem de Erro | Causa Mais Provável | Como Resolver Rapidamente |
| :--- | :--- | :--- |
| `werkzeug.routing.exceptions.BuildError: Could not build url for endpoint 'salas.listar'` | Um dos 4 arquivos de Blueprint (`salas.py`, `usuarios.py`, `reservas.py` ou `relatorios.py`) não teve a rota inicial registrada ou não foi registrado com `app.register_blueprint(...)` no `app/__init__.py`. | Confira se você colocou os esqueletos do **Passo 8.1** nos 4 arquivos e se os 5 `app.register_blueprint(...)` estão presentes no `app/__init__.py`. |
| `RuntimeError: SECRET_KEY não definida. Crie o arquivo .env conforme a Aula 02.` | A nossa trava de segurança do `create_app()` funcionou: o `.env` não foi encontrado ou a linha `SECRET_KEY=` está vazia. | Confira se o `.env` está na raiz do projeto e preencha a `SECRET_KEY`. |
| `jinja2.exceptions.UndefinedError: 'csrf_token' is undefined` | O `context_processor` do `app/__init__.py` não foi atualizado e não entrega o `csrf_token` aos templates. | Confira o dicionário devolvido por `injetar_utilitarios()` (3 chaves: `tem_permissao`, `csrf_token`, `rota_inicial`). |
| Todo formulário `POST` volta com *"Sua sessão expirou ou o formulário é inválido"*. | O formulário não tem o campo `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`, ou o cookie de sessão foi apagado. | Adicione o campo escondido logo após a tag `<form method="POST">`. Lembre-se: **todo** `POST` precisa dele. |
| `405 Method Not Allowed` ao clicar em *Sair do Sistema*. | O botão de sair ainda é um link `<a href>` (que faz `GET`), mas a rota agora aceita só `POST`. | Troque o link pelo pequeno formulário do `base.html` (Passo 6). |
| Digito `admin@salafacil.com` e `123456`, mas sempre diz *"E-mail ou senha inválidos"*. | O script `python seed_db.py` da Aula 04 ainda não foi executado no banco de dados atual. | Pare o servidor (`CTRL+C`), rode `python seed_db.py` para popular os usuários e depois inicie `python run.py` novamente. |

---

## 11. Exercícios Práticos de Fixação

1. **Desafio 1 (Alteração de Senha no Meu Perfil):** Adicione na rota `/auth/meu-perfil` (`app/blueprints/auth.py` e `app/templates/auth/perfil.html`) um pequeno formulário `POST` que permita ao próprio usuário logado atualizar sua senha (validando a senha atual com `check_password_hash` e salvando a nova com `generate_password_hash`).
2. **Desafio 2 (Testando o Perfil de Gestor):** Faça login com **`gestor@salafacil.com`** (senha `123456`), confira no menu lateral quais módulos aparecem para o Carlos Gestor e tente acessar `/usuarios/` pela barra de endereços para ver o bloqueio `403`.

<details>
<summary><strong>💡 Clique aqui para ver o Gabarito Comentado do Desafio 1</strong></summary>

**1. Em `app/blueprints/auth.py`**, atualize os imports do topo para incluir `generate_password_hash` e `execute_write`, e adapte a rota `meu_perfil` para aceitar `GET` e `POST`:

```python
from werkzeug.security import check_password_hash, generate_password_hash
from app.database import query_one, query_all, execute_write
```

```python
@auth_bp.route("/meu-perfil", methods=["GET", "POST"])
@login_obrigatorio
def meu_perfil():
    if request.method == "POST":
        senha_atual = request.form.get("senha_atual", "")
        nova_senha = request.form.get("nova_senha", "")

        usuario_db = query_one("SELECT senha_hash FROM usuarios WHERE id = %s", (g.usuario["id"],))
        if not check_password_hash(usuario_db["senha_hash"], senha_atual):
            flash("A senha atual informada está incorreta.", "erro")
        elif len(nova_senha) < 6:
            flash("A nova senha deve ter pelo menos 6 caracteres.", "aviso")
        else:
            execute_write(
                "UPDATE usuarios SET senha_hash = %s WHERE id = %s",
                (generate_password_hash(nova_senha), g.usuario["id"]),
            )
            flash("Sua senha foi atualizada com sucesso!", "sucesso")
            return redirect(url_for("auth.meu_perfil"))

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
```

**2. Em `app/templates/auth/perfil.html`**, adicione antes da tabela de permissões o formulário (repare no campo escondido do CSRF, obrigatório em todo `POST`):

```html
<form method="POST" class="bg-white rounded-2xl shadow-sm border border-slate-200 p-6 mb-8 grid grid-cols-1 md:grid-cols-3 gap-4">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <input type="password" name="senha_atual" required placeholder="Senha atual"
           class="px-4 py-2 rounded-xl border border-slate-300 text-sm">
    <input type="password" name="nova_senha" required minlength="6" placeholder="Nova senha (mín. 6)"
           class="px-4 py-2 rounded-xl border border-slate-300 text-sm">
    <button type="submit" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl">
        Alterar Senha
    </button>
</form>
```

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `check_password_hash(usuario_db["senha_hash"], senha_atual)` | Confere se a senha atual digitada bate com o hash do banco. | Impede que alguém que "pegou o computador emprestado" troque a sua senha sem saber a atual. | Qualquer pessoa com a sessão aberta poderia trocar a senha sem conhecê-la. |
| `len(nova_senha) < 6` | Recusa senhas curtas demais. | Senhas muito curtas são fáceis de adivinhar. | Seria aceita até uma senha de 1 letra. |
| `generate_password_hash(nova_senha)` | Cria o hash da nova senha antes de gravar. | Nunca gravamos senha em texto aberto (Aula 04). | A senha ficaria legível por qualquer pessoa com acesso ao banco. |
| `return redirect(url_for("auth.meu_perfil"))` após o sucesso | Redireciona em vez de renderizar direto. | Evita reenviar a troca de senha se o usuário apertar `F5`. | Ao atualizar a página, o navegador perguntaria se quer reenviar o formulário. |
| `<input type="hidden" name="csrf_token" ...>` | A ficha numerada do formulário. | Sem ela, o `validar_csrf` recusa o envio. | A senha **não consegue** ser alterada: a página só responde com o aviso de formulário inválido. |
</details>

---

## O Que Vem a Seguir?

Nosso sistema já tem autenticação real, sessões seguras, layout responsivo em Tailwind CSS e controle de permissões em dupla camada funcionando!

Na **Aula 06**, vamos construir o **Motor Universal de Paginação Server-Side e Pesquisa Dinâmica (AJAX)**: você aprenderá como paginar qualquer tabela no MySQL (`LIMIT` e `OFFSET`), como criar componentes reutilizáveis com *Macros* no Jinja2 e como funciona o JavaScript que filtra tabelas em tempo real enquanto o usuário digita!

---
<!-- nav -->
| Anterior | Índice | Próxima |
| :--- | :---: | ---: |
| [← Aula 04 — Conexão MySQL e Seed](./aula_04_conexao_mysql_seguranca_seed.md) | [📚 Índice do Curso](./README.md) | [Aula 06 — Motor de Paginação e Busca →](./aula_06_motor_paginacao_pesquisa_dinamica.md) |