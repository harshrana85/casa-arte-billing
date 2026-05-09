# Casa Arte Privée Billing System — Update & Navigation Fixed

## Login
Password: 1985

## Fixes
- Edit opens same PI/Invoice on entry page.
- Save / Update updates the same document instead of creating a new one.
- After Save / Update it returns to Saved Documents.
- Convert PI creates a new Invoice and opens it for packing/cost edits.
- Saving converted invoice updates that invoice, not a duplicate.
- Delete stays on Saved Documents list.

## Run
pip install -r requirements.txt
streamlit run app.py

## Streamlit Cloud
Upload all files to GitHub and reboot app.
Main file path: app.py
