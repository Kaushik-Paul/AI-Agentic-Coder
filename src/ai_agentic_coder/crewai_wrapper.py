#!/usr/bin/env python

import subprocess
import time
import threading
import re
import gradio as gr

from src.ai_agentic_coder.crew import EngineeringTeam

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
            progress(pct / 100.0, desc=f"AI is running hard")
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
