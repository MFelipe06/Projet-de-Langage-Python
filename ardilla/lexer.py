"""Lexer d'Ardilla (étape 3) : transforme le texte source en suite de tokens."""

import string
from collections.abc import Iterator

from ardilla.errors import LexError
from ardilla.stream import CharStream
from ardilla.tokens import Token, TokenType, classify_word

_LETTERS = frozenset(string.ascii_letters + "_")
_DIGITS = frozenset(string.digits)
_WHITESPACE = frozenset(" \t\r\n")

# Tokens d'un seul caractère.
_SINGLE_CHAR: dict[str, TokenType] = {
    "+": TokenType.MAS,
    "-": TokenType.MENOS,
    "*": TokenType.POR,
    "/": TokenType.ENTRE,
    "%": TokenType.RESTO,
    "=": TokenType.ASIGNAR,
    "<": TokenType.MENOR,
    ">": TokenType.MAYOR,
    "(": TokenType.PAREN_IZQ,
    ")": TokenType.PAREN_DER,
    "{": TokenType.LLAVE_IZQ,
    "}": TokenType.LLAVE_DER,
    ",": TokenType.COMA,
    ";": TokenType.PUNTO_Y_COMA,
}

# Premier caractère -> (second caractère attendu, type du token à deux caractères).
_TWO_CHAR: dict[str, tuple[str, TokenType]] = {
    "=": ("=", TokenType.IGUAL_IGUAL),
    "!": ("=", TokenType.DISTINTO),
    "<": ("=", TokenType.MENOR_IGUAL),
    ">": ("=", TokenType.MAYOR_IGUAL),
    ".": (".", TokenType.RANGO),
}

_ESCAPES = {"n": "\n", '"': '"', "\\": "\\"}


def _is_letter(char: str | None) -> bool:
    return char is not None and char in _LETTERS


def _is_digit(char: str | None) -> bool:
    return char is not None and char in _DIGITS


class Lexer:
    """Découpe une source Ardilla en tokens, un par un (générateur)."""

    def __init__(self, source: str) -> None:
        self._source = source
        self._stream = CharStream(source)

    def tokens(self) -> Iterator[Token]:
        """Produit les tokens à la demande, puis un token FIN.

        Une LexError est levée au moment où le lexer atteint l'erreur : les
        tokens situés avant ont déjà été produits.
        """
        stream = self._stream
        while True:
            self._skip_whitespace_and_comments()
            if stream.at_end():
                yield Token(TokenType.FIN, "", stream.line, stream.column)
                return
            yield self._next_token()

    def _skip_whitespace_and_comments(self) -> None:
        stream = self._stream
        while not stream.at_end():
            char = stream.peek()
            if char is not None and char in _WHITESPACE:
                stream.advance()
            elif char == "/" and stream.peek(1) == "/":
                while not stream.at_end() and stream.peek() != "\n":
                    stream.advance()
            else:
                return

    def _next_token(self) -> Token:
        stream = self._stream
        line, column, start = stream.line, stream.column, stream.index
        char = stream.advance()

        if char in _LETTERS:
            return self._word(start, line, column)
        if char in _DIGITS:
            return self._number(start, line, column)
        if char == '"':
            return self._string(start, line, column)

        if char in _TWO_CHAR and stream.peek() == _TWO_CHAR[char][0]:
            stream.advance()
            return self._token(_TWO_CHAR[char][1], start, line, column)
        if char in _SINGLE_CHAR:
            return self._token(_SINGLE_CHAR[char], start, line, column)

        if char == "!":
            raise LexError(
                "'!' seul n'existe pas : utilise 'no' ou '!='", line, column
            )
        if char == ".":
            raise LexError(
                "'.' seul n'existe pas : utilise '..' pour un intervalle", line, column
            )
        raise LexError(f"caractère inattendu {char!r}", line, column)

    def _token(
        self,
        token_type: TokenType,
        start: int,
        line: int,
        column: int,
        value: int | str | None = None,
    ) -> Token:
        """Construit un token dont le lexème est le texte de `start` à la position courante."""
        lexeme = self._source[start : self._stream.index]
        return Token(token_type, lexeme, line, column, value)

    def _word(self, start: int, line: int, column: int) -> Token:
        stream = self._stream
        while _is_letter(stream.peek()) or _is_digit(stream.peek()):
            stream.advance()
        word = self._source[start : stream.index]
        return Token(classify_word(word), word, line, column)

    def _number(self, start: int, line: int, column: int) -> Token:
        stream = self._stream
        while _is_digit(stream.peek()):
            stream.advance()
        if _is_letter(stream.peek()):
            raise LexError(
                "un identifiant ne peut pas commencer par un chiffre", line, column
            )
        text = self._source[start : stream.index]
        return Token(TokenType.ENTERO, text, line, column, int(text))

    def _string(self, start: int, line: int, column: int) -> Token:
        """Lit une chaîne dont le guillemet ouvrant vient d'être consommé."""
        stream = self._stream
        chars: list[str] = []
        while True:
            char = stream.peek()
            if char is None or char == "\n":
                raise LexError("chaîne non terminée", line, column)
            backslash_line, backslash_column = stream.line, stream.column
            stream.advance()
            if char == '"':
                break
            if char != "\\":
                chars.append(char)
                continue
            code = stream.peek()
            if code is None or code == "\n":
                raise LexError("chaîne non terminée", line, column)
            if code not in _ESCAPES:
                raise LexError(
                    f"séquence d'échappement inconnue : \\{code}",
                    backslash_line,
                    backslash_column,
                )
            stream.advance()
            chars.append(_ESCAPES[code])
        return self._token(TokenType.CADENA, start, line, column, "".join(chars))


def tokenize(source: str) -> Iterator[Token]:
    """Point d'entrée : retourne un générateur de tokens pour `source`."""
    return Lexer(source).tokens()
