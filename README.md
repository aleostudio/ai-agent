# Simple AI agent to chat with a LLM

This agent will interact with an existing Ollama instance or other AI providers as a chatbot, keeping short-term memory per user.

## Configuration

Create your ```.env``` file by copying:

```bash
cp env.dist .env
```

Then, customize it if needed.

## Build and run service

First, install dependencies with:

```bash
pip install --no-cache-dir -r requirements.txt
```

If you prefer to use **uv**, create and activate your **venv** with:

```bash
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

If you want to run the service through your local interpreter:

```bash
uvicorn app.main:app --host 0.0.0.0 --port 9201
```

If you want to use Docker, build and run with:

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
    "prompt": "Hi! Can you write me a list of things I can ask you?"
}'
```

The response will be something like this payload:

```json
{
    "user_id": "3e12c65f-fa39-4a20-aa6a-e55a56133f07",
    "response": {
        "content": "I'd be happy to help you with questions and tasks. Here's a list of things you can ask me:\n\n**General Knowledge**\n\n* Ask me about history, science, technology, literature, art, music, or any other topic\n* Get information on countries, cities, landmarks, cultures, and more\n* I can provide definitions for words, phrases, and concepts\n\n**Language and Writing**\n\n* Ask me to write a story, poem, or script\n* Get grammar and spelling suggestions\n* Practice writing in different styles (e.g., persuasive, narrative, descriptive)\n* Learn vocabulary through word associations, synonyms, antonyms\n\n**Math and Calculations**\n\n* Solve math problems, from basic arithmetic to advanced calculus\n* Get explanations for mathematical concepts and formulas\n* Calculate percentages, ratios, and conversions\n\n**Conversational Dialogue**\n\n* Engage in a conversation on a topic of your choice\n* Role-play different scenarios (e.g., job interview, customer service)\n* Practice social skills, such as active listening and responding\n\n**Creative Tasks**\n\n* Generate ideas for creative projects (e.g., writing, art, music)\n* Collaborate on brainstorming exercises\n* Get feedback on drafts or works-in-progress\n\n**Jokes and Entertainment**\n\n* Share jokes or puns with me\n* Play simple games (e.g., 20 Questions, Hangman)\n* Listen to or generate humor-related content\n\n**Trivia and Quizzes**\n\n* Take a quiz on various subjects\n* Test your knowledge on specific topics\n* Get hints or explanations for tricky questions\n\nFeel free to get creative and ask me anything that's on your mind!",
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

To keep **short-term memory**, add the `user_id` property returned from the first call (or pass your user_id in the first interaction to use it):

```bash
curl -XPOST "http://localhost:9201/interact" \
--header "Content-Type: application/json" \
--data '{
    "prompt": "Excuse me, I forgot to tell you that my name is Alessandro!",
    "user_id": "3e12c65f-fa39-4a20-aa6a-e55a56133f07"
}'
```

---

### Memory status

To check memory status, you can run these payloads:

**Check if there are active users with initialized memory:**

```bash
curl -XGET "http://localhost:9201/memory"
```

**Check memory status for given user:**

```bash
curl -XGET "http://localhost:9201/memory/3e12c65f-fa39-4a20-aa6a-e55a56133f07"
```

**Delete memory for given user:**

```bash
curl -XDELETE "http://localhost:9201/memory/3e12c65f-fa39-4a20-aa6a-e55a56133f07"
```

---

## Tests

Ensure you have ```pytest``` installed, otherwise:

```bash
pip install pytest
```

Then, launch tests with:

```bash
pytest tests/
```

## Debug

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
