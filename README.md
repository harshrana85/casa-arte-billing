# Casa Arte Privée Billing System — Packing Split Persistence Fixed

## Fix in this version
- Split packing-list boxes/parts no longer disappear after rerun.
- Add/Split Box rows are stored in session immediately.
- Save/Update writes split boxes permanently into documents.json.
- Reopening the same invoice reloads saved split boxes.
- PDF and Word use saved split rows.

## Login
Password: 1985

## Run
pip install -r requirements.txt
streamlit run app.py

## Streamlit Cloud
Upload all files to GitHub and reboot.
Main file: app.py
