#!/usr/bin/env python
import gradio as gr

from src.ai_agentic_coder.crewai_wrapper import run_crew_wrapper

# Example configuration
EXAMPLE_CONFIG = {
    "requirements": (
        "A simple account management system for a trading simulation platform.\n"
        "The system should allow users to create an account, deposit funds, and withdraw funds.\n"
        "The system should allow users to record that they have bought or sold shares, providing a quantity.\n"
        "The system should calculate the total value of the user's portfolio, and the profit or loss from the initial deposit.\n"
        "The system should be able to report the holdings of the user at any point in time.\n"
        "The system should be able to report the profit or loss of the user at any point in time.\n"
        "The system should be able to list the transactions that the user has made over time.\n"
        "The system should prevent the user from withdrawing funds that would leave them with a negative balance, or\n"
        "from buying more shares than they can afford, or selling shares that they don't have.\n"
        "The system has access to a function get_share_price(symbol) which returns the current price of a share, and includes a test implementation that returns fixed prices for AAPL, TSLA, GOOGL.\n"
        "- Enforce trading rules"
    ),
    "module_name": "accounts",
    "class_name": "Account"
}

def create_interface():
    """Create and return the Gradio interface."""
    with gr.Blocks(title="AI Agentic Coder", theme=gr.themes.Soft()) as demo:
        gr.HTML("""
        <div class="header">
            <div class="brand">AI Agentic Coder</div>
            <div class="subtitle">Generate high-quality Python code with a coordinated Agentic AIs</div>
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
        .note { color: #2563eb; margin-top: 6px; font-weight: 400; }
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
