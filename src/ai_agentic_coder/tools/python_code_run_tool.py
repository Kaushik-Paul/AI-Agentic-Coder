import sys
import os
import re
import subprocess
import time
import select
import json
import base64
import shutil
import signal
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from google.cloud import storage
from google.oauth2 import service_account


PREVIEW_PATH = os.getenv("AI_AGENTIC_CODER_PREVIEW_PATH", "/generated-app").rstrip("/") or "/generated-app"
PREVIEW_PORT = int(os.getenv("AI_AGENTIC_CODER_PREVIEW_PORT", "7861"))
RUN_RESULT_FILE = "latest_run_result.json"


def _output_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "output"


def _expiry_minutes() -> int:
    return int(os.getenv("AI_AGENTIC_CODER_PREVIEW_TTL_MINUTES", "30"))


def _base_url() -> str:
    explicit_base_url = os.getenv("AI_AGENTIC_CODER_BASE_URL")
    if explicit_base_url:
        return explicit_base_url.rstrip("/")

    space_host = os.getenv("SPACE_HOST")
    if space_host:
        if space_host.startswith(("http://", "https://")):
            return space_host.rstrip("/")
        return f"https://{space_host.rstrip('/')}"

    space_author = os.getenv("SPACE_AUTHOR_NAME")
    space_repo = os.getenv("SPACE_REPO_NAME")
    if space_author and space_repo:
        return f"https://{space_author}-{space_repo}.hf.space".lower()

    main_port = os.getenv("AI_AGENTIC_CODER_PORT") or os.getenv("GRADIO_SERVER_PORT") or "7860"
    return f"http://127.0.0.1:{main_port}"


def _preview_url() -> str:
    return f"{_base_url()}{PREVIEW_PATH}/"


def _terminate_later(process: subprocess.Popen, ttl_seconds: int) -> None:
    def terminate() -> None:
        if process.poll() is not None:
            return
        try:
            os.killpg(process.pid, signal.SIGTERM)
            process.wait(timeout=10)
        except Exception:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except Exception:
                pass

    timer = threading.Timer(ttl_seconds, terminate)
    timer.daemon = True
    timer.start()


def _wait_for_preview_server(process: subprocess.Popen, timeout_seconds: int = 60) -> bool:
    deadline = time.time() + timeout_seconds
    url = f"http://127.0.0.1:{PREVIEW_PORT}/"
    while time.time() < deadline:
        if process.poll() is not None:
            return False
        try:
            with urllib.request.urlopen(url, timeout=1):
                return True
        except (urllib.error.URLError, TimeoutError):
            time.sleep(0.5)
    return process.poll() is None

class PythonCodeRunToolInput(BaseModel):
    """Input schema for PythonCodeRunTool."""
    argument: str = Field(..., description="Description of the argument.")

class PythonCodeRunTool(BaseTool):
    name: str = "Python code runner"
    description: str = (
        "This tool runs the python code"
    )

    def upload_to_gcp(self) -> str:
        project_id = os.getenv("GCP_PROJECT_ID")
        bucket_name = os.getenv("GCP_BUCKET_NAME")
        if not project_id or not bucket_name:
            raise RuntimeError("GCP_PROJECT_ID and GCP_BUCKET_NAME are required.")

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        bucket_file_name = f"ai-agentic-coder-{timestamp}.zip"
        gcp_service_key = os.getenv("GCP_SERVICE_KEY")
        if not gcp_service_key:
            raise RuntimeError("GCP_SERVICE_KEY is required.")

        output_dir = _output_dir()
        archive_base = Path(tempfile.gettempdir()) / f"ai-agentic-coder-{timestamp}"
        archive_path = shutil.make_archive(str(archive_base), format="zip", root_dir=output_dir)

        service_key = json.loads(base64.b64decode(gcp_service_key).decode('utf-8'))
        creds = service_account.Credentials.from_service_account_info(service_key)

        # Initialize the GCP client
        client = storage.Client(project=project_id, credentials=creds)
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(bucket_file_name)
        blob.upload_from_filename(archive_path, content_type="application/zip")

        # Delete the temporary zip file after uploading
        os.remove(archive_path)

        # Get the signed URL for the uploaded file
        signed_url = blob.generate_signed_url(
            version="v4",
            method="GET",
            expiration=timedelta(minutes=_expiry_minutes()),
            response_disposition=f'attachment; filename="{bucket_file_name}"',
        )

        return signed_url

    def write_run_result(self, download_url: str, live_url: str) -> None:
        result_path = _output_dir() / RUN_RESULT_FILE
        result_path.write_text(
            json.dumps(
                {
                    "download_url": download_url,
                    "live_url": live_url,
                    "expires_in_minutes": _expiry_minutes(),
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    def _run(self, argument: str) -> str:
        # First upload the code to GCP
        signed_url = self.upload_to_gcp()

        project_src = Path(__file__).resolve().parents[2]
        module_path = "ai_agentic_coder.generated_app_runner"

        # Build the environment so the subprocess can find our package.
        # We need both the project root (src/) **and** the output directory
        # that contains accounts.py, so that `import accounts` succeeds.
        env = os.environ.copy()

        # Path to /src/ai_agentic_coder/output so `accounts.py` is importable
        output_dir = _output_dir()

        # Compose PYTHONPATH: [output_dir]:[project_src]:<existing>
        pythonpath_parts = [str(output_dir), str(project_src)]
        if env.get("PYTHONPATH"):
            pythonpath_parts.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
        env["GENERATED_GRADIO_APP_PATH"] = str(output_dir / "app.py")
        env["GENERATED_GRADIO_PORT"] = str(PREVIEW_PORT)
        env["GENERATED_GRADIO_ROOT_PATH"] = PREVIEW_PATH
        env["GRADIO_ROOT_PATH"] = PREVIEW_PATH
        env["GRADIO_SHARE"] = "False"

        # Construct the command to run the app as a module in unbuffered mode
        cmd = [sys.executable, "-u", "-m", module_path]

        # Ensure the child Python interpreter uses unbuffered stdout/stderr
        env["PYTHONUNBUFFERED"] = "1"

        print("Launching Gradio app... (this might take a few seconds)")

        # Detach the Gradio server so it keeps running even after CrewAI finishes.
        # `start_new_session=True` puts the child in its own process group so it
        # won't receive a SIGINT/SIGTERM when the parent exits.
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
            start_new_session=True,
        )

        public_url = _preview_url()
        local_url = None

        start_time = time.time()
        timeout = 60  # seconds

        # Non-blocking read loop with timeout
        while True:
            remaining = timeout - (time.time() - start_time)
            if remaining <= 0:
                break

            rlist, _, _ = select.select([process.stdout], [], [], remaining)
            if not rlist:
                break

            line = process.stdout.readline().rstrip()
            if line:
                print(line)

            # Fallback: capture local URL
            m_local = re.search(r"http://127\.0\.0\.1:\d+", line)
            if m_local and not local_url:
                local_url = m_local.group(0)
                break

        if not local_url and not _wait_for_preview_server(process):
            raise RuntimeError("Generated Gradio app exited before it became available.")

        # Close our copy of stdout; the app keeps running detached.
        try:
            process.stdout.close()
        except Exception:
            pass

        _terminate_later(process, _expiry_minutes() * 60)
        self.write_run_result(signed_url, public_url)
        return_urls = f"{signed_url}, {public_url}"

        return return_urls
