"""
Internationalization (i18n) module for the inventory system.

Lightweight translation system with no external dependencies.
Loads JSON dictionaries from utils/translations/ and exposes
a global `t(key)` function plus a LangSwitcher component for UI.
"""

from __future__ import annotations

import json
import locale
import sys
from pathlib import Path

from utils.logger import setup_logger

logger = setup_logger(__name__)

TRANSLATIONS_DIR = Path(__file__).parent / "translations"
DEFAULT_LANGUAGE = "es"
AVAILABLE_LANGUAGES = ("es", "en")


def detect_system_language() -> str:
    """Detect language from the operating system.

    Returns:
        Two-letter language code, defaulting to DEFAULT_LANGUAGE
        if the system language is not in AVAILABLE_LANGUAGES.
    """
    try:
        # Python 3.11+: getlocale() does not need explicit setlocale().
        # locale.getdefaultlocale() is deprecated in 3.13+ and will be removed.
        try:
            system_locale = locale.getlocale()[0] or ""
        except (AttributeError, ValueError):
            system_locale = ""
        if not system_locale:
            # Fall back to env vars
            for env in ("LC_ALL", "LC_MESSAGES", "LANG"):
                val = __import__("os").environ.get(env, "")
                if val:
                    system_locale = val
                    break
        lang = system_locale.split("_")[0].lower()
        if lang in AVAILABLE_LANGUAGES:
            return lang
    except Exception as e:
        logger.warning(f"Could not detect system language: {e}")
    return DEFAULT_LANGUAGE


class I18n:
    """Singleton translation manager.

    Holds the active locale and the loaded dictionaries.
    Call `set_locale(lang)` to switch at runtime; all `t(key)`
    calls after the switch will return the new translation.
    """

    _instance: I18n | None = None

    def __new__(cls) -> I18n:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self) -> None:
        if self._initialized:
            return
        self._translations: dict = {}
        self._locale: str = DEFAULT_LANGUAGE
        self._load_all()
        self._initialized = True

    def _load_all(self) -> None:
        """Load every available language dictionary from disk."""
        for lang in AVAILABLE_LANGUAGES:
            path = TRANSLATIONS_DIR / f"{lang}.json"
            if not path.exists():
                logger.warning(f"Translation file missing: {path}")
                self._translations[lang] = {}
                continue
            try:
                with open(path, encoding="utf-8") as f:
                    self._translations[lang] = json.load(f)
                logger.info(f"Loaded translations: {lang}")
            except (OSError, json.JSONDecodeError) as e:
                logger.error(f"Failed to load {lang}: {e}")
                self._translations[lang] = {}

    def set_locale(self, lang: str) -> bool:
        """Switch the active language. Returns True on success."""
        if lang not in AVAILABLE_LANGUAGES:
            logger.warning(f"Unknown locale: {lang}")
            return False
        self._locale = lang
        logger.info(f"Locale switched to: {lang}")
        return True

    def get_locale(self) -> str:
        return self._locale

    def t(self, key: str, **kwargs) -> str:
        """Translate a key with optional format-string interpolation.

        Falls back to:
        1. The key itself in the current locale if missing.
        2. The default locale if the current locale misses the key.
        3. The key as last resort (unless a `default` keyword is provided).
        """
        default = kwargs.pop("default", None)
        value = self._translations.get(self._locale, {}).get(key)
        if value is None and self._locale != DEFAULT_LANGUAGE:
            value = self._translations.get(DEFAULT_LANGUAGE, {}).get(key)
        if value is None:
            return default if default is not None else key
        try:
            return value.format(**kwargs) if kwargs else value
        except (KeyError, IndexError) as e:
            logger.warning(f"Bad format args for '{key}': {e}")
            return value


# Module-level singleton + shortcut function
_i18n = I18n()


def t(key: str, **kwargs) -> str:
    """Global translation shortcut."""
    return _i18n.t(key, **kwargs)


def set_locale(lang: str) -> bool:
    """Global locale switcher shortcut."""
    return _i18n.set_locale(lang)


def get_locale() -> str:
    """Global locale getter shortcut."""
    return _i18n.get_locale()


def available_languages() -> tuple:
    return AVAILABLE_LANGUAGES


def initialize_language(initial: str | None = None) -> str:
    """Initialize the active language.

    If `initial` is provided and valid, use it.
    Otherwise detect from the operating system.
    Returns the active language code.
    """
    if initial and initial in AVAILABLE_LANGUAGES:
        _i18n.set_locale(initial)
        return initial
    detected = detect_system_language()
    _i18n.set_locale(detected)
    return detected


if __name__ == "__main__":
    # Quick smoke test: `python -m utils.i18n`
    initialize_language()
    print(f"locale={get_locale()}")
    print(f"test.login.title={t('login.title')}")
    set_locale("en")
    print(f"locale={get_locale()}")
    print(f"test.login.title={t('login.title')}")
    sys.exit(0)
