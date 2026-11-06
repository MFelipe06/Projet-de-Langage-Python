import dataclasses

import pytest

from ardilla.ast_nodes import (
    Asignacion,
    Binario,
    BinaryOperator,
    Bloque,
    Booleano,
    Cadena,
    Declaracion,
    Devolver,
    Entero,
    ExpresionInstruccion,
    Expression,
    Funcion,
    Llamada,
    Mientras,
    Mostrar,
    Para,
    Programa,
    ProgramItem,
    Si,
    Statement,
    Unario,
    UnaryOperator,
    Variable,
)

POS = {"line": 1, "column": 1}


def entero(valor: int) -> Entero:
    return Entero(value=valor, **POS)


def variable(nombre: str) -> Variable:
    return Variable(name=nombre, **POS)


def bloque(*instrucciones: Statement) -> Bloque:
    return Bloque(statements=instrucciones, **POS)


# ---------- Construction et champs ----------


def test_noeud_expose_ses_champs_et_sa_position() -> None:
    noeud = Entero(value=5, line=3, column=7)
    assert (noeud.value, noeud.line, noeud.column) == (5, 3, 7)


def test_les_champs_doivent_etre_nommes() -> None:
    with pytest.raises(TypeError):
        Entero(5, 1, 1)  # type: ignore[misc]


def test_position_est_obligatoire() -> None:
    with pytest.raises(TypeError):
        Entero(value=5)  # type: ignore[call-arg]


def test_noeud_est_immuable() -> None:
    noeud = entero(5)
    with pytest.raises(dataclasses.FrozenInstanceError):
        noeud.value = 6  # type: ignore[misc]


# ---------- Égalité et hachage ----------


def test_noeuds_de_meme_structure_sont_egaux() -> None:
    assert entero(5) == entero(5)


def test_noeuds_de_valeurs_differentes_ne_sont_pas_egaux() -> None:
    assert entero(5) != entero(6)


def test_noeuds_de_types_differents_ne_sont_pas_egaux() -> None:
    assert Cadena(value="5", **POS) != Entero(value=5, **POS)


def test_la_position_ne_compte_pas_dans_l_egalite() -> None:
    assert Entero(value=5, line=1, column=1) == Entero(value=5, line=9, column=4)


def test_arbres_de_meme_structure_sont_egaux() -> None:
    def arbre(ligne: int) -> Binario:
        return Binario(
            operator=BinaryOperator.SUMA,
            left=Entero(value=1, line=ligne, column=1),
            right=Entero(value=2, line=ligne, column=5),
            line=ligne,
            column=3,
        )

    assert arbre(1) == arbre(2)


def test_arbres_dont_un_sous_noeud_differe_ne_sont_pas_egaux() -> None:
    def somme(droite: int) -> Binario:
        return Binario(
            operator=BinaryOperator.SUMA, left=entero(1), right=entero(droite), **POS
        )

    assert somme(2) != somme(3)


def test_noeud_avec_sous_noeuds_est_hachable() -> None:
    appel = Llamada(callee=variable("f"), arguments=(entero(1), entero(2)), **POS)
    assert len({appel, appel}) == 1


def test_noeuds_egaux_ont_le_meme_hachage() -> None:
    assert hash(entero(5)) == hash(Entero(value=5, line=8, column=8))


# ---------- Affichage ----------


def test_repr_est_lisible_et_sans_position() -> None:
    texte = repr(entero(5))
    assert texte == "Entero(value=5)"


def test_repr_d_un_arbre_montre_les_sous_noeuds() -> None:
    noeud = Unario(operator=UnaryOperator.NEGATIVO, operand=entero(5), **POS)
    assert "Entero(value=5)" in repr(noeud)


# ---------- Opérateurs ----------


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
def test_operateur_binaire_se_retrouve_par_son_symbole(
    symbole: str, attendu: BinaryOperator
) -> None:
    assert BinaryOperator(symbole) is attendu


def test_operateurs_binaires_sont_ceux_de_la_specification() -> None:
    valeurs = {operateur.value for operateur in BinaryOperator}
    assert valeurs == {"+", "-", "*", "/", "%", "==", "!=", "<", "<=", ">", ">=", "y", "o"}


@pytest.mark.parametrize(
    ("symbole", "attendu"),
    [("-", UnaryOperator.NEGATIVO), ("no", UnaryOperator.NO)],
)
def test_operateur_unaire_se_retrouve_par_son_symbole(
    symbole: str, attendu: UnaryOperator
) -> None:
    assert UnaryOperator(symbole) is attendu


def test_symbole_inconnu_n_est_pas_un_operateur() -> None:
    with pytest.raises(ValueError):
        BinaryOperator("**")


# ---------- Unions de types ----------


@pytest.mark.parametrize(
    "noeud",
    [
        entero(1),
        Cadena(value="a", **POS),
        Booleano(value=True, **POS),
        variable("x"),
        Unario(operator=UnaryOperator.NO, operand=variable("x"), **POS),
        Binario(operator=BinaryOperator.O, left=variable("a"), right=variable("b"), **POS),
        Llamada(callee=variable("f"), arguments=(), **POS),
    ],
    ids=lambda n: type(n).__name__,
)
def test_chaque_expression_appartient_a_l_union_expression(noeud: object) -> None:
    assert isinstance(noeud, Expression)
    assert not isinstance(noeud, Statement)


@pytest.mark.parametrize(
    "noeud",
    [
        Declaracion(name="x", value=entero(1), **POS),
        Asignacion(name="x", value=entero(1), **POS),
        Si(condition=variable("c"), then_branch=bloque(), else_branch=None, **POS),
        Mientras(condition=variable("c"), body=bloque(), **POS),
        Para(variable="k", start=entero(0), stop=entero(3), body=bloque(), **POS),
        Devolver(value=None, **POS),
        Mostrar(arguments=(), **POS),
        ExpresionInstruccion(expression=entero(1), **POS),
    ],
    ids=lambda n: type(n).__name__,
)
def test_chaque_instruction_appartient_a_l_union_statement(noeud: object) -> None:
    assert isinstance(noeud, Statement)
    assert not isinstance(noeud, Expression)


def test_une_fonction_est_un_element_de_programme_mais_pas_une_instruction() -> None:
    fonction = Funcion(name="f", parameters=(), body=bloque(), **POS)
    assert isinstance(fonction, ProgramItem)
    assert not isinstance(fonction, Statement)


def test_un_bloc_n_est_ni_une_instruction_ni_une_expression() -> None:
    assert not isinstance(bloque(), Statement | Expression)


# ---------- Cas particuliers de la grammaire ----------


def test_devolver_sans_valeur() -> None:
    assert Devolver(value=None, **POS).value is None


def test_mostrar_sans_argument() -> None:
    assert Mostrar(arguments=(), **POS).arguments == ()


def test_fonction_sans_parametre_a_un_tuple_vide() -> None:
    assert Funcion(name="f", parameters=(), body=bloque(), **POS).parameters == ()


def test_si_sans_sino() -> None:
    noeud = Si(condition=variable("c"), then_branch=bloque(), else_branch=None, **POS)
    assert noeud.else_branch is None


def test_si_avec_sino_simple_contient_un_bloc() -> None:
    noeud = Si(condition=variable("c"), then_branch=bloque(), else_branch=bloque(), **POS)
    assert isinstance(noeud.else_branch, Bloque)


def test_sino_si_contient_un_autre_si() -> None:
    interieur = Si(condition=variable("d"), then_branch=bloque(), else_branch=None, **POS)
    noeud = Si(condition=variable("c"), then_branch=bloque(), else_branch=interieur, **POS)
    assert isinstance(noeud.else_branch, Si)
    assert noeud.else_branch.condition == variable("d")


def test_appel_enchaine_f_de_1_de_2() -> None:
    interieur = Llamada(callee=variable("f"), arguments=(entero(1),), **POS)
    exterieur = Llamada(callee=interieur, arguments=(entero(2),), **POS)
    assert isinstance(exterieur.callee, Llamada)


# ---------- Un programme complet construit à la main ----------


def factorial() -> Programa:
    """Équivalent de ejemplos/factorial.ard."""
    corps = bloque(
        Si(
            condition=Binario(
                operator=BinaryOperator.MENOR_IGUAL,
                left=variable("n"),
                right=entero(1),
                **POS,
            ),
            then_branch=bloque(Devolver(value=entero(1), **POS)),
            else_branch=None,
            **POS,
        ),
        Devolver(
            value=Binario(
                operator=BinaryOperator.MULTIPLICACION,
                left=variable("n"),
                right=Llamada(
                    callee=variable("factorial"),
                    arguments=(
                        Binario(
                            operator=BinaryOperator.RESTA,
                            left=variable("n"),
                            right=entero(1),
                            **POS,
                        ),
                    ),
                    **POS,
                ),
                **POS,
            ),
            **POS,
        ),
    )
    boucle = Para(
        variable="k",
        start=entero(0),
        stop=entero(6),
        body=bloque(
            Mostrar(
                arguments=(
                    variable("k"),
                    Llamada(callee=variable("factorial"), arguments=(variable("k"),), **POS),
                ),
                **POS,
            )
        ),
        **POS,
    )
    fonction = Funcion(name="factorial", parameters=("n",), body=corps, **POS)
    return Programa(items=(fonction, boucle), **POS)


def test_programme_factorial_a_une_fonction_puis_une_boucle() -> None:
    programme = factorial()
    assert [type(element).__name__ for element in programme.items] == ["Funcion", "Para"]


def test_on_descend_dans_l_arbre_du_programme_factorial() -> None:
    fonction = factorial().items[0]
    assert isinstance(fonction, Funcion)
    assert fonction.name == "factorial"
    assert fonction.parameters == ("n",)
    premiere = fonction.body.statements[0]
    assert isinstance(premiere, Si)
    assert isinstance(premiere.condition, Binario)
    assert premiere.condition.operator is BinaryOperator.MENOR_IGUAL


def test_deux_constructions_du_programme_factorial_sont_egales() -> None:
    assert factorial() == factorial()


# ---------- match : aperçu de l'étape 8 ----------


def decrire(expression: Expression) -> str:
    match expression:
        case Entero(value=valeur):
            return f"entier {valeur}"
        case Binario(operator=BinaryOperator.SUMA):
            return "addition"
        case Binario():
            return "autre opération binaire"
        case _:
            return "autre expression"


def test_match_reconnait_les_noeuds_par_leur_type_et_leurs_champs() -> None:
    somme = Binario(operator=BinaryOperator.SUMA, left=entero(1), right=entero(2), **POS)
    produit = Binario(
        operator=BinaryOperator.MULTIPLICACION, left=entero(1), right=entero(2), **POS
    )
    assert decrire(entero(7)) == "entier 7"
    assert decrire(somme) == "addition"
    assert decrire(produit) == "autre opération binaire"
    assert decrire(variable("x")) == "autre expression"
