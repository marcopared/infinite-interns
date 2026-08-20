"""Deterministic Stage 2 fake worker.

The worker mutates only its mounted workspace and emits an atomic worker envelope.
The trusted executor materializes the Git candidate after container exit so the
worker never needs shared Git metadata outside its task mount.
"""

import json
import sys
from pathlib import Path


def main() -> None:
    if len(sys.argv) != 4:
        raise SystemExit("usage: worker.py INPUT_JSON WORKSPACE ARTIFACT_DIR")

    input_path = Path(sys.argv[1])
    workspace = Path(sys.argv[2])
    artifact_dir = Path(sys.argv[3])
    payload = json.loads(input_path.read_text())
    attempt_id = str(payload["attempt_id"])
    if not attempt_id or "/" in attempt_id or "\\" in attempt_id or ".." in attempt_id:
        raise ValueError("attempt_id is not safe for a fixture output path")

    output = workspace / f"task-output-{attempt_id}.txt"
    output.write_text(f"completed {attempt_id}\n")

    result = {
        "attempt_id": attempt_id,
        "lease_epoch": payload["lease_epoch"],
        "status": "succeeded",
    }
    temporary = artifact_dir / "worker-result.json.tmp"
    temporary.write_text(json.dumps(result, sort_keys=True))
    temporary.replace(artifact_dir / "worker-result.json")


if __name__ == "__main__":
    main()
