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
# 2. python create_agent.py                         #
# 3. cd ../<agent-slug> && make setup && make dev   #
#                                                   #
#####################################################

import os
import re
import shutil
from pathlib import Path

# =============================================================================
# Config
# =============================================================================

agent_name           = "New agent"
agent_description    = "A general-purpose assistant that answers questions using an LLM."
agent_port           = 9501
a2a_card_id          = "general-assistant"
a2a_card_name        = "General Knowledge"
a2a_card_description = "Answers general questions, provides explanations, and helps with non-specialized tasks."
a2a_card_tags        = ["general", "assistant", "knowledge", "qa"]
a2a_card_examples    = ["Tell me about Python", "What's the weather like?", "Explain quantum computing"]

# =============================================================================

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
from app.core.config import settings


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
def create_env_file(env_dist_path: Path, env_path: Path, display: str, port: int) -> None:
    content = env_dist_path.read_text(encoding="utf-8")
    patches = {
        'APP_NAME="AI agent"': f'APP_NAME="{display}"',
        "APP_PORT=9201": f"APP_PORT={port}",
        "APP_URL=http://localhost:9201": f"APP_URL=http://localhost:{port}",
    }
    for old, new in patches.items():
        content = content.replace(old, new)

    env_path.write_text(content, encoding="utf-8")


# Main
def main() -> None:

    # Derive names
    display = agent_name.strip()
    slug = to_slug(display)
    snake = to_snake(display)
    camel = to_camel(display)
    port_str = str(agent_port)

    # Paths
    src_dir = Path(__file__).resolve().parent
    dst_dir = src_dir.parent / slug
    if dst_dir.exists():
        print(f"Target folder already exists: {dst_dir}")
        return

    print(f'Creating agent "{display}" ...')
    print(f"Slug:  {slug}")
    print(f"Snake: {snake}")
    print(f"Camel: {camel}")
    print(f"Port:  {port_str}")
    print()

    copy_tree(src_dir, dst_dir)
    print(f"Copied to {dst_dir}")

    rename_files(dst_dir, snake)
    replace_contents(dst_dir, snake, camel, display, slug, port_str)
    rewrite_a2a_card(dst_dir)
    generate_env(dst_dir, display)

    # Done
    print()
    print(f'Agent "{display}" created in ../{slug}/')
    print(f"Port: {port_str}")
    print()
    print(f"cd ../{slug} && make setup && make dev")
    print()


# Copy tree (exclude hidden dirs, __pycache__, this script, uv.lock)
def copy_tree(src_dir: Path, dst_dir: Path) -> None:
    script_name = Path(__file__).name
    keep_hidden = {".gitignore", ".dockerignore"}

    def ignore(directory: str, entries: list[str]) -> set[str]:
        is_root = os.path.abspath(directory) == str(src_dir)
        return {
            e for e in entries
            if (e.startswith(".") and e not in keep_hidden)
            or e == "__pycache__"
            or (is_root and e in {script_name, "uv.lock"})
        }

    shutil.copytree(src_dir, dst_dir, ignore=ignore)


# Rename files with "agent" in the name
def rename_files(dst_dir: Path, snake: str) -> None:
    file_renames = [
        (Path("app/agent/agent.py"), Path(f"app/agent/{snake}.py")),
        (Path("app/model/agent_request.py"), Path(f"app/model/{snake}_request.py")),
        (Path("app/agent/agent_state.py"), Path(f"app/agent/{snake}_state.py")),
    ]
    for old_rel, new_rel in file_renames:
        old_path = dst_dir / old_rel
        if old_path.exists():
            old_path.rename(dst_dir / new_rel)
            print(f"Renamed {old_rel} -> {new_rel}")


# Content replacements (order matters: specific first)
def replace_contents(dst_dir: Path, snake: str, camel: str, display: str, slug: str, port_str: str) -> None:
    replacements = [
        ("AgentA2AExecutor", f"{camel}A2AExecutor"),
        ("AgentState", f"{camel}State"),
        ("AgentRequest", f"{camel}Request"),
        ("class Agent:", f"class {camel}:"),
        ("from app.agent.agent import Agent", f"from app.agent.{snake} import {camel}"),
        ("from app.model.agent_request import AgentRequest", f"from app.model.{snake}_request import {camel}Request"),
        ("from app.agent.agent_state import AgentState", f"from app.agent.{snake}_state import {camel}State"),
        ("from app.core.a2a import AgentA2AExecutor", f"from app.core.a2a import {camel}A2AExecutor"),
        ("agent_executor = AgentA2AExecutor(", f"agent_executor = {camel}A2AExecutor("),
        ("agent_state", f"{snake}_state"),
        ("agent_request", f"{snake}_request"),
        ("AI agent", display),
        ('"ai-agent"', f'"{slug}"'),
        ("container_name: ai-agent", f"container_name: {slug}"),
        ("9201", port_str),
    ]

    count = sum(1 for p in dst_dir.rglob("*") if p.is_file() and is_text_file(p) and (replace_in_file(p, replacements) or True))
    print(f"Processed {count} text files")


# Rewrite a2a_card.py
def rewrite_a2a_card(dst_dir: Path) -> None:
    write_a2a_card(
        dst_dir / "app" / "a2a_card.py",
        display=agent_name.strip(),
        description=agent_description,
        card_id=a2a_card_id,
        card_name=a2a_card_name,
        card_description=a2a_card_description,
        card_tags=a2a_card_tags,
        card_examples=a2a_card_examples,
    )
    print("Wrote a2a_card.py")


# Create .env from env.dist
def generate_env(dst_dir: Path, display: str) -> None:
    env_dist = dst_dir / "env.dist"
    if env_dist.exists():
        create_env_file(env_dist, dst_dir / ".env", display, agent_port)
        print("Created .env from env.dist")


if __name__ == "__main__":
    main()
