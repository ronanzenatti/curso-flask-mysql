# tests/test_utilitarios.py
from app.utils.security import caminho_seguro
from app.utils.validacao import (
    PADRAO_CODIGO_SALA, PADRAO_EMAIL, data_iso_valida, hora_valida,
    horarios_se_sobrepoem, inteiro_no_intervalo, lista_de_inteiros, neutralizar_formula,
)


def test_caminho_seguro_aceita_apenas_caminhos_internos():
    assert caminho_seguro("/salas/") == "/salas/"
    assert caminho_seguro("//site-falso.com") is None
    assert caminho_seguro("http://site-falso.com") is None
    assert caminho_seguro("/\\site-falso.com") is None
    assert caminho_seguro("") is None
    assert caminho_seguro(None) is None


def test_horarios_se_sobrepoem_nos_cenarios_da_aula_09():
    # Reserva existente: 09:00 às 11:00
    assert horarios_se_sobrepoem("09:00", "11:00", "08:30", "09:30")   # invade o começo
    assert horarios_se_sobrepoem("09:00", "11:00", "10:30", "11:30")   # invade o final
    assert horarios_se_sobrepoem("09:00", "11:00", "09:30", "10:30")   # dentro do horário
    assert horarios_se_sobrepoem("09:00", "11:00", "08:00", "12:00")   # engloba tudo
    assert not horarios_se_sobrepoem("09:00", "11:00", "11:00", "13:00")  # vizinho depois: permitido
    assert not horarios_se_sobrepoem("09:00", "11:00", "07:00", "09:00")  # vizinho antes: permitido


def test_inteiro_no_intervalo():
    assert inteiro_no_intervalo("5", 1, 10) == 5
    assert inteiro_no_intervalo("0", 1, 10) is None
    assert inteiro_no_intervalo("11", 1, 10) is None
    assert inteiro_no_intervalo("abc", 1, 10) is None
    assert inteiro_no_intervalo(None, 1, 10) is None


def test_lista_de_inteiros_ignora_valores_estranhos():
    assert lista_de_inteiros(["1", "5", "abc", "²", "-3"]) == {1, 5}


def test_formato_do_codigo_da_sala_e_do_email():
    assert PADRAO_CODIGO_SALA.match("LAB-101")
    assert not PADRAO_CODIGO_SALA.match("lab 104!")
    assert not PADRAO_CODIGO_SALA.match("A")
    assert PADRAO_EMAIL.match("ana@salafacil.com")
    assert not PADRAO_EMAIL.match("ana@salafacil")
    assert not PADRAO_EMAIL.match("ana salafacil.com")


def test_datas_e_horas_validas():
    assert data_iso_valida("2026-10-15")
    assert not data_iso_valida("2026-02-30")
    assert not data_iso_valida("banana")
    assert not data_iso_valida(None)
    assert hora_valida("08:30")
    assert not hora_valida("25:99")


def test_neutralizar_formula_protege_o_excel():
    assert neutralizar_formula("=1+1") == "'=1+1"
    assert neutralizar_formula("@cmd") == "'@cmd"
    assert neutralizar_formula("-5 pessoas") == "'-5 pessoas"
    assert neutralizar_formula("Aula de Python") == "Aula de Python"
    assert neutralizar_formula(35) == 35
    assert neutralizar_formula(-5) == -5
