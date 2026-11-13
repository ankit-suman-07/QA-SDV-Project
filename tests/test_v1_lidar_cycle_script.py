"""Exit-path checks for scripts/run-v1-lidar-cycle.sh with stub docker/curl.

No Docker stack is needed: the stubs report a running stack, a capture that
has seen vehicle-002 healthy, and record every provider request.
"""

import os
import stat
import subprocess
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "run-v1-lidar-cycle.sh"

FAKE_DOCKER = """#!/bin/sh
case "$1" in
  compose) printf 'mqtt\\nprovider-001\\nprovider-002\\napp-001\\napp-002\\n' ;;
  run) echo '{"topic": "sdv/vehicle-002/health", "event": {"vehicleId": "vehicle-002", "health": "HEALTHY"}}'
       sleep 3 ;;
esac
exit 0
"""

# Inject reaches the provider but the body is not what the script expects,
# so the script fails right after the inject.
FAKE_CURL = """#!/bin/sh
echo "$*" >> "$CALLS"
out=""
prev=""
for arg in "$@"; do
  [ "$prev" = "-o" ] && out="$arg"
  prev="$arg"
done
case "$*" in
  */health*) exit 0 ;;
esac
[ -n "$out" ] && echo '{"unexpected": true}' > "$out"
printf 200
"""


def _write_exe(path, text):
    path.write_text(text)
    path.chmod(path.stat().st_mode | stat.S_IEXEC)


def test_failed_inject_check_still_clears_scenario(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    _write_exe(bin_dir / "docker", FAKE_DOCKER)
    _write_exe(bin_dir / "curl", FAKE_CURL)
    calls = tmp_path / "calls.log"

    env = dict(
        os.environ,
        PATH=f"{bin_dir}:{os.environ['PATH']}",
        CALLS=str(calls),
        PUBLISH_INTERVAL_SECONDS="1",
    )
    result = subprocess.run(
        ["sh", str(SCRIPT)],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )

    assert result.returncode == 1, result.stderr
    requests = calls.read_text()
    assert "INJECT_SCENARIO" in requests
    assert "CLEAR_SCENARIO" in requests, (
        "inject may have been applied; the exit trap must clear it"
    )
