from datetime import datetime
# app/utils/validacao.py
import re

# Código de sala: 2 a 25 caracteres; letras MAIÚSCULAS, números e hífen (ex.: LAB-101)
PADRAO_CODIGO_SALA = re.compile(r"^[A-Z0-9][A-Z0-9-]{1,24}$")


def inteiro_no_intervalo(texto, minimo, maximo):
    """Converte o texto em número inteiro e confere o intervalo. Devolve o número ou None."""
    try:
        valor = int(texto)
    except (TypeError, ValueError):
        return None
    if minimo <= valor <= maximo:
        return valor
    return None


# Formato básico de e-mail: algo@dominio.ext, sem espaços
PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def lista_de_inteiros(textos):
    """Converte uma lista de textos em um conjunto de inteiros, ignorando o que não for número."""
    numeros = set()
    for texto in textos:
        if texto.isascii() and texto.isdigit():
            numeros.add(int(texto))
    return numeros




def data_iso_valida(texto):
    """True se o texto for uma data real no formato AAAA-MM-DD (ex.: 2026-10-15)."""
    try:
        datetime.strptime(texto, "%Y-%m-%d")
    except (TypeError, ValueError):
        return False
    return True


def hora_valida(texto):
    """True se o texto for um horário real no formato HH:MM (ex.: 08:30)."""
    try:
        datetime.strptime(texto, "%H:%M")
    except (TypeError, ValueError):
        return False
    return True


def horarios_se_sobrepoem(inicio_a, fim_a, inicio_b, fim_b):
    """A mesma regra do SQL: há conflito se A começa antes de B terminar E A termina depois de B começar."""
    return inicio_a < fim_b and fim_a > inicio_b


CARACTERES_DE_FORMULA = ("=", "+", "-", "@", "\t", "\r")


def neutralizar_formula(valor):
    """Evita 'injeção de fórmula' em planilhas: textos iniciados por = + - @ ganham um apóstrofo na frente."""
    if isinstance(valor, str) and valor.startswith(CARACTERES_DE_FORMULA):
        return "'" + valor
    return valor
