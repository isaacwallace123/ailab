from __future__ import annotations

import math
import re
from collections import Counter

_FIXED_PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:[A-Z0-9 ]+ )?PRIVATE KEY-----"),
    "openai-key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "github-token": re.compile(r"\bgh[opusr]_[A-Za-z0-9]{30,}\b"),
    "aws-access-key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}
_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(?:api[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|secret)\b"
    r"\s*[:=]\s*['\"]?([^'\"\s,;#}]+)"
)
_PLACEHOLDERS = {
    "changeme",
    "dummy",
    "example",
    "placeholder",
    "redacted",
    "replace",
    "sample",
    "test",
    "your_",
    "your-",
}


def _entropy(value: str) -> float:
    counts = Counter(value)
    length = len(value)
    return -sum((count / length) * math.log2(count / length) for count in counts.values())


def detect_secret(content: str) -> str | None:
    """Return a detector name without ever returning the suspected secret value."""
    for detector, pattern in _FIXED_PATTERNS.items():
        if pattern.search(content):
            return detector

    for match in _ASSIGNMENT_PATTERN.finditer(content):
        candidate = match.group(1).strip()
        lowered = candidate.lower()
        if any(marker in lowered for marker in _PLACEHOLDERS):
            continue
        if candidate.startswith(("${", "{{", "<")):
            continue
        if len(candidate) >= 20 and _entropy(candidate) >= 3.5:
            return "high-entropy-assignment"
    return None
