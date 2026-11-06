import subprocess
import sys
from pathlib import Path

import pytest

from ardilla.generator import generate_python
from ardilla.parser import parse_source
from ardilla.semantic import analyze


def compile_source(source: str) -> str:
    program = parse_source(source)
    analyze(program)
    return generate_python(program)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        (
            "mostrar 7 / 2;",
            (
                "import builtins as _ardilla_builtins\n\n"
                "_ardilla_builtins.print((7 // 2))\n"
            ),
        ),
        (
            "mostrar verdadero, falso;",
            (
                "import builtins as _ardilla_builtins\n\n"
                "_ardilla_builtins.print(True, False)\n"
            ),
        ),
        (
            "mostrar no falso;",
            (
                "import builtins as _ardilla_builtins\n\n"
                "_ardilla_builtins.print((not False))\n"
            ),
        ),
        (
            "mostrar 1 + 2 * 3;",
            (
                "import builtins as _ardilla_builtins\n\n"
                "_ardilla_builtins.print((1 + (2 * 3)))\n"
            ),
        ),
        (
            'mostrar "hola\\n";',
            (
                "import builtins as _ardilla_builtins\n\n"
                "_ardilla_builtins.print('hola\\n')\n"
            ),
        ),
    ],
)
def test_expressions_are_translated_to_python(source: str, expected: str) -> None:
    assert compile_source(source) == expected


def test_empty_program_produces_empty_python_source() -> None:
    assert generate_python(parse_source("")) == ""


def test_empty_blocks_generate_pass() -> None:
    assert compile_source("funcion vide() {} si verdadero {}") == (
        "import builtins as _ardilla_builtins\n"
        "\n"
        "def _ardilla_function_0():\n"
        "    pass\n"
        "\n"
        "if True:\n"
        "    pass\n"
    )


def test_if_else_if_is_generated_as_elif() -> None:
    generated = compile_source(
        "si verdadero { mostrar 1; } sino si falso { mostrar 2; } sino { mostrar 3; }"
    )

    assert generated == (
        "import builtins as _ardilla_builtins\n"
        "\n"
        "if True:\n"
        "    _ardilla_builtins.print(1)\n"
        "elif False:\n"
        "    _ardilla_builtins.print(2)\n"
        "else:\n"
        "    _ardilla_builtins.print(3)\n"
    )


def test_for_loop_uses_exclusive_python_range() -> None:
    assert compile_source("para k en 0..3 { mostrar k; }") == (
        "import builtins as _ardilla_builtins\n"
        "\n"
        "for _ardilla_variable_0 in _ardilla_builtins.range(0, 3):\n"
        "    _ardilla_builtins.print(_ardilla_variable_0)\n"
    )


def test_nested_scope_shadowing_does_not_change_the_outer_variable() -> None:
    source = (
        "var total = 10; "
        "si verdadero { var total = 20; mostrar total; } "
        "mostrar total;"
    )
    generated = compile_source(source)
    result = subprocess.run(
        [sys.executable, "-c", generated],
        capture_output=True,
        check=True,
        text=True,
    )

    assert result.stdout.splitlines() == ["20", "10"]


def test_python_builtin_and_keyword_names_do_not_collide() -> None:
    source = (
        "funcion print(class) { devolver class; } "
        "funcion range(n) { devolver n; } "
        "mostrar print(range(3)); "
        "para i en 0..range(2) { mostrar i; }"
    )
    generated = compile_source(source)
    result = subprocess.run(
        [sys.executable, "-c", generated],
        capture_output=True,
        check=True,
        text=True,
    )

    assert result.stdout.splitlines() == ["3", "0", "1"]


@pytest.mark.parametrize("filename", ["factorial", "fizzbuzz", "suma"])
def test_examples_generate_python_and_match_expected_output(filename: str) -> None:
    examples = Path(__file__).parents[1] / "ejemplos"
    source = (examples / f"{filename}.ard").read_text(encoding="utf-8")
    expected = (examples / f"{filename}.out").read_text(encoding="utf-8")
    generated = compile_source(source)
    result = subprocess.run(
        [sys.executable, "-c", generated],
        capture_output=True,
        check=True,
        text=True,
    )

    assert result.stdout.splitlines() == expected.splitlines()
