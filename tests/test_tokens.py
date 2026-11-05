import dataclasses

import pytest

from ardilla.tokens import KEYWORDS, Token, TokenType, classify_word

MOTS_CLES_SPEC = {
    "var", "funcion", "devolver", "si", "sino", "mientras", "para",
    "en", "mostrar", "y", "o", "no", "verdadero", "falso",
}


def test_token_est_immuable() -> None:
    token = Token(TokenType.SI, "si", 1, 1)
    with pytest.raises(dataclasses.FrozenInstanceError):
        token.line = 2  # type: ignore[misc]


def test_deux_tokens_avec_les_memes_champs_sont_egaux() -> None:
    assert Token(TokenType.IDENT, "x", 3, 5) == Token(TokenType.IDENT, "x", 3, 5)


def test_deux_tokens_a_des_positions_differentes_ne_sont_pas_egaux() -> None:
    assert Token(TokenType.IDENT, "x", 3, 5) != Token(TokenType.IDENT, "x", 3, 6)


def test_token_est_utilisable_dans_un_ensemble() -> None:
    token = Token(TokenType.COMA, ",", 1, 4)
    assert len({token, Token(TokenType.COMA, ",", 1, 4)}) == 1


def test_valeur_par_defaut_est_none() -> None:
    assert Token(TokenType.MAS, "+", 1, 1).value is None


def test_repr_sans_valeur_montre_type_texte_et_position() -> None:
    assert repr(Token(TokenType.SI, "si", 1, 5)) == "Token(SI 'si' @1:5)"


def test_repr_avec_valeur_entiere_montre_la_valeur() -> None:
    token = Token(TokenType.ENTERO, "42", 3, 7, 42)
    assert repr(token) == "Token(ENTERO '42' = 42 @3:7)"


def test_repr_avec_valeur_chaine_montre_la_valeur_sans_echappement() -> None:
    token = Token(TokenType.CADENA, '"a\\nb"', 2, 1, "a\nb")
    assert repr(token) == "Token(CADENA '\"a\\\\nb\"' = 'a\\nb' @2:1)"


def test_repr_affiche_une_valeur_zero() -> None:
    assert "= 0" in repr(Token(TokenType.ENTERO, "0", 1, 1, 0))


@pytest.mark.parametrize(
    ("mot", "attendu"),
    [
        ("var", TokenType.VAR),
        ("funcion", TokenType.FUNCION),
        ("devolver", TokenType.DEVOLVER),
        ("si", TokenType.SI),
        ("sino", TokenType.SINO),
        ("mientras", TokenType.MIENTRAS),
        ("para", TokenType.PARA),
        ("en", TokenType.EN),
        ("mostrar", TokenType.MOSTRAR),
        ("y", TokenType.Y),
        ("o", TokenType.O),
        ("no", TokenType.NO),
        ("verdadero", TokenType.VERDADERO),
        ("falso", TokenType.FALSO),
    ],
)
def test_mot_cle_est_reconnu(mot: str, attendu: TokenType) -> None:
    assert classify_word(mot) is attendu


@pytest.mark.parametrize("mot", ["total", "x", "siguiente", "Var", "SI", "_si", "si2"])
def test_mot_qui_nest_pas_un_mot_cle_est_un_identifiant(mot: str) -> None:
    assert classify_word(mot) is TokenType.IDENT


def test_les_mots_cles_sont_exactement_ceux_de_la_specification() -> None:
    assert set(KEYWORDS) == MOTS_CLES_SPEC


def test_chaque_mot_cle_a_un_type_different() -> None:
    assert len(set(KEYWORDS.values())) == len(KEYWORDS)


def test_les_types_de_token_ont_des_valeurs_uniques() -> None:
    valeurs = [t.value for t in TokenType]
    assert len(valeurs) == len(set(valeurs))
