import subprocess
import sys
from pathlib import Path

import pytest

from ardilla.cli import compile_source, main
from ardilla.errors import ParseErrors

ROOT = Path(__file__).parents[1]


def test_compile_source_runs_the_compilation_pipeline() -> None:
    generated = compile_source("mostrar 1 + 2;")

    assert "_ardilla_builtins.print((1 + 2))" in generated


def test_compile_source_reports_syntax_errors() -> None:
    with pytest.raises(ParseErrors):
        compile_source("var = 1;")


def test_compile_command_prints_generated_python(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["compile", str(ROOT / "ejemplos" / "suma.ard")])

    assert result == 0
    assert "_ardilla_builtins.print('suma:', _ardilla_variable_0)" in capsys.readouterr().out


def test_format_command_prints_formatted_ardilla(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["format", str(ROOT / "ejemplos" / "factorial.ard")])

    assert result == 0
    formatted = capsys.readouterr().out
    assert formatted.startswith("funcion factorial(n) {\n")
    assert "    si (n <= 1) {\n" in formatted


def test_run_command_executes_source_file(capfd: pytest.CaptureFixture[str]) -> None:
    result = main(["run", str(ROOT / "ejemplos" / "suma.ard")])

    assert result == 0
    assert capfd.readouterr().out.splitlines() == ["suma: 55"]


def test_run_command_reports_invalid_source(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = tmp_path / "incorrect.ard"
    source.write_text("mostrar ;\nvar = 1;", encoding="utf-8")

    result = main(["run", str(source)])
    output = capsys.readouterr()

    assert result == 1
    assert "erreur(s) syntaxique(s)" in output.err


def test_run_command_reports_missing_file(capsys: pytest.CaptureFixture[str]) -> None:
    result = main(["run", str(ROOT / "absent.ard")])

    assert result == 1
    assert "absent.ard" in capsys.readouterr().err


def test_python_module_cli_runs_an_example() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ardilla",
            "run",
            str(ROOT / "ejemplos" / "factorial.ard"),
        ],
        capture_output=True,
        check=True,
        text=True,
        cwd=ROOT,
    )

    assert result.stdout.splitlines() == [
        "0 1",
        "1 1",
        "2 2",
        "3 6",
        "4 24",
        "5 120",
    ]


def test_python_module_cli_starts_a_stateful_repl() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "ardilla", "repl"],
        input="var total = 40;\n\nmostrar total + 2;\n\n:quit\n",
        capture_output=True,
        check=True,
        text=True,
        cwd=ROOT,
    )

    assert any(line.endswith("42") for line in result.stdout.splitlines())


def test_invalid_command_line_is_reported_by_argparse(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as info:
        main([])

    assert info.value.code == 2
    assert "usage:" in capsys.readouterr().err
