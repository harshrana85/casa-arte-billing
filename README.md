# Casa Arte Privée Billing System — Final Revised

## Run
pip install -r requirements.txt
streamlit run app.py

## Login
Password: 1985

## Latest fixes
- Delete saved invoices/proformas
- Delete saved customers
- Edit selected document opens it back in entry page
- Convert Proforma to Invoice opens converted invoice immediately for packing/cost edits
- Stamp is darker and moved to bottom-right of every PDF page
- Shipping charges field works after ticking Add Shipping Charges

## Streamlit Deploy
Upload to GitHub, then deploy on Streamlit Cloud.
Main file: app.py

## Storage
Local JSON files:
- data/documents.json
- data/customers.json
- data/settings.json
