from pathlib import Path

import pytest

from ardilla.errors import ParseErrors
from ardilla.formatter import format_source
from ardilla.parser import parse_source

ROOT = Path(__file__).parents[1]


def test_format_source_normalizes_spacing_and_indentation() -> None:
    source = "var x=1+2*3;si verdadero{mostrar x;}"

    assert format_source(source) == (
        "var x = (1 + (2 * 3));\n"
        "\n"
        "si verdadero {\n"
        "    mostrar x;\n"
        "}\n"
    )


def test_format_source_keeps_else_if_structure() -> None:
    source = "si verdadero{}sino si falso{}sino{}"

    assert format_source(source) == (
        "si verdadero {\n"
        "} sino si falso {\n"
        "} sino {\n"
        "}\n"
    )


def test_format_source_is_idempotent() -> None:
    source = "funcion f(x){si x>0{devolver x;}sino{devolver 0;}}"
    formatted = format_source(source)

    assert format_source(formatted) == formatted


def test_formatted_examples_parse_back_to_the_same_ast() -> None:
    examples = ROOT / "ejemplos"
    for path in sorted(examples.glob("*.ard")):
        source = path.read_text(encoding="utf-8")
        formatted = format_source(source)

        assert parse_source(formatted) == parse_source(source)


def test_format_source_preserves_supported_string_escapes() -> None:
    source = 'mostrar "ligne\\navec \\"guillemets\\" et \\\\\";'

    assert format_source(source) == (
        'mostrar "ligne\\navec \\"guillemets\\" et \\\\\";\n'
    )


def test_format_source_rejects_invalid_syntax() -> None:
    with pytest.raises(ParseErrors, match="erreur"):
        format_source("var = 1;")


def test_empty_source_formats_as_empty_source() -> None:
    assert format_source("") == ""
