"""POS adapters - implementations for each POS provider."""

from consult_schemas import POSProvider

from apps.web.pos.adapters.base import POSAdapter
from apps.web.pos.adapters.mock import MockPOSAdapter
from apps.web.pos.adapters.toast import ToastAdapter


def get_adapter(provider: POSProvider) -> POSAdapter:
    """
    Get a POS adapter instance for the specified provider.

    This is the main entry point for obtaining POS adapters. Use this
    factory function rather than instantiating adapters directly.

    Args:
        provider: The POS provider to get an adapter for.

    Returns:
        An adapter instance implementing the POSAdapter protocol.

    Raises:
        ValueError: If the provider is not supported.

    Example:
        adapter = get_adapter(POSProvider.TOAST)
        session = await adapter.authenticate(credentials)
        menus = await adapter.get_menus(session, location_id)
    """
    if provider == POSProvider.MOCK:
        return MockPOSAdapter()
    elif provider == POSProvider.TOAST:
        return ToastAdapter()
    else:
        supported = ", ".join([POSProvider.MOCK.value, POSProvider.TOAST.value])
        raise ValueError(
            f"Unsupported POS provider: {provider}. Supported: {supported}"
        )


__all__ = [
    "MockPOSAdapter",
    "POSAdapter",
    "ToastAdapter",
    "get_adapter",
]
