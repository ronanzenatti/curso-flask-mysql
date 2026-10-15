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
