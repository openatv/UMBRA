"""Umbra gettext domain, usable on the receiver and by offline style tools."""

import gettext
from pathlib import Path

DOMAIN = "Umbra"
LOCALE = Path(__file__).resolve().parent / "locale"
_catalog = gettext.NullTranslations()


def locale_init():
    global _catalog
    try:
        from Components.Language import language
        languages = [language.getLanguage()]
    except ImportError:
        languages = None
    gettext.bindtextdomain(DOMAIN, str(LOCALE))
    _catalog = gettext.translation(DOMAIN, str(LOCALE), languages=languages, fallback=True)


def _(message):
    translated = _catalog.gettext(message)
    return gettext.gettext(message) if translated == message else translated


def ngettext(singular, plural, count):
    return _catalog.ngettext(singular, plural, count)


def N_(message):
    return message


locale_init()
try:
    from Components.Language import language
    language.addCallback(locale_init)
except ImportError:
    pass
