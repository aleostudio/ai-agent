#!/usr/bin/env python3
#####################################################
#            _____                          _       #
#      /\   |_   _|                        | |      #
#     /  \    | |     __ _  __ _  ___ _ __ | |_     #
#    / /\ \   | |    / _` |/ _` |/ _ \ '_ \| __|    #
#   / ____ \ _| |_  | (_| | (_| |  __/ | | | |_     #
#  /_/    \_\_____|  \__,_|\__, |\___|_| |_|\__|    #
#                           __/ |  | |              #
#    __ _  ___ _ __   ___ _|___/_ _| |_ ___  _ __   #
#   / _` |/ _ \ '_ \ / _ \ '__/ _` | __/ _ \| '__|  #
#  | (_| |  __/ | | |  __/ | | (_| | || (_) | |     #
#   \__, |\___|_| |_|\___|_|  \__,_|\__\___/|_|     #
#    __/ |                                          #
#   |___/   alessandro.orru <at> aleostudio.com     #
#                                                   #
#                                                   #
# Clones the current boilerplate into a new folder  #
# with renamed classes, files, ports, and A2A card. #
#                                                   #
# Ready to run with `make dev`.                     #
#                                                   #
# Usage:                                            #
# 1. Edit the variables below                       #
# 2. python scripts/create_agent.py                 #
# 3. cd ../<agent-slug> && make setup && make dev   #
#                                                   #
#####################################################

import os
import re
import shutil
from pathlib import Path
from models import AgentConfig, SourceLayout

# ==============================================================================
# Config
# ==============================================================================

# Multi-agent scaffold config: add as many agents as needed.
AGENT_CONFIGS: list[AgentConfig] = [
    AgentConfig(
        agent_name="New agent",
        agent_description="A general-purpose assistant that answers questions using an LLM.",
        agent_port=9501,
        a2a_card_id="general-assistant",
        a2a_card_name="General Knowledge",
        a2a_card_description="Answers general questions, provides explanations, and helps with non-specialized tasks.",
        a2a_card_tags=["general", "assistant", "knowledge", "qa"],
        a2a_card_examples=["Tell me about Python", "What's the weather like?", "Explain quantum computing"],
    )
]

# ==============================================================================
# DO NOT EDIT BELOW
# ==============================================================================


def _load_agent_configs() -> list[AgentConfig]:
    return AGENT_CONFIGS


# Read UTF-8 text content from file
def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# Extract first regex group with fallback default
def _extract(pattern: str, text: str, default: str, flags: int = 0) -> str:
    match = re.search(pattern, text, flags)
    return match.group(1) if match else default


# Read an env key value from env-like text content
def _extract_env_value(content: str, key: str, default: str) -> str:
    pattern = rf"(?m)^{re.escape(key)}=(.*)$"
    match = re.search(pattern, content)
    if not match:
        return default
    return match.group(1).strip().strip('"').strip("'")


# Discover source project naming/layout to build dynamic replacements
def discover_source_layout(src_dir: Path) -> SourceLayout:
    main_text = _read_text(src_dir / "app" / "main.py")
    agent_import = re.search(r"from app\.agent\.(\w+) import (\w+)", main_text)
    if not agent_import:
        raise RuntimeError("Could not detect agent import in app/main.py")

    agent_module = agent_import.group(1)
    agent_class = agent_import.group(2)

    agent_file = src_dir / "app" / "agent" / f"{agent_module}.py"
    if not agent_file.exists():
        raise RuntimeError(f"Agent file not found: {agent_file}")

    agent_text = _read_text(agent_file)
    state_import = re.search(r"from app\.agent\.(\w+) import (\w+State)\b", agent_text)
    if state_import:
        state_module = state_import.group(1)
        state_class = state_import.group(2)
    else:
        state_module = "agent_state"
        state_class = "AgentState"

    api_text = _read_text(src_dir / "app" / "api.py")
    request_class = _extract(r"class\s+([a-zA-Z0-9_]+Request)\(", api_text, "AgentRequest")

    a2a_text = _read_text(src_dir / "app" / "core" / "a2a" / "a2a.py")
    a2a_executor_class = _extract(r"class\s+([a-zA-Z0-9_]+A2AExecutor)\(", a2a_text, "AgentA2AExecutor")

    config_text = _read_text(src_dir / "app" / "config.py")
    app_name_default = _extract(r'APP_NAME:\s*str\s*=\s*os\.getenv\("APP_NAME",\s*"([^"]+)"\)', config_text, "AI agent")

    env_dist_path = src_dir / "env.dist"
    env_dist_text = _read_text(env_dist_path) if env_dist_path.exists() else ""
    app_port = _extract_env_value(env_dist_text, "APP_PORT", "9201")
    app_url = _extract_env_value(env_dist_text, "APP_URL", f"http://localhost:{app_port}")

    pyproject_path = src_dir / "pyproject.toml"
    pyproject_text = _read_text(pyproject_path) if pyproject_path.exists() else ""
    package_name = _extract(r'(?m)^name\s*=\s*"([^"]+)"\s*$', pyproject_text, "ai-agent")

    compose_path = src_dir / "docker-compose.yml"
    compose_text = _read_text(compose_path) if compose_path.exists() else ""
    container_name = _extract(r"(?m)^\s*container_name:\s*([^\s]+)\s*$", compose_text, "ai-agent")

    return SourceLayout(
        agent_module=agent_module,
        agent_class=agent_class,
        state_module=state_module,
        state_class=state_class,
        request_class=request_class,
        a2a_executor_class=a2a_executor_class,
        app_name_default=app_name_default,
        app_port=app_port,
        app_url=app_url,
        package_name=package_name,
        container_name=container_name,
    )


# Update strings like 'Math Specialist' -> 'math-specialist'
def to_slug(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


# Update strings like 'Math Specialist' -> 'math_specialist'
def to_snake(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "_", s)
    return s.strip("_")


# Update strings like 'Math Specialist' -> 'MathSpecialist'
def to_camel(name: str) -> str:
    return "".join(word.capitalize() for word in re.split(r"[^a-zA-Z0-9]+", name.strip()) if word)


# File helpers
def is_text_file(path: Path) -> bool:
    if path.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".ico", ".woff", ".woff2", ".ttf", ".eot", ".otf", ".zip", ".tar", ".gz", ".bz2", ".pyc", ".pyo", ".so", ".dll", ".exe", ".bin"}:
        return False
    try:
        path.read_text(encoding="utf-8")
        return True
    except (UnicodeDecodeError, PermissionError):
        return False


# Apply ordered string replacements to a text file
def replace_in_file(path: Path, replacements: list[tuple[str, str]]) -> None:
    try:
        content = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, PermissionError):
        return
    original = content
    for old, new in replacements:
        content = content.replace(old, new)
    if content != original:
        path.write_text(content, encoding="utf-8")


# A2A card generator
def write_a2a_card(path: Path, display: str, description: str, card_id: str, card_name: str, card_description: str, card_tags: list[str], card_examples: list[str]) -> None:
    tags_str = ", ".join(f'"{t}"' for t in card_tags)
    examples_str = ", ".join(f'"{e}"' for e in card_examples)
    content = f'''from a2a.types import AgentCapabilities, AgentCard, AgentSkill
from app.config import settings


# Build agent card from settings
def build_agent_card() -> AgentCard:
    return AgentCard(
        name="{display}",
        description="{description}",
        url=settings.APP_URL,
        version=settings.APP_VERSION,
        capabilities=AgentCapabilities(streaming=False, push_notifications=False),
        default_input_modes=["text/plain"],
        default_output_modes=["text/plain"],
        skills=[
            AgentSkill(
                id="{card_id}",
                name="{card_name}",
                description="{card_description}",
                tags=[{tags_str}],
                examples=[{examples_str}],
            )
        ],
    )
'''
    path.write_text(content, encoding="utf-8")


# Env generator
# Set or append a single env key-value pair in env-like text
def _set_env_key(content: str, key: str, value: str) -> str:
    line = f"{key}={value}"
    pattern = rf"(?m)^{re.escape(key)}=.*$"
    if re.search(pattern, content):
        return re.sub(pattern, line, content, count=1)
    return content.rstrip() + f"\n{line}\n"


def create_env_file(env_dist_path: Path, env_path: Path, display: str, port: int) -> None:
    content = env_dist_path.read_text(encoding="utf-8")
    content = _set_env_key(content, "APP_NAME", f'"{display}"')
    content = _set_env_key(content, "APP_PORT", str(port))
    content = _set_env_key(content, "APP_URL", f"http://localhost:{port}")

    env_path.write_text(content, encoding="utf-8")


# Main
def create_single_agent(src_dir: Path, source: SourceLayout, config: AgentConfig) -> bool:
    # Derive names
    display = config.agent_name.strip()
    slug = to_slug(display)
    snake = to_snake(display)
    camel = to_camel(display)
    port_str = str(config.agent_port)

    # Paths
    dst_dir = src_dir.parent / slug
    if dst_dir.exists():
        print(f"Target folder already exists: {dst_dir}")
        return False

    print("=====================================")
    print(f'Creating agent "{display}" ...')
    print("=====================================")
    print(f"Slug:  {slug}")
    print(f"Snake: {snake}")
    print(f"Camel: {camel}")
    print(f"Port:  {port_str}")
    print()

    copy_tree(src_dir, dst_dir)
    print(f"Copied to {dst_dir}")

    rename_files(dst_dir, source, snake)
    replace_contents(dst_dir, source, snake, camel, display, slug, port_str)
    rewrite_a2a_card(dst_dir, config)
    generate_env(dst_dir, display, config.agent_port)

    # Done
    print()
    print(f'Agent "{display}" created in {dst_dir}/')
    print(f"Port: {port_str}")
    print()
    print(f"cd ../{slug} && make setup && make dev")
    print()
    print()
    return True


def main() -> None:
    src_dir = Path(__file__).resolve().parent.parent
    source = discover_source_layout(src_dir)
    configs = _load_agent_configs()
    if not configs:
        print("No agent configs provided. Nothing to do.")
        return

    created = 0
    for config in configs:
        if create_single_agent(src_dir, source, config):
            created += 1

    print(f"Scaffold completed: created {created}/{len(configs)} agent(s)")


# Copy tree (exclude hidden dirs, __pycache__, uv.lock)
def copy_tree(src_dir: Path, dst_dir: Path) -> None:
    keep_hidden = {".gitignore", ".dockerignore"}

    def ignore(directory: str, entries: list[str]) -> set[str]:
        is_root = os.path.abspath(directory) == str(src_dir)
        return {
            e for e in entries
            if (e.startswith(".") and e not in keep_hidden)
            or e == "__pycache__"
            or (is_root and e in {"uv.lock"})
        }

    shutil.copytree(src_dir, dst_dir, ignore=ignore)


# Rename current agent files to the new agent names
def rename_files(dst_dir: Path, source: SourceLayout, snake: str) -> None:
    file_renames = [
        (Path(f"app/agent/{source.agent_module}.py"), Path(f"app/agent/{snake}.py")),
        (Path(f"app/agent/{source.state_module}.py"), Path(f"app/agent/{snake}_state.py")),
    ]
    for old_rel, new_rel in file_renames:
        old_path = dst_dir / old_rel
        if old_path.exists():
            old_path.rename(dst_dir / new_rel)
            print(f"Renamed {old_rel} -> {new_rel}")


# Content replacements (order matters: specific first)
def replace_contents(dst_dir: Path, source: SourceLayout, snake: str, camel: str, display: str, slug: str, port_str: str) -> None:
    replacements: list[tuple[str, str]] = [
        (source.a2a_executor_class, f"{camel}A2AExecutor"),
        (source.state_class, f"{camel}State"),
        (source.request_class, f"{camel}Request"),
        (f"class {source.agent_class}:", f"class {camel}:"),
        (f"from app.agent.{source.agent_module} import {source.agent_class}", f"from app.agent.{snake} import {camel}"),
        (f"agent: {source.agent_class} | None = None", f"agent: {camel} | None = None"),
        (f"agent: Optional[{source.agent_class}] = None", f"agent: Optional[{camel}] = None"),
        (f"runtime.agent = {source.agent_class}(", f"runtime.agent = {camel}("),
        (f"return {source.agent_class}(", f"return {camel}("),
        (f"from app.agent.{source.state_module} import {source.state_class}", f"from app.agent.{snake}_state import {camel}State"),
        (f"from app.core.a2a import {source.a2a_executor_class}", f"from app.core.a2a import {camel}A2AExecutor"),
        (f"agent_executor = {source.a2a_executor_class}(", f"agent_executor = {camel}A2AExecutor("),
        (source.state_module, f"{snake}_state"),
        (source.app_name_default, display),
        (f'"{source.package_name}"', f'"{slug}"'),
        (f"container_name: {source.container_name}", f"container_name: {slug}"),
        (source.app_url, f"http://localhost:{port_str}"),
        (source.app_port, port_str),
    ]
    replacements = [(old, new) for old, new in replacements if old and old != new]

    count = sum(1 for p in dst_dir.rglob("*") if p.is_file() and is_text_file(p) and (replace_in_file(p, replacements) or True))
    print(f"Processed {count} text files")


# Rewrite a2a_card.py
def rewrite_a2a_card(dst_dir: Path, config: AgentConfig) -> None:
    write_a2a_card(
        dst_dir / "app" / "a2a_card.py",
        display=config.agent_name.strip(),
        description=config.agent_description,
        card_id=config.a2a_card_id,
        card_name=config.a2a_card_name,
        card_description=config.a2a_card_description,
        card_tags=config.a2a_card_tags,
        card_examples=config.a2a_card_examples,
    )
    print("Wrote a2a_card.py")


# Create .env from env.dist
def generate_env(dst_dir: Path, display: str, port: int) -> None:
    env_dist = dst_dir / "env.dist"
    if env_dist.exists():
        create_env_file(env_dist, dst_dir / ".env", display, port)
        print("Created .env from env.dist")


if __name__ == "__main__":
    main()
