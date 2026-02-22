from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class ApiLikeResponse:
    """Resposta padronizada para simular um contrato de API."""

    ok: bool
    status_code: int
    message: str
    data: dict[str, Any] = field(default_factory=dict)
