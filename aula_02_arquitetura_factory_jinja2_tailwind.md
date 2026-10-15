# Aula 02 — Arquitetura Profissional: Application Factory, Variáveis de Ambiente (`.env`), Jinja2 e Tailwind CSS

Na **Aula 01**, demos um passo fundamental: configuramos nosso ambiente virtual (`venv`), instalamos o Flask e criamos o arquivo `hello.py` com nossas primeiras rotas.

Porém, ao terminar a Aula 01, deixamos uma pergunta no ar:
> *"Em um sistema real com login, banco de dados MySQL, dezenas de rotas e páginas estilizadas, nós vamos colocar tudo dentro de um único arquivo `hello.py` e escrever HTML dentro de strings do Python?"*

Se tentássemos fazer o sistema **SalaFácil** inteiro dentro de um único arquivo `.py`, ele rapidamente passaria de **3.000 linhas**. Encontrar um erro, alterar uma cor na tela ou trabalhar em equipe seria um pesadelo.

Nesta **Aula 02**, vamos transformar nosso experimento inicial em uma **arquitetura de software profissional**. Você vai aprender:
1. Como organizar pastas e pacotes Python em um projeto web real.
2. Como proteger senhas e configurações sensíveis usando variáveis de ambiente (`.env` e `config.py`).
3. O que é e como funciona o padrão **Application Factory** (`create_app`).
4. Como separar o código Python do visual HTML usando o motor de templates **Jinja2** e estilizar páginas modernas sem sair do HTML com **Tailwind CSS**.

---

## 1. De um Arquivo Único para uma Arquitetura Modular

Para que o nosso sistema cresça de forma limpa e organizada até a Aula 10, vamos dividir as responsabilidades em pastas bem definidas (o princípio de **Separação de Responsabilidades**):

* **Configurações e Segredos (`.env` e `app/config.py`):** Guardam senhas do banco de dados e chaves secretas fora do código principal.
* **Coração da Aplicação (`app/__init__.py`):** Cria e configura o servidor Flask.
* **Banco de Dados (`app/database.py` e `sql/`):** Cuidam exclusivamente da comunicação com o MySQL (veremos nas Aulas 03 e 04).
* **Utilitários (`app/utils/`):** Ferramentas reutilizáveis de segurança e paginação (veremos nas Aulas 05 e 06).
* **Módulos de Rotas (`app/blueprints/`):** Em vez de colocar todas as rotas juntas, teremos um arquivo separado para Login (`auth.py`), um para Salas (`salas.py`), um para Usuários (`usuarios.py`), um para Reservas (`reservas.py`) e outro para Relatórios (`relatorios.py`).
* **Páginas Visuais (`app/templates/`):** Onde ficam todos os arquivos `.html` processados pelo **Jinja2**.
* **Arquivos Estáticos (`app/static/`):** Onde ficam arquivos JavaScript (`.js`), imagens ou folhas de estilo que o navegador baixa diretamente.

---

## 2. Criando a Estrutura de Pastas e Arquivos do Projeto

Vamos preparar a árvore de diretórios do **SalaFácil** dentro da nossa pasta `sistema_reservas_salas/` (aquela mesma onde já estão a pasta `venv/`, o `requirements.txt` e o `hello.py` da Aula 01).

Veja o mapa completo de onde cada peça do nosso quebra-cabeça vai morar ao longo do curso:

```text
sistema_reservas_salas/
├── venv/                          # (Aula 01) Ambiente virtual isolado
├── hello.py                       # (Aula 01) Nosso primeiro teste (pode manter como consulta)
├── requirements.txt               # (Aula 01) Lista de bibliotecas instaladas
├── .env                           # (Aula 02) Variáveis secretas do ambiente local
├── .gitignore                     # (Aula 02) Lista do que o Git NUNCA deve publicar (.env, venv...)
├── run.py                         # (Aula 02) Arquivo que liga o servidor profissional
├── seed_db.py                     # (Aula 04) Script que popula o banco MySQL automaticamente
├── sql/
│   └── schema.sql                 # (Aula 03) Script SQL com as 5 tabelas do sistema
├── tests/
│   └── test_utilitarios.py        # (Aula 10) Testes automáticos das funções de segurança e validação
└── app/                           # Pacote principal da nossa aplicação
    ├── __init__.py                # (Aula 02) Application Factory (função create_app)
    ├── config.py                  # (Aula 02) Classe Config que lê o arquivo .env
    ├── database.py                # (Aula 04) Pool de conexões MySQL e transações seguras
    ├── utils/
    │   ├── __init__.py
    │   ├── security.py            # (Aula 05) Login, permissões, proteção CSRF e limite de tentativas
    │   ├── validacao.py           # (Aula 07) Funções que conferem os dados recebidos dos formulários
    │   └── pagination.py          # (Aula 06) Motor universal de paginação SQL
    ├── blueprints/
    │   ├── __init__.py
    │   ├── auth.py                # (Aula 05) Rotas de Login, Logout e Meu Perfil
    │   ├── salas.py               # (Aula 07) Rotas do Catálogo de Salas
    │   ├── usuarios.py            # (Aula 08) Rotas de Usuários e Matriz de Permissões
    │   ├── reservas.py            # (Aula 09) Rotas de Reservas e Anti-Conflito
    │   └── relatorios.py          # (Aula 10) Rotas de Relatórios e Exportação CSV
    ├── static/
    │   └── js/
    │       └── tabela_dinamica.js # (Aula 06) Busca dinâmica AJAX com Debounce
    └── templates/
        ├── boas_vindas.html       # (Aula 02) Nossa primeira tela com Tailwind CSS
        ├── base.html              # (Aula 05) Layout principal com menu lateral (Sidebar)
        ├── base_parcial.html      # (Aula 06) Layout "só o recheio", usado pelas buscas dinâmicas
        ├── erro.html              # (Aula 05) Tela amigável para erros 404 e 500
        ├── components/
        │   └── paginacao.html     # (Aula 06) Componente visual de botões de página
        ├── auth/
        │   ├── login.html         # (Aula 05) Tela de Login
        │   ├── perfil.html        # (Aula 05) Tela de Meu Perfil e Permissões
        │   └── 403.html           # (Aula 05) Tela de Acesso Negado
        ├── salas/
        │   ├── index.html         # (Aula 07) Listagem de Salas
        │   └── form.html          # (Aula 07) Cadastro e Edição de Sala
        ├── usuarios/
        │   ├── index.html         # (Aula 08) Listagem de Usuários
        │   ├── form.html          # (Aula 08) Cadastro de Novo Usuário
        │   └── permissoes.html    # (Aula 08) Matriz de Permissões Personalizadas
        ├── reservas/
        │   ├── index.html         # (Aula 09) Agenda Geral de Reservas
        │   └── form.html          # (Aula 09) Solicitação de Reserva
        └── relatorios/
            └── painel.html        # (Aula 10) Painel de KPIs e Relatórios
```

### Passo 2.1 — Criando todas as pastas pelo Terminal

Com o terminal aberto na pasta `sistema_reservas_salas/`, escolha o comando correspondente ao seu sistema operacional para criar todas as pastas de uma só vez:

```powershell
# No Windows (PowerShell):
mkdir sql, tests, app/utils, app/blueprints, app/static/js, app/templates/components, app/templates/auth, app/templates/usuarios, app/templates/salas, app/templates/reservas, app/templates/relatorios
```

```bash
# No Linux, macOS ou Git Bash:
mkdir -p sql tests app/utils app/blueprints app/static/js app/templates/components app/templates/auth app/templates/usuarios app/templates/salas app/templates/reservas app/templates/relatorios
```

```cmd
# No Windows (Prompt de Comando / CMD):
mkdir sql tests app\utils app\blueprints app\static\js app\templates\components app\templates\auth app\templates\usuarios app\templates\salas app\templates\reservas app\templates\relatorios
```

> **💡 Curiosidade técnica para usuários de Windows PowerShell:**  
> No Linux, usamos `mkdir -p` e separamos as pastas com espaço. Já no PowerShell do Windows, `mkdir` é um atalho para o comando `New-Item -ItemType Directory`: ele **não** usa `-p` (ele já cria as pastas pai automaticamente) e exige que múltiplos caminhos na mesma linha sejam separados por **vírgula (`,`)**.

---

### Passo 2.2 — Criando os arquivos no projeto

Você pode escolher criar apenas os arquivos desta **Aula 02** agora (Opção A — Recomendado para ir vendo o projeto crescer aula a aula) ou já deixar todos os arquivos vazios criados na árvore (Opção B):

#### Opção A (Recomendada): Criar agora apenas os arquivos da Aula 02

```powershell
# No Windows (PowerShell):
New-Item -ItemType File -Force -Path run.py, .gitignore, app/__init__.py, app/config.py, app/templates/boas_vindas.html
```

```bash
# No Linux, macOS ou Git Bash:
touch run.py .gitignore app/__init__.py app/config.py app/templates/boas_vindas.html
```

```cmd
# No Windows (CMD):
type nul > run.py & type nul > .gitignore & type nul > app\__init__.py & type nul > app\config.py & type nul > app\templates\boas_vindas.html
```

#### Opção B: Criar todos os arquivos vazios do curso de uma só vez

```powershell
# No Windows (PowerShell):
New-Item -ItemType File -Force -Path run.py, seed_db.py, .gitignore, sql/schema.sql, tests/test_utilitarios.py, app/__init__.py, app/config.py, app/database.py, app/utils/__init__.py, app/utils/pagination.py, app/utils/security.py, app/utils/validacao.py, app/blueprints/__init__.py, app/blueprints/auth.py, app/blueprints/usuarios.py, app/blueprints/salas.py, app/blueprints/reservas.py, app/blueprints/relatorios.py, app/static/js/tabela_dinamica.js, app/templates/base.html, app/templates/base_parcial.html, app/templates/erro.html, app/templates/boas_vindas.html, app/templates/components/paginacao.html, app/templates/auth/login.html, app/templates/auth/perfil.html, app/templates/auth/403.html, app/templates/usuarios/index.html, app/templates/usuarios/form.html, app/templates/usuarios/permissoes.html, app/templates/salas/index.html, app/templates/salas/form.html, app/templates/reservas/index.html, app/templates/reservas/form.html, app/templates/relatorios/painel.html
```

```bash
# No Linux, macOS ou Git Bash:
touch run.py seed_db.py .gitignore sql/schema.sql tests/test_utilitarios.py app/__init__.py app/config.py app/database.py app/utils/__init__.py app/utils/pagination.py app/utils/security.py app/utils/validacao.py app/blueprints/__init__.py app/blueprints/auth.py app/blueprints/usuarios.py app/blueprints/salas.py app/blueprints/reservas.py app/blueprints/relatorios.py app/static/js/tabela_dinamica.js app/templates/base.html app/templates/base_parcial.html app/templates/erro.html app/templates/boas_vindas.html app/templates/components/paginacao.html app/templates/auth/login.html app/templates/auth/perfil.html app/templates/auth/403.html app/templates/usuarios/index.html app/templates/usuarios/form.html app/templates/usuarios/permissoes.html app/templates/salas/index.html app/templates/salas/form.html app/templates/reservas/index.html app/templates/reservas/form.html app/templates/relatorios/painel.html
```

---

## 3. Protegendo Credenciais com Variáveis de Ambiente (`.env` e `app/config.py`)

### Por que nunca colocar senhas direto no código Python?
Imagine que no computador do laboratório da faculdade a senha do seu MySQL seja `1234`, mas no computador da sua casa a senha seja `root999`, e no servidor da empresa seja `Xy9#mP2$qL`. Se você escrever a senha direto dentro do código Python:
1. Toda vez que trocar de computador, você terá que caçar e editar o código-fonte.
2. Pior: se você publicar seu código no GitHub, **qualquer pessoa na internet verá a senha do seu banco de dados!**

Para resolver isso, usamos um arquivo chamado **`.env`** (lê-se *dot-env*). Ele fica apenas na sua máquina local e guarda as configurações específicas daquele computador no formato `CHAVE=VALOR`.

### Passo 3.1 — Criando o arquivo `.env`

Na raiz do projeto (`sistema_reservas_salas/.env`), crie um arquivo chamado exatamente **`.env`** (começando com ponto e sem nada antes do ponto) e cole o conteúdo abaixo:

```ini
FLASK_DEBUG=1
SECRET_KEY=chave_super_secreta_desenvolvimento_reservas_2026
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=sua_senha_mysql
DB_NAME=gestao_reservas_salas
```

> **Nota:** Em `DB_PASSWORD`, você já pode colocar a senha do seu servidor MySQL local (ou deixar `DB_PASSWORD=` vazio se o seu MySQL local — como no XAMPP/Laragon padrão — não tiver senha para o usuário `root`).

#### Linha por linha do `.env`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `FLASK_DEBUG=1` | Liga (`1`) ou desliga (`0`) o modo de depuração que vimos na Aula 01 (recarga automática e tela de erro detalhada). | Em vez de escrever `debug=True` dentro do código, deixamos essa decisão no `.env`. No computador do aluno vale `1`; no servidor da empresa o valor será `0`. *(O nome antigo `FLASK_ENV` foi aposentado pelo Flask 2.3 e hoje é ignorado, por isso usamos `FLASK_DEBUG`.)* | Sem a linha, o modo debug fica **desligado**: o servidor não recarrega sozinho e os erros aparecem como uma página cinza genérica. |
| `SECRET_KEY=...` | A "assinatura" usada para proteger o cookie de login. | Sem ela, o Flask não consegue guardar quem está logado (Aula 05). | O sistema se **recusa a iniciar** com uma mensagem clara (veremos o motivo logo abaixo). |
| `DB_HOST`, `DB_PORT` | Endereço e porta do servidor MySQL. | Dizem ao Python *onde* está o banco. | O Python usa os valores padrão do `config.py`, que servem para a maioria dos computadores locais. |
| `DB_USER`, `DB_PASSWORD` | Usuário e senha de acesso ao MySQL. | Credenciais de entrada, diferentes em cada computador. | O Python tenta entrar com `root` e senha vazia, e o MySQL pode recusar com `Access denied`. |
| `DB_NAME` | Nome do banco de dados do sistema. | Permite trocar o banco sem editar código. | Usa `gestao_reservas_salas`. |

---

### Passo 3.2 — Criando o `.gitignore` (a lista do que nunca deve ser publicado)

#### Contextualização: o que é o Git e por que o `.env` precisa de proteção?

O **Git** é um "histórico de versões" do seu projeto, e o **GitHub** é o site onde as pessoas guardam esse histórico na internet. Quando você publica o projeto, o Git envia **todos** os arquivos da pasta, a menos que você diga o contrário.

> **Analogia da mudança de casa:** imagine que você vai se mudar e pede ao caminhão que leve "tudo que estiver dentro de casa". Se não separar nada, seguem juntos o seu cofre, o seu diário e o lixo da cozinha. O **`.gitignore`** é a **lista de coisas que ficam para trás** na hora da mudança.

No nosso projeto, três coisas **não podem** viajar para o GitHub: o `.env` (contém a senha do banco e a `SECRET_KEY`), a pasta `venv/` (pesada e específica do seu computador) e as pastas `__pycache__/` (arquivos temporários que o Python gera sozinho).

Abra o arquivo **`.gitignore`** (na raiz, ao lado do `run.py`) e digite:

```text
# Segredos do ambiente local: NUNCA publicar
.env

# Ambiente virtual do Python: cada pessoa cria o seu
venv/

# Arquivos temporários gerados pelo Python
__pycache__/
*.pyc
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `# Segredos do ambiente local...` | Comentário: no `.gitignore`, linhas iniciadas por `#` são só anotações. | Explica para a próxima pessoa por que a regra existe. | Nada muda no funcionamento; só perde a explicação. |
| `.env` | Regra que manda o Git ignorar o arquivo chamado exatamente `.env`. | Impede que a senha do MySQL e a `SECRET_KEY` sejam publicadas. | O `.env` vai para o GitHub e **qualquer pessoa** passa a ver suas credenciais. Se isso acontecer, é preciso trocar a senha e a chave imediatamente, pois o histórico do Git guarda tudo. |
| `venv/` | Ignora a pasta inteira do ambiente virtual. | Ela tem milhares de arquivos que cada computador recria com `pip install -r requirements.txt`. | O repositório fica enorme e quebra em outros sistemas operacionais. |
| `__pycache__/` e `*.pyc` | Ignora as pastas e os arquivos de cache do Python (`*` significa "qualquer nome"). | São gerados automaticamente a cada execução e não fazem parte do seu código. | Aparecem dezenas de arquivos inúteis em cada atualização que você enviar. |

> 💡 O que o `.gitignore` não faz: ele só vale para arquivos que **ainda não foram** enviados ao Git. Se você já publicou o `.env` antes de criar essa regra, apagar depois não basta: troque as senhas.

---

### Passo 3.3 — Criando a Classe de Configuração (`app/config.py`)

O Python sozinho não lê o arquivo `.env` automaticamente. É aqui que entra a biblioteca `python-dotenv` que instalamos na Aula 01!

Abra o arquivo **`app/config.py`** e digite o código abaixo:

```python
# app/config.py
import os
from dotenv import load_dotenv

# 1. Lê o arquivo .env da raiz do projeto e carrega seus valores na memória do sistema
load_dotenv()


# 2. Centraliza todas as configurações da aplicação em uma classe organizada
class Config:
    # Sem valor padrão de propósito: se esquecermos a chave, o sistema NÃO inicia (veja create_app)
    SECRET_KEY = os.getenv("SECRET_KEY", "")
    # Modo de depuração controlado pelo .env ("1" liga, qualquer outra coisa desliga)
    DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"
    DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER", "root")
    DB_PASSWORD = os.getenv("DB_PASSWORD", "")
    DB_NAME = os.getenv("DB_NAME", "gestao_reservas_salas")
    ITEMS_PER_PAGE = 8
```

### Dissecando o `app/config.py` linha por linha:
* **`load_dotenv()`**: Procura o arquivo `.env` na pasta do projeto e carrega todas as linhas dele como variáveis de ambiente do sistema operacional.
* **`os.getenv("NOME_DA_VARIAVEL", "valor_padrao")`**: Busca o valor da variável carregada do `.env`. E se o aluno esquecer de criar o arquivo `.env`? O segundo argumento (`"valor_padrao"`) entra em ação como uma rede de segurança para o programa não quebrar! *(Para a `SECRET_KEY` a rede de segurança é um texto vazio de propósito, como você verá abaixo.)*
* **`SECRET_KEY` (O que é isso?)**: O Flask usa a `SECRET_KEY` como uma "assinatura digital criptográfica". Quando um usuário faz login no sistema (Aula 05) ou quando exibimos mensagens de alerta na tela, o Flask assina esses dados com a `SECRET_KEY` para impedir que qualquer pessoa mal-intencionada falsifique a sessão de login no navegador.
* **Por que o valor padrão da `SECRET_KEY` é vazio (`""`) e não algo como `"chave-padrao"`?**  
  Imagine uma fechadura de fábrica com a **mesma chave** em todas as portas do bairro. Se o sistema aceitasse uma chave padrão conhecida por todos (e ela estaria escrita neste curso!), um invasor poderia **fabricar cookies de login falsos** e entrar como administrador. Com o padrão vazio, esquecer a chave faz o sistema parar com um aviso claro, em vez de ficar silenciosamente inseguro.
* **`DEBUG = os.getenv("FLASK_DEBUG", "0") == "1"`**: lê o texto `FLASK_DEBUG` do `.env` e compara com `"1"`. O resultado é `True` ou `False`. Se a variável não existir, o padrão `"0"` mantém o modo debug **desligado**: o lado seguro é sempre o padrão.
* **Por que `int(os.getenv("DB_PORT", 3306))` tem um `int(...)` em volta?**  
  Tudo o que vem de um arquivo de texto como o `.env` é lido pelo Python como texto (*string*, ex.: `"3306"`). Como o conector do MySQL exige que a porta seja um **número inteiro**, fazemos a conversão explícita com `int(...)`.
* **`ITEMS_PER_PAGE = 8`**: Define o número padrão de linhas que exibiremos por página nas tabelas do sistema a partir da Aula 06.

---

## 4. O Padrão Application Factory (`app/__init__.py`)

### O que significa um arquivo chamado `__init__.py` no Python?
Em Python, quando você coloca um arquivo chamado `__init__.py` dentro de uma pasta (como a pasta `app/`), o Python passa a tratar aquela pasta inteira como um **Pacote Importável**! Isso significa que, de fora da pasta, podemos escrever simplesmente `from app import create_app`, e o Python automaticamente procurará a função `create_app` dentro de `app/__init__.py`.

### O que é uma "Application Factory" (Fábrica de Aplicação)?
No `hello.py` da Aula 01, nós criamos a variável `app = Flask(__name__)` solta no topo do arquivo (no escopo global). Em projetos grandes com vários arquivos importando uns aos outros, criar o `app` solto causa um problema clássico chamado **Importação Circular** (*Circular Import*: o arquivo A tenta importar o arquivo B, que tenta importar o arquivo A antes de ele terminar de carregar).

Para evitar isso, usamos o padrão oficial recomendado pela documentação do Flask: a **Application Factory**. Em vez de criar o objeto `app` solto, nós criamos uma **função construtora chamada `create_app()`**. Ela monta o Flask, carrega as configurações, registra as rotas e devolve o `app` prontinho no `return app`!

Abra o arquivo **`app/__init__.py`** e digite o código abaixo:

```python
# app/__init__.py
from flask import Flask, render_template
from app.config import Config


def create_app():
    # 1. Instancia o Flask dentro da função fábrica
    app = Flask(__name__)

    # 2. Carrega todas as variáveis da classe Config (SECRET_KEY, DB_HOST, etc.)
    app.config.from_object(Config)

    # 2.1 Trava de segurança: sem SECRET_KEY o sistema não deve nem iniciar
    if not app.config["SECRET_KEY"]:
        raise RuntimeError("SECRET_KEY não definida. Crie o arquivo .env conforme a Aula 02.")

    # 3. Rota inicial provisória de boas-vindas usando Template HTML + Jinja2
    @app.route("/")
    def index():
        resumo_inicial = [
            {"modulo": "Banco MySQL & Seed", "status": "Pronto para Aulas 03 e 04", "icone": "🗄️"},
            {"modulo": "Login & Permissões", "status": "Pronto para Aula 05", "icone": "🔐"},
            {"modulo": "Catálogo de Salas", "status": "Pronto para Aulas 06 e 07", "icone": "🏢"},
            {"modulo": "Usuários & Reservas", "status": "Pronto para Aulas 08 a 10", "icone": "📅"},
        ]
        return render_template("boas_vindas.html", modulos=resumo_inicial)

    # 4. Devolve a aplicação configurada e pronta para rodar
    return app
```

### Entendendo as novidades do `app/__init__.py`:
1. **`app.config.from_object(Config)`**: Pega todos os atributos em letras maiúsculas da nossa classe `Config` (do arquivo `app/config.py`) e guarda dentro do dicionário interno de configurações do Flask (`app.config`).
2. **A trava de segurança da `SECRET_KEY` (passo 2.1 do código):**

   | Linha | O que é | Por que está ali | O que acontece se tirar |
   | :--- | :--- | :--- | :--- |
   | `if not app.config["SECRET_KEY"]:` | Pergunta: "a chave está vazia ou ausente?". Em Python, texto vazio conta como "falso", e o `not` inverte a resposta. | É o "porteiro" que confere, antes de abrir o sistema, se a chave existe. | O sistema inicia sem chave e só quebra mais tarde, na hora do login, com uma mensagem confusa. |
   | `raise RuntimeError("...")` | Interrompe o programa de propósito e mostra a nossa mensagem. | Falhar cedo e de forma clara é melhor do que rodar inseguro. | Sem o `raise`, o `if` não teria efeito nenhum. |
3. **`render_template("boas_vindas.html", modulos=resumo_inicial)`**:  
   Aqui está o grande salto de qualidade em relação à Aula 01! Em vez de escrever HTML dentro do Python, chamamos a função `render_template` do Flask:
   * O primeiro argumento (`"boas_vindas.html"`) diz ao Flask: *"Vá até a subpasta `app/templates/`, abra o arquivo `boas_vindas.html` e processe-o"*.
   * O segundo argumento (`modulos=resumo_inicial`) envia a nossa lista de dicionários do Python (`resumo_inicial`) para dentro do arquivo HTML com o nome de **`modulos`**!

---

## 5. Templates Dinâmicos com Jinja2 e Estilização com Tailwind CSS

Antes de criarmos o arquivo `app/templates/boas_vindas.html`, vamos entender rapidamente as duas ferramentas que trabalham juntas dentro dele:

### 5.1 — Como o Jinja2 funciona dentro do HTML?
O **Jinja2** lê o seu arquivo HTML antes de enviá-lo para o navegador e procura dois tipos especiais de marcação:

* **`{{ variavel }}` (Duplo Bigode — Exibição de Valor):**  
  Sempre que você abre e fecha duas chaves `{{ ... }}`, o Jinja2 imprime naquele ponto do HTML o valor de uma variável vinda do Python. Por exemplo: `{{ item.modulo }}` será substituído por `Catálogo de Salas`.
* **`{% comando %}` (Chave e Porcentagem — Lógica de Programação):**  
  Usado para estruturas de repetição (`{% for item in modulos %}`) e decisões condicionais (`{% if ... %}`). Diferente do Python (que usa indentação para saber onde um `for` termina), no HTML nós precisamos avisar explicitamente onde o bloco acaba usando **`{% endfor %}`** ou **`{% endif %}`**.

### 5.2 — Como o Tailwind CSS funciona?
Normalmente, para deixar um site bonito com CSS tradicional, você precisa criar um arquivo `.css` separado, inventar nomes de classes (`.cartao-topo`, `.cabecalho-azul`) e escrever dezenas de regras CSS.

O **Tailwind CSS** usa uma abordagem chamada **Utility-First (Classes Utilitárias)**. Você estiliza os elementos aplicando pequenas classes prontas diretamente no atributo `class="..."` do HTML! Veja como é intuitivo ler:

| Classe do Tailwind CSS | O que ela faz no visual da página |
| :--- | :--- |
| `bg-indigo-700` / `bg-white` | Define a cor de fundo (*Background*) como azul-índigo escuro ou branco. |
| `text-white` / `text-slate-800` | Define a cor do texto como branco ou cinza-ardósia escuro. |
| `px-6 py-4` | Adiciona espaçamento interno (*Padding*) horizontal (`px`) e vertical (`py`). |
| `rounded-xl` / `rounded-2xl` | Arredonda os cantos da caixa ou do botão (*Border Radius*). |
| `shadow-sm` / `shadow-md` | Aplica uma sombra suave de elevação no cartão. |
| `grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6` | Cria uma grade responsiva: **1 coluna** na tela do celular, **2 colunas** em tablets (`md:`) e **4 colunas** lado a lado em monitores grandes (`lg:`), com espaço (`gap-6`) entre os cartões! |

Para não exigir a instalação do Node.js no laboratório, carregamos o Tailwind através de uma única linha `<script src="https://cdn.tailwindcss.com"></script>` no `<head>` do HTML (o chamado **Tailwind Play CDN**).

#### Linha por linha do `<script src="https://cdn.tailwindcss.com"></script>`

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `<script ...></script>` | Tag HTML que pede ao navegador para baixar e executar um programa em JavaScript. | O Tailwind é, na verdade, um programa que lê as classes da página (`bg-indigo-700`, `px-6`...) e gera o CSS correspondente na hora. | Nenhuma classe do Tailwind funciona e a página aparece só com texto preto sobre fundo branco. |
| `src="https://cdn.tailwindcss.com"` | O endereço de onde o navegador baixa o programa. *CDN* é uma rede de servidores espalhados pelo mundo que entrega arquivos rápido. | Evita instalar qualquer coisa no computador. | Sem internet, o download falha e a página fica sem estilo (veja o Guia de Sobrevivência). |

> ⚠️ **Atenção ao copiar!** O endereço deve ficar **limpo**, exatamente como acima. Se o seu editor ou um site de cópia transformar a linha em algo como `src="[https://cdn...](https://cdn...)"` (colchetes e parênteses vindos do formato Markdown), o navegador não encontra o arquivo e o Tailwind **não carrega**.

> 🏭 **E em produção?** O Play CDN é uma ferramenta de **aprendizado**: o navegador de cada visitante precisa baixar cerca de 300 KB de JavaScript e "montar" o CSS a cada abertura de página, o que é lento. Em um sistema publicado de verdade, usa-se a *Tailwind CLI* (que exige Node.js) para gerar **um único arquivo `.css` pronto e pequeno**. Para o laboratório, o CDN é perfeito; só não o leve para a produção.

---

### Passo 5.3 — Criando o Template `app/templates/boas_vindas.html`

Abra o arquivo **`app/templates/boas_vindas.html`** e insira o código abaixo:

```html
<!-- app/templates/boas_vindas.html -->
<!DOCTYPE html>
<html lang="pt-BR">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SalaFácil — Gestão de Reservas de Salas</title>
    <!-- Carrega o motor do Tailwind CSS via Play CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-slate-50 text-slate-800 min-h-screen flex flex-col justify-between">

    <!-- Cabeçalho Superior (Header) -->
    <header class="bg-indigo-700 text-white shadow-md">
        <div class="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
            <div class="flex items-center gap-3">
                <span class="bg-white text-indigo-700 font-bold px-3 py-1 rounded-lg text-lg">SF</span>
                <h1 class="text-xl font-bold tracking-tight">SalaFácil — Flask + MySQL + Tailwind CSS</h1>
            </div>
            <span class="text-xs bg-indigo-900 px-3 py-1 rounded-full font-medium">Aula 02 Concluída</span>
        </div>
    </header>

    <!-- Conteúdo Principal (Main) -->
    <main class="max-w-6xl mx-auto px-6 py-10 flex-1 w-full">
        <!-- Banner de Destaque -->
        <div class="bg-white rounded-2xl shadow-sm border border-slate-200 p-8 mb-8">
            <h2 class="text-2xl font-bold text-slate-900 mb-2">Ambiente Flask Configurado com Sucesso!</h2>
            <p class="text-slate-600">
                Sua aplicação já utiliza o padrão <strong>Application Factory</strong>, variáveis de ambiente com <code>.env</code> e estilização responsiva com <strong>Tailwind CSS</strong>.
            </p>
        </div>

        <!-- Grade Responsiva de Cards gerados dinamicamente pelo Jinja2 -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            {% for item in modulos %}
            <div class="bg-white p-6 rounded-xl border border-slate-200 shadow-sm hover:shadow-md transition">
                <div class="text-3xl mb-3">{{ item.icone }}</div>
                <h3 class="font-semibold text-lg text-slate-900">{{ item.modulo }}</h3>
                <p class="text-sm text-indigo-600 mt-1 font-medium">{{ item.status }}</p>
            </div>
            {% endfor %}
        </div>
    </main>

    <!-- Rodapé (Footer) -->
    <footer class="bg-white border-t border-slate-200 py-4 text-center text-sm text-slate-500">
        Curso Prático de Flask com MySQL — Sistema de Gestão de Reservas de Salas
    </footer>

</body>
</html>
```

#### Observe a mágica do laço `{% for item in modulos %}` no HTML acima:
No Python (`app/__init__.py`), nossa lista `resumo_inicial` tinha **4 dicionários**. No HTML, nós escrevemos o código visual do cartão (`<div class="bg-white p-6...">`) **apenas uma vez** dentro do bloco `{% for item in modulos %} ... {% endfor %}`. O Jinja2 repete esse bloco HTML 4 vezes automaticamente, preenchendo o ícone (`{{ item.icone }}`), o nome (`{{ item.modulo }}`) e o status (`{{ item.status }}`) de cada cartão!

---

## 6. O Ponto de Entrada da Aplicação (`run.py`)

Agora que nosso servidor é construído dentro da função `create_app()` (em `app/__init__.py`), precisamos de um arquivo simples e limpo na raiz do projeto apenas para chamar essa fábrica e dar a partida no servidor.

Abra o arquivo **`run.py`** (na raiz `sistema_reservas_salas/run.py`) e digite:

```python
# run.py
from app import create_app

# Chama a nossa Application Factory para montar o servidor Flask
app = create_app()

if __name__ == "__main__":
    # O modo debug NÃO é escrito aqui: ele vem do .env (FLASK_DEBUG) via app.config["DEBUG"]
    app.run(host="127.0.0.1", port=5000)
```

#### Linha por linha do `run.py`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `from app import create_app` | Importa a "fábrica" que montamos em `app/__init__.py`. | O `run.py` não sabe construir o servidor sozinho; ele pede à fábrica. | `NameError: name 'create_app' is not defined`. |
| `app = create_app()` | Executa a fábrica e guarda o servidor pronto na variável `app`. | É aqui que o `.env` é lido, a trava da `SECRET_KEY` é conferida e as rotas são registradas. | Não existe servidor para ligar. |
| `if __name__ == "__main__":` | Só executa o bloco abaixo quando rodamos `python run.py` diretamente (e não quando outro arquivo importa o `run.py`). | Evita ligar o servidor por acidente em outras situações, como nos testes da Aula 10. | O servidor sobe toda vez que alguém importar o arquivo. |
| `app.run(host="127.0.0.1", port=5000)` | Liga o servidor de desenvolvimento só para o seu computador, na porta 5000. | É o botão "ligar". Sem `debug=...`, o Flask usa o valor que veio do `.env`. | O programa termina imediatamente, sem atender ninguém. |

> **Por que tiramos o `debug=True` daqui?** Quando o valor fica escrito no código, é fácil esquecer de desligá-lo ao publicar o sistema (veja o aviso da Aula 01). Agora, para ligar ou desligar o modo debug basta mudar uma linha do `.env`, sem tocar no código.

### Executando o Projeto Profissional!

1. Se o `hello.py` da Aula 01 ainda estiver rodando no seu terminal, pare-o pressionando **`CTRL + C`**.
2. Com o `(venv)` ativo na pasta `sistema_reservas_salas/`, execute agora o nosso novo ponto de entrada:

```bash
python run.py
```

3. Abra o navegador em **`http://127.0.0.1:5000`**.
4. Você verá o painel moderno do **SalaFácil** com barra superior azul-índigo, tipografia limpa e os 4 cartões responsivos! Experimente diminuir a largura da janela do navegador para ver os 4 cartões se reorganizarem automaticamente para 2 colunas e depois 1 coluna.

---

## 7. Guia de Sobrevivência no Laboratório (Erros Comuns na Aula 02)

| Sintoma / Mensagem de Erro | Causa Mais Provável | Como Resolver Rapidamente |
| :--- | :--- | :--- |
| `jinja2.exceptions.TemplateNotFound: boas_vindas.html` | O arquivo `boas_vindas.html` foi criado fora da pasta `app/templates/`, ou a pasta foi nomeada no singular (`template/` em vez de `templates/`). | Confira se o caminho exato do arquivo é `sistema_reservas_salas/app/templates/boas_vindas.html`. O Flask exige o nome `templates` no plural! |
| `ModuleNotFoundError: No module named 'app'` | Você tentou rodar `python run.py` estando fora da pasta `sistema_reservas_salas/` ou criou o arquivo `run.py` dentro da subpasta `app/`. | O arquivo `run.py` deve ficar na raiz (`sistema_reservas_salas/run.py`) e o terminal também deve estar aberto na pasta `sistema_reservas_salas/`. |
| A página carregou apenas texto preto no fundo branco, sem cores nem formato de cartões. | O computador está sem acesso à internet no momento (impedindo o download do script `https://cdn.tailwindcss.com`) ou houve erro de digitação na tag `<script>` do `<head>`. | Verifique a conexão de rede do laboratório e confira a linha `<script src="https://cdn.tailwindcss.com"></script>` no topo do `boas_vindas.html`. |
| `RuntimeError: SECRET_KEY não definida. Crie o arquivo .env conforme a Aula 02.` ao rodar `python run.py`. | A trava de segurança funcionou: o `.env` não existe, está em outra pasta ou a linha `SECRET_KEY=` está vazia. | Confira se o arquivo `.env` está na raiz (ao lado do `run.py`) e se a linha `SECRET_KEY=` tem um texto depois do sinal de igual. |
| Mudei o `FLASK_DEBUG` no `.env`, mas nada mudou. | O `.env` só é lido quando o programa **inicia**. | Pare o servidor (`CTRL + C`) e rode `python run.py` de novo. |
| Minhas variáveis do `.env` não estão sendo lidas (sempre usa o valor padrão do `config.py`). | No Windows, ao criar o arquivo pelo Bloco de Notas, ele pode ter sido salvo ocultamente como `.env.txt`. | Crie o arquivo `.env` diretamente pela barra lateral do VS Code (clicando em *New File* na raiz do projeto) para garantir que ele se chame exatamente `.env`. |

---

## 8. Exercícios Práticos de Fixação

Vamos testar se você compreendeu o fluxo completo entre **`.env` $\rightarrow$ `app/config.py` $\rightarrow$ `app/__init__.py` $\rightarrow$ Template Jinja2**:

1. **Desafio 1 (Nova Variável de Ambiente):** Abra o seu arquivo `.env` e adicione no final uma nova linha:
   ```ini
   NOME_INSTITUICAO=Centro Universitário SalaFácil
   ```
2. **Desafio 2 (Expondo na Classe `Config`):** Abra o arquivo `app/config.py` e adicione dentro da classe `Config` o atributo `NOME_INSTITUICAO` lendo essa variável do `.env` com `os.getenv(...)`.
3. **Desafio 3 (Criando Rota `/status` em JSON):** No arquivo `app/__init__.py` (dentro da função `create_app()`), crie uma nova rota `@app.route("/status")` que retorne um dicionário Python contendo o nome da instituição lido de `app.config["NOME_INSTITUICAO"]` e o banco configurado em `app.config["DB_NAME"]`.
4. **Desafio 4 (Exibindo no Rodapé do HTML):** O Flask disponibiliza automaticamente o objeto `config` dentro de qualquer template Jinja2! Abra o `app/templates/boas_vindas.html` e, no `<footer>`, exiba dinamicamente `{{ config.NOME_INSTITUICAO }}`.

<details>
<summary><strong>💡 Clique aqui para ver o Gabarito Comentado dos Exercícios</strong></summary>

**1. No arquivo `.env`:**
```ini
NOME_INSTITUICAO=Centro Universitário SalaFácil
```

**2. No arquivo `app/config.py` (dentro da `class Config:`):**
```python
    NOME_INSTITUICAO = os.getenv("NOME_INSTITUICAO", "Instituição Padrão")
```

**3. No arquivo `app/__init__.py` (dentro de `def create_app():`, logo abaixo da rota `index`):**
```python
    @app.route("/status")
    def status():
        return {
            "instituicao": app.config["NOME_INSTITUICAO"],
            "banco_de_dados": app.config["DB_NAME"],
            "itens_por_pagina": app.config["ITEMS_PER_PAGE"],
            "status": "online",
        }
```
*(Nota: quando você altera o arquivo `.env`, reinicie o `python run.py` com `CTRL+C` e `python run.py` para que o `load_dotenv()` recarregue o arquivo `.env` atualizado!).*

> ⚠️ **Rota `/status` é só de aprendizado.** Ela mostra o nome do banco de dados para **qualquer visitante**, sem exigir login. Informação de infraestrutura é pista valiosa para quem quer atacar o sistema. Quando chegarmos à Aula 05 (login), apague esta rota ou proteja-a com `@login_obrigatorio`.

**4. No arquivo `app/templates/boas_vindas.html` (no `<footer>`):**
```html
    <footer class="bg-white border-t border-slate-200 py-4 text-center text-sm text-slate-500">
        {{ config.NOME_INSTITUICAO }} — Curso Prático de Flask com MySQL
    </footer>
```
</details>

---

## O Que Vem a Seguir?

Nossa fundação arquitetural está pronta, limpa e estilizada! Na **Aula 03**, vamos mergulhar no banco de dados **MySQL**: entenderemos por que sistemas corporativos usam **Permissões Personalizadas (Granulares)** em vez de apenas cargos fixos e construiremos nosso esquema relacional completo (`sql/schema.sql`) com 5 tabelas interligadas!

---
<!-- nav -->
| Anterior | Índice | Próxima |
| :--- | :---: | ---: |
| [← Aula 01 — Fundamentos e Hello World](./aula_01_introducao_ambiente_hello_world.md) | [📚 Índice do Curso](./README.md) | [Aula 03 — Modelagem do Banco MySQL →](./aula_03_modelagem_banco_mysql_permissoes.md) |