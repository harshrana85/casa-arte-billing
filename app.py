
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Casa Arte Billing", layout="wide")

st.title("CASA ARTE PRIVÉE — Billing System")

doc_type = st.selectbox("Document Type", ["Proforma Invoice", "Invoice"])
currency = st.selectbox("Currency", ["EUR", "USD", "AED"])

st.subheader("Client Details")
col1, col2 = st.columns(2)

with col1:
    company = st.text_input("Company Name")
    reg = st.text_input("Registration Number")
    contact = st.text_input("Contact Person")

with col2:
    email = st.text_input("Email")
    phone = st.text_input("Phone")
    address = st.text_area("Billing Address")

same_ship = st.checkbox("Ship To same as Bill To", value=True)

if not same_ship:
    st.subheader("Shipping Details")
    ship_company = st.text_input("Shipping Company")
    ship_address = st.text_area("Shipping Address")

st.subheader("Products")

df = pd.DataFrame([
    {
        "Brand": "Paola Lenti",
        "Product Details": "Helico Coffee Table",
        "Size": "100 Dia x 33H",
        "Finish": "Majolica",
        "Qty": 1,
        "Rate": 2557.80
    }
])

edited_df = st.data_editor(df, num_rows="dynamic")

subtotal = (edited_df["Qty"] * edited_df["Rate"]).sum()

discount = st.number_input("Discount %", value=0.0)
shipping = st.number_input("Shipping Charges", value=0.0)

discount_amount = subtotal * (discount / 100)
grand_total = subtotal - discount_amount + shipping

st.subheader("Totals")
st.write(f"Subtotal: {currency} {subtotal:,.2f}")
st.write(f"Discount: {currency} {discount_amount:,.2f}")
st.write(f"Shipping: {currency} {shipping:,.2f}")
st.write(f"Grand Total: {currency} {grand_total:,.2f}")

st.subheader("Bank Details")

banks = {
    "EUR": [
        ("Mashreq Bank PSC UAE", "AE830330000019102080621"),
        ("WIO Bank PJSC", "AE830860000009168276489")
    ],
    "USD": [
        ("Mashreq Bank PSC UAE", "AE130330000019102080620"),
        ("WIO Bank PJSC", "AE480860000009878943739")
    ],
    "AED": [
        ("WIO Bank PJSC", "AE730860000009886170371")
    ]
}

for bank, iban in banks[currency]:
    st.info(f"{bank}\nIBAN: {iban}")

st.subheader("Terms & Conditions")
terms = st.text_area(
    "Editable Terms",
    "55% advance payment and 45% before dispatch."
)

if doc_type == "Invoice":
    st.subheader("Packing List")
    pack_df = pd.DataFrame({
        "Brand": edited_df["Brand"],
        "Product": edited_df["Product Details"],
        "Length": [0]*len(edited_df),
        "Breadth": [0]*len(edited_df),
        "Height": [0]*len(edited_df),
        "CBM": [0]*len(edited_df),
        "GW": [0]*len(edited_df),
        "NW": [0]*len(edited_df),
    })
    st.data_editor(pack_df, num_rows="dynamic")

st.success("Casa Arte Billing System Running")
