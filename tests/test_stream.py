import pytest

from ardilla.stream import CharStream


def test_peek_ne_consomme_pas_le_caractere() -> None:
    stream = CharStream("ab")
    assert stream.peek() == "a"
    assert stream.peek() == "a"
    assert stream.index == 0


def test_peek_avec_decalage_regarde_plus_loin() -> None:
    stream = CharStream("abc")
    assert stream.peek(1) == "b"
    assert stream.peek(2) == "c"


def test_peek_apres_la_fin_retourne_none() -> None:
    stream = CharStream("a")
    assert stream.peek(1) is None


def test_peek_sur_source_vide_retourne_none() -> None:
    assert CharStream("").peek() is None


def test_advance_retourne_le_caractere_et_avance() -> None:
    stream = CharStream("ab")
    assert stream.advance() == "a"
    assert stream.peek() == "b"


def test_position_initiale_est_ligne_1_colonne_1() -> None:
    stream = CharStream("abc")
    assert (stream.line, stream.column) == (1, 1)


def test_advance_incremente_la_colonne() -> None:
    stream = CharStream("abc")
    stream.advance()
    stream.advance()
    assert (stream.line, stream.column) == (1, 3)


def test_retour_a_la_ligne_incremente_la_ligne_et_remet_la_colonne_a_1() -> None:
    stream = CharStream("a\nb")
    stream.advance()
    stream.advance()
    assert (stream.line, stream.column) == (2, 1)


def test_at_end_devient_vrai_apres_le_dernier_caractere() -> None:
    stream = CharStream("a")
    assert not stream.at_end()
    stream.advance()
    assert stream.at_end()


def test_advance_en_fin_de_source_leve_une_erreur() -> None:
    with pytest.raises(IndexError):
        CharStream("").advance()
