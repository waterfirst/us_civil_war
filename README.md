# Financial Indices Dashboard (Streamlit)

A lightweight Streamlit dashboard that monitors key market indices (Gold, Silver, DXY, US10Y, BTC, SKEW, VIX), computes a heuristic “risk traffic light” for potential U.S. instability/market turbulence, and optionally provides qualitative interpretation via Google Gemini.

https://us-civil-war.streamlit.app/


## Features
- Live data via Yahoo Finance (yfinance)
- Simple risk traffic light from VIX/SKEW/DXY/US10Y/Gold/Silver/BTC
- Clean table view; manual refresh button
- Optional Gemini qualitative analysis (sidebar input for API key)

## Project Structure
- `streamlit_dashboard.py`: main app entry
- `requirements.txt`: dependencies

## Local Setup
```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows
pip install -r requirements.txt
streamlit run streamlit_dashboard.py
```

Open the app at `http://localhost:8501`.

## Streamlit Community Cloud Deployment
1. Push this repo to GitHub.
2. On Streamlit Community Cloud, create a new app:
   - Repository: your GitHub repo
   - Branch: main
   - File: `streamlit_dashboard.py`
3. Add a secret (optional) for Gemini:
   - In the app’s Settings → Secrets, add:
     ```toml
     google_api_key = "YOUR_GEMINI_API_KEY"
     ```
   - Or enter the key in the sidebar during runtime.

## Configuration
- Model selection in the sidebar. Default: `gemini-1.5-flash`. If unavailable, try `gemini-1.5-pro`, `gemini-1.5-flash-8b`, or `gemini-1.0-pro`.
- If you see 404 for a model, switch to another model.

## Notes
- Data is for informational purposes only; not investment or political advice.
- Yahoo Finance symbols used:
  - Gold: `GC=F` (XAU/USD)
  - Silver: `SI=F` (XAG/USD)
  - DXY: `DX-Y.NYB`
  - US10Y: `^TNX`
  - BTC: `BTC-USD`
  - SKEW: `^SKEW`
  - VIX: `^VIX`

## Troubleshooting
- If Gemini call is slow or errors (404):
  - Try another model from the dropdown
  - Ensure your API key has access to the selected model
  - Check package version: `pip install -U google-generativeai`
- If yfinance returns empty data, retry later (rate limits/market closed/temporary issues).
