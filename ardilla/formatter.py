"""Formateur canonique du code source Ardilla."""

from __future__ import annotations

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
from ardilla.parser import parse_source


def _format_expression(expression: Expression) -> str:
    match expression:
        case Entero(value=value):
            return str(value)
        case Cadena(value=value):
            escaped = (
                expression.value.replace("\\", "\\\\")
                .replace('"', '\\"')
                .replace("\n", "\\n")
            )
            return f'"{escaped}"'
        case Booleano(value=value):
            return "verdadero" if value else "falso"
        case Variable(name=name):
            return name
        case Unario(operator=operator, operand=operand):
            return f"({operator.value} {_format_expression(operand)})"
        case Binario(operator=operator, left=left, right=right):
            return (
                f"({_format_expression(left)} {operator.value} "
                f"{_format_expression(right)})"
            )
        case Llamada(callee=callee, arguments=arguments):
            rendered = ", ".join(_format_expression(arg) for arg in arguments)
            return f"{_format_expression(callee)}({rendered})"
        case _:
            assert_never(expression)


def _format_block_contents(block: Bloque, level: int) -> list[str]:
    lines: list[str] = []
    for statement in block.statements:
        lines.extend(_format_statement(statement, level))
    return lines


def _format_if(statement: Si, level: int) -> list[str]:
    indent = "    " * level
    lines = [f"{indent}si {_format_expression(statement.condition)} {{"]
    lines.extend(_format_block_contents(statement.then_branch, level + 1))

    branch = statement.else_branch
    if isinstance(branch, Si):
        while isinstance(branch, Si):
            lines.append(
                f"{indent}}} sino si {_format_expression(branch.condition)} {{"
            )
            lines.extend(_format_block_contents(branch.then_branch, level + 1))
            next_branch = branch.else_branch
            if isinstance(next_branch, Si):
                branch = next_branch
                continue
            if isinstance(next_branch, Bloque):
                lines.append(f"{indent}}} sino {{")
                lines.extend(_format_block_contents(next_branch, level + 1))
            lines.append(f"{indent}}}")
            return lines
    elif isinstance(branch, Bloque):
        lines.append(f"{indent}}} sino {{")
        lines.extend(_format_block_contents(branch, level + 1))
    lines.append(f"{indent}}}")
    return lines


def _format_statement(statement: Statement, level: int) -> list[str]:
    indent = "    " * level
    match statement:
        case Declaracion(name=name, value=value):
            return [f"{indent}var {name} = {_format_expression(value)};"]
        case Asignacion(name=name, value=value):
            return [f"{indent}{name} = {_format_expression(value)};"]
        case Si():
            return _format_if(statement, level)
        case Mientras(condition=condition, body=body):
            lines = [f"{indent}mientras {_format_expression(condition)} {{"]
            lines.extend(_format_block_contents(body, level + 1))
            lines.append(f"{indent}}}")
            return lines
        case Para(variable=variable, start=start, stop=stop, body=body):
            lines = [
                (
                    f"{indent}para {variable} en {_format_expression(start)}.."
                    f"{_format_expression(stop)} {{"
                )
            ]
            lines.extend(_format_block_contents(body, level + 1))
            lines.append(f"{indent}}}")
            return lines
        case Devolver(value=value):
            expression = "" if value is None else f" {_format_expression(value)}"
            return [f"{indent}devolver{expression};"]
        case Mostrar(arguments=arguments):
            rendered = ", ".join(_format_expression(arg) for arg in arguments)
            return [f"{indent}mostrar{f' {rendered}' if rendered else ''};"]
        case ExpresionInstruccion(expression=expression):
            return [f"{indent}{_format_expression(expression)};"]
        case _:
            assert_never(statement)


def format_program(program: Programa) -> str:
    """Retourne la représentation canonique d'un AST Ardilla."""
    lines: list[str] = []
    for item in program.items:
        if lines:
            lines.append("")
        if isinstance(item, Funcion):
            parameters = ", ".join(item.parameters)
            lines.append(f"funcion {item.name}({parameters}) {{")
            lines.extend(_format_block_contents(item.body, 1))
            lines.append("}")
        else:
            lines.extend(_format_statement(item, 0))
    return "\n".join(lines) + ("\n" if lines else "")


def format_source(source: str) -> str:
    """Analyse puis reformate un programme source Ardilla."""
    return format_program(parse_source(source))
