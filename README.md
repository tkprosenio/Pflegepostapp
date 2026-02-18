# Pflegepostapp

Pflegepostapp ist eine Streamlit-Anwendung zur **mehrstufigen (Multi-Agent) Erstellung von deutschsprachigen Social-Media-Posts** rund um Pflegethemen.
Die App nutzt CrewAI, Pydantic-Validierung und ein umschaltbares LLM-Backend für A/B-Tests von Tonalität und Empathie.

## Features

- **Multi-Agent Workflow mit CrewAI**
  - Brand & Topic Strategist
  - SGB XI Legal Checker
  - Social Media Creator
- **Dynamische Modellwahl in der UI**
  - `gpt-4o-mini` (OpenAI)
  - `gemini-1.5-flash` (Google)
- **Strukturierte Ausgaben mit Pydantic**
  - `PostVariant`
  - `PlatformPosts`
  - `CrewOutput`
- **Brand-spezifische Tonalität** über vordefinierte Brand-Profile.
- **Session-State-basierte Ergebnis-Persistenz** (`st.session_state.generated_posts`), damit UI-Interaktionen (z. B. Download) die Generierung nicht erneut starten.
- **JSON-Download** der generierten Ergebnisse.

## Tech Stack

- Python
- Streamlit
- CrewAI
- LangChain Provider-Integrationen:
  - `langchain-openai`
  - `langchain-google-genai`
- Pydantic
- python-dotenv

## Voraussetzungen

- Python 3.10+
- API-Zugriff auf mindestens **einen** Provider:
  - OpenAI für `gpt-4o-mini`
  - Google Generative AI für `gemini-1.5-flash`

## Installation

```bash
pip install -r requirements.txt
```

## Konfiguration der API-Keys

Die App liest API-Keys aus:

1. Umgebungsvariablen
2. optional `.env`
3. Streamlit Secrets (`st.secrets`)

### Lokal per `.env`

```env
OPENAI_API_KEY=...
GOOGLE_API_KEY=...
```

> Hinweis: In der Praxis muss nur der Key vorhanden sein, der zum gewählten Modell passt.

### Streamlit Cloud Secrets

```toml
OPENAI_API_KEY="..."
GOOGLE_API_KEY="..."
```

## App starten

```bash
streamlit run app.py
```

## Nutzung

1. In der Sidebar Modell wählen (`gpt-4o-mini` oder `gemini-1.5-flash`).
2. Brand auswählen.
3. Thema, Plattformen und Variantenanzahl festlegen.
4. **Posts generieren** klicken.
5. Ergebnisse ansehen und als JSON herunterladen.

## Ausgabeformat (vereinfacht)

```json
{
  "results": [
    {
      "platform_name": "Instagram",
      "variants": [
        {
          "title": "...",
          "body": "...",
          "hashtags": ["#..."],
          "emojis": ["💙"],
          "cta": "..."
        }
      ]
    }
  ]
}
```

## Troubleshooting

- **`OPENAI_API_KEY fehlt`**
  - Modell `gpt-4o-mini` ist ausgewählt, aber OpenAI-Key fehlt.

- **`GOOGLE_API_KEY fehlt`**
  - Modell `gemini-1.5-flash` ist ausgewählt, aber Google-Key fehlt.

- **`ModuleNotFoundError: No module named 'crewai'`**
  - Abhängigkeiten neu installieren:
    ```bash
    pip install -r requirements.txt
    ```

## Projektstruktur

- `app.py` – Streamlit UI, CrewAI Orchestrierung, Pydantic Output-Verarbeitung
- `requirements.txt` – Laufzeitabhängigkeiten
- `README.md` – Projektdokumentation
