"""Définition des tokens du langage Ardilla (étape 2)."""

from dataclasses import dataclass
from enum import Enum, auto


class TokenType(Enum):
    """Toutes les catégories de tokens que le lexer pourra produire."""

    # Mots-clés
    VAR = auto()
    FUNCION = auto()
    DEVOLVER = auto()
    SI = auto()
    SINO = auto()
    MIENTRAS = auto()
    PARA = auto()
    EN = auto()
    MOSTRAR = auto()
    Y = auto()
    O = auto()
    NO = auto()
    VERDADERO = auto()
    FALSO = auto()

    # Identifiants et littéraux
    IDENT = auto()
    ENTERO = auto()
    CADENA = auto()

    # Opérateurs arithmétiques
    MAS = auto()  # +
    MENOS = auto()  # -
    POR = auto()  # *
    ENTRE = auto()  # /
    RESTO = auto()  # %

    # Opérateurs de comparaison
    IGUAL_IGUAL = auto()  # ==
    DISTINTO = auto()  # !=
    MENOR = auto()  # <
    MENOR_IGUAL = auto()  # <=
    MAYOR = auto()  # >
    MAYOR_IGUAL = auto()  # >=

    # Autres symboles
    ASIGNAR = auto()  # =
    RANGO = auto()  # ..
    PAREN_IZQ = auto()  # (
    PAREN_DER = auto()  # )
    LLAVE_IZQ = auto()  # {
    LLAVE_DER = auto()  # }
    COMA = auto()  # ,
    PUNTO_Y_COMA = auto()  # ;

    # Fin du fichier source
    FIN = auto()


KEYWORDS: dict[str, TokenType] = {
    "var": TokenType.VAR,
    "funcion": TokenType.FUNCION,
    "devolver": TokenType.DEVOLVER,
    "si": TokenType.SI,
    "sino": TokenType.SINO,
    "mientras": TokenType.MIENTRAS,
    "para": TokenType.PARA,
    "en": TokenType.EN,
    "mostrar": TokenType.MOSTRAR,
    "y": TokenType.Y,
    "o": TokenType.O,
    "no": TokenType.NO,
    "verdadero": TokenType.VERDADERO,
    "falso": TokenType.FALSO,
}


def classify_word(word: str) -> TokenType:
    """Retourne le type du mot-clé, ou IDENT si ce n'est pas un mot-clé."""
    return KEYWORDS.get(word, TokenType.IDENT)


@dataclass(frozen=True)
class Token:
    """Un token : son type, son texte exact, sa valeur et sa position.

    `line` et `column` commencent à 1. `value` ne sert qu'aux littéraux :
    un `int` pour ENTERO, un `str` (échappements résolus) pour CADENA.
    """

    type: TokenType
    lexeme: str
    line: int
    column: int
    value: int | str | None = None

    def __repr__(self) -> str:
        valeur = f" = {self.value!r}" if self.value is not None else ""
        return (
            f"Token({self.type.name} {self.lexeme!r}{valeur} "
            f"@{self.line}:{self.column})"
        )
