
import streamlit as st
import pandas as pd
import json, uuid, base64
from pathlib import Path
from datetime import date, datetime
from io import BytesIO
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

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
        {"Bank Name":"MASHREQ BANK PSC UAE","Currency":"EUR","IBAN":"AE830330000019102080621","SWIFT/BIC":"BOMLAEADXXX","Bank Address":"Umniyati Street, Burj Khalifa Community, Dubai, UAE. Postal Address: P.O. Box 1250, Dubai, UAE."},
        {"Bank Name":"WIO BANK PJSC","Currency":"EUR","IBAN":"AE830860000009168276489","SWIFT/BIC":"WIOBAEADXXX","Bank Address":"Etihad Airways Centre, 5th Floor, Abu Dhabi, UAE."},
    ],
    "USD": [
        {"Bank Name":"MASHREQ BANK PSC UAE","Currency":"USD","IBAN":"AE130330000019102080620","SWIFT/BIC":"BOMLAEADXXX","Bank Address":"Umniyati Street, Burj Khalifa Community, Dubai, UAE. Postal Address: P.O. Box 1250, Dubai, UAE."},
        {"Bank Name":"WIO BANK PJSC","Currency":"USD","IBAN":"AE480860000009878943739","SWIFT/BIC":"WIOBAEADXXX","Bank Address":"Etihad Airways Centre, 5th Floor, Abu Dhabi, UAE."},
    ],
    "AED": [
        {"Bank Name":"WIO BANK PJSC","Currency":"AED","IBAN":"AE730860000009886170371","SWIFT/BIC":"WIOBAEADXXX","Bank Address":"Etihad Airways Centre, 5th Floor, Abu Dhabi, UAE."},
    ],
}

PRODUCT_COLS = ["Brand","Product Details","Size","Finish","Qty","Rate Per Piece"]
PACK_COLS = ["Brand","Product Details","Length","Breadth","Height","CBM","GW","NW"]

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

def img_b64(path):
    return base64.b64encode(path.read_bytes()).decode() if path.exists() else ""

def money(v, currency):
    symbol = {"EUR":"€","USD":"$","AED":"AED"}.get(currency, currency)
    return f"{symbol} {float(v or 0):,.2f}"

def number_prefix(doc_type):
    return "CAP/PI" if doc_type == "Proforma Invoice" else "CAP/INV"

def next_number(doc_type, docs):
    prefix = number_prefix(doc_type)
    year = datetime.now().year
    nums = []
    for d in docs:
        n = str(d.get("number",""))
        if n.startswith(f"{prefix}/{year}/"):
            try:
                nums.append(int(n.split("/")[-1]))
            except Exception:
                pass
    return f"{prefix}/{year}/{(max(nums) if nums else 0)+1:04d}"

def calculate(products, discount_type, discount_value, shipping_enabled, shipping_cost):
    subtotal = 0.0
    for p in products:
        subtotal += float(p.get("Qty",0) or 0) * float(p.get("Rate Per Piece",0) or 0)
    discount = subtotal * float(discount_value or 0) / 100 if discount_type == "Percentage" else float(discount_value or 0)
    shipping = float(shipping_cost or 0) if shipping_enabled else 0.0
    return subtotal, discount, shipping, subtotal - discount + shipping

def packing_from_products(products, existing=None):
    existing = existing or []
    out = []
    for i,p in enumerate(products):
        ex = existing[i] if i < len(existing) else {}
        l = float(ex.get("Length",0) or 0)
        b = float(ex.get("Breadth",0) or 0)
        h = float(ex.get("Height",0) or 0)
        q = float(p.get("Qty",1) or 1)
        out.append({
            "Brand": p.get("Brand",""),
            "Product Details": p.get("Product Details",""),
            "Length": l,
            "Breadth": b,
            "Height": h,
            "CBM": round(l*b*h*q/1000000, 3),
            "GW": float(ex.get("GW",0) or 0),
            "NW": float(ex.get("NW",0) or 0),
        })
    return out


def pdf_header_footer(canvas, doc, title=""):
    w, h = A4
    canvas.saveState()

    # Logo
    if LOGO_PATH.exists():
        canvas.drawImage(
            str(LOGO_PATH),
            12 * mm,
            h - 24 * mm,
            width=35 * mm,
            height=16 * mm,
            preserveAspectRatio=True,
            mask="auto"
        )

    # Header text
    canvas.setFillColor(colors.HexColor("#071c2e"))
    canvas.setFont("Helvetica-Bold", 11)
    canvas.drawRightString(w - 12 * mm, h - 15 * mm, COMPANY["name"])

    canvas.setFillColor(colors.HexColor("#9b763c"))
    canvas.setFont("Helvetica-Bold", 9)
    canvas.drawRightString(w - 12 * mm, h - 20 * mm, title)

    canvas.setStrokeColor(colors.HexColor("#d0aa65"))
    canvas.line(12 * mm, h - 27 * mm, w - 12 * mm, h - 27 * mm)

    # Stamp bottom right
    if STAMP_PATH.exists():
        try:
            canvas.saveState()
            canvas.setFillAlpha(0.55)
            canvas.drawImage(
                str(STAMP_PATH),
                w - 48 * mm,
                15 * mm,
                width=32 * mm,
                height=32 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )
            canvas.restoreState()
        except Exception:
            canvas.drawImage(
                str(STAMP_PATH),
                w - 48 * mm,
                15 * mm,
                width=32 * mm,
                height=32 * mm,
                preserveAspectRatio=True,
                mask="auto"
            )

    # Footer
    canvas.setFillColor(colors.grey)
    canvas.setFont("Helvetica", 7)
    canvas.drawCentredString(
        w / 2,
        8 * mm,
        f"{COMPANY['name']} | {COMPANY['email']} | Page {canvas.getPageNumber()}"
    )

    canvas.restoreState()


def build_pdf(docdata):
    buffer = BytesIO()
    pdf = SimpleDocTemplate(buffer, pagesize=A4, leftMargin=12*mm, rightMargin=12*mm, topMargin=32*mm, bottomMargin=15*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Small", parent=styles["Normal"], fontSize=7.5, leading=9))
    styles.add(ParagraphStyle(name="Tiny", parent=styles["Normal"], fontSize=6.8, leading=8))
    styles.add(ParagraphStyle(name="TitleGold", parent=styles["Title"], fontSize=18, textColor=colors.HexColor("#9b763c"), leading=21))
    styles.add(ParagraphStyle(name="Navy", parent=styles["Heading2"], fontSize=11, textColor=colors.HexColor("#071c2e"), leading=13))
    story = []

    story.append(Paragraph(docdata["type"].upper(), styles["TitleGold"]))
    story.append(Paragraph(f"No: {docdata['number']} &nbsp;&nbsp; Date: {docdata['date']} &nbsp;&nbsp; Currency: {docdata['currency']}", styles["Small"]))
    story.append(Paragraph(f"{COMPANY['address']}<br/>{COMPANY['license']}<br/>{COMPANY['phone']}<br/>{COMPANY['email']}", styles["Small"]))
    story.append(Spacer(1,5))

    bill = docdata.get("bill_to",{})
    ship = docdata.get("ship_to",{})
    bill_text = "<br/>".join([f"<b>{bill.get('Company Name','')}</b>", bill.get("Registration Number",""), bill.get("GST/VAT",""), bill.get("Contact Person",""), bill.get("Phone",""), bill.get("Email",""), bill.get("Address",""), bill.get("Country","")])
    ship_text = "Same as Bill To" if docdata.get("ship_same") else "<br/>".join([ship.get("Company Name",""), ship.get("Contact Person",""), ship.get("Phone",""), ship.get("Email",""), ship.get("Address",""), ship.get("Country","")])
    bt = Table([[Paragraph("<b>BILL TO</b><br/>"+bill_text, styles["Small"]), Paragraph("<b>SHIP TO</b><br/>"+ship_text, styles["Small"])]], colWidths=[86*mm,86*mm])
    bt.setStyle(TableStyle([("BOX",(0,0),(-1,-1),0.5,colors.HexColor("#c9b083")),("BACKGROUND",(0,0),(-1,-1),colors.HexColor("#faf7f1")),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(bt); story.append(Spacer(1,6))

    rows = [["SL","Brand","Product Details","Size","Finish","Qty","Rate/PC","Amount"]]
    for i,p in enumerate(docdata["products"], 1):
        qty=float(p.get("Qty",0) or 0); rate=float(p.get("Rate Per Piece",0) or 0)
        rows.append([i, p.get("Brand",""), Paragraph(p.get("Product Details",""), styles["Tiny"]), p.get("Size",""), Paragraph(p.get("Finish",""), styles["Tiny"]), qty, money(rate, docdata["currency"]), money(qty*rate, docdata["currency"])])
    t = Table(rows, repeatRows=1, colWidths=[8*mm,24*mm,43*mm,25*mm,34*mm,10*mm,23*mm,24*mm])
    t.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#071c2e")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("GRID",(0,0),(-1,-1),0.25,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),6.8),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(t); story.append(Spacer(1,6))

    subtotal, disc, shipc, total = calculate(docdata["products"], docdata["discount_type"], docdata["discount_value"], docdata["shipping_enabled"], docdata["shipping_cost"])
    totals = [["Subtotal", money(subtotal, docdata["currency"])],["Discount", f"- {money(disc, docdata['currency'])}"],["Shipping", money(shipc, docdata["currency"])],["Grand Total", money(total, docdata["currency"])]]
    tt = Table(totals, colWidths=[40*mm,38*mm], hAlign="RIGHT")
    tt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,3),(-1,3),colors.HexColor("#071c2e")),("TEXTCOLOR",(0,3),(-1,3),colors.white),("FONTNAME",(0,3),(-1,3),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8)]))
    story.append(tt); story.append(Spacer(1,7))

    story.append(Paragraph("BANK DETAILS", styles["Navy"]))
    bank_rows = [["Bank Name","Currency","IBAN","SWIFT/BIC","Bank Address"]]
    for b in BANKS[docdata["currency"]]:
        bank_rows.append([b["Bank Name"], b["Currency"], b["IBAN"], b["SWIFT/BIC"], Paragraph(b["Bank Address"], styles["Tiny"])])
    bank_table = Table(bank_rows, repeatRows=1, colWidths=[38*mm,16*mm,45*mm,25*mm,55*mm])
    bank_table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#9b763c")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.grey),("FONTSIZE",(0,0),(-1,-1),6.8),("VALIGN",(0,0),(-1,-1),"TOP")]))
    story.append(bank_table)

    story.append(PageBreak())
    story.append(Paragraph("TERMS & CONDITIONS", styles["TitleGold"]))
    if LOGO_PATH.exists(): story.append(Spacer(1,2))
    for line in docdata.get("terms","").split("\n"):
        if line.strip():
            story.append(Paragraph(line.strip(), styles["Small"]))
            story.append(Spacer(1,1.5))
    story.append(Spacer(1,12))
    sig = [["Seller Signature", "Buyer Signature"]]
    if STAMP_PATH.exists():
        sig.append([Image(str(STAMP_PATH), width=28*mm, height=20*mm), ""])
    sig.append(["HARSH TEJPAL RANA\nOWNER\nCASA ARTE PRIVEE FZ-LLC", "Name:\nCompany:\nDate:"])
    sigt = Table(sig, colWidths=[85*mm,85*mm])
    sigt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.25,colors.grey),("BACKGROUND",(0,0),(-1,0),colors.HexColor("#faf7f1")),("VALIGN",(0,0),(-1,-1),"TOP"),("FONTSIZE",(0,0),(-1,-1),8)]))
    story.append(sigt)

    if docdata["type"] == "Invoice":
        story.append(PageBreak())
        story.append(Paragraph("PACKING LIST", styles["TitleGold"]))
        pack = packing_from_products(docdata["products"], docdata.get("packing",[]))
        prow = [["SL","Brand","Product Details","Length","Breadth","Height","CBM","GW","NW"]]
        for i,p in enumerate(pack, 1):
            prow.append([i,p["Brand"],Paragraph(p["Product Details"],styles["Tiny"]),p["Length"],p["Breadth"],p["Height"],p["CBM"],p["GW"],p["NW"]])
        pt = Table(prow, repeatRows=1, colWidths=[8*mm,28*mm,58*mm,15*mm,15*mm,15*mm,18*mm,17*mm,17*mm])
        pt.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),colors.HexColor("#071c2e")),("TEXTCOLOR",(0,0),(-1,0),colors.white),("GRID",(0,0),(-1,-1),0.25,colors.lightgrey),("FONTSIZE",(0,0),(-1,-1),6.8),("VALIGN",(0,0),(-1,-1),"TOP")]))
        story.append(pt); story.append(Spacer(1,8))
        story.append(Paragraph(f"<b>Total CBM:</b> {sum(float(x.get('CBM',0) or 0) for x in pack):.3f} &nbsp;&nbsp; <b>Total GW:</b> {sum(float(x.get('GW',0) or 0) for x in pack):.2f} KG &nbsp;&nbsp; <b>Total NW:</b> {sum(float(x.get('NW',0) or 0) for x in pack):.2f} KG", styles["Navy"]))
        story.append(Spacer(1,15))
        story.append(Paragraph("Digital Signature / Authorized Signatory", styles["Navy"]))
        if STAMP_PATH.exists():
            story.append(Image(str(STAMP_PATH), width=30*mm, height=22*mm))
        story.append(Paragraph("HARSH TEJPAL RANA<br/>OWNER<br/>CASA ARTE PRIVEE FZ-LLC", styles["Small"]))

    pdf.build(story, onFirstPage=lambda c,d: pdf_header_footer(c,d,docdata["type"]), onLaterPages=lambda c,d: pdf_header_footer(c,d,docdata["type"]))
    return buffer.getvalue()

settings = load_json(SETTINGS_FILE, {"terms":"","password":"1985"})
st.set_page_config(page_title="Casa Arte Privée Billing", layout="wide")

# optional password, on by default
if "auth" not in st.session_state: st.session_state.auth = False
if not st.session_state.auth:
    st.markdown("<div style='background:#071c2e;padding:38px;border-radius:22px;text-align:center;color:white;margin-top:80px;'><h1 style='color:#d0aa65;font-family:Georgia;'>CASA ARTE PRIVÉE</h1><p style='letter-spacing:4px;'>BILLING SYSTEM LOGIN</p></div>", unsafe_allow_html=True)
    pw = st.text_input("Password", type="password")
    if st.button("Login"):
        if pw == str(settings.get("password","1985")):
            st.session_state.auth = True
            st.rerun()
        else:
            st.error("Incorrect password")
    st.stop()

st.markdown("""
<style>
.stApp { background:#f7f3ec; }
.block-container { max-width:1500px; padding-top:1rem; }
.cap { background:#071c2e; color:white; padding:22px; border-radius:22px; margin-bottom:18px; box-shadow:0 12px 30px #0002; }
.gold { color:#d0aa65; font-family:Georgia,serif; }
.card { background:white; border:1px solid #eadfcd; border-radius:18px; padding:16px; margin-bottom:16px; box-shadow:0 8px 24px #071c2e10; }
</style>
""", unsafe_allow_html=True)

logo = img_b64(LOGO_PATH)
logo_html = f"<img src='data:image/png;base64,{logo}' style='height:78px;object-fit:contain;margin-right:18px;'>" if logo else ""
st.markdown(f"<div class='cap' style='display:flex;align-items:center;'>{logo_html}<div><h1 class='gold' style='margin:0;font-size:34px;'>CASA ARTE PRIVÉE</h1><div style='letter-spacing:5px;font-size:11px;'>BILLING · PROFORMA · INVOICE · PACKING LIST</div></div></div>", unsafe_allow_html=True)

customers = load_json(CUSTOMERS_FILE, [])
documents = load_json(DOCUMENTS_FILE, [])

if "editing_id" not in st.session_state: st.session_state.editing_id = None


st.sidebar.markdown("## CASA ARTE PRIVÉE")
if "page" not in st.session_state:
    st.session_state.page = "Create / Edit"

page = st.sidebar.radio(
    "Navigation",
    ["Create / Edit", "Saved Documents", "Customers", "Settings"],
    index=["Create / Edit", "Saved Documents", "Customers", "Settings"].index(st.session_state.page),
    key="page_radio"
)
st.session_state.page = page


if st.session_state.page == "Create / Edit":
    editing = next((d for d in documents if d.get("id") == st.session_state.editing_id), None) if st.session_state.editing_id else None

    c1,c2,c3,c4 = st.columns(4)
    doc_type = c1.selectbox("Document Type", ["Proforma Invoice","Invoice"], index=1 if editing and editing.get("type")=="Invoice" else 0)
    currency = c2.selectbox("Currency", ["EUR","USD","AED"], index=["EUR","USD","AED"].index(editing.get("currency","EUR")) if editing else 0)
    doc_date = c3.date_input("Date", value=datetime.strptime(editing.get("date"), "%Y-%m-%d").date() if editing else date.today())
    doc_number = c4.text_input("Document No.", value=editing.get("number") if editing else next_number(doc_type, documents))

    if st.button("Start New Blank Document"):
        st.session_state.editing_id = None
        st.session_state.page = "Create / Edit"
        st.rerun()

    st.markdown("<div class='card'><h3 class='gold'>Customer Details</h3>", unsafe_allow_html=True)
    names = ["-- New Customer --"] + [c.get("Company Name","") for c in customers]
    selected = st.selectbox("Choose saved customer", names)
    selected_customer = next((c for c in customers if c.get("Company Name")==selected), {}) if selected != "-- New Customer --" else {}
    bill_existing = editing.get("bill_to", {}) if editing else selected_customer
    a,b = st.columns(2)
    with a:
        bill_company = st.text_input("Company Name", value=bill_existing.get("Company Name",""))
        bill_reg = st.text_input("Company Registration Number", value=bill_existing.get("Registration Number",""))
        bill_vat = st.text_input("GST / VAT", value=bill_existing.get("GST/VAT",""))
        bill_contact = st.text_input("Contact Person", value=bill_existing.get("Contact Person",""))
    with b:
        bill_phone = st.text_input("Phone", value=bill_existing.get("Phone",""))
        bill_email = st.text_input("Email", value=bill_existing.get("Email",""))
        bill_country = st.text_input("Country", value=bill_existing.get("Country",""))
        bill_address = st.text_area("Billing Address", value=bill_existing.get("Address",""), height=92)
    ship_same = st.checkbox("Ship To same as Bill To", value=editing.get("ship_same", True) if editing else True)
    ship_to = {}
    if not ship_same:
        s1,s2 = st.columns(2)
        ship_existing = editing.get("ship_to", {}) if editing else selected_customer.get("ship_to", {})
        with s1:
            ship_to["Company Name"] = st.text_input("Shipping Company", value=ship_existing.get("Company Name",""))
            ship_to["Contact Person"] = st.text_input("Shipping Contact", value=ship_existing.get("Contact Person",""))
            ship_to["Phone"] = st.text_input("Shipping Phone", value=ship_existing.get("Phone",""))
        with s2:
            ship_to["Email"] = st.text_input("Shipping Email", value=ship_existing.get("Email",""))
            ship_to["Country"] = st.text_input("Shipping Country", value=ship_existing.get("Country",""))
            ship_to["Address"] = st.text_area("Shipping Address", value=ship_existing.get("Address",""), height=92)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><h3 class='gold'>Products</h3>", unsafe_allow_html=True)
    init_products = editing.get("products") if editing else [{"Brand":"","Product Details":"","Size":"","Finish":"","Qty":1,"Rate Per Piece":0.0}]
    pdf = pd.DataFrame(init_products)
    for col in PRODUCT_COLS:
        if col not in pdf.columns: pdf[col] = 0 if col in ["Qty","Rate Per Piece"] else ""
    edited_df = st.data_editor(pdf[PRODUCT_COLS], num_rows="dynamic", use_container_width=True, key=f"prod_{st.session_state.editing_id or 'new'}")
    products = edited_df.fillna("").to_dict("records")
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><h3 class='gold'>Discount / Shipping / Totals</h3>", unsafe_allow_html=True)
    d1,d2,d3,d4 = st.columns(4)
    discount_type = d1.selectbox("Discount Type", ["Percentage","Flat Amount"], index=["Percentage","Flat Amount"].index(editing.get("discount_type","Percentage")) if editing else 0)
    discount_value = d2.number_input("Discount Value", min_value=0.0, value=float(editing.get("discount_value",0) if editing else 0))
    shipping_enabled = d3.checkbox("Add Shipping Charges?", value=bool(editing.get("shipping_enabled", False)) if editing else False)
    shipping_cost = d4.number_input("Shipping Cost", min_value=0.0, value=float(editing.get("shipping_cost",0) if editing else 0), disabled=not shipping_enabled, help="Tick Add Shipping Charges first, then enter shipping amount.")
    subtotal, discount_amount, shipping_amount, grand = calculate(products, discount_type, discount_value, shipping_enabled, shipping_cost)
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Subtotal", money(subtotal, currency))
    m2.metric("Discount", money(discount_amount, currency))
    m3.metric("Shipping", money(shipping_amount, currency))
    m4.metric("Grand Total", money(grand, currency))
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><h3 class='gold'>Bank Details</h3>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame(BANKS[currency]), use_container_width=True, hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div class='card'><h3 class='gold'>Terms & Conditions</h3>", unsafe_allow_html=True)
    terms = st.text_area("Editable default terms for this document", value=editing.get("terms", settings.get("terms","")) if editing else settings.get("terms",""), height=330)
    st.markdown("</div>", unsafe_allow_html=True)

    packing = []
    if doc_type == "Invoice":
        st.markdown("<div class='card'><h3 class='gold'>Packing List — Mandatory</h3>", unsafe_allow_html=True)
        pack_init = pd.DataFrame(packing_from_products(products, editing.get("packing", []) if editing else []))
        pack_edit = st.data_editor(pack_init[PACK_COLS], num_rows="fixed", use_container_width=True, key=f"pack_{st.session_state.editing_id or 'new'}")
        packing = pack_edit.fillna(0).to_dict("records")
        for i,row in enumerate(packing):
            qty = float(products[i].get("Qty",1) or 1) if i < len(products) else 1
            row["CBM"] = round(float(row.get("Length",0) or 0)*float(row.get("Breadth",0) or 0)*float(row.get("Height",0) or 0)*qty/1000000, 3)
        st.write(f"**Total CBM:** {sum(float(x.get('CBM',0) or 0) for x in packing):.3f} | **Total GW:** {sum(float(x.get('GW',0) or 0) for x in packing):.2f} KG | **Total NW:** {sum(float(x.get('NW',0) or 0) for x in packing):.2f} KG")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.warning("Proforma: packing list is hidden. It will auto-create when converted to Invoice.")

    bill_to = {"Company Name":bill_company,"Registration Number":bill_reg,"GST/VAT":bill_vat,"Contact Person":bill_contact,"Phone":bill_phone,"Email":bill_email,"Country":bill_country,"Address":bill_address}
    docdata = {
        "id": editing.get("id") if editing else str(uuid.uuid4()),
        "type": doc_type, "number": doc_number, "date": str(doc_date), "currency": currency,
        "bill_to": bill_to, "ship_same": ship_same, "ship_to": ship_to,
        "products": products, "discount_type": discount_type, "discount_value": discount_value,
        "shipping_enabled": shipping_enabled, "shipping_cost": shipping_cost,
        "terms": terms, "packing": packing, "total": grand,
        "created_at": editing.get("created_at") if editing else datetime.now().isoformat(timespec="seconds"),
        "updated_at": datetime.now().isoformat(timespec="seconds")
    }

    x1,x2,x3 = st.columns(3)
    if x1.button("Save / Update Document", type="primary"):
        # save/update customer
        if bill_company:
            cust = dict(bill_to)
            cust["ship_to"] = bill_to if ship_same else ship_to
            found = next((i for i,c in enumerate(customers) if c.get("Company Name","").lower()==bill_company.lower()), None)
            if found is None: customers.append(cust)
            else: customers[found] = cust
            save_json(CUSTOMERS_FILE, customers)
        idx = next((i for i,d in enumerate(documents) if d.get("id")==docdata["id"]), None)
        if idx is None:
            documents.append(docdata)
        else:
            documents[idx] = docdata
        save_json(DOCUMENTS_FILE, documents)
        st.session_state.editing_id = docdata["id"]
        st.success(f"Saved: {docdata['number']}")

    if x2.button("Convert Proforma to Invoice"):
        if doc_type == "Proforma Invoice":
            newdoc = dict(docdata)
            newdoc["id"] = str(uuid.uuid4())
            newdoc["type"] = "Invoice"
            newdoc["number"] = next_number("Invoice", documents)
            newdoc["packing"] = packing_from_products(products)
            newdoc["created_at"] = datetime.now().isoformat(timespec="seconds")
            newdoc["updated_at"] = datetime.now().isoformat(timespec="seconds")
            documents.append(newdoc)
            save_json(DOCUMENTS_FILE, documents)
            st.session_state.editing_id = newdoc["id"]
            st.session_state.page = "Create / Edit"
            st.success(f"Converted to Invoice: {newdoc['number']}. Opening converted invoice for editing/packing details...")
            st.rerun()
        else:
            st.info("Already an Invoice.")

    x3.download_button("Download PDF", data=build_pdf(docdata), file_name=f"{doc_number.replace('/','-')}.pdf", mime="application/pdf")

if st.session_state.page == "Saved Documents":
    st.markdown("<div class='card'><h3 class='gold'>Saved Documents — Select / Edit / Convert / Delete</h3>", unsafe_allow_html=True)
    search = st.text_input("Search saved documents by number, customer, type, currency")
    results = documents
    if search:
        s = search.lower()
        results = [d for d in documents if s in json.dumps(d, ensure_ascii=False).lower()]

    if not results:
        st.warning("No documents saved.")
    else:
        st.caption("Each document has its own Edit, Convert, Download and Delete action. Edit/Convert will take you back to the data entry page.")
        for d in sorted(results, key=lambda x: x.get("updated_at", x.get("created_at","")), reverse=True):
            customer_name = d.get("bill_to", {}).get("Company Name", "")
            row = st.container(border=True)
            with row:
                c0, c1, c2, c3, c4, c5 = st.columns([2.4, 1.3, 2.2, 1.1, 1.2, 1.8])
                c0.markdown(f"**{d.get('number','')}**")
                c0.caption(f"{d.get('date','')} · {d.get('currency','')}")
                c1.markdown(f"**{d.get('type','')}**")
                c2.markdown(customer_name or "No customer")
                c3.markdown(f"**{money(d.get('total',0), d.get('currency','EUR'))}**")

                if c4.button("Edit", key=f"edit_{d.get('id')}"):
                    st.session_state.editing_id = d.get("id")
                    st.session_state.page = "Create / Edit"
                    st.rerun()

                if d.get("type") == "Proforma Invoice":
                    if c5.button("Convert to Invoice", key=f"convert_{d.get('id')}"):
                        newdoc = dict(d)
                        newdoc["id"] = str(uuid.uuid4())
                        newdoc["type"] = "Invoice"
                        newdoc["number"] = next_number("Invoice", documents)
                        newdoc["packing"] = packing_from_products(newdoc.get("products", []))
                        newdoc["created_at"] = datetime.now().isoformat(timespec="seconds")
                        newdoc["updated_at"] = datetime.now().isoformat(timespec="seconds")
                        documents.append(newdoc)
                        save_json(DOCUMENTS_FILE, documents)
                        st.session_state.editing_id = newdoc["id"]
                        st.session_state.page = "Create / Edit"
                        st.rerun()
                else:
                    c5.caption("Already invoice")

                d1, d2 = st.columns([1.2, 2])
                d1.download_button(
                    "Download PDF",
                    data=build_pdf(d),
                    file_name=f"{d.get('number','document').replace('/','-')}.pdf",
                    mime="application/pdf",
                    key=f"pdf_{d.get('id')}"
                )

                confirm = d2.checkbox(f"Confirm delete {d.get('number','')}", key=f"confirm_delete_{d.get('id')}")
                if d2.button("Delete", key=f"delete_{d.get('id')}", type="secondary"):
                    if confirm:
                        documents = [x for x in documents if x.get("id") != d.get("id")]
                        save_json(DOCUMENTS_FILE, documents)
                        if st.session_state.editing_id == d.get("id"):
                            st.session_state.editing_id = None
                        st.success(f"Deleted {d.get('number','document')}")
                        st.rerun()
                    else:
                        st.warning("Tick confirm delete first.")
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.page == "Customers":
    st.markdown("<div class='card'><h3 class='gold'>Customer Database</h3>", unsafe_allow_html=True)
    if customers:
        st.dataframe(pd.DataFrame(customers).drop(columns=["ship_to"], errors="ignore"), use_container_width=True, hide_index=True)
        customer_names_for_delete = [c.get("Company Name","") for c in customers if c.get("Company Name","")]
        if customer_names_for_delete:
            selected_customer_delete = st.selectbox("Select customer to delete", customer_names_for_delete)
            confirm_delete_customer = st.checkbox(f"Confirm delete customer {selected_customer_delete}")
            if st.button("Delete Selected Customer", type="secondary"):
                if confirm_delete_customer:
                    customers = [c for c in customers if c.get("Company Name","") != selected_customer_delete]
                    save_json(CUSTOMERS_FILE, customers)
                    st.success(f"Deleted customer: {selected_customer_delete}")
                    st.rerun()
                else:
                    st.warning("Please tick confirm delete first.")
    else:
        st.info("No customers saved yet.")
    st.markdown("</div>", unsafe_allow_html=True)

if st.session_state.page == "Settings":
    st.markdown("<div class='card'><h3 class='gold'>Settings</h3>", unsafe_allow_html=True)
    st.write("Password is currently set to **1985**.")
    new_terms = st.text_area("Default Terms & Conditions", value=settings.get("terms",""), height=430)
    if st.button("Save Default Terms"):
        settings["terms"] = new_terms
        save_json(SETTINGS_FILE, settings)
        st.success("Settings saved.")
    st.markdown("</div>", unsafe_allow_html=True)
