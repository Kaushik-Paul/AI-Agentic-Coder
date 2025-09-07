import sys
import os
import re
import subprocess
import time
import select
import json
import base64
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path

from crewai.tools import BaseTool
from pydantic import BaseModel, Field
from google.cloud import storage
from google.oauth2 import service_account

class PythonCodeRunToolInput(BaseModel):
    """Input schema for PythonCodeRunTool."""
    argument: str = Field(..., description="Description of the argument.")

class PythonCodeRunTool(BaseTool):
    name: str = "Python code runner"
    description: str = (
        "This tool runs the python code"
    )

    def upload_to_gcp(self):
        project_id = os.getenv("GCP_PROJECT_ID")
        bucket_name = os.getenv("GCP_BUCKET_NAME")
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        bucket_file_name = f"ai-agentic-coder-{timestamp}"
        gcp_service_key = os.getenv("GCP_SERVICE_KEY")
        local_file_name = bucket_file_name + ".zip"
        output_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../output"))

        # Create a zip file of the output directory
        shutil.make_archive(bucket_file_name, format="zip", root_dir=output_dir)

        service_key = json.loads(base64.b64decode(gcp_service_key).decode('utf-8'))
        creds = service_account.Credentials.from_service_account_info(service_key)

        # Initialize the GCP client
        client = storage.Client(project=project_id, credentials=creds)
        bucket = client.get_bucket(bucket_name)
        blob = bucket.blob(bucket_file_name)
        blob.upload_from_filename(local_file_name)

        # Delete the temporary zip file after uploading
        os.remove(local_file_name)

        # Get the signed URL for the uploaded file
        signed_url = blob.generate_signed_url(
            version="v4",
            method="GET",
            expiration=timedelta(minutes=10)
        )

        return signed_url

    def _run(self, argument: str) -> str:
        # First upload the code to GCP
        signed_url = self.upload_to_gcp()

        # Get the project root directory (src/ai_agentic_coder)
        # Resolve project root and module path
        project_root = Path(__file__).resolve().parents[2]  # /.../AI-Agentic-Coder
        module_path = "src.ai_agentic_coder.output.app"

        # Build the environment so the subprocess can find our package.
        # We need both the project root (src/) **and** the output directory
        # that contains accounts.py, so that `import accounts` succeeds.
        env = os.environ.copy()

        # Path to /src/ai_agentic_coder/output so `accounts.py` is importable
        output_dir = project_root / "ai_agentic_coder" / "output"

        # Compose PYTHONPATH: [output_dir]:[project_root]:<existing>
        pythonpath_parts = [str(output_dir), str(project_root)]
        if env.get("PYTHONPATH"):
            pythonpath_parts.append(env["PYTHONPATH"])
        env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)

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

        public_url = None
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

            # Prefer public URL
            m = re.search(r"Running on public URL:\s*(https?://\S+)", line)
            if m:
                public_url = m.group(1)
                break

            # Fallback: capture local URL
            m_local = re.search(r"http://127\.0\.0\.1:\d+", line)
            if m_local and not local_url:
                local_url = m_local.group(0)

        if not public_url and local_url:
            public_url = local_url

        if not public_url:
            public_url = "http://127.0.0.1:7860/"

        # Close our copy of stdout; the app keeps running detached.
        try:
            process.stdout.close()
        except Exception:
            pass

        return_urls = f"{signed_url}, {public_url}"

        return return_urls