"""REPL Ardilla avec mémoire d'un programme entre les soumissions."""

from __future__ import annotations

from collections.abc import Callable, Generator

from ardilla.backend import Backend
from ardilla.parser import parse_source
from ardilla.python_backend import default_backend
from ardilla.semantic import analyze


class InteractiveSession:
    """Compile et exécute les cellules successives dans le même espace Python."""

    def __init__(self, backend: Backend | None = None) -> None:
        self._source = ""
        self._python_source = ""
        self._namespace: dict[str, object] = {"__name__": "__main__"}
        self._backend = backend if backend is not None else default_backend()

    def submit(self, source: str) -> None:
        """Ajoute une cellule si elle est valide, puis exécute uniquement son code."""
        if not source.strip():
            return

        updated_source = f"{self._source}\n{source}" if self._source else source
        program = parse_source(updated_source)
        analyze(program)
        updated_python = self._backend.generate(program)

        if not updated_python.startswith(self._python_source):
            raise RuntimeError("le code Python déjà exécuté a changé")

        new_python = updated_python[len(self._python_source) :]
        compiled = compile(new_python, "<ardilla-repl>", "exec")
        self._source = updated_source
        self._python_source = updated_python
        exec(compiled, self._namespace)  # noqa: S102


def repl_prompts(
    submit: Callable[[str], None],
    write: Callable[[str], None] = print,
) -> Generator[str, str | None]:
    """Dialogue envoi/réception des lignes et fournit le prompt suivant."""
    lines: list[str] = []
    line = yield "ardilla> "

    while line is not None:
        command = line.strip()
        if command in {":quit", ":exit", ":salir"}:
            if lines:
                write("Programme non exécuté ; utilise :run avant de quitter.")
            return
        if command == ":help":
            write("Saisis un programme, puis une ligne vide ou :run. Quitter : :quit.")
            line = yield "ardilla> " if not lines else "...> "
            continue
        if command == ":run" or not command:
            if lines:
                submit("\n".join(lines))
                lines.clear()
            line = yield "ardilla> "
            continue

        lines.append(line)
        line = yield "...> "
