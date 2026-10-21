"""Shared UI helpers: stylesheet loading and small HTML components.

All user-provided text must go through esc() before being placed in HTML.
HTML strings are kept on a single line on purpose: Streamlit's markdown
parser treats indented lines as code blocks.
"""
import html
import os
from typing import List, Optional, Sequence, Tuple

import streamlit as st

CSS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "style.css")

STATUS_LABELS = {
    "completed": ("Completed", "cl-badge--completed"),
    "eligible": ("Eligible", "cl-badge--eligible"),
    "blocked": ("Blocked", "cl-badge--blocked"),
}


def esc(value) -> str:
    return html.escape(str(value))


@st.cache_data(show_spinner=False)
def _read_css(mtime: float) -> str:
    with open(CSS_PATH, encoding="utf-8") as f:
        return f.read()


def inject_css() -> None:
    """Inject the single stylesheet. The file read is cached; the <style> tag
    is re-emitted on each rerun because Streamlit rebuilds the page."""
    try:
        mtime = os.path.getmtime(CSS_PATH)
    except OSError:
        return
    st.markdown(f"<style>{_read_css(mtime)}</style>", unsafe_allow_html=True)


def page_header(eyebrow: str, title: str, subtitle: str) -> None:
    st.markdown(
        f'<div class="cl-header"><div class="cl-eyebrow">{esc(eyebrow)}</div>'
        f'<h1 class="cl-title">{esc(title)}</h1><p class="cl-subtitle">{esc(subtitle)}</p></div>',
        unsafe_allow_html=True,
    )


def section_title(text: str, hint: Optional[str] = None) -> None:
    hint_html = f"<p>{esc(hint)}</p>" if hint else ""
    st.markdown(f'<div class="cl-section"><h2>{esc(text)}</h2>{hint_html}</div>', unsafe_allow_html=True)


def badge(status: str, text: Optional[str] = None) -> str:
    label, css = STATUS_LABELS[status]
    return f'<span class="cl-badge {css}">{esc(text or label)}</span>'


def course_card(code: str, name: str, meta: str, status: Optional[str] = None) -> str:
    b = badge(status) if status else ""
    return (
        f'<div class="cl-course"><div class="cl-course-top"><span class="cl-code">{esc(code)}</span>{b}</div>'
        f'<div class="cl-course-name">{esc(name)}</div><div class="cl-course-meta">{esc(meta)}</div></div>'
    )


def empty_state(title: str, body: str) -> None:
    st.markdown(
        f'<div class="cl-empty"><strong>{esc(title)}</strong><span>{esc(body)}</span></div>',
        unsafe_allow_html=True,
    )


def util_bar(used: int, cap: int) -> str:
    pct = min(100, round(100 * used / cap)) if cap else 0
    return (
        f'<div class="cl-bar" role="progressbar" aria-label="Credits used" aria-valuenow="{pct}" '
        f'aria-valuemin="0" aria-valuemax="100"><div class="cl-bar-fill" style="width:{pct}%"></div></div>'
    )


def legend(items: Sequence[Tuple[str, str]]) -> None:
    spans = "".join(f'<span><i style="background:{color}"></i>{esc(label)}</span>' for label, color in items)
    st.markdown(f'<div class="cl-legend">{spans}</div>', unsafe_allow_html=True)


def html_table(headers: List[str], rows: List[List[str]], aligns: Optional[List[str]] = None,
               footer: Optional[List[str]] = None) -> str:
    """Build a table. Cells in `rows`/`footer` are trusted HTML: escape user text with esc()."""
    aligns = aligns or ["left"] * len(headers)
    head = "".join(f'<th style="text-align:{a}">{esc(h)}</th>' for h, a in zip(headers, aligns))
    body = "".join(
        "<tr>" + "".join(f'<td style="text-align:{a}">{cell}</td>' for cell, a in zip(r, aligns)) + "</tr>"
        for r in rows
    )
    foot = ""
    if footer:
        foot = "<tfoot><tr>" + "".join(f'<td style="text-align:{a}">{cell}</td>' for cell, a in zip(footer, aligns)) + "</tr></tfoot>"
    return f'<div class="cl-table-wrap"><table class="cl-table"><thead><tr>{head}</tr></thead><tbody>{body}</tbody>{foot}</table></div>'


def set_flash(kind: str, message: str) -> None:
    st.session_state["flash"] = (kind, message)


def show_flash() -> None:
    flash = st.session_state.pop("flash", None)
    if flash:
        kind, message = flash
        getattr(st, kind, st.info)(message)