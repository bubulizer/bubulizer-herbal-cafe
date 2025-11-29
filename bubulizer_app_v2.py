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

SHEET_NAME = "BUBULIZER"    # Google Sheet name
WHATSAPP_NUMBER = "2348023808592"  # Nigeria format

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
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# GOOGLE SHEETS HELPERS
# =========================

@st.cache_resource
def get_gsheet_client():
    """Create a gspread client from Streamlit secrets."""
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
    """Open or create the 'Orders' worksheet inside the BUBULIZER sheet."""
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
    ws = get_orders_worksheet()
    row_count = len(ws.get_all_values())
    order_id = row_count
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
# WHATSAPP MESSAGE BUILDER
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

# =========================
# MENU DATA — NOW IN NGN
# =========================

menu_items = [
    ("Herbal Tea", "Lemongrass Detox Tea",     "Fresh lemongrass, ginger, honey.",         1500),
    ("Herbal Tea", "Moringa Immune Booster",   "Moringa, lemon, honey.",                  1800),
    ("Herbal Tea", "Hibiscus Heart Tonic",     "Hibiscus, clove, cinnamon.",              1700),
    ("Smoothie",   "Tropical Energy Smoothie", "Pineapple, mango, ginger, chia.",         2500),
    ("Smoothie",   "Green Gut Health Smoothie","Spinach, avocado, apple, flaxseed.",      3000),
    ("Smoothie",   "Banana Peanut Power",      "Banana, peanut, oats, soy milk.",         2200),
    ("Juice",      "Beetroot Liver Cleanse",   "Beetroot, carrot, apple, lemon.",         2000),
    ("Juice",      "Carrot Skin Glow",         "Carrot, orange, turmeric.",               1800),
    ("Snack",      "Millet & Sesame Energy Balls (3)", "Millet, sesame, dates.",          1200),
    ("Snack",      "Herbal Sweet Potato Fries","Oven-baked with rosemary.",                1500),
]

menu_df = pd.DataFrame(menu_items, columns=["Category", "Name", "Description", "Price_NGN"])

# =========================
# CART MANAGEMENT
# =========================

if "cart" not in st.session_state:
    st.session_state.cart = []

def add_to_cart(item_name, qty):
    row = menu_df[menu_df["Name"] == item_name].iloc[0]
    price = row["Price_NGN"]

    # Check if item already exists
    for item in st.session_state.cart:
        if item["Name"] == item_name:
            item["Qty"] += qty
            item["Total"] = item["Qty"] * item["Price_NGN"]
            return

    # Add new item
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
# SIDEBAR NAVIGATION
# =========================

with st.sidebar:
    st.markdown(f"<h3 class='bub-title'>{APP_NAME}</h3>", unsafe_allow_html=True)
    page = st.radio("Navigate", ["Home", "Menu & Order", "Order Summary", "Admin (Sheet View)", "About"])
    st.markdown("---")
    st.caption("BUBULIZER • NGN Edition • Streamlit + Google Sheets + WhatsApp")

# =========================
# PAGES
# =========================

if page == "Home":
    st.markdown(f"<h1 class='bub-title'>🍵 {APP_NAME}</h1>", unsafe_allow_html=True)
    st.subheader("Nigeria Edition — Powered by Natural Wellness.")
    st.write(
        """
        - All prices displayed in **NGN (₦)**  
        - Orders automatically logged into Google Sheets  
        - One-tap WhatsApp order confirmation  
        """
    )

elif page == "Menu & Order":
    st.title("📋 Menu & Order")

    categories = ["All"] + sorted(menu_df["Category"].unique())
    selected_cat = st.selectbox("Filter by category", categories)

    filtered_df = menu_df if selected_cat == "All" else menu_df[menu_df["Category"] == selected_cat]
    st.dataframe(filtered_df, use_container_width=True)

    st.subheader("Add Items to Cart")
    item_name = st.selectbox("Select item", filtered_df["Name"].tolist())
    qty = st.number_input("Quantity", min_value=1, max_value=20, value=1)

    if st.button("➕ Add to cart"):
        add_to_cart(item_name, qty)
        st.success(f"Added {qty} × {item_name} to cart.")

    st.subheader("Your Cart")
    cart_df = cart_to_df()

    if cart_df.empty:
        st.warning("Your cart is empty.")
    else:
        st.dataframe(cart_df, use_container_width=True)
        total_amount = int(cart_df["Total"].sum())
        st.subheader(f"Estimated Total: ₦{total_amount:,}")

        if st.button("🧹 Clear cart"):
            clear_cart()
            st.info("Cart cleared.")

elif page == "Order Summary":
    st.title("🧾 Order Summary & Checkout")

    cart_df = cart_to_df()
    if cart_df.empty:
        st.warning("Your cart is empty.")
    else:
        st.dataframe(cart_df, use_container_width=True)
        total_amount = int(cart_df["Total"].sum())
        st.subheader(f"Order Total: ₦{total_amount:,}")

        with st.form("checkout_form"):
            customer_name = st.text_input("Full Name")
            phone = st.text_input("Phone / WhatsApp")
            order_type = st.selectbox("Order Type", ["Pickup at Café", "Delivery"])
            notes = st.text_area("Notes", height=80)
            submitted = st.form_submit_button("✅ Confirm Order")

        if submitted:
            if not customer_name or not phone:
                st.error("Name and phone required.")
            else:
                order_id, timestamp = save_order_to_sheet(
                    customer_name, phone, order_type, notes, total_amount, cart_df
                )

                wa_link = generate_whatsapp_link(
                    order_id, customer_name, phone, order_type,
                    total_amount, timestamp, cart_df, notes
                )

                st.success(f"Order #{order_id} saved!")
                st.markdown(f"[📲 Send order via WhatsApp]({wa_link})")

elif page == "Admin (Sheet View)":
    st.title("🛠 Admin — Orders from Google Sheet")
    try:
        df = load_orders_df()
        st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load data: {e}")

elif page == "About":
    st.title("ℹ️ About BUBULIZER")
    st.write("Powered by natural herbs. Built with Streamlit, Python, and Google Sheets.")
