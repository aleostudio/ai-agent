# AI agent with MCP/A2A client

This agent will interact with an existing **Ollama** instance or other AI providers as a chatbot and it has built-in **MCP** and **A2A clients** (as orchestrator or simple client) to connect to remote MCP servers or A2A registry to use their **tools**.

## Index

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Scaffold new agent](#scaffold-new-agent)
- [Run service](#run-service)
- [Customize system prompt](#customize-system-prompt)
- [UI for debug](#ui-for-debug)
- [Tests](#tests)
- [Debug in VSCode](#debug-in-vscode)
- [License](#license)

---

## Prerequisites

- Python >= 3.13 (recommended: 3.13)
- [uv](https://docs.astral.sh/uv/getting-started/installation) and [pip](https://pip.pypa.io/en/stable/installation) installed
- [A2A registry](https://github.com/aleostudio/a2a-registry) if A2A is enabled

[↑ index](#index)

---

## Configuration

Init **virtualenv** and install dependencies with:

```bash
uv venv --python 3.13
source .venv/bin/activate
uv sync
```

Create your ```.env``` file by copying:

```bash
cp env.dist .env
```

Then, customize it if needed (e.g. **model**, **temperature** and so on).

If you want to **stream** the agent response (like a chatbot), change this variable in:

```bash
RESPONSE_TYPE="stream"
```

### MCP

If you want to **enable MCP support**, update these env vars with your URL (`MCP_SERVERS` is in JSON array format; you can add several servers):

```bash
MCP_ENABLED=True
MCP_SERVERS='[{"name": "mcp-server", "transport": "sse", "url": "http://localhost:8000/sse"}]'
```

### A2A

If you want to **enable A2A support**, ensure you have [A2A registry](https://github.com/aleostudio/a2a-registry) up and running and then set these variables:

```bash
A2A_ENABLED=true
A2A_ROLE=orchestrator
REGISTRY_URL=http://localhost:9300
```

Registry self-healing polling (enabled by default) checks every 60 seconds if the agent is still present in the registry and re-registers automatically if missing:

```bash
REGISTRY_POLL_ENABLED=true
REGISTRY_POLL_INTERVAL_S=60.0
```

Pay attention that `orchestrator` will use **other A2A agents** discovered by A2A registry. If you set `client` as role, this agent will work as a specific A2A agent, called by another A2A orchestrator.

> **NOTE**:
> to work properly, tool calling needs a fairly intelligent model, so consider using at least a **8b model** or more.

If you want to run in **pure A2A mode** (without FastAPI HTTP APIs like `/interact`, `/tools`, `/ui`, `/`), set:

```bash
A2A_ENABLED=true
HTTP_API_ENABLED=false
```

> `HTTP_API_ENABLED=false` requires `A2A_ENABLED=true`.

[↑ index](#index)

---

## Scaffold new agent

To clone this boilerplate into a new agent folder with renamed classes/files and updated port/card metadata:

```bash
python scripts/create_agent.py
```

or with Makefile:

```bash
make scaffold
```

Before running it, edit the variables at the top of:

```bash
scripts/create_agent.py
```

[↑ index](#index)

---

## Run service

If you want to run the service through your local **uvicorn** to customize host or port:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9201
```

If you prefer, there is a **shortcut script** with predefined port:

```bash
sh run.sh
```

or simply with the built-in **Makefile**

```bash
make
```

If you want to use **Docker**, build and run with:

```bash
docker-compose build
docker-compose up -d
```

Check if app is up & running

```bash
curl -XGET "http://localhost:9201"
```

You can start the conversation with this simple payload:

```bash
curl -XPOST "http://localhost:9201/interact" \
--header "Content-Type: application/json" \
--data '{
    "prompt": "Hi! Who are you?"
}'
```

The response will be something like this payload:

```json
{
    "response": {
        "content": "Hello! I'm a helpful assistant here to assist with any questions or tasks you may have. I'm designed to provide clear and accurate information on a wide range of topics, from science and history to entertainment and culture. Feel free to ask me anything, and I'll do my best to help!",
        "additional_kwargs": {},
        "response_metadata": {
            "model": "llama3.2",
            "created_at": "2025-03-17T16:34:39.038796Z",
            "done": true,
            "done_reason": "stop",
            "total_duration": 6812295667,
            "load_duration": 41449333,
            "prompt_eval_count": 40,
            "prompt_eval_duration": 138000000,
            "eval_count": 335,
            "eval_duration": 6631000000,
            "message": {
                "role": "assistant",
                "content": "",
                "images": null,
                "tool_calls": null
            }
        },
        "type": "ai",
        "name": null,
        "id": "run-d8728972-8cad-408c-8316-511dd36a5b79-0",
        "example": false,
        "tool_calls": [],
        "invalid_tool_calls": [],
        "usage_metadata": {
            "input_tokens": 40,
            "output_tokens": 335,
            "total_tokens": 375
        }
    }
}
```

[↑ index](#index)

> If `HTTP_API_ENABLED=false`, these HTTP endpoints are disabled and only the A2A server is exposed.

---

## Customize system prompt

In order to customize **system prompts** open the file `app/prompts.py`.
Here you will find:

### SYSTEM_PROMPT

This prompt is used for **standard LLM agent** (generic questions like chatbot).

Set `MCP_ENABLED` and `A2A_ENABLED` to `false` and call the agent via API.

### SYSTEM_PROMPT_A2A_ORCH

This prompt is used for **A2A orchestrator agent** (an orchestrator that route
the request to other A2A agents). The agents are dynamically injected inside the
prompt, reading the agents list from A2A registry.

Set `A2A_ENABLED` to `true` and `A2A_ROLE` to `orchestrator`.

### SYSTEM_PROMPT_A2A_CLIENT

If you need to expose a specific tool through A2A, you need to customize this prompt.
An orchestrator will read your card (`app/a2a_card.py`) and will route the request to this agent.

Set `A2A_ENABLED` to `true` and `A2A_ROLE` to `client`.

### TOOLS_SECTION

Appended dynamically to any base prompt when tools are available (MCP or A2A routing).
Enforces rules to prevent the model from leaking tool names or JSON in responses.

[↑ index](#index)

---

### UI for debug

If you want to test the agent through an UI, there is a built-in ChatGPT-like UI at [this address](http://localhost:9201/ui).

[↑ index](#index)

---

## Tests

Install dev dependencies:

```bash
uv sync --extra dev
```

Then run tests and lint:

```bash
uv run pytest -q
uv run ruff check .
```

[↑ index](#index)

---

## Debug in VSCode

To debug your Python microservice you need to:

- Install **VSCode**
- Ensure you have **Python extension** installed
- Ensure you have selected the **right interpreter with virtualenv** on VSCode
- Click on **Run and Debug** menu and **create a launch.json file**
- From dropdown, select **Python debugger** and **FastAPI**
- Change the ```.vscode/launch.json``` created in the project root with this (customizing host and port if changed):

```json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "FastAPI Debug",
            "type": "debugpy",
            "request": "launch",
            "module": "uvicorn",
            "args": [
                "app.main:app",
                "--host", "0.0.0.0",
                "--port", "9201",
                "--reload"
            ],
            "envFile": "${workspaceFolder}/.env",
            "console": "integratedTerminal",
            "cwd": "${workspaceFolder}",
            "justMyCode": true
        }
    ]
}
```

- Put some breakpoint in the code, then press the **green play button**
- Call the API to debug

[↑ index](#index)

---

## License

This project is licensed under the MIT License.

[↑ index](#index)

---

Made with ♥️ by Alessandro Orrù
