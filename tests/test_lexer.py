import types
from pathlib import Path

import pytest

from ardilla.errors import LexError
from ardilla.lexer import tokenize
from ardilla.tokens import Token, TokenType

T = TokenType
EJEMPLOS = sorted((Path(__file__).parent.parent / "ejemplos").glob("*.ard"))


def lex(source: str) -> list[Token]:
    return list(tokenize(source))


def types_of(source: str) -> list[TokenType]:
    """Types des tokens, sans le FIN final."""
    return [token.type for token in lex(source)][:-1]


def error_of(source: str) -> LexError:
    with pytest.raises(LexError) as info:
        lex(source)
    return info.value


# ---------- Cas de base ----------


def test_source_vide_ne_produit_que_fin() -> None:
    assert types_of("") == []
    assert [t.type for t in lex("")] == [T.FIN]


def test_espaces_et_retours_a_la_ligne_seuls_ne_produisent_que_fin() -> None:
    assert [t.type for t in lex("  \t\n\r\n  ")] == [T.FIN]


@pytest.mark.parametrize("source", ["", "var x;", "// rien", "x"])
def test_fin_est_toujours_le_dernier_token(source: str) -> None:
    assert lex(source)[-1].type is T.FIN


# ---------- Symboles ----------


@pytest.mark.parametrize(
    ("source", "attendu"),
    [
        ("+", T.MAS),
        ("-", T.MENOS),
        ("*", T.POR),
        ("/", T.ENTRE),
        ("%", T.RESTO),
        ("=", T.ASIGNAR),
        ("<", T.MENOR),
        (">", T.MAYOR),
        ("(", T.PAREN_IZQ),
        (")", T.PAREN_DER),
        ("{", T.LLAVE_IZQ),
        ("}", T.LLAVE_DER),
        (",", T.COMA),
        (";", T.PUNTO_Y_COMA),
        ("==", T.IGUAL_IGUAL),
        ("!=", T.DISTINTO),
        ("<=", T.MENOR_IGUAL),
        (">=", T.MAYOR_IGUAL),
        ("..", T.RANGO),
    ],
)
def test_symbole_est_reconnu(source: str, attendu: TokenType) -> None:
    tokens = lex(source)
    assert tokens[0].type is attendu
    assert tokens[0].lexeme == source
    assert len(tokens) == 2  # le symbole et FIN


def test_inferieur_ou_egal_est_un_seul_token() -> None:
    assert types_of("a<=b") == [T.IDENT, T.MENOR_IGUAL, T.IDENT]


def test_inferieur_puis_egal_separes_donnent_deux_tokens() -> None:
    assert types_of("a < = b") == [T.IDENT, T.MENOR, T.ASIGNAR, T.IDENT]


def test_egal_egal_egal_donne_egal_egal_puis_egal() -> None:
    assert types_of("===") == [T.IGUAL_IGUAL, T.ASIGNAR]


def test_division_n_est_pas_un_commentaire() -> None:
    assert types_of("6 / 2") == [T.ENTERO, T.ENTRE, T.ENTERO]


# ---------- Mots-clés et identifiants ----------


def test_mot_cle_et_identifiant() -> None:
    assert types_of("var total") == [T.VAR, T.IDENT]


@pytest.mark.parametrize("mot", ["siguiente", "sin", "Var", "SI", "_x1", "yy", "no2"])
def test_mot_proche_dun_mot_cle_est_un_identifiant(mot: str) -> None:
    token = lex(mot)[0]
    assert token.type is T.IDENT
    assert token.lexeme == mot


def test_sino_est_un_mot_cle_distinct_de_si() -> None:
    assert types_of("si sino") == [T.SI, T.SINO]


def test_identifiant_avec_chiffres_et_underscore() -> None:
    assert lex("mi_var_2")[0].lexeme == "mi_var_2"


def test_identifiant_a_une_valeur_none() -> None:
    assert lex("x")[0].value is None


# ---------- Entiers ----------


def test_entier_a_un_lexeme_et_une_valeur() -> None:
    token = lex("42")[0]
    assert (token.type, token.lexeme, token.value) == (T.ENTERO, "42", 42)


def test_entier_avec_zeros_initiaux_garde_son_lexeme() -> None:
    token = lex("007")[0]
    assert (token.lexeme, token.value) == ("007", 7)


def test_intervalle_sans_espaces_donne_trois_tokens() -> None:
    assert types_of("0..5") == [T.ENTERO, T.RANGO, T.ENTERO]


def test_moins_devant_un_entier_est_un_token_separe() -> None:
    assert types_of("-5") == [T.MENOS, T.ENTERO]


# ---------- Chaînes ----------


def test_chaine_simple_a_un_lexeme_avec_guillemets_et_une_valeur_sans() -> None:
    token = lex('"hola"')[0]
    assert (token.type, token.lexeme, token.value) == (T.CADENA, '"hola"', "hola")


def test_chaine_vide() -> None:
    assert lex('""')[0].value == ""


def test_chaine_peut_contenir_des_espaces_et_des_symboles() -> None:
    assert lex('"a + b; // c"')[0].value == "a + b; // c"


@pytest.mark.parametrize(
    ("source", "valeur"),
    [
        (r'"a\nb"', "a\nb"),
        (r'"dijo \"hola\""', 'dijo "hola"'),
        (r'"a\\b"', "a\\b"),
    ],
)
def test_sequences_d_echappement_sont_resolues(source: str, valeur: str) -> None:
    token = lex(source)[0]
    assert token.value == valeur
    assert token.lexeme == source


# ---------- Commentaires et espaces ----------


def test_commentaire_est_ignore_jusqu_a_la_fin_de_la_ligne() -> None:
    assert types_of("var x // un commentaire\nz") == [T.VAR, T.IDENT, T.IDENT]


def test_commentaire_en_fin_de_fichier_sans_retour_a_la_ligne() -> None:
    assert types_of("x // fin") == [T.IDENT]


def test_ligne_de_commentaire_seule() -> None:
    assert types_of("// rien\n") == []


def test_tabulations_et_crlf_sont_des_separateurs() -> None:
    assert types_of("var\tx\r\n=\r\n5") == [T.VAR, T.IDENT, T.ASIGNAR, T.ENTERO]


# ---------- Positions ----------


def test_positions_sur_une_ligne() -> None:
    tokens = lex("var x = 5;")
    assert [(t.line, t.column) for t in tokens] == [
        (1, 1),  # var
        (1, 5),  # x
        (1, 7),  # =
        (1, 9),  # 5
        (1, 10),  # ;
        (1, 11),  # FIN
    ]


def test_position_apres_un_retour_a_la_ligne_et_une_indentation() -> None:
    token = lex("var x\n  z")[2]
    assert (token.lexeme, token.line, token.column) == ("z", 2, 3)


def test_crlf_compte_pour_une_seule_ligne() -> None:
    token = lex("a\r\nb")[1]
    assert (token.line, token.column) == (2, 1)


def test_position_apres_un_commentaire() -> None:
    token = lex("// hola\nx")[0]
    assert (token.line, token.column) == (2, 1)


def test_chaine_est_positionnee_sur_son_guillemet_ouvrant() -> None:
    token = lex('mostrar "hola";')[1]
    assert (token.line, token.column) == (1, 9)


def test_fin_est_positionne_apres_le_dernier_caractere() -> None:
    fin = lex("ab\ncd")[-1]
    assert (fin.line, fin.column) == (2, 3)


# ---------- Générateur ----------


def test_tokenize_retourne_un_generateur() -> None:
    assert isinstance(tokenize("x"), types.GeneratorType)


def test_tokenize_ne_lit_rien_avant_la_premiere_demande() -> None:
    flux = tokenize("@")  # source invalide, mais aucune erreur pour l'instant
    with pytest.raises(LexError):
        next(flux)


def test_les_tokens_avant_l_erreur_sont_produits() -> None:
    flux = tokenize('var x "abc')
    assert next(flux).type is T.VAR
    assert next(flux).type is T.IDENT
    with pytest.raises(LexError):
        next(flux)


# ---------- Erreurs lexicales ----------


def test_chaine_non_terminee_en_fin_de_ligne_est_signalee_au_guillemet_ouvrant() -> None:
    erreur = error_of('mostrar "hola;')
    assert (erreur.line, erreur.column) == (1, 9)
    assert "non terminée" in erreur.message


def test_chaine_interrompue_par_un_retour_a_la_ligne() -> None:
    erreur = error_of('"abc\nx"')
    assert (erreur.line, erreur.column) == (1, 1)
    assert "non terminée" in erreur.message


def test_chaine_terminee_par_un_antislash_en_fin_de_source() -> None:
    erreur = error_of('"abc\\')
    assert (erreur.line, erreur.column) == (1, 1)


def test_sequence_d_echappement_inconnue_est_signalee_sur_l_antislash() -> None:
    erreur = error_of(r'"a\tb"')
    assert (erreur.line, erreur.column) == (1, 3)
    assert "\\t" in erreur.message


def test_caractere_inattendu() -> None:
    erreur = error_of("var x = @;")
    assert (erreur.line, erreur.column) == (1, 9)
    assert "'@'" in erreur.message


def test_lettre_accentuee_hors_chaine_est_refusee() -> None:
    erreur = error_of("café")
    assert (erreur.line, erreur.column) == (1, 4)


def test_accents_dans_une_chaine_sont_acceptes() -> None:
    assert lex('"café"')[0].value == "café"


def test_point_d_exclamation_seul() -> None:
    erreur = error_of("!x")
    assert (erreur.line, erreur.column) == (1, 1)


def test_point_seul() -> None:
    erreur = error_of("a.b")
    assert (erreur.line, erreur.column) == (1, 2)


def test_nombre_suivi_de_lettres() -> None:
    erreur = error_of("12abc")
    assert (erreur.line, erreur.column) == (1, 1)
    assert "chiffre" in erreur.message


def test_erreur_sur_la_deuxieme_ligne() -> None:
    erreur = error_of("var x = 1;\n  @")
    assert (erreur.line, erreur.column) == (2, 3)


def test_str_de_l_erreur_commence_par_la_position() -> None:
    erreur = error_of('mostrar "hola;')
    assert str(erreur) == "1:9: chaîne non terminée"


# ---------- Programmes d'exemple ----------


@pytest.mark.parametrize("chemin", EJEMPLOS, ids=lambda p: p.name)
def test_programme_d_exemple_est_entierement_decoupe_en_tokens(chemin: Path) -> None:
    source = chemin.read_text(encoding="utf-8-sig")
    tokens = lex(source)
    assert len(tokens) > 1
    assert tokens[-1].type is T.FIN
