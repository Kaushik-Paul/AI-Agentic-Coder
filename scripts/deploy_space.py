#!/usr/bin/env python
import os

from huggingface_hub import HfApi


SPACE_ID = os.getenv("HF_SPACE_ID", "kaushikpaul/AI-Agentic-Coder")

ALLOW_PATTERNS = [
    "README.md",
    "requirements.txt",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "LICENSE",
    "src/**",
]

IGNORE_PATTERNS = [
    "src/ai_agentic_coder/output/*.md",
    "src/ai_agentic_coder/output/app.py",
    "src/ai_agentic_coder/output/test_*.py",
    "src/ai_agentic_coder/output/*.txt",
    "src/ai_agentic_coder/output/*.zip",
    "src/**/__pycache__/**",
]

DELETE_PATTERNS = [
    ".venv/**",
    "venv/**",
    "env/**",
    ".env",
    ".idea/**",
    ".vscode/**",
    ".ruff_cache/**",
    "__pycache__/**",
    "src/**/__pycache__/**",
    "src/ai_agentic_coder/output/*.md",
    "src/ai_agentic_coder/output/app.py",
    "src/ai_agentic_coder/output/test_*.py",
    "src/ai_agentic_coder/output/*.txt",
    "src/ai_agentic_coder/output/*.zip",
]


def main() -> None:
    print(f"Deploying to Hugging Face Space: {SPACE_ID}")
    HfApi().upload_folder(
        repo_id=SPACE_ID,
        repo_type="space",
        folder_path=".",
        allow_patterns=ALLOW_PATTERNS,
        ignore_patterns=IGNORE_PATTERNS,
        delete_patterns=DELETE_PATTERNS,
        commit_message="Deploy Space",
    )
    print(f"Space available at https://huggingface.co/spaces/{SPACE_ID}")


if __name__ == "__main__":
    main()
