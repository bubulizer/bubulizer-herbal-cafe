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

SHEET_NAME = "BUBULIZER"    # Google Sheet name you created

# Replace this with your real WhatsApp business number, e.g. "2567XXXXXXXX"
WHATSAPP_NUMBER = "2567XXXXXXX"

st.set_page_config(
    page_title=APP_NAME,
    page_icon="🍵",
    layout="centered"
)

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
            "price_ugx",
            "line_total_ugx",
            "order_total_ugx"
        ])
    return ws

def save_order_to_sheet(customer_name, phone, order_type, notes, total_amount, cart_df):
    """Append order rows to Google Sheet and return order_id, timestamp."""
    ws = get_orders_worksheet()
    # simple order_id = current number of orders (row count - header)
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
            int(row["Price_UGX"]),
            int(row["Total"]),
            int(total_amount)
        ])

    return order_id, timestamp

def load_orders_df():
    """Load all orders from Google Sheet into a DataFrame."""
    ws = get_orders_worksheet()
    records = ws.get_all_records()
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)

# =========================
# WHATSAPP LINK
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
        lines.append(f"- {int(row['Qty'])} × {row['Name']} = {int(row['Total']):,} UGX")
    lines.append("")
    lines.append(f"TOTAL: {total_amount:,} UGX")

    message = "\n".join(lines)
    encoded = quote_plus(message)
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={encoded}"

# =========================
# MENU DATA (customisable)
# =========================
menu_items = [
    ("Herbal Tea", "Lemongrass Detox Tea",     "Fresh lemongrass, ginger, honey.",         6000),
    ("Herbal Tea", "Moringa Immune Booster",   "Moringa leaves, lemon, organic honey.",   7000),
    ("Herbal Tea", "Hibiscus Heart Tonic",     "Dried hibiscus, clove, cinnamon.",        6500),
    ("Smoothie",   "Tropical Energy Smoothie", "Pineapple, mango, ginger, chia seeds.",   9000),
    ("Smoothie",   "Green Gut Health Smoothie","Spinach, avocado, apple, flaxseed.",      9500),
    ("Smoothie",   "Banana Peanut Power",      "Banana, peanut, oats, soy milk.",         8500),
    ("Juice",      "Beetroot Liver Cleanse",   "Beetroot, carrot, apple, lemon.",         8000),
    ("Juice",      "Carrot Skin Glow",         "Carrot, orange, turmeric.",               7500),
    ("Snack",      "Millet & Sesame Energy Balls (3)", "Millet, sesame, dates, coconut.", 5000),
    ("Snack",      "Herbal Sweet Potato Fries","Oven-baked, rosemary & thyme.",           6000),
]
menu_df = pd.DataFrame(menu_items, columns=["Category", "Name", "Description", "Price_UGX"])

# =========================
# SESSION STATE (CART)
# =========================
if "cart" not in st.session_state:
    st.session_state.cart = []

def add_to_cart(item_name, qty):
    if qty <= 0:
        return
    row = menu_df[menu_df["Name"] == item_name].iloc[0]
    price = row["Price_UGX"]
    category = row["Category"]
    for item in st.session_state.cart:
        if item["Name"] == item_name:
            item["Qty"] += qty
            item["Total"] = item["Qty"] * item["Price_UGX"]
            break
    else:
        st.session_state.cart.append({
            "Category": category,
            "Name": item_name,
            "Price_UGX": price,
            "Qty": qty,
            "Total": qty * price
        })

def clear_cart():
    st.session_state.cart = []

def cart_to_df():
    if not st.session_state.cart:
        return pd.DataFrame(columns=["Category", "Name", "Price_UGX", "Qty", "Total"])
    return pd.DataFrame(st.session_state.cart)

# =========================
# SIDEBAR NAV
# =========================
with st.sidebar:
    st.markdown(f"<h3 class='bub-title'>{APP_NAME}</h3>", unsafe_allow_html=True)
    page = st.radio("Navigate", ["Home", "Menu & Order", "Order Summary", "Admin (Sheet View)", "About"])
    st.markdown("---")
    st.caption("BUBULIZER v3 • Streamlit + Google Sheets + WhatsApp")

# =========================
# PAGES
# =========================
if page == "Home":
    st.markdown(f"<h1 class='bub-title'>🍵 {APP_NAME}</h1>", unsafe_allow_html=True)
    st.subheader("Herbal wellness, engineered properly.")
    st.write(
        """
        This is the cloud-ready version of the **BUBULIZER Herbal Café** app.

        - Orders are stored in a secure Google Sheet (`BUBULIZER`).  
        - You can review all orders from the Admin page.  
        - Customers can confirm and send orders to WhatsApp with one tap.
        """
    )

elif page == "Menu & Order":
    st.title("📋 Menu & Order")

    categories = ["All"] + sorted(menu_df["Category"].unique())
    selected_cat = st.selectbox("Filter by category", categories)

    filtered_df = menu_df if selected_cat == "All" else menu_df[menu_df["Category"] == selected_cat]
    st.subheader("Menu")
    st.dataframe(filtered_df[["Category", "Name", "Description", "Price_UGX"]], use_container_width=True)

    st.markdown("### Add Items to Cart")
    item_name = st.selectbox("Select item", filtered_df["Name"].tolist())
    qty = st.number_input("Quantity", min_value=1, max_value=20, value=1, step=1)

    if st.button("➕ Add to cart"):
        add_to_cart(item_name, qty)
        st.success(f"Added {qty} × {item_name} to your cart.")

    st.markdown("### Your Cart")
    cart_df = cart_to_df()
    if cart_df.empty:
        st.warning("Your cart is empty.")
    else:
        cart_df_display = cart_df.copy()
        cart_df_display["Price_UGX"] = cart_df_display["Price_UGX"].astype(int)
        cart_df_display["Total"] = cart_df_display["Total"].astype(int)
        st.dataframe(cart_df_display, use_container_width=True)

        total_amount = int(cart_df["Total"].sum())
        st.subheader(f"Estimated Total: {total_amount:,} UGX")

        if st.button("🧹 Clear cart"):
            clear_cart()
            st.info("Cart cleared.")

elif page == "Order Summary":
    st.title("🧾 Order Summary & Checkout")

    cart_df = cart_to_df()
    if cart_df.empty:
        st.warning("Your cart is empty. Add items from **Menu & Order**.")
    else:
        cart_df_display = cart_df.copy()
        cart_df_display["Price_UGX"] = cart_df_display["Price_UGX"].astype(int)
        cart_df_display["Total"] = cart_df_display["Total"].astype(int)
        total_amount = int(cart_df["Total"].sum())

        st.subheader("Your Cart")
        st.dataframe(cart_df_display, use_container_width=True)
        st.subheader(f"Order Total: {total_amount:,} UGX")

        st.markdown("### Your Details")
        with st.form("checkout_form"):
            customer_name = st.text_input("Full Name")
            phone = st.text_input("Phone / WhatsApp")
            order_type = st.selectbox("Order Type", ["Pickup at Café", "Delivery (within city)"])
            notes = st.text_area("Notes (allergies, sweetness, etc.)", height=80)
            submitted = st.form_submit_button("✅ Confirm Order")

        if submitted:
            if not customer_name or not phone:
                st.error("Name and phone are required.")
            else:
                order_id, timestamp = save_order_to_sheet(
                    customer_name, phone, order_type, notes, total_amount, cart_df_display
                )
                wa_link = generate_whatsapp_link(
                    order_id, customer_name, phone, order_type,
                    total_amount, timestamp, cart_df_display, notes
                )

                st.success(f"Order #{order_id} saved to Google Sheets.")
                st.markdown("#### Receipt")
                st.write(f"**Order ID:** {order_id}")
                st.write(f"**Time:** {timestamp}")
                st.write(f"**Name:** {customer_name}")
                st.write(f"**Phone:** {phone}")
                st.write(f"**Order Type:** {order_type}")
                if notes:
                    st.write(f"**Notes:** {notes}")
                st.write("---")
                st.dataframe(cart_df_display[["Name", "Qty", "Total"]], use_container_width=True)
                st.write(f"**Total:** {total_amount:,} UGX")

                if "XXXX" not in WHATSAPP_NUMBER:
                    st.markdown(f"[📲 Send order via WhatsApp]({wa_link})")
                    st.info("Tap the link above on your phone to open WhatsApp with the order pre-filled.")
                else:
                    st.warning("Set WHATSAPP_NUMBER in the code to enable WhatsApp integration.")

elif page == "Admin (Sheet View)":
    st.title("🛠 Admin – Orders from Google Sheet")
    try:
        df = load_orders_df()
        if df.empty:
            st.info("No orders yet.")
        else:
            st.dataframe(df, use_container_width=True)
    except Exception as e:
        st.error(f"Could not load data from Google Sheets: {e}")

elif page == "About":
    st.title("ℹ️ About BUBULIZER v3")
    st.write(
        """
        - UI: Streamlit  
        - Storage: Google Sheets (`BUBULIZER` → `Orders` worksheet)  
        - Orders: WhatsApp deep link for confirmation  
        - Hosting: Streamlit Community Cloud  

        This avoids SQLite and local files so it runs safely on Streamlit Cloud.
        """
    )
