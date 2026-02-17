# Pflegepostapp

## Zweck
Die Pflegepostapp unterstützt dabei, **deutschsprachige Social-Media-Postings** für Pflegethemen (z. B. Demenz, Sturzprophylaxe, pflegende Angehörige) zu erstellen.
Die App nutzt Streamlit für die Oberfläche und OpenAI für die Textgenerierung.

Start der App lokal:

```bash
streamlit run app.py
```

## Lokales Setup
1. Python-Umgebung aktivieren (optional, aber empfohlen).
2. Abhängigkeiten installieren:

```bash
pip install -r requirements.txt
```

3. API-Key setzen.
   - Optional über eine `.env` im Projektverzeichnis:

```env
OPENAI_API_KEY=...
```

   - Alternativ direkt als Umgebungsvariable im Terminal setzen.

## Streamlit Cloud Setup
Wenn die App auf Streamlit Cloud läuft, den API-Key in den Secrets hinterlegen:

1. **Manage app** öffnen.
2. **Secrets** auswählen.
3. Folgenden Eintrag speichern:

```toml
OPENAI_API_KEY="..."
```

## Troubleshooting
- **Fehler: `OPENAI_API_KEY fehlt`**  
  Prüfen, ob der Key lokal als Umgebungsvariable oder in `.env` gesetzt ist.

- **Deployment funktioniert lokal, aber nicht in Streamlit Cloud (oder umgekehrt)**  
  Meist liegt ein Umgebungs-Mismatch vor (lokale `.env` vs. Cloud-Secrets). Sicherstellen, dass in der jeweiligen Laufumgebung `OPENAI_API_KEY` korrekt gesetzt ist.
