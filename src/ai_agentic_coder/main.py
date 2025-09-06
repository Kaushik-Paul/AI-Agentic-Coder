#!/usr/bin/env python
import warnings
import os
import subprocess
import time
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
    "requirements": """A simple account management system for a trading simulation platform.
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
    """Run the crew with the given inputs and return the result."""
    try:
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
        
        progress(0.3, desc="Initializing crew...")
        crew = EngineeringTeam().crew()
        
        progress(0.6, desc="Running crew...")
        result = crew.kickoff(inputs=inputs)
        
        return f"✅ Task completed!\n\n{result.raw if hasattr(result, 'raw') else result}"
        
    except Exception as e:
        return f"❌ Error: {str(e)}"

def create_interface():
    """Create and return the Gradio interface."""
    with gr.Blocks(title="AI Agentic Coder") as demo:
        gr.Markdown("# AI Agentic Coder")
        
        with gr.Row():
            # Left column - Inputs
            with gr.Column(scale=2):
                requirements = gr.Textbox(
                    label="Requirements",
                    placeholder="Describe what you want to build...",
                    lines=15,
                    max_lines=20,
                )
                
                with gr.Row():
                    with gr.Column(scale=3):
                        module_name = gr.Textbox(
                            label="Module Name",
                            placeholder="Enter your module name",
                            value=""
                        )
                    with gr.Column(scale=1, min_width=40):
                        gr.Markdown(".py", show_label=False)
                    
                    class_name = gr.Textbox(
                        label="Class Name",
                        placeholder="Enter your class name",
                        value=""
                    )
                
                run_btn = gr.Button(
                    "Run AI Coder",
                    variant="primary",
                    elem_id="run-btn"
                )
            
            # Right column - Example
            with gr.Column(scale=1):
                gr.Markdown("### Example")
                gr.Markdown("Click below to load an example:")
                example_btn = gr.Button("Load Trading Account Example", variant="secondary")
                
                # Example description
                gr.Markdown("""
                **Example will load:**
                - Trading account management system
                - Module: `accounts.py`
                - Class: `Account`
                
                **Note:** All code will be generated in Python 3.x
                """)
        
        # Output section
        with gr.Row():
            output = gr.Textbox(
                label="Output",
                interactive=False,
                lines=20,
                show_copy_button=True,
                elem_classes=["card"]
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
        
        # Function to handle run button state
        def run_crew_wrapper(requirements, module_name, class_name):
            progress = gr.Progress()
            progress(0.01, desc="Starting...")
            
            # Simulate gradual progress up to 95% over ~5 minutes while crew runs
            total_secs = 300
            step_secs = total_secs / 95
            
            def simulate_progress():
                for pct in range(1, 96):
                    time.sleep(step_secs)
                    progress(pct / 100, desc=f"Processing... {pct}%")
            
            # Run progress simulation in parallel thread
            import threading
            sim_thread = threading.Thread(target=simulate_progress, daemon=True)
            sim_thread.start()
            
            # Run the heavy task
            raw_output = run_crew(requirements, module_name, class_name, progress)
            
            # Ensure simulation finishes
            sim_thread.join(0)
            
            # Parse URLs from raw_output (expecting after "Task completed!\n\n")
            summary_lines = raw_output.split("\n\n", 1)
            summary_text = summary_lines[0]
            urls_text = summary_lines[1] if len(summary_lines) > 1 else ""
            links = [u.strip() for u in urls_text.split(',') if u.strip()]
            download_url = links[0] if links else ""
            live_url = links[1] if len(links) > 1 else ""
            
            progress(1.0, desc="Completed!")
            
            # Show URL boxes now
            return (
                raw_output,
                gr.Textbox.update(value=download_url, visible=True),
                gr.Textbox.update(value=live_url, visible=True)
            )
        
        click_event = run_btn.click(
            fn=run_crew_wrapper,
            inputs=[requirements, module_name, class_name],
            outputs=[output, download_url_box, live_url_box],
            show_progress=True,
            api_name="run_crew"
        )
        
        demo.css = """
        body{background:#f4f6f9;font-family:Inter,Helvetica,Arial,sans-serif;}
        .card{border:1px solid #e0e0e0;border-radius:8px;padding:10px;background:white;box-shadow:0 2px 5px rgba(0,0,0,0.05);}        
        #run-btn{background:#0066ff;color:white;padding:12px 24px;font-size:16px;border-radius:6px;border:none;transition:background .3s ease;}        
        #run-btn:disabled{cursor:not-allowed!important;opacity:.6!important;background:#6c89c9!important;}        
        #run-btn:hover:not(:disabled){background:#0056d1;}
        """
        
        # Add JavaScript to handle button state using gr.HTML
        js_code = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const runBtn = document.getElementById('run-btn');
            if (runBtn) {
                runBtn.addEventListener('click', function() {
                    this.disabled = true;
                    this.style.cursor = 'not-allowed';
                    this.innerHTML = 'Running...';
                    
                    // Re-enable the button when progress is complete
                    const checkCompletion = setInterval(() => {
                        if (!document.querySelector('.progress-bar')) {
                            this.disabled = false;
                            this.style.cursor = 'pointer';
                            this.innerHTML = 'Run CrewAI';
                            clearInterval(checkCompletion);
                        }
                    }, 1000);
                });
            }
        });
        </script>
        """
        
        # Add the JavaScript to the interface
        html = gr.HTML(js_code)
        
    return demo

if __name__ == "__main__":
    demo = create_interface()
    demo.launch()