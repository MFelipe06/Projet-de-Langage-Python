import pytest

from ardilla.ast_nodes import (
    Binario,
    BinaryOperator,
    Booleano,
    Cadena,
    Entero,
    Expression,
    Llamada,
    Unario,
    UnaryOperator,
    Variable,
)
from ardilla.errors import ArdillaError, LexError, ParseError
from ardilla.lexer import tokenize
from ardilla.parser import (
    COMPARISON_TYPES,
    INFIX_PARSELETS,
    PREFIX_PARSELETS,
    Parser,
    Power,
    infix,
    parse_expression_source,
    prefix,
)
from ardilla.tokens import Token, TokenType

T = TokenType
parse = parse_expression_source


def show(expression: Expression) -> str:
    """Écrit un arbre entièrement parenthésé : rend la priorité visible."""
    match expression:
        case Entero(value=valeur) | Booleano(value=valeur):
            return str(valeur)
        case Cadena(value=texte):
            return repr(texte)
        case Variable(name=nom):
            return nom
        case Unario(operator=operateur, operand=operande):
            return f"({operateur.value} {show(operande)})"
        case Binario(operator=operateur, left=gauche, right=droite):
            return f"({show(gauche)} {operateur.value} {show(droite)})"
        case Llamada(callee=appele, arguments=arguments):
            return f"{show(appele)}({', '.join(show(a) for a in arguments)})"
    raise AssertionError(f"nœud inattendu : {expression!r}")


def erreur(source: str) -> ParseError:
    with pytest.raises(ParseError) as info:
        parse(source)
    return info.value


# ---------- Expressions simples ----------


def test_entier() -> None:
    assert parse("42") == Entero(value=42, line=1, column=1)


def test_chaine_a_sa_valeur_sans_guillemets() -> None:
    noeud = parse('"hola"')
    assert isinstance(noeud, Cadena)
    assert noeud.value == "hola"


@pytest.mark.parametrize(
    ("source", "valeur"), [("verdadero", True), ("falso", False)]
)
def test_booleen(source: str, valeur: bool) -> None:
    noeud = parse(source)
    assert isinstance(noeud, Booleano)
    assert noeud.value is valeur


def test_variable() -> None:
    noeud = parse("total")
    assert isinstance(noeud, Variable)
    assert noeud.name == "total"


def test_parentheses_ne_laissent_pas_de_trace_dans_l_arbre() -> None:
    assert parse("((5))") == parse("5")


# ---------- Priorité et associativité ----------


@pytest.mark.parametrize(
    ("source", "attendu"),
    [
        ("1 + 2 * 3", "(1 + (2 * 3))"),
        ("1 * 2 + 3", "((1 * 2) + 3)"),
        ("1 - 2 - 3", "((1 - 2) - 3)"),
        ("8 / 4 / 2", "((8 / 4) / 2)"),
        ("10 % 4 * 2", "((10 % 4) * 2)"),
        ("1 + 2 - 3 + 4", "(((1 + 2) - 3) + 4)"),
        ("(1 + 2) * 3", "((1 + 2) * 3)"),
        ("2 * (3 + 4)", "(2 * (3 + 4))"),
        ("a + 1 < b * 2", "((a + 1) < (b * 2))"),
        ("a o b y c", "(a o (b y c))"),
        ("a y b o c", "((a y b) o c)"),
        ("a o b o c", "((a o b) o c)"),
        ("a y b y c", "((a y b) y c)"),
        ("a < b y c > d", "((a < b) y (c > d))"),
        ("a == b o c != d", "((a == b) o (c != d))"),
    ],
)
def test_priorite_et_associativite(source: str, attendu: str) -> None:
    assert show(parse(source)) == attendu


@pytest.mark.parametrize(
    ("source", "attendu"),
    [
        ("-1 + 2", "((- 1) + 2)"),
        ("-2 * 3", "((- 2) * 3)"),
        ("- - 5", "(- (- 5))"),
        ("a - -b", "(a - (- b))"),
        ("2 * -3", "(2 * (- 3))"),
        ("-f(x)", "(- f(x))"),
        ("no a y b", "((no a) y b)"),
        ("no a o b", "((no a) o b)"),
        ("no a == b", "(no (a == b))"),
        ("no no x", "(no (no x))"),
        ("a y no b", "(a y (no b))"),
        ("a o no b y c", "(a o ((no b) y c))"),
        ("no a + 1 < 2", "(no ((a + 1) < 2))"),
    ],
)
def test_operateurs_unaires(source: str, attendu: str) -> None:
    assert show(parse(source)) == attendu


@pytest.mark.parametrize(
    ("symbole", "attendu"),
    [
        ("+", BinaryOperator.SUMA),
        ("-", BinaryOperator.RESTA),
        ("*", BinaryOperator.MULTIPLICACION),
        ("/", BinaryOperator.DIVISION),
        ("%", BinaryOperator.RESTO),
        ("==", BinaryOperator.IGUAL),
        ("!=", BinaryOperator.DISTINTO),
        ("<", BinaryOperator.MENOR),
        ("<=", BinaryOperator.MENOR_IGUAL),
        (">", BinaryOperator.MAYOR),
        (">=", BinaryOperator.MAYOR_IGUAL),
        ("y", BinaryOperator.Y),
        ("o", BinaryOperator.O),
    ],
)
def test_chaque_operateur_binaire_est_reconnu(
    symbole: str, attendu: BinaryOperator
) -> None:
    noeud = parse(f"a {symbole} b")
    assert isinstance(noeud, Binario)
    assert noeud.operator is attendu


@pytest.mark.parametrize(
    ("source", "attendu"),
    [("-x", UnaryOperator.NEGATIVO), ("no x", UnaryOperator.NO)],
)
def test_operateur_unaire_est_reconnu(source: str, attendu: UnaryOperator) -> None:
    noeud = parse(source)
    assert isinstance(noeud, Unario)
    assert noeud.operator is attendu


def test_longue_chaine_d_additions_ne_depasse_pas_la_pile() -> None:
    assert isinstance(parse(" + ".join(["1"] * 2000)), Binario)


def test_parentheses_imbriquees() -> None:
    assert parse("(" * 100 + "5" + ")" * 100) == parse("5")


# ---------- Appels de fonction ----------


@pytest.mark.parametrize(
    ("source", "attendu"),
    [
        ("f()", "f()"),
        ("f(1)", "f(1)"),
        ("f(1, 2 + 3)", "f(1, (2 + 3))"),
        ("f(g(x), h())", "f(g(x), h())"),
        ("f(1)(2)", "f(1)(2)"),
        ("f(x) + 1", "(f(x) + 1)"),
        ("1 + f(2) * 3", "(1 + (f(2) * 3))"),
        ("no f(x)", "(no f(x))"),
        ("n * factorial(n - 1)", "(n * factorial((n - 1)))"),
        ("(f)(x)", "f(x)"),
        ("f(a < b, c y d)", "f((a < b), (c y d))"),
    ],
)
def test_appels(source: str, attendu: str) -> None:
    assert show(parse(source)) == attendu


def test_appel_sans_argument_a_un_tuple_vide() -> None:
    noeud = parse("f()")
    assert isinstance(noeud, Llamada)
    assert noeud.arguments == ()


# ---------- Expressions tirées des programmes d'exemple ----------


@pytest.mark.parametrize(
    ("source", "attendu"),
    [
        ("n <= 1", "(n <= 1)"),
        ("n % 15 == 0", "((n % 15) == 0)"),
        ("i <= 10", "(i <= 10)"),
        ("total + i", "(total + i)"),
        ('"suma:"', "'suma:'"),
    ],
)
def test_expressions_des_exemples(source: str, attendu: str) -> None:
    assert show(parse(source)) == attendu


# ---------- Positions ----------


def test_binario_a_la_position_de_son_premier_token() -> None:
    noeud = parse("  1 + 2")
    assert (noeud.line, noeud.column) == (1, 3)


def test_unario_a_la_position_de_son_operateur() -> None:
    noeud = parse("  - 5")
    assert (noeud.line, noeud.column) == (1, 3)


def test_llamada_a_la_position_de_la_fonction_appelee() -> None:
    noeud = parse("  f(1)")
    assert (noeud.line, noeud.column) == (1, 3)


def test_position_sur_une_deuxieme_ligne() -> None:
    noeud = parse("1 +\n  x")
    assert isinstance(noeud, Binario)
    assert (noeud.right.line, noeud.right.column) == (2, 3)


# ---------- Erreurs de syntaxe ----------


def test_expression_vide() -> None:
    e = erreur("")
    assert (e.line, e.column) == (1, 1)
    assert "expression attendue" in e.message


def test_operande_manquant_apres_un_operateur() -> None:
    e = erreur("1 +")
    assert (e.line, e.column) == (1, 4)
    assert "fin du fichier" in e.message


def test_erreur_est_juste_apres_le_dernier_token_meme_si_la_ligne_est_finie() -> None:
    e = erreur("1 +\n")
    assert (e.line, e.column) == (1, 4)


def test_operateur_inattendu_a_la_place_d_un_operande() -> None:
    e = erreur("1 + * 2")
    assert (e.line, e.column) == (1, 4)
    assert "'*'" in e.message


def test_parenthese_fermante_manquante() -> None:
    e = erreur("(1 + 2")
    assert (e.line, e.column) == (1, 7)
    assert "')' attendu" in e.message


def test_parentheses_vides() -> None:
    e = erreur("()")
    assert (e.line, e.column) == (1, 2)


def test_parenthese_fermante_en_trop() -> None:
    e = erreur("1 + 2)")
    assert (e.line, e.column) == (1, 6)
    assert "')'" in e.message


def test_deux_operandes_sans_operateur() -> None:
    e = erreur("1 2")
    assert (e.line, e.column) == (1, 2)
    assert "'2'" in e.message


def test_appel_sans_parenthese_fermante() -> None:
    e = erreur("f(1")
    assert (e.line, e.column) == (1, 4)


def test_appel_avec_deux_arguments_sans_virgule() -> None:
    e = erreur("f(1 2)")
    assert (e.line, e.column) == (1, 4)
    assert "')' attendu" in e.message


def test_virgule_finale_dans_un_appel() -> None:
    e = erreur("f(1,)")
    assert (e.line, e.column) == (1, 5)
    assert "expression attendue" in e.message


@pytest.mark.parametrize(
    ("source", "colonne"),
    [("a < b < c", 7), ("a == b != c", 8), ("a < b == c", 7), ("1 <= 2 >= 3", 8)],
)
def test_comparaisons_chainees_sont_refusees_sur_le_deuxieme_operateur(
    source: str, colonne: int
) -> None:
    e = erreur(source)
    assert (e.line, e.column) == (1, colonne)
    assert "ne se chaînent pas" in e.message


def test_comparaisons_chainees_avec_parentheses_sont_acceptees() -> None:
    assert show(parse("(a < b) < c")) == "((a < b) < c)"


@pytest.mark.parametrize(
    ("source", "colonne"),
    [("1 + no x", 5), ("-no x", 2), ("a == no b", 6), ("2 * no x", 5)],
)
def test_no_sans_parentheses_apres_un_operateur_plus_fort_est_refuse(
    source: str, colonne: int
) -> None:
    e = erreur(source)
    assert (e.line, e.column) == (1, colonne)
    assert "'no'" in e.message


def test_no_entre_parentheses_est_accepte_partout() -> None:
    assert show(parse("1 + (no x)")) == "(1 + (no x))"


def test_les_erreurs_lexicales_traversent_le_parser() -> None:
    with pytest.raises(LexError):
        parse("1 + @")


def test_parse_error_est_une_erreur_ardilla() -> None:
    assert issubclass(ParseError, ArdillaError)


def test_str_de_l_erreur_commence_par_la_position() -> None:
    assert str(erreur("(1 + 2")).startswith("1:7: ")


# ---------- Les tables et les décorateurs ----------


def test_tokens_qui_peuvent_commencer_une_expression() -> None:
    assert set(PREFIX_PARSELETS) == {
        T.ENTERO,
        T.CADENA,
        T.VERDADERO,
        T.FALSO,
        T.IDENT,
        T.PAREN_IZQ,
        T.NO,
        T.MENOS,
    }


def test_tokens_qui_peuvent_continuer_une_expression() -> None:
    assert set(INFIX_PARSELETS) == {
        T.O,
        T.Y,
        T.MAS,
        T.MENOS,
        T.POR,
        T.ENTRE,
        T.RESTO,
        T.PAREN_IZQ,
    } | COMPARISON_TYPES


def test_puissances_de_liaison_sont_dans_l_ordre_de_la_specification() -> None:
    assert (
        Power.OR
        < Power.AND
        < Power.NOT
        < Power.COMPARISON
        < Power.ADDITIVE
        < Power.MULTIPLICATIVE
        < Power.UNARY_MINUS
        < Power.CALL
        < Power.PRIMARY
    )


@pytest.mark.parametrize(
    ("token_type", "puissance"),
    [
        (T.O, Power.OR),
        (T.Y, Power.AND),
        (T.MENOR, Power.COMPARISON),
        (T.MAS, Power.ADDITIVE),
        (T.MENOS, Power.ADDITIVE),
        (T.POR, Power.MULTIPLICATIVE),
        (T.RESTO, Power.MULTIPLICATIVE),
        (T.PAREN_IZQ, Power.CALL),
    ],
)
def test_puissance_infixe_enregistree(token_type: TokenType, puissance: Power) -> None:
    assert INFIX_PARSELETS[token_type].power == puissance


def test_les_decorateurs_retournent_la_fonction_inchangee() -> None:
    def parselet_prefixe(parser: Parser, token: Token) -> Expression:
        raise NotImplementedError

    def parselet_infixe(parser: Parser, left: Expression, token: Token) -> Expression:
        raise NotImplementedError

    try:
        assert prefix(T.COMA)(parselet_prefixe) is parselet_prefixe
        assert infix(T.COMA, power=5)(parselet_infixe) is parselet_infixe
        assert PREFIX_PARSELETS[T.COMA].function is parselet_prefixe
        assert INFIX_PARSELETS[T.COMA].power == 5
    finally:
        PREFIX_PARSELETS.pop(T.COMA, None)
        INFIX_PARSELETS.pop(T.COMA, None)


# ---------- La classe Parser ----------


def test_parser_refuse_une_liste_sans_fin() -> None:
    with pytest.raises(ValueError):
        Parser([])


def test_peek_ne_consomme_pas() -> None:
    parser = Parser(tokenize("x y"))
    assert parser.peek() is parser.peek()


def test_advance_retourne_le_token_courant_puis_passe_au_suivant() -> None:
    parser = Parser(tokenize("x y"))
    assert parser.advance().lexeme == "x"
    assert parser.peek().lexeme == "y"


def test_advance_reste_sur_fin() -> None:
    parser = Parser(tokenize(""))
    assert parser.advance().type is T.FIN
    assert parser.advance().type is T.FIN


def test_match_consomme_seulement_si_le_type_correspond() -> None:
    parser = Parser(tokenize("x ,"))
    assert parser.match(T.COMA) is None
    assert parser.match(T.IDENT) is not None
    assert parser.match(T.COMA) is not None


def test_expect_leve_une_parse_error_avec_le_message_attendu() -> None:
    parser = Parser(tokenize("x"))
    parser.advance()
    with pytest.raises(ParseError, match="';' attendu"):
        parser.expect(T.PUNTO_Y_COMA, "';'")


def test_parser_laisse_les_tokens_suivants_apres_une_expression() -> None:
    parser = Parser(tokenize("1 + 2 ; x"))
    parser.parse_expression()
    assert parser.peek().type is T.PUNTO_Y_COMA
