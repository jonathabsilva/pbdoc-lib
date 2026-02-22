"""pbdoc-lib: automação reutilizável do PBDoc via Selenium headless."""

from .config import PBDocConfig, PBDocSelectors
from .exceptions import LoginError, PBDocAutomationError
from .models import ApiLikeResponse

__all__ = [
    "ApiLikeResponse",
    "LoginError",
    "PBDocAutomationError",
    "PBDocClient",
    "PBDocConfig",
    "PBDocSelectors",
]


def __getattr__(name: str):
    if name == "PBDocClient":
        from .client import PBDocClient

        return PBDocClient
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
