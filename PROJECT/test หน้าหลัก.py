import sqlite3
import hashlib
import os
import datetime
#import qrcode
from io import BytesIO
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import messagebox

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


#c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\2.db

def get_db_connection():
    conn = sqlite3.connect(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\2.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # users: id, username, password_hash, is_admin
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_admin INTEGER DEFAULT 0
        )
    """)
    # products: id, name, category, price, stock, description
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL,
            stock INTEGER NOT NULL DEFAULT 0,
            description TEXT
        )
    """)
    # orders: id, user_id, total, created_at
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            total REAL NOT NULL,
            created_at TEXT NOT NULL,
            qrcode_path TEXT,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    # order_items: id, order_id, product_id, qty, price_each
    c.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            qty INTEGER NOT NULL,
            price_each REAL NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id),
            FOREIGN KEY(product_id) REFERENCES products(id)
        )
    """)

    conn.commit()
    conn.close()
def show_home_screen(self):
        self.clear_main()
        # Top bar with username, profile, cart button
        top = ctk.CTkFrame(self.main_frame)
        top.pack(fill="x", side="top", padx=8, pady=8)
        ctk.CTkLabel(top, text=f"PharmaCare +    ผู้ใช้: {self.current_user['username']}", font=("Arial", 14, "bold")).pack(side="left")
        btn_profile = ctk.CTkButton(top, text="Profile", width=100, command=self.show_profile)
        btn_profile.pack(side="right", padx=6)
        btn_cart = ctk.CTkButton(top, text=f"ตะกร้า ({self.cart_total_qty()})", width=130, command=self.show_cart)
        btn_cart.pack(side="right", padx=6)
        if self.current_user["is_admin"]:
            btn_admin = ctk.CTkButton(top, text="Admin", width=100, command=self.show_admin)
            btn_admin.pack(side="right", padx=6)

        # Left: categories
        left = ctk.CTkFrame(self.main_frame, width=180)
        left.pack(side="left", fill="y", padx=(8,4), pady=8)
        ctk.CTkLabel(left, text="หมวดหมู่", font=("Arial", 16, "bold")).pack(pady=6)

        # Fetch distinct categories from DB
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM products")
        cats = [r["category"] for r in c.fetchall()]
        conn.close()

        selected_category = ctk.StringVar(value="ทั้งหมด")
        def select_cat(cat):
            selected_category.set(cat)
            self.display_products_frame(cat)

        # Category buttons
        btn_all = ctk.CTkButton(left, text="ทั้งหมด", width=150, command=lambda: select_cat("ทั้งหมด"))
        btn_all.pack(pady=4)
        for cat in cats:
            b = ctk.CTkButton(left, text=cat, width=150, command=lambda c=cat: select_cat(c))
            b.pack(pady=4)

        # Center: products area (scrollable)
        center = ctk.CTkFrame(self.main_frame)
        center.pack(side="left", fill="both", expand=True, padx=(4,4), pady=8)

        self.products_container = ctk.CTkScrollableFrame(center)
        self.products_container.pack(fill="both", expand=True, padx=10, pady=6)

        # Right: persistent category list + small cart summary (optional)
        right = ctk.CTkFrame(self.main_frame, width=220)
        right.pack(side="right", fill="y", padx=(4,8), pady=8)
        ctk.CTkLabel(right, text="ตะกร้าสรุป", font=("Arial", 14, "bold")).pack(pady=6)
        self.cart_summary = ctk.CTkTextbox(right, width=200, height=200)
        self.cart_summary.pack(pady=6)
        self.update_cart_display_summary()

        # initially show all products
        self.display_products_frame("ทั้งหมด")

        def display_products_frame(self, category="ทั้งหมด"):
            # clear current product widgets
            for w in self.products_container.winfo_children():
                w.destroy()

            conn = get_db_connection()
            c = conn.cursor()
            if category == "ทั้งหมด":
                c.execute("SELECT * FROM products")
            else:
                c.execute("SELECT * FROM products WHERE category = ?", (category,))
            products = c.fetchall()
            conn.close()

            # display as cards
            for prod in products:
                card = ctk.CTkFrame(self.products_container, corner_radius=8)
                card.pack(fill="x", padx=8, pady=6)

                header = ctk.CTkFrame(card)
                header.pack(fill="x", pady=6, padx=6)
                ctk.CTkLabel(header, text=prod["name"], font=("Arial", 14, "bold")).pack(side="left")
                ctk.CTkLabel(header, text=f"{prod['price']:.2f} บาท", anchor="e").pack(side="right")

                body = ctk.CTkFrame(card)
                body.pack(fill="x", padx=6, pady=(0,8))
                ctk.CTkLabel(body, text=prod["description"] or "-", wraplength=500, justify="left").pack(side="left", padx=6)

                # qty selector + add to cart
                right_box = ctk.CTkFrame(body)
                right_box.pack(side="right", padx=10)
                qty_var = ctk.IntVar(value=1)
                qty_spinner = ctk.CTkEntry(right_box, width=60, textvariable=qty_var)
                qty_spinner.pack(pady=4)
                def add_this(p=prod, var=qty_var):
                    try:
                        q = int(var.get())
                    except:
                        messagebox.showerror("ผิดพลาด", "จำนวนไม่ถูกต้อง")
                        return
                    if q <= 0:
                        messagebox.showwarning("ผิดพลาด", "จำนวนต้องมากกว่า 0")
                        return
                    # check stock
                    if p["stock"] < q:
                        messagebox.showwarning("สต็อกไม่พอ", f"สินค้าคงเหลือ {p['stock']} ชิ้น")
                        return
                    self.add_to_cart(p["id"], q)
                btn = ctk.CTkButton(right_box, text="เพิ่มลงตะกร้า", command=add_this)
                btn.pack()

    # ---------- Cart management ----------
        def add_to_cart(self, product_id, qty=1):
            self.cart[product_id] = self.cart.get(product_id, 0) + qty
            # update button text
            self.update_cart_display_summary()
            # update cart button label at top (by re-rendering home screen top)
            self.show_home_screen()
    