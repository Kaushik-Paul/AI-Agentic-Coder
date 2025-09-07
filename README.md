# AI Agentic Coder

[![Live Demo – Hugging Face Space](https://img.shields.io/badge/Live%20Demo-Hugging%20Face%20Space-yellow?logo=huggingface&logoColor=white)](https://huggingface.co/spaces/kaushikpaul/AI-Agentic-Coder)

An AI-powered agentic coding assistant that:
- Turns your natural language requirements into a working Python module
- Designs the module, implements the code, writes simple tests, and builds a demo UI
- Packages the output and launches the generated Gradio app with a public URL

Backed by a multi-agent CrewAI pipeline, the app coordinates “engineering lead”, “backend”, “frontend”, “QA”, and a “runner” agent to deliver end-to-end results.

## Live Demo
- Visit the hosted Space: https://huggingface.co/spaces/kaushikpaul/AI-Agentic-Coder

## Features
- **Idea → Running App in Minutes**
  - One-click pipeline: design the module → implement code → generate tests → scaffold a Gradio demo → launch and return live/public URLs.
- **Multi‑Agent Orchestration (CrewAI)**
  - Specialized agents for engineering lead, backend, frontend, QA, and runtime. Tasks are declared in YAML and executed sequentially for predictable outcomes.
- **Production‑Friendly Reliability**
  - Built‑in retry limits and execution timeouts for coding/testing agents, plus automatic cleanup of previous app processes to avoid port conflicts.
- **Model‑Flexible by Design**
  - Swap LLMs per‑agent via `config/agents.yaml` using OpenRouter model IDs. Compatible with OpenAI‑style endpoints and easy to tune per role.
- **Modern Developer UX**
  - Polished Gradio UI with non‑blocking background execution, streaming progress, one‑click example loader, and strict URL extraction/validation on completion.
- **Secure Artifact Delivery**
  - Packages outputs, uploads to Google Cloud Storage, and returns short‑lived signed URLs—no secrets in code, environment‑based configuration.
- **Extensible & Maintainable**
  - Add agents, tasks, or custom tools (e.g., `python_code_run_tool.py`) without touching the core pipeline. Everything is declarative and composable.
- **Runs Local or in the Cloud**
  - Works out of the box on your machine and is ready for Hugging Face Spaces deployment with the same entry point.

## Architecture Overview
- **Crew & Agents:** `src/ai_agentic_coder/crew.py`
  - Agents configured in `src/ai_agentic_coder/config/agents.yaml`
  - Tasks configured in `src/ai_agentic_coder/config/tasks.yaml`
- **Tools:**
  - Python code runner and GCS uploader: `src/ai_agentic_coder/tools/python_code_run_tool.py`
- **UI:** `src/ai_agentic_coder/gradio_ui.py`
- **Entry point:** `src/ai_agentic_coder/main.py`
- **Outputs:** `src/ai_agentic_coder/output/`
  - Design doc, backend module, test module, demo app, and utility artifacts

### Pipeline (from tasks.yaml)
1. `design_task` → writes `src/ai_agentic_coder/output/{module_name}_design.md`
2. `code_task` → writes `src/ai_agentic_coder/output/{module_name}` (e.g., `accounts.py`)
3. `frontend_task` → writes `src/ai_agentic_coder/output/app.py` (Gradio demo with share=True)
4. `test_task` → writes `src/ai_agentic_coder/output/test_{module_name}`
5. `python_code_run_task` → uploads zip to GCS, runs the app, and returns two URLs; also writes `src/ai_agentic_coder/output/gradio_public_url.txt`

## Prerequisites
- Python 3.10–3.12 (project targets >=3.10 per `pyproject.toml`)
- A modern browser (Chrome, Edge, Safari, Firefox)
- API keys and credentials (see Configuration)

## Quick Start

### 1) Clone the repo
```bash
git clone https://github.com/Kaushik-Paul/AI-Agentic-Coder.git
cd AI-Agentic-Coder
```

### 2) (Optional) Create and activate a virtual environment
```bash
python3 -m venv .venv
source .venv/bin/activate    # Windows: .venv\Scripts\activate
```

### 3) Install dependencies
#### Option A — Install with uv (recommended)
1) Install uv
- Linux/macOS:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
# ensure ~/.local/bin is on your PATH
export PATH="$HOME/.local/bin:$PATH"
```
- Windows (PowerShell):
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

2) Sync dependencies
```bash
uv sync
```

#### Option B — Install with pip
```bash
pip install -r requirements.txt
```

### 4) Create a .env file
Create a `.env` file in the project root with the following variables (adjust as needed):

```ini
# ——— LLM provider (using OpenRouter-hosted models in agents.yaml) ———
OPENROUTER_API_KEY=your_openrouter_key
# Optional but commonly needed when using OpenRouter via OpenAI-compatible clients:
# OPENAI_API_BASE=https://openrouter.ai/api/v1
# OPENAI_API_KEY=${OPENROUTER_API_KEY}

# ——— Google Cloud Storage (used by PythonCodeRunTool) ———
GCP_PROJECT_ID=your_gcp_project_id
GCP_BUCKET_NAME=your_public_or_private_bucket_name
# Base64-encoded service account JSON. Example to generate:
#   cat service_account.json | base64 -w 0
GCP_SERVICE_KEY=base64_encoded_service_account_json
```

### 5) Run the app
Using uv:
```bash
uv run python -m src.ai_agentic_coder.main
```
Using python directly:
```bash
python -m src.ai_agentic_coder.main
```
Gradio will print a local URL (e.g., http://127.0.0.1:7860). Open it in your browser.

## Built with CrewAI
This project leverages [CrewAI](https://docs.crewai.com/en/introduction), a powerful framework for orchestrating role-playing, autonomous AI agents. CrewAI enables the creation of sophisticated AI workflows where different agents can work together to accomplish complex tasks.

Key features used in this project:
- **Agents**: Specialized AI agents for design, backend, frontend, testing, and running
- **Tasks**: Well-defined tasks that agents perform sequentially
- **Tools**: Custom Python tool to package, upload, and run generated code
- **Delegation**: Sequential, YAML-driven orchestration of the pipeline

## Configuration

### LLMs and Agents
- File: `src/ai_agentic_coder/config/agents.yaml`
- Default agents use OpenRouter-hosted models (e.g., `openrouter/meta-llama/llama-3.1-405b-instruct:free`, `openrouter/moonshotai/kimi-k2:free`).
- To change models or providers, update the `llm` field for each agent. Ensure appropriate API keys and base configuration are set for your provider.

### Tasks & Outputs
- File: `src/ai_agentic_coder/config/tasks.yaml`
- Pipeline and outputs are described in the Architecture section.

### UI Behavior
- File: `src/ai_agentic_coder/gradio_ui.py`
- You provide: `Requirements`, `Module Name` (without .py), `Class Name`.
- The app displays a progress bar during execution and, on success, two URLs: a signed download URL and a live app URL.

## Usage
1. Open the app in your browser.
2. Paste or write your requirements (what you want to build).
3. Enter a module name (e.g., `accounts`) and class name (e.g., `Account`).
4. Click “Run AI Coder”.
5. Wait a few minutes while the pipeline runs. When done, you’ll see:
   - A signed Google Cloud Storage URL to download the generated artifacts as a zip
   - A public/live URL of the generated Gradio demo app

## Outputs
Generated files are saved under `src/ai_agentic_coder/output/`:
- `{module_name}_design.md` — Detailed design produced by the engineering lead agent
- `{module_name}.py` — The generated backend module
- `app.py` — A minimal Gradio UI demonstrating the backend (launched with share=True)
- `test_{module_name}` — Unit test module for the backend
- `gradio_public_url.txt` — A convenience file containing the live URL output

## Deployment
- The project is already hosted on Hugging Face Spaces: https://huggingface.co/spaces/kaushikpaul/AI-Agentic-Coder
- To deploy your own Space:
  - Set Space SDK to “Gradio” and point to `src/ai_agentic_coder/main.py` as the entry file.
  - Add required secrets in the Space settings:
    - `OPENROUTER_API_KEY`
    - `GCP_PROJECT_ID`, `GCP_BUCKET_NAME`, `GCP_SERVICE_KEY` (base64-encoded service account JSON)
  - Ensure the Python version matches (3.10–3.12) and install via `requirements.txt` or `pyproject.toml`.

## Troubleshooting
- **Missing or invalid API keys/credentials**
  - Verify `.env` values. Ensure OpenRouter key and GCP service key are valid; confirm bucket exists and is accessible.
- **GCS upload errors**
  - Confirm `GCP_SERVICE_KEY` contains a valid base64-encoded service account JSON with `storage.objects.create` permission.
- **Live URL not detected**
  - The runner waits up to 60 seconds to capture a public URL. If the generated UI didn’t enable `share=True` or the network blocks tunnels, you may see: “Gradio started but no accessible URL was detected within 60 seconds.” Re-run or check network settings.
- **Virtualenv issues on Windows**
  - Use `.venv\Scripts\activate` and ensure `python` points to the venv interpreter.

## Tech Stack
- **Python**: 3.10–3.12
- **Frameworks/Libraries**: CrewAI, Gradio 5, google-cloud-storage, python-dotenv, requests, httpx
- **Orchestration**: YAML-configured agents and tasks via CrewAI
- **UI**: Gradio Blocks with live progress and URL surfacing

## Security & Privacy
- Do not commit `.env` files or secrets.
- Use least-privilege GCP service accounts. Prefer short-lived signed URLs for distribution (already used here).

## License
This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
