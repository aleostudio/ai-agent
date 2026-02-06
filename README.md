# Simple AI agent with MCP client

This agent will interact with an existing **Ollama** instance or other AI providers as a chatbot and it has a built-in **MCP client** to connect to remote MCP servers to use their **tools**.

## Index

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Run service](#run-service)
- [Customize system prompt](#customize-system-prompt)
- [Tests](#tests)
- [Debug in VSCode](#debug-in-vscode)

---

## Prerequisites

- Python >= 3.12
- [uv](https://docs.astral.sh/uv/getting-started/installation) and [pip](https://pip.pypa.io/en/stable/installation) installed

[↑ index](#index)

---

## Configuration

Init **virtualenv** and install dependencies with:

```bash
uv venv
source .venv/bin/activate
uv sync
```

Create your ```.env``` file by copying:

```bash
cp env.dist .env
```

Then, customize it if needed (e.g. **model**, **temperature** and so on).

If you want to **enable MCP support**, update these env vars with your URL (`MCP_SERVERS` is in JSON array format; you can add several servers):

```bash
MCP_ENABLED=True
MCP_SERVERS='[{"name": "mcp-server", "transport": "sse", "url": "http://localhost:8000/sse"}]'
```

> **NOTE**: 
> to work properly, tool calling needs a fairly intelligent model, so consider using at least an **8b model**

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

---

## Customize system prompt

In order to customize **system prompts** open the file `app/prompts.py`.
Here you will find:

- `SYSTEM_PROMPT`: standard prompt used for generic questions
- `SYSTEM_PROMPT_TOOLS`: prompt used by LLM if tools calling is enabled

[↑ index](#index)

---

## Tests

Ensure you have ```pytest``` installed, otherwise:

```bash
uv pip install pytest
```

Then, launch tests with:

```bash
pytest tests/
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

Made with ♥️ by Alessandro Orrù
