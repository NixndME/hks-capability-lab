"""Structured error classification for Kubernetes connectivity/API problems.
Every user-facing failure in this app should resolve to one of these codes
with a safe, credential-free message and concrete remediation -- never a
bare "ERROR" with no context.
"""
from dataclasses import dataclass, field

VALID_CODES = {
    "KUBECONFIG_NOT_FOUND",
    "KUBECONFIG_INVALID",
    "KUBERNETES_CONNECTION_FAILED",
    "KUBERNETES_AUTH_FAILED",
    "KUBERNETES_FORBIDDEN",
    "KUBERNETES_TIMEOUT",
    "KUBERNETES_API_ERROR",
    "INTERNAL_ERROR",
    "HOSTED_MODE_NOT_EXECUTED",
}


@dataclass
class StructuredError:
    code: str
    message: str
    remediation: list[str] = field(default_factory=list)
    details: str | None = None  # safe, sanitized diagnostic text only

    def to_dict(self) -> dict:
        return {
            "code": self.code,
            "message": self.message,
            "remediation": self.remediation,
            "details": self.details,
        }


REMEDIATION = {
    "KUBECONFIG_NOT_FOUND": [
        "No kubeconfig was found inside this container.",
        "Start the container with your kubeconfig mounted read-only:",
        "podman run --rm -p 8080:8080 -v ~/.kube:/home/hksexp/.kube:ro "
        "docker.io/nixndme/hks-capability-lab-experience:latest",
    ],
    "KUBECONFIG_INVALID": [
        "The mounted kubeconfig could not be parsed.",
        "Verify it's a valid kubeconfig file (YAML) and the mount path is correct.",
    ],
    "KUBERNETES_CONNECTION_FAILED": [
        "The Kubernetes API server could not be reached.",
        "Check the cluster is up, and that this container can reach it (VPN, network routing, firewall).",
    ],
    "KUBERNETES_AUTH_FAILED": [
        "The credentials in your kubeconfig were rejected by the API server.",
        "Verify your kubeconfig's token/certificate hasn't expired.",
    ],
    "KUBERNETES_FORBIDDEN": [
        "Your Kubernetes identity reached the API server but isn't authorized for this action.",
        "Ask a cluster admin for the required RBAC permissions, or switch kubeconfig context.",
    ],
    "KUBERNETES_TIMEOUT": [
        "The request to the Kubernetes API server timed out.",
        "The cluster may be slow, overloaded, or unreachable from this network.",
    ],
    "KUBERNETES_API_ERROR": [
        "The Kubernetes API server returned an unexpected error.",
        "Check the technical details below, or the cluster's own status.",
    ],
    "INTERNAL_ERROR": [
        "Something went wrong inside this application, not on your cluster.",
        "Check the container logs (podman logs <container>) for a full traceback.",
    ],
    "HOSTED_MODE_NOT_EXECUTED": [
        "Hosted mode never connects to a Kubernetes cluster.",
        "Run this locally with Podman to execute real actions against your own cluster.",
    ],
}

MESSAGES = {
    "KUBECONFIG_NOT_FOUND": "No Kubernetes configuration is available.",
    "KUBECONFIG_INVALID": "The Kubernetes configuration could not be parsed.",
    "KUBERNETES_CONNECTION_FAILED": "Unable to connect to the configured Kubernetes cluster.",
    "KUBERNETES_AUTH_FAILED": "Kubernetes rejected the provided credentials.",
    "KUBERNETES_FORBIDDEN": "Kubernetes access denied for this operation.",
    "KUBERNETES_TIMEOUT": "The Kubernetes API server did not respond in time.",
    "KUBERNETES_API_ERROR": "The Kubernetes API returned an error.",
    "INTERNAL_ERROR": "An internal error occurred.",
    "HOSTED_MODE_NOT_EXECUTED": "This action does not run in hosted mode.",
}


def build(code: str, details: str | None = None) -> StructuredError:
    if code not in VALID_CODES:
        code = "INTERNAL_ERROR"
    return StructuredError(
        code=code,
        message=MESSAGES[code],
        remediation=REMEDIATION[code],
        details=_sanitize(details) if details else None,
    )


_SENSITIVE_MARKERS = ("token", "bearer", "certificate", "private key", "client-key", "password", "secret")


def _sanitize(text: str) -> str:
    """Best-effort scrub of anything that looks like it could be credential
    material, so raw exception text is safe to show in the UI. Truncated to
    keep the UI's collapsible technical-details panel readable."""
    lowered = text.lower()
    if any(marker in lowered for marker in _SENSITIVE_MARKERS):
        return "(diagnostic text withheld -- may contain credential material; see container logs)"
    return text[:500]


def classify_exception(exc: Exception) -> StructuredError:
    """Maps a raised exception (from the kubernetes python client or config
    loader) to a structured, credential-free error. Never returns a bare
    'ERROR' -- always a specific code with remediation."""
    type_name = type(exc).__name__
    text = str(exc)
    lowered = text.lower()

    if type_name == "ConfigException" or "config" in type_name.lower():
        if "no configuration found" in lowered or "no such file" in lowered or "not found" in lowered:
            return build("KUBECONFIG_NOT_FOUND", text)
        return build("KUBECONFIG_INVALID", text)

    status = getattr(exc, "status", None)
    if status == 401:
        return build("KUBERNETES_AUTH_FAILED", text)
    if status == 403:
        return build("KUBERNETES_FORBIDDEN", text)
    if status is not None:
        return build("KUBERNETES_API_ERROR", text)

    if "timed out" in lowered or "timeout" in lowered:
        return build("KUBERNETES_TIMEOUT", text)
    if any(
        marker in lowered
        for marker in ("connection refused", "max retries exceeded", "failed to establish a new connection", "name or service not known", "no route to host")
    ):
        return build("KUBERNETES_CONNECTION_FAILED", text)

    return build("INTERNAL_ERROR", text)
