# Casa Arte Privée Billing System — Word PL Roundtrip Fixed

## Fix
- Word download now exports Packing List with separate CBM, GW, and NW columns.
- No packing row data should go missing in Word.
- Uploading the Word file back now imports packing data correctly.
- CBM values are imported and preserved.
- Packing summary continues to total CBM/GW/NW/Boxes.

## Login
Password: 1985

## Run
pip install -r requirements.txt
streamlit run app.py
