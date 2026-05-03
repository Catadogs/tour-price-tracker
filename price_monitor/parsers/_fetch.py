"""Rate-limited HTTP fetching with retry budgets.

All provider parsers use this module for outbound requests so per-provider
rate limits and exponential-backoff retry are applied uniformly.
"""

from __future__ import annotations

import logging
import time

import requests

_last_request: dict[str, float] = {}


def _rate_limit_wait(provider: str, cooldown_seconds: float) -> None:
    """Block until cooldown_seconds have elapsed since last request to provider."""
    last = _last_request.get(provider, 0)
    elapsed = time.monotonic() - last
    remaining = cooldown_seconds - elapsed
    if remaining > 0:
        logging.debug(
            "Rate limit: waiting %.1fs for provider %s", remaining, provider
        )
        time.sleep(remaining)


def fetch_with_retry(
    url: str,
    provider: str,
    rate_limit_seconds: float = 10,
    max_retries: int = 3,
    timeout: int = 30,
) -> str:
    """Fetch HTML from url with rate limiting and exponential-backoff retry.

    Args:
        url: The URL to fetch.
        provider: Provider name for rate-limit tracking (e.g. "bgoperator").
        rate_limit_seconds: Minimum seconds between requests to this provider.
        max_retries: Maximum retry attempts on transient failures.
        timeout: HTTP request timeout in seconds.

    Returns:
        Response body as text.

    Raises:
        requests.RequestException: After all retries are exhausted.
    """
    headers = {
        "User-Agent": "Mozilla/5.0 personal-bg-price-monitor",
        "Accept": "text/html,application/xhtml+xml",
    }

    last_exc: Exception | None = None

    for attempt in range(max_retries + 1):
        _rate_limit_wait(provider, rate_limit_seconds)

        try:
            response = requests.get(url, timeout=timeout, headers=headers)
            _last_request[provider] = time.monotonic()

            if response.status_code >= 500 or response.status_code == 429:
                response.raise_for_status()
            response.raise_for_status()
            return response.text

        except requests.RequestException as exc:
            last_exc = exc
            if attempt < max_retries:
                backoff = 2**attempt
                logging.warning(
                    "Fetch attempt %d/%d failed for %s (%s), retrying in %ds",
                    attempt + 1,
                    max_retries + 1,
                    provider,
                    exc,
                    backoff,
                )
                time.sleep(backoff)
            else:
                logging.exception(
                    "All %d fetch attempts failed for %s", max_retries + 1, provider
                )

    raise last_exc  # type: ignore[misc]
