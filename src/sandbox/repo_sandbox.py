import os
import shutil
import stat
import subprocess
import tempfile
from pathlib import Path
import docker

class RepoSandbox:
    def __init__(self, repo_url: str):
        self.repo_url = repo_url
        # Create an isolated temporary directory on the host machine
        self.temp_dir = tempfile.mkdtemp(prefix="repo_sandbox_")
        self.workspace_path = Path(self.temp_dir)
        print(f"[Init] Created temporary directory at: {self.workspace_path}")

    def clone(self):
        """Clones the target git repository into the temporary workspace."""
        print(f"[Git] Cloning {self.repo_url}...")
        try:
            # We use git CLI directly so you see raw output and errors clearly
            result = subprocess.run(
                ["git", "clone", self.repo_url, str(self.workspace_path)],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"[Git] Clone successful.")
        except subprocess.CalledProcessError as e:
            print(f"[Git Error] Failed to clone:\n{e.stderr}")
            raise

    def run_in_docker(self, image: str, command: str) -> int:
        """
        Mounts the cloned repo into a Docker container and executes the command.
        """
        print(f"[Docker] Initializing Docker client...")
        client = docker.from_env()

        print(f"[Docker] Spinning up container with image: '{image}'")
        print(f"[Docker] Command to execute: '{command}'")

        # Mount our host temp directory to /workspace inside the container
        volumes = {
            str(self.workspace_path): {
                'bind': '/workspace',
                'mode': 'rw'  # Read/Write permissions
            }
        }

        try:
            # client.containers.run creates and starts a container
            container = client.containers.run(
                image=image,
                command=command,
                working_dir="/workspace",
                volumes=volumes,
                detach=True,   # Run in background so we can stream logs
                remove=True    # Automatically delete container when done
            )

            # Stream logs in real-time
            for log in container.logs(stream=True, follow=True):
                print(log.decode('utf-8', errors='replace'), end="")

            # Wait for execution to finish and grab the exit code
            result = container.wait()
            exit_code = result.get("StatusCode", 0)
            print(f"\n[Docker] Process finished with exit code: {exit_code}")
            return exit_code

        except docker.errors.ContainerError as e:
            print(f"[Docker Error] Container execution failed: {e}")
            return 1
        except docker.errors.ImageNotFound:
            print(f"[Docker Error] Image '{image}' not found locally or on Docker Hub.")
            return 1

    def cleanup(self):
        """Safely delete the temporary directory and all downloaded files."""
        print(f"[Cleanup] Removing {self.workspace_path}...")
        if self.workspace_path.exists():
            try:
                # Python 3.12+ uses 'onexc', older versions use 'onerror'
                import sys
                if sys.version_info >= (3, 12):
                    shutil.rmtree(self.workspace_path, onexc=lambda func, path, exc: (os.chmod(path, stat.S_IWRITE), func(path)))
                else:
                    shutil.rmtree(self.workspace_path, onerror=_remove_readonly)
            except Exception as e:
                print(f"[Cleanup Warning] Could not completely remove directory: {e}")
        print("[Cleanup] Done.")