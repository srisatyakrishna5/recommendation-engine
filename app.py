from __future__ import annotations

import base64
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"
ICONS_DIR = ROOT_DIR / "icons"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from recommendation_engine import RecommendationEngine, get_settings

# ---------------------------------------------------------------------------
# Icon helpers — encode PNGs as base64 for inline HTML usage
# ---------------------------------------------------------------------------
_icon_cache: dict[str, str] = {}

def _icon_img(filename: str, height: int = 20) -> str:
    """Return an <img> tag with a base64-encoded PNG from the icons/ folder."""
    if filename not in _icon_cache:
        icon_path = ICONS_DIR / filename
        if icon_path.exists():
            b64 = base64.b64encode(icon_path.read_bytes()).decode()
            _icon_cache[filename] = (
                f'<img src="data:image/png;base64,{b64}" '
                f'height="{height}" style="vertical-align:middle;" />'
            )
        else:
            _icon_cache[filename] = ""
    return _icon_cache[filename]

# Map service keys to icon filenames
SERVICE_ICONS = {
    "openai": "azure-openai.png",
    "search": "cognitive-search.png",
    "docintel": "form-recognizers.png",
    "vision": "computer-vision.png",
    "speech": "speech-services.png",
}

# ---------------------------------------------------------------------------
# Custom CSS for a polished, modern look
# ---------------------------------------------------------------------------
_CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&family=Sora:wght@500;600;700;800&display=swap');

:root {
    --brand-ink: #153143;
    --brand-muted: #597486;
    --brand-teal: #0f766e;
    --brand-coral: #ff7a59;
    --brand-gold: #f6c35b;
    --brand-line: #d9e7eb;
}

.stApp {
    font-family: 'Manrope', sans-serif;
    color: var(--brand-ink);
    background:
        radial-gradient(35rem 24rem at 95% 6%, rgba(15, 118, 110, 0.10), transparent 68%),
        radial-gradient(32rem 22rem at 2% 12%, rgba(246, 195, 91, 0.16), transparent 70%),
        linear-gradient(180deg, #f9fcfd 0%, #f2f8fa 100%);
}

section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #17354a 0%, #244961 100%);
}

h1, h2, h3, h4 {
    font-family: 'Sora', sans-serif;
    letter-spacing: -0.02em;
}

.hero-banner {
    border-radius: 20px;
    padding: 1.75rem;
    margin-bottom: 1.5rem;
    color: #fff;
    background: linear-gradient(120deg, #0d7c79 0%, #16a394 48%, #2d8fce 100%);
    box-shadow: 0 18px 40px rgba(21, 49, 67, 0.22);
    overflow: hidden;
    position: relative;
}

.hero-banner::after {
    content: "";
    position: absolute;
    width: 13rem;
    height: 13rem;
    border-radius: 50%;
    right: -4rem;
    top: -5rem;
    background: radial-gradient(circle, rgba(255,255,255,0.26) 0%, rgba(255,255,255,0.03) 64%, transparent 72%);
}

.brand-shell {
    display: grid;
    grid-template-columns: minmax(0, 1fr);
    gap: 1rem;
    position: relative;
    z-index: 2;
}

.brand-header {
    display: flex;
    gap: 1rem;
    align-items: center;
}

.brand-mark {
    width: 3.25rem;
    height: 3.25rem;
    border-radius: 0.95rem;
    background: linear-gradient(145deg, rgba(255,255,255,0.35) 0%, rgba(255,255,255,0.16) 100%);
    border: 1px solid rgba(255,255,255,0.45);
    display: flex;
    align-items: center;
    justify-content: center;
    font-family: 'Sora', sans-serif;
    font-weight: 800;
    font-size: 1.05rem;
    letter-spacing: 0.06em;
    backdrop-filter: blur(6px);
}

.brand-kicker {
    display: inline-flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.22rem 0.65rem;
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #0f493d;
    background: linear-gradient(130deg, #ffe7a8 0%, #ffd382 100%);
}

.brand-title {
    margin: 0.35rem 0 0.2rem 0;
    color: #fff;
    font-size: clamp(1.45rem, 2.4vw, 2.25rem);
}

.brand-subtitle {
    margin: 0;
    color: rgba(236, 253, 251, 0.95);
    font-size: 0.95rem;
    max-width: 72ch;
}

.service-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(11rem, 1fr));
    gap: 0.7rem;
    margin-top: 0.4rem;
}

.service-card {
    border-radius: 12px;
    padding: 0.62rem 0.72rem;
    border: 1px solid rgba(255,255,255,0.32);
    background: rgba(255,255,255,0.15);
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.55rem;
    min-height: 3rem;
}

.service-left {
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.84rem;
    font-weight: 700;
    color: #f3ffff;
}

.service-left img {
    height: 16px;
    width: auto;
    filter: drop-shadow(0 1px 1px rgba(0,0,0,0.2));
}

.service-state {
    font-size: 0.73rem;
    font-weight: 700;
    letter-spacing: 0.03em;
    text-transform: uppercase;
    padding: 0.18rem 0.52rem;
    border-radius: 999px;
}

.service-online .service-state {
    color: #0d6f53;
    background: #dcfce7;
}

.service-offline .service-state {
    color: #9f1239;
    background: #ffe4e6;
}

.pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    padding: 6px 12px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 700;
    background: #def7f2;
    color: #0f766e;
    border: 1px solid #9fddd1;
}

.product-card {
    background: linear-gradient(145deg, #ffffff 0%, #f4fbfd 100%);
    border: 1px solid var(--brand-line);
    border-radius: 14px;
    padding: 1.5rem;
    margin-bottom: 1rem;
    transition: box-shadow 0.25s ease, transform 0.25s ease;
}

.product-card:hover {
    box-shadow: 0 12px 34px rgba(24, 66, 82, 0.11);
    transform: translateY(-2px);
}

.product-card h3 { margin: 0 0 0.4rem 0; color: var(--brand-ink); font-size: 1.25rem; }
.product-card .description { color: var(--brand-muted); font-size: 0.92rem; margin-bottom: 0.75rem; }

.stars { color: #f59e0b; font-size: 1rem; letter-spacing: 2px; display: inline-block; }
.stars-dim { color: #cbd5e1; }

.metric-row { display: flex; gap: 0.75rem; flex-wrap: wrap; margin: 0.75rem 0; }
.metric-badge {
    display: inline-flex; flex-direction: column; align-items: center;
    background: white; border: 1px solid #d7e8ed; border-radius: 10px;
    padding: 8px 16px; min-width: 90px;
}
.metric-badge .label { font-size: 0.7rem; text-transform: uppercase; color: #94a3b8; font-weight: 600; letter-spacing: 0.5px; }
.metric-badge .value { font-size: 1.1rem; font-weight: 700; color: #1f3d52; }
.metric-badge .value.green { color: #0f766e; }
.metric-badge .value.blue  { color: #246a9a; }

.rationale-box {
    background: #eefcf8; border-left: 4px solid #109f87;
    border-radius: 0 8px 8px 0; padding: 0.75rem 1rem;
    margin: 0.5rem 0; font-size: 0.9rem; color: #0b5a49;
}
.caution-box {
    background: #fff7e8; border-left: 4px solid #de8b00;
    border-radius: 0 8px 8px 0; padding: 0.75rem 1rem;
    margin: 0.5rem 0; font-size: 0.9rem; color: #965800;
}
.tip-box {
    background: #e9f6ff; border-left: 4px solid #2089cf;
    border-radius: 0 8px 8px 0; padding: 0.75rem 1rem;
    margin: 0.5rem 0; font-size: 0.9rem; color: #105e93;
}

.tag-chip {
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    font-size: 0.75rem; font-weight: 500; margin: 2px 3px;
    background: #e6f5fb; color: #14658d;
}
.benefit-chip {
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    font-size: 0.75rem; font-weight: 500; margin: 2px 3px;
    background: #e5faf3; color: #0d6d52;
}

.guidance-card {
    background: linear-gradient(130deg, #fff8eb 0%, #fff3db 100%);
    border: 1px solid #f5ddb0; border-radius: 14px;
    padding: 1.5rem; margin-bottom: 1.5rem;
}
.guidance-card h4 { margin: 0 0 0.6rem 0; color: #9b5d00; }
.guidance-card ul { margin: 0; padding-left: 1.2rem; }
.guidance-card li { color: #6d4d18; margin-bottom: 0.3rem; font-size: 0.92rem; }

.trace-step {
    display: flex; align-items: flex-start; gap: 12px;
    padding: 8px 0; border-bottom: 1px solid #e7eff2;
}
.trace-dot {
    width: 10px; height: 10px; border-radius: 50%;
    margin-top: 5px; flex-shrink: 0;
}
.trace-dot.ok   { background: #22c55e; }
.trace-dot.fail { background: #ef4444; }
.trace-dot.skip { background: #94a3b8; }
.trace-agent { font-weight: 600; font-size: 0.88rem; color: #1e293b; }
.trace-detail { font-size: 0.85rem; color: #64748b; }

.insight-card {
    background: #f7fcfd; border: 1px solid #d9e7eb;
    border-radius: 10px; padding: 1rem; margin: 0.5rem 0;
}
.insight-card .icon { font-size: 1.3rem; margin-right: 0.5rem; }

.arch-section {
    background: linear-gradient(145deg, #ffffff 0%, #f2f9fb 100%);
    border: 1px solid #d9e7eb; border-radius: 12px;
    padding: 1.25rem; margin-bottom: 1rem;
}
.arch-section h4 { margin: 0 0 0.5rem 0; }

.input-section {
    background: #f8fafc; border: 1px solid #dbe8ed;
    border-radius: 14px; padding: 1.5rem; margin-bottom: 1rem;
}

.admin-card {
    background: white; border: 1px solid #d9e7eb;
    border-radius: 14px; padding: 1.5rem; margin-bottom: 1rem;
}

.upload-preview {
    margin-top: 0.65rem;
}

.upload-preview-frame {
    width: 100%;
    height: 240px;
    border-radius: 12px;
    border: 1px solid #d9e7eb;
    background: linear-gradient(180deg, #f8fbfc 0%, #eef5f7 100%);
    display: flex;
    align-items: center;
    justify-content: center;
    overflow: hidden;
}

.upload-preview-empty {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 0.3rem;
    color: #64808f;
    background:
        repeating-linear-gradient(
            -45deg,
            rgba(100, 128, 143, 0.05),
            rgba(100, 128, 143, 0.05) 12px,
            rgba(255, 255, 255, 0.0) 12px,
            rgba(255, 255, 255, 0.0) 24px
        );
}

.upload-preview-empty-icon {
    font-size: 1.6rem;
    line-height: 1;
}

.upload-preview-empty-text {
    font-size: 0.84rem;
    font-weight: 600;
}

.upload-preview-frame img {
    width: 100%;
    height: 100%;
    object-fit: contain;
}

.upload-preview-caption {
    margin: 0.35rem 0 0 0;
    text-align: center;
    color: #5d7383;
    font-size: 0.82rem;
}

@media (max-width: 780px) {
    .hero-banner {
        padding: 1.2rem;
    }

    .brand-mark {
        width: 2.65rem;
        height: 2.65rem;
        border-radius: 0.75rem;
        font-size: 0.9rem;
    }

    .brand-title {
        font-size: 1.45rem;
    }

    .upload-preview-frame {
        height: 200px;
    }
}
</style>
"""


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _star_html(rating: float) -> str:
    """Render star rating as HTML."""
    full = int(rating)
    half = 1 if (rating - full) >= 0.3 else 0
    empty = 5 - full - half
    return (
        '<span class="stars">'
        + "★" * full
        + ("⯨" if half else "")
        + f'<span class="stars-dim">{"★" * empty}</span>'
        + f"</span> <small>({rating:.1f})</small>"
    )


def _service_card_html(label: str, enabled: bool, icon_html: str) -> str:
    card_cls = "service-online" if enabled else "service-offline"
    state = "online" if enabled else "offline"
    return (
        f'<div class="service-card {card_cls}">'
        f'<span class="service-left">{icon_html}<span>{label}</span></span>'
        f'<span class="service-state">{state}</span>'
        f"</div>"
    )


def _app_initials(title: str) -> str:
    words = [part for part in title.split() if part]
    if not words:
        return "RE"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def _tag_chips(items: list[str], css_class: str = "tag-chip") -> str:
    if not items:
        return ""
    return " ".join(f'<span class="{css_class}">{t}</span>' for t in items)


def _render_hero(settings) -> None:
    ico_openai = _icon_img(SERVICE_ICONS["openai"], 18)
    ico_search = _icon_img(SERVICE_ICONS["search"], 18)
    ico_vision = _icon_img(SERVICE_ICONS["vision"], 18)
    ico_speech = _icon_img(SERVICE_ICONS["speech"], 18)

    statuses = [
        ("Azure OpenAI", settings.azure_openai_ready, ico_openai),
        ("Azure AI Search", settings.azure_search_ready, ico_search),
        ("Azure Vision", settings.vision_ready, ico_vision),
        ("Azure Speech", settings.speech_ready, ico_speech),
    ]
    service_cards = "".join(
        _service_card_html(lbl, on, ico) for lbl, on, ico in statuses
    )
    initials = _app_initials(settings.app_title)
    st.markdown(
        f"""
        <div class="hero-banner">
            <div class="brand-shell">
                <div class="brand-header">
                    <div class="brand-mark">{initials}</div>
                    <div>
                        <span class="brand-kicker">Trusted Product Intelligence</span>
                        <h1 class="brand-title">{settings.app_title}</h1>
                        <p class="brand-subtitle">
                            A branded recommendation workspace that blends Azure OpenAI reasoning,
                            Azure AI Search grounding, and multimodal context to deliver confident product guidance.
                        </p>
                    </div>
                </div>
                <div class="service-grid">{service_cards}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_recommendations(bundle) -> None:
    # --- Guidance card ---
    guidance_items = "".join(f"<li>{tip}</li>" for tip in bundle.guidance)
    st.markdown(
        f"""
        <div class="guidance-card">
            <h4>💡 Expert Guidance</h4>
            <p style="color:#4c1d95; margin:0 0 0.5rem 0;">{bundle.summary}</p>
            <ul>{guidance_items}</ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # --- Search mode badge ---
    st.markdown(
        f'<span class="pill pill-on" style="margin-bottom:1rem; display:inline-flex;">'
        f'🗂️ Search mode: <strong style="margin-left:4px;">{bundle.search_mode}</strong></span>',
        unsafe_allow_html=True,
    )

    if not bundle.recommendations:
        st.warning("No catalog-matched products could be verified for this request.")
        return

    # --- Product cards ---
    for idx, rec in enumerate(bundle.recommendations, 1):
        p = rec.product
        stars = _star_html(p.rating)
        tags_html = _tag_chips(p.tags, "tag-chip")
        benefits_html = _tag_chips(p.benefits, "benefit-chip")

        rationale_html = f'<div class="rationale-box">✅ <strong>Why it fits:</strong> {rec.rationale}</div>'
        caution_html = (
            f'<div class="caution-box">⚠️ <strong>Watch out:</strong> {rec.caution}</div>'
            if rec.caution else ""
        )
        tip_html = (
            f'<div class="tip-box">💡 <strong>Buying tip:</strong> {rec.buying_tip}</div>'
            if rec.buying_tip else ""
        )

        st.markdown(
            f"""
            <div class="product-card">
                <div style="display:flex; justify-content:space-between; align-items:flex-start;">
                    <h3>#{idx} &nbsp; {p.name}</h3>
                    <div>{stars}</div>
                </div>
                <div class="description">{p.description}</div>
                <div class="metric-row">
                    <div class="metric-badge">
                        <span class="label">Price</span>
                        <span class="value green">${p.price:,.2f}</span>
                    </div>
                    <div class="metric-badge">
                        <span class="label">Category</span>
                        <span class="value">{p.category}</span>
                    </div>
                    <div class="metric-badge">
                        <span class="label">Value Score</span>
                        <span class="value blue">{rec.value_score:.1f}/10</span>
                    </div>
                </div>
                {rationale_html}
                {caution_html}
                {tip_html}
                <div style="margin-top:0.6rem;">
                    {tags_html}
                    {benefits_html}
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --- Agent trace timeline ---
    with st.expander("🔗 Processing Trace", expanded=False):
        trace_html = ""
        for step in bundle.trace:
            status_lower = step.status.lower()
            dot_cls = "ok" if "ok" in status_lower or "done" in status_lower or "success" in status_lower else (
                "fail" if "fail" in status_lower or "error" in status_lower else "skip"
            )
            trace_html += f"""
            <div class="trace-step">
                <span class="trace-dot {dot_cls}"></span>
                <div>
                    <span class="trace-agent">{step.agent_name}</span>
                    <span style="color:#94a3b8; font-size:0.8rem; margin-left:6px;">[{step.status}]</span>
                    <br/><span class="trace-detail">{step.detail}</span>
                </div>
            </div>
            """
        st.markdown(trace_html, unsafe_allow_html=True)

    # --- Extracted context insights ---
    with st.expander("📋 Extracted Context", expanded=False):
        if bundle.transcript:
            st.markdown(
                f'<div class="insight-card"><span class="icon">🎙️</span>'
                f'<strong>Speech transcript:</strong> {bundle.transcript}</div>',
                unsafe_allow_html=True,
            )
        if bundle.document_insight:
            st.markdown(
                f'<div class="insight-card"><span class="icon">📄</span>'
                f'<strong>Document summary:</strong> {bundle.document_insight.summary}</div>',
                unsafe_allow_html=True,
            )
        if bundle.image_insight:
            img_tags = (
                f'<br/><span class="icon">🏷️</span><strong>Tags:</strong> '
                + _tag_chips(bundle.image_insight.tags)
                if bundle.image_insight.tags else ""
            )
            st.markdown(
                f'<div class="insight-card"><span class="icon">👁️</span>'
                f'<strong>Image understanding:</strong> {bundle.image_insight.description}'
                f'{img_tags}</div>',
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Main application
# ---------------------------------------------------------------------------

def main() -> None:
    settings = get_settings()
    engine = RecommendationEngine(settings)

    st.set_page_config(
        page_title=settings.app_title,
        page_icon="🛍️",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Inject custom CSS
    st.markdown(_CUSTOM_CSS, unsafe_allow_html=True)

    # Hero banner with service status pills
    _render_hero(settings)

    # Tabs
    customer_tab, admin_tab, architecture_tab = st.tabs([
        "🛒  Customer Assistant",
        "⚙️  Admin Catalog",
        "🏗️  Architecture",
    ])

    # ------------------------------------------------------------------
    # CUSTOMER ASSISTANT
    # ------------------------------------------------------------------
    with customer_tab:
        st.markdown("#### Tell us what you need")

        col_input, col_media = st.columns([3, 2], gap="large")

        with col_input:
            query = st.text_area(
                "Describe your needs",
                placeholder="e.g. Suggest affordable products for deep-cleaning my kitchen and removing pet hair from the couch.",
                height=160,
                label_visibility="collapsed",
            )

            audio_bytes = None
            audio_name = "voice-query.wav"
            if hasattr(st, "audio_input"):
                recorded_audio = st.audio_input("🎙️ Or describe by voice")
                if recorded_audio is not None:
                    audio_bytes = recorded_audio.getvalue()
                    audio_name = recorded_audio.name or audio_name
            else:
                st.caption("Upgrade Streamlit for voice input support.")

        with col_media:
            uploaded_image = st.file_uploader(
                "📷 Upload a room or product image",
                type=["png", "jpg", "jpeg", "webp"],
            )
            if uploaded_image:
                img_b64 = base64.b64encode(uploaded_image.getvalue()).decode()
                ext = Path(uploaded_image.name).suffix.lstrip(".").lower()
                mime = {"jpg": "jpeg", "jpeg": "jpeg", "png": "png", "webp": "webp"}.get(ext, "png")
                st.markdown(
                    f'<div class="upload-preview">'
                    f'  <div class="upload-preview-frame">'
                    f'    <img src="data:image/{mime};base64,{img_b64}" alt="Uploaded image preview" />'
                    f"  </div>"
                    f'  <p class="upload-preview-caption">Uploaded image</p>'
                    f"</div>",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    """
                    <div class="upload-preview">
                        <div class="upload-preview-frame">
                            <div class="upload-preview-empty">
                                <div class="upload-preview-empty-icon">🖼️</div>
                                <div class="upload-preview-empty-text">Image preview appears here</div>
                            </div>
                        </div>
                        <p class="upload-preview-caption">No image selected</p>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
        _, btn_col, _ = st.columns([2, 3, 2])
        with btn_col:
            go = st.button(
                "✨  Get Personalized Recommendations",
                type="primary",
            )

        if go:
            if not query and not audio_bytes and not uploaded_image:
                st.warning("Please provide a text prompt, voice note, or image first.")
            else:
                with st.spinner("🤖 Processing your request..."):
                    bundle = engine.recommend(
                        query=query,
                        audio_bytes=audio_bytes,
                        audio_name=audio_name,
                        image_bytes=uploaded_image.getvalue() if uploaded_image else None,
                        image_name=uploaded_image.name if uploaded_image else None,
                    )
                st.divider()
                _render_recommendations(bundle)

    # ------------------------------------------------------------------
    # ADMIN CATALOG
    # ------------------------------------------------------------------
    with admin_tab:
        cat_rows = engine.catalog_rows()

        # Summary metrics
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Total Products", len(cat_rows))
        unique_cats = len({r.get("category", "") for r in cat_rows}) if cat_rows else 0
        m2.metric("Categories", unique_cats)
        avg_price = sum(r.get("price", 0) for r in cat_rows) / max(len(cat_rows), 1) if cat_rows else 0
        m3.metric("Avg Price", f"${avg_price:,.2f}")
        avg_rating = sum(r.get("rating", 0) for r in cat_rows) / max(len(cat_rows), 1) if cat_rows else 0
        m4.metric("Avg Rating", f"{avg_rating:.1f} ★")

        st.markdown("---")

        mgmt_col, add_col = st.columns([3, 2], gap="large")

        with mgmt_col:
            st.markdown("##### 📦 Current Catalog")
            st.dataframe(
                cat_rows,
                width="stretch",
                height=350,
            )

            st.markdown("##### 📤 Import Catalog")
            uploaded_catalog = st.file_uploader(
                "Upload catalog file (CSV or JSON)",
                type=["csv", "json"],
                key="catalog-upload",
            )
            ic1, ic2 = st.columns([1, 1])
            with ic1:
                replace_catalog = st.toggle("Replace existing catalog", value=True)
            with ic2:
                if st.button("⬆️ Ingest", use_container_width=True):
                    if uploaded_catalog is None:
                        st.warning("Upload a file first.")
                    else:
                        result = engine.import_catalog(
                            filename=uploaded_catalog.name,
                            raw_bytes=uploaded_catalog.getvalue(),
                            replace=replace_catalog,
                        )
                        st.success(result.message)
                        st.rerun()

            st.markdown("##### 🔄 Azure AI Search Sync")
            if st.button("Sync catalog to Azure AI Search", use_container_width=True):
                with st.spinner("Syncing..."):
                    synced, message = engine.sync_catalog_to_search()
                if synced:
                    st.success(message)
                else:
                    st.info(message)

        with add_col:
            st.markdown("##### ➕ Add Product Manually")
            with st.form("manual-product-form"):
                name = st.text_input("Product name")
                category = st.text_input("Category", value="Cleaning")
                description = st.text_area("Description", height=100)
                p1, p2 = st.columns(2)
                with p1:
                    price = st.number_input("Price ($)", min_value=0.0, value=19.99, step=1.0)
                with p2:
                    rating = st.slider("Rating", 0.0, 5.0, 4.2, 0.1)
                tags = st.text_input("Tags", placeholder="mop, reusable, microfiber")
                use_cases = st.text_input("Use cases", placeholder="kitchen floors, tile")
                benefits = st.text_input("Benefits", placeholder="durable, washable")
                submitted = st.form_submit_button("Add Product", use_container_width=True)
                if submitted:
                    if not name or not description:
                        st.warning("Name and description are required.")
                    else:
                        engine.add_manual_product(
                            name=name, category=category, description=description,
                            price=price, rating=rating, tags=tags,
                            use_cases=use_cases, benefits=benefits,
                        )
                        st.success(f"Added **{name}** to the catalog.")
                        st.rerun()

    # ------------------------------------------------------------------
    # ARCHITECTURE
    # ------------------------------------------------------------------
    with architecture_tab:
        st.markdown("#### System Architecture Overview")

        # Pre-compute icon img tags for architecture section
        ico_a_openai = _icon_img(SERVICE_ICONS["openai"], 22)
        ico_a_search = _icon_img(SERVICE_ICONS["search"], 22)
        ico_a_vision = _icon_img(SERVICE_ICONS["vision"], 22)
        ico_a_speech = _icon_img(SERVICE_ICONS["speech"], 22)

        a1, a2 = st.columns(2, gap="medium")

        with a1:
            st.markdown(
                f"""
                <div class="arch-section">
                    <h4>📥 Input Channels</h4>
                    <ul>
                        <li><strong>Text</strong> &mdash; Natural language product queries</li>
                        <li>{ico_a_speech} <strong>Voice</strong> &mdash; Azure Speech transcription</li>
                        <li>{ico_a_vision} <strong>Image</strong> &mdash; Azure Vision captioning &amp; tagging</li>
                    </ul>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div class="arch-section">
                    <h4>🤖 Processing Pipeline</h4>
                    <table style="width:100%; font-size:0.88rem;">
                        <tr><td style="padding:4px 8px;">🧠</td><td><strong>QueryInterpreter</strong></td><td style="color:#64748b;">Builds need profile + search terms (single LLM call)</td></tr>
                        <tr><td style="padding:4px 8px;">🔍</td><td><strong>CatalogSearch</strong></td><td style="color:#64748b;">Azure AI Search / local fallback</td></tr>
                        <tr><td style="padding:4px 8px;">💰</td><td><strong>ValueScorer</strong></td><td style="color:#64748b;">Algorithmic relevance + value scoring</td></tr>
                        <tr><td style="padding:4px 8px;">📋</td><td><strong>Explainer</strong></td><td style="color:#64748b;">LLM-powered buying advice</td></tr>
                        <tr><td style="padding:4px 8px;">🛡️</td><td><strong>Validator</strong></td><td style="color:#64748b;">Groundedness verification</td></tr>
                    </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with a2:
            st.markdown(
                f"""
                <div class="arch-section">
                    <h4>☁️ Azure Services</h4>
                    <table style="width:100%; font-size:0.88rem;">
                        <tr><td style="padding:6px 8px;">{ico_a_openai}</td><td><strong>Azure OpenAI GPT-4o</strong></td><td style="color:#64748b;">Reasoning &amp; explanation</td></tr>
                        <tr><td style="padding:6px 8px;">{ico_a_search}</td><td><strong>Azure AI Search</strong></td><td style="color:#64748b;">Semantic &amp; vector retrieval</td></tr>
                        <tr><td style="padding:6px 8px;">{ico_a_vision}</td><td><strong>Azure AI Vision</strong></td><td style="color:#64748b;">Image captioning &amp; tags</td></tr>
                        <tr><td style="padding:6px 8px;">{ico_a_speech}</td><td><strong>Speech Service</strong></td><td style="color:#64748b;">Voice transcription</td></tr>
                    </table>
                </div>
                """,
                unsafe_allow_html=True,
            )

            st.markdown(
                """
                <div class="arch-section">
                    <h4>⚡ Data Flow</h4>
                    <ol style="font-size:0.88rem; color:#475569; padding-left:1.2rem;">
                        <li>User sends text / voice / image</li>
                        <li>Input channels extract structured context</li>
                        <li>QueryInterpreter builds need profile + search terms (1 LLM call)</li>
                        <li>CatalogSearch queries index with expanded terms</li>
                        <li>ValueScorer ranks matches algorithmically</li>
                        <li>Explainer produces buying advice (1 LLM call)</li>
                        <li>Validator ensures groundedness</li>
                        <li>Results rendered with trace &amp; context</li>
                    </ol>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with st.expander("📋 Environment Variables Reference"):
            try:
                env_text = Path(".env.template").read_text(encoding="utf-8")
                st.code(env_text, language="bash")
            except FileNotFoundError:
                st.info("No .env.template file found in the project root.")


if __name__ == "__main__":
    main()
