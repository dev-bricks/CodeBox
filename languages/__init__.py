# CodeBox Language Providers
# Auto-Discovery, Dynamic Registration, Plugin-Support und Extension-Mapping

from __future__ import annotations

from typing import Callable, List, Optional, Union

from .base import LanguageProvider
from .declarative import DeclarativeLanguageProvider
from .python_lang import PythonProvider
from .javascript_lang import JavaScriptProvider
from .typescript_lang import TypeScriptProvider
from .cpp_lang import CppProvider
from .rust_lang import RustProvider
from .go_lang import GoProvider
from .java_lang import JavaProvider

__all__ = [
    "LanguageProvider",
    "DeclarativeLanguageProvider",
    "PythonProvider",
    "JavaScriptProvider",
    "TypeScriptProvider",
    "CppProvider",
    "RustProvider",
    "GoProvider",
    "JavaProvider",
    "get_provider_for_extension",
    "get_provider_by_name",
    "get_all_providers",
    "register_provider",
    "unregister_provider",
    "reset_providers",
    "is_provider_registered",
    "add_provider_listener",
    "remove_provider_listener",
]

_BUILTIN_FACTORIES = [
    PythonProvider,
    JavaScriptProvider,
    TypeScriptProvider,
    CppProvider,
    RustProvider,
    GoProvider,
    JavaProvider,
]

_PROVIDERS: List[LanguageProvider] = []
PROVIDERS: dict[str, LanguageProvider] = {}
PROVIDERS_BY_NAME: dict[str, LanguageProvider] = {}
_LISTENERS: List[Callable[[], None]] = []


def _notify_listeners() -> None:
    for listener in list(_LISTENERS):
        try:
            listener()
        except Exception:
            pass


def register_provider(provider: LanguageProvider, override: bool = True) -> None:
    """
    Registriert einen LanguageProvider dynamisch im System.

    :param provider: Eine Instanz von LanguageProvider oder einer Unterklasse.
    :param override: Wenn False und der Name oder eine Extension schon existiert, wird ein Fehler ausgelöst.
    """
    if not isinstance(provider, LanguageProvider):
        raise TypeError(f"Expected LanguageProvider instance, got {type(provider).__name__}")

    name = provider.get_name()
    if not name or not isinstance(name, str):
        raise ValueError("LanguageProvider must have a non-empty name string")

    extensions = provider.get_extensions()
    if not extensions:
        raise ValueError(f"LanguageProvider '{name}' must provide at least one file extension")

    if name in PROVIDERS_BY_NAME:
        if not override:
            raise ValueError(f"LanguageProvider '{name}' is already registered")
        old_provider = PROVIDERS_BY_NAME[name]
        if old_provider in _PROVIDERS:
            _PROVIDERS.remove(old_provider)
        for ext, p in list(PROVIDERS.items()):
            if p is old_provider:
                del PROVIDERS[ext]

    _PROVIDERS.append(provider)
    PROVIDERS_BY_NAME[name] = provider

    for ext in extensions:
        normalized_ext = ext.lower().lstrip(".")
        if normalized_ext:
            if not override and normalized_ext in PROVIDERS and PROVIDERS[normalized_ext].get_name() != name:
                raise ValueError(f"Extension '{normalized_ext}' is already claimed by '{PROVIDERS[normalized_ext].get_name()}'")
            PROVIDERS[normalized_ext] = provider

    _notify_listeners()


def unregister_provider(name_or_provider: Union[str, LanguageProvider]) -> Optional[LanguageProvider]:
    """
    Entfernt einen LanguageProvider anhand des Namens oder der Instanz aus der Registry.
    """
    if isinstance(name_or_provider, LanguageProvider):
        name = name_or_provider.get_name()
    else:
        name = str(name_or_provider)

    provider = PROVIDERS_BY_NAME.pop(name, None)
    if provider:
        if provider in _PROVIDERS:
            _PROVIDERS.remove(provider)
        for ext, p in list(PROVIDERS.items()):
            if p is provider or p.get_name() == name:
                del PROVIDERS[ext]
        _notify_listeners()
    return provider


def reset_providers() -> None:
    """
    Setzt alle registrierten Provider auf die Standard-Built-ins zurück.
    """
    _PROVIDERS.clear()
    PROVIDERS.clear()
    PROVIDERS_BY_NAME.clear()
    for factory in _BUILTIN_FACTORIES:
        p = factory()
        _PROVIDERS.append(p)
        PROVIDERS_BY_NAME[p.get_name()] = p
        for ext in p.get_extensions():
            normalized_ext = ext.lower().lstrip(".")
            if normalized_ext:
                PROVIDERS[normalized_ext] = p
    _notify_listeners()


def is_provider_registered(name: Optional[str]) -> bool:
    """Prüft, ob eine Sprache unter dem Namen registriert ist."""
    if not name or not isinstance(name, str):
        return False
    return name.strip() in PROVIDERS_BY_NAME


def add_provider_listener(callback: Callable[[], None]) -> None:
    """Registriert einen Listener, der bei Änderungen an den registrierten Sprachen aufgerufen wird."""
    if callback not in _LISTENERS:
        _LISTENERS.append(callback)


def remove_provider_listener(callback: Callable[[], None]) -> None:
    """Entfernt einen Listener."""
    if callback in _LISTENERS:
        _LISTENERS.remove(callback)


def get_provider_for_extension(ext: Optional[str]) -> Optional[LanguageProvider]:
    """Returns the LanguageProvider for a file extension (without dot)."""
    if not ext or not isinstance(ext, str):
        return None
    normalized = ext.strip().lower().lstrip(".")
    if not normalized:
        return None
    return PROVIDERS.get(normalized)


def get_provider_by_name(name: Optional[str]) -> Optional[LanguageProvider]:
    """Returns the LanguageProvider by language name."""
    if not name or not isinstance(name, str):
        return None
    return PROVIDERS_BY_NAME.get(name.strip())


def get_all_providers() -> List[LanguageProvider]:
    """Returns all registered providers."""
    return list(_PROVIDERS)


# Standard-Provider beim Import initialisieren
reset_providers()
