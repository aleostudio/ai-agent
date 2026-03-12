from dataclasses import dataclass


@dataclass
class AgentConfig:
    agent_name: str
    agent_description: str
    agent_port: int
    a2a_card_id: str
    a2a_card_name: str
    a2a_card_description: str
    a2a_card_tags: list[str]
    a2a_card_examples: list[str]


@dataclass
class SourceLayout:
    agent_module: str
    agent_class: str
    state_module: str
    state_class: str
    request_class: str
    a2a_executor_class: str
    app_name_default: str
    app_port: str
    app_url: str
    package_name: str
    container_name: str