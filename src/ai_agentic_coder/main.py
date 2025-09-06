#!/usr/bin/env python
import warnings
import os
import subprocess
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
                
                run_btn = gr.Button("Run CrewAI", variant="primary")
            
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
                - Class: `TradingAccount`
                
                **Note:** All code will be generated in Python 3.x
                """)
        
        # Output section
        with gr.Row():
            output = gr.Textbox(
                label="Output",
                interactive=False,
                lines=20,
                show_copy_button=True
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
            # Create a progress instance
            progress = gr.Progress()
            progress(0.1, desc="Starting...")
            
            try:
                # Call the main function with progress updates
                result = run_crew(requirements, module_name, class_name, progress)
                progress(1.0, desc="Completed!")
                return result
            except Exception as e:
                progress(1.0, desc=f"Error: {str(e)}")
                raise
        
        # Store the original click handler
        click_event = run_btn.click(
            fn=run_crew_wrapper,
            inputs=[requirements, module_name, class_name],
            outputs=output,
            show_progress=True,
            api_name="run_crew"
        )
        
        # Add CSS for button state
        demo.css = """
        #run-btn:disabled {
            cursor: not-allowed !important;
            opacity: 0.7 !important;
        }
        """
        
        # Add JavaScript to handle button state using gr.HTML
        js_code = """
        <script>
        document.addEventListener('DOMContentLoaded', function() {
            const runBtn = document.querySelector('button[data-testid="Run CrewAI"]');
            if (runBtn) {
                runBtn.id = 'run-btn';
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