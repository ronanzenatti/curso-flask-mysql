# Aula 01 — Fundamentos Web, Ambiente Virtual (`venv`) e Primeiras Rotas no Flask

Bem-vindo(a) à primeira aula do nosso curso prático! Ao longo de **10 encontros**, vamos construir juntos, passo a passo e do absoluto zero, o **SalaFácil**: um sistema completo de **Gestão de Reservas de Salas e Laboratórios** usando **Python (Flask)**, banco de dados **MySQL** e interface moderna com **Tailwind CSS**.

Se você conhece o básico de lógica de programação em Python (variáveis, funções `def`, listas e dicionários), mas **nunca criou um sistema para a Web**, fique tranquilo(a): esta aula foi desenhada exatamente para você. Hoje nós não vamos correr. Nosso objetivo é entender **como um programa em Python conversa com o navegador**, preparar seu computador como um desenvolvedor profissional e colocar seu primeiro servidor Flask no ar entendendo cada linha de código digitada.

---

## 1. Como a Web Funciona? (Da Tela do Navegador até o seu Código Python)

Quando você escreve um script Python comum no terminal (usando `input()` e `print()`), o programa roda na sua máquina, lê o teclado e mostra um texto na tela preta. Na Web, a dinâmica é diferente porque envolve **dois lados separados**:

1. **O Cliente (Frontend / Navegador):** É o Google Chrome, Edge ou Firefox aberto no computador ou celular do usuário. O navegador só entende três coisas: **HTML** (estrutura da página), **CSS** (cores e visual) e **JavaScript** (interatividade na tela). O navegador **não sabe executar código Python**.
2. **O Servidor (Backend / Nossa Aplicação Flask):** É um programa em Python que fica rodando continuamente, esperando alguém pedir alguma informação para processar regras de negócio, consultar o banco de dados MySQL e devolver uma resposta.

### A Analogia do Restaurante (O Ciclo Requisição $\rightarrow$ Resposta)

Para entender como o navegador e o Flask conversam, imagine um restaurante:

```text
[ Navegador (Cliente) ]  --- 1. Pedido HTTP (GET /salas) --->  [ Servidor Flask (Cozinha) ]
[ Navegador (Cliente) ]  <-- 2. Resposta HTTP (HTML/JSON) ---  [ Servidor Flask (Cozinha) ]
```

1. **O Cliente faz um pedido (*Request*):** Quando você digita `http://127.0.0.1:5000/salas` no navegador e aperta `Enter`, o navegador envia uma mensagem através da rede usando o protocolo **HTTP**.
2. **A Rota recebe o pedido:** O Flask olha para o endereço pedido (`/salas`) e procura qual função Python do seu código é responsável por atender aquele endereço. Chamamos esse endereço de **Rota**.
3. **A Função Python trabalha:** Sua função Python executa a lógica necessária (por exemplo, busca as salas disponíveis no banco de dados).
4. **O Servidor entrega o prato (*Response*):** A função Python retorna uma resposta (que pode ser uma página **HTML** pronta para exibir na tela ou dados em formato **JSON**). O navegador recebe essa resposta e desenha a tela para o usuário.

### Os dois tipos de pedidos HTTP que mais usaremos no curso:
* **`GET` (Consultar / Buscar):** Usado quando o navegador quer **ler** uma página ou fazer uma pesquisa (ex.: abrir a página inicial, listar salas ou buscar por `?q=Projetor`).
* **`POST` (Enviar / Gravar):** Usado quando o usuário preenche um formulário na tela e clica em "Salvar" ou "Entrar" (ex.: enviar e-mail e senha no login, cadastrar uma nova reserva no banco de dados).

---

## 2. O que é o Flask (e o que significam WSGI, Werkzeug e Jinja2)?

O **Flask** é um *microframework* web para Python criado por Armin Ronacher.

> **Por que "microframework"?**  
> A palavra "micro" **não** significa que o Flask serve apenas para projetos pequenos. Grandes empresas usam Flask em sistemas com milhões de acessos. Ele é chamado de *micro* porque seu núcleo é enxuto: em vez de obrigar você a usar um banco de dados específico ou uma estrutura rígida e pesada logo no primeiro dia, ele entrega o essencial para a Web funcionar e deixa você escolher as melhores ferramentas para o seu projeto (no nosso caso: **MySQL** para o banco de dados e **Tailwind CSS** para o visual).

Quando instalamos o Flask, ele traz consigo dois motores fundamentais que aparecem frequentemente nas mensagens do terminal. Vale a pena conhecer o nome deles sem mistério:

| Nome Técnico | O que ele faz (em português claro) | Onde você vai vê-lo no curso |
| :--- | :--- | :--- |
| **WSGI / Werkzeug** | É o "porteiro" e tradutor HTTP do Flask. Ele recebe os dados brutos da rede enviados pelo navegador, transforma em objetos Python fáceis de ler (`request`), descobre qual rota chamar e empacota a resposta (`response`) com segurança (inclusive criptografando senhas e sessões de login). | Nas mensagens do terminal quando o servidor sobe e quando usarmos `werkzeug.security` para proteger senhas na Aula 04. |
| **Jinja2** | É o "montador de páginas HTML" (*Template Engine*). Ele permite escrever arquivos `.html` normais misturados com variáveis do Python (`{{ usuario.nome }}`), criando páginas dinâmicas. | A partir da **Aula 02**, quando criarmos nossas primeiras telas visuais com Tailwind CSS. |

---

## 3. Pré-requisitos do Ambiente

Antes de colocar a mão no código, verifique se o seu computador possui as três ferramentas base que usaremos durante todo o curso:

1. **Python (versão 3.10 ou superior):**
   * Abra o seu terminal e digite `python --version` (ou `python3 --version` no Linux/macOS).
   * Se aparecer algo como `Python 3.11.x`, `Python 3.12.x` ou superior, está tudo pronto!
   * *Dica para Windows:* Se você ainda vai instalar o Python pelo site oficial (`python.org`), lembre-se de marcar a caixinha **"Add Python to PATH"** na primeira tela do instalador.
2. **Servidor MySQL 8.0+ (Para usar a partir da Aula 03):**
   * Pode ser o MySQL Community Server, XAMPP, Laragon ou WampServer, acompanhado de um programa visual para ver as tabelas (MySQL Workbench, DBeaver ou a extensão MySQL do VS Code).
3. **Visual Studio Code (VS Code):**
   * Nosso editor de código oficial. Recomendamos instalar três extensões gratuitas na aba *Extensions* (`Ctrl+Shift+X`):
     * **Python** (da Microsoft): ajuda a completar o código e detectar erros de digitação.
     * **Jinja** (de *wholroyd*): colore corretamente os comandos do Flask dentro dos arquivos HTML.
     * **Tailwind CSS IntelliSense** (da Tailwind Labs): sugere automaticamente os nomes das classes de estilo do Tailwind.

---

## 4. Criando a Pasta do Projeto e o Ambiente Virtual (`venv`)

### Por que precisamos de um "Ambiente Virtual" (`venv`)?

Imagine que você instale todas as bibliotecas Python diretamente no sistema operacional do seu computador (o chamado "ambiente global"). Hoje você cria um projeto da faculdade que exige o `Flask 2.2`. Daqui a seis meses, você começa outro sistema que exige o `Flask 3.1`. Se você atualizar o Flask no computador, o projeto antigo pode parar de funcionar!

O **Ambiente Virtual (`venv`)** resolve isso criando uma **"bolha isolada"** (uma pastinha exclusiva) dentro do nosso projeto. Tudo o que instalarmos enquanto o `venv` estiver ligado ficará guardado apenas dentro da pasta do **SalaFácil**, sem bagunçar o seu computador e sem interferir em outros trabalhos.

---

### Passo 4.1 — Criar a pasta raiz do projeto

Abra o seu terminal (PowerShell ou CMD no Windows; Bash ou Zsh no Linux/macOS) e execute os dois comandos abaixo, um por vez:

```bash
# 1. Cria a pasta onde todo o nosso sistema viverá durante o curso
mkdir sistema_reservas_salas

# 2. Entra dentro da pasta que acabamos de criar
cd sistema_reservas_salas
```

---

### Passo 4.2 — Criar o ambiente virtual (`venv`)

Agora que você está dentro da pasta `sistema_reservas_salas`, execute o comando abaixo para criar a bolha isolada do Python:

```bash
# No Windows:
python -m venv venv

# No Linux ou macOS:
python3 -m venv venv
```

#### Entendendo o comando `python -m venv venv` (Por que tem dois `venv`?):
* `python`: chama o interpretador do Python.
* `-m venv`: pede ao Python para executar o módulo interno (*module*) criador de ambientes virtuais, que se chama `venv`.
* `venv` (o segundo): é o **nome da pasta** que será criada. Por convenção mundial, quase todo programador Python chama essa pasta de `venv` ou `.venv`.

Ao rodar esse comando, aguarde alguns segundos. Você verá que surgiu uma subpasta `venv/` dentro de `sistema_reservas_salas/`.

> ⚠️ **Regra de Ouro sobre a pasta `venv/`:**  
> Você **nunca** deve criar nem salvar arquivos do seu projeto dentro da pasta `venv/`. Ela pertence exclusivamente ao Python para guardar as bibliotecas instaladas. Nossos arquivos de código ficarão ao lado dela, na pasta `sistema_reservas_salas/`.

---

### Passo 4.3 — Ativar o ambiente virtual

Criar a pasta `venv` não basta; nós precisamos **entrar na bolha** (ativar o ambiente) toda vez que abrirmos o terminal para trabalhar no projeto.

Escolha o comando de acordo com o terminal que você está usando:

```bash
# Opção 1 — Windows usando PowerShell (Terminal padrão do VS Code):
venv\Scripts\Activate.ps1

# Opção 2 — Windows usando Prompt de Comando clássico (CMD):
venv\Scripts\activate.bat

# Opção 3 — Windows usando Git Bash:
source venv/Scripts/activate

# Opção 4 — Linux ou macOS:
source venv/bin/activate
```

#### 🛠️ Deu erro vermelho no Windows PowerShell? Veja como resolver em 10 segundos:
No Windows, o PowerShell vem de fábrica bloqueando a execução de scripts locais por segurança, exibindo um erro como *"A execução de scripts foi desabilitada neste sistema"*. Para liberar scripts criados no seu próprio usuário, rode este comando uma única vez no PowerShell:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Depois disso, rode novamente `venv\Scripts\Activate.ps1`.

#### Como saber se o `venv` está realmente ativo?
Olhe para o começo da linha do seu terminal. Deve aparecer um **`(venv)`** entre parênteses antes do caminho da pasta, exatamente assim:

```text
(venv) PS C:\projetos\sistema_reservas_salas>
```

Enquanto esse `(venv)` estiver visível, qualquer comando `python` ou `pip` que você digitar estará rodando com segurança dentro do nosso ambiente isolado!

---

## 5. Instalando o Flask e Congelando Dependências (`pip`)

Com o **`(venv)` ativo** no terminal, vamos usar o **`pip`** (o gerenciador oficial de pacotes do Python) para atualizar o instalador e baixar as três bibliotecas que usaremos ao longo do curso:

```bash
# 1. Atualiza o próprio instalador pip para a versão mais recente
pip install --upgrade pip

# 2. Instala o Flask, o conector do MySQL e o leitor de variáveis de ambiente
pip install Flask mysql-connector-python python-dotenv
```

### O que acabamos de instalar?

1. **`Flask`**: O framework web principal. Ao instalá-lo, o `pip` baixa automaticamente os ajudantes oficiais do Flask (`Werkzeug`, `Jinja2`, `MarkupSafe`, `itsdangerous`, `click` e `blinker`).
2. **`mysql-connector-python`**: O driver oficial da Oracle/MySQL que permitirá ao nosso código Python conversar com o banco de dados MySQL a partir da Aula 04.
3. **`python-dotenv`**: Uma biblioteca que lê senhas e configurações secretas de um arquivo `.env` (que aprenderemos a usar na Aula 02).

### Criando o arquivo `requirements.txt` (A "Lista de Ingredientes" do Projeto)

Como não enviamos a pasta `venv` (que é pesada) quando compartilhamos um projeto no GitHub ou entregamos um trabalho para o professor, como outra pessoa saberá quais bibliotecas instalar para rodar o seu sistema?

Para isso existe o comando `pip freeze`. Ele lista todos os pacotes instalados no `venv` atual com suas versões exatas. Usando o sinal `>`, salvamos essa lista diretamente em um arquivo de texto chamado `requirements.txt`:

```bash
pip freeze > requirements.txt
```

Se você abrir o arquivo `requirements.txt` no VS Code, verá algo muito parecido com isto:

```text
blinker==1.9.0
click==8.5.0
Flask==3.1.3
itsdangerous==2.2.0
Jinja2==3.1.6
MarkupSafe==3.0.4
mysql-connector-python==26.7.0
python-dotenv==1.2.4
Werkzeug==3.1.9
```

> **Dica profissional:** Quando você baixar este projeto em outro computador no futuro, bastará criar o `venv`, ativá-lo e rodar `pip install -r requirements.txt` para que o Python instale todos os pacotes da lista de uma só vez!

---

## 6. Seu Primeiro Servidor Web no Flask (`hello.py`)

Chegou a hora de escrever código! Vamos criar um arquivo chamado `hello.py` diretamente dentro da pasta `sistema_reservas_salas/` (ao lado da pasta `venv` e do `requirements.txt`).

Sua pasta neste momento terá apenas esta estrutura simples:

```text
sistema_reservas_salas/
├── venv/
├── requirements.txt
└── hello.py
```

Abra o VS Code na pasta `sistema_reservas_salas`, crie o arquivo **`hello.py`** e digite o código abaixo:

```python
# hello.py
from flask import Flask
from markupsafe import escape

# 1. Criamos a instância da nossa aplicação Flask
app = Flask(__name__)


# 2. Rota Principal ("/") -> Retorna HTML simples para o navegador
@app.route("/")
def pagina_inicial():
    return """
    <h1>Olá, Mundo! Nosso servidor Flask está no ar! 🚀</h1>
    <p>Bem-vindo ao primeiro teste do sistema <strong>SalaFácil</strong>.</p>
    <ul>
        <li><a href="/sobre">Ver informações do sistema (Formato JSON)</a></li>
        <li><a href="/saudacao/Visitante">Testar rota dinâmica com parâmetro</a></li>
    </ul>
    """


# 3. Rota "/sobre" -> Retorna um Dicionário Python (O Flask converte para JSON!)
@app.route("/sobre")
def sobre_o_sistema():
    dados_do_projeto = {
        "sistema": "SalaFácil — Gestão de Reservas de Salas",
        "versao": "1.0-aula01",
        "tecnologias": ["Python", "Flask", "MySQL", "Tailwind CSS"],
        "servidor_ativo": True,
    }
    return dados_do_projeto


# 4. Rota Dinâmica com Variável na URL ("/saudacao/<nome>")
@app.route("/saudacao/<nome>")
def saudar_usuario(nome):
    return f"<h2>Olá, {escape(nome)}!</h2><p>O Flask capturou seu nome diretamente da barra de endereços!</p>"


# 5. Bloco de Inicialização do Servidor de Desenvolvimento
if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
```

---

## 7. Dissecando o Código Linha por Linha (Para Entender de Verdade!)

Não passe para a frente sem entender o que cada um dos 5 blocos do `hello.py` está fazendo. Vamos destrinchá-los com calma:

### Bloco 1: `from flask import Flask` e `app = Flask(__name__)`
* Na primeira linha, do pacote `flask` (com **f** minúsculo, que instalamos via `pip`), importamos a classe principal `Flask` (com **F** maiúsculo).
* Na linha `app = Flask(__name__)`, estamos criando o objeto `app`, que representa o nosso servidor web.
* **Mas o que é esse `__name__` com dois sublinhados de cada lado?**  
  No Python, `__name__` é uma variável interna automática que informa o nome do arquivo ou módulo atual. Quando passamos `__name__` para o `Flask(...)`, estamos dando uma **bússola** para o Flask: *"Ei, Flask! Use a localização deste arquivo aqui como ponto de referência para encontrar as pastas de páginas HTML (`templates`) e arquivos de estilo/scripts (`static`)!"*.

### Bloco 2: O Decorator `@app.route("/")` e a Função de Visualização (*View Function*)
* Logo acima da função `def pagina_inicial():`, temos a linha `@app.route("/")`.
* Em Python, qualquer comando que começa com **`@`** em cima de uma função é chamado de **Decorator** (Decorador). Pense nele como uma etiqueta adesiva que dá um superpoder para a função de baixo.
* Sem o `@app.route("/")`, `pagina_inicial()` seria apenas uma função Python comum que ninguém na internet conseguiria chamar. Com o `@app.route("/")`, você está dizendo ao Flask:
  > *"Sempre que alguém acessar a raiz do site (`/`), execute a função `pagina_inicial()` e envie o texto que ela retornar no `return` como resposta para o navegador!"*

### Bloco 3: Retornando um Dicionário Python em `@app.route("/sobre")`
* Repare na função `sobre_o_sistema()`: em vez de retornar uma string com tags HTML (`<h1>...`), ela retorna um **dicionário Python** comum (`{"sistema": "...", "tecnologias": [...]}`).
* **O que o Flask faz quando uma rota retorna um dicionário?**  
  Automaticamente, o Flask converte esse dicionário Python para o formato **JSON** (*JavaScript Object Notation*), que é a língua universal usada para trocar dados entre sistemas e atualizar tabelas na tela sem precisar recarregar a página inteira!

### Bloco 4: Capturando valores da URL com `@app.route("/saudacao/<nome>")`
* Observe os sinais de menor e maior em `<nome>`. Quando colocamos `<alguma_coisa>` dentro do `@app.route`, criamos uma **rota dinâmica**.
* Qualquer palavra que o usuário digitar no navegador depois de `/saudacao/` (por exemplo, `/saudacao/Ana` ou `/saudacao/Ronan`) será capturada pelo Flask e entregue automaticamente como argumento para o parâmetro `nome` da função `def saudar_usuario(nome):`.
* Nas próximas aulas, usaremos exatamente essa técnica para editar ou excluir uma sala específica pelo número de identificação dela (por exemplo: `/salas/<int:sala_id>/editar`).

#### 🛡️ Segurança desde a primeira rota: por que `escape(nome)` e não apenas `{nome}`?

Repare que a rota devolve um HTML montado com o texto que **o visitante digitou na barra de endereços**. Isso abre uma brecha chamada **XSS (*Cross-Site Scripting*)**.

> **Analogia do mural de recados:** imagine um mural de escola onde qualquer pessoa pode pendurar um papel e o coordenador lê em voz alta, sem conferir, **tudo** o que está escrito. Se alguém escrever *"Ao ouvir isto, todos devem entregar a carteira"*, o coordenador acaba dando uma ordem que ele nunca quis dar. No navegador acontece o mesmo: se alguém acessar `/saudacao/<script>alert('invadido')</script>`, o navegador **executa** esse trecho como se fosse código do nosso site. Em um sistema real, esse código poderia roubar a sessão de login de quem clicou no link.

A solução é o `escape(...)`, que troca os símbolos perigosos por versões inofensivas (`<` vira `&lt;`), de modo que o navegador **mostra** o texto na tela em vez de **executá-lo**.

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `from markupsafe import escape` | Importa a função `escape` do pacote `markupsafe`, que já veio junto com o Flask (aparece no `requirements.txt`). | Precisamos dela para "neutralizar" o texto digitado pelo visitante. | O Python avisa `NameError: name 'escape' is not defined` ao abrir a rota. |
| `{escape(nome)}` dentro da f-string | Chama a função sobre o valor capturado da URL antes de colocá-lo no HTML. | Garante que qualquer `<`, `>`, `&` ou aspas digitados virem texto comum. | A rota continua funcionando para nomes normais (`Maria`), mas passa a **executar** qualquer script embutido no endereço: a brecha de XSS volta. |

> 💡 **Regra para o resto do curso:** nos templates Jinja2 (a partir da Aula 02), o `{{ variavel }}` já faz esse `escape` **automaticamente**. O perigo aparece apenas quando montamos HTML "na mão" dentro do Python, como fizemos nesta aula.

### Bloco 5: `if __name__ == "__main__":` e `app.run(...)`
* A condição `if __name__ == "__main__":` garante que o servidor só será iniciado quando executarmos este arquivo diretamente pelo comando `python hello.py`.
* Dentro do `app.run(host="127.0.0.1", port=5000, debug=True)`, configuramos três parâmetros vitais:
  1. **`host="127.0.0.1"`**: É o endereço IP universal chamado de **`localhost`**. Ele significa *"este próprio computador"*. Ou seja, o servidor ficará acessível apenas na sua máquina durante o desenvolvimento.
  2. **`port=5000`**: Um computador pode rodar vários programas de rede ao mesmo tempo (banco de dados, navegador, Spotify). A **porta** funciona como o número do apartamento de um prédio: o MySQL mora na porta `3306`, e o Flask, por padrão, atende na porta **`5000`**.
  3. **`debug=True`**: Ativa o **Modo de Depuração** de desenvolvimento, que nos dá dois grandes benefícios:
     * **Recarregamento Automático (*Hot Reload*):** Sempre que você alterar o código no VS Code e salvar (`Ctrl + S`), o Flask reinicia sozinho em menos de 1 segundo, sem você precisar parar e rodar o comando no terminal de novo!
     * **Tela de Erro Explicativa no Navegador:** Se o seu código Python tiver algum erro, o Flask mostrará diretamente no navegador exatamente qual linha falhou e o motivo do erro.

> ⚠️ **`debug=True` é só para o seu computador!** Pense no modo de depuração como uma **oficina com as portas abertas**: ótima para o mecânico trabalhar, péssima para receber clientes. A tela de erro do modo debug permite **executar comandos Python** no servidor. Se um sistema publicado na internet estiver com `debug=True`, qualquer visitante que provocar um erro ganha acesso ao seu servidor. Por isso, a partir da Aula 02 o modo debug será controlado por uma variável no arquivo `.env`, e nunca escrito fixo no código.

---

## 8. Executando e Testando na Prática

Salve o arquivo `hello.py` (`Ctrl + S`). No terminal, certifique-se de que o `(venv)` está ativo e execute:

```bash
python hello.py
```

O seu terminal vai mostrar as seguintes mensagens e ficará "travado" (aguardando conexões — isso é normal, significa que o servidor está ligado e escutando!):

```text
 * Serving Flask app 'hello'
 * Debug mode: on
WARNING: This is a development server. Do not use it in a production deployment.
 * Running on http://127.0.0.1:5000
Press CTRL+C to quit
 * Restarting with stat
 * Debugger is active!
 * Debugger PIN: 123-456-789
```

### Faça os 5 testes abaixo no seu navegador:

1. **Teste 1 (Rota Principal HTML):** Abra o navegador e acesse `http://127.0.0.1:5000/`. Você verá o título *"Olá, Mundo! Nosso servidor Flask está no ar!"* e os dois links clicáveis.
2. **Teste 2 (Rota JSON):** Clique no primeiro link ou acesse `http://127.0.0.1:5000/sobre`. Veja como o navegador exibe os dados estruturados em formato JSON!
3. **Teste 3 (Rota Dinâmica):** Acesse `http://127.0.0.1:5000/saudacao/Maria` e depois troque `Maria` pelo seu próprio nome na barra de endereços do navegador. Veja a página mudar instantaneamente!
4. **Teste 4 (Lendo os Logs do Terminal):** Volte para a janela do seu terminal e observe as linhas novas que apareceram enquanto você navegava:
   ```text
   127.0.0.1 - - [14/Oct/2026 10:15:01] "GET / HTTP/1.1" 200 -
   127.0.0.1 - - [14/Oct/2026 10:15:08] "GET /sobre HTTP/1.1" 200 -
   127.0.0.1 - - [14/Oct/2026 10:15:15] "GET /saudacao/Maria HTTP/1.1" 200 -
   ```
   Cada linha dessas é o registro ao vivo de um pedido HTTP (`GET`), a rota acessada (`/sobre`) e o código de status HTTP **`200`**, que significa **"Sucesso (OK)"**! Se você tentar acessar uma rota que não existe no código (como `http://127.0.0.1:5000/banana`), verá no navegador a mensagem *Not Found* e no terminal o código **`404`** (*Página Não Encontrada*).
5. **Teste 5 (Provando que o `escape` protege):** Acesse `http://127.0.0.1:5000/saudacao/<h1>Maria`. Em vez de aparecer **Maria** em letras gigantes, a página mostrará o texto `<h1>Maria` literalmente, porque o `escape` transformou a tag em texto comum. Agora apague temporariamente o `escape(...)` da rota, salve, repita o teste e veja o título gigante aparecer: isso prova que o navegador estava **executando** o HTML digitado na URL. Depois do teste, coloque o `escape` de volta! *(Usamos `<h1>` sem a tag de fechamento porque o caractere `/` separa partes da URL e o Flask devolveria `404`.)*

> **Como desligar o servidor no terminal?**  
> Quando quiser parar o servidor para voltar a digitar outros comandos no terminal, clique dentro do terminal e pressione **`CTRL + C`** no teclado.

---

## 9. Guia de Sobrevivência no Laboratório (Erros Comuns e Soluções)

Se algo não sair como esperado durante a aula, consulte esta tabela rápida antes de se preocupar:

| Sintoma / Mensagem de Erro | Causa Mais Provável | Como Resolver Rapidamente |
| :--- | :--- | :--- |
| `ModuleNotFoundError: No module named 'flask'` | O ambiente virtual `venv` **não está ativo** no terminal, ou você executou o arquivo pelo botão "Play" do VS Code apontando para o Python global da máquina. | Verifique se aparece `(venv)` no início da linha do terminal. Se não aparecer, rode `venv\Scripts\Activate.ps1` (Windows) ou `source venv/bin/activate` (Linux/Mac) e execute `python hello.py` pelo terminal. |
| `Address already in use` ou `Port 5000 is in use` | Você já tem outro terminal aberto rodando o `hello.py` (ou no macOS o recurso *AirPlay Receiver* está usando a porta 5000). | Feche o outro terminal com `CTRL + C`, ou mude o número da porta no final do `hello.py` para `port=5001` e acesse `http://127.0.0.1:5001`. |
| Alterei o texto no `hello.py`, atualizei o navegador (`F5`), mas continua aparecendo o texto antigo. | O arquivo não foi salvo no editor de código antes de atualizar o navegador. | No VS Code, repare se há uma bolinha branca ao lado do nome `hello.py` na aba superior. Pressione **`Ctrl + S`** para salvar e depois atualize o navegador. |
| `TypeError: The view function for '...' did not return a valid response` | Você criou uma função com `@app.route(...)`, mas esqueceu de colocar a linha `return ...` no final dela (e em Python, função sem `return` devolve `None`). | Garanta que toda função associada a uma rota retorne uma *string* HTML ou um dicionário Python. |

---

## 10. Exercícios Práticos de Fixação

Para ter certeza de que você dominou os conceitos desta primeira aula, implemente os 3 pequenos desafios abaixo dentro do seu arquivo `hello.py` e teste no navegador:

1. **Desafio 1 (Nova Rota HTML):** Crie uma rota `@app.route("/instituicao")` que retorne um título `<h2>` com o nome da sua escola/faculdade e um parágrafo `<p>` com o nome do seu curso.
2. **Desafio 2 (Rota com Número Inteiro na URL):** Crie uma rota `@app.route("/dobro/<int:numero>")` associada a uma função `def calcular_dobro(numero):`. Quando o Flask vê `<int:numero>`, ele já converte o valor da URL para número inteiro automaticamente! Faça a função retornar um texto informando qual é o dobro do número digitado na URL (teste acessando `http://127.0.0.1:5000/dobro/15`).
3. **Desafio 3 (Rota JSON de Sala de Exemplo):** Crie uma rota `@app.route("/sala-teste")` que retorne um dicionário Python representando uma sala de aula com as chaves `"codigo": "LAB-101"`, `"capacidade": 40` e `"recursos": ["Projetor", "Ar-condicionado", "40 PCs"]`.

<details>
<summary><strong>💡 Clique aqui para ver o Gabarito Comentado dos Exercícios</strong></summary>

```python
# Adicione estas três rotas antes do bloco "if __name__ == '__main__':" no seu hello.py:

# Resolução do Desafio 1:
@app.route("/instituicao")
def mostrar_instituicao():
    return """
    <h2>Centro Universitário de Tecnologia</h2>
    <p>Curso Prático de Desenvolvimento Web com Python e Flask.</p>
    """


# Resolução do Desafio 2:
# O prefixo "int:" antes de "numero" diz ao Flask para aceitar apenas números inteiros
# e já entregar a variável convertida para int dentro da função Python!
@app.route("/dobro/<int:numero>")
def calcular_dobro(numero):
    resultado = numero * 2
    return f"<h2>O dobro de {numero} é igual a {resultado}!</h2>"


# Resolução do Desafio 3:
@app.route("/sala-teste")
def sala_teste():
    return {
        "codigo": "LAB-101",
        "capacidade": 40,
        "recursos": ["Projetor", "Ar-condicionado", "40 PCs"],
    }
```
</details>

---

## O Que Vem a Seguir?

Agora que você já sabe o que é um ambiente virtual, como o protocolo HTTP funciona e como criar rotas HTML e JSON no Flask, surge uma pergunta importante:
> *"Em um sistema real com dezenas de telas, nós vamos escrever código HTML gigante dentro de strings no Python como fizemos no `hello.py`?"*

**De jeito nenhum!** Na **Aula 02**, vamos aprender a organizar o nosso projeto com uma estrutura profissional (**Application Factory**), proteger configurações em variáveis de ambiente (`.env`) e separar o Python do HTML usando templates **Jinja2** estilizados com **Tailwind CSS**!

---
<!-- nav -->
| Anterior | Índice | Próxima |
| :--- | :---: | ---: |
| &nbsp; | [📚 Índice do Curso](./README.md) | [Aula 02 — Arquitetura, Jinja2 e Tailwind →](./aula_02_arquitetura_factory_jinja2_tailwind.md) |