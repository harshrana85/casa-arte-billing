# Casa Arte Privée Billing System — PL Summary Override Fixed

## Fixes
- Blank/empty packing rows are ignored and not counted.
- Unnecessary blank row in PDF/Word removed.
- Split item into 2 boxes now counts correctly.
- Live packing summary updates on entry page.
- Manual override added for Total Boxes, Total CBM, Total GW, Total NW.
- PDF and Word use manual override if enabled.

## Login
Password: 1985

## Run
pip install -r requirements.txt
streamlit run app.py

## Streamlit Cloud
Upload all files to GitHub and reboot.
Main file: app.py
