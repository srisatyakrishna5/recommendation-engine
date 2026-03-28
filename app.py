from __future__ import annotations

import html
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parent
ICONS_DIR = ROOT_DIR / "icons"

from src.config import get_settings, Settings
from src.engine import RecommendationEngine


def _rating_text(rating: float) -> str:
    full = int(rating)
    half = 1 if (rating - full) >= 0.3 else 0
    empty = max(0, 5 - full - half)
    return f"{'★' * full}{'⯨' if half else ''}{'☆' * empty} ({rating:.1f})"


def _bullet_list(items: list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def _inject_brand_styles() -> None:
    st.markdown(
        """
        <style>
        .brand-hero {
            border: 1px solid #d7e4f6;
            border-radius: 16px;
            padding: 1rem 1.15rem;
            margin: 0.2rem 0 0.9rem 0;
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            box-shadow: 0 8px 20px rgba(15, 42, 77, 0.06);
        }
        .brand-row {
            display: flex;
            align-items: center;
            gap: 0.85rem;
            margin-bottom: 0.45rem;
        }
        .brand-mark {
            width: 2.5rem;
            height: 2.5rem;
            border-radius: 10px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            font-weight: 800;
            font-size: 0.88rem;
            letter-spacing: 0.04em;
            color: #fff;
            background: linear-gradient(135deg, #0f5ea6 0%, #1d7bd7 100%);
            box-shadow: 0 8px 16px rgba(22, 96, 166, 0.28);
        }
        .brand-kicker {
            display: inline-block;
            font-size: 0.7rem;
            letter-spacing: 0.06em;
            text-transform: uppercase;
            font-weight: 700;
            color: #1b4f89;
            background: #eaf3ff;
            border: 1px solid #cfe2ff;
            padding: 0.16rem 0.48rem;
            border-radius: 999px;
            margin-bottom: 0.22rem;
        }
        .brand-title {
            margin: 0;
            color: #122b4a;
            font-size: 1.42rem;
            font-weight: 750;
            line-height: 1.15;
        }
        .brand-subtitle {
            margin: 0.3rem 0 0.75rem 0;
            color: #486382;
            font-size: 0.92rem;
        }
        .brand-statuses {
            display: flex;
            gap: 0.45rem;
            flex-wrap: wrap;
        }
        .brand-status-pill {
            display: inline-flex;
            align-items: center;
            gap: 0.35rem;
            border-radius: 999px;
            border: 1px solid transparent;
            padding: 0.22rem 0.55rem;
            font-size: 0.74rem;
            font-weight: 700;
        }
        .brand-status-pill.ready {
            background: #eafcf3;
            color: #116648;
            border-color: #cfeedd;
        }
        .brand-status-pill.offline {
            background: #fff1f2;
            color: #9f1239;
            border-color: #fecdd3;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _app_initials(title: str) -> str:
    words = [segment for segment in title.split() if segment]
    if not words:
        return "RE"
    if len(words) == 1:
        return words[0][:2].upper()
    return (words[0][0] + words[1][0]).upper()


def _inject_recommendation_styles() -> None:
    st.markdown(
        """
        <style>
        .rec-summary {
            border: 1px solid #c7dbff;
            background: linear-gradient(180deg, #eef5ff 0%, #f7fbff 100%);
            border-radius: 14px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.8rem;
            color: #163a63;
        }
        .rec-guidance {
            border: 1px solid #ffe3a8;
            background: #fff9eb;
            border-radius: 14px;
            padding: 0.9rem 1rem;
            margin-bottom: 0.9rem;
        }
        .rec-card {
            border: 1px solid #d7e3f5;
            background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
            border-radius: 16px;
            padding: 1rem;
            margin: 0.7rem 0 0.95rem 0;
        }
        .rec-header {
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            gap: 1rem;
            margin-bottom: 0.5rem;
        }
        .rec-title {
            margin: 0;
            color: #112b4a;
            font-size: 1.1rem;
            font-weight: 700;
        }
        .rec-desc {
            color: #46607e;
            font-size: 0.93rem;
            margin: 0.3rem 0 0.7rem 0;
        }
        .rec-metrics {
            display: flex;
            gap: 0.45rem;
            flex-wrap: wrap;
            margin: 0.3rem 0 0.75rem 0;
        }
        .rec-badge {
            display: inline-block;
            border-radius: 999px;
            padding: 0.27rem 0.62rem;
            font-size: 0.76rem;
            font-weight: 700;
            border: 1px solid transparent;
        }
        .rec-badge.price { background: #edfdf6; color: #08663f; border-color: #c9f7df; }
        .rec-badge.category { background: #eef6ff; color: #1b4f89; border-color: #cfe1fb; }
        .rec-badge.rating { background: #fff6e6; color: #8a5300; border-color: #ffe2ab; }
        .rec-badge.value { background: #f3eefe; color: #5a2f8a; border-color: #ded0fb; }
        .rec-rationale {
            border-left: 4px solid #1f76d2;
            background: #eff6ff;
            color: #143b66;
            border-radius: 8px;
            padding: 0.58rem 0.75rem;
            margin: 0.35rem 0;
        }
        .rec-caution {
            border-left: 4px solid #d97706;
            background: #fff7ea;
            color: #8a4b00;
            border-radius: 8px;
            padding: 0.58rem 0.75rem;
            margin: 0.35rem 0;
        }
        .rec-tip {
            border-left: 4px solid #0b8f6a;
            background: #ecfdf7;
            color: #0b684d;
            border-radius: 8px;
            padding: 0.58rem 0.75rem;
            margin: 0.35rem 0;
        }
        .rec-chips {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
            margin-top: 0.45rem;
        }
        .rec-chip {
            display: inline-block;
            border-radius: 999px;
            padding: 0.18rem 0.52rem;
            font-size: 0.73rem;
            font-weight: 600;
            border: 1px solid transparent;
        }
        .rec-chip.tag { background: #eaf4ff; color: #2d4e78; border-color: #d2e6ff; }
        .rec-chip.benefit { background: #eafcf3; color: #1e6848; border-color: #cdeedc; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _chips_html(items: list[str], chip_kind: str) -> str:
    return "".join(
        f'<span class="rec-chip {chip_kind}">{html.escape(item)}</span>'
        for item in items
        if item and item.strip()
    )


def _guidance_markdown(items: list[str]) -> str:
    points: list[str] = []
    for raw in items:
        text = str(raw or "").strip()
        if not text:
            continue
        if " - " in text and text.startswith("-"):
            text = text[1:].strip()
            parts = [part.strip(" .") for part in text.split(" - ") if part.strip(" .")]
            points.extend(parts)
        else:
            points.append(text.lstrip("-* ").strip())
    return "\n".join(f"- {point}" for point in points if point)


def _render_hero(settings: Settings) -> None:
    _inject_brand_styles()
    service_statuses = [
        ("OpenAI", settings.azure_openai_ready),
        ("Search", settings.azure_search_ready),
        ("Vision", settings.vision_ready),
        ("Speech", settings.speech_ready),
        ("Doc Intelligence", settings.document_intelligence_ready),
    ]
    status_pills = "".join(
        (
            f'<span class="brand-status-pill {"ready" if enabled else "offline"}">' 
            f'{html.escape(label)}: {"Ready" if enabled else "Offline"}</span>'
        )
        for label, enabled in service_statuses
    )
    st.markdown(
        (
            '<section class="brand-hero">'
            '<div class="brand-row">'
            f'<div class="brand-mark">{html.escape(_app_initials(settings.app_title))}</div>'
            '<div>'
            f'<h1 class="brand-title">{html.escape(settings.app_title)}</h1>'
            '</div>'
            '</div>'
            '<p class="brand-subtitle">'
            'Intelligent product recommendations powered by multimodal understanding and catalog-grounded retrieval.'
            '</p>'
            f'<div class="brand-statuses">{status_pills}</div>'
            '</section>'
        ),
        unsafe_allow_html=True,
    )

    st.divider()


def _render_recommendations(bundle) -> None:
    _inject_recommendation_styles()
    st.subheader("Recommendations")
    st.markdown(
        (
            f'<div class="rec-summary"><strong>Summary</strong><br/>{html.escape(bundle.summary)}<br/>'
            f'<span style="color:#4f6991; font-size:0.83rem;">Search mode: {html.escape(bundle.search_mode)}</span></div>'
        ),
        unsafe_allow_html=True,
    )

    if bundle.guidance:
        with st.container(border=True):
            st.markdown("**Guidance**")
            st.markdown(_guidance_markdown(bundle.guidance))

    if not bundle.recommendations:
        st.warning("No catalog-matched products could be verified for this request.")
        return

    for idx, rec in enumerate(bundle.recommendations, 1):
        product = rec.product
        rating_text = _rating_text(product.rating)
        tags_html = _chips_html(product.tags, "tag")
        benefits_html = _chips_html(product.benefits, "benefit")
        rec_html = [
            '<div class="rec-card">',
            '<div class="rec-header">',
            f'<h3 class="rec-title">{idx}. {html.escape(product.name)}</h3>',
            '</div>',
            f'<p class="rec-desc">{html.escape(product.description)}</p>',
            '<div class="rec-metrics">',
            f'<span class="rec-badge price">Price: ${product.price:,.2f}</span>',
            f'<span class="rec-badge category">Category: {html.escape(product.category)}</span>',
            f'<span class="rec-badge rating">Rating: {html.escape(rating_text)}</span>',
            f'<span class="rec-badge value">Value Score: {rec.value_score:.1f}/10</span>',
            '</div>',
            f'<div class="rec-rationale"><strong>Why it fits:</strong> {html.escape(rec.rationale)}</div>',
        ]
        if rec.caution:
            rec_html.append(f'<div class="rec-caution"><strong>Caution:</strong> {html.escape(rec.caution)}</div>')
        if rec.buying_tip:
            rec_html.append(f'<div class="rec-tip"><strong>Buying tip:</strong> {html.escape(rec.buying_tip)}</div>')
        if tags_html or benefits_html:
            rec_html.append('<div class="rec-chips">')
            rec_html.append(tags_html)
            rec_html.append(benefits_html)
            rec_html.append('</div>')
        rec_html.append('</div>')
        st.markdown("".join(rec_html), unsafe_allow_html=True)

    with st.expander("Processing trace", expanded=False):
        for step in bundle.trace:
            st.write(f"{step.agent_name} [{step.status}]")
            st.caption(step.detail)

    with st.expander("Extracted context", expanded=False):
        if bundle.transcript:
            st.markdown(f"**Speech transcript**: {bundle.transcript}")
        if bundle.document_insight:
            st.markdown(f"**Document summary**: {bundle.document_insight.summary}")
        if bundle.image_insight:
            st.markdown(f"**Image understanding**: {bundle.image_insight.description}")
            if bundle.image_insight.tags:
                st.caption(f"Image tags: {', '.join(bundle.image_insight.tags)}")


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

    _render_hero(settings)

    # Tabs
    customer_tab, admin_tab = st.tabs([
        "🛒  Customer Assistant",
        "⚙️  Admin Catalog",
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
                st.image(uploaded_image.getvalue(), caption="Uploaded image", use_container_width=True)
            else:
                st.caption("No image selected.")
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
                "Upload catalog file (CSV or JSON or PDF with tabular data)",
                type=["csv", "json","pdf"],
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

if __name__ == "__main__":
    main()
