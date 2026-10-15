# Aula 08 — Módulo de Usuários e Matriz Visual de Permissões Personalizadas

Na **Aula 07**, construímos nosso primeiro CRUD completo com paginação e pesquisa dinâmica: o **Catálogo de Salas**. Lá, todas as operações aconteciam sobre uma única tabela (`salas`).

Agora vamos dar um passo além na sua formação como desenvolvedor(a) web! Nesta **Aula 08**, vamos construir o **Módulo de Gestão de Usuários e a Matriz Visual de Permissões Personalizadas** (`app/blueprints/usuarios.py` e seus 3 templates HTML).

Este módulo é especial porque ensina a resolver um dos desafios mais comuns do mercado de trabalho: **como cadastrar e editar um relacionamento Muitos-para-Muitos (`N:M`) usando múltiplos *checkboxes* na tela!** Você vai aprender:
1. Por que usar **`LEFT JOIN`** com `COUNT(...)` e `GROUP BY` para listar usuários sem esconder quem tem zero permissões.
2. Como capturar várias caixinhas marcadas (*checkboxes*) no Flask usando **`request.form.getlist()`**.
3. Como usar o `id` recém-gerado pelo MySQL (`novo_id`) para gravar dados em duas tabelas seguidas (`usuarios` $\rightarrow$ `usuario_permissoes`) **dentro de uma transação**.
4. Como funciona a **Sincronização por Diferença de Conjuntos** (`para_remover` e `para_adicionar`) que atualiza permissões sem perder o histórico.
5. Como impedir que alguém use o cadastro de usuários para **dar a si mesmo mais poder** do que deveria (escalada de privilégio).
6. Duas formas elegantes de agrupar dados na tela: via dicionário Python (`setdefault`) e via filtro Jinja2 (`|groupby('modulo')`).

---

## 1. As 3 Rotas e as 3 Permissões do Módulo de Usuários

Vamos observar como as rotas de `app/blueprints/usuarios.py` se conectam às chaves de permissão que criamos para o módulo de **Usuários**:

| Rota no Flask | Método HTTP | Função Python | Permissão Exigida | O que Faz no Sistema |
| :--- | :---: | :--- | :--- | :--- |
| `/usuarios/` | `GET` | `listar()` | `usuarios.visualizar` | Lista todos os usuários com busca dinâmica, filtro de ativo/inativo e contagem de permissões. |
| `/usuarios/novo` | `GET`, `POST` | `criar()` | `usuarios.gerenciar` | Cadastra um novo usuário com senha criptografada e já grava suas permissões iniciais (livres para quem também tem `usuarios.permissoes`; perfil Solicitante para os demais). |
| `/usuarios/<id>/permissoes` | `GET`, `POST` | `gerenciar_permissoes()` | `usuarios.permissoes` | Abre a matriz de 13 permissões agrupadas por módulo para marcar/desmarcar acessos e ativar/bloquear a conta. |

> **Por que separar `usuarios.gerenciar` de `usuarios.permissoes`?**  
> Em muitas instituições, o setor de RH pode ter a permissão `usuarios.gerenciar` para cadastrar novos funcionários que acabaram de ser contratados, mas apenas a equipe de Governança de TI possui a chave `usuarios.permissoes` para promover alguém ou conceder poderes administrativos!

---

## 2. Entendendo a Lógica SQL e Python antes de Codificar

Antes de abrirmos o arquivo `app/blueprints/usuarios.py`, vamos dominar os quatro conceitos técnicos que tornam esse código tão poderoso:

### 2.1 — Por que usar `LEFT JOIN` (e não `INNER JOIN`) na Listagem de Usuários?
Na tela de listagem de usuários, queremos mostrar os dados de cada pessoa (`nome`, `email`, `setor`, `cargo_etiqueta`) **e também** uma coluna dizendo quantas permissões ativas ela possui (`total_permissoes`).

Veja a consulta SQL que usaremos:
```sql
SELECT u.id, u.nome, u.email, u.setor, u.cargo_etiqueta, u.ativo, u.criado_em,
       COUNT(up.permissao_id) AS total_permissoes
FROM usuarios u
LEFT JOIN usuario_permissoes up ON up.usuario_id = u.id
WHERE 1=1
GROUP BY u.id
```

* **O que aconteceria se usássemos `INNER JOIN` aqui?**  
  O `INNER JOIN` exige que o usuário exista nas duas tabelas ao mesmo tempo. Se você cadastrasse um usuário novo sem marcar nenhuma permissão (0 permissões), ele não teria nenhuma linha na tabela `usuario_permissoes` e **desapareceria da lista de usuários**!
* **Por que o `LEFT JOIN` resolve isso?**  
  O `LEFT JOIN` preserva **100% das linhas da tabela da esquerda (`usuarios`)**, mesmo que não haja nenhuma correspondência na tabela da direita (`usuario_permissoes`). E como `COUNT(up.permissao_id)` conta apenas valores não-nulos, um usuário sem permissões aparece normalmente na tabela exibindo **`0 chaves`**!

---

### 2.2 — `request.form.get()` vs. `request.form.getlist()` (O Segredo dos Checkboxes!)
Nos formulários de Login e de Salas, cada campo tinha um atributo `name` único (`name="email"`, `name="capacidade"`). Por isso usávamos `request.form.get("nome_do_campo")`, que devolve uma única *string*.

Já na nossa Matriz de Permissões, teremos **13 caixinhas de marcação (`<input type="checkbox">`)**, e todas elas terão o mesmo nome **`name="permissoes_ids"`**, mudando apenas o `value` com o ID de cada permissão (`value="1"`, `value="2"`, ..., `value="13"`):

```html
<input type="checkbox" name="permissoes_ids" value="1"> Visualizar Salas
<input type="checkbox" name="permissoes_ids" value="5"> Visualizar Reservas
<input type="checkbox" name="permissoes_ids" value="6"> Solicitar Reserva
```

* Se o usuário marcar essas 3 caixinhas e você usar `request.form.get("permissoes_ids")` no Python, o Flask devolverá **apenas a primeira** (`"1"`) e ignorará todas as outras!
* Quando usamos **`request.form.getlist("permissoes_ids")`**, o Flask captura **todas** as caixinhas marcadas e nos entrega uma **lista Python completa**: `['1', '5', '6']`! E se nenhuma caixinha for marcada, ele devolve uma lista vazia `[]` sem dar erro.

---

### 2.3 — Gravando em Duas Tabelas ao Criar um Usuário (`novo_id` e `transacao()`)
Quando cadastramos um usuário novo na rota `criar()`, precisamos gravar dados em **dois lugares**:
1. Primeiro, fazemos o `INSERT INTO usuarios ...`.
2. O `cursor.lastrowid` devolve o número de identificação que o MySQL acabou de gerar (por exemplo, `novo_id = 4`).
3. Com o `novo_id` na mão, fazemos um laço inserindo os pares `(novo_id, permissao_id)` na tabela `usuario_permissoes`.

> **Analogia da matrícula:** matricular um aluno envolve dois papéis: a **ficha do aluno** e a **lista de disciplinas**. Se a secretaria arquivar a ficha e o sistema cair antes de registrar as disciplinas, o aluno existe mas não pode assistir a nenhuma aula, um "meio-cadastro". Por isso os dois passos precisam estar no **mesmo bloco indivisível**: a `transacao()` que criamos na Aula 04. Ou o usuário nasce **com** as permissões, ou **nada** é gravado.

Antes, o código confirmava o usuário primeiro (`execute_write`) e as permissões depois; se a segunda parte falhasse, sobrava um usuário sem permissões. Agora tudo acontece dentro de um único `with transacao() as cursor:`.

---

### 2.4 — Como Atualizar Permissões Sem Perder o Histórico? (Comparando Conjuntos)
Imagine que o Carlos Gestor tinha **9 permissões** marcadas. O administrador abre a tela de permissões do Carlos, desmarca 2 caixinhas antigas, marca 1 caixinha nova e clica em **Salvar**.

A primeira ideia seria "apagar tudo e inserir de novo". Só que isso tem um efeito colateral: a coluna `concedido_em` (a data em que cada permissão foi concedida) é **recriada para todas**, inclusive para as 8 que não mudaram! A tela "Meu Perfil" passaria a mostrar a data de hoje em tudo, perdendo a história real.

> **Analogia da lista de compras:** se você já tem 10 itens no carrinho e quer trocar 2, você não esvazia o carrinho para colocar tudo de volta. Você **remove os 2** e **adiciona os novos**.

Usamos a matemática de **conjuntos** (que você viu na Aula 05 com `set`):
* `para_remover = ids_atuais - novos_ids` → o que **estava** marcado e **não está mais**.
* `para_adicionar = novos_ids - ids_atuais` → o que **não estava** marcado e **agora está**.

Dentro de uma única `transacao()`:
1. Atualizamos os dados básicos do usuário (`UPDATE usuarios SET cargo_etiqueta = %s, ativo = %s WHERE id = %s`);
2. Apagamos **somente** as ligações em `para_remover`;
3. Inserimos **somente** as ligações em `para_adicionar`;
4. O `commit` acontece sozinho ao final do bloco `with`. Como ele só ocorre no fim, a troca é atômica (instantânea e indivisível).

---

### 2.5 — A Regra Que Faltava: Quem Pode Dar Poderes a Quem?
Na seção 1 dissemos que `usuarios.gerenciar` (cadastrar) e `usuarios.permissoes` (configurar permissões) são chaves **separadas** de propósito: o RH cadastra funcionários, mas só a Governança de TI promove alguém.

Mas havia uma brecha: na tela de cadastro aparecia a matriz com as 13 permissões para **qualquer** pessoa com `usuarios.gerenciar`. Alguém do RH poderia criar um usuário com **todas** as chaves marcadas e, depois, logar com ele: virou administrador sem ter a permissão de configurar permissões!

> **Analogia do chaveiro:** o atendente da portaria pode **cadastrar um visitante novo**, mas quem decide quais portas o visitante abre é o chaveiro-chefe. Se o atendente pudesse entregar qualquer chave, a regra do chaveiro-chefe seria inútil.

**Nossa regra:** quem tem **apenas** `usuarios.gerenciar` cria o usuário com o **perfil básico de Solicitante** (3 permissões fixas, escolhidas pelo servidor). Só quem **também** tem `usuarios.permissoes` vê e usa a matriz de checkboxes no cadastro. E, como a decisão é do servidor, adulterar o formulário no navegador não adianta.

---

## 3. Codificando o Blueprint de Usuários (`app/blueprints/usuarios.py`)

Primeiro, acrescente **ao final** do arquivo `app/utils/validacao.py` (criado na Aula 07) duas novidades:

```python
# Formato básico de e-mail: algo@dominio.ext, sem espaços
PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def lista_de_inteiros(textos):
    """Converte uma lista de textos em um conjunto de inteiros, ignorando o que não for número."""
    numeros = set()
    for texto in textos:
        if texto.isascii() and texto.isdigit():
            numeros.add(int(texto))
    return numeros
```

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")` | Molde de e-mail. Leitura: `[^@\s]+` = um ou mais caracteres que **não** sejam `@` nem espaço; depois `@`; depois mais um bloco assim; depois um ponto (`\.`) e mais um bloco (a extensão, como `com`). | Uma conferência simples e suficiente para barrar textos óbvios como `joao`, `a@b` ou `x y@z.com`. | Qualquer texto seria aceito como e-mail. |
| `def lista_de_inteiros(textos)` | Recebe a lista de textos do `request.form.getlist(...)` (por exemplo `["1", "5", "abc"]`). | Os checkboxes chegam como **texto**, e alguém pode adulterar os valores. | `int("abc")` derrubaria a página com erro 500. |
| `numeros = set()` | Conjunto vazio. | Conjuntos não repetem valores e permitem as operações `-` e `&` que usaremos. | Com lista, `1` marcado duas vezes seria gravado duas vezes. |
| `if texto.isascii() and texto.isdigit():` | Só aceita textos formados por dígitos de 0 a 9. | `isdigit()` sozinho aceita símbolos como `²`, que o `int()` não converte. | Alguém enviaria `²` e provocaria um erro 500. |
| `numeros.add(int(texto))` | Converte para número e guarda. | Valor limpo e seguro. | Ficaríamos com textos no conjunto. |

Agora abra o arquivo **`app/blueprints/usuarios.py`** (substituindo o esqueleto provisório da Aula 05) e digite o código completo abaixo:

```python
# app/blueprints/usuarios.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from werkzeug.security import generate_password_hash
from app.database import query_all, query_one, transacao
from app.utils.security import permissao_obrigatoria, tem_permissao
from app.utils.pagination import obter_parametros_listagem, paginar_consulta
from app.utils.validacao import PADRAO_EMAIL, lista_de_inteiros

usuarios_bp = Blueprint("usuarios", __name__, url_prefix="/usuarios")

# Perfil básico "Solicitante": é o que recebe quem cadastra um usuário sem poder dar permissões
PERMISSOES_PADRAO_SOLICITANTE = ("salas.visualizar", "reservas.visualizar", "reservas.criar")


@usuarios_bp.route("/")
@permissao_obrigatoria("usuarios.visualizar")
def listar():
    busca, pagina, por_pagina = obter_parametros_listagem()
    status_filtro = request.args.get("ativo", "")

    sql = """
        SELECT u.id, u.nome, u.email, u.setor, u.cargo_etiqueta, u.ativo, u.criado_em,
               COUNT(up.permissao_id) AS total_permissoes
        FROM usuarios u
        LEFT JOIN usuario_permissoes up ON up.usuario_id = u.id
        WHERE 1=1
    """
    params = []

    if busca:
        sql += " AND (u.nome LIKE %s OR u.email LIKE %s OR u.setor LIKE %s OR u.cargo_etiqueta LIKE %s)"
        termo = f"%{busca}%"
        params.extend([termo, termo, termo, termo])

    if status_filtro in ("0", "1"):
        sql += " AND u.ativo = %s"
        params.append(int(status_filtro))

    sql += " GROUP BY u.id"

    paginacao = paginar_consulta(
        sql_base=sql,
        params=params,
        pagina=pagina,
        por_pagina=por_pagina,
        ordenacao="u.nome ASC",
    )

    return render_template(
        "usuarios/index.html",
        paginacao=paginacao,
        busca=busca,
        status_filtro=status_filtro,
    )


@usuarios_bp.route("/novo", methods=["GET", "POST"])
@permissao_obrigatoria("usuarios.gerenciar")
def criar():
    todas_permissoes = query_all("SELECT * FROM permissoes ORDER BY modulo, nome")
    # Só quem TAMBÉM tem 'usuarios.permissoes' pode escolher as permissões iniciais
    pode_definir_permissoes = tem_permissao("usuarios.permissoes")

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip().lower()
        senha = request.form.get("senha", "")
        setor = request.form.get("setor", "").strip()
        cargo_etiqueta = request.form.get("cargo_etiqueta", "").strip()

        erros = []
        if not nome or len(nome) > 120:
            erros.append("Informe o nome completo (até 120 caracteres).")
        if not PADRAO_EMAIL.match(email) or len(email) > 150:
            erros.append("Informe um e-mail válido (até 150 caracteres).")
        if len(senha) < 6 or len(senha) > 128:
            erros.append("A senha deve ter entre 6 e 128 caracteres.")
        if not setor or len(setor) > 80:
            erros.append("Informe o setor (até 80 caracteres).")
        if not cargo_etiqueta or len(cargo_etiqueta) > 60:
            erros.append("Informe a etiqueta de cargo (até 60 caracteres).")

        # O SERVIDOR decide quais permissões o novo usuário recebe (nunca confie só no formulário)
        if pode_definir_permissoes:
            ids_validos = {p["id"] for p in todas_permissoes}
            marcados = lista_de_inteiros(request.form.getlist("permissoes_ids"))
            permissoes_ids = sorted(marcados & ids_validos)
        else:
            permissoes_ids = [p["id"] for p in todas_permissoes if p["codigo"] in PERMISSOES_PADRAO_SOLICITANTE]

        if not erros and query_one("SELECT id FROM usuarios WHERE email = %s", (email,)):
            erros.append("Já existe um usuário cadastrado com este e-mail.")

        if erros:
            for erro in erros:
                flash(erro, "erro")
            return render_template(
                "usuarios/form.html", permissoes=todas_permissoes, dados=request.form,
                reenviado=True, pode_definir_permissoes=pode_definir_permissoes,
            )

        # Usuário + permissões na MESMA transação: ou grava tudo, ou não grava nada
        with transacao() as cursor:
            cursor.execute(
                """
                INSERT INTO usuarios (nome, email, senha_hash, setor, cargo_etiqueta, ativo)
                VALUES (%s, %s, %s, %s, %s, 1)
                """,
                (nome, email, generate_password_hash(senha), setor, cargo_etiqueta),
            )
            novo_id = cursor.lastrowid
            for pid in permissoes_ids:
                cursor.execute(
                    "INSERT INTO usuario_permissoes (usuario_id, permissao_id) VALUES (%s, %s)",
                    (novo_id, pid),
                )

        flash(f"Usuário '{nome}' criado com {len(permissoes_ids)} permissões!", "sucesso")
        return redirect(url_for("usuarios.listar"))

    return render_template(
        "usuarios/form.html", permissoes=todas_permissoes, dados=request.form,
        reenviado=False, pode_definir_permissoes=pode_definir_permissoes,
    )


@usuarios_bp.route("/<int:usuario_id>/permissoes", methods=["GET", "POST"])
@permissao_obrigatoria("usuarios.permissoes")
def gerenciar_permissoes(usuario_id):
    usuario = query_one("SELECT * FROM usuarios WHERE id = %s", (usuario_id,))
    if not usuario:
        flash("Usuário não encontrado.", "erro")
        return redirect(url_for("usuarios.listar"))

    todas_permissoes = query_all("SELECT * FROM permissoes ORDER BY modulo, nome")
    atuais = query_all(
        "SELECT permissao_id FROM usuario_permissoes WHERE usuario_id = %s",
        (usuario_id,),
    )
    ids_atuais = {linha["permissao_id"] for linha in atuais}

    if request.method == "POST":
        ids_validos = {p["id"] for p in todas_permissoes}
        novos_ids = lista_de_inteiros(request.form.getlist("permissoes_ids")) & ids_validos
        cargo_etiqueta = request.form.get("cargo_etiqueta", "").strip()
        ativo = 1 if request.form.get("ativo") == "1" else 0

        if not cargo_etiqueta or len(cargo_etiqueta) > 60:
            flash("Informe a etiqueta de cargo (até 60 caracteres).", "erro")
            return redirect(url_for("usuarios.gerenciar_permissoes", usuario_id=usuario_id))

        # Trava anti-autoexclusão: ninguém pode se trancar para fora do próprio painel
        if usuario_id == g.usuario["id"]:
            id_chave_mestra = next(p["id"] for p in todas_permissoes if p["codigo"] == "usuarios.permissoes")
            if ativo == 0 or id_chave_mestra not in novos_ids:
                flash(
                    "Por segurança, você não pode bloquear a sua própria conta "
                    "nem retirar de si a permissão 'usuarios.permissoes'.",
                    "aviso",
                )
                return redirect(url_for("usuarios.gerenciar_permissoes", usuario_id=usuario_id))

        # Só mexe no que mudou: assim o 'concedido_em' das permissões antigas é preservado
        para_remover = ids_atuais - novos_ids
        para_adicionar = novos_ids - ids_atuais

        with transacao() as cursor:
            cursor.execute(
                "UPDATE usuarios SET cargo_etiqueta = %s, ativo = %s WHERE id = %s",
                (cargo_etiqueta, ativo, usuario_id),
            )
            if para_remover:
                marcadores = ",".join(["%s"] * len(para_remover))
                cursor.execute(
                    f"DELETE FROM usuario_permissoes WHERE usuario_id = %s AND permissao_id IN ({marcadores})",
                    (usuario_id, *para_remover),
                )
            for pid in para_adicionar:
                cursor.execute(
                    "INSERT INTO usuario_permissoes (usuario_id, permissao_id) VALUES (%s, %s)",
                    (usuario_id, pid),
                )

        flash(f"Permissões personalizadas de {usuario['nome']} atualizadas com sucesso!", "sucesso")
        return redirect(url_for("usuarios.listar"))

    # Agrupa permissões por módulo para exibir em cards organizados no Tailwind CSS
    permissoes_por_modulo = {}
    for p in todas_permissoes:
        permissoes_por_modulo.setdefault(p["modulo"], []).append(p)

    return render_template(
        "usuarios/permissoes.html",
        usuario=usuario,
        permissoes_por_modulo=permissoes_por_modulo,
        ids_atuais=ids_atuais,
    )
```

### Linha por linha das novidades do `usuarios.py`

#### Imports e constante

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `from app.database import query_all, query_one, transacao` | Traz as ferramentas de banco, incluindo a `transacao()` da Aula 04. | Substitui o uso manual de `get_db()` e `cursor`. | `ImportError` ao iniciar. |
| `from app.utils.security import permissao_obrigatoria, tem_permissao` | Além do decorator, trazemos `tem_permissao` para consultar chaves **dentro** da função. | A rota `criar` decide o que fazer conforme as chaves de quem está logado. | `NameError` na rota `criar`. |
| `PERMISSOES_PADRAO_SOLICITANTE = (...)` | As 3 chaves do perfil básico, guardadas em uma constante. | Uma única definição; fácil de mudar. | O servidor não saberia quais permissões entregar a quem não pode escolher. |

#### Rota `criar()`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `pode_definir_permissoes = tem_permissao("usuarios.permissoes")` | `True` se quem está cadastrando também tem a "chave-mestra". | É a decisão central contra a escalada de privilégio (seção 2.5). | Voltamos à brecha: qualquer pessoa com `usuarios.gerenciar` cria um superusuário. |
| `if not PADRAO_EMAIL.match(email) or len(email) > 150:` | Valida o formato e o tamanho do e-mail. | `150` é o tamanho da coluna no banco. | E-mails inválidos ou longos demais gerariam erro do MySQL (tela 500). |
| `if len(senha) < 6 or len(senha) > 128:` | Exige de 6 a 128 caracteres. | O `minlength` do HTML pode ser burlado; o limite máximo evita abusos (senhas gigantes gastam processamento ao gerar o hash). | Senhas de 1 letra seriam aceitas. |
| `marcados = lista_de_inteiros(request.form.getlist("permissoes_ids"))` | Transforma os checkboxes marcados em um conjunto de números. | Entrada limpa. | Textos adulterados quebrariam a rota. |
| `permissoes_ids = sorted(marcados & ids_validos)` | O `&` é a **interseção** de conjuntos: só ficam os ids que existem de verdade no catálogo. | Impede gravar uma permissão inexistente (que causaria erro de chave estrangeira). | Um id inventado (`999`) geraria erro 500 no meio do cadastro. |
| `else: permissoes_ids = [p["id"] for p in todas_permissoes if p["codigo"] in PERMISSOES_PADRAO_SOLICITANTE]` | Para quem **não** pode escolher, o servidor mesmo define as 3 permissões básicas, ignorando o que veio no formulário. | Mesmo que alguém adultere o HTML marcando tudo, nada disso é lido. | A brecha de escalada de privilégio continua aberta. |
| `if not erros and query_one(...)` | Checa e-mail duplicado só se o resto está certo. | Poupa uma consulta e evita mensagens repetidas. | Funcionaria, mas faria consultas à toa. |
| `with transacao() as cursor:` | Abre o bloco indivisível (Aula 04). | Usuário e permissões gravados juntos. | Um erro no meio deixaria um usuário sem permissões. |
| `novo_id = cursor.lastrowid` | O id que o MySQL acabou de gerar para o usuário. | Os `INSERT` seguintes precisam dele para ligar as permissões. | Não saberíamos a quem pertencem as permissões. |
| `render_template(..., reenviado=True, pode_definir_permissoes=...)` | Ao reexibir o formulário após erro, avisa o template que é um reenvio. | Para manter os checkboxes que a pessoa marcou. | Os checkboxes voltariam ao padrão e perderiam a seleção. |

#### Rota `gerenciar_permissoes()`

| Linha | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `novos_ids = lista_de_inteiros(...) & ids_validos` | Conjunto de permissões marcadas, filtrado pelo catálogo. | Mesma proteção do cadastro. | Ids falsos causariam erro. |
| `if usuario_id == g.usuario["id"]:` | Verdadeiro quando a pessoa está editando **a própria** conta. | Só nesse caso existe o risco de se trancar para fora. | A regra bloquearia também a edição de outras pessoas. |
| `id_chave_mestra = next(p["id"] for p in todas_permissoes if p["codigo"] == "usuarios.permissoes")` | Procura, no catálogo, o `id` da chave `usuarios.permissoes`. `next(...)` pega o primeiro resultado do filtro. | Precisamos do número para saber se a pessoa a manteve marcada. | Não poderíamos conferir a retirada da própria chave. |
| `if ativo == 0 or id_chave_mestra not in novos_ids:` | Bloqueia desativar a si mesmo **ou** desmarcar a própria chave-mestra. | Evita o acidente do administrador que perde o acesso ao painel e não consegue consertar. | A única pessoa capaz de dar permissões poderia se bloquear por engano. |
| `para_remover = ids_atuais - novos_ids` | Subtração de conjuntos: o que tinha e não tem mais. | Só apagamos o que realmente foi desmarcado. | Apagaríamos todas e perderíamos o `concedido_em`. |
| `para_adicionar = novos_ids - ids_atuais` | O que não tinha e agora tem. | Só inserimos o novo. | Reinseriríamos as que já existem (erro de chave duplicada). |
| `if para_remover:` | Só executa o `DELETE` se houver o que remover. | `IN ()` vazio é um erro de sintaxe SQL. | Quando ninguém desmarcou nada, o SQL quebraria. |
| `marcadores = ",".join(["%s"] * len(para_remover))` | Gera um `%s` para cada item: três itens viram `"%s,%s,%s"`. | O número de itens muda; os valores continuam seguros (parametrizados). | Teríamos de colar números dentro do SQL (risco de SQL Injection). |
| `f"DELETE ... IN ({marcadores})"` com `(usuario_id, *para_remover)` | O `f"..."` só insere os marcadores (`%s`), e **nunca valores**. O `*` "espalha" os itens do conjunto como argumentos. | É seguro e flexível. | Não conseguiríamos apagar um número variável de linhas com uma única consulta. |

---

## 4. Criando os 3 Templates HTML do Módulo de Usuários

### Passo 4.1 — Template da Tabela de Usuários (`app/templates/usuarios/index.html`)

Assim como fizemos no Catálogo de Salas, este template importa a macro `renderizar_paginacao` e conecta o formulário de busca dinâmica ao container `#container-tabela-usuarios`.

Abra o arquivo **`app/templates/usuarios/index.html`** e digite o código abaixo:

```html
<!-- app/templates/usuarios/index.html -->
{% extends layout %}
{% from "components/paginacao.html" import renderizar_paginacao %}
{% block titulo %}Usuários e Permissões — SalaFácil{% endblock %}

{% block conteudo %}
<div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
    <div>
        <h2 class="text-2xl font-bold text-slate-900">Usuários & Permissões Personalizadas</h2>
        <p class="text-sm text-slate-500">Gerencie contas e configure permissões granulares por usuário</p>
    </div>
    {% if tem_permissao('usuarios.gerenciar') %}
    <a href="{{ url_for('usuarios.criar') }}"
       class="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-semibold rounded-xl shadow-sm transition">
        + Novo Usuário
    </a>
    {% endif %}
</div>

<!-- Barra de Pesquisa Dinâmica e Filtros -->
<form method="GET" action="{{ url_for('usuarios.listar') }}"
      data-target="#container-tabela-usuarios"
      class="js-form-filtro bg-white p-4 rounded-2xl shadow-sm border border-slate-200 mb-6 flex flex-col md:flex-row gap-4">
    <div class="flex-1">
        <input type="text" name="q" value="{{ busca }}"
               placeholder="Pesquisar dinamicamente por nome, e-mail, setor ou cargo..."
               class="js-busca-dinamica w-full px-4 py-2 rounded-xl border border-slate-300 focus:ring-2 focus:ring-indigo-500 outline-none text-sm">
    </div>
    <select name="ativo" class="js-filtro-imediato px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white">
        <option value="">Todos os Status</option>
        <option value="1" {% if status_filtro == '1' %}selected{% endif %}>Somente Ativos</option>
        <option value="0" {% if status_filtro == '0' %}selected{% endif %}>Somente Inativos</option>
    </select>
    <select name="per_page" class="js-filtro-imediato px-3 py-2 rounded-xl border border-slate-300 text-sm bg-white">
        {% for qtd in [5, 8, 10, 20] %}
        <option value="{{ qtd }}" {% if paginacao.por_pagina == qtd %}selected{% endif %}>{{ qtd }} por página</option>
        {% endfor %}
    </select>
</form>

<!-- Container da Tabela Paginada -->
<div id="container-tabela-usuarios" class="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
    <div class="overflow-x-auto">
        <table class="w-full text-left border-collapse">
            <thead>
                <tr class="bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-600 uppercase">
                    <th class="py-3.5 px-6">Nome / E-mail</th>
                    <th class="py-3.5 px-6">Setor</th>
                    <th class="py-3.5 px-6">Perfil Base</th>
                    <th class="py-3.5 px-6 text-center">Permissões Ativas</th>
                    <th class="py-3.5 px-6 text-center">Status</th>
                    <th class="py-3.5 px-6 text-right">Ações</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-slate-200 text-sm">
                {% for u in paginacao.itens %}
                <tr class="hover:bg-slate-50/80 transition">
                    <td class="py-4 px-6">
                        <p class="font-semibold text-slate-900">{{ u.nome }}</p>
                        <p class="text-xs text-slate-500">{{ u.email }}</p>
                    </td>
                    <td class="py-4 px-6 text-slate-700">{{ u.setor }}</td>
                    <td class="py-4 px-6">
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-indigo-50 text-indigo-700">
                            {{ u.cargo_etiqueta }}
                        </span>
                    </td>
                    <td class="py-4 px-6 text-center">
                        <span class="px-2.5 py-1 rounded-lg bg-slate-100 text-slate-800 font-bold text-xs">
                            {{ u.total_permissoes }} chaves
                        </span>
                    </td>
                    <td class="py-4 px-6 text-center">
                        {% if u.ativo %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-100 text-emerald-800">Ativo</span>
                        {% else %}
                        <span class="px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-100 text-rose-800">Inativo</span>
                        {% endif %}
                    </td>
                    <td class="py-4 px-6 text-right">
                        {% if tem_permissao('usuarios.permissoes') %}
                        <a href="{{ url_for('usuarios.gerenciar_permissoes', usuario_id=u.id) }}"
                           class="inline-flex items-center gap-1 px-3 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold transition">
                            🔐 Permissões
                        </a>
                        {% endif %}
                    </td>
                </tr>
                {% else %}
                <tr>
                    <td colspan="6" class="py-10 text-center text-slate-500">
                        Nenhum usuário encontrado para "{{ busca }}".
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    {{ renderizar_paginacao(paginacao, '#container-tabela-usuarios') }}
</div>
{% endblock %}
```

---

### Passo 4.2 — Template de Cadastro de Novo Usuário (`app/templates/usuarios/form.html`)

Na tela de criar um novo usuário, queremos exibir as 13 permissões separadas em **4 cartões visuais** (Módulo Salas, Módulo Reservas, Módulo Usuários e Módulo Relatórios).

#### Como o filtro `|groupby('modulo')` do Jinja2 faz isso em 1 linha?
Na rota `criar()`, passamos uma lista simples `permissoes=todas_permissoes`. No HTML, quando escrevemos:
```jinja2
{% for modulo, lista_permissoes in permissoes|groupby('modulo') %}
```
O próprio Jinja2 agrupa automaticamente os dicionários pela chave `'modulo'` e nos entrega o nome do módulo (`modulo`) e a sublista de permissões daquele módulo (`lista_permissoes`)!

Além disso, incluímos **3 botões rápidos de atalho** (*Padrão Solicitante*, *Marcar Todas* e *Limpar Seleção*) que marcam ou desmarcam os checkboxes na tela com uma linha de JavaScript para agilizar o trabalho do administrador.

Abra o arquivo **`app/templates/usuarios/form.html`** e digite o código abaixo:

```html
<!-- app/templates/usuarios/form.html -->
{% extends "base.html" %}
{% block titulo %}Novo Usuário — SalaFácil{% endblock %}

{% block conteudo %}
<div class="max-w-5xl mx-auto">
    <div class="mb-6 flex items-center justify-between">
        <div>
            <h2 class="text-2xl font-bold text-slate-900">Cadastrar Novo Usuário</h2>
            <p class="text-sm text-slate-500">Defina as credenciais de acesso e selecione as permissões personalizadas iniciais</p>
        </div>
        <a href="{{ url_for('usuarios.listar') }}" class="text-sm text-slate-600 hover:text-slate-900 font-medium">
            ← Voltar para Usuários
        </a>
    </div>

    <form method="POST" class="space-y-6">
        <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 grid grid-cols-1 md:grid-cols-2 gap-5">
            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">Nome Completo</label>
                <input type="text" name="nome" required maxlength="120" placeholder="Ex: Rodrigo Almeida"
                       value="{{ dados.get('nome', '') }}"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">E-mail Institucional</label>
                <input type="email" name="email" required maxlength="150" placeholder="rodrigo@salafacil.com"
                       value="{{ dados.get('email', '') }}"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">Senha Inicial</label>
                <input type="password" name="senha" required minlength="6" maxlength="128" placeholder="Mínimo de 6 caracteres"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div>
                <label class="block text-sm font-semibold text-slate-700 mb-1">Setor / Departamento</label>
                <input type="text" name="setor" required maxlength="80" value="{{ dados.get('setor', 'Docência') }}"
                       placeholder="Ex: Coordenação, TI, Docência"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>

            <div class="md:col-span-2">
                <label class="block text-sm font-semibold text-slate-700 mb-1">Etiqueta de Cargo / Perfil Base</label>
                <input type="text" name="cargo_etiqueta" required maxlength="60" value="{{ dados.get('cargo_etiqueta', 'Solicitante') }}"
                       placeholder="Ex: Solicitante, Gestor de Espaços, Coordenador"
                       class="w-full px-4 py-2.5 rounded-xl border border-slate-300 text-sm">
            </div>
        </div>

        {% if not pode_definir_permissoes %}
        <!-- Quem só tem 'usuarios.gerenciar' não escolhe permissões: o servidor aplica o perfil Solicitante -->
        <div class="bg-amber-50 border border-amber-200 text-amber-800 rounded-2xl p-5 text-sm">
            <p class="font-semibold">Permissões iniciais: perfil básico de Solicitante</p>
            <p class="mt-1">
                O novo usuário receberá as 3 permissões básicas (visualizar salas, visualizar reservas e solicitar reservas).
                Para conceder outras permissões, peça a quem possui a chave <code>usuarios.permissoes</code>
                que as ajuste depois do cadastro.
            </p>
        </div>
        {% else %}
        <!-- Seleção de Permissões Personalizadas Iniciais -->
        <div>
            <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 mb-3">
                <h3 class="text-base font-bold text-slate-900">Permissões Personalizadas Iniciais</h3>
                <div class="flex gap-2">
                    <button type="button"
                            onclick="document.querySelectorAll('.js-chk-perm').forEach(c => c.checked = ['salas.visualizar','reservas.visualizar','reservas.criar'].includes(c.dataset.codigo))"
                            class="px-3 py-1 rounded-lg bg-slate-200 hover:bg-slate-300 text-slate-700 text-xs font-semibold">
                        Padrão Solicitante
                    </button>
                    <button type="button"
                            onclick="document.querySelectorAll('.js-chk-perm').forEach(c => c.checked = true)"
                            class="px-3 py-1 rounded-lg bg-indigo-100 hover:bg-indigo-200 text-indigo-700 text-xs font-semibold">
                        Marcar Todas
                    </button>
                    <button type="button"
                            onclick="document.querySelectorAll('.js-chk-perm').forEach(c => c.checked = false)"
                            class="px-3 py-1 rounded-lg bg-rose-50 hover:bg-rose-100 text-rose-700 text-xs font-semibold">
                        Limpar Seleção
                    </button>
                </div>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                {% for modulo, lista_permissoes in permissoes|groupby('modulo') %}
                <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
                    <h4 class="font-bold text-base text-indigo-700 border-b border-slate-100 pb-3 mb-4">
                        Módulo: {{ modulo }}
                    </h4>
                    <div class="space-y-3">
                        {% for perm in lista_permissoes %}
                        <label class="flex items-start gap-3 p-2.5 rounded-xl hover:bg-slate-50 cursor-pointer border border-transparent hover:border-slate-200 transition">
                            <input type="checkbox" name="permissoes_ids" value="{{ perm.id }}"
                                   data-codigo="{{ perm.codigo }}"
                                   {% if (reenviado and perm.id|string in dados.getlist('permissoes_ids'))
                                      or (not reenviado and perm.codigo in ('salas.visualizar', 'reservas.visualizar', 'reservas.criar')) %}checked{% endif %}
                                   class="js-chk-perm mt-1 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500">
                            <div>
                                <p class="text-sm font-semibold text-slate-900">
                                    {{ perm.nome }}
                                    <code class="text-[11px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded ml-1">{{ perm.codigo }}</code>
                                </p>
                                <p class="text-xs text-slate-500">{{ perm.descricao }}</p>
                            </div>
                        </label>
                        {% endfor %}
                    </div>
                </div>
                {% endfor %}
            </div>
        </div>
        {% endif %}

        <div class="flex justify-end gap-3">
            <a href="{{ url_for('usuarios.listar') }}"
               class="px-5 py-2.5 rounded-xl bg-slate-100 hover:bg-slate-200 text-slate-700 text-sm font-semibold transition">
                Cancelar
            </a>
            <button type="submit"
                    class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-sm text-sm transition">
                Criar Usuário
            </button>
        </div>
    </form>
</div>
{% endblock %}
```

#### Linha por linha das novidades do `usuarios/form.html`

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `{% extends layout %}` no `index.html` | Herda o molde "completo" ou "parcial" conforme o pedido (Aula 06, seção 8.1). | Buscas dinâmicas leves. | Funciona, porém mais pesado e consumindo mensagens flash. |
| `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">` | A ficha numerada. | Todo `POST` exige. | O cadastro responde "formulário inválido". |
| `value="{{ dados.get('nome', '') }}"` (e os demais campos) | Reexibe o que a pessoa digitou após um erro; na primeira abertura, `dados` está vazio e o campo fica em branco (ou com o valor padrão, como `'Docência'`). | Evita redigitar tudo a cada erro. | O formulário volta vazio a cada erro. |
| A **senha** não tem `value=` | Por segurança, nunca devolvemos a senha ao navegador. | Evita que a senha fique visível no código-fonte da página. | A senha digitada ficaria exposta no HTML devolvido. |
| `{% if not pode_definir_permissoes %} ... {% else %} ... {% endif %}` | Mostra um aviso amarelo para quem só tem `usuarios.gerenciar`, e a matriz de checkboxes para quem também tem `usuarios.permissoes`. | O que a tela mostra combina com o que o servidor vai aceitar (seção 2.5). | A tela ofereceria opções que o servidor ignora, confundindo o usuário. |
| `{% if (reenviado and perm.id\|string in dados.getlist('permissoes_ids')) or (not reenviado and perm.codigo in (...)) %}checked{% endif %}` | Decide se cada checkbox nasce marcado. Em um **reenvio após erro** (`reenviado`), marca exatamente o que a pessoa tinha marcado; na **primeira abertura**, marca as 3 do perfil Solicitante. `perm.id\|string` converte o número em texto, pois `getlist` devolve textos. | Os checkboxes "lembram" a escolha sem perder o padrão sugerido. | Depois de um erro, todas as escolhas voltariam ao padrão. |

---

### Passo 4.3 — Template da Matriz de Permissões (`app/templates/usuarios/permissoes.html`)

Quando o administrador clica no botão **🔐 Permissões** de qualquer usuário na listagem, abrimos a rota `/usuarios/<usuario_id>/permissoes`.

Repare como sabemos quais caixinhas já devem vir marcadas (`checked`) quando a página abre:
1. No Python (`gerenciar_permissoes`), buscamos os IDs das permissões atuais do usuário e guardamos em um conjunto: `ids_atuais = {linha["permissao_id"] for linha in atuais}`.
2. No HTML abaixo, dentro de cada `<input type="checkbox">`, fazemos a pergunta:
   `{% if perm.id in ids_atuais %}checked{% endif %}`!

Abra o arquivo **`app/templates/usuarios/permissoes.html`** e digite o código abaixo:

```html
<!-- app/templates/usuarios/permissoes.html -->
{% extends "base.html" %}
{% block titulo %}Permissões de {{ usuario.nome }} — SalaFácil{% endblock %}

{% block conteudo %}
<div class="mb-6 flex items-center justify-between">
    <div>
        <h2 class="text-2xl font-bold text-slate-900">Permissões Personalizadas: {{ usuario.nome }}</h2>
        <p class="text-sm text-slate-500">{{ usuario.email }} • Setor: {{ usuario.setor }}</p>
    </div>
    <a href="{{ url_for('usuarios.listar') }}" class="text-sm text-slate-600 hover:text-slate-900 font-medium">
        ← Voltar para Usuários
    </a>
</div>

<form method="POST" class="space-y-6">
    <input type="hidden" name="csrf_token" value="{{ csrf_token() }}">
    <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200 grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1">Etiqueta de Cargo / Função</label>
            <input type="text" name="cargo_etiqueta" required maxlength="60" value="{{ usuario.cargo_etiqueta }}"
                   class="w-full px-4 py-2 rounded-xl border border-slate-300 text-sm">
        </div>
        <div>
            <label class="block text-sm font-semibold text-slate-700 mb-1">Status da Conta</label>
            <select name="ativo" class="w-full px-4 py-2 rounded-xl border border-slate-300 text-sm bg-white">
                <option value="1" {% if usuario.ativo %}selected{% endif %}>Conta Ativa (Pode fazer login)</option>
                <option value="0" {% if not usuario.ativo %}selected{% endif %}>Conta Bloqueada / Inativa</option>
            </select>
        </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        {% for modulo, lista_permissoes in permissoes_por_modulo.items() %}
        <div class="bg-white p-6 rounded-2xl shadow-sm border border-slate-200">
            <h3 class="font-bold text-base text-indigo-700 border-b border-slate-100 pb-3 mb-4">
                Módulo: {{ modulo }}
            </h3>
            <div class="space-y-3">
                {% for perm in lista_permissoes %}
                <label class="flex items-start gap-3 p-2.5 rounded-xl hover:bg-slate-50 cursor-pointer border border-transparent hover:border-slate-200 transition">
                    <input type="checkbox" name="permissoes_ids" value="{{ perm.id }}"
                           {% if perm.id in ids_atuais %}checked{% endif %}
                           class="mt-1 h-4 w-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500">
                    <div>
                        <p class="text-sm font-semibold text-slate-900">
                            {{ perm.nome }}
                            <code class="text-[11px] bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded ml-1">{{ perm.codigo }}</code>
                        </p>
                        <p class="text-xs text-slate-500">{{ perm.descricao }}</p>
                    </div>
                </label>
                {% endfor %}
            </div>
        </div>
        {% endfor %}
    </div>

    <div class="flex justify-end gap-3">
        <button type="submit"
                class="px-6 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-xl shadow-sm text-sm transition">
            Salvar Permissões Personalizadas
        </button>
    </div>
</form>
{% endblock %}
```

---

## 5. O Grande Teste ao Vivo: Permissões em Tempo Real em Duas Janelas!

Esta é uma das demonstrações mais legais de todo o curso. Com o `python run.py` rodando no terminal, siga este passo a passo para ver o poder da arquitetura que construímos:

1. **Na Janela Normal do Navegador (Como Administradora):**  
   Faça login com **`admin@salafacil.com`** (senha `123456`) e clique em **👥 Usuários & Permissões** no menu lateral.
   * Teste a barra de pesquisa digitando `Docência` ou `Infraestrutura` para ver o filtro dinâmico funcionando.
2. **Na Janela Anônima do Navegador (`Ctrl + Shift + N` — Como Beatriz):**  
   Abra uma janela anônima (que tem um cookie de sessão independente!), acesse `http://127.0.0.1:5000` e faça login com **`beatriz@salafacil.com`** (senha `123456`).
   * Clique em **🏢 Catálogo de Salas** na janela da Beatriz. Repare que na coluna *Ações* ela vê apenas o botão **Reservar** (ela **não** tem o botão **Editar**).
3. **Concedendo Permissão em Tempo Real:**  
   Volte para a janela da **Administradora**, clique no botão **🔐 Permissões** na linha da `Beatriz Professora`, marque a caixinha **`Editar Salas (salas.editar)`** e clique em **Salvar Permissões Personalizadas**.
4. **Veja o Efeito Imediato (Sem precisar de Logout!):**  
   Volte para a janela anônima da **Beatriz** e apenas atualize a página (`F5`) no Catálogo de Salas. O botão **Editar** apareceu instantaneamente em todas as salas para ela!
5. **Teste da Escalada de Privilégio (a brecha que fechamos):**  
   Na conta da Administradora, abra as permissões do **Carlos Gestor** e marque **`usuarios.visualizar`** e **`usuarios.gerenciar`** (mas **não** `usuarios.permissoes`). Entre como Carlos em outra janela anônima e acesse **+ Novo Usuário**: em vez da matriz de checkboxes, aparece o **aviso amarelo** do perfil Solicitante. Cadastre `teste@salafacil.com` e confira na lista: o usuário nasceu com **3 chaves**, nunca com mais. (Pelo *Inspecionar Elemento* é impossível "inventar" permissões, pois o servidor ignora o formulário nesse caso.) *(Depois, devolva a Carlos as 9 permissões originais.)*
6. **Teste do Histórico Preservado:**  
   Abra **Meu Perfil** como Carlos e anote a coluna *Concedida em*. Na conta da Administradora, mude apenas **uma** permissão do Carlos e salve. Volte ao perfil dele: as datas das demais permissões **continuam as mesmas**, e só a nova tem a data de agora.
7. **Teste da Trava Anti-Autoexclusão:**  
   Como Ana (administradora), abra as permissões **dela mesma**, desmarque `usuarios.permissoes` (ou mude a conta para *Bloqueada*) e salve. O sistema recusa com um aviso amarelo e nada é alterado.
8. **Teste de Bloqueio Instantâneo de Conta:**  
   Na janela da Administradora, abra novamente as permissões da Beatriz, mude o **Status da Conta** para **Conta Bloqueada / Inativa** e salve. Quando a Beatriz der qualquer clique na janela dela, o `carregar_usuario_logado()` detectará que `ativo = 0`, encerrará a sessão dela na hora e a enviará de volta para a tela de Login! *(Depois, lembre-se de reativar a conta da Beatriz e deixá-la com as 3 permissões originais).*

---

## 6. Guia de Sobrevivência no Laboratório (Erros Comuns na Aula 08)

| Sintoma / Mensagem de Erro | Causa Mais Provável | Como Resolver Rapidamente |
| :--- | :--- | :--- |
| Ao marcar 5 permissões e salvar, apenas 1 permissão é gravada no banco de dados. | No código Python (`criar` ou `gerenciar_permissoes`), foi usado `request.form.get("permissoes_ids")` em vez de `request.form.getlist("permissoes_ids")`. | Sempre use **`.getlist("permissoes_ids")`** quando houver múltiplos checkboxes com o mesmo atributo `name`. |
| Desmarquei ou marquei permissões na tela `permissoes.html`, cliquei em Salvar, deu mensagem de sucesso, mas ao abrir de novo nada mudou no banco. | Os comandos `cursor.execute(...)` foram escritos **fora** do bloco `with transacao() as cursor:` (o `commit` automático só acontece ao final do bloco `with`). | Garanta que o `UPDATE`, o `DELETE` e os `INSERT` estejam **indentados dentro** do `with`. |
| `mysql.connector.errors.ProgrammingError: 1064 ... near ')'` ao salvar permissões. | O `DELETE ... IN (...)` foi executado com o conjunto `para_remover` vazio (`IN ()` não existe em SQL). | Mantenha o `if para_remover:` antes de montar o `DELETE`. |
| *"Sua sessão expirou ou o formulário é inválido"* ao salvar. | Faltou o campo `csrf_token` no `form.html` ou no `permissoes.html`. | Adicione o `<input type="hidden" name="csrf_token" value="{{ csrf_token() }}">`. |
| `jinja2.exceptions.UndefinedError: 'dados' is undefined` no cadastro. | Um dos `render_template("usuarios/form.html", ...)` não passa `dados`, `reenviado` e `pode_definir_permissoes`. | Os dois `render_template` do formulário na rota `criar` devem passar os três argumentos. |
| `Error Code: 1055. Expression #2 of SELECT list is not in GROUP BY clause` | Em configurações muito restritas de `sql_mode` de versões antigas do MySQL, agrupar apenas por `GROUP BY u.id` sem ser chave primária reconhecida pode reclamar. | Na nossa tabela `usuarios`, `u.id` é `PRIMARY KEY`, então o MySQL 8.0+ permite `GROUP BY u.id` nativamente (dependência funcional). |

---

## 7. Exercícios Práticos de Fixação

1. **Desafio 1 (Criando um Perfil Personalizado de "Auditor de Relatórios"):**  
   Pela interface web (`/usuarios/novo`), cadastre um 4º usuário chamado `Marcos Auditor` (`auditor@salafacil.com`, senha `123456`, Setor: `Controladoria`, Cargo: `Auditor`). Conceda a ele **apenas** as permissões `reservas.visualizar`, `relatorios.visualizar` e `relatorios.exportar` (desmarcando todas as de salas e usuários). Faça login com ele em uma janela anônima e verifique como fica o menu lateral!
2. **Desafio 2 (Sem Administrador Restante):**  
   A trava anti-autoexclusão impede que alguém bloqueie **a si mesmo**. Mas ainda há um cenário: se existirem **dois** administradores e cada um bloquear o outro, o sistema pode ficar sem ninguém com a chave `usuarios.permissoes`. Escreva (no papel ou no código) uma regra que conte quantos usuários **ativos** possuem `usuarios.permissoes` e recuse a operação se ela deixar esse número em **zero**. *(Dica: um `SELECT COUNT(DISTINCT u.id)` com `INNER JOIN` entre `usuarios`, `usuario_permissoes` e `permissoes`, filtrando `u.ativo = 1` e `p.codigo = 'usuarios.permissoes'`.)*
3. **Desafio 3 (Rota de Edição de Dados):** A chave `usuarios.gerenciar` hoje só **cadastra**. Crie a rota `GET/POST /usuarios/<id>/editar` (protegida por `usuarios.gerenciar`) que permita alterar `nome` e `setor` do usuário, validando os campos no mesmo estilo das Aulas 07 e 08 e lembrando do `csrf_token`.

<details>
<summary><strong>💡 Clique aqui para ver a explicação do Desafio 2</strong></summary>

A consulta que conta quantas pessoas ativas ainda terão a chave seria:
```sql
SELECT COUNT(DISTINCT u.id) AS total
FROM usuarios u
INNER JOIN usuario_permissoes up ON up.usuario_id = u.id
INNER JOIN permissoes p ON p.id = up.permissao_id
WHERE u.ativo = 1 AND p.codigo = 'usuarios.permissoes' AND u.id != %s
```
O `u.id != %s` (com o id do usuário que está sendo editado) mostra quantos **outros** administradores existem. Se o resultado for `0` **e** a operação remove a chave (ou desativa) o usuário editado, a rota deve recusar com `flash(...)`. É a mesma ideia da trava de autoexclusão, aplicada ao sistema inteiro: **o sistema nunca pode ficar sem um administrador**.
</details>

---

## O Que Vem a Seguir?

Os módulos de **Catálogo de Salas** e de **Usuários & Permissões Personalizadas** já estão 100% operacionais!

Na **Aula 09**, vamos construir o coração operacional do sistema: o **Módulo de Gestão de Reservas de Salas com Algoritmo SQL Anti-Conflito de Horários**! Você aprenderá a fórmula matemática para detectar sobreposição de horários no MySQL, o segredo do escape `'%%H:%%i'` no `mysql-connector-python`, a validação automática de capacidade da sala e o fluxo de aprovação/cancelamento baseado em permissões!

---
<!-- nav -->
| Anterior | Índice | Próxima |
| :--- | :---: | ---: |
| [← Aula 07 — Módulo Catálogo de Salas](./aula_07_modulo_catalogo_salas_crud.md) | [📚 Índice do Curso](./README.md) | [Aula 09 — Gestão de Reservas e Anti-Conflito →](./aula_09_gestao_reservas_validacao_conflitos.md) |