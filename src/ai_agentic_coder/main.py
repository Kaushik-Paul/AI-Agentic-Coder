#!/usr/bin/env python
import warnings
import os
import subprocess
import time
import threading
import re
import gradio as gr
from dotenv import load_dotenv

from crewai.agent import Agent as _CrewaiAgent
from src.ai_agentic_coder.crew import EngineeringTeam

# Load environment variables
load_dotenv(override=True)
warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")
os.makedirs('output', exist_ok=True)

# Example configuration
EXAMPLE_CONFIG = {
    "requirements": \
    """A simple account management system for a trading simulation platform.
    The system should allow users to create an account, deposit funds, and withdraw funds.
    The system should allow users to record that they have bought or sold shares, providing a quantity.
    The system should calculate the total value of the user's portfolio, and the profit or loss from the initial deposit.
    The system should be able to report the holdings of the user at any point in time.
    The system should be able to report the profit or loss of the user at any point in time.
    The system should be able to list the transactions that the user has made over time.
    The system should prevent the user from withdrawing funds that would leave them with a negative balance, or
     from buying more shares than they can afford, or selling shares that they don't have.
     The system has access to a function get_share_price(symbol) which returns the current price of a share, and includes a test implementation that returns fixed prices for AAPL, TSLA, GOOGL.
    - Enforce trading rules""",
    "module_name": "accounts",
    "class_name": "Account"
}

try:
    if not getattr(_CrewaiAgent, "_patched_skip_docker_validation", False):
        def _skip_docker_validation(self):  # type: ignore[return-value]
            """Override to bypass Docker validation entirely."""
            return None

        _CrewaiAgent._validate_docker_installation = _skip_docker_validation  # type: ignore[method-assign]
        _CrewaiAgent._patched_skip_docker_validation = True  # type: ignore[attr-defined]
except ImportError:
    pass

def run_crew(requirements, module_name, class_name, progress=gr.Progress()):
    """Run the crew with the given inputs and return ONLY the raw result text."""
    try:
        # Kill any running processes from previous runs
        subprocess.run(
            ["pkill", "-f", "python.*src.ai_agentic_coder.output.app"],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL
        )
        
        inputs = {
            'requirements': requirements,
            'module_name': f"{module_name}.py",  # Add .py extension
            'class_name': class_name
        }
        
        # Baseline progress hints (wrapper controls real-time progress)
        progress(0.02, desc="Initializing crew...")
        crew = EngineeringTeam().crew()
        
        progress(0.05, desc="Running crew...")
        result = crew.kickoff(inputs=inputs)
        
        raw = str(result.raw) if hasattr(result, 'raw') else str(result)

        return raw
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

def create_interface():
    """Create and return the Gradio interface."""
    with gr.Blocks(title="AI Agentic Coder", theme=gr.themes.Soft()) as demo:
        gr.HTML("""
        <div class="header">
            <div class="brand">AI Agentic Coder</div>
            <div class="subtitle">Generate high-quality Python code with a coordinated CrewAI</div>
        </div>
        """)
        
        with gr.Row():
            # Left column - Inputs (wider so Module/Class stay on one row)
            with gr.Column(scale=3):
                requirements = gr.Textbox(
                    label="Requirements",
                    placeholder="Describe what you want to build...",
                    lines=15,
                    max_lines=20,
                    elem_classes=["card"]
                )
                
                # Module and Class in the same row, minimal .py suffix inside module input via CSS
                with gr.Row():
                    with gr.Column(scale=1, min_width=420):
                        module_name = gr.Textbox(
                            label="Module Name",
                            placeholder="Enter your module name",
                            value="",
                            elem_classes=["card-input"],
                            elem_id="module-name"
                        )
                    with gr.Column(scale=1, min_width=420):
                        class_name = gr.Textbox(
                            label="Class Name",
                            placeholder="Enter your class name",
                            value="",
                            elem_classes=["card-input"]
                        )
                
                run_btn = gr.Button(
                    "Run AI Coder",
                    variant="primary",
                    elem_id="run-btn"
                )
            
            # Right column - Example
            with gr.Column(scale=1):
                gr.Markdown("### Example", elem_classes=["section-title"]) 
                gr.Markdown("Click below to load an example:")
                example_btn = gr.Button("Load Trading Account Example", variant="secondary")
                
                # Example description
                gr.Markdown("""
                **Example will load:**
                - Trading account management system
                - Module: `accounts.py`
                - Class: `Account`
                """)
                gr.HTML("""
                <div class="note nowrap"><strong>Note:</strong> All code will be generated in Python 3.x</div>
                """)
        
        # Output section (hidden by default)
        with gr.Row():
            output = gr.Textbox(
                label="Output",
                interactive=False,
                lines=20,
                show_copy_button=True,
                elem_classes=["card"],
                visible=False,
                elem_id="output-box"
            )

        # Hidden URL fields (shown after task completion)
        with gr.Row():
            download_url_box = gr.Textbox(
                label="Download URL",
                interactive=False,
                visible=False,
                show_copy_button=True,
                elem_classes=["card"]
            )
            live_url_box = gr.Textbox(
                label="Live App URL",
                interactive=False,
                visible=False,
                show_copy_button=True,
                elem_classes=["card"]
            )

        # Button click handlers
        def load_example():
            return (
                EXAMPLE_CONFIG["requirements"],
                EXAMPLE_CONFIG["module_name"],
                EXAMPLE_CONFIG["class_name"]
            )

        example_btn.click(
            fn=load_example,
            outputs=[requirements, module_name, class_name]
        )

        # Generator function to manage state, progress, and output
        def run_crew_wrapper(requirements, module_name, class_name):
            progress = gr.Progress()
            # Immediately disable the button, show Output as progress area, and hide URL boxes
            yield (
                gr.update(value="[░░░░░░░░░░░░░░░░░░░░] 1% - AI is running hard", visible=True, label="Progress"),
                gr.update(value="", visible=False),  # clear Download URL box at start
                gr.update(value="", visible=False),  # clear Live URL box at start
                gr.update(interactive=False, value="Running…")
            )
            # Kick progress so overlay appears immediately
            progress(0.01, desc="Starting…")

            done = threading.Event()
            result_holder: dict[str, str | None] = {"output": None, "error": None}

            def worker():
                try:
                    result_holder["output"] = run_crew(requirements, module_name, class_name, progress)
                except Exception as e:  # pragma: no cover
                    result_holder["error"] = str(e)
                finally:
                    done.set()

            t = threading.Thread(target=worker, daemon=True)
            t.start()

            start = time.time()
            total = 300.0  # ~5 minutes
            last_pct = 1
            while not done.is_set():
                elapsed = time.time() - start
                pct = min(95, max(1, int((elapsed / total) * 95)))
                if pct != last_pct:
                    # Overlay progress and textual progress in output box
                    progress(pct / 100.0, desc=f"AI is running hard ({pct}%)")
                    last_pct = pct
                    bar_len = 24
                    filled = int(bar_len * pct / 100)
                    bar = ("█" * filled) + ("░" * (bar_len - filled))
                    yield (
                        gr.update(value=f"[{bar}] {pct}% - AI is running hard", visible=True, label="Progress"),
                        gr.update(visible=False),
                        gr.update(visible=False),
                        gr.update(interactive=False, value="Running…")
                    )
                time.sleep(1.0)

            # Worker is done
            t.join()
            progress(1.0, desc="Finalizing…")

            if result_holder["error"]:
                final_output = f"❌ Error: {result_holder['error']}"
                # Show error in output, keep URL boxes hidden, re-enable button
                yield (
                    gr.update(value=final_output, visible=True, label="Error", elem_classes=["card", "error"]),
                    gr.update(visible=False),
                    gr.update(visible=False),
                    gr.update(interactive=True, value="Run AI Coder")
                )
                return

            raw_output = result_holder["output"] or ""

            # If the output looks like a failure (but no exception was thrown), treat it as an error
            failure_like = bool(re.search(r"\b(failed|failure|error|exception|traceback)\b", raw_output, re.IGNORECASE))

            # Extract and validate URLs strictly (avoid putting random text into URL boxes)
            rough_urls = re.findall(r"https?://[^\s\"'<>]+", raw_output)
            cleaned_urls = [u.rstrip(".,);]") for u in rough_urls]
            valid_urls = [u for u in cleaned_urls if re.match(r"^https?://[A-Za-z0-9.-]+(?::\d+)?(?:/\S*)?$", u)]

            if failure_like or len(valid_urls) == 0:
                final_output = f"❌ Error: {raw_output.strip()}"
                yield (
                    gr.update(value=final_output, visible=True, label="Error", elem_classes=["card", "error"]),
                    gr.update(value="", visible=False),
                    gr.update(value="", visible=False),
                    gr.update(interactive=True, value="Run AI Coder")
                )
                return

            # Use up to two validated URLs
            download_url = valid_urls[0] if len(valid_urls) > 0 else ""
            live_url = valid_urls[1] if len(valid_urls) > 1 else ""

            # Success: hide output, show URLs, re-enable button
            yield (
                gr.update(value="", visible=False, label="Output"),
                gr.update(value=download_url, visible=bool(download_url)),
                gr.update(value=live_url, visible=bool(live_url)),
                gr.update(interactive=True, value="Run AI Coder")
            )

        # Click event: also pass the button as an output so we can disable/enable it
        run_btn.click(
            fn=run_crew_wrapper,
            inputs=[requirements, module_name, class_name],
            outputs=[output, download_url_box, live_url_box, run_btn],
            show_progress="full",
            api_name="run_crew"
        )

        # Modern UI styles
        demo.css = """
        html, body { background: #0b1220; color: #e2e8f0; font-family: Inter, Helvetica, Arial, sans-serif; overflow-x: hidden; }
        .gradio-container { max-width: 100% !important; width: 100% !important; margin: 0 auto !important; padding: 0 16px; }
        .header { max-width: 100%; margin: 24px auto 8px; padding: 12px 16px; text-align: center; }
        .brand { font-weight: 900; font-size: 36px; background: linear-gradient(90deg,#2563eb,#7c3aed); -webkit-background-clip: text; -webkit-text-fill-color: transparent; text-shadow: 0 2px 28px rgba(37,99,235,.45); }
        .subtitle { color: #cbd5e1; margin-top: 8px; font-weight: 600; }
        .section-title { color: #a5b4fc; }
        .card { border: 1px solid rgba(148,163,184,.2); border-radius: 12px; padding: 10px; background: rgba(2,6,23,.5); box-shadow: 0 4px 14px rgba(0,0,0,.25); }
        .card-input input, .card-input textarea { background: rgba(15,23,42,.6) !important; color: #e2e8f0 !important; border: 1px solid rgba(148,163,184,.25) !important; }
        #run-btn { background: linear-gradient(90deg,#2563eb,#7c3aed); color: white; padding: 12px 24px; font-size: 16px; border-radius: 10px; border: none; transition: transform .15s ease, opacity .2s ease; }
        #run-btn:hover:not(:disabled) { transform: translateY(-1px); }
        #run-btn:disabled { cursor: not-allowed !important; opacity: .7 !important; }
        /* Minimal .py suffix inside module textbox */
        #module-name { position: relative; }
        #module-name input, #module-name textarea { padding-right: 84px !important; }
        #module-name::after { content: ".py"; position: absolute; right: 12px; top: 50%; transform: translateY(-50%); background: #2563eb; color: #ffffff; font-weight: 700; padding: 4px 10px; border-radius: 8px; border: 1px solid rgba(255,255,255,.25); box-shadow: 0 2px 6px rgba(0,0,0,.25); pointer-events: none; z-index: 1; }
        /* Error output styling (only when .error class present) */
        #output-box.error textarea { background: #7f1d1d !important; border-color: #ef4444 !important; color: #fee2e2 !important; }
        #output-box.error label, #output-box.error .wrap .label { color: #ef4444 !important; }
        .nowrap { white-space: nowrap; }
        .note { color: #93c5fd; margin-top: 6px; }
        """
        
        # Add small JS snippet to maintain a tooltip reflecting disabled state
        gr.HTML("""
        <script>
        setInterval(() => {
          const b = document.getElementById('run-btn');
          if (b) {
            b.title = b.disabled ? 'Processing… This can take ~5-6 minutes' : 'Click to run the AI coder';
          }
        }, 1000);
        </script>
        """)
        
        # Ensure progress overlay renders reliably
        demo.queue()
        
    return demo

if __name__ == "__main__":
    demo = create_interface()
    demo.launch()