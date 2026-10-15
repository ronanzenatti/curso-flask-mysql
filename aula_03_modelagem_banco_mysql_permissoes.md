# Aula 03 — Modelagem Relacional no MySQL e Arquitetura de Permissões Personalizadas

Nas **Aulas 01 e 02**, preparamos nosso ambiente Python, entendemos como o Flask responde a requisições HTTP e organizamos nosso projeto usando o padrão **Application Factory** (`create_app`), variáveis de ambiente (`.env`) e **Tailwind CSS**.

Porém, até agora, os dados que apareceram na nossa tela (aqueles 4 cartões de boas-vindas) estavam fixos dentro de uma lista no código Python. Se o servidor reiniciar, qualquer informação criada em variáveis comuns da memória RAM desaparece.

Para que um sistema web guarde usuários, salas e reservas de forma permanente, segura e rápida, precisamos de um **Banco de Dados Relacional**. Nesta **Aula 03**, vamos projetar o coração de dados do **SalaFácil** no **MySQL**, aprendendo na prática:
1. Por que sistemas profissionais usam **Permissões Personalizadas (Granulares)** em vez de apenas cargos fixos.
2. Como funciona um relacionamento **Muitos-para-Muitos (`N:M`)** com tabela associativa (pivô).
3. Como escolher os tipos de dados corretos no MySQL (`VARCHAR`, `TINYINT(1)`, `ENUM`, `DATE`, `TIME`).
4. O segredo da integridade referencial: quando usar `ON DELETE CASCADE`, `ON DELETE RESTRICT` e `ON DELETE SET NULL`.
5. Como acelerar a checagem de conflitos de horário com **Índices Compostos (`INDEX`)** e como o próprio banco pode recusar dados absurdos com **regras `CHECK`**.

---

## 1. O Problema dos "Cargos Fixos" vs. Permissões Personalizadas (Granulares)

Imagine que você está criando um sistema simples na faculdade. A primeira ideia que costuma surgir para controlar quem pode fazer o quê é criar uma coluna chamada `cargo` na tabela de usuários e espalhar vários `if` pelo código Python:

```python
# Abordagem limitada (Cargos Fixos / Engessados):
if usuario.cargo == "admin":
    # Pode fazer tudo!
```

### Por que essa abordagem falha no mundo real?
Nas empresas e universidades, as funções das pessoas são dinâmicas e cheias de exceções:
* **Caso 1 (O Recepcionista):** Precisa cadastrar novas reservas e aprovar pedidos de salas de reunião, mas **não pode** excluir uma sala do prédio nem mexer nas senhas de outros usuários.
* **Caso 2 (O Coordenador de Curso):** Precisa acessar o painel de relatórios e exportar planilhas CSV para a diretoria, mas **não pode** alterar a capacidade física dos laboratórios.
* **Caso 3 (O Estagiário de TI):** É um solicitante comum, mas nesta semana recebeu a missão de atualizar a lista de projetores e computadores de todas as salas. Ele precisa apenas da permissão de **editar salas**, sem se tornar Administrador Geral do sistema!

Se o seu sistema só conhece `admin` e `comum`, você fica de mãos atadas.

### Nossa Solução Profissional: Modelagem Híbrida e Granular
No **SalaFácil**, resolveremos esse problema combinando dois conceitos elegantes:
1. **Etiqueta de Cargo (`cargo_etiqueta`):** Cada usuário tem um título informativo no seu cadastro (ex.: *Administrador Geral*, *Gestor de Espaços*, *Solicitante*, *Coordenador*). Ele serve para identificar visualmente a função da pessoa na instituição.
2. **Chaves de Permissão Personalizadas (`permissoes` + `usuario_permissoes`):** Cada ação protegida do sistema ganha um código único no formato `modulo.acao` (como `salas.criar`, `salas.excluir`, `reservas.aprovar`, `relatorios.exportar`). Um administrador pode marcar ou desmarcar individualmente **qualquer caixinha de permissão para qualquer usuário**, criando perfis sob medida!

---

## 2. Desenhando as 5 Tabelas do Banco (`gestao_reservas_salas`)

Antes de escrever uma única linha de SQL, todo bom desenvolvedor desenha o mapa das tabelas e como elas se conectam. Nosso banco de dados se chamará **`gestao_reservas_salas`** e terá **5 tabelas**:

```text
+------------------+          +-----------------------+          +------------------+
|     usuarios     |          |  usuario_permissoes   |          |    permissoes    |
+------------------+          +-----------------------+          +------------------+
| PK id            | 1      N | PK,FK usuario_id      | N      1 | PK id            |
|    nome          |<---------| PK,FK permissao_id    |--------->|    codigo        |
|    email         |          |       concedido_em    |          |    nome          |
|    senha_hash    |          +-----------------------+          |    modulo        |
|    setor         |                                             |    descricao     |
|    cargo_etiqueta|                                             +------------------+
|    ativo         |
+------------------+
       | 1
       | (Solicita ou Aprova)
       | N
+------------------+          +------------------+
|     reservas     |          |      salas       |
+------------------+          +------------------+
| PK id            | N      1 | PK id            |
| FK sala_id       |--------->|    codigo        |
| FK usuario_id    |          |    nome          |
| FK aprovador_id  |          |    bloco         |
|    titulo        |          |    capacidade    |
|    data_reserva  |          |    recursos      |
|    hora_inicio   |          |    ativa         |
|    hora_fim      |          +------------------+
|    status        |
+------------------+
```

### Resumo das Responsabilidades e Relacionamentos:

| Tabela | Papel no Sistema | Como se Relaciona (Chaves Estrangeiras) |
| :--- | :--- | :--- |
| **`usuarios`** | Guarda os dados pessoais, a senha criptografada (`senha_hash`), o setor e se a conta está ativa ou bloqueada. | **1:N** com `usuario_permissoes` e **1:N** com `reservas`. |
| **`permissoes`** | O catálogo fixo das **13 ações protegidas** do sistema (ex.: `salas.criar`, `reservas.aprovar`). | **N:M** com `usuarios` por meio da tabela `usuario_permissoes`. |
| **`usuario_permissoes`** | **Tabela Associativa (Pivô):** Liga cada `usuario_id` a cada `permissao_id` que ele possui. | Possui duas chaves estrangeiras: aponta para `usuarios(id)` e para `permissoes(id)`. |
| **`salas`** | O catálogo físico das salas e laboratórios (código `LAB-101`, bloco, capacidade de lugares e equipamentos). | **1:N** com `reservas` (uma sala pode ter várias reservas ao longo do tempo). |
| **`reservas`** | A agenda de pedidos: qual sala, qual data, horário de início e término, quem pediu (`usuario_id`), quem aprovou (`aprovador_id`) e o `status`. | Aponta para `salas(id)` e tem **duas** conexões com `usuarios(id)` (o solicitante e o aprovador). |

---

## 3. Entendendo os Conceitos SQL Antes de Codificar

Ao ler o nosso script SQL logo abaixo, você encontrará comandos que fazem toda a diferença em um banco de dados profissional. Vamos entender cada um deles de forma simples:

### 3.1 — `CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci`
Na língua portuguesa, usamos muitos acentos (*Administração, Auditório, Reunião, Ciências*), além de emojis modernos (🏢, 📅, 🔐). O padrão `utf8mb4` garante que o MySQL aceite 100% dos caracteres acentuados e emojis sem salvar símbolos estranhos (como `Ã§Ã£o`), e o `utf8mb4_unicode_ci` (*case-insensitive*) permite que uma busca por `"auditorio"` encontre `"Auditório"` mesmo sem acento ou letra maiúscula!

### 3.2 — `TINYINT(1)` para Campos Verdadeiro/Falso (Booleano)
O MySQL usa o tipo `TINYINT(1)` para representar valores booleanos:
* **`1`** significa **Verdadeiro (`True`)** $\rightarrow$ Usuário ativo / Sala disponível.
* **`0`** significa **Falso (`False`)** $\rightarrow$ Usuário bloqueado / Sala em manutenção.

### 3.3 — `ENUM('pendente', 'aprovada', 'rejeitada', 'cancelada')`
Na tabela `reservas`, a coluna `status` não é um texto livre onde qualquer um pode escrever `"ok"` ou `"confirmado"`. O tipo `ENUM` cria uma **lista fechada de opções permitidas** diretamente no banco de dados. Se alguém tentar gravar um status fora dessas 4 palavras, o próprio MySQL bloqueia a operação!

### 3.4 — Chave Primária Composta (`PRIMARY KEY (usuario_id, permissao_id)`)
Na tabela `usuario_permissoes`, não criamos uma coluna `id` numérica solta. Em vez disso, dissemos que a Chave Primária é a **combinação** de `(usuario_id, permissao_id)`.
* **Por que isso é genial?** Porque o próprio banco de dados impede que o usuário `1` receba a permissão `5` duas vezes! O par `(1, 5)` só pode existir uma única vez na tabela.

### 3.5 — As 3 Regras de Ouro de Exclusão (`ON DELETE`)
O que acontece no banco de dados se alguém tentar apagar (`DELETE`) um registro que está ligado a outra tabela? No nosso sistema, usamos as **3 regras clássicas da engenharia de dados**:

1. **`ON DELETE CASCADE` (Efeito Cascata — Usado em `usuario_permissoes`):**  
   Se um usuário for excluído da tabela `usuarios`, o MySQL apaga **automaticamente** todas as linhas dele na tabela `usuario_permissoes`. Não sobra "lixo" órfão no banco!
2. **`ON DELETE RESTRICT` (Bloqueio de Segurança — Usado em `reservas` para `sala_id` e `usuario_id`):**  
   Imagine se alguém apagasse a sala `LAB-101` que já teve 200 aulas realizadas no semestre. Todo o relatório histórico da instituição ficaria corrompido! O `ON DELETE RESTRICT` proíbe apagar uma sala ou usuário que já possua reservas registradas (para desativar uma sala antiga sem perder o histórico, basta mudar `ativa = 0`).
3. **`ON DELETE SET NULL` (Preservação com Limpeza — Usado em `reservas` para `aprovador_id`):**  
   A coluna `aprovador_id` guarda quem aprovou a reserva. Enquanto a reserva está `pendente`, esse campo fica vazio (`NULL`). E se o gestor que aprovou a reserva sair da empresa e sua conta for removida? A reserva não deve ser apagada: o `ON DELETE SET NULL` mantém a reserva intacta e apenas coloca `NULL` no campo `aprovador_id`.

### 3.6 — Regras `CHECK`: o "porteiro" dentro do banco de dados

> **Analogia do porteiro:** o sistema Python (Flask) é a recepção do prédio e já confere os dados do visitante. Mas e se alguém entrar pela **janela dos fundos** (um script mal escrito, um erro de programação, alguém mexendo direto no MySQL)? O **`CHECK`** é um **segundo porteiro, dentro do banco**, que recusa qualquer linha que viole uma regra, não importa por onde ela chegou.

Usaremos três regras, todas muito simples:

| Regra | Em português claro | O que impede |
| :--- | :--- | :--- |
| `CHECK (capacidade >= 1)` na tabela `salas` | "Uma sala precisa ter pelo menos 1 lugar." | Salas com capacidade `0` ou negativa. |
| `CHECK (hora_fim > hora_inicio)` na tabela `reservas` | "O término precisa ser depois do início." | Reservas que terminam antes de começar (como `14:00` às `13:00`). |
| `CHECK (participantes_estimados >= 1)` na tabela `reservas` | "Toda reserva tem pelo menos 1 participante." | Reservas com `0` ou negativos participantes. |

> 📌 O `CHECK` é **aplicado de verdade** a partir do MySQL 8.0.16 (nossa versão mínima recomendada). Em versões mais antigas ele é lido, mas ignorado em silêncio.

---

## 4. Criando o Script Completo do Esquema (`sql/schema.sql`)

Agora que cada linha faz sentido, abra (ou crie) o arquivo **`sql/schema.sql`** dentro da subpasta `sql/` do seu projeto (`sistema_reservas_salas/sql/schema.sql`) e insira o código abaixo:

```sql
-- sql/schema.sql
CREATE DATABASE IF NOT EXISTS gestao_reservas_salas
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE gestao_reservas_salas;

-- 1. Tabela de Usuários
CREATE TABLE IF NOT EXISTS usuarios (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nome VARCHAR(120) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    senha_hash VARCHAR(255) NOT NULL,
    setor VARCHAR(80) NOT NULL DEFAULT 'Geral',
    cargo_etiqueta VARCHAR(60) NOT NULL DEFAULT 'Solicitante',
    ativo TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    atualizado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB;

-- 2. Catálogo de Permissões do Sistema
CREATE TABLE IF NOT EXISTS permissoes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(60) NOT NULL UNIQUE,
    nome VARCHAR(100) NOT NULL,
    modulo VARCHAR(50) NOT NULL,
    descricao VARCHAR(255) NOT NULL,
    INDEX idx_permissoes_modulo (modulo, codigo)
) ENGINE=InnoDB;

-- 3. Tabela Associativa de Permissões Personalizadas por Usuário
CREATE TABLE IF NOT EXISTS usuario_permissoes (
    usuario_id INT NOT NULL,
    permissao_id INT NOT NULL,
    concedido_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (usuario_id, permissao_id),
    CONSTRAINT fk_up_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE CASCADE,
    CONSTRAINT fk_up_permissao
        FOREIGN KEY (permissao_id) REFERENCES permissoes(id)
        ON DELETE CASCADE
) ENGINE=InnoDB;

-- 4. Tabela de Salas Disponíveis para Reserva
CREATE TABLE IF NOT EXISTS salas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    codigo VARCHAR(25) NOT NULL UNIQUE,
    nome VARCHAR(120) NOT NULL,
    bloco VARCHAR(60) NOT NULL,
    capacidade INT NOT NULL DEFAULT 10,
    recursos VARCHAR(255) NOT NULL DEFAULT '',
    ativa TINYINT(1) NOT NULL DEFAULT 1,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT ck_salas_capacidade CHECK (capacidade >= 1)
) ENGINE=InnoDB;

-- 5. Tabela de Reservas de Salas
CREATE TABLE IF NOT EXISTS reservas (
    id INT AUTO_INCREMENT PRIMARY KEY,
    sala_id INT NOT NULL,
    usuario_id INT NOT NULL,
    aprovador_id INT NULL,
    titulo VARCHAR(150) NOT NULL,
    finalidade VARCHAR(255) NOT NULL,
    data_reserva DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fim TIME NOT NULL,
    participantes_estimados INT NOT NULL DEFAULT 1,
    status ENUM('pendente', 'aprovada', 'rejeitada', 'cancelada') NOT NULL DEFAULT 'pendente',
    observacoes TEXT NULL,
    criado_em DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_reserva_sala
        FOREIGN KEY (sala_id) REFERENCES salas(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_reserva_usuario
        FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
        ON DELETE RESTRICT,
    CONSTRAINT fk_reserva_aprovador
        FOREIGN KEY (aprovador_id) REFERENCES usuarios(id)
        ON DELETE SET NULL,
    CONSTRAINT ck_reserva_horario CHECK (hora_fim > hora_inicio),
    CONSTRAINT ck_reserva_participantes CHECK (participantes_estimados >= 1),
    INDEX idx_reservas_conflito (sala_id, data_reserva, status, hora_inicio, hora_fim),
    INDEX idx_reservas_listagem (data_reserva, status, titulo)
) ENGINE=InnoDB;
```

---

### Linha por linha das novidades do `schema.sql`

| Trecho | O que é | Por que está ali | O que acontece se tirar |
| :--- | :--- | :--- | :--- |
| `CONSTRAINT ck_salas_capacidade CHECK (capacidade >= 1)` | Cria uma regra com nome (`ck_salas_capacidade`) que só aceita capacidade maior ou igual a 1. | Garante, no próprio banco, que nenhuma sala tenha 0 lugares, mesmo que o Python falhe em conferir. | O banco aceita salas com capacidade `0` ou `-5`, e os relatórios passam a mostrar valores sem sentido. |
| `CONSTRAINT ck_reserva_horario CHECK (hora_fim > hora_inicio)` | Regra que compara duas colunas da mesma linha. | É a última barreira contra reservas "ao contrário". | Uma reserva das `14:00` às `13:00` entraria no banco e quebraria o cálculo de horas dos relatórios (resultado negativo). |
| `CONSTRAINT ck_reserva_participantes CHECK (participantes_estimados >= 1)` | Regra de número mínimo de participantes. | Evita reservas "fantasma" com zero pessoas. | O banco aceita `0` ou valores negativos. |
| `INDEX idx_reservas_conflito (sala_id, data_reserva, status, hora_inicio, hora_fim)` | Índice composto, explicado na seção 5. | Acelera a pergunta "esta sala está livre neste horário?". | Funciona, mas cada verificação percorre a tabela inteira (mais lento com o tempo). |

> 🔍 **Onde foram parar os índices de busca de texto?** Nas primeiras versões deste curso havia também `idx_salas_busca` e `idx_usuarios_busca`. Nós os **removemos** de propósito, e a seção 5 explica por quê: eles nunca eram usados pelas nossas pesquisas.

---

## 5. Índices Compostos (`INDEX`): para Que Servem (e para Que NÃO Servem)

Repare na linha que começa com `INDEX idx_...` no final da tabela `reservas` do nosso `schema.sql`:

```sql
INDEX idx_reservas_conflito (sala_id, data_reserva, status, hora_inicio, hora_fim)
```

### A Analogia do Índice de um Livro:
Imagine um livro de 1.000 páginas sem sumário nem índice alfabético. Se alguém perguntar *"Em qual página fala sobre a sala LAB-101 no dia 15/10?"*, você terá que ler o livro inteiro da página 1 até a 1.000 (no banco de dados, isso se chama **Full Table Scan** — varredura completa da tabela, que deixa o sistema lento).

Quando criamos um **`INDEX`**, o MySQL monta uma árvore de busca ordenada em memória (*B-Tree*). Assim, quando nosso sistema for verificar se já existe outra reserva na mesma sala e data (na Aula 09), o MySQL vai direto à "página certa" em vez de ler tudo.

### O que o índice faz e o que ele NÃO faz (leia com atenção!)

| Afirmação | Verdade? | Explicação |
| :--- | :---: | :--- |
| "O índice acelera buscas por **igualdade** (`sala_id = 3 AND data_reserva = '2026-10-15'`)." | ✅ Sim | É exatamente o caso do `idx_reservas_conflito`. A sala e a data ficam no início do índice. |
| "O índice **impede reservas duplicadas ou em conflito**." | ❌ Não | Este índice **não é `UNIQUE`**: ele só acelera a consulta. Quem impede o conflito é a **lógica da Aula 09**, protegida por uma transação. |
| "O índice acelera pesquisas de texto como `LIKE '%Projetor%'`." | ❌ Não | O índice funciona como uma agenda de contatos em ordem alfabética: dá para achar quem **começa** com "Pro", mas não quem **contém** "jet" no meio do nome. Com o `%` no início, o MySQL precisa ler todas as linhas. |

> 💡 **Por isso removemos os índices de busca de texto.** Nossa pesquisa dinâmica usa `LIKE '%termo%'` em várias colunas ao mesmo tempo com `OR`; nenhum índice comum ajuda nisso, então eles só ocupariam espaço e deixariam as gravações mais lentas. Para o volume de uma instituição de ensino (milhares de linhas) a leitura completa leva poucos milissegundos e é perfeitamente aceitável. Se um dia a tabela tiver milhões de linhas, a ferramenta correta é o índice **`FULLTEXT`** (busca por palavras), que fica como assunto de estudo avançado.

---

## 6. O Catálogo Oficial das 13 Permissões Personalizadas

Na tabela `permissoes`, cadastraremos **13 chaves de permissão granulares**, divididas nos **4 módulos principais** do sistema. Guarde bem esta tabela de referência, pois usaremos esses códigos exatos no Python e nos templates HTML a partir da Aula 05:

| Código (`codigo`) | Módulo (`modulo`) | Nome Amigável (`nome`) | O Que Esta Chave Libera no Sistema |
| :--- | :--- | :--- | :--- |
| `salas.visualizar` | Salas | Visualizar Salas | Consultar a tabela paginada de salas e seus equipamentos. |
| `salas.criar` | Salas | Cadastrar Salas | Acessar o formulário `/salas/nova` e salvar novas salas no banco. |
| `salas.editar` | Salas | Editar Salas | Alterar capacidade, equipamentos e status ativo/manutenção de uma sala. |
| `salas.excluir` | Salas | Excluir Salas | Remover do banco salas que ainda não possuam histórico de reservas. |
| `reservas.visualizar` | Reservas | Visualizar Reservas | Consultar a agenda geral de reservas de salas. |
| `reservas.criar` | Reservas | Solicitar Reserva | Criar novos agendamentos de salas (passando pela validação anti-conflito). |
| `reservas.aprovar` | Reservas | Aprovar/Rejeitar Reservas | Aprovar ou recusar pedidos pendentes (e ter as próprias reservas aprovadas automaticamente). |
| `reservas.cancelar_qualquer` | Reservas | Cancelar Qualquer Reserva | Cancelar reservas feitas por outras pessoas (sem ela, o usuário só cancela as próprias). |
| `usuarios.visualizar` | Usuários | Visualizar Usuários | Listar usuários cadastrados e ver quantas permissões cada um possui. |
| `usuarios.gerenciar` | Usuários | Cadastrar Usuários | Cadastrar novos usuários no sistema. As permissões iniciais seguem o perfil básico de Solicitante, a menos que quem cadastra também possua `usuarios.permissoes`. |
| `usuarios.permissoes` | Usuários | Configurar Permissões | Abrir a matriz visual de checkboxes para alterar permissões e status de uma conta, e escolher permissões livremente no cadastro de novos usuários. |
| `relatorios.visualizar` | Relatórios | Acessar Relatórios | Visualizar os cards de KPIs e as duas tabelas de relatórios gerenciais. |
| `relatorios.exportar` | Relatórios | Exportar Relatórios | Baixar planilhas em formato CSV (Excel) e acionar o modo de impressão oficial. |

---

## 7. Como Testar a Criação do Banco Agora (Opcional antes da Aula 04)

Na **Aula 04**, criaremos um script em Python (`seed_db.py`) que lerá este arquivo `sql/schema.sql`, criará o banco automaticamente (usando o nome definido em `DB_NAME` no seu `.env`) e já preencherá todas as 13 permissões, usuários de teste, salas e reservas para você com um único comando!

Mas, se você já quiser testar o seu arquivo `sql/schema.sql` diretamente no seu servidor MySQL hoje mesmo para ver as 5 tabelas criadas, você pode fazer isso de duas formas rápidas:

### Opção 1 — Pelo MySQL Workbench ou DBeaver (Visual):
1. Abra o MySQL Workbench (ou DBeaver) e conecte-se ao seu servidor local (`127.0.0.1`, porta `3306`).
2. Abra o arquivo `sql/schema.sql` (ou copie e cole o conteúdo dele em uma aba de *Query*).
3. Clique no ícone do **Raio ⚡ (Execute)** e atualize a lista de *Schemas* na barra lateral esquerda. O banco **`gestao_reservas_salas`** aparecerá com as 5 tabelas!

### Opção 2 — Pelo Terminal do MySQL:
Se o comando `mysql` estiver disponível no seu terminal, basta rodar:

```bash
mysql -u root -p < sql/schema.sql
```

Depois, entrando no MySQL (`mysql -u root -p`), você pode conferir as tabelas criadas com:

```sql
USE gestao_reservas_salas;
SHOW TABLES;
DESCRIBE reservas;
```

---

## 8. Como Consultaremos as Permissões de um Usuário no SQL? (`INNER JOIN`)

Para entender como as tabelas `permissoes` e `usuario_permissoes` trabalharão juntas nas próximas aulas, observe esta consulta SQL com `INNER JOIN`:

```sql
SELECT p.codigo, p.nome, p.modulo
FROM permissoes p
INNER JOIN usuario_permissoes up ON up.permissao_id = p.id
WHERE up.usuario_id = 1
ORDER BY p.modulo, p.nome;
```

### Como ler essa consulta em português claro:
1. **`FROM permissoes p`**: Comece olhando para o catálogo de permissões (apelidado de `p`).
2. **`INNER JOIN usuario_permissoes up ON up.permissao_id = p.id`**: Junte cada permissão com a tabela de vínculos (`up`), conectando o `id` da permissão nas duas tabelas.
3. **`WHERE up.usuario_id = 1`**: Filtre apenas as linhas que pertencem ao usuário de ID `1`.
4. **Resultado:** O MySQL devolve em menos de 1 milissegundo a lista exata de códigos (`salas.visualizar`, `reservas.criar`, etc.) que aquele usuário tem direito de usar!

---

## 9. Guia de Sobrevivência no Laboratório (Erros Comuns de SQL na Aula 03)

| Sintoma / Mensagem de Erro | Causa Mais Provável | Como Resolver Rapidamente |
| :--- | :--- | :--- |
| `Error Code: 1046. No database selected` | Você tentou executar apenas um `CREATE TABLE` isolado no MySQL Workbench sem antes rodar as linhas `CREATE DATABASE...` e `USE gestao_reservas_salas;`. | Execute sempre o script `sql/schema.sql` desde a primeira linha (sem selecionar apenas um trecho com o mouse), ou dê um duplo clique sobre o banco `gestao_reservas_salas` na barra lateral do Workbench. |
| `Error Code: 1824. Failed to open the referenced table` | Você tentou criar a tabela `usuario_permissoes` ou `reservas` **antes** de criar as tabelas `usuarios`, `permissoes` e `salas`. | Como as chaves estrangeiras (`FOREIGN KEY`) apontam para `usuarios`, `permissoes` e `salas`, a ordem das tabelas no arquivo `sql/schema.sql` é obrigatória: primeiro as tabelas independentes, depois as tabelas que dependem delas! |
| `Can't connect to MySQL server on '127.0.0.1' (10061)` | O serviço do servidor MySQL está desligado no seu computador. | Se estiver usando XAMPP ou Laragon, abra o painel de controle deles e clique em **Start** no MySQL. Se instalou o MySQL Server no Windows, abra o aplicativo **Serviços (`services.msc`)**, procure por `MySQL80` e clique em **Iniciar**. |

---

## 10. Exercícios Práticos de Fixação

Para fixar os conceitos de modelagem relacional e integridade referencial desta aula, responda e pratique:

1. **Desafio 1 (Análise de Integridade):** Olhando para o nosso `sql/schema.sql`, explique com suas palavras: o que acontecerá no banco de dados se tentarmos rodar `DELETE FROM salas WHERE id = 1;` sendo que a sala `1` já possui reservas cadastradas na tabela `reservas`? E o que acontecerá se rodarmos `DELETE FROM usuarios WHERE id = 2;` em um usuário que possui 5 permissões na tabela `usuario_permissoes`, mas **nenhuma** reserva na tabela `reservas`?
2. **Desafio 2 (Escrevendo SQL Manual):** Suponha que a direção da faculdade pediu uma 14ª permissão chamada `salas.manutencao` (Módulo: `Salas`, Nome: `Colocar Sala em Manutenção`, Descrição: `Permite bloquear salas para reforma`). Escreva a instrução `INSERT INTO permissoes ...` que cadastraria essa nova permissão no banco.
3. **Desafio 3 (Consulta SQL com Filtro):** Escreva uma consulta `SELECT` na tabela `salas` que liste apenas o `codigo`, o `nome` e a `capacidade` das salas que estão **ativas** (`ativa = 1`) e que comportam **30 ou mais lugares** (`capacidade >= 30`), ordenadas da maior capacidade para a menor.
4. **Desafio 4 (Testando o "porteiro" `CHECK`):** Depois de rodar o `seed_db.py` na Aula 04, tente executar no MySQL Workbench um `UPDATE salas SET capacidade = 0 WHERE codigo = 'LAB-101';`. O que o MySQL responde e por quê?

<details>
<summary><strong>💡 Clique aqui para ver o Gabarito Comentado dos Exercícios</strong></summary>

**1. Resposta do Desafio 1:**
* Ao tentar deletar a sala `1` que já tem reservas, o MySQL **bloqueará a exclusão** com erro de chave estrangeira por causa da regra `ON DELETE RESTRICT` definida em `fk_reserva_sala`. Isso protege o histórico de reservas da instituição.
* Já ao deletar o usuário `2` (que não tem reservas, mas tem 5 linhas em `usuario_permissoes`), a exclusão **será permitida** e, graças à regra `ON DELETE CASCADE` em `fk_up_usuario`, o MySQL apagará automaticamente as 5 linhas de permissão dele na tabela `usuario_permissoes`!

**2. Resolução do Desafio 2:**
```sql
INSERT INTO permissoes (codigo, nome, modulo, descricao)
VALUES (
    'salas.manutencao',
    'Colocar Sala em Manutenção',
    'Salas',
    'Permite bloquear salas para reforma'
);
```

**3. Resolução do Desafio 3:**
```sql
SELECT codigo, nome, capacidade
FROM salas
WHERE ativa = 1
  AND capacidade >= 30
ORDER BY capacidade DESC;
```

**4. Resolução do Desafio 4:**
O MySQL recusa o comando com o erro `Error Code: 3819. Check constraint 'ck_salas_capacidade' is violated.` O "porteiro" `CHECK (capacidade >= 1)` barrou o valor `0`, e a linha da sala continua com a capacidade antiga. Isso prova que a regra vale até para quem acessa o banco diretamente, sem passar pelo Flask.
</details>

---

## O Que Vem a Seguir?

Nosso arquivo `sql/schema.sql` está pronto e bem fundamentado! Na **Aula 04**, vamos construir a ponte entre o **Python (Flask)** e o **MySQL**: criaremos nosso gerenciador de conexões seguro (`app/database.py` com proteção contra *SQL Injection*), desenvolveremos o script automatizado de carga inicial (`seed_db.py` com senhas criptografadas) e faremos uma rota de diagnóstico no Flask para ver os dados do MySQL chegando ao navegador!

---
<!-- nav -->
| Anterior | Índice | Próxima |
| :--- | :---: | ---: |
| [← Aula 02 — Arquitetura, Jinja2 e Tailwind](./aula_02_arquitetura_factory_jinja2_tailwind.md) | [📚 Índice do Curso](./README.md) | [Aula 04 — Conexão MySQL e Seed →](./aula_04_conexao_mysql_seguranca_seed.md) |