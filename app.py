import json
import os
from typing import Any

import streamlit as st
from crewai import Agent, Crew, Process, Task
from pydantic import BaseModel, Field

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency at runtime
    load_dotenv = None

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI

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
        "Kurz, dynamisch, Hook in der ersten Zeile, leicht verständlich, aktivierende Sprache, "
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

BRANDS = {
    "Pflegebox": {
        "ton": "pragmatisch, verlässlich, entlastend, unkompliziert, sachlich",
        "ansprache": "formell aber nahbar ('Sie')",
        "keywords": ["#Pflegebox", "#Pflegehilfsmittel", "#PflegeZuHause", "#Entlastung"],
        "usp": "Kostenfreie Lieferung von Pflegehilfsmitteln, Übernahme des Papierkrams (§40 SGB XI)",
    },
    "Sanubi": {
        "ton": "professionell, kompetent, modern, lösungsorientiert, klinisch-sauber",
        "ansprache": "respektvoll auf Augenhöhe ('Sie')",
        "keywords": ["#Sanubi", "#Gesundheit", "#PflegeQualität", "#PremiumService"],
        "usp": "Ganzheitliches, hochwertiges Gesundheitserlebnis und smarte Lösungen für Pflegebedürftige",
    },
    "deinePflege": {
        "ton": "persönlich, empathisch, ermutigend, nahbar, Startup-Vibe, warm",
        "ansprache": "konsequentes, freundschaftliches ('Du')",
        "keywords": ["#deinePflege", "#PflegeDigital", "#GemeinsamStark", "#PflegeAlltag"],
        "usp": "Digitale Pflegeorganisation per App, Entbürokratisierung, Empowerment der Angehörigen",
    },
    "Pflege-durch-Angehörige": {
        "ton": "hochinformativ, aufklärend, schützend, mentor-haft, tiefgründig",
        "ansprache": "formell und respektvoll ('Sie')",
        "keywords": ["#PflegeDurchAngehörige", "#PflegeWissen", "#PflegeTipps", "#Pflegegrad"],
        "usp": "Tiefgreifendes Informationsportal, Insider-Wissen, rechtliche Aufklärung und Checklisten",
    },
}


class PostVariant(BaseModel):
    title: str = Field(..., description="Kurze Überschrift")
    body: str = Field(..., description="Post-Text mit 2-5 Sätzen")
    hashtags: list[str] = Field(default_factory=list)
    emojis: list[str] = Field(default_factory=list)
    cta: str = Field(..., description="Klare Handlungsaufforderung")


class PlatformPosts(BaseModel):
    platform_name: str
    variants: list[PostVariant]


class CrewOutput(BaseModel):
    results: list[PlatformPosts]


def get_api_keys() -> tuple[str, str]:
    openai_key = os.getenv("OPENAI_API_KEY", "")
    google_key = os.getenv("GOOGLE_API_KEY", "")

    if load_dotenv and (not openai_key or not google_key):
        load_dotenv()
        openai_key = openai_key or os.getenv("OPENAI_API_KEY", "")
        google_key = google_key or os.getenv("GOOGLE_API_KEY", "")

    if not openai_key:
        openai_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
    if not google_key:
        google_key = st.secrets.get("GOOGLE_API_KEY", "") if hasattr(st, "secrets") else ""

    return openai_key, google_key


def run_crewai_generation(
    thema: str,
    platformen: list[str],
    num_variants: int,
    brand_name: str,
    selected_model_name: str,
    openai_key: str,
    google_key: str,
) -> dict[str, Any]:
    if thema not in PFLEGETHEMEN:
        raise ValueError(f"Nicht unterstütztes Thema: {thema}")
    if brand_name not in BRANDS:
        raise ValueError(f"Nicht unterstützte Marke: {brand_name}")
    if not platformen:
        raise ValueError("Bitte mindestens eine Plattform auswählen.")

    unsupported = [platform for platform in platformen if platform not in PLATTFORMEN]
    if unsupported:
        raise ValueError(f"Nicht unterstützte Plattform(en): {', '.join(unsupported)}")

    if selected_model_name == "gpt-4o-mini":
        llm = ChatOpenAI(model="gpt-4o-mini", api_key=openai_key, temperature=0.7)
    elif selected_model_name == "gemini-1.5-flash":
        llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=google_key,
            temperature=0.7,
        )
    else:
        raise ValueError(f"Nicht unterstütztes Modell: {selected_model_name}")

    brand_info = BRANDS[brand_name]
    platform_guidelines = {name: PLATTFORMEN[name] for name in platformen}

    strategist = Agent(
        role="Brand & Topic Strategist",
        goal="Entwickle eine markenkonforme, empathische und fachlich saubere Content-Strategie.",
        backstory=(
            "Du bist Experte für Pflegekommunikation und Markenton. "
            "Du bereitest den Content-Brief für Social-Media-Teams vor."
        ),
        llm=llm,
        verbose=False,
    )

    legal_checker = Agent(
        role="SGB XI Legal Checker",
        goal="Prüfe Aussagen auf rechtliche Plausibilität und sichere Formulierungen.",
        backstory=(
            "Du kennst SGB XI Grundlagen, vermeidest rechtliche Übertreibungen "
            "und machst Inhalte compliant und verantwortungsvoll."
        ),
        llm=llm,
        verbose=False,
    )

    creator = Agent(
        role="Social Media Creator",
        goal="Erstelle plattformspezifische Post-Varianten in strikt strukturiertem JSON.",
        backstory=(
            "Du erstellst performante, empathische und markenkonforme Pflege-Posts mit klaren CTAs."
        ),
        llm=llm,
        verbose=False,
    )

    strategy_task = Task(
        description=(
            "Erstelle einen kompakten Marken- und Themenbriefingtext für die Content-Produktion.\n"
            f"Marke: {brand_name}\n"
            f"Brand-Details: {json.dumps(brand_info, ensure_ascii=False)}\n"
            f"Thema: {thema}\n"
            f"Faktenbasis: {PFLEGETHEMEN[thema]}\n"
            f"Plattformen: {', '.join(platformen)}\n"
            "Definiere Kernbotschaften, Tonalität, Do's/Don'ts, und Plattform-Fokus."
        ),
        expected_output="Ein präzises Briefing mit Kernbotschaften, Tonalität und Plattformhinweisen.",
        agent=strategist,
    )

    legal_task = Task(
        description=(
            "Prüfe das Briefing auf rechtliche Risiken und SGB XI Sensibilität. "
            "Formuliere sichere, klare Leitlinien (keine Rechtsberatung versprechen, keine absoluten Zusagen)."
        ),
        expected_output="Compliant-Leitlinien für die finale Content-Erstellung.",
        agent=legal_checker,
        context=[strategy_task],
    )

    final_description = (
        "Erzeuge finale Social-Media-Posts als STRICT JSON passend zu CrewOutput Schema.\n"
        f"Anzahl Varianten pro Plattform: {num_variants}\n"
        f"Plattform-Richtlinien: {json.dumps(platform_guidelines, ensure_ascii=False)}\n"
        f"Brand Keywords (nach Möglichkeit einbauen): {', '.join(brand_info['keywords'])}\n"
        "Antworte ausschließlich als valides JSON Objekt im CrewOutput-Format."
    )

    try:
        final_task = Task(
            description=final_description,
            expected_output="JSON gemäß CrewOutput mit results/platform_name/variants.",
            agent=creator,
            context=[strategy_task, legal_task],
            output_json=CrewOutput,
        )
    except TypeError:
        final_task = Task(
            description=final_description,
            expected_output="JSON gemäß CrewOutput mit results/platform_name/variants.",
            agent=creator,
            context=[strategy_task, legal_task],
            output_pydantic=CrewOutput,
        )

    crew = Crew(
        agents=[strategist, legal_checker, creator],
        tasks=[strategy_task, legal_task, final_task],
        process=Process.sequential,
        verbose=False,
    )

    try:
        kickoff_result = crew.kickoff()
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"CrewAI-Ausführung fehlgeschlagen: {exc}") from exc

    payload: Any = kickoff_result
    if hasattr(kickoff_result, "pydantic") and getattr(kickoff_result, "pydantic") is not None:
        payload = kickoff_result.pydantic
    elif hasattr(kickoff_result, "json_dict") and getattr(kickoff_result, "json_dict") is not None:
        payload = kickoff_result.json_dict
    elif hasattr(kickoff_result, "raw") and isinstance(kickoff_result.raw, str):
        payload = json.loads(kickoff_result.raw)

    if isinstance(payload, CrewOutput):
        return payload.model_dump()
    if isinstance(payload, dict):
        return CrewOutput.model_validate(payload).model_dump()
    if isinstance(payload, str):
        return CrewOutput.model_validate(json.loads(payload)).model_dump()

    raise RuntimeError("CrewAI lieferte kein verwertbares strukturiertes Ergebnis.")


def render_posts(data: dict[str, Any]) -> None:
    results = data.get("results", [])
    if not results:
        st.info("Noch keine Posts vorhanden.")
        return

    for platform_block in results:
        st.subheader(platform_block["platform_name"])
        for idx, variant in enumerate(platform_block.get("variants", []), start=1):
            with st.container(border=True):
                st.markdown(f"**Variante {idx}: {variant['title']}**")
                st.write(variant["body"])
                st.markdown(f"**Hashtags:** {' '.join(variant.get('hashtags', []))}")
                st.markdown(f"**Emojis:** {' '.join(variant.get('emojis', []))}")
                st.markdown(f"**CTA:** {variant.get('cta', '')}")


def main() -> None:
    st.set_page_config(page_title="Pflegepostapp", page_icon="🤖", layout="wide")
    st.title("🤖 Pflegepostapp · Multi-Agent Social Media Generator")

    if "generated_posts" not in st.session_state:
        st.session_state.generated_posts = None

    openai_key, google_key = get_api_keys()

    with st.sidebar:
        st.header("Konfiguration")
        selected_model_name = st.selectbox("KI-Modell", ["gpt-4o-mini", "gemini-1.5-flash"])
        brand_name = st.selectbox("Brand", options=list(BRANDS.keys()))
        thema = st.selectbox("Thema", options=list(PFLEGETHEMEN.keys()))
        platformen = st.multiselect("Plattformen", options=list(PLATTFORMEN.keys()), default=["Instagram"])
        num_variants = st.slider("Varianten pro Plattform", min_value=1, max_value=5, value=3)

    if selected_model_name == "gpt-4o-mini" and not openai_key:
        st.error("OPENAI_API_KEY fehlt. Bitte in Umgebungsvariablen oder Streamlit-Secrets setzen.")
        st.stop()

    if selected_model_name == "gemini-1.5-flash" and not google_key:
        st.error("GOOGLE_API_KEY fehlt. Bitte in Umgebungsvariablen oder Streamlit-Secrets setzen.")
        st.stop()

    if st.button("Posts generieren", type="primary"):
        with st.spinner("CrewAI erstellt Ihre Posts..."):
            try:
                result = run_crewai_generation(
                    thema=thema,
                    platformen=platformen,
                    num_variants=num_variants,
                    brand_name=brand_name,
                    selected_model_name=selected_model_name,
                    openai_key=openai_key,
                    google_key=google_key,
                )
                st.session_state.generated_posts = result
                st.success("Posts erfolgreich generiert.")
            except Exception as exc:  # noqa: BLE001
                st.error(str(exc))

    if st.session_state.generated_posts:
        render_posts(st.session_state.generated_posts)
        st.download_button(
            label="JSON herunterladen",
            data=json.dumps(st.session_state.generated_posts, ensure_ascii=False, indent=2),
            file_name="pflege_posts.json",
            mime="application/json",
        )


if __name__ == "__main__":
    main()
