import pytest
from pydantic import ValidationError
from app.model.agent_request import AgentRequest


def test_prompt_is_trimmed():
    payload = AgentRequest(prompt="   hello  ")
    assert payload.prompt == "hello"


@pytest.mark.parametrize("value", ["", "   "])
def test_prompt_cannot_be_empty(value: str):
    with pytest.raises(ValidationError):
        AgentRequest(prompt=value)
