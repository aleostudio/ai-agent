import app.prompts as prompts


def test_build_system_prompt_chat_with_tools_appends_tools_section():
    out = prompts.build_system_prompt(role="chat", tool_names=["mcp__calc"])
    assert "You can use external tools through the system." in out


def test_build_system_prompt_orchestrator_injects_agents():
    out = prompts.build_system_prompt(
        role="a2a_orchestrator",
        agents=[{"name": "math-agent", "description": "Does math"}],
    )
    assert "math-agent" in out
    assert "Does math" in out


def test_build_system_prompt_client_injects_skills():
    out = prompts.build_system_prompt(
        role="a2a_client",
        skills=[{"name": "billing", "description": "Billing support"}],
    )
    assert "billing" in out
    assert "Billing support" in out
