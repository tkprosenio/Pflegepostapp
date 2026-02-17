import json
import os
import re
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

PFLEGETHEMEN: dict[str, str] = {
    "Demenz": (
        "Demenz verändert Gedächtnis, Orientierung und Verhalten. Ruhige Kommunikation, klare Tagesstrukturen, "
        "Validation und Sicherheit im Alltag sind zentrale Bausteine in der Betreuung."
    ),
    "Sturzprophylaxe": (
        "Stürze lassen sich durch Kraft- und Gleichgewichtstraining, sichere Wohnumgebung, passende Hilfsmittel "
        "und regelmäßige Medikationsprüfung oft reduzieren."
    ),
    "Pflegende Angehörige": (
        "Pflegende Angehörige tragen hohe Verantwortung. Entlastungsangebote, Selbstfürsorge, Pausen und "
        "frühe Beratung helfen, Überlastung vorzubeugen."
    ),
    "Dekubitusprävention": (
        "Druckentlastung, regelmäßige Lagewechsel, Hautbeobachtung, Mobilisation und ausreichende Ernährung "
        "sind wichtige Elemente zur Vorbeugung von Dekubitus."
    ),
    "Flüssigkeitsmanagement": (
        "Ausreichende Flüssigkeitszufuhr unterstützt Kreislauf, Kognition und Allgemeinzustand. Trinkpläne, "
        "geeignete Getränke und Beobachtung von Warnzeichen sind praxisrelevant."
    ),
}

PLATTFORMEN: dict[str, str] = {
    "TikTok": (
        "Kurz, dynamisch, hook in der ersten Zeile, leicht verständlich, aktivierende Sprache, "
        "praxisnahe Tipps, trendige aber seriöse Ansprache."
    ),
    "Instagram": (
        "Emotional, community-orientiert, visuell denkend, klarer Mehrwert pro Slide/Caption, "
        "freundlich und inspirierend."
    ),
    "Facebook": (
        "Etwas ausführlicher, erklärend, nahbar und vertrauenswürdig, mit klaren Alltagsbeispielen "
        "und Gesprächsanstoß für Kommentare."
    ),
}

PLATFORM_ORDER: tuple[str, ...] = ("TikTok", "Instagram", "Facebook")

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


def _split_csv_like(value: str) -> list[str]:
    parts = [part.strip() for part in re.split(r"[,;|]", value) if part.strip()]
    if parts:
        return parts
    return [token for token in value.split() if token.strip()]


def _normalize_hashtags(value: str) -> list[str]:
    tags = _split_csv_like(value)
    normalized: list[str] = []
    seen: set[str] = set()
    for tag in tags:
        clean = tag.strip()
        if not clean:
            continue
        token = re.sub(r"^#+", "", clean).strip()
        token = re.sub(r"[\s,;|]+", "", token)
        if not token or not re.search(r"\w", token):
            continue

        normalized_tag = f"#{token}"
        if normalized_tag in seen:
            continue
        seen.add(normalized_tag)
        normalized.append(normalized_tag)
    return normalized


def _normalize_emojis(value: str) -> list[str]:
    return _split_csv_like(value)


def _extract_prefixed_value(block: str, prefix: str) -> str:
    pattern = re.compile(rf"^{re.escape(prefix)}\s*(.+)$", flags=re.IGNORECASE | re.MULTILINE)
    match = pattern.search(block)
    if match:
        return match.group(1).strip()

    for line in block.splitlines():
        normalized = line.strip()
        if normalized.lower().startswith(prefix.lower().rstrip(":")):
            return normalized.split(":", 1)[1].strip() if ":" in normalized else ""
    return ""


def _parse_variant_block(block: str, platform: str, thema: str, variant_index: int) -> dict[str, Any]:
    cleaned = block.strip()
    title = _extract_prefixed_value(cleaned, "Title:")
    body = _extract_prefixed_value(cleaned, "Body:")
    hashtags_raw = _extract_prefixed_value(cleaned, "Hashtags:")
    emojis_raw = _extract_prefixed_value(cleaned, "Emojis:")
    cta = _extract_prefixed_value(cleaned, "CTA:")

    if not body:
        lines = [line.strip() for line in cleaned.splitlines() if line.strip()]
        if len(lines) > 1:
            body = "\n".join(lines[1:])
        elif lines:
            body = lines[0]

    return {
        "platform": platform,
        "title": title,
        "body": body,
        "hashtags": _normalize_hashtags(hashtags_raw),
        "emojis": _normalize_emojis(emojis_raw),
        "cta": cta,
        "topic": thema,
        "variant_index": variant_index,
    }


def _build_prompt(thema: str, platform: str, num: int) -> str:
    themen_fakten = PFLEGETHEMEN[thema]
    style = PLATTFORMEN[platform]
    return (
        "Erstelle deutschsprachige Social-Media-Posts mit fachlich korrekter, alltagstauglicher Pflegekommunikation.\n"
        f"Thema: {thema}\n"
        f"Faktenbasis: {themen_fakten}\n"
        f"Plattform: {platform}\n"
        f"Stil: {style}\n\n"
        f"Erzeuge exakt {num} Varianten.\n"
        "WICHTIG: Gib ausschließlich Blöcke in folgendem Format aus, Blöcke jeweils mit --- trennen:\n"
        "Title: <kurze Überschrift>\n"
        "Body: <2-5 Sätze>\n"
        "Hashtags: <durch Komma getrennt, mit #>\n"
        "Emojis: <passende Emojis, durch Komma getrennt>\n"
        "CTA: <klare Handlungsaufforderung>\n"
    )


def generate_post(thema: str, platformen: list[str], num: int) -> dict[str, Any]:
    if thema not in PFLEGETHEMEN:
        return {"error": f"Nicht unterstütztes Thema: {thema}"}

    if not platformen:
        return {"error": "Bitte mindestens eine Plattform auswählen."}

    unsupported = [platform for platform in platformen if platform not in PLATTFORMEN]
    if unsupported:
        return {"error": f"Nicht unterstützte Plattform(en): {', '.join(unsupported)}"}

    if not OPENAI_API_KEY:
        return {"error": "OPENAI_API_KEY fehlt. Bitte in der Umgebung setzen."}

    clamped_num = max(3, min(5, num))
    selected_in_order = [platform for platform in PLATFORM_ORDER if platform in set(platformen)]

    client = OpenAI()
    posts: list[dict[str, Any]] = []

    for platform in selected_in_order:
        prompt = _build_prompt(thema=thema, platform=platform, num=clamped_num)
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Du bist ein erfahrener Content-Redakteur für Pflegekommunikation.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.8,
        )

        response_text = completion.choices[0].message.content or ""
        blocks = [block.strip() for block in response_text.split("---") if block.strip()]

        for variant_index, block in enumerate(blocks[:clamped_num]):
            posts.append(
                _parse_variant_block(
                    block=block,
                    platform=platform,
                    thema=thema,
                    variant_index=variant_index,
                )
            )

    return {"posts": posts}


def main() -> None:
    st.title("🤖 Pflege-Post Generator")

    if not OPENAI_API_KEY:
        st.error("OPENAI_API_KEY fehlt. Bitte Umgebungsvariable setzen, dann die Seite neu laden.")

    thema = st.selectbox("Pflege-Thema", options=list(PFLEGETHEMEN.keys()))
    platformen = st.multiselect("Plattformen", options=list(PLATTFORMEN.keys()))
    num = st.slider("Anzahl Varianten pro Plattform", min_value=3, max_value=5, value=3)

    if st.button("Posts generieren"):
        if not OPENAI_API_KEY:
            st.error("Generierung übersprungen: OPENAI_API_KEY fehlt.")
            return

        result = generate_post(thema=thema, platformen=platformen, num=num)
        if "error" in result:
            st.error(result["error"])
            return

        for post in result["posts"]:
            st.subheader(f"{post['platform']} · Variante {post['variant_index'] + 1}")
            st.markdown(f"**Thema:** {post['topic']}")
            st.markdown(f"**Title:** {post['title']}")
            st.markdown(f"**Body:**\n{post['body']}")
            st.markdown(f"**Hashtags:** {' '.join(post['hashtags'])}")
            st.markdown(f"**Emojis:** {' '.join(post['emojis'])}")
            st.markdown(f"**CTA:** {post['cta']}")
            st.divider()

        st.json(result)
        st.download_button(
            label="JSON herunterladen",
            data=json.dumps(result, ensure_ascii=False, indent=2),
            file_name="pflege_posts.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
