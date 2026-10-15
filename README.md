# Curso Prático de Flask com MySQL e Tailwind CSS — Sistema SalaFácil

Bem-vindo(a) ao curso prático e progressivo de desenvolvimento web com **Python (Flask)**, **MySQL** e **Tailwind CSS**. Ao longo de **10 aulas detalhadas passo a passo**, você construirá do absoluto zero o **SalaFácil**: um sistema completo de **Gestão de Reservas de Salas e Laboratórios** com controle de acesso baseado em **permissões personalizadas por usuário**, **paginação server-side**, **pesquisa dinâmica em tempo real em todas as tabelas** e **relatórios gerenciais exportáveis**.

---

## 1. Proposta Pedagógica e Objetivos de Aprendizagem

Este curso foi desenhado especialmente para estudantes e desenvolvedores que conhecem o básico de lógica de programação em Python, mas **nunca programaram para a Web com Flask**. Em vez de apenas apresentar blocos prontos de código, cada aula disseca **o que** cada linha faz, **por que** ela existe e **como** os componentes conversam entre si, incluindo guias de resolução dos erros mais comuns em laboratório e exercícios comentados.

Ao concluir as 10 aulas, você será capaz de:

- Compreender como a Web funciona na prática (ciclo HTTP Requisição $\rightarrow$ Resposta, métodos `GET` e `POST`, códigos de status `200`, `401`, `403`, `404` e arquitetura **WSGI / Werkzeug**).
- Configurar ambientes virtuais isolados em Python (`venv`), congelar pacotes (`requirements.txt`) e proteger credenciais sensíveis com variáveis de ambiente (`.env` e `app/config.py`).
- Estruturar aplicações profissionais utilizando o padrão **Application Factory** (`create_app()`), módulos independentes com **Blueprints** e herança de templates no **Jinja2** (`{% extends "base.html" %}`).
- Projetar e modelar bancos de dados relacionais no **MySQL** (`utf8mb4`), dominando relacionamentos **1:N** e **N:M** (tabela pivô), regras de integridade referencial (`ON DELETE CASCADE`, `RESTRICT` e `SET NULL`) e índices compostos (`INDEX`).
- Conectar o Flask ao MySQL com segurança no objeto de contexto `g` (`teardown_appcontext`), usando **pool de conexões**, cursores em dicionário (`dictionary=True`), **transações** (`commit`/`rollback`, `with transacao()`), proteção total contra **SQL Injection** (`%s`) e criptografia de senhas (`generate_password_hash` e `check_password_hash`).
- Implementar **Permissões Personalizadas (Granulares)** por usuário, protegendo rotas no Backend com *decorators* (`@login_obrigatorio` e `@permissao_obrigatoria`) e adaptando menus e botões no Frontend com `tem_permissao()`.
- Defender o sistema dos ataques mais comuns da Web: **XSS** (`escape`), **CSRF** (ficha numerada em todo formulário `POST`), **redirecionamento malicioso** (`caminho_seguro`), **força bruta** no login, **escalada de privilégio**, **injeção de fórmulas em planilhas** e **validação de dados no servidor** (nunca confiar só no HTML).
- Construir um motor universal reutilizável de **Paginação Server-Side** (`LIMIT` e `OFFSET`) aliado à **Pesquisa Dinâmica Assíncrona** (`Fetch API`, *Debounce* de 300ms, cancelamento de pedidos antigos com `AbortController` e `DOMParser`).
- Validar regras críticas de negócio, como o **algoritmo matemático anti-conflito de horários** em agendamentos de salas (protegido contra cliques simultâneos com `SELECT ... FOR UPDATE`) e o controle de lotação máxima.
- Desenvolver um painel de **Relatórios Gerenciais** estilizado com **Tailwind CSS**, contendo indicadores (KPIs), agregações SQL (`TIMESTAMPDIFF`, `CASE WHEN`, `COALESCE`), paginação independente de múltiplas tabelas na mesma página, impressão completa (`@media print`) e exportação em **CSV em streaming (UTF-8 com BOM para Excel)**.
- Escrever **testes automáticos** (`pytest`) para as regras de segurança e de negócio e conhecer o checklist para **publicar** o sistema em produção.

---

## 2. Tecnologias Utilizadas

| Camada | Tecnologia / Biblioteca | Versão Recomendada | Papel no Projeto |
| :--- | :--- | :--- | :--- |
| **Linguagem Base** | Python | 3.10+ | Lógica de negócio, rotas, decorators de segurança e motor de paginação. |
| **Framework Web** | Flask (`Werkzeug` + `Jinja2`) | 3.1+ (`3.1.3`) | Roteamento modular com Blueprints, sessões seguras e motor de templates HTML. |
| **Banco de Dados** | MySQL + `mysql-connector-python` | 8.0+ / `26.7.0` | Persistência relacional, consultas parametrizadas anti-SQL Injection e agregações analíticas. |
| **Estilização UI** | Tailwind CSS | 3.x (Play CDN) | Layout responsivo, sidebar administrativa, badges semânticos, formulários e cards de KPIs. |
| **Interatividade** | JavaScript Vanilla (`Fetch API` + `DOMParser`) | ES6+ | Pesquisa dinâmica com *debounce* de 300ms e troca assíncrona de páginas sem recarregar a tela. |
| **Configuração** | `python-dotenv` | 1.2+ (`1.2.4`) | Leitura segura de variáveis de ambiente a partir do arquivo `.env`. |
| **Testes** *(só desenvolvimento)* | `pytest` | 8+ | Testes automáticos das funções de segurança e validação (Aula 10). Instalado à parte, fora do `requirements.txt`. |

---

## 3. Sumário Geral das 10 Aulas do Curso

O curso está organizado em **10 arquivos Markdown (`.md`)** sequenciais. Cada aula termina com o sistema executável e testável no navegador:

| Aula | Arquivo Markdown | Foco Pedagógico da Aula | Arquivos Trabalhados no Projeto |
| :--- | :--- | :--- | :--- |
| **Aula 01** | [aula\_01\_introducao\_ambiente\_hello\_world.md](./aula_01_introducao_ambiente_hello_world.md) | Como a Web e o HTTP funcionam, criação do ambiente virtual (`venv`), instalação com `pip` e dissecação linha por linha do primeiro servidor Flask. | `requirements.txt`, `hello.py` |
| **Aula 02** | [aula\_02\_arquitetura\_factory\_jinja2\_tailwind.md](./aula_02_arquitetura_factory_jinja2_tailwind.md) | Organização modular de pastas, variáveis de ambiente (`.env`) e `.gitignore`, padrão *Application Factory* (`create_app`), introdução ao Jinja2 e estilização com Tailwind CSS. | `.env`, `.gitignore`, `run.py`, `app/config.py`, `app/__init__.py`, `app/templates/boas_vindas.html` |
| **Aula 03** | [aula\_03\_modelagem\_banco\_mysql\_permissoes.md](./aula_03_modelagem_banco_mysql_permissoes.md) | Cargos fixos vs. permissões granulares (`N:M`), modelagem das 5 tabelas no MySQL, chaves estrangeiras (`CASCADE`, `RESTRICT`, `SET NULL`), regras `CHECK` e índices compostos (o que fazem e o que não fazem). | `sql/schema.sql` |
| **Aula 04** | [aula\_04\_conexao\_mysql\_seguranca\_seed.md](./aula_04_conexao_mysql_seguranca_seed.md) | Ciclo de vida da requisição (`g` e `teardown_appcontext`), pool de conexões, transações (`transacao()`), prevenção de *SQL Injection* (`%s`), hash de senhas e script automatizado de carga inicial (`seed`). | `app/database.py`, `seed_db.py`, `app/config.py`, `app/__init__.py` |
| **Aula 05** | [aula\_05\_autenticacao\_sessoes\_blueprints\_acesso.md](./aula_05_autenticacao_sessoes_blueprints_acesso.md) | Autenticação vs. autorização, sessões criptografadas (`session`), decorators, Blueprints, layout base com Sidebar e **defesas contra CSRF, redirecionamento malicioso e força bruta**, além de páginas de erro 404/500. | `app/utils/security.py`, `app/blueprints/auth.py`, `base.html`, `erro.html`, `auth/login.html`, `auth/perfil.html`, `auth/403.html`, `app/__init__.py` |
| **Aula 06** | [aula\_06\_motor\_paginacao\_pesquisa\_dinamica.md](./aula_06_motor_paginacao_pesquisa_dinamica.md) | Matemática de paginação SQL (`LIMIT`/`OFFSET`), subconsulta `COUNT(*)`, *Macros* no Jinja2, controlador JavaScript com `fetch()`, *Debounce* de 300ms, tratamento de erros e layout parcial para respostas leves. | `app/utils/pagination.py`, `components/paginacao.html`, `base_parcial.html`, `static/js/tabela_dinamica.js` |
| **Aula 07** | [aula\_07\_modulo\_catalogo\_salas\_crud.md](./aula_07_modulo_catalogo_salas_crud.md) | CRUD completo, filtros dinâmicos com `WHERE 1=1` e `LIKE %s`, **validação de dados no servidor**, formulário unificado de criação/edição que "lembra" o que foi digitado e exclusão segura verificando histórico. | `app/utils/validacao.py`, `app/blueprints/salas.py`, `templates/salas/index.html`, `templates/salas/form.html` |
| **Aula 08** | [aula\_08\_modulo\_usuarios\_matriz\_permissoes.md](./aula_08_modulo_usuarios_matriz_permissoes.md) | Listagem com `LEFT JOIN` e `GROUP BY`, `request.form.getlist`, filtro `|groupby('modulo')`, gravação em duas tabelas numa **transação**, sincronização por diferença de conjuntos e **prevenção de escalada de privilégio**. | `app/blueprints/usuarios.py`, `usuarios/index.html`, `usuarios/form.html`, `usuarios/permissoes.html` |
| **Aula 09** | [aula\_09\_gestao\_reservas\_validacao\_conflitos.md](./aula_09_gestao_reservas_validacao_conflitos.md) | Interseção de horários no SQL, escape `'%%H:%%i'`, validação de lotação, **proteção contra clique simultâneo (`FOR UPDATE`)**, ciclo de vida seguro da reserva e regras de cancelamento. | `app/blueprints/reservas.py`, `templates/reservas/index.html`, `templates/reservas/form.html` |
| **Aula 10** | [aula\_10\_relatorios\_gerenciais\_exportacao\_csv.md](./aula_10_relatorios_gerenciais_exportacao_csv.md) | Consultas analíticas (`TIMESTAMPDIFF`, `CASE WHEN`, `COALESCE`), paginação independente de 2 tabelas, impressão completa, **CSV em streaming protegido contra injeção de fórmulas**, **testes automáticos** e checklist de produção. | `app/blueprints/relatorios.py`, `templates/relatorios/painel.html`, `tests/test_utilitarios.py` |

---

## 4. Arquitetura e Árvore de Arquivos do Projeto

Ao longo das 10 aulas, construímos a seguinte estrutura profissional dentro da pasta `sistema_reservas_salas/`:

```text
sistema_reservas_salas/
├── venv/                          # [Aula 01] Ambiente virtual isolado do Python
├── hello.py                       # [Aula 01] Primeiro servidor de aprendizado (rotas HTML e JSON)
├── requirements.txt               # [Aula 01] Lista de dependências congeladas com pip freeze
├── .env                           # [Aula 02] Variáveis de ambiente locais (credenciais, SECRET_KEY e FLASK_DEBUG)
├── .gitignore                     # [Aula 02] Lista do que o Git nunca deve publicar (.env, venv, cache)
├── run.py                         # [Aula 02] Ponto de entrada que inicia o servidor via create_app()
├── seed_db.py                     # [Aula 04] Script de criação e população automática do banco MySQL
├── sql/
│   └── schema.sql                 # [Aula 03] Modelagem DDL das 5 tabelas, regras CHECK e índice de conflito
├── tests/
│   └── test_utilitarios.py        # [Aula 10] Testes automáticos (pytest) de segurança e validação
└── app/
    ├── __init__.py                # [Aulas 02, 04 e 05] Application Factory, hooks e registro de Blueprints
    ├── config.py                  # [Aula 02] Classe Config integrada ao python-dotenv
    ├── database.py                # [Aula 04] Pool de conexões MySQL, helpers query_all/one/execute_write e transacao()
    ├── utils/
    │   ├── __init__.py
    │   ├── security.py            # [Aula 05] Decorators de acesso, tem_permissao, proteção CSRF, caminho_seguro e limite de tentativas
    │   ├── validacao.py           # [Aulas 07-10] Conferência de dados vindos dos formulários e proteção de planilhas
    │   └── pagination.py          # [Aula 06] Motor server-side paginar_consulta() e validação de parâmetros
    ├── blueprints/
    │   ├── __init__.py
    │   ├── auth.py                # [Aula 05] Rotas /auth/login, /auth/logout e /auth/meu-perfil
    │   ├── salas.py               # [Aula 07] CRUD completo do Catálogo de Salas (/salas/)
    │   ├── usuarios.py            # [Aula 08] Gestão de Usuários e Matriz de Permissões (/usuarios/)
    │   ├── reservas.py            # [Aula 09] Agenda de Reservas e validação anti-conflito (/reservas/)
    │   └── relatorios.py          # [Aula 10] Painel de KPIs, relatórios paginados e exportação CSV (/relatorios/)
    ├── static/
    │   └── js/
    │       └── tabela_dinamica.js # [Aula 06] Controlador AJAX com Debounce de 300ms e DOMParser
    └── templates/
        ├── boas_vindas.html       # [Aula 02] Primeiro template estilizado com Tailwind CSS e Jinja2
        ├── base.html              # [Aula 05] Layout administrativo principal com Sidebar responsiva e Flash Messages
        ├── base_parcial.html      # [Aula 06] Layout "só o recheio" usado pelas buscas dinâmicas
        ├── erro.html              # [Aula 05] Tela amigável para erros 404 e 500
        ├── components/
        │   └── paginacao.html     # [Aula 06] Macro Jinja2 reutilizável para botões de paginação
        ├── auth/
        │   ├── login.html         # [Aula 05] Tela de autenticação com contas de demonstração
        │   ├── perfil.html        # [Aula 05] Consulta de dados institucionais e permissões ativas do usuário
        │   └── 403.html           # [Aula 05] Página personalizada de Acesso Negado (HTTP 403 Forbidden)
        ├── salas/
        │   ├── index.html         # [Aula 07] Tabela paginada de salas com busca dinâmica e filtro de capacidade
        │   └── form.html          # [Aula 07] Formulário unificado de cadastro e edição de sala
        ├── usuarios/
        │   ├── index.html         # [Aula 08] Tabela paginada de usuários com contagem de chaves ativas
        │   ├── form.html          # [Aula 08] Cadastro de usuário com seleção inicial de permissões por módulo
        │   └── permissoes.html    # [Aula 08] Matriz visual de checkboxes para edição granular de permissões
        ├── reservas/
        │   ├── index.html         # [Aula 09] Agenda paginada com aprovação, rejeição e cancelamento rápido
        │   └── form.html          # [Aula 09] Formulário de solicitação de reserva de sala
        └── relatorios/
            └── painel.html        # [Aula 10] Cards de KPIs e 2 tabelas independentes (Consolidada e Analítica)
```

---

## 5. Detalhamento Programático Aula por Aula

### Aula 01 — Fundamentos Web, Ambiente Virtual (`venv`) e Primeiras Rotas no Flask
**Arquivo:** [`aula_01_introducao_ambiente_hello_world.md`](./aula_01_introducao_ambiente_hello_world.md)
1. **Como a Web Funciona**: Diferença entre Cliente (Navegador) e Servidor (Flask), protocolo HTTP e métodos `GET` vs. `POST`.
2. **O Ecossistema Flask**: O papel do WSGI/Werkzeug e do motor de templates Jinja2.
3. **Isolamento com Ambiente Virtual (`venv`)**: Por que usar um `venv`, criação e ativação no Windows (PowerShell, CMD, Git Bash), Linux e macOS.
4. **Gerenciamento de Pacotes (`pip`)**: Instalação de `Flask`, `mysql-connector-python` e `python-dotenv`, e congelamento no `requirements.txt`.
5. **Dissecação Completa do `hello.py`**: O significado de `__name__`, como funciona o decorator `@app.route`, retorno de HTML vs. conversão automática de dicionários para JSON, rotas dinâmicas (`<nome>`) e modo `debug=True`.
6. **Leitura de Logs HTTP no Terminal, Guia de Erros Comuns e Exercícios Comentados**.
7. **Segurança desde a primeira rota**: o que é *XSS* e por que usamos `escape()`, e por que o `debug=True` é só para o seu computador.

### Aula 02 — Arquitetura Profissional: Application Factory, `.env`, Jinja2 e Tailwind CSS
**Arquivo:** [`aula_02_arquitetura_factory_jinja2_tailwind.md`](./aula_02_arquitetura_factory_jinja2_tailwind.md)
1. **Separação de Responsabilidades**: Por que dividir um sistema real em pacotes e módulos.
2. **Criação da Árvore de Diretórios**: Comandos práticos para PowerShell, Bash e CMD.
3. **Segurança de Configurações (`.env` e `app/config.py`)**: O papel da `SECRET_KEY`, uso de `load_dotenv()` e valores padrão de segurança em `os.getenv()`.
4. **O Padrão Application Factory (`app/__init__.py`)**: O que faz o arquivo `__init__.py` no Python, evitando importações circulares com `create_app()` e enviando dados para templates com `render_template()`.
5. **Introdução ao Jinja2 e ao Tailwind CSS (`boas_vindas.html`)**: Expressões `{{ ... }}`, laços `{% for %}...{% endfor %}` e classes utilitárias responsivas do Tailwind via Play CDN.
6. **Ponto de Entrada (`run.py`), Guia de Erros Comuns e Exercícios Comentados**.
7. **`.gitignore` e Trava da `SECRET_KEY`**: o que nunca vai para o GitHub e por que o sistema se recusa a iniciar sem chave; modo debug controlado pelo `.env` (`FLASK_DEBUG`).

### Aula 03 — Modelagem Relacional no MySQL e Arquitetura de Permissões Personalizadas
**Arquivo:** [`aula_03_modelagem_banco_mysql_permissoes.md`](./aula_03_modelagem_banco_mysql_permissoes.md)
1. **Cargos Fixos vs. Permissões Granulares**: Por que sistemas corporativos precisam de permissões personalizadas por usuário.
2. **Diagrama Relacional das 5 Tabelas (`gestao_reservas_salas`)**: Como `usuarios`, `permissoes`, `usuario_permissoes`, `salas` e `reservas` se conectam.
3. **Domínio dos Conceitos SQL**: `utf8mb4`, booleanos com `TINYINT(1)`, validação com `ENUM`, chave primária composta (`PRIMARY KEY (usuario_id, permissao_id)`) e as 3 regras de exclusão (`ON DELETE CASCADE`, `RESTRICT` e `SET NULL`).
4. **Construção do Script `sql/schema.sql` e Índices Compostos (`INDEX`)**: Otimizando buscas textuais e checagem de conflitos de horário.
5. **Catálogo das 13 Permissões, Consultas `INNER JOIN` e Exercícios Comentados**.
6. **Regras `CHECK` e a verdade sobre índices**: o "segundo porteiro" dentro do banco e por que `LIKE '%termo%'` não usa índice.

### Aula 04 — Conectando Flask ao MySQL com Segurança e Carga Inicial (`seed_db.py`)
**Arquivo:** [`aula_04_conexao_mysql_seguranca_seed.md`](./aula_04_conexao_mysql_seguranca_seed.md)
1. **Conexão vs. Cursor no Python**: Como funciona o `mysql-connector-python` e a importância do `cursor(dictionary=True)`.
2. **Ciclo de Vida da Requisição no Flask (`g`, `current_app` e `teardown_appcontext`)**: Reaproveitando uma única conexão por requisição HTTP e garantindo o fechamento automático.
3. **Blindagem contra SQL Injection**: Por que jamais usar `f-strings` em comandos SQL e como passar tuplas parametrizadas com `%s`.
4. **Codificação do `app/database.py`**: Funções reutilizáveis `get_db()`, `query_all()`, `query_one()` e `execute_write()` com controle de transação (`commit` e `rollback`).
5. **Criptografia de Senhas e Script `seed_db.py`**: Como funciona o `generate_password_hash`, uso de `INSERT IGNORE`, `executemany` e datas dinâmicas com `timedelta`.
6. **Integração no `app/__init__.py` Exibindo Contagens Reais do MySQL na Tela Inicial**.
7. **Pool de Conexões e `transacao()`**: o "bicicletário" de conexões, a transação como transferência bancária e um seed que funciona de qualquer pasta e com qualquer `DB_NAME`.

### Aula 05 — Autenticação, Sessões, Blueprints e Controle de Acesso em Dupla Camada
**Arquivo:** [`aula_05_autenticacao_sessoes_blueprints_acesso.md`](./aula_05_autenticacao_sessoes_blueprints_acesso.md)
1. **Autenticação, Autorização e Sessões HTTP (`session`)**: Como o cookie assinado pela `SECRET_KEY` mantém o usuário logado.
2. **Dupla Camada de Segurança**: UX no Frontend (`tem_permissao` no Jinja2) + proteção real no Backend (`@permissao_obrigatoria` nas rotas).
3. **Motor de Segurança (`app/utils/security.py`)**: Construção explicada de `carregar_usuario_logado()`, conjuntos `set` de busca $O(1)$ e decorators com `@wraps(view_func)`.
4. **Módulo de Autenticação com Blueprints (`app/blueprints/auth.py`)**: Rotas `/auth/login`, `/auth/logout` e `/auth/meu-perfil`, validação com `check_password_hash` e notificações com `flash()`.
5. **Herança de Templates (`base.html`) e Telas de Autenticação (`login.html`, `perfil.html`, `403.html`)**: Menu lateral dinâmico, `@app.before_request`, `@app.context_processor` e `@app.errorhandler(403)`.
6. **Os 4 ataques que bloqueamos**: CSRF (ficha numerada nos formulários), *open redirect* (`caminho_seguro`), força bruta (limite de tentativas) e vazamento por erro (páginas 404/500 amigáveis); consulta única de usuário/permissões e página inicial por permissão.

### Aula 06 — Motor Universal de Paginação Server-Side e Pesquisa Dinâmica (AJAX)
**Arquivo:** [`aula_06_motor_paginacao_pesquisa_dinamica.md`](./aula_06_motor_paginacao_pesquisa_dinamica.md)
1. **Paginação Server-Side vs. Client-Side**: Por que paginar diretamente no MySQL.
2. **A Matemática do `LIMIT` e `OFFSET`**: Fórmula `(pagina - 1) * por_pagina`, arredondamento com `math.ceil()` e leitura de parâmetros GET com `request.args`.
3. **Motor Python (`app/utils/pagination.py`)**: Subconsulta universal `SELECT COUNT(*)`, proteção de limites e janela deslizante de páginas visíveis.
4. **Macros no Jinja2 (`app/templates/components/paginacao.html`)**: Criando um componente visual reutilizável com atributos `data-page` e `data-target`.
5. **Pesquisa Dinâmica Assíncrona (`app/static/js/tabela_dinamica.js`)**: Como funcionam o temporizador *Debounce* de 300ms, a `Fetch API`, a atualização parcial do DOM com `DOMParser`, o `history.replaceState` e a delegação de eventos.
6. **Robustez e desempenho**: cancelamento de pedidos antigos (`AbortController`), tratamento de erros e sessão expirada, tecla Enter e o layout parcial (`base_parcial.html`) que devolve só o "recheio" da página.

### Aula 07 — Módulo de Catálogo de Salas (CRUD Completo com Busca Dinâmica)
**Arquivo:** [`aula_07_modulo_catalogo_salas_crud.md`](./aula_07_modulo_catalogo_salas_crud.md)
1. **As 4 Operações do CRUD e Suas Permissões**: Conectando `salas.visualizar`, `salas.criar`, `salas.editar` e `salas.excluir`.
2. **Construção de Filtros SQL Dinâmicos (`app/blueprints/salas.py`)**: O truque do `WHERE 1=1`, busca simultânea em 4 colunas com `LIKE %s` e filtro numérico de capacidade mínima.
3. **Listagem Paginada (`app/templates/salas/index.html`)**: Integrando a macro de paginação e as classes `.js-busca-dinamica` e `.js-filtro-imediato`.
4. **Formulário Unificado de Criação e Edição (`app/templates/salas/form.html`)**: Usando expressões ternárias do Jinja2 e o operador `~` para compartilhar o mesmo HTML.
5. **Exclusão Segura via `POST`**: Verificando vínculos na tabela `reservas` antes de executar o `DELETE` e orientando o uso do status *Em Manutenção*.
6. **Validação no servidor (`app/utils/validacao.py`)**: por que `required` no HTML não protege, expressões regulares básicas, formulários que "lembram" o que foi digitado e proteção das reservas futuras ao editar uma sala.

### Aula 08 — Módulo de Usuários e Matriz Visual de Permissões Personalizadas
**Arquivo:** [`aula_08_modulo_usuarios_matriz_permissoes.md`](./aula_08_modulo_usuarios_matriz_permissoes.md)
1. **Listagem Relacional com `LEFT JOIN` e `GROUP BY`**: Contando quantas permissões cada usuário possui (`COUNT(up.permissao_id)`) sem ocultar usuários com zero permissões.
2. **Capturando Múltiplos Checkboxes no Flask**: A diferença fundamental entre `request.form.get()` e `request.form.getlist("permissoes_ids")`.
3. **Cadastro em Duas Tabelas (`novo_id`) e Agrupamento com `|groupby('modulo')` (`usuarios/form.html`)**: Gravando o usuário e suas permissões iniciais na sequência.
4. **Matriz Visual de Permissões (`usuarios/permissoes.html`)**: Sincronização transacional (`UPDATE` + `DELETE` + `INSERT` + `commit`) e teste ao vivo de concessão/revogação instantânea em duas janelas.
5. **Segurança do módulo**: cadastro de usuário numa única transação, comparação de conjuntos (`para_remover`/`para_adicionar`) que preserva o histórico, regra contra escalada de privilégio e trava anti-autoexclusão.

### Aula 09 — Gestão de Reservas de Salas e Algoritmo SQL Anti-Conflito de Horários
**Arquivo:** [`aula_09_gestao_reservas_validacao_conflitos.md`](./aula_09_gestao_reservas_validacao_conflitos.md)
1. **A Matemática da Colisão de Horários**: Análise visual dos 4 cenários de sobreposição e da fórmula universal `hora_inicio < novo_fim AND hora_fim > novo_inicio` (permitindo reservas adjacentes).
2. **O Escape `'%%H:%%i'` no `TIME_FORMAT`**: Evitando conflitos de interpolação com os marcadores `%s` do `mysql-connector-python`.
3. **Duplo `JOIN` na Tabela `usuarios` (`reservas.py`)**: `INNER JOIN` para o solicitante e `LEFT JOIN` para o aprovador.
4. **Regras de Negócio no Agendamento**: Validação cronológica, validação da lotação máxima da sala e aprovação automática condicional para quem possui `reservas.aprovar`.
5. **Fluxo de Aprovação, Recusa e Cancelamento (`reservas/index.html`)**: Mini-formulários `POST` inline e regra de propriedade (*dono da reserva* vs. `reservas.cancelar_qualquer`).
6. **Concorrência e estados**: o problema do clique simultâneo e a trava `SELECT ... FOR UPDATE` dentro de `transacao()`; ações que só valem para o estado atual da reserva (`WHERE ... AND status = 'pendente'`).

### Aula 10 — Relatórios Gerenciais, Paginação Dupla Independente e Exportação CSV
**Arquivo:** [`aula_10_relatorios_gerenciais_exportacao_csv.md`](./aula_10_relatorios_gerenciais_exportacao_csv.md)
1. **Agregação Condicional no MySQL**: Calculando múltiplos indicadores em uma única query com `SUM(CASE WHEN ...)`, `COALESCE` e `ROUND`.
2. **Cálculo Preciso de Horas Ocupadas (`TIMESTAMPDIFF`)**: Somando durações em minutos divididas por `60.0` e preservando salas ociosas com filtro de datas na cláusula `ON` do `LEFT JOIN`.
3. **Paginação Dupla Independente na Mesma Tela**: Isolando os parâmetros `q_salas` / `page_salas` (Tabela 1) de `q` / `page` (Tabela 2) com `data-page-param`.
4. **Exportação CSV para Excel e Modo de Impressão**: Gerando planilhas em memória RAM (`io.StringIO`) com assinatura UTF-8 BOM (`\ufeff`), delimitador `;` e folha de estilo `@media print`.
5. **CSV em *streaming* e seguro**: geradores com `yield`, proteção contra injeção de fórmulas, botões que levam os filtros atuais e impressão completa.
6. **Testes automáticos e produção**: `pytest` nas funções de segurança e validação, e o checklist para publicar (gunicorn/waitress, `SECRET_KEY` nova, HTTPS).

---

## 6. Mapa das 5 Tabelas com Paginação Server-Side e Pesquisa Dinâmica

Todas as **5 listagens de dados** do sistema contam com paginação no MySQL e pesquisa dinâmica instantânea:

| Tabela / Tela | Rota (`Blueprint`) | Campos Pesquisados Dinamicamente (`LIKE`) | Filtros Adicionais |
| :--- | :--- | :--- | :--- |
| **1. Catálogo de Salas** | `salas.listar` | Código da sala, nome, bloco e recursos/equipamentos | Capacidade mínima de lugares e itens por página |
| **2. Lista de Usuários** | `usuarios.listar` | Nome, e-mail, setor e etiqueta de cargo | Status da conta (Ativo/Inativo) e itens por página |
| **3. Agenda de Reservas** | `reservas.listar` | Título do evento, finalidade, código/nome da sala, solicitante e setor | Data específica, status da reserva e itens por página |
| **4. Ocupação Consolidada por Sala** | `relatorios.painel` | Código da sala, nome da sala e bloco (`q_salas`) | Período (formulário próprio que recarrega a página e afeta KPIs e tabelas) e página própria (`page_salas`) |
| **5. Auditoria Analítica de Reservas** | `relatorios.painel` | Evento, código da sala, nome da sala, solicitante e setor (`q`) | Status da reserva, itens por página, exportação CSV e impressão completa (ambas respeitam os filtros da tela) |

---

## 7. Guia Rápido de Execução do Projeto Completo

Após acompanhar as aulas (ou clonar o repositório completo), execute os passos abaixo na pasta raiz `sistema_reservas_salas/`:

```bash
# 1. Crie e ative o ambiente virtual (caso ainda não esteja ativo)
python -m venv venv
# No Windows (PowerShell): venv\Scripts\Activate.ps1
# No Windows (CMD):        venv\Scripts\activate.bat
# No Linux/macOS:          source venv/bin/activate

# 2. Instale as dependências do projeto
pip install -r requirements.txt

# 3. Configure sua senha do MySQL no arquivo .env e rode o script de carga inicial
python seed_db.py

# 4. Inicie o servidor Flask
python run.py

# 5. (Opcional) Rode os testes automáticos da Aula 10
pip install pytest
python -m pytest
```

> ⚠️ O `.env` (com a senha do MySQL e a `SECRET_KEY`) **não** vai para o repositório: ele está no `.gitignore`. Crie o seu seguindo a Aula 02, incluindo `FLASK_DEBUG=1` apenas no seu computador.

> 📦 **Projeto de referência:** a pasta [`sistema_reservas_salas/`](./sistema_reservas_salas/) contém o código final das 10 aulas, testado, para você **conferir o seu trabalho**. O `.env` não está nela: copie o `.env.example` e ajuste a senha do MySQL.

Acesse **`http://127.0.0.1:5000`** no navegador e experimente os 3 perfis de teste criados automaticamente pelo `seed_db.py` (a senha padrão para todos é **`123456`**; as contas só aparecem na tela de login com `FLASK_DEBUG=1`, e devem ser apagadas antes de publicar o sistema):

* **Ana Administradora (`admin@salafacil.com`)**: Possui todas as **13 permissões personalizadas** ativas.
* **Carlos Gestor (`gestor@salafacil.com`)**: Possui **9 permissões** (gerencia salas, aprova/cancela reservas e exporta relatórios, mas não gerencia usuários nem permissões).
* **Beatriz Professora (`beatriz@salafacil.com`)**: Possui **3 permissões** (visualiza salas e agenda, solicita reservas e cancela apenas os próprios agendamentos).

---
<!-- nav -->
| Início da Trilha |
| :---: |
| [🚀 Começar pela Aula 01 — Fundamentos Web, Ambiente Virtual e Primeiras Rotas no Flask →](./aula_01_introducao_ambiente_hello_world.md) |