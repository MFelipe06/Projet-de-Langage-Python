import pytest

from ardilla.errors import ArdillaError
from ardilla.parser import parse_source
from ardilla.semantic import SemanticError, SemanticErrors, analyze


def check(source: str) -> None:
    analyze(parse_source(source))


def semantic_errors(source: str) -> SemanticErrors:
    with pytest.raises(SemanticErrors) as info:
        check(source)
    return info.value


def test_programme_sans_erreur_semantique() -> None:
    check(
        "var total = 0; "
        "funcion somme(n) { var resultat = n + total; devolver resultat; } "
        "mostrar somme(3);"
    )


def test_fonctions_peuvent_s_appeler_avant_leur_declaration() -> None:
    check("funcion premier() { devolver suivant(); } funcion suivant() { devolver 1; }")


def test_variable_non_declaree_dans_une_expression() -> None:
    error = semantic_errors("mostrar absent;").errors[0]

    assert error.message == "la variable 'absent' n'est pas déclarée"
    assert (error.line, error.column) == (1, 9)


def test_affectation_a_une_variable_non_declaree() -> None:
    error = semantic_errors("x = 1;").errors[0]

    assert "variable 'x'" in error.message
    assert (error.line, error.column) == (1, 1)


def test_declaration_est_visible_apres_son_initialisation() -> None:
    errors = semantic_errors("var x = x;")

    assert len(errors.errors) == 1
    assert errors.errors[0].message == "la variable 'x' n'est pas déclarée"


def test_declaration_dupliquee_dans_le_meme_bloc() -> None:
    error = semantic_errors("var x = 1; var x = 2;").errors[0]

    assert "déjà déclarée" in error.message
    assert (error.line, error.column) == (1, 12)


def test_declaration_dans_un_bloc_interne_ne_se_propage_pas() -> None:
    error = semantic_errors("si verdadero { var interne = 1; } mostrar interne;")
    assert len(error.errors) == 1
    assert error.errors[0].message == "la variable 'interne' n'est pas déclarée"


def test_bloc_interne_peut_lire_une_variable_exterieure() -> None:
    check("var x = 1; si verdadero { mostrar x; }")


def test_redéclaration_dans_un_bloc_interne_est_autorisee() -> None:
    check("var x = 1; si verdadero { var x = 2; mostrar x; }")


def test_variable_de_boucle_est_disponible_dans_son_corps_seulement() -> None:
    error = semantic_errors("para k en 0..2 { mostrar k; } mostrar k;")

    assert len(error.errors) == 1
    assert error.errors[0].message == "la variable 'k' n'est pas déclarée"
    assert (error.errors[0].line, error.errors[0].column) == (1, 39)


def test_borne_de_boucle_est_evaluee_avant_declarer_sa_variable() -> None:
    errors = semantic_errors("para k en k..2 {}")

    assert len(errors.errors) == 1
    assert errors.errors[0].message == "la variable 'k' n'est pas déclarée"


def test_parametres_sont_declares_dans_la_portee_de_fonction() -> None:
    check("funcion f(x) { var resultat = x; devolver resultat; }")


def test_parametres_dupliques_sont_signales() -> None:
    error = semantic_errors("funcion f(x, x) {}").errors[0]

    assert "variable 'x' est déjà déclarée" in error.message


def test_fonction_dupliquee_est_signalee() -> None:
    error = semantic_errors("funcion f() {} funcion f() {}").errors[0]

    assert error.message == "la fonction 'f' est déjà déclarée"


def test_appel_a_une_fonction_inexistante() -> None:
    error = semantic_errors("inconnue();").errors[0]

    assert error.message == "la fonction 'inconnue' n'est pas déclarée"
    assert (error.line, error.column) == (1, 1)


@pytest.mark.parametrize(
    ("source", "message"),
    [
        ("funcion f(x) {} f();", "0 reçu(s)"),
        ("funcion f() {} f(1);", "1 reçu(s)"),
    ],
)
def test_nombre_d_arguments_incorrect(source: str, message: str) -> None:
    error = semantic_errors(source).errors[0]

    assert "attend" in error.message
    assert message in error.message


def test_appel_d_une_expression_qui_n_est_pas_un_nom_de_fonction() -> None:
    error = semantic_errors("(1)(2);").errors[0]

    assert error.message == "seul le nom d'une fonction peut être appelé"


def test_devolver_hors_d_une_fonction() -> None:
    error = semantic_errors("si verdadero { devolver 1; }").errors[0]

    assert error.message == "'devolver' n'est autorisé que dans une fonction"
    assert (error.line, error.column) == (1, 16)


def test_erreurs_sont_collectees_et_chainees() -> None:
    errors = semantic_errors("mostrar x; autre = 1; z(); devolver;")

    assert len(errors.errors) == 4
    assert all(isinstance(error, SemanticError) for error in errors.errors)
    assert isinstance(errors, ArdillaError)
    assert errors.__cause__ is errors.errors[0]


def test_analyseur_peut_etre_reutilise_apres_une_erreur() -> None:
    from ardilla.semantic import SemanticAnalyzer

    analyzer = SemanticAnalyzer()
    with pytest.raises(SemanticErrors):
        analyzer.analyze(parse_source("mostrar x;"))

    analyzer.analyze(parse_source("mostrar;"))
