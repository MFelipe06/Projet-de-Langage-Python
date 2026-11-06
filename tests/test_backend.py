import pytest

from ardilla.ast_nodes import Programa
from ardilla.backend import Backend
from ardilla.cli import compile_source
from ardilla.parser import parse_source
from ardilla.python_backend import PythonBackend
from ardilla.semantic import SemanticErrors


class RecordingBackend:
    def __init__(self) -> None:
        self.program: Programa | None = None

    def generate(self, program: Programa) -> str:
        self.program = program
        return "recorded backend output"


def test_python_backend_implements_the_backend_protocol() -> None:
    assert isinstance(PythonBackend(), Backend)


def test_compile_pipeline_accepts_an_alternative_backend() -> None:
    backend = RecordingBackend()

    output = compile_source("mostrar 1;", backend)

    assert output == "recorded backend output"
    assert backend.program == parse_source("mostrar 1;")


def test_protocol_backend_remains_separate_from_pipeline_validation() -> None:
    backend = RecordingBackend()

    with pytest.raises(SemanticErrors, match="unknown"):
        compile_source("mostrar unknown;", backend)

    assert backend.program is None
