# NSE AI Stock Scanner V1

Browser-based Streamlit app that scans NSE equities using Upstox 1-minute candles.

## Run
pip install -r requirements.txt
streamlit run app.py

## Browser deployment
Upload `app.py` and `requirements.txt` to GitHub, then deploy with Streamlit Community Cloud. It gives a `https://<your-app>.streamlit.app` URL.

## Upstox
Create an Upstox developer app and generate an access token. V1 asks for the token in the browser and does not store it. Upstox tokens expire at 3:30 AM the following day.

## Important
V1 limits the number of instruments scanned. A production version should use a defined universe such as NIFTY 500, caching/batching, rate-limit handling, and OAuth.

## Roadmap
V2: NIFTY 50/100/500, VWAP, RSI, MACD, relative volume, breakout/reversal.
V3: natural-language AI agent and news analysis.
V4: scheduled scans and Telegram/email alerts.
