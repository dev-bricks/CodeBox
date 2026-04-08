# CodeBox Language Providers
# Auto-Discovery und Extension-Mapping

from .base import LanguageProvider
from .python_lang import PythonProvider
from .javascript_lang import JavaScriptProvider
from .typescript_lang import TypeScriptProvider
from .cpp_lang import CppProvider
from .rust_lang import RustProvider
from .go_lang import GoProvider
from .java_lang import JavaProvider

__all__ = [
    "LanguageProvider", "PythonProvider", "JavaScriptProvider",
    "TypeScriptProvider", "CppProvider", "RustProvider",
    "GoProvider", "JavaProvider",
    "get_provider_for_extension", "get_provider_by_name", "get_all_providers",
]

# Provider-Instanzen
_PROVIDERS = [
    PythonProvider(),
    JavaScriptProvider(),
    TypeScriptProvider(),
    CppProvider(),
    RustProvider(),
    GoProvider(),
    JavaProvider(),
]

# Extension -> Provider Mapping
PROVIDERS = {}
for _p in _PROVIDERS:
    for _ext in _p.get_extensions():
        PROVIDERS[_ext] = _p

# Name -> Provider Mapping
PROVIDERS_BY_NAME = {_p.get_name(): _p for _p in _PROVIDERS}


def get_provider_for_extension(ext: str):
    """Returns the LanguageProvider for a file extension (without dot)."""
    return PROVIDERS.get(ext.lower().lstrip('.'))


def get_provider_by_name(name: str):
    """Returns the LanguageProvider by language name."""
    return PROVIDERS_BY_NAME.get(name)


def get_all_providers():
    """Returns all registered providers."""
    return list(_PROVIDERS)
