"""Nœuds de l'arbre syntaxique abstrait (AST) d'Ardilla (étape 4).

Chaque règle de la grammaire EBNF qui produit un élément du programme a ici
son nœud. Le parser (étapes 5 et 6) construit ces objets ; l'analyse
sémantique (étape 7) et le générateur de Python (étape 8) les parcourent.

Choix de conception :
- les nœuds sont immuables (`frozen=True`) et ne contiennent que des tuples,
  jamais de listes : ils restent hashables ;
- tous les champs se passent par leur nom (`kw_only=True`) ;
- `line` et `column` (à partir de 1) servent aux messages d'erreur, mais ils
  sont exclus de la comparaison : deux nœuds de même structure sont égaux
  même s'ils n'ont pas la même position.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class BinaryOperator(Enum):
    """Opérateurs binaires. La valeur est le symbole écrit dans la source."""

    SUMA = "+"
    RESTA = "-"
    MULTIPLICACION = "*"
    DIVISION = "/"
    RESTO = "%"
    IGUAL = "=="
    DISTINTO = "!="
    MENOR = "<"
    MENOR_IGUAL = "<="
    MAYOR = ">"
    MAYOR_IGUAL = ">="
    Y = "y"
    O = "o"


class UnaryOperator(Enum):
    """Opérateurs unaires : le moins (`-x`) et la négation logique (`no x`)."""

    NEGATIVO = "-"
    NO = "no"


@dataclass(frozen=True, kw_only=True)
class Node:
    """Base de tous les nœuds : leur position dans la source."""

    line: int = field(compare=False, repr=False)
    column: int = field(compare=False, repr=False)


# ---------- Expressions ----------


@dataclass(frozen=True, kw_only=True)
class Entero(Node):
    value: int


@dataclass(frozen=True, kw_only=True)
class Cadena(Node):
    value: str


@dataclass(frozen=True, kw_only=True)
class Booleano(Node):
    value: bool


@dataclass(frozen=True, kw_only=True)
class Variable(Node):
    name: str


@dataclass(frozen=True, kw_only=True)
class Unario(Node):
    operator: UnaryOperator
    operand: Expression


@dataclass(frozen=True, kw_only=True)
class Binario(Node):
    operator: BinaryOperator
    left: Expression
    right: Expression


@dataclass(frozen=True, kw_only=True)
class Llamada(Node):
    """Appel de fonction. La grammaire permet n'importe quelle expression comme
    `callee` ; c'est l'analyse sémantique qui exigera une `Variable`."""

    callee: Expression
    arguments: tuple[Expression, ...]


# ---------- Instructions ----------


@dataclass(frozen=True, kw_only=True)
class Bloque(Node):
    statements: tuple[Statement, ...]


@dataclass(frozen=True, kw_only=True)
class Declaracion(Node):
    """`var nombre = valor;`"""

    name: str
    value: Expression


@dataclass(frozen=True, kw_only=True)
class Asignacion(Node):
    """`nombre = valor;`"""

    name: str
    value: Expression


@dataclass(frozen=True, kw_only=True)
class Si(Node):
    """`si condition { ... }`, avec éventuellement un `sino`.

    `else_branch` vaut None (pas de `sino`), un `Bloque` (`sino { ... }`)
    ou un autre `Si` (`sino si ...`).
    """

    condition: Expression
    then_branch: Bloque
    else_branch: Bloque | Si | None


@dataclass(frozen=True, kw_only=True)
class Mientras(Node):
    condition: Expression
    body: Bloque


@dataclass(frozen=True, kw_only=True)
class Para(Node):
    """`para variable en start..stop { ... }` (`stop` est exclu)."""

    variable: str
    start: Expression
    stop: Expression
    body: Bloque


@dataclass(frozen=True, kw_only=True)
class Devolver(Node):
    """`devolver;` (value vaut None) ou `devolver expresion;`"""

    value: Expression | None


@dataclass(frozen=True, kw_only=True)
class Mostrar(Node):
    """`mostrar a, b;` ; `arguments` peut être vide."""

    arguments: tuple[Expression, ...]


@dataclass(frozen=True, kw_only=True)
class ExpresionInstruccion(Node):
    """Une expression utilisée comme instruction : `f(3);`"""

    expression: Expression


# ---------- Fonctions et programme ----------


@dataclass(frozen=True, kw_only=True)
class Funcion(Node):
    name: str
    parameters: tuple[str, ...]
    body: Bloque


@dataclass(frozen=True, kw_only=True)
class Programa(Node):
    items: tuple[ProgramItem, ...]


# ---------- Unions de types ----------
# Dire « une expression est l'un de ces nœuds » permet à mypy de vérifier
# que l'on traite tous les cas (voir `assert_never` à l'étape 8).

Expression = Entero | Cadena | Booleano | Variable | Unario | Binario | Llamada

Statement = (
    Declaracion
    | Asignacion
    | Si
    | Mientras
    | Para
    | Devolver
    | Mostrar
    | ExpresionInstruccion
)

ProgramItem = Funcion | Statement
