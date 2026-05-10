# Casa Arte Privée Billing System — Packing CBM Column Fixed

## Fix
- CBM column is visible in Packing List entry.
- CBM can be manually entered/edited.
- If CBM is zero, app auto-suggests L × B × H / 1,000,000.
- Packing summary automatically totals the CBM column.
- GW/NW and total boxes continue to calculate in summary.

## Login
Password: 1985

## Run
pip install -r requirements.txt
streamlit run app.py
