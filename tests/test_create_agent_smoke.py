import os
import subprocess
import sys
from pathlib import Path


def test_create_agent_smoke(tmp_path: Path):
    repo_root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env.update(
        {
            "AGENT_NAME": "Smoke Agent",
            "AGENT_PORT": "9799",
            "CREATE_AGENT_TARGET_BASE_DIR": str(tmp_path),
        }
    )

    result = subprocess.run(
        [sys.executable, "scripts/create_agent.py"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr or result.stdout

    generated = tmp_path / "smoke-agent"
    assert generated.exists()

    generated_agent = generated / "app" / "agent" / "smoke_agent.py"
    generated_main = generated / "app" / "main.py"
    generated_env = generated / ".env"

    assert generated_agent.exists()
    assert generated_main.exists()
    assert generated_env.exists()

    agent_text = generated_agent.read_text(encoding="utf-8")
    main_text = generated_main.read_text(encoding="utf-8")
    env_text = generated_env.read_text(encoding="utf-8")

    assert "class SmokeAgent:" in agent_text
    assert "from app.agent.smoke_agent import SmokeAgent" in main_text
    assert "runtime.agent = SmokeAgent(" in main_text
    assert "runtime.agent = Agent(" not in main_text
    assert "APP_PORT=9799" in env_text
