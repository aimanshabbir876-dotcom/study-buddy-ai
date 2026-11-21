# app.py
# Study Buddy AI - the Streamlit interface.
# Run with:  streamlit run app.py

import os
import re
import uuid
from datetime import date

import streamlit as st

import database as db
from ai_engine import MAX_DOC_CHARS, get_ai_response
from file_reader import ALLOWED_TYPES, read_uploaded_file
from prompts import LANGUAGES, LEVELS, MODE_INFO, MODES

# ---------- Page settings ----------
st.set_page_config(
    page_title="Study Buddy AI",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

USER_AVATAR = "🧑‍🎓"
BOT_AVATAR = "📚"

# Cards shown on the home page: (title, icon, mode, description, color)
QUICK_ACTIONS = [
    ("Explain a Topic", "💡", "Explain Simply", "Hard topics explained in easy words.", "#4338CA"),
    ("Summarize Notes", "📚", "Summarizer", "Paste text or upload a file to get key points.", "#0E9F8E"),
    ("Generate Quiz", "🧠", "Quiz Generator", "Practice with MCQs and short questions.", "#D97706"),
    ("Ask a Question", "❓", "Ask a Question", "Get a clear answer to any study question.", "#2563EB"),
    ("Make Notes", "📝", "Notes Generator", "Short or detailed notes on any topic.", "#DB2777"),
    ("Exam Preparation", "🎯", "Exam Preparation", "Revision plan, likely questions and tips.", "#7C3AED"),
]

STUDY_TIPS = [
    "Study in short sessions of 25 minutes, then take a 5-minute break.",
    "Explain a topic out loud in your own words. If you get stuck, that is what to revise.",
    "Test yourself with a quiz instead of only re-reading your notes.",
    "Start with the hardest subject when your mind is fresh.",
    "Sleep well before an exam. Your brain saves what you learned while you sleep.",
    "Write a short summary after each lesson. It takes 5 minutes and saves hours later.",
    "Revise a topic again after 1 day, 1 week and 1 month to remember it for longer.",
    "Put your phone in another room while you study.",
]

# ---------- Colors for light and dark mode ----------
THEMES = {
    "light": {
        "bg": "#F4F6FB", "card": "#FFFFFF", "sidebar": "#EAEDFA", "text": "#1C2147",
        "muted": "#5B6285", "border": "#DDE2F3", "primary": "#4338CA", "soft": "#E7E6FB",
    },
    "dark": {
        "bg": "#0E1226", "card": "#181D3A", "sidebar": "#0A0D1D", "text": "#E8EAFB",
        "muted": "#9AA2CC", "border": "#2A3060", "primary": "#8B84FF", "soft": "#262B55",
    },
}

BASE_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700;800&display=swap');

html, body, .stApp, button, input, textarea { font-family: 'Nunito', sans-serif; }
.stApp { background: var(--bg); }
[data-testid="stHeader"] { background: transparent; }
[data-testid="stSidebar"] { background: var(--sidebar); border-right: 1px solid var(--border); }
.block-container { max-width: 1000px; padding-top: 2rem; }

/* Sidebar brand */
.brand { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.brand-name { font-size: 1.25rem; font-weight: 800; color: var(--text); }
.section-label { font-size: 0.85rem; font-weight: 700; color: var(--muted); margin: 14px 0 4px 2px; }

/* Buttons (all buttons stretch to the width of their column) */
.stButton, [data-testid="stDownloadButton"], [data-testid="stPopover"] { width: 100% !important; }
.stButton > button, [data-testid="stDownloadButton"] button, [data-testid="stPopover"] button {
    width: 100%; border-radius: 12px; font-weight: 700;
}
[data-testid="stSidebar"] .stButton > button { padding: 0.35rem 0.6rem; }
[class*="st-key-open_"] button { justify-content: flex-start; text-align: left; }

/* Chat bubbles */
[data-testid="stChatMessage"] {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 16px; padding: 14px 16px; margin-bottom: 10px;
}

/* Home page */
.hero {
    display: flex; align-items: center; gap: 22px;
    background: linear-gradient(135deg, #3730A3 0%, #4F46E5 100%);
    border-radius: 22px; padding: 30px 32px; margin-bottom: 22px;
}
.hero-logo { flex-shrink: 0; }
.hero-title { font-size: 2rem; font-weight: 800; line-height: 1.2; margin-bottom: 8px; }
.hero-text { font-size: 1.02rem; line-height: 1.55; max-width: 620px; }

.stat {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 16px; padding: 14px 18px; margin-bottom: 8px;
}
.stat-num { font-size: 1.6rem; font-weight: 800; color: var(--primary); line-height: 1.1; }
.stat-label { font-size: 0.9rem; color: var(--muted); }

.page-heading { font-size: 1.3rem; font-weight: 800; color: var(--text); margin: 22px 0 10px; }

.action-card {
    background: var(--card); border: 1px solid var(--border);
    border-radius: 18px; padding: 18px; margin-bottom: 8px; min-height: 150px;
}
.action-icon {
    width: 46px; height: 46px; border-radius: 14px; font-size: 1.5rem;
    display: flex; align-items: center; justify-content: center; margin-bottom: 10px;
}
.action-title { font-size: 1.08rem; font-weight: 800; color: var(--text); margin-bottom: 4px; }
.action-desc { font-size: 0.92rem; color: var(--muted); line-height: 1.45; }

.tip {
    background: var(--card); border: 1px solid var(--border); border-left: 6px solid #F5B301;
    border-radius: 14px; padding: 14px 18px; color: var(--text);
}
.tip-title { font-weight: 800; margin-bottom: 4px; }

.chat-meta { color: var(--muted); font-size: 0.9rem; margin-top: -8px; }
"""

# Extra rules that are only used when dark mode is switched on
DARK_CSS = """
.stApp, .stApp [data-testid="stMarkdownContainer"] *, .stApp label,
.stApp [data-testid="stWidgetLabel"] *, .stApp [data-testid="stCaptionContainer"] *,
.stApp h1, .stApp h2, .stApp h3, .stApp h4, .stApp summary, .stApp summary * {
    color: var(--text) !important;
}
[data-testid="stBottom"] > div, [data-testid="stBottomBlockContainer"] { background: var(--bg) !important; }
[data-testid="stChatInput"], [data-testid="stChatInput"] > div, [data-testid="stChatInput"] textarea {
    background: var(--card) !important; color: var(--text) !important; border-color: var(--border) !important;
}
.stApp input, .stApp textarea { background: var(--card) !important; color: var(--text) !important; }
div[data-baseweb="select"] > div, div[data-baseweb="input"] > div {
    background: var(--card) !important; border-color: var(--border) !important;
}
div[data-baseweb="select"] *, div[data-baseweb="input"] * { color: var(--text) !important; }
div[data-baseweb="popover"] > div, div[data-baseweb="popover"] ul, div[data-baseweb="menu"],
ul[role="listbox"] li, [data-testid="stPopoverBody"] {
    background: var(--card) !important; color: var(--text) !important;
}
[data-testid="stExpander"] { background: var(--card) !important; border-color: var(--border) !important; }
[data-testid="stFileUploaderDropzone"] { background: var(--soft) !important; }
[data-testid="stFileUploaderDropzone"] * { color: var(--text) !important; }
.stButton > button, [data-testid="stDownloadButton"] button, [data-testid="stPopover"] button {
    background: var(--card) !important; border: 1px solid var(--border) !important;
}
.stButton > button *, [data-testid="stDownloadButton"] button *, [data-testid="stPopover"] button * {
    color: var(--text) !important;
}
.stButton > button[kind="primary"], [data-testid="stBaseButton-primary"] {
    background: var(--primary) !important; border-color: var(--primary) !important;
}
.stButton > button[kind="primary"] *, [data-testid="stBaseButton-primary"] * { color: #0E1226 !important; }
"""

# The hero card always uses white text (kept last so it wins over other rules)
# Design fixes. Kept last so they win over other rules.
HERO_CSS = """
/* Buttons fill the width of their column */
[data-testid="stElementContainer"]:has(.stButton),
[data-testid="stElementContainer"]:has([data-testid="stButton"]),
[data-testid="stElementContainer"]:has([data-testid="stDownloadButton"]),
[data-testid="stElementContainer"]:has([data-testid="stPopover"]) { width: 100% !important; }
.stButton > button, [data-testid="stDownloadButton"] button, [data-testid="stPopover"] button {
    width: 100% !important;
}

/* Cards all have the same height */
.action-card { min-height: 185px; }

/* Study mode and other menus follow the theme colors */
div[data-baseweb="select"] > div, div[data-baseweb="select"] > div > div {
    background-color: var(--card) !important;
}
div[data-baseweb="select"] svg { fill: var(--text) !important; }
[data-baseweb="popover"] [role="listbox"], [data-baseweb="popover"] [role="option"] {
    background-color: var(--card) !important; color: var(--text) !important;
}

/* Chat box: readable placeholder and send button */
[data-testid="stChatInput"] textarea::placeholder { color: var(--muted) !important; opacity: 1 !important; }
[data-testid="stChatInputSubmitButton"] { background: var(--soft) !important; }
[data-testid="stChatInputSubmitButton"] svg { fill: var(--text) !important; color: var(--text) !important; }

/* The hero card always uses white text */
.stApp div.hero, .stApp div.hero * { color: #FFFFFF !important; }
"""


def logo_svg(size=40):
    """A simple open-book logo."""
    return (
        f'<svg width="{size}" height="{size}" viewBox="0 0 64 64" fill="none" '
        'xmlns="http://www.w3.org/2000/svg">'
        '<rect x="2" y="2" width="60" height="60" rx="16" fill="#4338CA"/>'
        '<path d="M32 19c-5-4-12-5-20-4v30c8-1 15 0 20 4 5-4 12-5 20-4V15c-8-1-15 0-20 4z" fill="#FFFFFF"/>'
        '<path d="M32 19v30" stroke="#4338CA" stroke-width="3"/>'
        '<rect x="38" y="23" width="9" height="3" rx="1.5" fill="#F5B301"/>'
        '<rect x="38" y="30" width="9" height="3" rx="1.5" fill="#C7C9F2"/>'
        '</svg>'
    )


def inject_css():
    """Adds our colors and styles to the page."""
    theme = THEMES["dark" if st.session_state.dark_mode else "light"]
    variables = ":root {" + "".join(f"--{k}: {v};" for k, v in theme.items()) + "}"
    css = variables + BASE_CSS
    if st.session_state.dark_mode:
        css += DARK_CSS
    css += HERO_CSS
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ---------- Helper functions ----------

def clean_title(text):
    """Makes a safe, short chat title."""
    text = re.sub(r"[*_`#\[\]<>~|]", "", text)
    text = " ".join(text.split())
    if len(text) > 45:
        text = text[:45].rstrip() + "..."
    return text or "New chat"


def short_label(title, limit=26):
    return title if len(title) <= limit else title[:limit].rstrip() + "..."


def get_owner():
    """Online: every visitor gets a private ID that is kept in the page link.
    On the laptop (MULTI_USER is not set): one owner, so old chats stay visible."""
    if os.getenv("MULTI_USER", "").lower() != "true":
        return db.DEFAULT_OWNER
    visitor = st.query_params.get("u")
    if not visitor or not re.fullmatch(r"[a-f0-9]{16}", visitor):
        visitor = uuid.uuid4().hex[:16]
        st.query_params["u"] = visitor
    return visitor


def init_state():
    """Sets up the app's memory the first time the page loads."""
    if "ready" in st.session_state:
        return

    db.init_db()
    st.session_state.owner = get_owner()

    language = db.get_setting("language", "English", owner=st.session_state.owner)
    level = db.get_setting("level", "Beginner", owner=st.session_state.owner)

    st.session_state.page = "home"
    st.session_state.current_chat_id = None
    st.session_state.mode_sel = "Ask a Question"
    st.session_state.language_sel = language if language in LANGUAGES else "English"
    st.session_state.level_sel = level if level in LEVELS else "Beginner"
    st.session_state.dark_mode = (
        db.get_setting("dark_mode", "False", owner=st.session_state.owner) == "True"
    )
    st.session_state.pending_doc = None
    st.session_state.nonce = 0
    st.session_state.ready = True


# ---------- Button actions (callbacks) ----------

def save_prefs():
    owner = st.session_state.owner
    db.set_setting("language", st.session_state.language_sel, owner=owner)
    db.set_setting("level", st.session_state.level_sel, owner=owner)
    db.set_setting("dark_mode", st.session_state.dark_mode, owner=owner)


def go_home():
    st.session_state.page = "home"
    st.session_state.current_chat_id = None
    st.session_state.pending_doc = None


def new_chat(mode=None):
    """Starts a fresh conversation. Old conversations stay saved."""
    st.session_state.page = "chat"
    st.session_state.current_chat_id = None
    st.session_state.pending_doc = None
    st.session_state.nonce += 1
    if mode in MODES:
        st.session_state.mode_sel = mode


def open_chat(chat_id):
    chat = db.get_chat(chat_id, owner=st.session_state.owner)
    if not chat:
        return
    st.session_state.page = "chat"
    st.session_state.current_chat_id = chat_id
    st.session_state.pending_doc = None
    st.session_state.nonce += 1
    if chat["mode"] in MODES:
        st.session_state.mode_sel = chat["mode"]
    if chat["language"] in LANGUAGES:
        st.session_state.language_sel = chat["language"]
    if chat["level"] in LEVELS:
        st.session_state.level_sel = chat["level"]


def rename_chat(chat_id):
    typed = st.session_state.get(f"rename_{chat_id}", "").strip()
    if typed:
        db.rename_chat(chat_id, clean_title(typed))


def delete_chat(chat_id):
    db.delete_chat(chat_id)
    if st.session_state.current_chat_id == chat_id:
        go_home()


def clear_messages(chat_id):
    db.clear_messages(chat_id)


def remove_document(chat_id):
    if chat_id:
        db.set_document(chat_id, None, None)
    st.session_state.pending_doc = None
    st.session_state.nonce += 1  # resets the upload box


def use_prompt(text):
    st.session_state.pending_prompt = text


def get_attached_doc(chat):
    """Returns (file_name, file_text) for the current chat, or (None, None)."""
    if chat and chat.get("doc_name"):
        return chat["doc_name"], chat["doc_text"]
    pending = st.session_state.pending_doc
    if pending:
        return pending["name"], pending["text"]
    return None, None


# ---------- Sidebar ----------

def render_chat_row(chat):
    """One saved conversation: open button + rename/delete menu."""
    chat_id = chat["id"]
    is_active = chat_id == st.session_state.current_chat_id
    icon = MODE_INFO.get(chat["mode"], {}).get("icon", "💬")

    open_col, menu_col = st.columns([5, 1.4])
    open_col.button(
        f"{icon} {short_label(chat['title'])}",
        key=f"open_{chat_id}",
        type="primary" if is_active else "secondary",
        on_click=open_chat,
        args=(chat_id,),
    )
    with menu_col.popover("⋯"):
        st.text_input("Chat name", value=chat["title"], key=f"rename_{chat_id}")
        st.button("💾 Save name", key=f"save_{chat_id}", on_click=rename_chat, args=(chat_id,))
        st.button("🗑️ Delete chat", key=f"del_{chat_id}", on_click=delete_chat, args=(chat_id,))


def render_sidebar():
    with st.sidebar:
        st.markdown(
            f'<div class="brand">{logo_svg(38)}<span class="brand-name">Study Buddy AI</span></div>',
            unsafe_allow_html=True,
        )

        st.button("➕ New Chat", type="primary", on_click=new_chat)
        st.button("🏠 Home", on_click=go_home)

        st.markdown('<div class="section-label">Study mode</div>', unsafe_allow_html=True)
        st.selectbox(
            "Study mode",
            list(MODES.keys()),
            key="mode_sel",
            format_func=lambda name: f"{MODE_INFO[name]['icon']} {name}",
            label_visibility="collapsed",
        )

        chats = db.list_chats(owner=st.session_state.owner)
        st.markdown('<div class="section-label">Recent chats</div>', unsafe_allow_html=True)
        if not chats:
            st.caption("Your conversations are saved here automatically.")
        for chat in chats[:5]:
            render_chat_row(chat)

        older = chats[5:]
        if older:
            with st.expander(f"Older chats ({len(older)})"):
                for chat in older:
                    render_chat_row(chat)

        st.markdown('<div class="section-label">Settings</div>', unsafe_allow_html=True)
        with st.expander("⚙️ Language, level and theme"):
            st.selectbox("🌍 Answer language", LANGUAGES, key="language_sel", on_change=save_prefs)
            st.selectbox("🎯 Your level", LEVELS, key="level_sel", on_change=save_prefs)
            st.toggle("🌙 Dark mode", key="dark_mode", on_change=save_prefs)


# ---------- Home page ----------

def render_home():
    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-logo">{logo_svg(84)}</div>
            <div>
                <div class="hero-title">Welcome to Your Personal Study Buddy</div>
                <div class="hero-text">
                    Ask questions, get easy explanations, make notes, practice with quizzes
                    and learn from your own PDF, TXT and DOCX files. I can reply in English,
                    Roman Urdu or Urdu.
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    stats = db.get_stats(owner=st.session_state.owner)
    columns = st.columns(3)
    tiles = [
        (stats["chats"], "Saved conversations"),
        (stats["questions"], "Questions asked"),
        (stats["files"], "Files uploaded"),
    ]
    for column, (number, label) in zip(columns, tiles):
        column.markdown(
            f'<div class="stat"><div class="stat-num">{number}</div>'
            f'<div class="stat-label">{label}</div></div>',
            unsafe_allow_html=True,
        )

    st.markdown('<div class="page-heading">What would you like to do today?</div>', unsafe_allow_html=True)

    for row_start in range(0, len(QUICK_ACTIONS), 3):
        columns = st.columns(3)
        for column, action in zip(columns, QUICK_ACTIONS[row_start:row_start + 3]):
            title, icon, mode, description, color = action
            with column:
                st.markdown(
                    f'<div class="action-card">'
                    f'<div class="action-icon" style="background:{color}22">{icon}</div>'
                    f'<div class="action-title">{title}</div>'
                    f'<div class="action-desc">{description}</div>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
                st.button(
                    f"Start: {title}",
                    key=f"card_{mode}",
                    on_click=new_chat,
                    args=(mode,),
                )

    st.markdown('<div class="page-heading">Study tips</div>', unsafe_allow_html=True)
    tip = STUDY_TIPS[date.today().toordinal() % len(STUDY_TIPS)]
    st.markdown(
        f'<div class="tip"><div class="tip-title">💡 Tip of the day</div>{tip}</div>',
        unsafe_allow_html=True,
    )
    with st.expander("See more study tips"):
        for item in STUDY_TIPS:
            st.markdown(f"- {item}")

    # Typing here starts a new chat in the selected mode
    typed = st.chat_input("Ask Study Buddy anything...")
    if typed:
        st.session_state.pending_prompt = typed
        new_chat()
        st.rerun()


# ---------- Chat page ----------

def render_upload_box(chat):
    """Upload area for study material. The file belongs to the current chat."""
    chat_id = chat["id"] if chat else None
    doc_name, doc_text = get_attached_doc(chat)

    with st.expander("📎 Study material (PDF, TXT, DOCX)", expanded=bool(doc_name)):
        if doc_name:
            st.success(f"Attached: **{doc_name}** ({len(doc_text):,} characters)")
            if len(doc_text) > MAX_DOC_CHARS:
                st.caption(
                    "This is a long file. For each question I read the most useful parts of it."
                )
            st.button("Remove file", key="remove_doc", on_click=remove_document, args=(chat_id,))
            return

        st.caption("Upload your notes, then ask me to summarize them, explain hard parts or make a quiz.")
        uploaded = st.file_uploader(
            "Upload a file",
            type=ALLOWED_TYPES,
            key=f"uploader_{chat_id or 'new'}_{st.session_state.nonce}",
            label_visibility="collapsed",
        )
        if uploaded is not None:
            text, error = read_uploaded_file(uploaded)
            if error:
                st.error(error)
            else:
                if chat_id:
                    db.set_document(chat_id, uploaded.name, text)
                else:
                    st.session_state.pending_doc = {"name": uploaded.name, "text": text}
                st.rerun()


def handle_user_message(chat, messages, prompt):
    """Shows the question, gets the AI answer, and saves both."""
    mode = st.session_state.mode_sel
    language = st.session_state.language_sel
    level = st.session_state.level_sel
    doc_name, doc_text = get_attached_doc(chat)

    with st.chat_message("user", avatar=USER_AVATAR):
        st.markdown(prompt)

    history = messages + [{"role": "user", "content": prompt}]

    with st.chat_message("assistant", avatar=BOT_AVATAR):
        with st.spinner("Study Buddy is thinking..."):
            reply, success = get_ai_response(mode, history, language, level, doc_name, doc_text)

        if not success:
            st.error(f"{reply}\n\nYour message was not saved. Please try again.")
            return

        st.markdown(reply)

    # Save only after the AI answered successfully
    if chat is None:
        chat_id = db.create_chat(
            clean_title(prompt), mode, language, level, owner=st.session_state.owner
        )
        pending = st.session_state.pending_doc
        if pending:
            db.set_document(chat_id, pending["name"], pending["text"])
            st.session_state.pending_doc = None
        st.session_state.current_chat_id = chat_id
    else:
        chat_id = chat["id"]
        db.update_chat_settings(chat_id, mode, language, level)

    db.add_message(chat_id, "user", prompt)
    db.add_message(chat_id, "assistant", reply)
    st.rerun()


def render_chat():
    chat_id = st.session_state.current_chat_id
    chat = db.get_chat(chat_id, owner=st.session_state.owner) if chat_id else None

    if chat_id and chat is None:  # the chat was deleted
        go_home()
        st.rerun()

    messages = db.get_messages(chat_id) if chat else []
    mode = st.session_state.mode_sel
    info = MODE_INFO[mode]
    doc_name, _ = get_attached_doc(chat)

    # Header
    title = chat["title"] if chat else "New chat"
    title_col, download_col, clear_col = st.columns([5, 1.6, 1.4])
    title_col.markdown(f"### {info['icon']} {title}")
    title_col.markdown(
        f'<div class="chat-meta">{mode} · {st.session_state.language_sel} · '
        f"{st.session_state.level_sel}</div>",
        unsafe_allow_html=True,
    )

    if messages:
        chat_text = "\n\n".join(f"{m['role'].upper()}: {m['content']}" for m in messages)
        download_col.download_button(
            "⬇️ Download",
            chat_text,
            file_name=f"study_buddy_chat_{chat_id}.txt",
        )
        with clear_col.popover("🧹 Clear"):
            st.write("Remove all messages from this chat? The chat stays in your history.")
            st.button(
                "Yes, clear messages",
                key="clear_messages",
                on_click=clear_messages,
                args=(chat_id,),
            )

    render_upload_box(chat)

    # Old messages
    for message in messages:
        avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])

    # Empty chat: welcome message and ideas
    if not messages:
        st.markdown(f"**What would you like to study today?** {info['description']}")
        if doc_name:
            ideas = [
                "Summarize this file",
                "Explain the difficult parts in simple words",
                "List the important points",
                "Create a quiz from this file",
            ]
        else:
            ideas = info["examples"]
        st.caption("Try one of these:")
        for number, idea in enumerate(ideas):
            st.button(idea, key=f"idea_{number}", on_click=use_prompt, args=(idea,))

    # Input box
    placeholder = "Ask about your uploaded file..." if doc_name else info["placeholder"]
    typed = st.chat_input(placeholder)
    pending = st.session_state.pop("pending_prompt", None)
    prompt = typed or pending

    if prompt:
        handle_user_message(chat, messages, prompt)


# ---------- Run the app ----------

def main():
    init_state()
    inject_css()
    render_sidebar()

    if st.session_state.page == "home":
        render_home()
    else:
        render_chat()


main()
