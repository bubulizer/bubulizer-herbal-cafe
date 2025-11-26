import streamlit as st
import pandas as pd
import sqlite3
import os
import csv
from datetime import datetime
from urllib.parse import quote_plus

# =========================
# CONFIG & BRANDING
# =========================
APP_NAME = "BUBULIZER Herbal Café"
PRIMARY_COLOR = "#14532d"   # deep herbal green
ACCENT_COLOR = "#f59e0b"    # warm gold
LOGO_PATH = "C:/Users/DrPius/Documents/pius bubu/bubulizer_logo.png"  # e.g. "static/bubulizer_logo.png"

# WhatsApp business number in international format without + or spaces
# Example: "2567XXXXXXXX"  (Uganda/Nigeria)
WHATSAPP_NUMBER = "2348023808592"  # TODO: replace with real number

# File paths
BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, "bubulizer_db.sqlite")
CSV_PATH = os.path.join(BASE_DIR, "orders_log.csv")

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title=APP_NAME,
    page_icon="🍵",
    layout="centered"
)

# Simple CSS for branding
st.markdown(
    f"""
    <style>
    .stApp {{
        background-color: #f9fafb;
    }}
    .bubulizer-title {{
        color: {PRIMARY_COLOR};
    }}
    .bubulizer-accent {{
        color: {ACCENT_COLOR};
    }}
    </style>
    """,
    unsafe_allow_html=True
)

# =========================
# MENU DATA (CUSTOMISE THESE)
# =========================
menu_items = [
    ("Herbal Tea", "BUBULIZER Bridelia Tea",     "Bridelia, Yellow mombin, False daisy, African Mahogany, Colocynth, and African Limba Wood.",         20000),
    ("Herbal Tea", "BUBULIZER Small Leaf Tea",   "Small Leaf (Stone Breaker).",   20000),
    ("Chilli Pepper", "BUBULIZER Chilli Pepper Powder",     "Dried Chilli Pepper.",        2000),
    ("Spice",   "BUBULIZER Banga Soup Spice", "Nutmeg, Guinea plum, Paradise plum, Negro Pepper, Scent leaves, Cocoplum, and liquorice.",   2000),
    ("Spice",   "BUBULIZER Pepper Soup Spice", "Calabash Nutmeg, Aidan fruit, and Spice tree.",      1500),
    #("Smoothie",   "Banana Peanut Power",      "Banana, peanut, oats, soy milk.",         8500),
    ("Alcoholic Beverage",      "BUBULIZER Alcoholic Bitters",   "Treaed Water, Ethanol, Hog Plum, False Dalsy, Large Leaved Mahogany, Sausage Tree, Cattle Stick, and Caramel.",         10000),
    #("Juice",      "Carrot Skin Glow",         "Carrot, orange, turmeric.",               7500),
    #("Snack",      "Millet & Sesame Energy Balls (3)", "Millet, sesame, dates, coconut.", 5000),
    #("Snack",      "Herbal Sweet Potato Fries","Oven-baked, rosemary & thyme.",           6000),
]
menu_df = pd.DataFrame(menu_items, columns=["Category", "Name", "Description", "Price_NGN"])

# =========================
# DATABASE HELPERS
# =========================
def get_conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT,
            phone TEXT,
            order_type TEXT,
            notes TEXT,
            total_amount INTEGER,
            created_at TEXT
        )
        """
    )
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER,
            item_name TEXT,
            qty INTEGER,
            price_ngn INTEGER,
            total_ngn INTEGER,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
        """
    )
    conn.commit()
    conn.close()

def save_order_to_db(customer_name, phone, order_type, notes, total_amount, cart_df):
    created_at = datetime.now().isoformat(timespec="seconds")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO orders (customer_name, phone, order_type, notes, total_amount, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (customer_name, phone, order_type, notes, total_amount, created_at)
    )
    order_id = cur.lastrowid

    for _, row in cart_df.iterrows():
        cur.execute(
            """
            INSERT INTO order_items (order_id, item_name, qty, price_ngn, total_ugx)
            VALUES (?, ?, ?, ?, ?)
            """,
            (order_id, row["Name"], int(row["Qty"]), int(row["Price_NGN"]), int(row["Total"]))
        )

    conn.commit()
    conn.close()
    return order_id, created_at

# =========================
# CSV LOGGING
# =========================
def append_order_to_csv(order_id, customer_name, phone, order_type, notes, total_amount, created_at, cart_df):
    header_exists = os.path.exists(CSV_PATH)
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if not header_exists:
            writer.writerow([
                "order_id", "created_at", "customer_name", "phone", "order_type",
                "item_name", "qty", "price_ngn", "total_ngn", "notes", "order_total_ngn"
            ])
        for _, row in cart_df.iterrows():
            writer.writerow([
                order_id,
                created_at,
                customer_name,
                phone,
                order_type,
                row["Name"],
                int(row["Qty"]),
                int(row["Price_NGN"]),
                int(row["Total"]),
                notes,
                total_amount
            ])

# =========================
# WHATSAPP LINK
# =========================
def generate_whatsapp_link(order_id, customer_name, phone, order_type, total_amount, created_at, cart_df, notes=""):
    lines = []
    lines.append(f"{APP_NAME} Order")
    lines.append(f"Order ID: {order_id}")
    lines.append(f"Time: {created_at}")
    lines.append(f"Customer: {customer_name}")
    lines.append(f"Customer phone: {phone}")
    lines.append(f"Order type: {order_type}")
    if notes:
        lines.append(f"Notes: {notes}")
    lines.append("")
    lines.append("Items:")
    for _, row in cart_df.iterrows():
        lines.append(f"- {int(row['Qty'])} × {row['Name']} = {int(row['Total']):,} NGN")
    lines.append("")
    lines.append(f"TOTAL: {total_amount:,} NGN")

    message = "\n".join(lines)
    encoded = quote_plus(message)
    return f"https://wa.me/{WHATSAPP_NUMBER}?text={encoded}"

# =========================
# SESSION STATE (CART)
# =========================
if "cart" not in st.session_state:
    st.session_state.cart = []

def add_to_cart(item_name, qty):
    if qty <= 0:
        return
    row = menu_df[menu_df["Name"] == item_name].iloc[0]
    price = row["Price_NGN"]
    category = row["Category"]
    for item in st.session_state.cart:
        if item["Name"] == item_name:
            item["Qty"] += qty
            item["Total"] = item["Qty"] * item["Price_NGN"]
            break
    else:
        st.session_state.cart.append({
            "Category": category,
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

# Initialize DB
init_db()

# =========================
# SIDEBAR NAV
# =========================
with st.sidebar:
    if LOGO_PATH and os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, use_column_width=True)
    st.markdown(f"<h3 class='bubulizer-title'>{APP_NAME}</h3>", unsafe_allow_html=True)
    page = st.radio("Navigate", ["Home", "Menu & Order", "Order Summary", "Admin (Preview)", "About"])
    st.markdown("---")
    st.caption("BUBULIZER • Streamlit + SQLite + WhatsApp")

# =========================
# PAGES
# =========================
if page == "Home":
    st.markdown(f"<h1 class='bubulizer-title'>🍵 {APP_NAME}</h1>", unsafe_allow_html=True)
    st.subheader("Your marketplace for premium herbal wellness products.")
    st.write(
        """
        Welcome to **BUBULIZER Herbal Café**, a curated platform where you can discover and order a wide variety of **herbal products** from different sellers.

        Whether you're looking for BUBULIZER's signature teas and spices or unique items from other vendors, placing an order is simple:

        - 🛍️ Select items on the **Menu & Order** page
        - 📋 Review and finalize your order under **Order Summary**
        - 📲 Send your order instantly via **WhatsApp** with a single tap
        """
    )
    st.subheader("⚙️ Prototype Features")
    st.write(
        """
        This online cafe provides robust order management tools: every order is saved to a local **SQLite database** and logged as a **CSV file** for easy record-keeping and analysis in programs like Excel.
        """
    )
    st.info("💡 **Tip:** To make this platform accessible to the public, deploy this app on a cloud service like Streamlit Cloud or HuggingFace Spaces.")

elif page == "Menu & Order":
    st.title("📋 Menu & Order")
    categories = ["All"] + sorted(menu_df["Category"].unique())
    selected_cat = st.selectbox("Filter by category", categories)

    filtered_df = menu_df if selected_cat == "All" else menu_df[menu_df["Category"] == selected_cat]
    st.subheader("Menu")
    st.dataframe(filtered_df[["Category", "Name", "Description", "Price_NGN"]], use_container_width=True)

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
        cart_df_display["Price_NGN"] = cart_df_display["Price_NGN"].astype(int)
        cart_df_display["Total"] = cart_df_display["Total"].astype(int)
        st.dataframe(cart_df_display, use_container_width=True)
        total_amount = int(cart_df["Total"].sum())
        st.subheader(f"Estimated Total: {total_amount:,} NGN")
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
        cart_df_display["Price_NGN"] = cart_df_display["Price_NGN"].astype(int)
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
                cart_df_for_save = cart_df_display.copy()
                order_id, created_at = save_order_to_db(
                    customer_name, phone, order_type, notes, total_amount, cart_df_for_save
                )
                append_order_to_csv(order_id, customer_name, phone, order_type, notes,
                                    total_amount, created_at, cart_df_for_save)
                wa_link = generate_whatsapp_link(
                    order_id, customer_name, phone, order_type,
                    total_amount, created_at, cart_df_for_save, notes
                )

                st.success(f"Order #{order_id} saved.")
                st.markdown("#### Receipt")
                st.write(f"**Order ID:** {order_id}")
                st.write(f"**Time:** {created_at}")
                st.write(f"**Name:** {customer_name}")
                st.write(f"**Phone:** {phone}")
                st.write(f"**Order Type:** {order_type}")
                if notes:
                    st.write(f"**Notes:** {notes}")
                st.write("---")
                st.dataframe(cart_df_display[["Name", "Qty", "Total"]], use_container_width=True)
                st.write(f"**Total:** {total_amount:,} NGN")

                if "XXXX" not in WHATSAPP_NUMBER:
                    st.markdown(f"[📲 Send order via WhatsApp]({wa_link})", unsafe_allow_html=False)
                    st.info("Tap the button above on your phone to open WhatsApp with the order pre-filled.")
                else:
                    st.warning("Set WHATSAPP_NUMBER in the code to enable WhatsApp integration.")

elif page == "Admin (Preview)":
    st.title("🛠 Admin Preview (local only)")
    st.caption("Basic view of recent orders from SQLite (for testing).")
    try:
        conn = get_conn()
        df_orders = pd.read_sql_query("SELECT * FROM orders ORDER BY created_at DESC LIMIT 50", conn)
        conn.close()
        if df_orders.empty:
            st.info("No orders yet.")
        else:
            st.dataframe(df_orders, use_container_width=True)
    except Exception as e:
        st.error(f"Error reading DB: {e}")

elif page == "About":
    st.title("ℹ️ About BUBULIZER: Wellness & Flavor")
    st.markdown(
        """
        BUBULIZER serves as the digital order management platform for a select line of **authentic Herbal Teas, Spices, and Traditional Beverages**. Our products are sourced and prepared using a unique blend of natural, powerful ingredients.
        """
    )

    st.subheader("🌿 Our Featured Product Lineup")
    st.markdown(
        """
        Our catalog includes products like **BUBULIZER Bridelia Tea** (featuring ingredients such as Bridelia, Yellow mombin, and African Limba Wood), potent **BUBULIZER Spices** (including Banga Soup and Pepper Soup mixes), and our signature **BUBULIZER Alcoholic Bitters** (made with Hog Plum, Sausage Tree, and Caramel).
        """
    )

    st.subheader("🛠️ Application Features (Current Version)")
    st.write(
        """
        This version of the BUBULIZER ordering app is designed for streamlined efficiency, adding crucial management capabilities:

        * **Persistent Storage:** Order data is reliably stored using **SQLite**.
        * **Data Exports:** Simplified record keeping with **CSV exports** for all order history.
        * **Rapid Communication:** One-click **WhatsApp order sharing** to quickly notify staff or customers.
        * **Oversight:** A basic **admin preview** panel for quick status checks.
        """
    )

    st.subheader("☁️ Production Deployment Note")
    st.info(
        """
        This UI is a demonstration tool. For secure and scalable operation in a production environment, it is strongly recommended to connect this Streamlit interface to a hardened backend service (such as **Flask** or **FastAPI**) and deploy the entire system on a secure cloud platform.
        """
    )