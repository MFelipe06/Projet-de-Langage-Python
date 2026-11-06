"""Erreurs du compilateur Ardilla, toutes accompagnées d'une position."""


class ArdillaError(Exception):
    """Erreur de base : un message et une position (ligne, colonne) dans la source.

    `line` et `column` commencent à 1, comme dans les tokens.
    """

    def __init__(self, message: str, line: int, column: int) -> None:
        super().__init__(message)
        self.message = message
        self.line = line
        self.column = column

    def __str__(self) -> str:
        return f"{self.line}:{self.column}: {self.message}"


class LexError(ArdillaError):
    """Erreur lexicale : la source contient quelque chose qui n'est pas un token."""


class ParseError(ArdillaError):
    """Erreur syntaxique : les tokens ne forment pas une phrase valide."""
    