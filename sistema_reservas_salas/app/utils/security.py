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
