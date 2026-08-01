from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
from typing import Callable, TypeVar

from fastapi import HTTPException

from app.core.config import settings


T = TypeVar("T")

_EXECUTOR = ThreadPoolExecutor(max_workers=4)


def run_with_request_timeout(
    operation_name: str,
    func: Callable[[], T],
    *,
    timeout_seconds: int | None = None,
) -> T:
    effective_timeout = timeout_seconds if timeout_seconds is not None else settings.request_timeout_seconds
    future = _EXECUTOR.submit(func)
    try:
        return future.result(timeout=effective_timeout)
    except FuturesTimeoutError as error:
        raise HTTPException(
            status_code=504,
            detail=(
                f"{operation_name} exceeded the configured request timeout of "
                f"{effective_timeout} seconds."
            ),
        ) from error
