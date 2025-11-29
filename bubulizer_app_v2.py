import streamlit as st
import pandas as pd
from datetime import datetime
from urllib.parse import quote_plus

import gspread
from google.oauth2.service_account import Credentials

# =========================
# CONFIG & BRANDING
# =========================
APP_NAME = "BUBULIZER Herbal Café"
PRIMARY_COLOR = "#14532d"   # deep herbal green
ACCENT_COLOR = "#f59e0b"    # warm gold

SHEET_NAME = "BUBULIZER"
WHATSAPP_NUMBER = "2348023808592"  # Nigeria
LOGO_PATH = "static/bubulizer_logo.png"  # put your logo here or set to None

# Simple, demo-level user store (NOT for real security)
USERS = {
    "admin": "bubulizer_admin",
    "cashier": "bubulizer_pos",
}

DELIVERY_FEE_NGN = 800  # flat fee for delivery orders (tune to taste)

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🍵",
    layout="centered"
)

# =========================
# GLOBAL STYLING
# =========================
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: #f9fafb;
    }}
    .bub-title {{
        color: {PRIMARY_COLOR};
    }}
    .bub-accent {{
        color: {ACCENT_COLOR};
    }}
    .menu-card {{
        border-radius: 12px;
        border: 1px solid #e5e7eb;
        padding: 0.75rem;
        background-color: #ffffff;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# GOOGLE SHEETS HELPERS
# =========================

@st.cache_resource
def get_gsheet_client():
    creds_info = st.secrets["gcp_service_account"]
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    credentials = Credentials.from_service_account_info(creds_info, scopes=scopes)
    client = gspread.authorize(credentials)
    return client

@st.cache_resource
def get_orders_worksheet():
    client = get_gsheet_client()
    sh = client.open(SHEET_NAME)
    try:
        ws = sh.worksheet("Orders")
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title="Orders", rows=1000, cols=20)
        ws.append_row([
            "timestamp",
            "order_id",
            "customer_name",
            "phone",
            "order_type",
            "notes",
            "item_name",
            "qty",
            "price_ngn",
            "line_total_ngn",
            "order_total_ngn"
        ])
    return ws

def save_order_to_sheet(customer_name, phone, order_type, notes, total_amount, cart_df):
    """
    Append order rows to Google Sheet and return order_id, timestamp.
    Delivery fee + address, if any, are encoded inside 'notes'.
    """
    ws = get_orders_worksheet()
    row_count = len(ws.get_all_values())  # includes header
    order_id = row_count  # first order will be 1
    timestamp = datetime.now().isoformat(timespec="seconds")

    for _, row in cart_df.iterrows():
        ws.append_row([
            timestamp,
            order_id,
            customer_name,
            phone,
            order_type,
            notes,
            row["Name"],
            int(row["Qty"]),
            int(row["Price_NGN"]),
            int(row["Total"]),
            int(total_amount)
        ])

    return order_id, timestamp

def load_orders_df():
    ws = get_orders_worksheet()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)

# =========================
# WHATSAPP & MAPS
# =========================

def generate_whatsapp_link(order_id, customer_name, phone, order_type,
                           total_amount, timestamp, cart_df, notes=""):
    lines = []
    lines.append(f"{APP_NAME} Order")
    lines.append(f"Order ID: {order_id}")
    lines.append(f"Time: {timestamp}")
    lines.append(f"Customer: {customer_name}")
    lines.append(f"Customer phone: {phone}")
    lines.append(f"Order type: {order_type}")
    if notes:
        lines.append(f"Notes: {notes}")
    lines.append("")
    lines.append("Items:")
    for _, row in cart_df.iterrows():
        lines.append(f"- {row['Qty']} × {row['Name']} = {row['Total']:,} NGN")
    lines.append("")
    lines.append(f"TOTAL: {total_amount:,} NGN")

    encoded = quote_plus("\n".join(lines))
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={encoded}"

def build_maps_link(address: str) -> str:
    if not address.strip():
        return ""
    encoded = quote_plus(address)
    return f"https://www.google.com/maps/search/?api=1&query={encoded}"

# =========================
# MENU DATA — REAL BUBULIZER PRODUCTS (IMPORTED)
# =========================

menu_items = [
    ("Herbal Tea", "BUBULIZER Alcoholic Bitters",
     "Herbal alcoholic bitters (200ml). 18+ Drink responsibly.",
     1200,
     "static/BUBULIZER_Alcoholic Bitters.jpeg"),

    ("Herbal Tea", "BUBULIZER Bridelia Tea",
     "Bridelia tea – detox & immune support (50g).",
     1500,
     "static/BUBULIZER_Bridelia tea.jpeg"),

    ("Herbal Tea", "BUBULIZER Small Leaf Tea",
     "Small leaf (stone breaker) tea – kidney wellness (50g).",
     1500,
     "static/BUBULIZER_Small leaf.jpeg"),

    ("Spices", "BUBULIZER Banga Soup Spice",
     "Nutmeg, guinea plum, scent leaves, liquorice mix – perfect for Banga soup.",
     1000,
     "static/BUBULIZER_Banga spice.jpeg"),

    ("Spices", "BUBULIZER Pepper Soup Spice",
     "Calabash nutmeg, Aidan fruit, spice tree – for chicken, fish, beef.",
     1000,
     "static/BUBULIZER_Pepper soup spice.jpeg"),
]

menu_df = pd.DataFrame(
    menu_items,
    columns=["Category", "Name", "Description", "Price_NGN", "Image_URL"]
)

# =========================
# CART MANAGEMENT
# =========================

if "cart" not in st.session_state:
    st.session_state.cart = []

if "user" not in st.session_state:
    st.session_state.user = None  # {"username": "..."} or None

def add_to_cart(item_name, qty):
    row = menu_df[menu_df["Name"] == item_name].iloc[0]
    price = row["Price_NGN"]
    for item in st.session_state.cart:
        if item["Name"] == item_name:
            item["Qty"] += qty
            item["Total"] = item["Qty"] * item["Price_NGN"]
            return
    st.session_state.cart.append({
        "Category": row["Category"],
        "Name": item_name,
        "Price_NGN": price,
        "Qty": qty,
        "Total": qty * price
    })

def clear_cart():
    st.session_state.cart = []

def cart_to_df():
    if not st.session_state.cart:
        return pd.DataFrame(columns=["Category", "Name", "Price_NGN", "Qty", "Total"])
    return pd.DataFrame(st.session_state.cart)

# =========================
# LOGIN LOGIC (very simple)
# =========================

def login_widget():
    if st.session_state.user:
        st.write(f"Logged in as **{st.session_state.user['username']}**")
        if st.button("Logout"):
            st.session_state.user = None
            st.experimental_rerun()
    else:
        with st.expander("🔐 Staff Login (Admin / POS)", expanded=False):
            username = st.text_input("Username", key="login_user")
            pw = st.text_input("Password", type="password", key="login_pw")
            if st.button("Login"):
                if username in USERS and USERS[username] == pw:
                    st.session_state.user = {"username": username}
                    st.success(f"Welcome, {username}.")
                    st.experimental_rerun()
                else:
                    st.error("Invalid credentials.")

# =========================
# SIDEBAR NAVIGATION
# =========================

with st.sidebar:
    if LOGO_PATH:
        try:
            st.image(LOGO_PATH, use_container_width=True)
        except Exception:
            pass
    st.markdown(f"<h3 class='bub-title'>{APP_NAME}</h3>", unsafe_allow_html=True)
    page = st.radio(
        "Navigate",
        ["Home", "Menu & Order", "Order Summary", "POS (In-House)", "Admin (Sheet View)", "About"]
    )
    st.markdown("---")
    login_widget()
    st.caption("BUBULIZER • NGN Edition • Streamlit + Google Sheets + WhatsApp")

# =========================
# PAGE: HOME
# =========================

if page == "Home":
    st.markdown(f"<h1 class='bub-title'>🍵 {APP_NAME}</h1>", unsafe_allow_html=True)
    st.subheader("Nigeria Edition — Herbal wellness, engineered properly.")
    st.write(
        """
        - Browse the **Menu & Order** page for customer-facing orders  
        - Use **Order Summary** for final confirmation and WhatsApp sending  
        - Use **POS (In-House)** for walk-in customers at the counter  
        - Use **Admin (Sheet View)** to see all logged orders from Google Sheets  
        """
    )

# =========================
# PAGE: MENU & ORDER (customer)
# =========================

elif page == "Menu & Order":
    st.title("📋 Menu & Order")

    categories = ["All"] + sorted(menu_df["Category"].unique())
    selected_cat = st.selectbox("Filter by category", categories)

    filtered_df = menu_df if selected_cat == "All" else menu_df[menu_df["Category"] == selected_cat]

    st.subheader("Menu")
    # Show as cards with images
    for _, row in filtered_df.iterrows():
        with st.container():
            cols = st.columns([1, 2])
            with cols[0]:
                if row["Image_URL"]:
                    st.image(row["Image_URL"], use_container_width=True)
            with cols[1]:
                st.markdown(f"**{row['Name']}**")
                st.caption(row["Description"])
                st.markdown(f"**₦{int(row['Price_NGN']):,}**")
                qty = st.number_input(
                    f"Qty – {row['Name']}", min_value=1, max_value=20, value=1, key=f"qty_{row['Name']}"
                )
                if st.button(f"Add {row['Name']} to cart", key=f"btn_{row['Name']}"):
                    add_to_cart(row["Name"], qty)
                    st.success(f"Added {qty} × {row['Name']}")

    st.markdown("### Your Cart")
    cart_df = cart_to_df()
    if cart_df.empty:
        st.warning("Your cart is empty.")
    else:
        st.dataframe(cart_df, use_container_width=True)
        total_amount = int(cart_df["Total"].sum())
        st.subheader(f"Estimated Total (before delivery): ₦{total_amount:,}")
        if st.button("🧹 Clear cart"):
            clear_cart()
            st.info("Cart cleared.")

# =========================
# PAGE: ORDER SUMMARY (customer)
# =========================

elif page == "Order Summary":
    st.title("🧾 Order Summary & Checkout")

    cart_df = cart_to_df()
    if cart_df.empty:
        st.warning("Your cart is empty.")
    else:
        st.dataframe(cart_df, use_container_width=True)
        base_total = int(cart_df["Total"].sum())

        st.subheader("Order Type & Delivery")
        order_type = st.selectbox("Order Type", ["Pickup at Café", "Delivery"])
        delivery_address = ""
        delivery_fee = 0

        if order_type == "Delivery":
            delivery_address = st.text_area("Delivery Address (for Google Maps)", height=60)
            delivery_fee = DELIVERY_FEE_NGN
            st.info(f"Delivery fee: ₦{delivery_fee:,}")

        grand_total = base_total + delivery_fee
        st.subheader(f"Grand Total: ₦{grand_total:,}")

        st.markdown("### Your Details")
        with st.form("checkout_form"):
            customer_name = st.text_input("Full Name")
            phone = st.text_input("Phone / WhatsApp")
            extra_notes = st.text_area("Notes (allergies, sweetness, etc.)", height=80)
            submitted = st.form_submit_button("✅ Confirm Order")

        if submitted:
            if not customer_name or not phone:
                st.error("Name and phone required.")
            else:
                # Encode delivery details into notes string (so sheet schema remains stable)
                notes_parts = []
                if extra_notes:
                    notes_parts.append(extra_notes)
                if order_type == "Delivery":
                    notes_parts.append(f"Delivery fee: ₦{delivery_fee:,}")
                    if delivery_address:
                        notes_parts.append(f"Address: {delivery_address}")
                notes = " | ".join(notes_parts) if notes_parts else ""

                order_id, timestamp = save_order_to_sheet(
                    customer_name, phone, order_type, notes, grand_total, cart_df
                )

                wa_link = generate_whatsapp_link(
                    order_id, customer_name, phone, order_type,
                    grand_total, timestamp, cart_df, notes
                )

                st.success(f"Order #{order_id} saved!")
                st.markdown("#### Receipt")
                st.write(f"**Order ID:** {order_id}")
                st.write(f"**Time:** {timestamp}")
                st.write(f"**Name:** {customer_name}")
                st.write(f"**Phone:** {phone}")
                st.write(f"**Order Type:** {order_type}")
                st.write(f"**Base Total:** ₦{base_total:,}")
                st.write(f"**Delivery Fee:** ₦{delivery_fee:,}")
                st.write(f"**Grand Total:** ₦{grand_total:,}")
                if extra_notes:
                    st.write(f"**Notes:** {extra_notes}")
                if delivery_address:
                    maps_link = build_maps_link(delivery_address)
                    if maps_link:
                        st.markdown(f"[📍 View delivery address in Google Maps]({maps_link})")

                st.write("---")
                st.dataframe(cart_df[["Name", "Qty", "Total"]], use_container_width=True)

                st.markdown(f"[📲 Send order via WhatsApp]({wa_link})")

# =========================
# PAGE: POS (In-House) – staff only
# =========================

elif page == "POS (In-House)":
    st.title("🧮 POS – In-House Orders")

    if not st.session_state.user:
        st.error("Staff login required to access POS.")
    else:
        st.write(f"Logged in as **{st.session_state.user['username']}**")

        cart_df = cart_to_df()
        st.subheader("Current POS Cart")
        if cart_df.empty:
            st.info("Cart is empty. Use Menu page or add POS-specific items here.")
        else:
            st.dataframe(cart_df, use_container_width=True)

        base_total = int(cart_df["Total"].sum()) if not cart_df.empty else 0
        st.subheader(f"Current Total: ₦{base_total:,}")

        st.markdown("### POS Checkout")
        with st.form("pos_form"):
            customer_name = st.text_input("Customer Name (optional)", value="Walk-in")
            phone = st.text_input("Phone (optional)", value="")
            payment_method = st.selectbox("Payment Method", ["Cash", "Transfer", "Card"])
            notes = st.text_area("POS Notes", height=60)
            submitted = st.form_submit_button("💾 Save POS Order")

        if submitted:
            if cart_df.empty:
                st.error("Cart is empty, cannot save POS order.")
            else:
                order_type = f"POS – {payment_method}"
                order_id, timestamp = save_order_to_sheet(
                    customer_name, phone, order_type, notes, base_total, cart_df
                )
                st.success(f"POS Order #{order_id} saved for {payment_method}.")
                st.write(f"Time: {timestamp}")
                st.write(f"Total: ₦{base_total:,}")
                clear_cart()

# =========================
# PAGE: ADMIN – SHEET VIEW
# =========================

elif page == "Admin (Sheet View)":
    st.title("🛠 Admin – Orders from Google Sheet")

    if not st.session_state.user:
        st.error("Staff login required to view admin data.")
    else:
        try:
            df = load_orders_df()
            if df.empty:
                st.info("No orders yet.")
            else:
                st.dataframe(df, use_container_width=True)
        except Exception as e:
            st.error(f"Could not load data: {e}")

# =========================
# PAGE: ABOUT
# =========================

elif page == "About":
    st.title("ℹ️ About BUBULIZER")
    st.write(
        """
        **BUBULIZER Herbal Café** – digital ordering, POS, and WhatsApp workflow
        built with:
        - Streamlit (Python)
        - Google Sheets (serverless datastore)
        - WhatsApp deep links
        - Lightweight POS mode for staff
        """
    )
