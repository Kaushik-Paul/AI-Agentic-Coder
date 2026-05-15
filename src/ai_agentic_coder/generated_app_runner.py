"""Run generated Gradio apps with controlled launch settings."""

from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path
from typing import Any

import gradio as gr


_LAUNCH_CALLED = False


def _preview_port() -> int:
    return int(os.getenv("GENERATED_GRADIO_PORT", "7861"))


def _root_path() -> str:
    root_path = os.getenv("GENERATED_GRADIO_ROOT_PATH", "/generated-app").strip()
    if not root_path.startswith("/"):
        root_path = f"/{root_path}"
    return root_path.rstrip("/") or "/generated-app"


def _patch_launch(cls: type[Any]) -> None:
    original_launch = cls.launch
    if getattr(original_launch, "_ai_agentic_coder_controlled", False):
        return

    def controlled_launch(self: Any, *args: Any, **kwargs: Any) -> Any:
        global _LAUNCH_CALLED
        _LAUNCH_CALLED = True
        kwargs["server_name"] = "127.0.0.1"
        kwargs["server_port"] = _preview_port()
        kwargs["share"] = False
        kwargs["root_path"] = _root_path()
        kwargs["prevent_thread_lock"] = False
        return original_launch(self, *args, **kwargs)

    controlled_launch._ai_agentic_coder_controlled = True  # type: ignore[attr-defined]
    cls.launch = controlled_launch  # type: ignore[method-assign]


def main() -> None:
    app_path = Path(os.environ["GENERATED_GRADIO_APP_PATH"]).resolve()
    output_dir = app_path.parent

    sys.path.insert(0, str(output_dir))
    os.chdir(output_dir)

    _patch_launch(gr.Blocks)
    _patch_launch(gr.Interface)

    globals_after_run = runpy.run_path(str(app_path), run_name="__main__")

    if _LAUNCH_CALLED:
        return

    for value in globals_after_run.values():
        if isinstance(value, gr.Blocks):
            value.launch(
                server_name="127.0.0.1",
                server_port=_preview_port(),
                share=False,
                root_path=_root_path(),
                prevent_thread_lock=False,
            )
            return

    raise RuntimeError("Generated app did not define or launch a Gradio Blocks/Interface app.")


if __name__ == "__main__":
    main()
