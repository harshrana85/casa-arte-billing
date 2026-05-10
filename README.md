# Casa Arte Privée Billing System — Word Import CBM Fixed

## Fix
- CBM is now imported directly from Word Packing List CBM column.
- Supports headers like CBM, C.B.M, Cubic, m3, m³.
- Imported CBM is not overwritten by automatic L × B × H calculation.
- If Word CBM is blank, app calculates CBM from dimensions.

## Login
Password: 1985

## Run
pip install -r requirements.txt
streamlit run app.py
