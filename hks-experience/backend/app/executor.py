"""Runs the guided journey's real actions by invoking shim.sh, which itself
sources the EXISTING validator's scripts/lib.sh -- this module never
reimplements Kubernetes interaction logic, it only decides WHEN to call
which already-proven action_* function and parses the result.

Every action is single-step and user-triggered. There is deliberately no
"run everything" entrypoint here -- see config.EXECUTION_ENABLED and the
product brief's "DO NOT auto-run everything" requirement.

Result classification is never allowed to be empty. If shim.sh dies before
printing a PASS/FAIL/SKIP/BLOCKED marker (a bug, a crash, an unhandled
`exit`), the full raw output is still captured and surfaced -- an "ERROR"
with no diagnostic content is treated as its own bug, not an acceptable
terminal state.
"""
import re
import subprocess
from dataclasses import dataclass, field

from . import config

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@dataclass
class ActionResult:
    executed: bool
    result: str  # PASS | FAIL | SKIP | BLOCKED | NOT_EXECUTED | ERROR
    log_lines: list[str] = field(default_factory=list)
    raw_output: str = ""
    error_code: str | None = None
    error_message: str | None = None
    remediation: list[str] = field(default_factory=list)


def _parse(output: str, exit_code: int) -> ActionResult:
    clean = ANSI_RE.sub("", output)
    lines = [line for line in clean.splitlines() if line.strip()]

    blocked_line = next((line for line in lines if line.startswith("BLOCKED")), None)
    if blocked_line:
        code, message = _split_blocked(blocked_line)
        from . import errors

        structured = errors.build(code)
        return ActionResult(
            executed=True,
            result="BLOCKED",
            log_lines=lines,
            raw_output=output,
            error_code=structured.code,
            error_message=message or structured.message,
            remediation=structured.remediation,
        )
    if any(line.startswith("FAIL") for line in lines):
        return ActionResult(executed=True, result="FAIL", log_lines=lines, raw_output=output)
    if any(line.startswith("SKIP") for line in lines):
        return ActionResult(executed=True, result="SKIP", log_lines=lines, raw_output=output)
    if any(line.startswith("PASS") for line in lines):
        return ActionResult(executed=True, result="PASS", log_lines=lines, raw_output=output)

    # No recognized marker -- this used to silently become an empty-log
    # "ERROR". Never again: surface everything captured, plus the exit
    # code, so the failure is always debuggable from the UI alone.
    diagnostic = lines or [f"(no output captured; process exited with code {exit_code})"]
    from . import errors

    structured = errors.build("INTERNAL_ERROR", "\n".join(diagnostic))
    return ActionResult(
        executed=True,
        result="ERROR",
        log_lines=diagnostic,
        raw_output=output,
        error_code=structured.code,
        error_message=f"The action exited unexpectedly (code {exit_code}) without reporting a result.",
        remediation=structured.remediation,
    )


def _split_blocked(line: str) -> tuple[str, str]:
    """Parses 'BLOCKED  CODE: message' -> (CODE, message). Falls back to a
    generic connection-failure code if the line doesn't follow that shape
    (defensive -- still better than losing the line entirely)."""
    body = line[len("BLOCKED"):].strip()
    if ":" in body:
        code, _, message = body.partition(":")
        code = code.strip()
        from . import errors

        if code in errors.VALID_CODES:
            return code, message.strip()
    return "KUBERNETES_CONNECTION_FAILED", body


def run_action(action_name: str) -> ActionResult:
    if not config.EXECUTION_ENABLED:
        from . import errors

        structured = errors.build("HOSTED_MODE_NOT_EXECUTED")
        return ActionResult(
            executed=False,
            result="NOT_EXECUTED",
            log_lines=[structured.message],
            error_code=structured.code,
            error_message=structured.message,
            remediation=structured.remediation,
        )
    try:
        proc = subprocess.run(
            ["bash", config.SHIM_SCRIPT, f"action_{action_name}"],
            capture_output=True,
            text=True,
            timeout=config.ACTION_TIMEOUT_SECONDS,
            cwd=config.REPO_ROOT,
        )
    except subprocess.TimeoutExpired:
        from . import errors

        structured = errors.build("KUBERNETES_TIMEOUT", f"Action timed out after {config.ACTION_TIMEOUT_SECONDS}s")
        return ActionResult(
            executed=True,
            result="ERROR",
            log_lines=[f"Action timed out after {config.ACTION_TIMEOUT_SECONDS}s"],
            error_code=structured.code,
            error_message=structured.message,
            remediation=structured.remediation,
        )
    except FileNotFoundError as exc:
        from . import errors

        structured = errors.build("INTERNAL_ERROR", str(exc))
        return ActionResult(
            executed=False, result="ERROR", log_lines=[str(exc)],
            error_code=structured.code, error_message=structured.message, remediation=structured.remediation,
        )

    combined = proc.stdout + proc.stderr
    return _parse(combined, proc.returncode)
