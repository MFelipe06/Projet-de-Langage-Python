"""Parser d'Ardilla, partie expressions (étape 5) : méthode de Pratt.

Chaque type de token est associé à une fonction (un *parselet*) qui sait le
traiter. Deux tables les regroupent :
- `PREFIX_PARSELETS` : tokens qui peuvent **commencer** une expression
  (un nombre, `-`, `no`, `(`...) ;
- `INFIX_PARSELETS` : tokens qui **continuent** une expression déjà lue
  (`+`, `y`, `<`, `(` pour un appel...), avec leur puissance de liaison.

Les décorateurs `@prefix(...)` et `@infix(...)` remplissent ces tables.
Pour ajouter un opérateur au langage, on ajoute une fonction décorée.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from enum import IntEnum
from typing import NamedTuple

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
from ardilla.errors import ParseError, ParseErrors
from ardilla.lexer import tokenize
from ardilla.tokens import Token, TokenType


class Power(IntEnum):
    """Puissances de liaison : plus le nombre est grand, plus l'opérateur lie fort.

    Ces niveaux sont ceux du tableau de priorité de la spécification.
    """

    OR = 10
    AND = 20
    NOT = 30
    COMPARISON = 40
    ADDITIVE = 50
    MULTIPLICATIVE = 60
    UNARY_MINUS = 70
    CALL = 80
    PRIMARY = 100


PrefixFunction = Callable[["Parser", Token], Expression]
InfixFunction = Callable[["Parser", Expression, Token], Expression]


class PrefixEntry(NamedTuple):
    power: int
    function: PrefixFunction


class InfixEntry(NamedTuple):
    power: int
    function: InfixFunction


PREFIX_PARSELETS: dict[TokenType, PrefixEntry] = {}
INFIX_PARSELETS: dict[TokenType, InfixEntry] = {}

COMPARISON_TYPES = frozenset(
    {
        TokenType.IGUAL_IGUAL,
        TokenType.DISTINTO,
        TokenType.MENOR,
        TokenType.MENOR_IGUAL,
        TokenType.MAYOR,
        TokenType.MAYOR_IGUAL,
    }
)


# ---------- Décorateurs paramétrés ----------


def prefix(
    *token_types: TokenType, power: int = Power.PRIMARY
) -> Callable[[PrefixFunction], PrefixFunction]:
    """Enregistre une fonction comme parselet préfixe de ces types de token.

    `power` est le niveau de la construction : elle n'est acceptée que là où
    la puissance courante lui est strictement inférieure (voir `no`).
    """

    def register(function: PrefixFunction) -> PrefixFunction:
        for token_type in token_types:
            PREFIX_PARSELETS[token_type] = PrefixEntry(power, function)
        return function

    return register


def infix(
    *token_types: TokenType, power: int
) -> Callable[[InfixFunction], InfixFunction]:
    """Enregistre une fonction comme parselet infixe de ces types de token."""

    def register(function: InfixFunction) -> InfixFunction:
        for token_type in token_types:
            INFIX_PARSELETS[token_type] = InfixEntry(power, function)
        return function

    return register


def _describe(token: Token) -> str:
    if token.type is TokenType.FIN:
        return "fin du fichier"
    return f"'{token.lexeme}'"


# ---------- Le parser ----------


class Parser:
    """Lit une liste de tokens (terminée par FIN) et construit l'arbre."""

    def __init__(self, tokens: Iterable[Token]) -> None:
        self._tokens = list(tokens)
        if not self._tokens or self._tokens[-1].type is not TokenType.FIN:
            raise ValueError("la liste de tokens doit se terminer par FIN")
        self._index = 0
        self._errors: list[ParseError] = []

    # -- Navigation --

    def peek(self) -> Token:
        """Retourne le token courant sans le consommer."""
        return self._tokens[self._index]

    def advance(self) -> Token:
        """Consomme et retourne le token courant. Reste sur FIN une fois arrivé."""
        token = self._tokens[self._index]
        if token.type is not TokenType.FIN:
            self._index += 1
        return token

    def check(self, token_type: TokenType) -> bool:
        return self.peek().type is token_type

    def peek_next(self) -> Token:
        """Retourne le token suivant sans le consommer."""
        return self._tokens[min(self._index + 1, len(self._tokens) - 1)]

    def match(self, token_type: TokenType) -> Token | None:
        """Consomme le token courant s'il est de ce type, sinon retourne None."""
        if self.check(token_type):
            return self.advance()
        return None

    def expect(self, token_type: TokenType, what: str) -> Token:
        """Consomme un token du type attendu ou lève une ParseError."""
        if self.check(token_type):
            return self.advance()
        raise self.missing(f"{what} attendu, trouvé {_describe(self.peek())}")

    def expect_end(self) -> None:
        """Vérifie que tous les tokens ont été consommés."""
        if not self.check(TokenType.FIN):
            raise self.missing(
                f"opérateur ou fin de l'expression attendu, trouvé {_describe(self.peek())}"
            )

    # -- Programmes et instructions --

    def parse_program(self) -> Programa:
        """Analyse un programme et collecte les erreurs syntaxiques récupérables."""
        self._errors = []
        items: list[ProgramItem] = []
        start = self.peek()

        while not self.check(TokenType.FIN):
            previous_index = self._index
            try:
                if self.check(TokenType.FUNCION):
                    items.append(self.parse_function())
                else:
                    items.append(self.parse_statement())
            except ParseError as error:
                self._errors.append(error)
                self._synchronize(stop_at_function=True, stop_at_block_end=False)
                if self._index == previous_index and not self.check(TokenType.FIN):
                    self.advance()

        if self._errors:
            errors = tuple(self._errors)
            raise ParseErrors(errors) from errors[0]

        return Programa(items=tuple(items), line=start.line, column=start.column)

    def parse_function(self) -> Funcion:
        function_token = self.expect(TokenType.FUNCION, "'funcion'")
        name = self.expect(TokenType.IDENT, "nom de fonction")
        self.expect(TokenType.PAREN_IZQ, "'('")

        parameters: list[str] = []
        if not self.check(TokenType.PAREN_DER):
            parameters.append(self.expect(TokenType.IDENT, "paramètre").lexeme)
            while self.match(TokenType.COMA):
                parameters.append(self.expect(TokenType.IDENT, "paramètre").lexeme)

        self.expect(TokenType.PAREN_DER, "')'")
        body = self.parse_block()
        return Funcion(
            name=name.lexeme,
            parameters=tuple(parameters),
            body=body,
            line=function_token.line,
            column=function_token.column,
        )

    def parse_block(self) -> Bloque:
        opening = self.expect(TokenType.LLAVE_IZQ, "'{'")
        statements: list[Statement] = []

        while not self.check(TokenType.FIN) and not self.check(TokenType.LLAVE_DER):
            previous_index = self._index
            try:
                statements.append(self.parse_statement())
            except ParseError as error:
                self._errors.append(error)
                self._synchronize(stop_at_function=False, stop_at_block_end=True)
                if self._index == previous_index and not self.check(
                    TokenType.LLAVE_DER
                ):
                    self.advance()

        self.expect(TokenType.LLAVE_DER, "'}'")
        return Bloque(
            statements=tuple(statements),
            line=opening.line,
            column=opening.column,
        )

    def parse_statement(self) -> Statement:
        token = self.peek()
        if token.type is TokenType.VAR:
            return self.parse_declaration()
        if token.type is TokenType.IDENT and self.peek_next().type is TokenType.ASIGNAR:
            return self.parse_assignment()
        if token.type is TokenType.SI:
            return self.parse_if()
        if token.type is TokenType.MIENTRAS:
            return self.parse_while()
        if token.type is TokenType.PARA:
            return self.parse_for()
        if token.type is TokenType.DEVOLVER:
            return self.parse_return()
        if token.type is TokenType.MOSTRAR:
            return self.parse_print()

        expression = self.parse_expression()
        self.expect(TokenType.PUNTO_Y_COMA, "';'")
        return ExpresionInstruccion(
            expression=expression,
            line=expression.line,
            column=expression.column,
        )

    def parse_declaration(self) -> Declaracion:
        start = self.advance()
        name = self.expect(TokenType.IDENT, "nom de variable")
        self.expect(TokenType.ASIGNAR, "'='")
        value = self.parse_expression()
        self.expect(TokenType.PUNTO_Y_COMA, "';'")
        return Declaracion(
            name=name.lexeme,
            value=value,
            line=start.line,
            column=start.column,
        )

    def parse_assignment(self) -> Asignacion:
        name = self.advance()
        self.expect(TokenType.ASIGNAR, "'='")
        value = self.parse_expression()
        self.expect(TokenType.PUNTO_Y_COMA, "';'")
        return Asignacion(
            name=name.lexeme,
            value=value,
            line=name.line,
            column=name.column,
        )

    def parse_if(self) -> Si:
        start = self.advance()
        condition = self.parse_expression()
        then_branch = self.parse_block()
        else_branch: Bloque | Si | None = None

        if self.match(TokenType.SINO):
            if self.check(TokenType.SI):
                else_branch = self.parse_if()
            else:
                else_branch = self.parse_block()

        return Si(
            condition=condition,
            then_branch=then_branch,
            else_branch=else_branch,
            line=start.line,
            column=start.column,
        )

    def parse_while(self) -> Mientras:
        start = self.advance()
        condition = self.parse_expression()
        body = self.parse_block()
        return Mientras(
            condition=condition,
            body=body,
            line=start.line,
            column=start.column,
        )

    def parse_for(self) -> Para:
        start = self.advance()
        variable = self.expect(TokenType.IDENT, "variable de boucle")
        self.expect(TokenType.EN, "'en'")
        first = self.parse_expression()
        self.expect(TokenType.RANGO, "'..'")
        stop = self.parse_expression()
        body = self.parse_block()
        return Para(
            variable=variable.lexeme,
            start=first,
            stop=stop,
            body=body,
            line=start.line,
            column=start.column,
        )

    def parse_return(self) -> Devolver:
        start = self.advance()
        value = None if self.check(TokenType.PUNTO_Y_COMA) else self.parse_expression()
        self.expect(TokenType.PUNTO_Y_COMA, "';'")
        return Devolver(value=value, line=start.line, column=start.column)

    def parse_print(self) -> Mostrar:
        start = self.advance()
        arguments: list[Expression] = []
        if not self.check(TokenType.PUNTO_Y_COMA):
            arguments.append(self.parse_expression())
            while self.match(TokenType.COMA):
                arguments.append(self.parse_expression())
        self.expect(TokenType.PUNTO_Y_COMA, "';'")
        return Mostrar(
            arguments=tuple(arguments),
            line=start.line,
            column=start.column,
        )

    def _synchronize(
        self, *, stop_at_function: bool, stop_at_block_end: bool
    ) -> None:
        """Saute les tokens fautifs jusqu'à `;`, `}` ou une fonction suivante."""
        while not self.check(TokenType.FIN):
            if stop_at_block_end and self.check(TokenType.LLAVE_DER):
                return
            if stop_at_function and self.check(TokenType.FUNCION):
                return
            if self.match(TokenType.PUNTO_Y_COMA):
                return
            self.advance()

    # -- Erreurs --

    def missing(self, message: str) -> ParseError:
        """Erreur « il manque quelque chose » : position juste après le dernier token lu.

        S'il n'y a pas encore de token lu, la position est celle du token courant.
        """
        if self._index == 0:
            token = self.peek()
            return ParseError(message, token.line, token.column)
        previous = self._tokens[self._index - 1]
        return ParseError(
            message, previous.line, previous.column + len(previous.lexeme)
        )

    # -- Cœur de la méthode de Pratt --

    def parse_expression(self, min_power: int = 0) -> Expression:
        """Lit une expression en ne s'arrêtant que sur un opérateur plus faible.

        Les opérateurs infixes dont la puissance est <= `min_power` ne sont pas
        consommés : ils appartiennent à l'expression englobante.
        """
        token = self.peek()
        entry = PREFIX_PARSELETS.get(token.type)
        if entry is None:
            raise self.missing(f"expression attendue, trouvé {_describe(token)}")
        if entry.power <= min_power:
            raise ParseError(
                f"{_describe(token)} doit être entre parenthèses à cet endroit",
                token.line,
                token.column,
            )
        self.advance()
        left = entry.function(self, token)

        while True:
            token = self.peek()
            infix_entry = INFIX_PARSELETS.get(token.type)
            if infix_entry is None or infix_entry.power <= min_power:
                return left
            self.advance()
            left = infix_entry.function(self, left, token)


# ---------- Parselets préfixes : début d'une expression ----------


@prefix(TokenType.ENTERO)
def parse_entero(parser: Parser, token: Token) -> Expression:
    assert isinstance(token.value, int)
    return Entero(value=token.value, line=token.line, column=token.column)


@prefix(TokenType.CADENA)
def parse_cadena(parser: Parser, token: Token) -> Expression:
    assert isinstance(token.value, str)
    return Cadena(value=token.value, line=token.line, column=token.column)


@prefix(TokenType.VERDADERO, TokenType.FALSO)
def parse_booleano(parser: Parser, token: Token) -> Expression:
    return Booleano(
        value=token.type is TokenType.VERDADERO, line=token.line, column=token.column
    )


@prefix(TokenType.IDENT)
def parse_variable(parser: Parser, token: Token) -> Expression:
    return Variable(name=token.lexeme, line=token.line, column=token.column)


@prefix(TokenType.PAREN_IZQ)
def parse_grouping(parser: Parser, token: Token) -> Expression:
    """`( expression )` : les parenthèses n'existent pas dans l'arbre."""
    inner = parser.parse_expression()
    parser.expect(TokenType.PAREN_DER, "')'")
    return inner


@prefix(TokenType.NO, power=Power.NOT)
def parse_not(parser: Parser, token: Token) -> Expression:
    operand = parser.parse_expression(Power.NOT - 1)
    return Unario(
        operator=UnaryOperator.NO,
        operand=operand,
        line=token.line,
        column=token.column,
    )


@prefix(TokenType.MENOS, power=Power.UNARY_MINUS)
def parse_negative(parser: Parser, token: Token) -> Expression:
    operand = parser.parse_expression(Power.UNARY_MINUS - 1)
    return Unario(
        operator=UnaryOperator.NEGATIVO,
        operand=operand,
        line=token.line,
        column=token.column,
    )


# ---------- Parselets infixes : suite d'une expression ----------


@infix(TokenType.O, power=Power.OR)
@infix(TokenType.Y, power=Power.AND)
@infix(TokenType.MAS, TokenType.MENOS, power=Power.ADDITIVE)
@infix(TokenType.POR, TokenType.ENTRE, TokenType.RESTO, power=Power.MULTIPLICATIVE)
def parse_binary_left(parser: Parser, left: Expression, token: Token) -> Expression:
    """Opérateur binaire associatif à gauche : `a - b - c` = `(a - b) - c`.

    Le membre de droite est lu avec la puissance de l'opérateur lui-même : un
    opérateur de même niveau n'y est pas consommé et revient donc à la boucle.
    """
    power = INFIX_PARSELETS[token.type].power
    right = parser.parse_expression(power)
    return Binario(
        operator=BinaryOperator(token.lexeme),
        left=left,
        right=right,
        line=left.line,
        column=left.column,
    )


@infix(*COMPARISON_TYPES, power=Power.COMPARISON)
def parse_comparison(parser: Parser, left: Expression, token: Token) -> Expression:
    """Comparaison, non chaînable : `a < b < c` est une erreur."""
    right = parser.parse_expression(Power.COMPARISON)
    following = parser.peek()
    if following.type in COMPARISON_TYPES:
        raise ParseError(
            "les comparaisons ne se chaînent pas : utilise 'y' ou des parenthèses",
            following.line,
            following.column,
        )
    return Binario(
        operator=BinaryOperator(token.lexeme),
        left=left,
        right=right,
        line=left.line,
        column=left.column,
    )


@infix(TokenType.PAREN_IZQ, power=Power.CALL)
def parse_call(parser: Parser, callee: Expression, token: Token) -> Expression:
    """Appel `f(a, b)` : `(` joue le rôle d'un opérateur postfixe très fort."""
    arguments: list[Expression] = []
    if not parser.check(TokenType.PAREN_DER):
        arguments.append(parser.parse_expression())
        while parser.match(TokenType.COMA):
            arguments.append(parser.parse_expression())
    parser.expect(TokenType.PAREN_DER, "')'")
    return Llamada(
        callee=callee,
        arguments=tuple(arguments),
        line=callee.line,
        column=callee.column,
    )


# ---------- Point d'entrée ----------


def parse_expression_source(source: str) -> Expression:
    """Analyse un texte qui ne contient qu'une expression."""
    parser = Parser(tokenize(source))
    expression = parser.parse_expression()
    parser.expect_end()
    return expression


def parse_source(source: str) -> Programa:
    """Analyse un programme complet écrit en Ardilla."""
    return Parser(tokenize(source)).parse_program()
