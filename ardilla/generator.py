"""Génération de code Python à partir de l'AST Ardilla."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import assert_never

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
    Para,
    Programa,
    Si,
    Statement,
    Unario,
    Variable,
)


class PythonGenerator:
    """Traduit chaque nœud Ardilla en instructions et expressions Python."""

    def __init__(self) -> None:
        self._lines: list[str] = []
        self._indent = 0
        self._next_variable = 0
        self._functions: dict[str, str] = {}
        self._scopes: list[dict[str, str]] = []

    def generate(self, program: Programa) -> str:
        """Retourne le code Python du programme, terminé par une nouvelle ligne."""
        self._lines = []
        self._indent = 0
        self._next_variable = 0
        self._scopes = []
        self._functions = {
            item.name: f"_ardilla_function_{index}"
            for index, item in enumerate(
                item for item in program.items if isinstance(item, Funcion)
            )
        }

        if program.items:
            self._write("import builtins as _ardilla_builtins")
            self._lines.append("")
            has_item = False
            with self._scope():
                previous_was_function = False
                for item in program.items:
                    if has_item and (
                        isinstance(item, Funcion) or previous_was_function
                    ):
                        self._lines.append("")
                    if isinstance(item, Funcion):
                        self._emit_function(item)
                    else:
                        self._emit_statement(item)
                    previous_was_function = isinstance(item, Funcion)
                    has_item = True

        return "\n".join(self._lines) + ("\n" if self._lines else "")

    def _write(self, line: str) -> None:
        self._lines.append(f"{'    ' * self._indent}{line}")

    @contextmanager
    def _indented(self) -> Iterator[None]:
        self._indent += 1
        try:
            yield
        finally:
            self._indent -= 1

    @contextmanager
    def _scope(self) -> Iterator[None]:
        self._scopes.append({})
        try:
            yield
        finally:
            self._scopes.pop()

    def _declare(self, name: str) -> str:
        generated_name = f"_ardilla_variable_{self._next_variable}"
        self._next_variable += 1
        self._scopes[-1][name] = generated_name
        return generated_name

    def _resolve_variable(self, name: str) -> str:
        for scope in reversed(self._scopes):
            if name in scope:
                return scope[name]
        raise ValueError(f"la variable '{name}' doit être vérifiée sémantiquement")

    def _emit_block(self, block: Bloque) -> None:
        with self._scope():
            self._emit_statements(block)

    def _emit_statements(self, block: Bloque) -> None:
        if not block.statements:
            self._write("pass")
            return
        for statement in block.statements:
            self._emit_statement(statement)

    def _emit_function(self, function: Funcion) -> None:
        with self._scope():
            parameters = ", ".join(
                self._declare(parameter) for parameter in function.parameters
            )
            generated_name = self._functions[function.name]
            self._write(f"def {generated_name}({parameters}):")
            with self._indented():
                self._emit_statements(function.body)

    def _emit_for(
        self, variable: str, start: Expression, stop: Expression, body: Bloque
    ) -> None:
        generated_start = self._expression(start)
        generated_stop = self._expression(stop)
        with self._scope():
            generated_variable = self._declare(variable)
            self._write(
                f"for {generated_variable} in _ardilla_builtins.range("
                f"{generated_start}, {generated_stop}):"
            )
            with self._indented():
                self._emit_statements(body)

    def _emit_while(self, condition: Expression, body: Bloque) -> None:
        self._write(f"while {self._expression(condition)}:")
        with self._indented():
            self._emit_block(body)

    def _emit_if(self, statement: Si, keyword: str = "if") -> None:
        self._write(f"{keyword} {self._expression(statement.condition)}:")
        with self._indented():
            self._emit_block(statement.then_branch)

        if isinstance(statement.else_branch, Si):
            self._emit_if(statement.else_branch, "elif")
        elif isinstance(statement.else_branch, Bloque):
            self._write("else:")
            with self._indented():
                self._emit_block(statement.else_branch)

    def _emit_statement(self, statement: Statement) -> None:
        match statement:
            case Declaracion(name=name, value=value):
                generated_value = self._expression(value)
                generated_name = self._declare(name)
                self._write(f"{generated_name} = {generated_value}")
            case Asignacion(name=name, value=value):
                generated_name = self._resolve_variable(name)
                self._write(f"{generated_name} = {self._expression(value)}")
            case Si():
                self._emit_if(statement)
            case Mientras(condition=condition, body=body):
                self._emit_while(condition, body)
            case Para(variable=variable, start=start, stop=stop, body=body):
                self._emit_for(variable, start, stop, body)
            case Devolver(value=value):
                if value is None:
                    self._write("return")
                else:
                    self._write(f"return {self._expression(value)}")
            case Mostrar(arguments=arguments):
                rendered = ", ".join(self._expression(arg) for arg in arguments)
                self._write(f"_ardilla_builtins.print({rendered})")
            case ExpresionInstruccion(expression=expression):
                self._write(self._expression(expression))
            case _:
                assert_never(statement)

    def _expression(self, expression: Expression) -> str:
        match expression:
            case Entero(value=value):
                return str(value)
            case Cadena(value=value):
                return repr(value)
            case Booleano(value=value):
                return "True" if value else "False"
            case Variable(name=name):
                return self._resolve_variable(name)
            case Unario(operator=operator, operand=operand):
                if operator.value == "no":
                    return f"(not {self._expression(operand)})"
                return f"(-{self._expression(operand)})"
            case Binario(operator=operator, left=left, right=right):
                symbol = {
                    "+": "+",
                    "-": "-",
                    "*": "*",
                    "/": "//",
                    "%": "%",
                    "==": "==",
                    "!=": "!=",
                    "<": "<",
                    "<=": "<=",
                    ">": ">",
                    ">=": ">=",
                    "y": "and",
                    "o": "or",
                }[operator.value]
                return (
                    f"({self._expression(left)} {symbol} "
                    f"{self._expression(right)})"
                )
            case Llamada(callee=callee, arguments=arguments):
                rendered = ", ".join(self._expression(arg) for arg in arguments)
                if isinstance(callee, Variable):
                    generated_callee = self._functions[callee.name]
                else:
                    generated_callee = self._expression(callee)
                return f"{generated_callee}({rendered})"
            case _:
                assert_never(expression)


def generate_python(program: Programa) -> str:
    """Génère du code Python depuis un programme Ardilla."""
    return PythonGenerator().generate(program)
