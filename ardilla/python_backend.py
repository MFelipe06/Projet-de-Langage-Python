"""Backend Python du compilateur Ardilla."""

from __future__ import annotations

from ardilla.ast_nodes import Programa
from ardilla.backend import Backend
from ardilla.generator import generate_python


class PythonBackend:
    """Implémentation du backend qui génère du code Python."""

    def generate(self, program: Programa) -> str:
        return generate_python(program)


def default_backend() -> Backend:
    """Construit le backend utilisé par défaut par le CLI et le REPL."""
    return PythonBackend()
