"""Analyse sémantique d'Ardilla : noms, portées, appels et retours."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from functools import singledispatchmethod

from ardilla.ast_nodes import (
    Asignacion,
    Binario,
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
    Node,
    Para,
    Programa,
    Si,
    Unario,
    Variable,
)
from ardilla.errors import ArdillaError


class SemanticError(ArdillaError):
    """Erreur sémantique unique du programme."""


class SemanticErrors(SemanticError):
    """Plusieurs erreurs sémantiques trouvées pendant l'analyse."""

    def __init__(self, errors: tuple[SemanticError, ...]) -> None:
        if not errors:
            raise ValueError("au moins une SemanticError est nécessaire")
        first = errors[0]
        self.errors = errors
        super().__init__(
            f"{len(errors)} erreur(s) sémantique(s)", first.line, first.column
        )

    def __str__(self) -> str:
        details = "\n".join(f"  - {error}" for error in self.errors)
        return f"{self.message} :\n{details}"


class SemanticAnalyzer:
    """Vérifie les règles sémantiques en parcourant un AST."""

    def __init__(self) -> None:
        self._scopes: list[dict[str, Node]] = []
        self._functions: dict[str, int] = {}
        self._errors: list[SemanticError] = []
        self._function_stack: list[Funcion] = []

    def analyze(self, program: Programa) -> None:
        """Vérifie un programme entier, puis lève les erreurs collectées."""
        self._scopes = []
        self._functions = {}
        self._errors = []
        self._function_stack = []

        for item in program.items:
            if isinstance(item, Funcion):
                if item.name in self._functions:
                    self._error(
                        f"la fonction '{item.name}' est déjà déclarée",
                        item,
                    )
                else:
                    self._functions[item.name] = len(item.parameters)

        with self._scope():
            self.visit(program)

        if self._errors:
            errors = tuple(self._errors)
            raise SemanticErrors(errors) from errors[0]

    @contextmanager
    def _scope(self) -> Iterator[None]:
        self._scopes.append({})
        try:
            yield
        finally:
            self._scopes.pop()

    @contextmanager
    def _function_context(self, function: Funcion) -> Iterator[None]:
        self._function_stack.append(function)
        try:
            yield
        finally:
            self._function_stack.pop()

    def _error(self, message: str, node: Node) -> None:
        self._errors.append(SemanticError(message, node.line, node.column))

    def _declare(self, name: str, node: Node) -> None:
        current_scope = self._scopes[-1]
        if name in current_scope:
            self._error(f"la variable '{name}' est déjà déclarée dans ce bloc", node)
        else:
            current_scope[name] = node

    def _is_declared(self, name: str) -> bool:
        return any(name in scope for scope in reversed(self._scopes))

    def _visit_statements(self, block: Bloque) -> None:
        for statement in block.statements:
            self.visit(statement)

    @singledispatchmethod
    def visit(self, node: Node) -> None:
        raise TypeError(f"nœud AST non pris en charge : {type(node).__name__}")

    @visit.register
    def _(self, node: Programa) -> None:
        for item in node.items:
            self.visit(item)

    @visit.register
    def _(self, node: Funcion) -> None:
        with self._function_context(node), self._scope():
            for parameter in node.parameters:
                self._declare(parameter, node)
            self._visit_statements(node.body)

    @visit.register
    def _(self, node: Bloque) -> None:
        with self._scope():
            self._visit_statements(node)

    @visit.register
    def _(self, node: Declaracion) -> None:
        self._visit_expression(node.value)
        self._declare(node.name, node)

    @visit.register
    def _(self, node: Asignacion) -> None:
        self._visit_expression(node.value)
        if not self._is_declared(node.name):
            self._error(f"la variable '{node.name}' n'est pas déclarée", node)

    @visit.register
    def _(self, node: Si) -> None:
        self._visit_expression(node.condition)
        self.visit(node.then_branch)
        if node.else_branch is not None:
            self.visit(node.else_branch)

    @visit.register
    def _(self, node: Mientras) -> None:
        self._visit_expression(node.condition)
        self.visit(node.body)

    @visit.register
    def _(self, node: Para) -> None:
        self._visit_expression(node.start)
        self._visit_expression(node.stop)
        with self._scope():
            self._declare(node.variable, node)
            self._visit_statements(node.body)

    @visit.register
    def _(self, node: Devolver) -> None:
        if not self._function_stack:
            self._error("'devolver' n'est autorisé que dans une fonction", node)
        if node.value is not None:
            self._visit_expression(node.value)

    @visit.register
    def _(self, node: Mostrar) -> None:
        for argument in node.arguments:
            self._visit_expression(argument)

    @visit.register
    def _(self, node: ExpresionInstruccion) -> None:
        self._visit_expression(node.expression)

    @visit.register
    def _(self, node: Entero) -> None:
        pass

    @visit.register
    def _(self, node: Cadena) -> None:
        pass

    @visit.register
    def _(self, node: Booleano) -> None:
        pass

    @visit.register
    def _(self, node: Variable) -> None:
        if not self._is_declared(node.name):
            self._error(f"la variable '{node.name}' n'est pas déclarée", node)

    @visit.register
    def _(self, node: Unario) -> None:
        self._visit_expression(node.operand)

    @visit.register
    def _(self, node: Binario) -> None:
        self._visit_expression(node.left)
        self._visit_expression(node.right)

    @visit.register
    def _(self, node: Llamada) -> None:
        if isinstance(node.callee, Variable):
            name = node.callee.name
            arity = self._functions.get(name)
            if arity is None:
                self._error(f"la fonction '{name}' n'est pas déclarée", node)
            elif len(node.arguments) != arity:
                self._error(
                    f"la fonction '{name}' attend {arity} argument(s), "
                    f"{len(node.arguments)} reçu(s)",
                    node,
                )
        else:
            self._visit_expression(node.callee)
            self._error("seul le nom d'une fonction peut être appelé", node)

        for argument in node.arguments:
            self._visit_expression(argument)

    def _visit_expression(self, expression: Expression) -> None:
        self.visit(expression)


def analyze(program: Programa) -> None:
    """Point d'entrée pratique pour vérifier un programme Ardilla."""
    SemanticAnalyzer().analyze(program)
