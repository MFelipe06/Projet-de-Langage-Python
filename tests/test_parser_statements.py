import pytest

from ardilla.ast_nodes import (
    Asignacion,
    Binario,
    Bloque,
    Declaracion,
    Devolver,
    ExpresionInstruccion,
    Funcion,
    Llamada,
    Mientras,
    Mostrar,
    Para,
    Programa,
    Si,
)
from ardilla.errors import ParseError, ParseErrors
from ardilla.parser import parse_source


def test_programme_vide() -> None:
    assert parse_source("") == Programa(items=(), line=1, column=1)


def test_declaration_assignment_and_expression_statement() -> None:
    programme = parse_source("var total = 1 + 2; total = total * 3; f();")

    assert isinstance(programme.items[0], Declaracion)
    assert isinstance(programme.items[0].value, Binario)
    assert isinstance(programme.items[1], Asignacion)
    assert isinstance(programme.items[2], ExpresionInstruccion)
    assert isinstance(programme.items[2].expression, Llamada)


def test_if_else_if_and_else() -> None:
    programme = parse_source(
        "si a { mostrar 1; } sino si b { mostrar 2; } sino { mostrar 3; }"
    )

    statement = programme.items[0]
    assert isinstance(statement, Si)
    assert isinstance(statement.else_branch, Si)
    assert isinstance(statement.else_branch.else_branch, Bloque)


def test_while_and_for() -> None:
    programme = parse_source(
        "mientras x { x = x - 1; } para k en 0..6 { mostrar k; }"
    )

    assert isinstance(programme.items[0], Mientras)
    loop = programme.items[1]
    assert isinstance(loop, Para)
    assert loop.variable == "k"
    assert isinstance(loop.body.statements[0], Mostrar)


@pytest.mark.parametrize(
    ("source", "expected_value"),
    [("devolver;", None), ("devolver 42;", 42)],
)
def test_return_with_or_without_value(source: str, expected_value: int | None) -> None:
    statement = parse_source(source).items[0]

    assert isinstance(statement, Devolver)
    if expected_value is None:
        assert statement.value is None
    else:
        assert statement.value is not None
        assert statement.value.value == expected_value


def test_print_with_no_arguments_or_multiple_arguments() -> None:
    empty, several = parse_source("mostrar; mostrar a, 2 + 3;").items

    assert isinstance(empty, Mostrar)
    assert empty.arguments == ()
    assert isinstance(several, Mostrar)
    assert len(several.arguments) == 2


def test_function_with_optional_parameters_and_body() -> None:
    empty, function = parse_source(
        "funcion rien() {} funcion somme(a, b) { devolver a + b; }"
    ).items

    assert isinstance(empty, Funcion)
    assert empty.parameters == ()
    assert isinstance(function, Funcion)
    assert function.parameters == ("a", "b")
    assert isinstance(function.body.statements[0], Devolver)


def test_programme_factorial() -> None:
    programme = parse_source(
        "funcion factorial(n) { "
        "si n <= 1 { devolver 1; } "
        "devolver n * factorial(n - 1); "
        "} para k en 0..6 { mostrar k, factorial(k); }"
    )

    assert len(programme.items) == 2
    assert isinstance(programme.items[0], Funcion)
    assert isinstance(programme.items[1], Para)


def test_positions_are_taken_from_each_statement_start() -> None:
    programme = parse_source("\n  var x = 1;\n  si x { devolver; }")
    declaration, condition = programme.items

    assert (declaration.line, declaration.column) == (2, 3)
    assert (condition.line, condition.column) == (3, 3)


def test_syntax_errors_are_collected_and_chained_and_parser_recovers() -> None:
    with pytest.raises(ParseErrors) as info:
        parse_source("var = 1;\nmostrar ,;\nvar ok = 3;")

    error = info.value
    assert isinstance(error, ParseError)
    assert len(error.errors) == 2
    assert all(isinstance(item, ParseError) for item in error.errors)
    assert [item.line for item in error.errors] == [1, 2]
    assert error.__cause__ is error.errors[0]


def test_syntax_error_inside_block_is_collected() -> None:
    with pytest.raises(ParseErrors) as info:
        parse_source("funcion f() { var = 1; mostrar ,; }")

    assert len(info.value.errors) == 2
    assert all(item.line == 1 for item in info.value.errors)


def test_recovery_preserves_the_block_closing_brace() -> None:
    with pytest.raises(ParseErrors) as info:
        parse_source("funcion f() { var x = 1 }")

    assert len(info.value.errors) == 1
    assert "';'" in info.value.errors[0].message


def test_missing_semicolon_points_after_expression() -> None:
    with pytest.raises(ParseErrors) as info:
        parse_source("var x = 5\nmostrar x;")

    first_error = info.value.errors[0]
    assert (first_error.line, first_error.column) == (1, 10)
    assert "';'" in first_error.message


def test_unclosed_block_is_reported_at_end_of_input() -> None:
    with pytest.raises(ParseErrors) as info:
        parse_source("si verdadero { mostrar 1;")

    assert len(info.value.errors) == 1
    assert info.value.errors[0].message.startswith("'}' attendu")
