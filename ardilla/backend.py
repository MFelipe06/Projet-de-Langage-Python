"""Contrat des backends capables de traduire un AST Ardilla."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from ardilla.ast_nodes import Programa


@runtime_checkable
class Backend(Protocol):
    """Interface interchangeable pour une cible de compilation."""

    def generate(self, program: Programa) -> str:
        """Traduit un programme Ardilla en code pour le backend."""
        ...
