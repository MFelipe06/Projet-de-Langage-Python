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


class ParseErrors(ParseError):
    """Plusieurs erreurs syntaxiques trouvées pendant l'analyse d'un programme."""

    def __init__(self, errors: tuple[ParseError, ...]) -> None:
        if not errors:
            raise ValueError("au moins une ParseError est nécessaire")
        first = errors[0]
        self.errors = errors
        super().__init__(
            f"{len(errors)} erreur(s) syntaxique(s)", first.line, first.column
        )

    def __str__(self) -> str:
        details = "\n".join(f"  - {error}" for error in self.errors)
        return f"{self.message} :\n{details}"
    