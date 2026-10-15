# Aula 06 — Motor Universal de Paginação Server-Side e Pesquisa Dinâmica (AJAX)

Até a **Aula 05**, construímos a fundação completa de segurança do **SalaFácil**: nosso banco de dados MySQL está populado, o login criptografado está funcionando e o menu lateral inteligente já se adapta às permissões personalizadas de cada usuário.

A partir da próxima aula, começaremos a construir as telas operacionais do sistema (**Catálogo de Salas**, **Usuários & Permissões**, **Agenda de Reservas** e **Relatórios Gerenciais**). Todas essas telas têm um requisito profissional em comum:
> **"Todas as tabelas do sistema devem possuir paginação no servidor (Server-Side) e pesquisa dinâmica em tempo real."**

Imagine se nós escrevêssemos a lógica de calcular páginas, contar registros no MySQL, desenhar botões *"Anterior / Próxima"* e programar buscas em JavaScript do zero dentro de cada uma das **5 tabelas** do sistema: teríamos centenas de linhas de código repetido!

Nesta **Aula 06**, vamos pensar como engenheiros de software e construir um **Motor Universal Reutilizável** dividido em 3 peças que trabalharão juntas até o final do curso:
1. **No Backend (`app/utils/pagination.py`):** Uma função em Python que transforma qualquer consulta SQL comum em uma consulta paginada com `COUNT(*)`, `LIMIT` e `OFFSET`.
2. **No Template (`app/templates/components/paginacao.html`):** Uma **Macro Jinja2** estilizada com Tailwind CSS que desenha a barra de paginação automaticamente para qualquer tabela.
3. **No Frontend (`app/static/js/tabela_dinamica.js`):** Um script JavaScript com **Debounce de 300ms** e `fetch()` que filtra as tabelas em tempo real enquanto o usuário digita, sem recarregar a página inteira!

---

## 1. Por Que Paginar no Servidor (Server-Side) e Não no Navegador?

Quando uma tabela precisa exibir muitos registros, existem duas formas de programar a paginação:

* **Abordagem Amadora (Paginação no Cliente / Navegador):** O Python faz um `SELECT * FROM reservas` trazendo **50.000 linhas** do MySQL de uma só vez, envia um HTML gigante de 15 MB para o navegador e um plugin JavaScript esconde 49.992 linhas na tela. Resultado: o servidor fica lento, a memória estoura e a página demora 10 segundos para abrir no celular.
* **Abordagem Profissional (Paginação Server-Side no MySQL):** Se a tela exibe **8 registros por página**, o Python pede ao MySQL **apenas os 8 registros da página atual**! Não importa se a tabela tem 10 ou 1 milhão de reservas: o banco de dados só transfere 8 linhas por vez, mantendo o sistema instantâneo.

---

## 2. A Matemática da Paginação no MySQL (`LIMIT` e `OFFSET`)

Para pedir apenas uma "fatia" dos registros ao MySQL, usamos dois comandos no final do `SELECT`:
* **`LIMIT`**: Quantos registros queremos trazer no máximo (ex.: `por_pagina = 8`).
* **`OFFSET`**: Quantos registros devemos **pular** (ignorar) do início da tabela antes de começar a pegar os registros da página atual.

### Como calcular o `OFFSET` de qualquer página?
A fórmula matemática universal da paginação é:

$$\text{offset} = (\text{pagina} - 1) \times \text{por\_pagina}$$

Veja um exemplo prático: suponha que temos **25 salas** cadastradas no banco e configuramos **`por_pagina = 8`**.
1. Quantas páginas teremos no total? Dividimos $25 \div 8 = 3,125$. Como não existe "0,125 página", arredondamos **sempre para cima** usando a função `math.ceil()` do Python: teremos **4 páginas** (`total_paginas = 4`).
2. Veja o que a fórmula do `OFFSET` faz em cada página:

| Página Atual (`pagina`) | Cálculo do `OFFSET`: `(pagina - 1) * 8` | Comando enviado ao MySQL | Quais salas são exibidas na tela? |
| :---: | :---: | :--- | :--- |
| **Página 1** | $(1 - 1) \times 8 = \mathbf{0}$ | `LIMIT 8 OFFSET 0` | Pula 0 $\rightarrow$ Exibe da **1ª à 8ª** sala |
| **Página 2** | $(2 - 1) \times 8 = \mathbf{8}$ | `LIMIT 8 OFFSET 8` | Pula as 8 primeiras $\rightarrow$ Exibe da **9ª à 16ª** sala |
| **Página 3** | $(3 - 1) \times 8 = \mathbf{16}$ | `LIMIT 8 OFFSET 16` | Pula as 16 primeiras $\rightarrow$ Exibe da **17ª à 24ª** sala |
| **Página 4** | $(4 - 1) \times 8 = \mathbf{24}$ | `LIMIT 8 OFFSET 24` | Pula as 24 primeiras $\rightarrow$ Exibe a **25ª** (última) sala |

Simples e exato!

---

## 3. Como Ler Parâmetros de Busca na URL? (`request.args` vs. `request.form`)

Na **Aula 05**, quando criamos o formulário de Login (`method="POST"`), lemos os dados enviados usando `request.form.get("email")`.

Nas listagens e pesquisas dinâmicas, usamos o método **`GET`**, onde os filtros viajam visíveis na própria barra de endereços do navegador, logo após o ponto de interrogação **`?`** (a chamada **Query String**):

```text
http://127.0.0.1:5000/salas/?q=Projetor&page=2&per_page=8
                             \________/ \____/ \________/
                                 |        |        |
            request.args.get("q")         |        request.args.get("per_page")
                             request.args.get("page")
```

* **`request.form`**: Lê dados enviados de forma oculta no corpo de um **`POST`** (usado para criar, editar ou excluir registros).
* **`request.args`**: Lê os parâmetros da URL após o `?` em uma requisição **`GET`** (usado para buscas `?q=`, filtros de status e número da página `?page=`).

---

## 4. Construindo o Motor de Paginação no Python (`app/utils/pagination.py`)

Agora vamos criar o arquivo **`app/utils/pagination.py`** contendo 3 funções:
1. `validar_por_pagina()`: Garante que o usuário só possa escolher quantidades válidas de itens por página `(5, 8, 10, 20, 50)`, protegendo o sistema contra erros caso alguém digite `?per_page=0` ou `?per_page=abc` na URL.
2. `obter_parametros_listagem()`: Lê de uma só vez o termo pesquisado (`q`), a página atual (`page`) e a quantidade por página (`per_page`) da URL.
3. `paginar_consulta()`: Recebe a query SQL base de qualquer módulo, conta o total de registros no MySQL, aplica a matemática do `LIMIT` e `OFFSET` e devolve um dicionário completo com os itens e os dados dos botões de navegação.

Abra o arquivo **`app/utils/pagination.py`** e digite o código abaixo:

```python
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
```

---

## 5. Dissecando os Truques Inteligentes do `app/utils/pagination.py`

Vamos entender três detalhes fundamentais do código que acabamos de criar:

### 5.1 — Por que contar usando `SELECT COUNT(*) AS total FROM ({sql_base}) AS subconsulta_total`?
Imagine que na Aula 08 ou na Aula 10 a nossa consulta `sql_base` tenha um agrupamento `GROUP BY u.id` (para contar quantas permissões cada usuário tem). Se tentássemos simplesmente trocar o `SELECT ...` por `SELECT COUNT(*)`, o `GROUP BY` faria o MySQL retornar várias linhas de contagem em vez do total de usuários!
Ao envelopar a consulta inteira dentro de parênteses (`FROM (SELECT ...) AS subconsulta_total`), o MySQL primeiro resolve qualquer filtro ou agrupamento interno e, por fora, conta exatamente quantas linhas resultaram!

### 5.2 — A Proteção `if pagina > total_paginas:`
Suponha que o usuário esteja na **Página 3** da tabela de salas. De repente, ele digita `"Auditório"` na barra de pesquisa dinâmica. Como só existem 2 auditórios no banco, o resultado filtrado tem apenas **1 página** (`total_paginas = 1`).
Graças ao `if pagina > total_paginas: pagina = total_paginas`, o nosso motor traz o usuário automaticamente de volta para a Página 1, evitando que ele veja uma "Página 3 vazia"!

### 5.3 — A Janela Deslizante de Botões (`paginas_visiveis`)
Se um relatório tiver 80 páginas no total, não podemos desenhar 80 botões numéricos na tela! Por isso calculamos:
```python
inicio_janela = max(1, pagina - 2)
fim_janela = min(total_paginas, pagina + 2)
paginas_visiveis = list(range(inicio_janela, fim_janela + 1))
```
Isso mostra sempre até **2 páginas antes** e **2 páginas depois** da página atual (por exemplo, se o usuário está na página `5`, os botões exibidos serão `[3, 4, 5, 6, 7]`).

### 5.4 — Dois cuidados de segurança e desempenho que você deve conhecer

1. **O parâmetro `ordenacao` é colado no SQL por `f-string`.** Isso é seguro **somente porque** quem escreve esse texto somos nós, dentro do código (`ordenacao="codigo ASC"`). Os marcadores `%s` só funcionam para **valores**, e não para nomes de colunas. **Regra de ouro:** nunca passe para `ordenacao` algo que veio da barra de endereços (`request.args`), pois seria um buraco de SQL Injection.
2. **Limites honestos de desempenho:**

   | Técnica usada | Funciona bem até... | Quando começa a pesar | O que fazer então |
   | :--- | :--- | :--- | :--- |
   | `LIKE '%termo%'` em várias colunas | Dezenas de milhares de linhas | Centenas de milhares: cada busca lê a tabela inteira (índices comuns não ajudam com `%` no início). | Índice `FULLTEXT` ou um motor de busca dedicado. |
   | `OFFSET` grande (página 5.000) | Poucas centenas de páginas | O MySQL precisa **contar e descartar** todas as linhas anteriores. | Paginação por "último id visto" (*keyset pagination*). |
   | `COUNT(*)` a cada página | Tabelas pequenas e médias | Em tabelas enormes, a contagem é repetida em cada clique. | Guardar o total em cache por alguns segundos. |

   Para o SalaFácil (uma instituição de ensino), nenhum desses limites será alcançado; o importante é saber que eles existem.

---

## 6. O Que é uma Macro no Jinja2? (`app/templates/components/paginacao.html`)

No Python, quando queremos reaproveitar um bloco de lógica em vários lugares sem copiar e colar código, criamos uma **função (`def`)**.
No motor de templates **Jinja2**, existe exatamente o mesmo recurso para reaproveitar blocos visuais de HTML: ele se chama **Macro (`{% macro %}`)**!

Vamos criar a macro `renderizar_paginacao(paginacao, alvo_container='#container-tabela')` no arquivo **`app/templates/components/paginacao.html`**. Sempre que qualquer tabela do sistema precisar de um rodapé com contagem de registros (*"Exibindo 1 a 8 de 10 registros"*) e botões *"← Anterior | 1 | 2 | Próxima →"*, bastará chamar `{{ renderizar_paginacao(paginacao, '#id-da-tabela') }}`!

Abra o arquivo **`app/templates/components/paginacao.html`** e insira o código abaixo:

```html
<!-- app/templates/components/paginacao.html -->
{% macro renderizar_paginacao(paginacao, alvo_container='#container-tabela') %}
<div class="px-6 py-4 bg-slate-50 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4 text-sm no-print">
    <div class="text-slate-600">
        {% if paginacao.total_registros > 0 %}
            Exibindo <span class="font-semibold text-slate-900">{{ paginacao.inicio_item }}</span>
            a <span class="font-semibold text-slate-900">{{ paginacao.fim_item }}</span>
            de <span class="font-semibold text-indigo-600">{{ paginacao.total_registros }}</span> registros
        {% else %}
            Nenhum registro encontrado para os filtros aplicados
        {% endif %}
    </div>

    {% if paginacao.total_paginas > 1 %}
    <div class="flex items-center gap-1.5">
        <button type="button"
                data-page="{{ paginacao.pagina_anterior }}"
                data-target="{{ alvo_container }}"
                {% if not paginacao.tem_anterior %}disabled{% endif %}
                class="js-btn-pagina px-3 py-1.5 rounded-lg border text-xs font-semibold transition
                       {% if paginacao.tem_anterior %}bg-white border-slate-300 text-slate-700 hover:bg-indigo-50 hover:border-indigo-300
                       {% else %}bg-slate-100 border-slate-200 text-slate-400 cursor-not-allowed{% endif %}">
            ← Anterior
        </button>

        {% for num in paginacao.paginas_visiveis %}
        <button type="button"
                data-page="{{ num }}"
                data-target="{{ alvo_container }}"
                class="js-btn-pagina w-8 h-8 rounded-lg border text-xs font-bold transition
                       {% if num == paginacao.pagina %}bg-indigo-600 border-indigo-600 text-white shadow-sm
                       {% else %}bg-white border-slate-300 text-slate-700 hover:bg-indigo-50{% endif %}">
            {{ num }}
        </button>
        {% endfor %}

        <button type="button"
                data-page="{{ paginacao.proxima_pagina }}"
                data-target="{{ alvo_container }}"
                {% if not paginacao.tem_proxima %}disabled{% endif %}
                class="js-btn-pagina px-3 py-1.5 rounded-lg border text-xs font-semibold transition
                       {% if paginacao.tem_proxima %}bg-white border-slate-300 text-slate-700 hover:bg-indigo-50 hover:border-indigo-300
                       {% else %}bg-slate-100 border-slate-200 text-slate-400 cursor-not-allowed{% endif %}">
            Próxima →
        </button>
    </div>
    {% endif %}
</div>
{% endmacro %}
```

### Repare nos atributos `data-page` e `data-target` dos botões acima:
No HTML5, qualquer atributo que começa com **`data-`** serve para guardarmos informações extras que o **JavaScript** lerá quando o usuário clicar no botão:
* `data-page="{{ num }}"`: Informa ao JavaScript para qual número de página aquele botão deve ir.
* `data-target="{{ alvo_container }}"`: Informa ao JavaScript qual `<div>` de tabela na tela deve ser atualizada!

---

## 7. Pesquisa Dinâmica em Tempo Real com JavaScript (`app/static/js/tabela_dinamica.js`)

Agora vamos construir a terceira peça do nosso motor: o controlador JavaScript que já deixamos conectado lá no final do `base.html` na Aula 05 (`<script src="{{ url_for('static', filename='js/tabela_dinamica.js') }}"></script>`).

### Como ele funciona por baixo dos panos? (Sem Mistério!)

Imagine que o usuário está na tela de Salas e começa a digitar a palavra **`"Projetor"`** dentro da caixa de pesquisa. Se recarregássemos a página inteira a cada letra digitada, a tela piscaria e o cursor sairia de dentro da caixa de texto logo na primeira letra `"P"`!

Veja como o nosso `tabela_dinamica.js` resolve isso com 3 técnicas modernas:

1. **O Temporizador *Debounce* de 300ms (Economia Inteligente de Requisições):**  
   Quando você digita `"Projetor"` rápido no teclado, você aperta 8 teclas em menos de 1 segundo. Fazer 8 consultas seguidas ao MySQL (`"P"`, `"Pr"`, `"Pro"`, `"Proj"`...) seria um desperdício.  
   O **Debounce** funciona como a porta de um elevador: a cada tecla pressionada, ele zera um cronômetro de **300 milissegundos (0,3 segundo)**. Só quando você termina de digitar a palavra e faz uma micro-pausa de 0,3s é que ele dispara **1 única busca** para o servidor Flask!
2. **Busca em Segundo Plano (`fetch`) + Troca Cirúrgica do HTML (`DOMParser`):**  
   O JavaScript monta a URL com os filtros (ex.: `/salas/?q=Projetor&page=1`), pede o HTML atualizado ao Flask em segundo plano usando `fetch()`, recorta da resposta **apenas o interior da `<div>` da tabela** usando o `DOMParser` e substitui na tela (`container.innerHTML = novoConteudo.innerHTML`). Assim, a caixa de busca onde você está digitando nem se mexe!
3. **Atualização da Barra de Endereços (`window.history.replaceState`):**  
   Mesmo sem recarregar a página, o script atualiza a URL lá no topo do navegador para `/salas/?q=Projetor&page=1`. Se você copiar o link e mandar para um colega ou apertar `F5`, a pesquisa continua aplicada!

Abra o arquivo **`app/static/js/tabela_dinamica.js`** e insira o código abaixo:

```javascript
// app/static/js/tabela_dinamica.js
document.addEventListener("DOMContentLoaded", () => {
    let temporizadorDebounce = null;
    const pedidosEmAndamento = {};  // um pedido por tabela: { "#container-tabela-salas": AbortController }

    function mostrarErro(container, mensagem) {
        container.innerHTML = `<div class="p-8 text-center text-sm text-rose-700">${mensagem}</div>`;
    }

    function carregarTabelaDinamica(form, pagina = 1) {
        const seletorAlvo = form.dataset.target || "#container-tabela";
        const container = document.querySelector(seletorAlvo);
        if (!container) return;

        // Parte da URL atual para preservar filtros e páginas de outras tabelas na mesma tela
        const url = new URL(window.location.href);
        if (form.action) {
            url.pathname = new URL(form.action, window.location.origin).pathname;
        }

        const dadosForm = new FormData(form);
        dadosForm.forEach((valor, chave) => {
            if (valor !== "") {
                url.searchParams.set(chave, valor);
            } else {
                url.searchParams.delete(chave);
            }
        });

        // Permite definir um parâmetro de página exclusivo por tabela (ex: data-page-param="page_salas")
        const paramPagina = form.dataset.pageParam || "page";
        url.searchParams.set(paramPagina, pagina);

        // Cancela o pedido anterior DESTA tabela, se ainda estiver a caminho
        if (pedidosEmAndamento[seletorAlvo]) {
            pedidosEmAndamento[seletorAlvo].abort();
        }
        const controlador = new AbortController();
        pedidosEmAndamento[seletorAlvo] = controlador;

        container.classList.add("opacity-60", "transition-opacity");

        fetch(url.toString(), {
            headers: { "X-Requested-With": "XMLHttpRequest" },
            signal: controlador.signal
        })
        .then((resposta) => {
            // Sessão expirada: recarrega a página inteira para o servidor mandar para o login
            if (resposta.status === 401 || resposta.redirected) {
                window.location.reload();
                return null;
            }
            if (!resposta.ok) {
                throw new Error("Resposta com erro: " + resposta.status);
            }
            return resposta.text();
        })
        .then((html) => {
            if (html === null) return;
            const docTemp = new DOMParser().parseFromString(html, "text/html");
            const novoConteudo = docTemp.querySelector(seletorAlvo);
            if (!novoConteudo) {
                throw new Error("A resposta não trouxe o container esperado");
            }
            container.innerHTML = novoConteudo.innerHTML;
            window.history.replaceState({}, "", url.toString());
        })
        .catch((erro) => {
            if (erro.name === "AbortError") return;  // pedido cancelado de propósito: não é erro
            mostrarErro(container, "Não foi possível atualizar a tabela. Recarregue a página e tente novamente.");
        })
        .finally(() => {
            if (pedidosEmAndamento[seletorAlvo] === controlador) {
                container.classList.remove("opacity-60");
            }
        });
    }

    // 1. Escuta digitação nos campos de busca dinâmica com Debounce de 300ms
    document.body.addEventListener("input", (evento) => {
        if (evento.target.matches(".js-busca-dinamica")) {
            const form = evento.target.closest(".js-form-filtro");
            clearTimeout(temporizadorDebounce);
            temporizadorDebounce = setTimeout(() => {
                carregarTabelaDinamica(form, 1);
            }, 300);
        }
    });

    // 2. Escuta mudança em selects/filtros de data ou itens por página
    document.body.addEventListener("change", (evento) => {
        if (evento.target.matches(".js-filtro-imediato")) {
            const form = evento.target.closest(".js-form-filtro");
            carregarTabelaDinamica(form, 1);
        }
    });

    // 3. Escuta cliques nos botões de paginação
    document.body.addEventListener("click", (evento) => {
        const botaoPagina = evento.target.closest(".js-btn-pagina");
        if (botaoPagina && !botaoPagina.disabled) {
            evento.preventDefault();
            const seletorAlvo = botaoPagina.dataset.target || "#container-tabela";
            const form = document.querySelector(`.js-form-filtro[data-target="${seletorAlvo}"]`)
                      || document.querySelector(".js-form-filtro");
            if (form) {
                carregarTabelaDinamica(form, botaoPagina.dataset.page);
            }
        }
    });

    // 4. Tecla Enter dentro do formulário de filtros: busca dinâmica em vez de recarregar a página
    document.body.addEventListener("submit", (evento) => {
        const form = evento.target;
        if (form.matches(".js-form-filtro")) {
            evento.preventDefault();
            clearTimeout(temporizadorDebounce);
            carregarTabelaDinamica(form, 1);
        }
    });
});
```

### Linha por linha do `tabela_dinamica.js`

> **Novidades desta versão:** o script agora (1) **cancela** o pedido antigo quando você digita rápido, (2) **avisa** quando algo dá errado em vez de despejar uma página inteira dentro da tabela, (3) **reconhece sessão expirada** e (4) faz a tecla **Enter** funcionar sem recarregar a tela. Veja cada trecho:

#### Bloco 1 — Preparação

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `document.addEventListener("DOMContentLoaded", () => { ... })` | Manda o navegador executar o código só depois que o HTML terminou de carregar. | O script precisa que os formulários e tabelas já existam na página. | Em alguns casos o JavaScript rodaria antes da página existir e não encontraria nada. |
| `let temporizadorDebounce = null;` | Guarda o "cronômetro" do debounce. | Precisamos zerar o cronômetro anterior a cada tecla digitada. | Sem essa variável, não há como cancelar o cronômetro antigo e cada letra dispararia uma busca. |
| `const pedidosEmAndamento = {};` | Um "quadro de avisos" que anota qual pedido está em andamento para cada tabela. | Permite cancelar o pedido velho de uma tabela sem afetar a outra (na Aula 10 há duas tabelas na mesma tela). | O pedido antigo continuaria a viagem e poderia chegar **depois** do novo, mostrando dados desatualizados. |
| `function mostrarErro(container, mensagem)` | Escreve um aviso vermelho dentro do quadro da tabela. | Dá retorno claro ao usuário quando a busca falha. | A tabela ficaria apagada (opacidade) ou mostraria lixo, sem explicação. |

#### Bloco 2 — Montando o endereço da busca

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `const seletorAlvo = form.dataset.target \|\| "#container-tabela";` | Lê o atributo `data-target` do formulário (qual `<div>` atualizar). `\|\|` usa o texto padrão se o atributo não existir. | É o "endereço de entrega" do HTML novo. | Não sabemos qual parte da página atualizar. |
| `if (!container) return;` | Se a `<div>` não existe, aborta. | Evita erro de JavaScript por tentar mexer em algo inexistente. | Um erro no console quebra a busca. |
| `const url = new URL(window.location.href);` | Copia o endereço atual da página. | Preserva filtros de **outras** tabelas da mesma tela (Aula 10). | Cada busca apagaria os filtros de todas as outras tabelas. |
| `new FormData(form)` + `forEach(...)` | Lê todos os campos do formulário e os coloca na URL (`set`), removendo os vazios (`delete`). | Transforma o que o usuário digitou em `?q=Projetor&per_page=8`. | A busca não levaria nenhum filtro ao servidor. |
| `url.searchParams.set(paramPagina, pagina)` | Define o número da página, usando o nome de parâmetro específico da tabela (`data-page-param`). | Cada tabela pagina de forma independente. | Duas tabelas mudariam de página ao mesmo tempo. |

#### Bloco 3 — O pedido ao servidor (`fetch`) e os cuidados novos

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `pedidosEmAndamento[seletorAlvo].abort()` | Cancela o pedido anterior da mesma tabela, se ainda estiver a caminho. | Imagine pedir um café e, logo em seguida, **trocar o pedido**: o balcão cancela o primeiro. Assim, só a resposta mais recente aparece. | Respostas fora de ordem podem mostrar o resultado da busca "Pro" depois do de "Projetor". |
| `const controlador = new AbortController();` | Cria o "botão de cancelar" deste novo pedido. | Passado ao `fetch` como `signal`, permite cancelá-lo depois. | Sem ele, `abort()` não existe. |
| `fetch(url, {headers: {"X-Requested-With": "XMLHttpRequest"}, signal: ...})` | Faz o pedido em segundo plano e avisa ao servidor que é uma chamada do JavaScript. | O cabeçalho faz o servidor devolver JSON em caso de erro e **só o conteúdo da página** (veja a seção 8.1). | O servidor devolveria a página completa, e o erro de login viraria um redirecionamento HTML. |
| `if (resposta.status === 401 \|\| resposta.redirected) { window.location.reload(); return null; }` | Se a sessão expirou, recarrega a página inteira. | O servidor então redireciona para o login, e o usuário entende o que houve. | O texto de erro (ou a tela de login inteira) seria despejado dentro da tabela. |
| `if (!resposta.ok) throw new Error(...)` | Qualquer erro (403, 404, 500) vira uma exceção. | Direciona todos os problemas para o mesmo tratamento. | Páginas de erro seriam exibidas como se fossem dados da tabela. |
| `docTemp.querySelector(seletorAlvo)` + `container.innerHTML = novoConteudo.innerHTML` | Recorta do HTML recebido apenas o interior da `<div>` da tabela e o troca na tela. | A caixa de busca não é tocada, então o cursor continua onde estava. | A página inteira piscaria a cada letra digitada. |
| `if (!novoConteudo) throw new Error(...)` | Se a resposta não contém a `<div>` esperada, é um erro. | Antes, o código despejava a resposta inteira dentro da tabela, o que podia mostrar até uma página de login completa. | Voltaria o "HTML dentro de HTML" quebrando a tela. |
| `window.history.replaceState(...)` | Atualiza a barra de endereços sem recarregar. | Permite copiar o link ou apertar `F5` mantendo a busca. | A URL ficaria sempre igual, e `F5` perderia o filtro. |
| `.catch((erro) => { if (erro.name === "AbortError") return; mostrarErro(...) })` | Captura qualquer falha. Um `AbortError` é só o cancelamento proposital, então é ignorado. | Dá uma mensagem amigável quando a rede cai ou o servidor falha. | Qualquer falha deixaria a tabela "congelada" sem explicação. |
| `.finally(() => { if (pedidosEmAndamento[...] === controlador) container.classList.remove("opacity-60"); })` | Tira o efeito de "carregando" só se este for o pedido **mais recente**. | Evita que o pedido cancelado "acenda" a tabela enquanto o novo ainda está carregando. | A tabela ficaria acinzentada para sempre (ou piscaria entre pedidos). |

#### Bloco 4 — Os "ouvidos" da página (eventos)

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `document.body.addEventListener("input", ...)` + `setTimeout(..., 300)` | Escuta a digitação e só busca depois de 300 ms de pausa (*debounce*). | Poupa o servidor de dezenas de consultas por palavra. | A cada letra, uma consulta ao MySQL. |
| `document.body.addEventListener("change", ...)` | Escuta mudanças em `<select>` e `<input type="date">`. | Nessas caixas não há "digitação"; a busca deve ser imediata. | Mudar o status ou a data não atualizaria a tabela. |
| `document.body.addEventListener("click", ...)` + `.closest(".js-btn-pagina")` | Escuta cliques em **qualquer** lugar e reage só se o clique foi num botão de página. Isso é a *delegação de eventos* (veja o Desafio 3). | Os botões são destruídos e recriados a cada troca de página; o `body` permanece. | Depois da primeira troca de página, os botões novos não responderiam mais. |
| `document.body.addEventListener("submit", ...)` + `evento.preventDefault()` | Intercepta o envio do formulário de filtros (tecla Enter ou botão). | Antes, apertar Enter fazia a página recarregar inteira e podia perder filtros de outras tabelas. | Enter recarregaria a página inteira. |

---

## 8. O "Contrato" das 4 Classes CSS do Nosso Motor Dinâmico

Repare que o `tabela_dinamica.js` é controlado apenas por **classes CSS começando com `.js-`** e atributos `data-`. Isso significa que, nas Aulas 07, 08, 09 e 10, nós **não precisaremos escrever mais nenhuma linha de JavaScript**! Bastará colocar essas classes nos formulários HTML:

| Classe / Atributo no HTML | Onde Colocar | O que o `tabela_dinamica.js` Faz Automaticamente |
| :--- | :--- | :--- |
| **`class="js-form-filtro"`** | Na tag `<form>` da barra de pesquisa. | Identifica que aquele formulário controla uma tabela dinâmica. |
| **`data-target="#id-da-div"`** | Na tag `<form>` e na macro `renderizar_paginacao`. | Diz exatamente qual `<div id="...">` deve ter o conteúdo trocado quando a resposta chegar. |
| **`class="js-busca-dinamica"`** | Nos campos `<input type="text">` ou `<input type="number">`. | Aplica o **Debounce de 300ms** ao digitar e atualiza a tabela voltando para a página 1. |
| **`class="js-filtro-imediato"`** | Nos campos `<select>` (status, itens por página) e `<input type="date">`. | Atualiza a tabela **imediatamente** (sem esperar 300ms) assim que o usuário escolhe uma opção no menu suspenso. |
| **`class="js-btn-pagina"`** | Já vem pronta dentro da macro `paginacao.html`. | Intercepta o clique nos botões *Anterior / 1 / 2 / Próxima* e carrega a página pedida sem recarregar a tela. |

---

## 8.1 Otimização: Entregar Só o "Recheio" nas Buscas Dinâmicas

### O problema (contextualização)
Quando você digita uma letra na busca, o JavaScript pede ao Flask a página `/salas/?q=P`. Hoje o Flask responde com a página **inteira**: `<head>` com o Tailwind, menu lateral, mensagens, scripts... e o JavaScript, depois, **joga fora tudo** e aproveita apenas o interior da `<div>` da tabela.

> **Analogia da pizza:** é como pedir uma pizza e receber **a mesa, a toalha, os talheres e a pizza**, só para você pegar a pizza e devolver o resto. O ideal é o entregador trazer só o que foi pedido.

Existe ainda um efeito colateral desagradável: ao desenhar o menu lateral e a barra de mensagens, o Flask **consome as mensagens flash** (aquelas que aparecem uma única vez). Uma busca dinâmica poderia "gastar" uma mensagem que deveria aparecer para o usuário.

### A solução: dois "moldes pai" e um interruptor
Vamos criar um segundo molde, **`app/templates/base_parcial.html`**, que contém **somente** o bloco de conteúdo. As páginas de listagem passarão a herdar dele quando o pedido vier do JavaScript, e do `base.html` normal quando vier do navegador.

**Passo 1 — Crie o arquivo `app/templates/base_parcial.html`:**

```html
{# app/templates/base_parcial.html #}
{# Molde mínimo usado pelas buscas dinâmicas: devolve apenas o conteúdo da página #}
{% block conteudo %}{% endblock %}
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `{# ... #}` | Comentário do Jinja2: **não** aparece no HTML enviado ao navegador (diferente do `<!-- -->`). | Documenta o arquivo sem aumentar a resposta. | Nada muda no funcionamento; só perde a explicação. |
| `{% block conteudo %}{% endblock %}` | Abre a mesma "janela" `conteudo` que existe no `base.html`. | As páginas filhas preenchem esta janela, mas aqui **não há menu, nem `<head>`, nem scripts** ao redor. | As páginas filhas não teriam onde encaixar o conteúdo e a resposta viria vazia. |

**Passo 2 — Atualize o `app/__init__.py`.** Primeiro importe também o objeto `request` no topo (`from flask import Flask, render_template, redirect, url_for, request`) e depois acrescente uma variável ao `context_processor` que já existe:

```python
    @app.context_processor
    def injetar_utilitarios():
        # O nosso JavaScript avisa que é uma busca dinâmica com este cabeçalho
        requisicao_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        return {
            "tem_permissao": tem_permissao,
            "csrf_token": obter_token_csrf,
            "rota_inicial": rota_inicial,
            "layout": "base_parcial.html" if requisicao_ajax else "base.html",
        }
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `requisicao_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"` | Verdadeiro se o pedido veio do nosso `fetch`, que envia esse cabeçalho. | É a "senha" que distingue o navegador (página completa) do JavaScript (só o recheio). | Todos os pedidos seriam tratados da mesma forma e a otimização não aconteceria. |
| `"layout": "base_parcial.html" if requisicao_ajax else "base.html"` | Escolhe qual molde usar e o entrega aos templates na variável `layout`. | As páginas de listagem escrevem `{% extends layout %}` e herdam do molde certo automaticamente. | Sem a variável `layout`, `{% extends layout %}` falha com erro de template. |

**Passo 3 — Nas aulas 07 a 10**, as páginas de **listagem** começarão com `{% extends layout %}` (sem aspas!) em vez de `{% extends "base.html" %}`. Sem aspas, o Jinja2 entende que `layout` é uma **variável** cujo valor define qual arquivo herdar.

> 📌 **Atenção:** só as páginas com busca dinâmica usam `layout`. Login, perfil, formulários e telas de erro continuam com `{% extends "base.html" %}`, pois nunca são pedidas pelo JavaScript.

---

## 9. Testando o Motor de Paginação (`paginar_consulta`) na Prática!

Quer ver o dicionário do nosso motor `paginar_consulta` funcionando ao vivo no navegador antes mesmo de construirmos as telas completas de Salas na Aula 07?

Como o nosso banco MySQL já tem **10 salas cadastradas** pelo `seed_db.py`, podemos fazer um teste rápido de 1 minuto no esqueleto provisório de `app/blueprints/salas.py` (ou testar via JSON):

### Teste Rápido no Terminal / Navegador:
Abra o terminal interativo do Python dentro da pasta do projeto (com `venv` ativo) ou observe como `paginar_consulta` responde quando pedimos **5 salas por página**:

```bash
python -c "from app import create_app; from app.utils.pagination import paginar_consulta; app = create_app(); ctx = app.app_context(); ctx.push(); res = paginar_consulta('SELECT codigo, nome, capacidade FROM salas', pagina=1, por_pagina=5, ordenacao='codigo ASC'); print('Total de salas:', res['total_registros'], '| Total de paginas:', res['total_paginas'], '| Paginas visiveis:', res['paginas_visiveis']); print('Salas da Pagina 1:', [s['codigo'] for s in res['itens']])"
```

Ao executar essa linha no seu terminal, você verá imediatamente o motor consultando o MySQL e respondendo:

```text
Total de salas: 10 | Total de paginas: 2 | Paginas visiveis: [1, 2]
Salas da Pagina 1: ['AUD-201', 'EST-501', 'LAB-101', 'LAB-102', 'LAB-103']
```

E se você mudar `pagina=1` para `pagina=2` no comando acima, verá a segunda metade das salas (`['MIN-202', 'REU-301', 'REU-302', 'SAL-401', 'SAL-402']`)!

---

## 10. Guia de Sobrevivência no Laboratório (Erros Comuns na Aula 06)

| Sintoma / Mensagem de Erro | Causa Mais Provável | Como Resolver Rapidamente |
| :--- | :--- | :--- |
| `jinja2.exceptions.TemplateNotFound: components/paginacao.html` | O arquivo `paginacao.html` foi salvo direto em `app/templates/` em vez da subpasta `app/templates/components/`. | Verifique se o arquivo está exatamente em `app/templates/components/paginacao.html`. |
| Digito na barra de pesquisa nas próximas aulas, mas nada acontece (preciso apertar `Enter`). | O arquivo `tabela_dinamica.js` está no lugar errado ou faltou a classe `js-busca-dinamica` no `<input>` e `js-form-filtro` no `<form>`. | Abra o Inspecionar Elemento do navegador (`F12` $\rightarrow$ aba *Console* ou *Network*) e verifique se `static/js/tabela_dinamica.js` carregou com status `200`. |
| Ao buscar, a tabela some e aparece em vermelho *"Não foi possível atualizar a tabela..."*. | O servidor respondeu com erro (veja o terminal do Flask) ou a resposta não contém a `<div>` cujo `id` está no `data-target`. | Leia o erro no terminal onde roda o `python run.py` e confira se `data-target`, o `id` da `<div>` e o argumento da macro são idênticos. |
| `jinja2.exceptions.UndefinedError: 'layout' is undefined` | A variável `layout` não foi adicionada ao `context_processor` (seção 8.1). | Atualize `injetar_utilitarios()` no `app/__init__.py` com a chave `"layout"`. |
| `mysql.connector.errors.ProgrammingError: Every derived table must have its own alias` | Ao modificar `sql_contagem` em `pagination.py`, foi removido o trecho `AS subconsulta_total` após os parênteses. | No MySQL, toda subconsulta dentro de um `FROM (...)` exige obrigatoriamente um apelido (`AS subconsulta_total`) no final. |

---

## 11. Exercícios Práticos de Fixação

1. **Desafio 1 (Cálculo Manual de `OFFSET`):** Suponha que a tabela de reservas tenha **43 registros** e o usuário selecionou **`per_page = 10`** (10 registros por página). Responda:
   * Quantas páginas existirão no total (`total_paginas`)?
   * Qual será o valor do `OFFSET` quando o usuário clicar na **Página 4**?
   * Quais serão os valores de `inicio_item` e `fim_item` na **Página 5** (a última página)?
2. **Desafio 2 (Adicionando Opção de 15 Itens por Página):** Olhe para a constante `VALORES_POR_PAGINA_PERMITIDOS` no topo de `app/utils/pagination.py`. O que acontece se um usuário tentar acessar `?per_page=15` hoje? Como você permitiria oficialmente a opção de `15` itens por página no validador?
3. **Desafio 3 (Entendendo a Delegação de Eventos no JS):** No arquivo `tabela_dinamica.js`, por que anexamos o `addEventListener("click", ...)` no `document.body` em vez de anexar diretamente em cada botão `.js-btn-pagina`?

<details>
<summary><strong>💡 Clique aqui para ver o Gabarito Comentado dos Exercícios</strong></summary>

**1. Resposta do Desafio 1:**
* **Total de páginas:** $\lceil 43 \div 10 \rceil = \mathbf{5}$ páginas (`math.ceil(43 / 10)`).
* **`OFFSET` na Página 4:** $(4 - 1) \times 10 = \mathbf{30}$ (pula os 30 primeiros registros e mostra do 31º ao 40º).
* **Na Página 5 (última):** O `OFFSET` será $(5 - 1) \times 10 = 40$. Logo, `inicio_item = 40 + 1 = 41` e `fim_item = min(40 + 10, 43) = 43` (*"Exibindo 41 a 43 de 43 registros"*).

**2. Resposta do Desafio 2:**
* Hoje, como `15` não está na tupla `VALORES_POR_PAGINA_PERMITIDOS = (5, 8, 10, 20, 50)`, a função `validar_por_pagina()` ignora o `15` e devolve o padrão `8` (`ITEMS_PER_PAGE`). Para liberar `15`, basta incluí-lo na tupla: `VALORES_POR_PAGINA_PERMITIDOS = (5, 8, 10, 15, 20, 50)`.

**3. Resposta do Desafio 3:**
* Isso se chama **Event Delegation (Delegação de Eventos)**! Quando o `fetch()` substitui o HTML de `#container-tabela` por uma nova página, os botões antigos de paginação são destruídos e novos botões são criados no lugar. Se o evento de clique estivesse preso nos botões antigos, eles parariam de funcionar após a primeira troca de página! Como o evento está no `document.body` (que nunca é destruído), ele continua escutando os cliques em qualquer botão `.js-btn-pagina` novo que surgir na tela!
</details>

---

## O Que Vem a Seguir?

Nosso motor universal de paginação e busca dinâmica está pronto! Agora construir os módulos do sistema será incrivelmente rápido e prazeroso.

Na **Aula 07**, vamos inaugurar esse motor construindo o **Módulo Completo de Catálogo de Salas (CRUD)**: você criará a listagem de salas com filtro instantâneo por código, bloco, equipamentos e capacidade mínima, o formulário unificado de cadastro/edição e a exclusão segura protegida pela permissão `salas.excluir`!

---
<!-- nav -->
| Anterior | Índice | Próxima |
| :--- | :---: | ---: |
| [← Aula 05 — Autenticação e Permissões](./aula_05_autenticacao_sessoes_blueprints_acesso.md) | [📚 Índice do Curso](./README.md) | [Aula 07 — Módulo Catálogo de Salas →](./aula_07_modulo_catalogo_salas_crud.md) |