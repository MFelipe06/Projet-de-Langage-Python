from collections.abc import Generator

import pytest

from ardilla.repl import InteractiveSession, repl_prompts
from ardilla.semantic import SemanticErrors


def test_repl_keeps_variables_between_submissions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = InteractiveSession()
    session.submit("var total = 40;")
    session.submit("total = total + 2; mostrar total;")

    assert capsys.readouterr().out == "42\n"


def test_repl_keeps_functions_between_submissions(
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = InteractiveSession()
    session.submit("funcion doubler(x) { devolver x * 2; }")
    session.submit("mostrar doubler(5);")

    assert capsys.readouterr().out == "10\n"


def test_invalid_cell_does_not_replace_the_previous_program(
    capsys: pytest.CaptureFixture[str],
) -> None:
    session = InteractiveSession()
    session.submit("var value = 5;")

    with pytest.raises(SemanticErrors, match="n'est pas déclarée"):
        session.submit("mostrar missing;")

    session.submit("mostrar value;")
    assert capsys.readouterr().out == "5\n"


def test_repl_prompt_generator_uses_send_to_collect_a_cell() -> None:
    submitted: list[str] = []
    prompts: Generator[str, str | None] = repl_prompts(submitted.append)

    assert next(prompts) == "ardilla> "
    assert prompts.send("var x = 1;") == "...> "
    assert prompts.send("mostrar x;") == "...> "
    assert prompts.send(":run") == "ardilla> "
    assert submitted == ["var x = 1;\nmostrar x;"]

    with pytest.raises(StopIteration):
        prompts.send(":quit")


def test_repl_handles_help_and_unexecuted_source_on_exit() -> None:
    submitted: list[str] = []
    messages: list[str] = []
    prompts = repl_prompts(submitted.append, messages.append)

    assert next(prompts) == "ardilla> "
    assert prompts.send(":help") == "ardilla> "
    assert prompts.send("mostrar 1;") == "...> "
    with pytest.raises(StopIteration):
        prompts.send(":quit")

    assert not submitted
    assert len(messages) == 2
    assert "Quitter" in messages[0]
    assert "non exécuté" in messages[1]
