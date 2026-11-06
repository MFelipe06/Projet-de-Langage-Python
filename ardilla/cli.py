"""Interface en ligne de commande d'Ardilla."""

from __future__ import annotations

import argparse
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from ardilla.backend import Backend
from ardilla.errors import ArdillaError
from ardilla.formatter import format_source
from ardilla.parser import parse_source
from ardilla.python_backend import default_backend
from ardilla.repl import InteractiveSession, repl_prompts
from ardilla.semantic import analyze


def compile_source(source: str, backend: Backend | None = None) -> str:
    """Exécute les étapes lexer, parser, sémantique et génération Python."""
    program = parse_source(source)
    analyze(program)
    selected_backend = backend if backend is not None else default_backend()
    return selected_backend.generate(program)


def _read_source(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _run_file(path: Path) -> int:
    generated = compile_source(_read_source(path))
    result = subprocess.run(
        [sys.executable, "-"],
        input=generated,
        check=False,
        text=True,
    )
    return result.returncode


def _compile_file(path: Path) -> int:
    sys.stdout.write(compile_source(_read_source(path)))
    return 0


def _format_file(path: Path) -> int:
    sys.stdout.write(format_source(_read_source(path)))
    return 0


def _run_repl() -> int:
    session = InteractiveSession()

    def submit(source: str) -> None:
        try:
            session.submit(source)
        except ArdillaError as error:
            print(error, file=sys.stderr)
        except (
            ArithmeticError,
            NameError,
            RecursionError,
            SyntaxError,
            TypeError,
        ) as error:
            print(f"Erreur d'exécution : {error}", file=sys.stderr)

    dialogue = repl_prompts(submit)
    prompt = next(dialogue)
    while True:
        try:
            line = input(prompt)
        except EOFError:
            try:
                dialogue.send(None)
            except StopIteration:
                pass
            return 0
        try:
            prompt = dialogue.send(line)
        except StopIteration:
            return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Point d'entrée partagé par `python -m ardilla` et les tests."""
    parser = argparse.ArgumentParser(prog="ardilla")
    commands = parser.add_subparsers(dest="command", required=True)

    run_command = commands.add_parser("run", help="exécuter un fichier .ard")
    run_command.add_argument("file", type=Path)

    compile_command = commands.add_parser(
        "compile", help="afficher le Python généré"
    )
    compile_command.add_argument("file", type=Path)

    format_command = commands.add_parser(
        "format", help="formater un fichier Ardilla"
    )
    format_command.add_argument("file", type=Path)

    commands.add_parser("repl", help="démarrer le REPL interactif")
    arguments = parser.parse_args(argv)

    try:
        if arguments.command == "run":
            return _run_file(arguments.file)
        if arguments.command == "compile":
            return _compile_file(arguments.file)
        if arguments.command == "format":
            return _format_file(arguments.file)
        return _run_repl()
    except (OSError, ArdillaError) as error:
        print(error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
