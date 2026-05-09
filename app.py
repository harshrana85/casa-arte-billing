
import streamlit as st
import pandas as pd
import json, uuid, os, base64
from pathlib import Path
from datetime import date, datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfbase import pdfmetrics

APP_DIR = Path(__file__).parent
DATA_DIR = APP_DIR / "data"
ASSETS_DIR = APP_DIR / "assets"
CUSTOMERS_FILE = DATA_DIR / "customers.json"
DOCUMENTS_FILE = DATA_DIR / "documents.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
LOGO_PATH = ASSETS_DIR / "logo.png"
STAMP_PATH = ASSETS_DIR / "stamp.png"

DATA_DIR.mkdir(exist_ok=True)
ASSETS_DIR.mkdir(exist_ok=True)

COMPANY = {
    "name": "CASA ARTE PRIVEE FZ-LLC",
    "address": "AL Hulaila Industrial Zone-FZ, Ras Al Khaimah, United Arab Emirates",
    "license": "LICENCE NO. 5038159",
    "phone": "+393333920771 / +971585911456",
    "email": "casaartepriveefze@artedicasaae.co",
}

BANKS = {
    "EUR": [
        {
            "Bank Name": "MASHREQ BANK PSC UAE",
            "Currency": "EUR",
            "IBAN": "AE830330000019102080621",
            "SWIFT/BIC": "BOMLAEADXXX",
            "Bank Address": "Umniyati Street, Burj Khalifa Community, Dubai, UAE. Postal Address: P.O. Box 1250, Dubai, UAE.",
        },
        {
            "Bank Name": "WIO BANK PJSC",
            "Currency": "EUR",
            "IBAN": "AE830860000009168276489",
            "SWIFT/BIC": "WIOBAEADXXX",
            "Bank Address": "Etihad Airways Centre, 5th Floor, Abu Dhabi, UAE.",
        },
    ],
    "USD": [
        {
            "Bank Name": "MASHREQ BANK PSC UAE",
            "Currency": "USD",
            "IBAN": "AE130330000019102080620",
            "SWIFT/BIC": "BOMLAEADXXX",
            "Bank Address": "Umniyati Street, Burj Khalifa Community, Dubai, UAE. Postal Address: P.O. Box 1250, Dubai, UAE.",
        },
        {
            "Bank Name": "WIO BANK PJSC",
            "Currency": "USD",
            "IBAN": "AE480860000009878943739",
            "SWIFT/BIC": "WIOBAEADXXX",
            "Bank Address": "Etihad Airways Centre, 5th Floor, Abu Dhabi, UAE.",
        },
    ],
    "AED": [
        {
            "Bank Name": "WIO BANK PJSC",
            "Currency": "AED",
            "IBAN": "AE730860000009886170371",
            "SWIFT/BIC": "WIOBAEADXXX",
            "Bank Address": "Etihad Airways Centre, 5th Floor, Abu Dhabi, UAE.",
        }
    ],
}

DEFAULT_PRODUCT_COLUMNS = ["Brand", "Product Details", "Size", "Finish", "Qty", "Rate Per Piece"]
DEFAULT_PACKING_COLUMNS = ["Brand", "Product Details", "Length", "Breadth", "Height", "CBM", "GW", "NW"]

def load_json(path, default):
    if not path.exists():
        path.write_text(json.dumps(default, indent=2))
        return default
    try:
        return json.loads(path.read_text())
    except Exception:
        return default

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

def img_base64(path):
    if path.exists():
        return base64.b64encode(path.read_bytes()).decode()
    return ""

def money(value, currency):
    symbol = {"EUR":"€", "USD":"$", "AED":"AED"}.get(currency, currency)
    return f"{symbol} {float(value or 0):,.2f}"

def next_number(doc_type, docs):
    prefix = "CAP/PI" if doc_type == "Proforma Invoice" else "CAP/INV"
    year = datetime.now().year
    same = [d for d in docs if str(d.get("number","")).startswith(f"{prefix}/{year}")]
    return f"{prefix}/{year}/{len(same)+1:04d}"

def calc_totals(products, currency, discount_type, discount_value, shipping_enabled, shipping_cost):
    df = pd.DataFrame(products)
    if df.empty:
        subtotal = 0.0
    else:
        df["Qty"] = pd.to_numeric(df.get("Qty", 0), errors="coerce").fillna(0)
        df["Rate Per Piece"] = pd.to_numeric(df.get("Rate Per Piece", 0), errors="coerce").fillna(0)
        subtotal = float((df["Qty"] * df["Rate Per Piece"]).sum())
    if discount_type == "Percentage":
        discount_amount = subtotal * (float(discount_value or 0) / 100)
    else:
        discount_amount = float(discount_value or 0)
    shipping = float(shipping_cost or 0) if shipping_enabled else 0.0
    total = subtotal - discount_amount + shipping
    return subtotal, discount_amount, shipping, total

def ensure_pack(products, existing=None):
    existing = existing or []
    rows = []
    for i, p in enumerate(products):
        ex = existing[i] if i < len(existing) else {}
        length = float(ex.get("Length", 0) or 0)
        breadth = float(ex.get("Breadth", 0) or 0)
        height = float(ex.get("Height", 0) or 0)
        qty = float(p.get("Qty", 1) or 1)
        cbm = (length * breadth * height * qty) / 1000000
        rows.append({
            "Brand": p.get("Brand", ""),
            "Product Details": p.get("Product Details", ""),
            "Length": length,
            "Breadth": breadth,
            "Height": height,
            "CBM": round(cbm, 3),
            "GW": float(ex.get("GW", 0) or 0),
            "NW": float(ex.get("NW", 0) or 0),
        })
    return rows

def pdf_document(doc):
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=12*mm, leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=8, leading=10))
    styles.add(ParagraphStyle(name="GoldTitle", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#9b763c"), leading=22))
    styles.add(ParagraphStyle(name="Navy", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#071c2e")))
    story = []
    if LOGO_PATH.exists():
        story.append(Image(str(LOGO_PATH), width=38*mm, height=22*mm))
    story.append(Paragraph(COMPANY["name"], styles["GoldTitle"]))
    story.append(Paragraph(f'{COMPANY["address"]}<br/>{COMPANY["license"]}<br/>{COMPANY["phone"]}<br/>{COMPANY["email"]}', styles["Small"]))
    story.append(Spacer(1, 6))
    story.append(Paragraph(doc["type"].upper(), styles["Navy"]))
    story.append(Paragraph(f'No: {doc["number"]} &nbsp;&nbsp; Date: {doc["date"]} &nbsp;&nbsp; Currency: {doc["currency"]}', styles["Small"]))
    story.append(Spacer(1, 8))
    bill = doc.get("bill_to", {})
    ship = doc.get("ship_to", {})
    bill_text = "<br/>".join([f"<b>{bill.get('Company Name','')}</b>", bill.get("Registration Number",""), bill.get("GST/VAT",""), bill.get("Contact Person",""), bill.get("Phone",""), bill.get("Email",""), bill.get("Address",""), bill.get("Country","")])
    ship_text = "Same as Bill To" if doc.get("ship_same") else "<br/>".join([ship.get("Company Name",""), ship.get("Contact Person",""), ship.get("Phone",""), ship.get("Email",""), ship.get("Address",""), ship.get("Country","")])
    t = Table([[Paragraph("<b>BILL TO</b><br/>"+bill_text, styles["Small"]), Paragraph("<b>SHIP TO</b><br/>"+ship_text, styles["Small"])]], colWidths=[85*mm,85*mm])
    t.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#c9b083")),("VALIGN",(0,0),(-1,-1),"TOP"),("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#faf7f1"))]))
    story.append(t); story.append(Spacer(1,8))
    data = [["SL","Brand","Product Details","Size","Finish","Qty","Rate","Amount"]]
    for idx,p in enumerate(doc["products"],1):
        qty = float(p.get("Qty",0) or 0); rate = float(p.get("Rate Per Piece",0) or 0)
        data.append([idx, p.get("Brand",""), Paragraph(p.get("Product Details",""), styles["Small"]), p.get("Size",""), Paragraph(p.get("Finish",""), styles["Small"]), qty, money(rate, doc["currency"]), money(qty*rate, doc["currency"])])
    table = Table(data, repeatRows=1, colWidths=[9*mm,24*mm,42*mm,26*mm,35*mm,11*mm,22*mm,25*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#071c2e")), ("TEXTCOLOR",(0,0),(-1,0),colors.white),
        ("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"), ("FONTSIZE",(0,0),(-1,-1),7),
        ("GRID",(0,0),(-1,-1),0.25,colors.HexColor("#bfbfbf")), ("VALIGN",(0,0),(-1,-1),"TOP")
    ]))
    story.append(table); story.append(Spacer(1,8))
    subtotal, discount_amount, shipping, total = calc_totals(doc["products"], doc["currency"], doc["discount_type"], doc["discount_value"], doc["shipping_enabled"], doc["shipping_cost"])
    totals = [["Subtotal", money(subtotal, doc["currency"])], ["Discount", f"- {money(discount_amount, doc['currency'])}"], ["Shipping", money(shipping, doc["currency"])], ["Grand Total", money(total, doc["currency"])]]
    tt = Table(totals, colWidths=[40*mm,40*mm], hAlign="RIGHT")
    tt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,3),(-1,3),colors.HexColor("#071c2e")),("TEXTCOLOR",(0,3),(-1,3),colors.white),("FONTNAME",(0,3),(-1,3),"Helvetica-Bold")]))
    story.append(tt); story.append(Spacer(1,8))
    story.append(Paragraph("<b>BANK DETAILS</b>", styles["Navy"]))
    bank_rows = [["Bank Name","Currency","IBAN","SWIFT/BIC","Bank Address"]]
    for b in BANKS[doc["currency"]]:
        bank_rows.append([b["Bank Name"], b["Currency"], b["IBAN"], b["SWIFT/BIC"], Paragraph(b["Bank Address"], styles["Small"])])
    bt = Table(bank_rows, repeatRows=1, colWidths=[38*mm,16*mm,45*mm,25*mm,55*mm])
    bt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#9b763c")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.grey),("FONTSIZE",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(bt)
    story.append(PageBreak())
    story.append(Paragraph("TERMS & CONDITIONS", styles["GoldTitle"]))
    for para in str(doc.get("terms","")).split("\n"):
        if para.strip():
            story.append(Paragraph(para.strip(), styles["Small"]))
            story.append(Spacer(1,2))
    if doc["type"] == "Invoice":
        story.append(PageBreak())
        story.append(Paragraph("PACKING LIST", styles["GoldTitle"]))
        pack = ensure_pack(doc["products"], doc.get("packing", []))
        rows = [["SL","Brand","Product Details","L","B","H","CBM","GW","NW"]]
        for idx,p in enumerate(pack,1):
            rows.append([idx,p["Brand"],Paragraph(p["Product Details"],styles["Small"]),p["Length"],p["Breadth"],p["Height"],p["CBM"],p["GW"],p["NW"]])
        pt = Table(rows, repeatRows=1, colWidths=[9*mm,28*mm,58*mm,14*mm,14*mm,14*mm,18*mm,18*mm,18*mm])
        pt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#071c2e")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.grey),("FONTSIZE",(0,0),(-1,-1),7),("VALIGN",(0,0),(-1,-1),"TOP")]))
        story.append(pt)
        story.append(Spacer(1,8))
        story.append(Paragraph(f"<b>Total CBM:</b> {sum(float(x.get('CBM',0) or 0) for x in pack):.3f} &nbsp;&nbsp; <b>Total GW:</b> {sum(float(x.get('GW',0) or 0) for x in pack):.2f} KG &nbsp;&nbsp; <b>Total NW:</b> {sum(float(x.get('NW',0) or 0) for x in pack):.2f} KG", styles["Navy"]))
    pdf.build(story)
    return buffer.getvalue()

st.set_page_config(page_title="Casa Arte Privée Billing", layout="wide")

st.markdown("""
<style>
.stApp { background: #f7f3ec; }
.block-container { padding-top: 1.2rem; max-width: 1500px; }
.cap-header { background:#071c2e; padding:22px 28px; border-radius:22px; color:white; box-shadow:0 12px 30px rgba(0,0,0,.16); margin-bottom:18px; }
.cap-title { color:#d0aa65; font-size:34px; font-family: Georgia, serif; letter-spacing:1px; margin:0; }
.cap-sub { letter-spacing:5px; font-size:11px; color:#f1eee8; margin:0; }
.card { background:white; border-radius:18px; padding:18px; border:1px solid #eadfcd; box-shadow:0 8px 24px rgba(7,28,46,.06); margin-bottom:16px; }
.section-title { color:#071c2e; font-family: Georgia, serif; font-size:24px; border-bottom:2px solid #d0aa65; padding-bottom:8px; margin-bottom:12px; }
.gold { color:#9b763c; }
.small-note { font-size:12px; color:#6b7280; }
div[data-testid="stMetricValue"] { color:#9b763c; }
</style>
""", unsafe_allow_html=True)

logo_b64 = img_base64(LOGO_PATH)
logo_html = f'<img src="data:image/png;base64,{logo_b64}" style="height:82px;object-fit:contain;margin-right:18px;">' if logo_b64 else '<div style="height:74px;width:74px;border:1px solid #d0aa65;border-radius:18px;display:flex;align-items:center;justify-content:center;color:#d0aa65;font-size:34px;font-family:Georgia;">A</div>'
st.markdown(f"""
<div class="cap-header">
  <div style="display:flex;align-items:center;gap:18px;">
    {logo_html}
    <div>
      <h1 class="cap-title">CASA ARTE PRIVÉE</h1>
      <p class="cap-sub">BILLING · PROFORMA · INVOICE · PACKING LIST</p>
    </div>
  </div>
</div>
""", unsafe_allow_html=True)

customers = load_json(CUSTOMERS_FILE, [])
documents = load_json(DOCUMENTS_FILE, [])
settings = load_json(SETTINGS_FILE, {"terms": ""})

if "edit_doc_id" not in st.session_state: st.session_state.edit_doc_id = None
if "loaded_customer" not in st.session_state: st.session_state.loaded_customer = {}

tab_create, tab_saved, tab_customers, tab_settings = st.tabs(["Create / Edit Document", "Saved Proformas & Invoices", "Customer Database", "Settings"])

with tab_create:
    editing_doc = None
    if st.session_state.edit_doc_id:
        editing_doc = next((d for d in documents if d["id"] == st.session_state.edit_doc_id), None)

    c1, c2, c3, c4 = st.columns([1.2,1,1,1])
    with c1:
        doc_type = st.selectbox("Document Type", ["Proforma Invoice", "Invoice"], index=(1 if editing_doc and editing_doc["type"]=="Invoice" else 0))
    with c2:
        currency = st.selectbox("Currency", ["EUR","USD","AED"], index=(["EUR","USD","AED"].index(editing_doc.get("currency","EUR")) if editing_doc else 0))
    with c3:
        doc_date = st.date_input("Date", value=datetime.strptime(editing_doc.get("date"), "%Y-%m-%d").date() if editing_doc and editing_doc.get("date") else date.today())
    with c4:
        number = st.text_input("Document No.", value=editing_doc.get("number") if editing_doc else next_number(doc_type, documents))

    st.markdown('<div class="card"><div class="section-title">Customer & Shipping Details</div>', unsafe_allow_html=True)
    customer_names = ["-- New Customer --"] + [c.get("Company Name","") for c in customers]
    selected_customer = st.selectbox("Select existing customer to auto-fill", customer_names)
    selected_data = {}
    if selected_customer != "-- New Customer --":
        selected_data = next((c for c in customers if c.get("Company Name")==selected_customer), {})

    bill_existing = editing_doc.get("bill_to", {}) if editing_doc else selected_data
    colA, colB = st.columns(2)
    with colA:
        st.markdown("**BILL TO**")
        bill_company = st.text_input("Company Name", value=bill_existing.get("Company Name",""))
        bill_reg = st.text_input("Company Registration Number", value=bill_existing.get("Registration Number",""))
        bill_tax = st.text_input("GST / VAT Number", value=bill_existing.get("GST/VAT",""))
        bill_contact = st.text_input("Contact Person", value=bill_existing.get("Contact Person",""))
    with colB:
        bill_phone = st.text_input("Phone", value=bill_existing.get("Phone",""))
        bill_email = st.text_input("Email", value=bill_existing.get("Email",""))
        bill_country = st.text_input("Country", value=bill_existing.get("Country",""))
        bill_address = st.text_area("Billing Address", value=bill_existing.get("Address",""), height=105)

    ship_same = st.checkbox("Ship To same as Bill To", value=editing_doc.get("ship_same", True) if editing_doc else True)
    ship_to = {}
    if not ship_same:
        ship_existing = editing_doc.get("ship_to", {}) if editing_doc else selected_data.get("ship_to", {})
        s1, s2 = st.columns(2)
        with s1:
            st.markdown("**SHIP TO**")
            ship_to["Company Name"] = st.text_input("Shipping Company Name", value=ship_existing.get("Company Name",""))
            ship_to["Contact Person"] = st.text_input("Shipping Contact Person", value=ship_existing.get("Contact Person",""))
            ship_to["Phone"] = st.text_input("Shipping Phone", value=ship_existing.get("Phone",""))
        with s2:
            ship_to["Email"] = st.text_input("Shipping Email", value=ship_existing.get("Email",""))
            ship_to["Country"] = st.text_input("Shipping Country", value=ship_existing.get("Country",""))
            ship_to["Address"] = st.text_area("Shipping Address", value=ship_existing.get("Address",""), height=105)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="section-title">Products</div>', unsafe_allow_html=True)
    products_init = editing_doc.get("products") if editing_doc else [
        {"Brand":"Paola Lenti","Product Details":"Helico Coffee Table B237A","Size":"100 Dia x 33H cm","Finish":"Structure: Majolica CER 826. Top: Transparent Fusion Glass.","Qty":1,"Rate Per Piece":2557.80},
    ]
    product_df = pd.DataFrame(products_init)
    for col in DEFAULT_PRODUCT_COLUMNS:
        if col not in product_df.columns: product_df[col] = "" if col not in ["Qty","Rate Per Piece"] else 0
    product_df = product_df[DEFAULT_PRODUCT_COLUMNS]
    edited_products = st.data_editor(product_df, num_rows="dynamic", use_container_width=True, key=f"products_{st.session_state.edit_doc_id or 'new'}")
    products = edited_products.to_dict("records")
    st.caption("For 100+ products, keep adding rows. PDF export repeats headers and continues over multiple pages.")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="section-title">Discount, Shipping & Totals</div>', unsafe_allow_html=True)
    t1,t2,t3,t4 = st.columns(4)
    with t1:
        discount_type = st.selectbox("Discount Type", ["Percentage","Flat Amount"], index=(["Percentage","Flat Amount"].index(editing_doc.get("discount_type","Percentage")) if editing_doc else 0))
    with t2:
        discount_value = st.number_input("Discount Value", value=float(editing_doc.get("discount_value",0) if editing_doc else 0), min_value=0.0)
    with t3:
        shipping_enabled = st.checkbox("Add Shipping Charges?", value=editing_doc.get("shipping_enabled", False) if editing_doc else False)
    with t4:
        shipping_cost = st.number_input("Shipping Cost", value=float(editing_doc.get("shipping_cost",0) if editing_doc else 0), min_value=0.0, disabled=not shipping_enabled)

    subtotal, discount_amount, shipping, total = calc_totals(products, currency, discount_type, discount_value, shipping_enabled, shipping_cost)
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Subtotal", money(subtotal, currency))
    m2.metric("Discount", money(discount_amount, currency))
    m3.metric("Shipping", money(shipping, currency))
    m4.metric("Grand Total", money(total, currency))
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="section-title">Bank Details</div>', unsafe_allow_html=True)
    st.info("EUR and USD show Mashreq first, then WIO. AED shows WIO only.")
    bank_df = pd.DataFrame(BANKS[currency])
    st.dataframe(bank_df, use_container_width=True, hide_index=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card"><div class="section-title">Terms & Conditions</div>', unsafe_allow_html=True)
    terms_default = editing_doc.get("terms", settings.get("terms","")) if editing_doc else settings.get("terms","")
    terms = st.text_area("Default terms load automatically. Edit here for this document only.", value=terms_default, height=360)
    st.markdown('</div>', unsafe_allow_html=True)

    packing = []
    if doc_type == "Invoice":
        st.markdown('<div class="card"><div class="section-title">Packing List — Mandatory for Invoice</div>', unsafe_allow_html=True)
        pack_init = ensure_pack(products, editing_doc.get("packing", []) if editing_doc else [])
        pack_df = pd.DataFrame(pack_init)[DEFAULT_PACKING_COLUMNS]
        packing_df = st.data_editor(pack_df, num_rows="fixed", use_container_width=True, key=f"packing_{st.session_state.edit_doc_id or 'new'}")
        packing = packing_df.to_dict("records")
        # recalc CBM after edit
        for i,row in enumerate(packing):
            qty = float(products[i].get("Qty",1) or 1) if i < len(products) else 1
            row["CBM"] = round((float(row.get("Length",0) or 0)*float(row.get("Breadth",0) or 0)*float(row.get("Height",0) or 0)*qty)/1000000, 3)
        st.write(f"**Total CBM:** {sum(float(x.get('CBM',0) or 0) for x in packing):.3f} | **Total GW:** {sum(float(x.get('GW',0) or 0) for x in packing):.2f} KG | **Total NW:** {sum(float(x.get('NW',0) or 0) for x in packing):.2f} KG")
        st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.warning("Proforma Invoice: packing list is hidden. When converted to Invoice, packing list becomes mandatory and auto-fills products.")

    bill_to = {"Company Name":bill_company,"Registration Number":bill_reg,"GST/VAT":bill_tax,"Contact Person":bill_contact,"Phone":bill_phone,"Email":bill_email,"Country":bill_country,"Address":bill_address}
    current_doc = {
        "id": editing_doc.get("id") if editing_doc else str(uuid.uuid4()),
        "type": doc_type, "number": number, "date": str(doc_date), "currency": currency,
        "bill_to": bill_to, "ship_same": ship_same, "ship_to": ship_to, "products": products,
        "discount_type": discount_type, "discount_value": discount_value, "shipping_enabled": shipping_enabled, "shipping_cost": shipping_cost,
        "terms": terms, "packing": packing, "total": total, "updated_at": datetime.now().isoformat(timespec="seconds")
    }

    b1,b2,b3,b4 = st.columns([1,1,1,2])
    if b1.button("Save Document", type="primary"):
        # save customer if company exists
        if bill_company:
            existing_idx = next((i for i,c in enumerate(customers) if c.get("Company Name","").lower()==bill_company.lower()), None)
            cust_record = dict(bill_to)
            cust_record["ship_to"] = ship_to if not ship_same else bill_to
            if existing_idx is None: customers.append(cust_record)
            else: customers[existing_idx] = cust_record
            save_json(CUSTOMERS_FILE, customers)
        existing_idx = next((i for i,d in enumerate(documents) if d["id"] == current_doc["id"]), None)
        if existing_idx is None: documents.append(current_doc)
        else: documents[existing_idx] = current_doc
        save_json(DOCUMENTS_FILE, documents)
        st.success(f"Saved {doc_type}: {number}")
        st.session_state.edit_doc_id = current_doc["id"]

    if b2.button("Convert Proforma to Invoice"):
        if doc_type == "Proforma Invoice":
            current_doc["type"] = "Invoice"
            current_doc["number"] = next_number("Invoice", documents)
            current_doc["packing"] = ensure_pack(products)
            current_doc["id"] = str(uuid.uuid4())
            documents.append(current_doc)
            save_json(DOCUMENTS_FILE, documents)
            st.success(f"Converted and saved as Invoice: {current_doc['number']}")
            st.session_state.edit_doc_id = current_doc["id"]
        else:
            st.info("This document is already an Invoice.")

    pdf_bytes = pdf_document(current_doc)
    b3.download_button("Download PDF", data=pdf_bytes, file_name=f"{number.replace('/','-')}.pdf", mime="application/pdf")

with tab_saved:
    st.markdown('<div class="card"><div class="section-title">Saved Proformas & Invoices</div>', unsafe_allow_html=True)
    q = st.text_input("Search by number, customer, type, currency")
    filtered = documents
    if q:
        ql = q.lower()
        filtered = [d for d in documents if ql in json.dumps(d, ensure_ascii=False).lower()]
    if filtered:
        rows = []
        for d in filtered:
            rows.append({"Number":d["number"],"Type":d["type"],"Customer":d.get("bill_to",{}).get("Company Name",""),"Date":d["date"],"Currency":d["currency"],"Total":money(d.get("total",0), d["currency"]),"ID":d["id"]})
        st.dataframe(pd.DataFrame(rows).drop(columns=["ID"]), use_container_width=True, hide_index=True)
        selected_no = st.selectbox("Open document", [r["Number"] for r in rows])
        selected = next(d for d in filtered if d["number"] == selected_no)
        c1,c2,c3 = st.columns(3)
        if c1.button("Edit Selected"):
            st.session_state.edit_doc_id = selected["id"]
            st.rerun()
        if c2.button("Convert Selected Proforma to Invoice"):
            if selected["type"] == "Proforma Invoice":
                new_doc = dict(selected)
                new_doc["id"] = str(uuid.uuid4())
                new_doc["type"] = "Invoice"
                new_doc["number"] = next_number("Invoice", documents)
                new_doc["packing"] = ensure_pack(new_doc["products"])
                new_doc["updated_at"] = datetime.now().isoformat(timespec="seconds")
                documents.append(new_doc)
                save_json(DOCUMENTS_FILE, documents)
                st.success(f"Converted to {new_doc['number']}")
            else:
                st.info("Selected document is already an invoice.")
        c3.download_button("Download Selected PDF", data=pdf_document(selected), file_name=f"{selected['number'].replace('/','-')}.pdf", mime="application/pdf")
    else:
        st.warning("No saved documents yet.")
    st.markdown('</div>', unsafe_allow_html=True)

with tab_customers:
    st.markdown('<div class="card"><div class="section-title">Customer Database</div>', unsafe_allow_html=True)
    if customers:
        st.dataframe(pd.DataFrame(customers).drop(columns=["ship_to"], errors="ignore"), use_container_width=True, hide_index=True)
    else:
        st.info("No customers saved yet. Customers save automatically when documents are saved.")
    st.markdown('</div>', unsafe_allow_html=True)

with tab_settings:
    st.markdown('<div class="card"><div class="section-title">Default Terms & Conditions Template</div>', unsafe_allow_html=True)
    new_terms = st.text_area("Edit default terms used for new documents", value=settings.get("terms",""), height=500)
    if st.button("Save Default Terms"):
        settings["terms"] = new_terms
        save_json(SETTINGS_FILE, settings)
        st.success("Default terms updated.")
    st.markdown('</div>', unsafe_allow_html=True)
