"""POS adapters - implementations for each POS provider."""

from typing import Any

from consult_schemas import POSProvider

from apps.web.pos.adapters.base import POSAdapter
from apps.web.pos.adapters.clover import CloverAdapter
from apps.web.pos.adapters.mock import MockPOSAdapter
from apps.web.pos.adapters.toast import ToastAdapter


def get_adapter(provider: POSProvider, **kwargs: Any) -> POSAdapter:
    """
    Get a POS adapter instance for the specified provider.

    This is the main entry point for obtaining POS adapters. Use this
    factory function rather than instantiating adapters directly.

    Args:
        provider: The POS provider to get an adapter for.
        **kwargs: Additional arguments passed to the adapter constructor.
            For CloverAdapter: sandbox=True to use sandbox environment.

    Returns:
        An adapter instance implementing the POSAdapter protocol.

    Raises:
        ValueError: If the provider is not supported.

    Example:
        adapter = get_adapter(POSProvider.TOAST)
        session = await adapter.authenticate(credentials)
        menus = await adapter.get_menus(session, location_id)

        # Clover with sandbox
        adapter = get_adapter(POSProvider.CLOVER, sandbox=True)
    """
    if provider == POSProvider.MOCK:
        return MockPOSAdapter()
    elif provider == POSProvider.TOAST:
        return ToastAdapter()
    elif provider == POSProvider.CLOVER:
        return CloverAdapter(**kwargs)
    else:
        supported = ", ".join(
            [POSProvider.MOCK.value, POSProvider.TOAST.value, POSProvider.CLOVER.value]
        )
        raise ValueError(
            f"Unsupported POS provider: {provider}. Supported: {supported}"
        )


__all__ = [
    "CloverAdapter",
    "MockPOSAdapter",
    "POSAdapter",
    "ToastAdapter",
    "get_adapter",
]
