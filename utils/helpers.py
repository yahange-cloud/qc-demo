"""
Common utility functions for the QC Inspection System.
"""
import os
import json
import streamlit as st

I18N_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "i18n")


def load_i18n(lang="zh"):
    """Load i18n translation file."""
    path = os.path.join(I18N_DIR, f"{lang}.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def t(key, lang_dict=None, **kwargs):
    """Translate a key using the current language dict.

    Args:
        key: Translation key.
        lang_dict: Language dictionary. If None, uses session state.
        **kwargs: Format parameters for the translation string.
    """
    if lang_dict is None:
        lang_dict = st.session_state.get("i18n", {})
    text = lang_dict.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass
    return text


def init_session_state():
    """Initialize default session state values."""
    defaults = {
        "lang": "zh",
        "i18n": load_i18n("zh"),
        "data_loaded": False,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def switch_language(lang):
    """Switch the application language."""
    st.session_state["lang"] = lang
    st.session_state["i18n"] = load_i18n(lang)


def format_percentage(value, decimals=1):
    """Format a number as percentage string."""
    return f"{value:.{decimals}f}%"


def format_number(value):
    """Format a number with thousands separator."""
    if isinstance(value, float):
        return f"{value:,.1f}"
    return f"{value:,}"
