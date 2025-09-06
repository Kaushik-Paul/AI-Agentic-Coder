#!/usr/bin/env python
import warnings
import os
from dotenv import load_dotenv

from crewai.agent import Agent as _CrewaiAgent
from src.ai_agentic_coder.gradio_ui import create_interface

# Load environment variables
load_dotenv(override=True)
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
os.makedirs('output', exist_ok=True)

try:
    if not getattr(_CrewaiAgent, "_patched_skip_docker_validation", False):
        def _skip_docker_validation(self):  # type: ignore[return-value]
            """Override to bypass Docker validation entirely."""
            return None

        _CrewaiAgent._validate_docker_installation = _skip_docker_validation  # type: ignore[method-assign]
        _CrewaiAgent._patched_skip_docker_validation = True  # type: ignore[attr-defined]
except ImportError:
    pass

if __name__ == "__main__":
    ai_agentic_coder = create_interface()
    ai_agentic_coder.launch(server_port=8250)
