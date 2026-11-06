"""Flux de caractères avec regard en avant (lookahead) et suivi de la position."""


class CharStream:
    """Parcourt un texte caractère par caractère en suivant ligne et colonne.

    `peek` regarde un caractère sans le consommer ; `advance` le consomme.
    Les lignes et les colonnes commencent à 1.
    """

    def __init__(self, source: str) -> None:
        self._source = source
        self._index = 0
        self.line = 1
        self.column = 1

    @property
    def index(self) -> int:
        """Position (à partir de 0) du prochain caractère dans la source."""
        return self._index

    def at_end(self) -> bool:
        return self._index >= len(self._source)

    def peek(self, offset: int = 0) -> str | None:
        """Retourne le caractère `offset` positions plus loin, sans avancer.

        Retourne None au-delà de la fin (et non une chaîne vide : `"" in "abc"`
        vaut True en Python, ce qui provoquerait des bugs subtils).
        """
        position = self._index + offset
        if position < len(self._source):
            return self._source[position]
        return None

    def advance(self) -> str:
        """Consomme et retourne le caractère courant. Interdit en fin de source."""
        if self.at_end():
            raise IndexError("advance() appelé en fin de source")
        char = self._source[self._index]
        self._index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1
        return char
