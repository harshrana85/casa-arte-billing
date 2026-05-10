# Casa Arte Privée Billing System — Word Import CBM Root Fixed

## Fix
- Imported Word CBM is no longer overwritten by packing initializer.
- App's own Word PL export is imported by exact column positions:
  SL, Box No, Part, Brand, Product Details, Length, Breadth, Height, CBM, GW, NW.
- Single-letter dimension matching fixed so Length does not accidentally read SL.
- CBM imported from Word now stays visible in rows and summary.

## Login
Password: 1985

## Run
pip install -r requirements.txt
streamlit run app.py
