# Casa Arte Privée Billing System — Word Import Packing List

## Fix
- Word import now detects Invoice files.
- If uploaded Word has a Packing List table, it imports packing rows.
- Imported packing rows include Box No, Part, Brand, Product Details, Length, Breadth, Height, CBM, GW, NW.
- If Invoice has no PL table, packing rows auto-generate from products.
- Imported Invoice opens in entry page with packing list loaded.

## Login
Password: 1985

## Run
pip install -r requirements.txt
streamlit run app.py
