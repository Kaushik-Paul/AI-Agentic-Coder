#!/usr/bin/env python
import warnings

from dotenv import load_dotenv
import gradio as gr

from src.ai_agentic_coder.gradio_ui import create_interface

# Load environment variables
load_dotenv()
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

if __name__ == "__main__":
    ai_agentic_coder = create_interface()
    ai_agentic_coder.launch(theme=gr.themes.Soft(), ssr_mode=False)
