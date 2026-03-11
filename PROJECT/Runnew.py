import os
import re
import sqlite3
import datetime
import shutil

# UI
import customtkinter as ctk
from tkinter import messagebox, filedialog

# Images
from PIL import Image, ImageTk, ImageOps, ImageDraw, ImageFont

# ----------------------------- CONFIG -----------------------------
APP_TITLE = "PharmaCare+"
DB = "pharmacy.db"
ASSETS_BG = os.path.join("assets", "backgrounds", "NewBackground.png")
ASSETS_QR = os.path.join("assets", "qr", "qr.png")
DIR_PRODUCTS = os.path.join("assets", "products")
DIR_SLIPS = "slips"
DIR_INVOICES = "invoices"

ADMIN_EMAILS = {"admin@pharmacare.local"}
ADMIN_USERNAMES = {"Admin"}
ADMIN_PASSWORD = "admin1234"  # ใช้สำหรับ seed admin ตัวอย่าง

# หมวด/ประเภทย่อย (ปรับได้)
CATEGORY_MAP = {
    "เวชสำอาง": ["ครีมกันแดด", "โฟมล้างหน้า", "เซรั่ม", "มอยส์เจอร์ไรเซอร์"],
    "สินค้าเพื่อสุขภาพ": ["วิตามิน", "อาหารเสริม", "เครื่องวัดความดัน", "สมุนไพร"],
    "ยา": ["ยาแก้ปวด", "ยาลดไข้", "ยาแก้แพ้", "ยาฆ่าเชื้อ"],
}

# -------------------------- UTIL & BOOTSTRAP -----------------------
def ensure_dirs():
    for p in [os.path.dirname(ASSETS_BG), os.path.dirname(ASSETS_QR), DIR_PRODUCTS, DIR_SLIPS, DIR_INVOICES]:
        if p and not os.path.exists(p):
            os.makedirs(p, exist_ok=True)


def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # users
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            password TEXT,
            phone TEXT,
            address TEXT,
            profile_image TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )

    # products
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            sale_price REAL,
            description TEXT,
            image_path TEXT,
            category TEXT,
            subcategory TEXT,
            stock INTEGER NOT NULL DEFAULT 0,
            sku TEXT,
            labels TEXT,
            warnings TEXT
        )
        """
    )

    # orders
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            shipping_method TEXT,
            shipping_address TEXT,
            subtotal REAL DEFAULT 0,
            discount REAL DEFAULT 0,
            shipping_fee REAL DEFAULT 0,
            vat REAL DEFAULT 0,
            grand_total REAL DEFAULT 0,
            slip_path TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            shipping_status TEXT NOT NULL DEFAULT 'draft',
            tracking_no TEXT,
            invoice_path TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT
        )
        """
    )

    # order_items
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            name TEXT,
            price REAL,
            qty INTEGER,
            line_total REAL DEFAULT 0,
            FOREIGN KEY(order_id) REFERENCES orders(id) ON DELETE CASCADE
        )
        """
    )

    # coupons (เผื่ออนาคต)
    c.execute(
        """
        CREATE TABLE IF NOT EXISTS coupons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            type TEXT,
            value REAL,
            min_spend REAL,
            start_at TEXT,
            end_at TEXT,
            is_active INTEGER DEFAULT 1
        )
        """
    )

    # seed admin (เฉพาะครั้งแรกเมื่อไม่มีผู้ใช้ admin)
    try:
        c.execute("SELECT 1 FROM users WHERE email=?", (next(iter(ADMIN_EMAILS)),))
        if not c.fetchone():
            c.execute(
                "INSERT INTO users (email, username, password, phone) VALUES (?, ?, ?, ?)",
                (next(iter(ADMIN_EMAILS)), next(iter(ADMIN_USERNAMES)), ADMIN_PASSWORD, "0812345678"),
            )
    except Exception:
        pass

    conn.commit()
    conn.close()


ensure_dirs()
init_db()


# ------------------------------- APP --------------------------------
class PharmaApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_TITLE)
        self.root.geometry("1280x800")
        ctk.set_appearance_mode("light")  # default light
        ctk.set_default_color_theme("green")

        self.main_frame = ctk.CTkFrame(root)
        self.main_frame.pack(fill="both", expand=True)

        self.cart = {}
        self._is_on_cart_page = False

        self.current_username = None
        self.current_email = None
        self.is_admin = False

        self._theme_is_dark = False

        self.login_page()

    # ------------------------- Shared helpers ----------------------
    def _bg(self):
        try:
            if os.path.exists(ASSETS_BG):
                img_bg = Image.open(ASSETS_BG).resize((1920, 1080))
                self._bg_photo = ImageTk.PhotoImage(img_bg)
                lbl = ctk.CTkLabel(self.main_frame, image=self._bg_photo, text="")
                lbl.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception:
            pass

    def _toggle_theme(self):
        self._theme_is_dark = not self._theme_is_dark
        ctk.set_appearance_mode("dark" if self._theme_is_dark else "light")

    def _reset_session(self):
        self.cart = {}
        self._is_on_cart_page = False

    def _ensure_cart(self):
        if not hasattr(self, "cart") or self.cart is None:
            self.cart = {}

    def _logout(self):
        self._reset_session()
        self.current_username = None
        self.current_email = None
        self.is_admin = False
        self.login_page()

    # --------------------------- Login -----------------------------
    def login_page(self):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg()

        title = ctk.CTkLabel(self.main_frame, text=f"{APP_TITLE} – Login", font=("Oswald", 26, "bold"))
        title.place(relx=0.5, rely=0.20, anchor="center")

        ctk.CTkLabel(self.main_frame, text="Email").place(relx=0.5, rely=0.30, anchor="center")
        self.email_entry = ctk.CTkEntry(self.main_frame, width=260, placeholder_text="กรอก Email")
        self.email_entry.place(relx=0.5, rely=0.34, anchor="center")

        ctk.CTkLabel(self.main_frame, text="Username").place(relx=0.5, rely=0.39, anchor="center")
        self.username_entry = ctk.CTkEntry(self.main_frame, width=260, placeholder_text="กรอก Username")
        self.username_entry.place(relx=0.5, rely=0.43, anchor="center")

        ctk.CTkLabel(self.main_frame, text="Password").place(relx=0.5, rely=0.48, anchor="center")
        self.password_entry = ctk.CTkEntry(self.main_frame, width=260, show="*", placeholder_text="กรอก Password")
        self.password_entry.place(relx=0.5, rely=0.52, anchor="center")

        ctk.CTkButton(self.main_frame, text="เข้าสู่ระบบ", fg_color="green", command=self.login).place(relx=0.5, rely=0.58, anchor="center")
        ctk.CTkButton(self.main_frame, text="สมัครบัญชี", command=self.register_page).place(relx=0.5, rely=0.64, anchor="center")
        ctk.CTkButton(self.main_frame, text="ลืมรหัสผ่าน", fg_color="#ddd", text_color="#333", command=self.forgot_password_page).place(relx=0.5, rely=0.69, anchor="center")

        ctk.CTkButton(self.main_frame, text="🌗 Theme", width=80, command=self._toggle_theme).place(relx=0.95, rely=0.05, anchor="e")

    def login(self):
        email = self.email_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        if not email or not username or not password:
            messagebox.showerror("Error", "กรุณากรอกข้อมูลให้ครบ")
            return
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT email, username, password FROM users WHERE email=?", (email,))
        row = c.fetchone(); conn.close()
        if not row:
            messagebox.showerror("Error", "ไม่พบบัญชีนี้ กรุณาสมัครสมาชิก")
            return
        if username != row[1] or password != row[2]:
            messagebox.showerror("Error", "ชื่อผู้ใช้หรือรหัสผ่านไม่ถูกต้อง")
            return
        self.current_email = email
        self.current_username = username
        self.is_admin = (email in ADMIN_EMAILS) or (username in ADMIN_USERNAMES)
        self._reset_session()
        if self.is_admin:
            self.open_admin()
        else:
            self.main_page(username)

    # ------------------------- Register ----------------------------
    def register_page(self):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg()

        ctk.CTkLabel(self.main_frame, text="สมัครสมาชิก", font=("Oswald", 24, "bold")).place(relx=0.5, rely=0.20, anchor="center")

        ctk.CTkLabel(self.main_frame, text="Email").place(relx=0.5, rely=0.28, anchor="center")
        self.reg_email = ctk.CTkEntry(self.main_frame, width=300, placeholder_text="example@mail.com")
        self.reg_email.place(relx=0.5, rely=0.32, anchor="center")

        ctk.CTkLabel(self.main_frame, text="Username (≥8 ตัว มีตัวเลข+อักษร)").place(relx=0.5, rely=0.37, anchor="center")
        self.reg_user = ctk.CTkEntry(self.main_frame, width=300)
        self.reg_user.place(relx=0.5, rely=0.41, anchor="center")

        ctk.CTkLabel(self.main_frame, text="Password (≥8 ตัว มีตัวเลข+อักษร)").place(relx=0.5, rely=0.46, anchor="center")
        self.reg_pass = ctk.CTkEntry(self.main_frame, width=300, show="*")
        self.reg_pass.place(relx=0.5, rely=0.50, anchor="center")

        ctk.CTkLabel(self.main_frame, text="Confirm Password").place(relx=0.5, rely=0.55, anchor="center")
        self.reg_pass2 = ctk.CTkEntry(self.main_frame, width=300, show="*")
        self.reg_pass2.place(relx=0.5, rely=0.59, anchor="center")

        ctk.CTkLabel(self.main_frame, text="Phone (0xxxxxxxxx)").place(relx=0.5, rely=0.64, anchor="center")
        self.reg_phone = ctk.CTkEntry(self.main_frame, width=300)
        self.reg_phone.place(relx=0.5, rely=0.68, anchor="center")

        ctk.CTkButton(self.main_frame, text="สมัครสมาชิก", fg_color="green", command=self.register).place(relx=0.5, rely=0.75, anchor="center")
        ctk.CTkButton(self.main_frame, text="กลับ", command=self.login_page).place(relx=0.5, rely=0.80, anchor="center")

    def register(self):
        email = self.reg_email.get().strip()
        username = self.reg_user.get().strip()
        password = self.reg_pass.get().strip()
        password2 = self.reg_pass2.get().strip()
        phone = self.reg_phone.get().strip()

        if not email or not username or not password or not password2 or not phone:
            messagebox.showerror("Error", "กรุณากรอกข้อมูลให้ครบ")
            return
        if len(username) < 8 or not re.search("[a-zA-Z]", username) or not re.search("[0-9]", username):
            messagebox.showerror("Error", "Username ต้องมี ≥8 ตัว และมีตัวเลข+อักษร")
            return
        if len(password) < 8 or not re.search("[a-zA-Z]", password) or not re.search("[0-9]", password):
            messagebox.showerror("Error", "Password ต้องมี ≥8 ตัว และมีตัวเลข+อักษร")
            return
        if password != password2:
            messagebox.showerror("Error", "Password ไม่ตรงกัน")
            return
        if not re.fullmatch(r"0\d{9}", phone):
            messagebox.showerror("Error", "เบอร์โทรไม่ถูกต้อง (เช่น 0812345678)")
            return

        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (email, username, password, phone) VALUES (?, ?, ?, ?)",
                (email, username, password, phone),
            )
            conn.commit()
            messagebox.showinfo("สำเร็จ", f"สมัครสมาชิกสำเร็จ ยินดีต้อนรับ {username}")
            self.current_email = email
            self.current_username = username
            self.is_admin = (email in ADMIN_EMAILS) or (username in ADMIN_USERNAMES)
            self._reset_session()
            self.main_page(username)
        except sqlite3.IntegrityError as e:
            if "email" in str(e):
                messagebox.showerror("Error", "Email ถูกใช้งานแล้ว")
            elif "username" in str(e):
                messagebox.showerror("Error", "Username ถูกใช้งานแล้ว")
        finally:
            conn.close()

    # ----------------------- Forgot Password ----------------------
    def forgot_password_page(self):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg()

        ctk.CTkLabel(self.main_frame, text="ลืมรหัสผ่าน", font=("Oswald", 24, "bold")).place(relx=0.5, rely=0.20, anchor="center")

        ctk.CTkLabel(self.main_frame, text="Email").place(relx=0.5, rely=0.30, anchor="center")
        self.fp_email = ctk.CTkEntry(self.main_frame, width=300)
        self.fp_email.place(relx=0.5, rely=0.34, anchor="center")

        ctk.CTkLabel(self.main_frame, text="Phone (ยืนยันร่วม)").place(relx=0.5, rely=0.39, anchor="center")
        self.fp_phone = ctk.CTkEntry(self.main_frame, width=300)
        self.fp_phone.place(relx=0.5, rely=0.43, anchor="center")

        ctk.CTkLabel(self.main_frame, text="รหัสผ่านใหม่").place(relx=0.5, rely=0.48, anchor="center")
        self.fp_new = ctk.CTkEntry(self.main_frame, width=300, show="*")
        self.fp_new.place(relx=0.5, rely=0.52, anchor="center")

        ctk.CTkLabel(self.main_frame, text="ยืนยันรหัสผ่านใหม่").place(relx=0.5, rely=0.57, anchor="center")
        self.fp_new2 = ctk.CTkEntry(self.main_frame, width=300, show="*")
        self.fp_new2.place(relx=0.5, rely=0.61, anchor="center")

        ctk.CTkButton(self.main_frame, text="รีเซ็ต", fg_color="green", command=self._reset_password_submit).place(relx=0.5, rely=0.68, anchor="center")
        ctk.CTkButton(self.main_frame, text="กลับ", command=self.login_page).place(relx=0.5, rely=0.73, anchor="center")

    def _reset_password_submit(self):
        email = self.fp_email.get().strip()
        phone = self.fp_phone.get().strip()
        newpass = self.fp_new.get().strip()
        conf = self.fp_new2.get().strip()
        if not email or not phone or not newpass or not conf:
            messagebox.showerror("Error", "กรอกข้อมูลให้ครบ")
            return
        if not re.fullmatch(r"0\d{9}", phone):
            messagebox.showerror("Error", "เบอร์โทรไม่ถูกต้อง")
            return
        if len(newpass) < 8 or not re.search("[a-zA-Z]", newpass) or not re.search("[0-9]", newpass):
            messagebox.showerror("Error", "Password ใหม่ต้องมี ≥8 ตัวและมีตัวเลข+อักษร")
            return
        if newpass != conf:
            messagebox.showerror("Error", "รหัสผ่านใหม่ไม่ตรงกัน")
            return
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=? AND phone=?", (email, phone))
        row = c.fetchone()
        if not row:
            conn.close(); messagebox.showerror("Error", "ไม่พบบัญชีตาม Email/เบอร์")
            return
        c.execute("UPDATE users SET password=? WHERE id=?", (newpass, row[0]))
        conn.commit(); conn.close()
        messagebox.showinfo("สำเร็จ", "เปลี่ยนรหัสผ่านเรียบร้อย")
        self.login_page()

    # --------------------------- Main ------------------------------
    def main_page(self, username):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg()

        ctk.CTkLabel(self.main_frame, text=f"ยินดีต้อนรับ {username}", font=("Oswald", 20, "bold")).place(relx=0.08, rely=0.08, anchor="w")
        ctk.CTkButton(self.main_frame, text="🔙 Log out", fg_color="#b00020", command=self._logout).place(relx=0.95, rely=0.95, anchor="e")
        ctk.CTkButton(self.main_frame, text="🌗 Theme", width=80, command=self._toggle_theme).place(relx=0.88, rely=0.95, anchor="e")

        if not self.is_admin:
            # ลูกค้า
            ctk.CTkButton(self.main_frame, text="👤 โปรไฟล์", width=120, command=self.Profile_Page).place(relx=0.95, rely=0.08, anchor="e")
            ctk.CTkButton(self.main_frame, text="🛒 ตะกร้า", width=120, fg_color="green", command=self.cart_page).place(relx=0.95, rely=0.14, anchor="e")
            ctk.CTkButton(self.main_frame, text="🧾 คำสั่งซื้อของฉัน", width=160, fg_color="#0b7dda", command=self.orders_history_page).place(relx=0.80, rely=0.08, anchor="e")
        else:
            # แอดมิน
            ctk.CTkButton(self.main_frame, text="🛠 Admin", width=120, command=self.open_admin).place(relx=0.95, rely=0.08, anchor="e")

        toggle_btn = ctk.CTkSwitch(
        master=self.main_frame,
        text="🌞 / 🌙",
        command=lambda: ctk.set_appearance_mode("dark" if ctk.get_appearance_mode()=="Light" else "light")
        )
        toggle_btn.place(relx=0.95, rely=0.05, anchor="ne")

        content = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=16)
        content.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.80, relheight=0.72)

        # ซ้าย: หมวดหมู่
        left = ctk.CTkFrame(content, width=180, corner_radius=10)
        left.pack(side="left", fill="y", padx=10, pady=10)
        ctk.CTkLabel(left, text="หมวดหมู่", font=("Arial", 16, "bold")).pack(pady=10)

        self.selected_category = "ทั้งหมด"
        self.selected_subcategory = None

        self.sub_panel = ctk.CTkFrame(content, width=180, corner_radius=10)
        self.sub_panel.pack(side="left", fill="y", padx=10, pady=10)
        ctk.CTkLabel(self.sub_panel, text="ประเภท", font=("Arial", 16, "bold")).pack(pady=10)

        def show_sub(cname):
            # clear sub_panel except title
            for w in self.sub_panel.winfo_children():
                if isinstance(w, ctk.CTkLabel) and w.cget("text") == "ประเภท":
                    continue
                w.destroy()
            self.selected_category = cname
            self.selected_subcategory = None
            subs = CATEGORY_MAP.get(cname, [])
            ctk.CTkLabel(self.sub_panel, text=f"{cname}", font=("Arial", 14, "bold")).pack(pady=(0, 6))
            if subs:
                ctk.CTkButton(self.sub_panel, text="ทั้งหมด", width=150, command=lambda: (setattr(self, "selected_subcategory", None), self.render_products())).pack(pady=5)
                for s in subs:
                    ctk.CTkButton(self.sub_panel, text=s, width=150, command=lambda ss=s: (setattr(self, "selected_subcategory", ss), self.render_products())).pack(pady=5)
            self.render_products()

        for cat in ["ทั้งหมด"] + list(CATEGORY_MAP.keys()):
            ctk.CTkButton(left, text=cat, width=150, command=lambda x=cat: show_sub(x)).pack(pady=5)

        # กลาง: สินค้า
        center = ctk.CTkFrame(content, corner_radius=10)
        center.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        self.products_container = ctk.CTkScrollableFrame(center, label_text="สินค้า", fg_color="white")
        self.products_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ขวา: ตะกร้าสรุป (เฉพาะลูกค้า)
        if not self.is_admin:
            right = ctk.CTkFrame(content, width=220, corner_radius=10)
            right.pack(side="right", fill="y", padx=10, pady=10)
            ctk.CTkLabel(right, text="ตะกร้าสรุป", font=("Arial", 16, "bold")).pack(pady=10)
            self.cart_summary = ctk.CTkTextbox(right, width=200, height=220)
            self.cart_summary.pack(pady=10)
            self.cart_summary.insert("end", "ตะกร้าว่าง")
            ctk.CTkButton(right, text="ชำระสินค้า", fg_color="green", command=self.cart_page).pack(pady=(8, 2))
            self._update_cart_summary()

        # init show all
        show_sub("ทั้งหมด")

    # ---------------------- Product Listing ------------------------
    def render_products(self):
        for w in self.products_container.winfo_children():
            w.destroy()
        where = []
        params = []
        if self.selected_category != "ทั้งหมด":
            where.append("category = ?"); params.append(self.selected_category)
            if self.selected_subcategory:
                where.append("subcategory = ?"); params.append(self.selected_subcategory)
        sql = "SELECT id, name, price, IFNULL(sale_price, price), description, image_path, stock FROM products"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC"
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute(sql, params); rows = c.fetchall(); conn.close()
        if not rows:
            ctk.CTkLabel(self.products_container, text="(ยังไม่มีสินค้าในหมวดนี้)").pack(pady=12)
            return

        def cut(t, n=160):
            t = (t or "").strip(); return t if len(t) <= n else t[:n-1] + "…"

        for pid, name, price, effective_price, desc, img_path, stock in rows:
            card = ctk.CTkFrame(self.products_container, corner_radius=12)
            card.pack(fill="x", padx=8, pady=6)

            img_lbl = ctk.CTkLabel(card, text="")
            img_lbl.pack(side="left", padx=10, pady=10)
            try:
                if img_path and os.path.exists(img_path):
                    im = Image.open(img_path); im.thumbnail((80, 80))
                    ph = ImageTk.PhotoImage(im)
                    img_lbl.configure(image=ph); img_lbl.image = ph
                else:
                    img_lbl.configure(text="(no image)")
            except Exception:
                img_lbl.configure(text="(no image)")

            texts = ctk.CTkFrame(card, fg_color="transparent"); texts.pack(side="left", fill="x", expand=True, padx=6, pady=10)
            price_line = f"{effective_price:,.2f} บาท" + (f"  (ปกติ {price:,.2f})" if effective_price != price else "")
            ctk.CTkLabel(texts, text=name, font=("Arial", 14, "bold")).pack(anchor="w")
            ctk.CTkLabel(texts, text=price_line).pack(anchor="w")
            ctk.CTkLabel(texts, text=f"สต็อกคงเหลือ: {int(stock)} ชิ้น").pack(anchor="w")
            ctk.CTkLabel(texts, text=cut(desc), justify="left", anchor="w", wraplength=420).pack(anchor="w", pady=(2, 6))

            if not self.is_admin:
                btn = ctk.CTkButton(card, text=("เพิ่มลงตะกร้า" if stock > 0 else "สินค้าหมด"), width=120,
                                    fg_color=("#4CAF50" if stock > 0 else "#9E9E9E"),
                                    command=(lambda p=pid, n=name, pr=effective_price: self.add_to_cart(p, n, pr, 1)) if stock>0 else None)
                btn.pack(side="right", padx=10)
                if stock <= 0:
                    btn.configure(state="disabled")

    def add_to_cart(self, pid, name, price, qty=1):
        self._ensure_cart()
        # ตรวจสต็อก
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT stock FROM products WHERE id=?", (pid,))
        r = c.fetchone(); conn.close()
        if not r:
            messagebox.showerror("ตะกร้า", "ไม่พบข้อมูลสินค้า"); return
        stock = int(r[0] or 0)
        cur = self.cart.get(pid, {}).get("qty", 0)
        if cur + qty > stock:
            messagebox.showwarning("ตะกร้า", f"❌ สินค้าหมดหรือมีไม่พอ (เหลือ {stock})")
            return
        if pid in self.cart:
            self.cart[pid]["qty"] += qty
        else:
            self.cart[pid] = {"name": name, "price": float(price), "qty": qty}
        self._update_cart_summary()
        messagebox.showinfo("ตะกร้า", f"เพิ่ม {name} x{qty} ลงตะกร้าแล้ว")

    def _update_cart_summary(self):
        if not hasattr(self, "cart_summary"):
            return
        total_qty = sum(i["qty"] for i in self.cart.values())
        total_price = sum(float(i["price"]) * i["qty"] for i in self.cart.values())
        lines = [f"- {v['name']} x{v['qty']}" for v in list(self.cart.items())[:6]]
        self.cart_summary.configure(state="normal")
        self.cart_summary.delete("1.0", "end")
        if not self.cart:
            self.cart_summary.insert("end", "ตะกร้าว่าง")
        else:
            if lines:
                self.cart_summary.insert("end", "\n".join(lines) + "\n\n")
            self.cart_summary.insert("end", f"รวม {total_qty} ชิ้น\n{total_price:,.2f} บาท")
        self.cart_summary.configure(state="disabled")

    # --------------------------- Cart ------------------------------
    def cart_page(self):
        self._is_on_cart_page = True
        self._ensure_cart()
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg()

        username = self.current_username or "Guest"
        ctk.CTkButton(self.main_frame, text="🔙", width=50, command=lambda: (setattr(self, "_is_on_cart_page", False), self.main_page(username))).place(relx=0.95, rely=0.08, anchor="e")

        wrap = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=16)
        wrap.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.80, relheight=0.72)
        ctk.CTkLabel(wrap, text="ตะกร้าสินค้า", font=("Arial", 20, "bold")).pack(pady=10)

        self.cart_box = ctk.CTkScrollableFrame(wrap, fg_color="#bdfcc9", corner_radius=16, width=600, height=360)
        self.cart_box.pack(fill="both", expand=True, padx=40, pady=10)

        footer = ctk.CTkFrame(wrap, fg_color="transparent"); footer.pack(fill="x", padx=40, pady=(4, 8))
        self.total_label = ctk.CTkLabel(footer, text="รวม: 0.00 บาท", font=("Arial", 16, "bold"))
        self.total_label.pack(side="left")
        ctk.CTkButton(footer, text="ล้างตะกร้า", fg_color="#999", command=self._clear_cart).pack(side="right", padx=(8,0))
        ctk.CTkButton(footer, text="ชำระสินค้า", fg_color="#9bffb2", text_color="#000", command=self.review_order_page).pack(side="right", padx=(8,0))

        self._render_cart_items()

    def _render_cart_items(self):
        for w in self.cart_box.winfo_children():
            w.destroy()
        if not self.cart:
            ctk.CTkLabel(self.cart_box, text="ยังไม่มีสินค้าในตะกร้า", font=("Arial", 16)).pack(pady=20)
            self.total_label.configure(text="รวม: 0.00 บาท")
            self._update_cart_summary(); return
        total = 0.0
        header = ctk.CTkFrame(self.cart_box, fg_color="transparent")
        header.pack(fill="x", pady=(4,6), padx=14)
        for i, txt, w in [(0, "สินค้า", 280), (1, "ราคา", 80), (2, "จำนวน", 140), (3, "รวมย่อย", 100)]:
            ctk.CTkLabel(header, text=txt, width=w, anchor=("w" if i==0 else "e"), font=("Arial", 14, "bold")).grid(row=0, column=i, sticky="we")
        for pid, item in list(self.cart.items()):
            name, price, qty = item["name"], float(item["price"]), int(item["qty"])
            sub = price * qty; total += sub
            row = ctk.CTkFrame(self.cart_box, fg_color="white", corner_radius=10)
            row.pack(fill="x", padx=12, pady=5)
            ctk.CTkLabel(row, text=name, anchor="w").grid(row=0, column=0, sticky="w", padx=(10,4), pady=8)
            ctk.CTkLabel(row, text=f"{price:,.2f}", anchor="e", width=80).grid(row=0, column=1, sticky="e", padx=6)
            box = ctk.CTkFrame(row, fg_color="transparent"); box.grid(row=0, column=2, padx=6)
            ctk.CTkButton(box, text="-", width=28, command=lambda p=pid: self._change_qty(p, -1)).pack(side="left", padx=4)
            ctk.CTkLabel(box, text=str(qty), width=36, anchor="center").pack(side="left", padx=4)
            ctk.CTkButton(box, text="+", width=28, command=lambda p=pid: self._change_qty(p, +1)).pack(side="left", padx=4)
            ctk.CTkLabel(row, text=f"{sub:,.2f}", anchor="e", width=100).grid(row=0, column=3, sticky="e", padx=6)
            ctk.CTkButton(row, text="ลบ", fg_color="#b00020", command=lambda p=pid: self._remove_item(p)).grid(row=0, column=4, padx=(6, 10))
        self.total_label.configure(text=f"รวม: {total:,.2f} บาท")
        self._update_cart_summary()

    def _change_qty(self, pid, delta):
        if pid not in self.cart: return
        new_qty = self.cart[pid]["qty"] + int(delta)
        if new_qty <= 0:
            del self.cart[pid]
        else:
            # check stock
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("SELECT stock FROM products WHERE id=?", (pid,))
            r = c.fetchone(); conn.close()
            stock = int(r[0] or 0)
            if new_qty > stock:
                messagebox.showwarning("ตะกร้า", f"❌ มีเพียง {stock} ชิ้นในสต็อก")
                return
            self.cart[pid]["qty"] = new_qty
        self._render_cart_items()

    def _clear_cart(self):
        if not self.cart:
            messagebox.showinfo("ตะกร้า", "ตะกร้าว่างอยู่แล้ว"); return
        if not messagebox.askyesno("ยืนยัน", "ต้องการล้างตะกร้า?"):
            return
        self.cart.clear(); self._render_cart_items()

    def _remove_item(self, pid):
        if pid in self.cart:
            del self.cart[pid]
            self._render_cart_items()

    # ---------------------- Review & Payment -----------------------
    def review_order_page(self):
        if not self.cart:
            messagebox.showinfo("ตะกร้า", "ตะกร้าว่าง"); return
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg()

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT address FROM users WHERE email=?", (self.current_email,))
        r = c.fetchone(); conn.close()
        current_address = (r[0] if r and r[0] else "")

        ctk.CTkButton(self.main_frame, text="🔙", width=50, command=self.cart_page).place(relx=0.95, rely=0.08, anchor="e")

        wrap = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=16)
        wrap.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.78, relheight=0.72)
        ctk.CTkLabel(wrap, text="สรุปคำสั่งซื้อ (บิล)", font=("Arial", 20, "bold")).pack(pady=(14, 10))

        box = ctk.CTkScrollableFrame(wrap, width=900, height=300, corner_radius=12)
        box.pack(padx=16, pady=8, fill="x")
        header = ctk.CTkFrame(box, fg_color="transparent"); header.pack(fill="x", pady=(4,6), padx=8)
        for i, txt, w in [(0, "สินค้า", 260), (1, "ราคา", 120), (2, "จำนวน", 120), (3, "รวมย่อย", 120)]:
            ctk.CTkLabel(header, text=txt, width=w, anchor=("w" if i==0 else "e"), font=("Arial", 14, "bold")).grid(row=0, column=i, sticky="we")

        subtotal = 0.0
        for pid, it in self.cart.items():
            sub = float(it["price"]) * int(it["qty"]); subtotal += sub
            row = ctk.CTkFrame(box, fg_color="white", corner_radius=8); row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text=it["name"], anchor="w", width=260).grid(row=0, column=0, sticky="w", padx=(8,4), pady=6)
            ctk.CTkLabel(row, text=f"{float(it['price']):,.2f}", anchor="e", width=120).grid(row=0, column=1, sticky="e")
            ctk.CTkLabel(row, text=str(it["qty"]), anchor="e", width=120).grid(row=0, column=2, sticky="e")
            ctk.CTkLabel(row, text=f"{sub:,.2f}", anchor="e", width=120).grid(row=0, column=3, sticky="e")

        # ค่าขนส่ง/ส่วนลด/VAT/Grand
        shipping_fee = 0.0
        discount = 0.0
        vat = round((subtotal - discount + shipping_fee) * 0.07, 2)
        grand = round(subtotal - discount + shipping_fee + vat, 2)

        bottom = ctk.CTkFrame(wrap, fg_color="transparent"); bottom.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(bottom, text=f"ยอดรวม: {grand:,.2f} บาท", font=("Arial", 16, "bold")).pack(anchor="w")

        line2 = ctk.CTkFrame(bottom, fg_color="transparent"); line2.pack(fill="x", pady=(8,6))
        ctk.CTkLabel(line2, text="วิธีจัดส่ง:").pack(side="left", padx=(0,6))
        self._ship_method_var = ctk.StringVar(value="Kerry")
        ctk.CTkOptionMenu(line2, values=["Kerry", "J&T", "ไปรษณีย์ไทย", "Flash"], variable=self._ship_method_var, width=160).pack(side="left", padx=(0,20))

        ctk.CTkLabel(bottom, text="ที่อยู่จัดส่ง:").pack(anchor="w")
        self._addr_box_for_order = ctk.CTkTextbox(bottom, width=600, height=90)
        self._addr_box_for_order.pack(anchor="w", pady=(4,0))
        self._addr_box_for_order.insert("1.0", current_address or "กรอกที่อยู่จัดส่งที่นี่...")

        ctk.CTkButton(bottom, text="ยืนยันการสั่งซื้อ", fg_color="green", text_color="white", command=lambda: self._create_order_and_go_payment(subtotal, discount, shipping_fee, vat, grand)).place(relx=0.88, rely=0.75, anchor="e")

    def _create_order_and_go_payment(self, subtotal, discount, shipping_fee, vat, grand):
        ship_method = self._ship_method_var.get() if hasattr(self, "_ship_method_var") else "Kerry"
        address = self._addr_box_for_order.get("1.0", "end").strip() if hasattr(self, "_addr_box_for_order") else ""
        if not address or address == "กรอกที่อยู่จัดส่งที่นี่...":
            messagebox.showwarning("ที่อยู่", "กรุณากรอกที่อยู่จัดส่ง"); return
        if not self.cart:
            messagebox.showerror("ออเดอร์", "ตะกร้าว่าง"); return
        now = datetime.datetime.now().isoformat(timespec="seconds")
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            c.execute(
                """
                INSERT INTO orders (user_email, shipping_method, shipping_address, subtotal, discount, shipping_fee, vat, grand_total, status, shipping_status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', 'draft', ?, ?)
                """,
                (self.current_email, ship_method, address, float(subtotal), float(discount), float(shipping_fee), float(vat), float(grand), now, now),
            )
            oid = c.lastrowid
            for pid, it in self.cart.items():
                c.execute(
                    "INSERT INTO order_items (order_id, product_id, name, price, qty, line_total) VALUES (?, ?, ?, ?, ?, ?)",
                    (oid, pid, it["name"], float(it["price"]), int(it["qty"]), float(it["price"]) * int(it["qty"]))
                )
            conn.commit()
        except Exception as e:
            conn.rollback(); messagebox.showerror("ออเดอร์", f"ไม่สามารถสร้างออเดอร์ได้:\n{e}"); return
        finally:
            conn.close()
        self.payment_page(oid)

    def payment_page(self, order_id: int):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg()
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT grand_total, slip_path, status FROM orders WHERE id=?", (order_id,))
        row = c.fetchone(); conn.close()
        if not row:
            messagebox.showerror("ออเดอร์", "ไม่พบออเดอร์"); self.main_page(self.current_username or "Guest"); return
        grand, slip_path, status = float(row[0]), row[1], row[2]

        ctk.CTkButton(self.main_frame, text="🔙", width=50, command=self.review_order_page).place(relx=0.95, rely=0.08, anchor="e")
        ctk.CTkLabel(self.main_frame, text="ชำระเงิน", font=("Oswald", 32, "bold")).place(relx=0.6, rely=0.22, anchor="center")
        ctk.CTkLabel(self.main_frame, text=f"ยอดที่ต้องชำระ: {grand:,.2f} บาท", font=("Oswald", 18, "bold")).place(relx=0.6, rely=0.28, anchor="center")

        # QR
        if os.path.exists(ASSETS_QR):
            try:
                img_qr = Image.open(ASSETS_QR).resize((360, 220))
                self.qr_photo = ImageTk.PhotoImage(img_qr)
                ctk.CTkLabel(self.main_frame, image=self.qr_photo, text="").place(relx=0.6, rely=0.50, anchor="center")
            except Exception:
                ctk.CTkLabel(self.main_frame, text="(QR ไม่พร้อม)").place(relx=0.6, rely=0.50, anchor="center")
        else:
            ctk.CTkLabel(self.main_frame, text="(ไม่พบไฟล์ QR)").place(relx=0.6, rely=0.50, anchor="center")

        self._slip_label = ctk.CTkLabel(self.main_frame, text=f"สลิป: {'มีแล้ว' if slip_path else 'ยังไม่อัปโหลด'}")
        self._slip_label.place(relx=0.6, rely=0.60, anchor="center")

        ctk.CTkButton(self.main_frame, text="อัปโหลดสลิป", fg_color="#0288D1", command=lambda: self._choose_slip(order_id)).place(relx=0.53, rely=0.68, anchor="center")
        ctk.CTkButton(self.main_frame, text="ยืนยันส่งสลิป", fg_color="green", command=lambda: self._submit_payment(order_id)).place(relx=0.67, rely=0.68, anchor="center")

    def _choose_slip(self, order_id: int):
        fpath = filedialog.askopenfilename(title="เลือกไฟล์สลิป", filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"), ("All files", "*.*")])
        if not fpath: return
        os.makedirs(DIR_SLIPS, exist_ok=True)
        ext = os.path.splitext(fpath)[1].lower()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join(DIR_SLIPS, f"order_{order_id}_{ts}{ext}")
        try:
            shutil.copyfile(fpath, dest)
            self._pending_slip_path = dest
            self._slip_label.configure(text=f"สลิป: {os.path.basename(dest)}")
        except Exception as e:
            messagebox.showerror("สลิป", f"อัปโหลดล้มเหลว: {e}")

    def _submit_payment(self, order_id: int):
        slip = getattr(self, "_pending_slip_path", None)
        if not slip or not os.path.exists(slip):
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("SELECT slip_path FROM orders WHERE id=?", (order_id,))
            r = c.fetchone(); conn.close()
            if not r or not r[0] or not os.path.exists(r[0]):
                messagebox.showwarning("สลิป", "กรุณาอัปโหลดสลิปก่อน"); return
            slip = r[0]
        now = datetime.datetime.now().isoformat(timespec="seconds")
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            c.execute("UPDATE orders SET slip_path=?, status='submitted', updated_at=? WHERE id=?", (slip, now, order_id))
            conn.commit()
        except Exception as e:
            conn.rollback(); messagebox.showerror("ออเดอร์", f"บันทึกสลิปล้มเหลว:\n{e}"); return
        finally:
            conn.close()
        self._reset_session(); messagebox.showinfo("ส่งสลิปแล้ว", "เราได้รับสลิปของคุณแล้ว รอแอดมินตรวจสอบค่ะ/ครับ")
        self.main_page(self.current_username or "Guest")

    # --------------------------- Profile ---------------------------
    def Profile_Page(self):
        for w in self.main_frame.winfo_children():
            w.destroy(); self._bg()
        ctk.CTkButton(self.main_frame, text="🔙", width=50, command=lambda: self.main_page(self.current_username)).place(relx=0.95, rely=0.08, anchor="e")

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT address, profile_image, phone FROM users WHERE email=?", (self.current_email,))
        row = c.fetchone(); conn.close()
        address = (row[0] or "กรอกที่อยู่ของคุณที่นี่...") if row else "กรอกที่อยู่ของคุณที่นี่..."
        image_path = row[1] if row else None
        phone = (row[2] or "ยังไม่ได้ระบุ") if row else "ยังไม่ได้ระบุ"

        self.profile_img_label = ctk.CTkLabel(self.main_frame, text="(ไม่มีรูป)", width=150, height=150, fg_color="#EEE", corner_radius=12)
        self.profile_img_label.place(relx=0.3, rely=0.5, anchor="center")
        if image_path and os.path.exists(image_path):
            try:
                im = Image.open(image_path); im = ImageOps.fit(im, (150, 150), Image.LANCZOS)
                self.profile_img = ImageTk.PhotoImage(im)
                self.profile_img_label.configure(image=self.profile_img, text="")
            except Exception:
                pass
        ctk.CTkButton(self.main_frame, text="เลือกรูปโปรไฟล์", fg_color="#0288D1", command=self._choose_profile_image).place(relx=0.3, rely=0.65, anchor="center")

        ctk.CTkLabel(self.main_frame, text=f"ชื่อผู้ใช้ : {self.current_username}", font=("Oswald", 18, "bold")).place(relx=0.5, rely=0.45, anchor="w")
        ctk.CTkLabel(self.main_frame, text=f"Email : {self.current_email}", font=("Oswald", 18, "bold")).place(relx=0.5, rely=0.50, anchor="w")
        ctk.CTkLabel(self.main_frame, text=f"เบอร์ : {phone}", font=("Oswald", 18, "bold")).place(relx=0.5, rely=0.75, anchor="w")

        self.phone_entry = ctk.CTkEntry(self.main_frame, width=180, placeholder_text="กรอกเบอร์ใหม่หรือแก้ไขเบอร์")
        self.phone_entry.place(relx=0.53, rely=0.80, anchor="w")
        ctk.CTkButton(self.main_frame, text="บันทึกเบอร์ใหม่", fg_color="green", command=lambda: self.update_phone(self.phone_entry.get().strip())).place(relx=0.65, rely=0.80, anchor="w")

        ctk.CTkLabel(self.main_frame, text="ที่อยู่:", font=("Oswald", 18, "bold")).place(relx=0.5, rely=0.55, anchor="w")
        self.address_box = ctk.CTkTextbox(self.main_frame, width=380, height=100, border_width=2, border_color="gray30", fg_color="#F7F7F7", text_color="black")
        self.address_box.place(relx=0.66, rely=0.60, anchor="center")
        self.address_box.insert("1.0", address)
        self.address_box.configure(state="disabled")

        self.btn_save_addr = ctk.CTkButton(self.main_frame, text="บันทึก", width=90, fg_color="#007AFF", command=self._save_address)
        self.btn_save_addr.place(relx=0.66, rely=0.70, anchor="center"); self.btn_save_addr.configure(state="disabled")
        self.btn_edit_addr = ctk.CTkButton(self.main_frame, text="แก้ไข", width=90, fg_color="#4CAF50", command=self._enter_edit_address_mode)
        self.btn_edit_addr.place(relx=0.72, rely=0.70, anchor="center")
        self._address_placeholder = "กรอกที่อยู่ของคุณที่นี่..."

    def update_phone(self, new_phone):
        if not re.fullmatch(r"0\d{9}", new_phone):
            messagebox.showerror("Error", "เบอร์โทรไม่ถูกต้อง (เช่น 0812345678)"); return
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("UPDATE users SET phone=? WHERE email=?", (new_phone, self.current_email))
        conn.commit(); conn.close(); messagebox.showinfo("สำเร็จ", "บันทึกเบอร์โทรแล้ว"); self.Profile_Page()

    def _enter_edit_address_mode(self):
        self.address_box.configure(state="normal", fg_color="#E0F7FA", border_color="#0288D1")
        cur = self.address_box.get("1.0", "end").strip()
        if cur == self._address_placeholder:
            self.address_box.delete("1.0", "end")
        self.btn_edit_addr.configure(state="disabled"); self.btn_save_addr.configure(state="normal")

    def _save_address(self):
        address = self.address_box.get("1.0", "end").strip()
        if not address:
            messagebox.showwarning("แจ้งเตือน", "กรุณากรอกที่อยู่ก่อนบันทึก"); return
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("UPDATE users SET address=? WHERE email=?", (address, self.current_email))
        conn.commit(); conn.close()
        self.address_box.configure(state="disabled", fg_color="#F7F7F7", border_color="gray30")
        self.btn_edit_addr.configure(state="normal"); self.btn_save_addr.configure(state="disabled")
        messagebox.showinfo("สำเร็จ", "บันทึกที่อยู่เรียบร้อย")

    def _choose_profile_image(self):
        path = filedialog.askopenfilename(title="เลือกรูปโปรไฟล์", filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")])
        if not path: return
        try:
            im = Image.open(path); im = ImageOps.fit(im, (150, 150), Image.LANCZOS)
            self.profile_img = ImageTk.PhotoImage(im)
            self.profile_img_label.configure(image=self.profile_img, text="")
        except Exception as e:
            messagebox.showerror("รูปภาพ", f"ไม่สามารถโหลดรูปภาพได้: {e}"); return
        conn = sqlite3.connect(DB); c = conn.cursor(); c.execute("UPDATE users SET profile_image=? WHERE email=?", (path, self.current_email)); conn.commit(); conn.close()
        messagebox.showinfo("สำเร็จ", "อัปเดตรูปโปรไฟล์เรียบร้อย")

    # ---------------------- Order History (User) -------------------
    def orders_history_page(self):
        for w in self.main_frame.winfo_children():
            w.destroy(); self._bg()
        ctk.CTkButton(self.main_frame, text="🔙", width=50, command=lambda: self.main_page(self.current_username)).place(relx=0.95, rely=0.08, anchor="e")
        wrap = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=16)
        wrap.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.82, relheight=0.72)
        ctk.CTkLabel(wrap, text="คำสั่งซื้อของฉัน", font=("Oswald", 22, "bold")).pack(pady=(14,8))
        box = ctk.CTkScrollableFrame(wrap, width=1000, height=520)
        box.pack(fill="both", expand=True, padx=14, pady=10)

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute(
            """
            SELECT id, grand_total, status, shipping_status, tracking_no, slip_path, invoice_path, created_at
            FROM orders WHERE user_email=? ORDER BY id DESC
            """,
            (self.current_email,)
        )
        orders = c.fetchall(); conn.close()
        if not orders:
            ctk.CTkLabel(box, text="(ยังไม่มีคำสั่งซื้อ)").pack(pady=20); return

        head = ctk.CTkFrame(box, fg_color="transparent"); head.pack(fill="x", padx=8, pady=(6,2))
        for i, txt, w in [(0,"เลขที่",80),(1,"วันที่",180),(2,"ยอดรวม",140),(3,"สถานะ",160),(4,"จัดส่ง",160),(5,"Tracking",160),(6,"การกระทำ",260)]:
            ctk.CTkLabel(head, text=txt, width=w, anchor=("w" if i==0 else "center"), font=("Arial", 14, "bold")).grid(row=0, column=i, sticky="we")

        for oid, total, st, shipst, track, slip, inv, created in orders:
            row = ctk.CTkFrame(box, fg_color="white", corner_radius=8); row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text=f"#{oid}", width=80, anchor="w").grid(row=0, column=0, padx=6, pady=8, sticky="w")
            ctk.CTkLabel(row, text=str(created), width=180).grid(row=0, column=1)
            ctk.CTkLabel(row, text=f"{float(total):,.2f} ฿", width=140).grid(row=0, column=2)
            ctk.CTkLabel(row, text=st, width=160).grid(row=0, column=3)
            ctk.CTkLabel(row, text=shipst, width=160).grid(row=0, column=4)
            ctk.CTkLabel(row, text=(track or "-"), width=160).grid(row=0, column=5)
            btns = ctk.CTkFrame(row, fg_color="transparent"); btns.grid(row=0, column=6, padx=6)
            ctk.CTkButton(btns, text="ดูรายละเอียด", width=110, command=lambda x=oid: self._open_order_detail_user(x)).pack(side="left", padx=4)
            if inv and os.path.exists(inv):
                ctk.CTkButton(btns, text="ดูใบเสร็จ", fg_color="#0288D1", text_color="white", width=110, command=lambda p=inv: self._open_invoice_preview(p)).pack(side="left", padx=4)
            else:
                ctk.CTkButton(btns, text="(ยังไม่มีใบเสร็จ)", state="disabled", width=110).pack(side="left", padx=4)
            if slip and os.path.exists(slip):
                ctk.CTkButton(btns, text="ดูสลิป", width=90, command=lambda p=slip: self._open_invoice_preview(p)).pack(side="left", padx=4)

    def _open_invoice_preview(self, path: str):
        if not path or not os.path.exists(path):
            messagebox.showerror("ไฟล์", "ไม่พบไฟล์"); return
        top = ctk.CTkToplevel(self.root); top.title(os.path.basename(path)); top.geometry("820x640")
        frm = ctk.CTkScrollableFrame(top, width=800, height=600); frm.pack(fill="both", expand=True, padx=10, pady=10)
        try:
            im = Image.open(path); im.thumbnail((760, 1200))
            photo = ImageTk.PhotoImage(im)
            lbl = ctk.CTkLabel(frm, image=photo, text=""); lbl.image = photo; lbl.pack(pady=10)
        except Exception as e:
            ctk.CTkLabel(frm, text=f"ไม่สามารถแสดงภาพได้: {e}").pack(pady=20)

    def _open_order_detail_user(self, order_id: int):
        top = ctk.CTkToplevel(self.root); top.title(f"รายละเอียดออเดอร์ #{order_id}"); top.geometry("720x560")
        box = ctk.CTkScrollableFrame(top, width=680, height=460, label_text=f"ออเดอร์ #{order_id}")
        box.pack(fill="both", expand=True, padx=10, pady=10)
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT shipping_method, shipping_address, grand_total, status, shipping_status, tracking_no, created_at FROM orders WHERE id=?", (order_id,))
        head = c.fetchone()
        c.execute("SELECT name, price, qty, line_total FROM order_items WHERE order_id=?", (order_id,))
        items = c.fetchall(); conn.close()
        if head:
            sm, addr, total, st, shipst, track, created = head
            info = f"วันที่: {created}\nวิธีจัดส่ง: {sm}\nสถานะ: {st} | จัดส่ง: {shipst}\nTracking: {track or '-'}\nที่อยู่: {addr}\nยอดรวม: {float(total):,.2f} บาท"
            ctk.CTkLabel(box, text=info, justify="left").pack(anchor="w", padx=10, pady=(6,10))
        headf = ctk.CTkFrame(box, fg_color="transparent"); headf.pack(fill="x", padx=10)
        for i, txt, w in [(0,"สินค้า",300),(1,"ราคา",120),(2,"จำนวน",120),(3,"รวมย่อย",120)]:
            ctk.CTkLabel(headf, text=txt, width=w, anchor=("w" if i==0 else "e"), font=("Arial", 14, "bold")).grid(row=0, column=i, sticky="we")
        for name, price, qty, line_total in items:
            sub = (line_total if line_total is not None else float(price)*int(qty))
            row = ctk.CTkFrame(box, fg_color="white", corner_radius=6); row.pack(fill="x", padx=10, pady=4)
            ctk.CTkLabel(row, text=name, width=300, anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=6)
            ctk.CTkLabel(row, text=f"{float(price):,.2f}", width=120, anchor="e").grid(row=0, column=1, sticky="e")
            ctk.CTkLabel(row, text=str(int(qty)), width=120, anchor="e").grid(row=0, column=2, sticky="e")
            ctk.CTkLabel(row, text=f"{sub:,.2f}", width=120, anchor="e").grid(row=0, column=3, sticky="e")

    # --------------------------- Admin -----------------------------
    def open_admin(self):
        for w in self.main_frame.winfo_children():
            w.destroy(); self._bg()
        ctk.CTkButton(self.main_frame, text="🔙", width=50, command=lambda: self.main_page(self.current_username or "Admin")).place(relx=0.95, rely=0.08, anchor="e")
        container = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20)
        container.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.80, relheight=0.70)

        # Left: product list
        left = ctk.CTkFrame(container, width=280, corner_radius=12); left.pack(side="left", fill="y", padx=10, pady=10)
        ctk.CTkLabel(left, text="รายการสินค้า", font=("Oswald", 18, "bold")).pack(pady=(12,6))
        self.list_panel = ctk.CTkScrollableFrame(left, width=260, height=420)
        self.list_panel.pack(fill="both", expand=True, padx=10, pady=10)
        ctk.CTkButton(left, text="รีเฟรชรายการ", command=self._admin_refresh_products).pack(pady=(0,10))

        # Right: form
        right = ctk.CTkFrame(container, corner_radius=12); right.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkButton(self.main_frame, text="เช็คออเดอร์", fg_color="#555", command=self.open_orders_admin).place(relx=0.74, rely=0.09, anchor="e")
        ctk.CTkLabel(right, text="จัดการสินค้า", font=("Oswald", 18, "bold")).grid(row=0, column=0, columnspan=4, pady=(12,8), sticky="w")

        ctk.CTkLabel(right, text="ชื่อสินค้า").grid(row=1, column=0, sticky="e", padx=8, pady=6)
        self.p_name = ctk.CTkEntry(right, width=320, placeholder_text="เช่น วิตามินซี 500mg"); self.p_name.grid(row=1, column=1, columnspan=2, sticky="w", padx=8, pady=6)
        ctk.CTkLabel(right, text="ราคา (บาท)").grid(row=2, column=0, sticky="e", padx=8, pady=6)
        self.p_price = ctk.CTkEntry(right, width=160, placeholder_text="เช่น 199"); self.p_price.grid(row=2, column=1, sticky="w", padx=8, pady=6)
        ctk.CTkLabel(right, text="สต็อก").grid(row=2, column=2, sticky="e", padx=8, pady=6)
        self.p_stock = ctk.CTkEntry(right, width=120, placeholder_text="เช่น 50"); self.p_stock.grid(row=2, column=3, sticky="w", padx=8, pady=6)
        ctk.CTkLabel(right, text="รายละเอียด").grid(row=3, column=0, sticky="ne", padx=8, pady=6)
        self.p_desc = ctk.CTkTextbox(right, width=320, height=120); self.p_desc.grid(row=3, column=1, columnspan=2, sticky="w", padx=8, pady=6)

        self.preview = ctk.CTkLabel(right, text="(ยังไม่มีรูป)", width=160, height=160, fg_color="#f1f1f1", corner_radius=12)
        self.preview.grid(row=1, column=4, rowspan=3, padx=(16,8), pady=6)

        ctk.CTkLabel(right, text="หมวดหมู่").grid(row=4, column=0, sticky="e", padx=8, pady=6)
        self.p_cat = ctk.CTkOptionMenu(right, values=list(CATEGORY_MAP.keys()), width=160, command=self._on_admin_cat_change)
        self.p_cat.grid(row=4, column=1, sticky="w", padx=8, pady=6)
        ctk.CTkLabel(right, text="ประเภทย่อย").grid(row=4, column=2, sticky="e", padx=8, pady=6)
        self.p_subcat = ctk.CTkOptionMenu(right, values=[""], width=160)
        self.p_subcat.grid(row=4, column=3, sticky="w", padx=8, pady=6)

        ctk.CTkButton(right, text="เลือกรูปภาพ…", command=self._admin_pick_image).grid(row=5, column=4, sticky="n", padx=8, pady=(0,12))
        row_btn = ctk.CTkFrame(right, fg_color="transparent"); row_btn.grid(row=6, column=0, columnspan=4, sticky="we", padx=8, pady=(10,0))
        ctk.CTkButton(row_btn, text="เพิ่มใหม่", fg_color="#2e7d32", command=self._admin_create).pack(side="left", padx=6)
        ctk.CTkButton(row_btn, text="บันทึก", fg_color="#1976d2", command=self._admin_save).pack(side="left", padx=6)
        ctk.CTkButton(row_btn, text="ลบ", fg_color="#b00020", command=self._admin_delete).pack(side="left", padx=6)
        ctk.CTkButton(row_btn, text="ล้างฟอร์ม", command=self._admin_clear_form).pack(side="left", padx=6)

        first_cat = list(CATEGORY_MAP.keys())[0]
        self.p_cat.set(first_cat); self._on_admin_cat_change(first_cat)
        self._admin_refresh_products()

    def _on_admin_cat_change(self, selected):
        subs = CATEGORY_MAP.get(selected, []) or [""]
        self.p_subcat.configure(values=subs); self.p_subcat.set(subs[0])

    def _admin_pick_image(self):
        path = filedialog.askopenfilename(title="เลือกรูปสินค้า", filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")])
        if not path: return
        try:
            im = Image.open(path); im.thumbnail((180, 180))
            ph = ImageTk.PhotoImage(im)
            self.preview.configure(image=ph, text=""); self.preview.image = ph
            self.product_image_path = path
        except Exception as e:
            messagebox.showerror("รูปภาพ", f"แสดงตัวอย่างรูปไม่ได้:\n{e}")

    def _admin_refresh_products(self):
        for w in self.list_panel.winfo_children(): w.destroy()
        conn = sqlite3.connect(DB); c = conn.cursor(); c.execute("SELECT id, name, IFNULL(sale_price, price) FROM products ORDER BY id DESC"); rows = c.fetchall(); conn.close()
        if not rows:
            ctk.CTkLabel(self.list_panel, text="(ยังไม่มีสินค้า)").pack(pady=10); return
        for pid, name, price in rows:
            ctk.CTkButton(self.list_panel, text=f"  {name} - {price:.2f} บาท", width=240, command=lambda p=pid: self._admin_load_into_form(p)).pack(fill="x", padx=6, pady=4)

    def _admin_load_into_form(self, product_id: int):
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT id, name, price, sale_price, description, image_path, category, subcategory, stock FROM products WHERE id=?", (product_id,))
        row = c.fetchone(); conn.close()
        if not row:
            messagebox.showerror("โหลดสินค้า", "ไม่พบข้อมูลสินค้า"); return
        self.selected_product_id = row[0]
        name, price, sale_price, desc, img_path, cat, sub, stock = row[1], row[2], row[3], row[4], row[5], row[6], row[7], int(row[8] or 0)
        self.p_name.delete(0, "end"); self.p_name.insert(0, name)
        self.p_price.delete(0, "end"); self.p_price.insert(0, f"{(sale_price if sale_price is not None else price):g}")
        self.p_desc.delete("1.0", "end"); self.p_desc.insert("1.0", desc or "")
        self.p_stock.delete(0, "end"); self.p_stock.insert(0, str(stock))
        self.product_image_path = img_path
        self.preview.configure(image=None, text="(ยังไม่มีรูป)"); self.preview.image = None
        if img_path and os.path.exists(img_path):
            try:
                im = Image.open(img_path); im.thumbnail((180, 180))
                self.admin_img_photo = ImageTk.PhotoImage(im)
                self.preview.configure(image=self.admin_img_photo, text=""); self.preview.image = self.admin_img_photo
            except Exception:
                pass
        if cat not in CATEGORY_MAP:
            self.p_cat.configure(values=list(CATEGORY_MAP.keys()) + [cat])
        else:
            self.p_cat.configure(values=list(CATEGORY_MAP.keys()))
        self.p_cat.set(cat or list(CATEGORY_MAP.keys())[0])
        subs = CATEGORY_MAP.get(self.p_cat.get(), []) or [""]
        self.p_subcat.configure(values=subs); self.p_subcat.set(sub if sub in subs else subs[0])

    def _admin_create(self):
        self.selected_product_id = None
        self.p_name.delete(0, "end"); self.p_price.delete(0, "end"); self.p_desc.delete("1.0", "end")
        self.p_stock.delete(0, "end")
        self.product_image_path = None
        self.preview.configure(image=None, text="(ยังไม่มีรูป)"); self.preview.image = None
        first_cat = list(CATEGORY_MAP.keys())[0]; self.p_cat.set(first_cat); self._on_admin_cat_change(first_cat)

    def _admin_save(self):
        name = self.p_name.get().strip()
        price_txt = self.p_price.get().strip() or "0"
        stock_txt = (self.p_stock.get() or "0").strip()
        desc = self.p_desc.get("1.0", "end").strip()
        cat = self.p_cat.get().strip(); sub = self.p_subcat.get().strip()
        try:
            price = float(price_txt); stock = int(stock_txt)
            if stock < 0: raise ValueError
        except ValueError:
            messagebox.showerror("บันทึก", "ราคา/สต็อกไม่ถูกต้อง"); return
        if self.selected_product_id is not None and not getattr(self, "product_image_path", None):
            conn_old = sqlite3.connect(DB); c_old = conn_old.cursor(); c_old.execute("SELECT image_path FROM products WHERE id=?", (self.selected_product_id,)); old = c_old.fetchone(); conn_old.close()
            if old and old[0]: self.product_image_path = old[0]
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            if self.selected_product_id is None:
                c.execute("INSERT INTO products (name, price, description, image_path, category, subcategory, stock) VALUES (?, ?, ?, ?, ?, ?, ?)", (name, price, desc, getattr(self, "product_image_path", None), cat, sub, stock))
                conn.commit(); self.selected_product_id = c.lastrowid; messagebox.showinfo("บันทึก", "เพิ่มสินค้าเรียบร้อย")
            else:
                c.execute("UPDATE products SET name=?, price=?, description=?, image_path=?, category=?, subcategory=?, stock=? WHERE id=?", (name, price, desc, getattr(self, "product_image_path", None), cat, sub, stock, self.selected_product_id))
                conn.commit(); messagebox.showinfo("บันทึก", "อัปเดตสินค้าเรียบร้อย")
        finally:
            conn.close()
        self._admin_refresh_products(); self._admin_load_into_form(self.selected_product_id)

    def _admin_delete(self):
        if self.selected_product_id is None:
            messagebox.showwarning("ลบสินค้า", "กรุณาเลือกสินค้าที่จะลบก่อน"); return
        if not messagebox.askyesno("ยืนยัน", "ต้องการลบสินค้านี้หรือไม่?"): return
        conn = sqlite3.connect(DB); c = conn.cursor(); c.execute("DELETE FROM products WHERE id=?", (self.selected_product_id,)); conn.commit(); conn.close()
        messagebox.showinfo("ลบสินค้า", "ลบสินค้าเรียบร้อย"); self._admin_refresh_products(); self._admin_create()

    # ------------------------ Admin Orders -------------------------
    def open_orders_admin(self):
        for w in self.main_frame.winfo_children():
            w.destroy(); self._bg()
        ctk.CTkButton(self.main_frame, text="🔙", width=50, command=self.open_admin).place(relx=0.95, rely=0.08, anchor="e")
        wrap = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=16)
        wrap.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.82, relheight=0.72)
        ctk.CTkLabel(wrap, text="เช็คออเดอร์", font=("Oswald", 22, "bold")).pack(pady=(14,8))
        top = ctk.CTkFrame(wrap, fg_color="transparent"); top.pack(fill="x", padx=10, pady=(0,8))
        ctk.CTkLabel(top, text="สถานะ:").pack(side="left", padx=(0,6))
        self._order_status_var = ctk.StringVar(value="submitted")
        ctk.CTkOptionMenu(top, values=["submitted","pending","approved","rejected"], variable=self._order_status_var, width=160).pack(side="left", padx=(0,10))
        ctk.CTkButton(top, text="รีเฟรช", command=self._admin_refresh_orders).pack(side="left")
        body = ctk.CTkFrame(wrap, fg_color="transparent"); body.pack(fill="both", expand=True, padx=10, pady=10)
        left = ctk.CTkScrollableFrame(body, width=280, height=420, label_text="รายการออเดอร์"); left.pack(side="left", fill="y")
        self._orders_list_panel = left
        right = ctk.CTkFrame(body, corner_radius=12); right.pack(side="left", fill="both", expand=True, padx=10)
        self._order_detail_panel = right
        ctk.CTkLabel(self._order_detail_panel, text="เลือกรายการทางซ้ายเพื่อดูรายละเอียด").pack(pady=20)
        self._admin_refresh_orders()

    def _admin_refresh_orders(self):
        for w in self._orders_list_panel.winfo_children():
            if isinstance(w, ctk.CTkLabel):
                continue
            w.destroy()
        status = self._order_status_var.get() if hasattr(self, "_order_status_var") else "submitted"
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT id, user_email, grand_total, status, shipping_status, created_at FROM orders WHERE status=? ORDER BY id DESC", (status,))
        rows = c.fetchall(); conn.close()
        if not rows:
            ctk.CTkLabel(self._orders_list_panel, text="(ไม่พบออเดอร์)").pack(pady=10); return
        for oid, email, total, st, shipst, created in rows:
            ctk.CTkButton(self._orders_list_panel, text=f"#{oid} | {email}\n฿{total:,.2f} | {st} | {shipst}", command=lambda o=oid: self._admin_open_order(o)).pack(fill="x", padx=6, pady=6)

    def _admin_open_order(self, order_id: int):
        for w in self._order_detail_panel.winfo_children(): w.destroy()
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT user_email, shipping_method, shipping_address, grand_total, slip_path, status, shipping_status, tracking_no, created_at FROM orders WHERE id=?", (order_id,))
        head = c.fetchone()
        if not head:
            conn.close(); ctk.CTkLabel(self._order_detail_panel, text="ไม่พบออเดอร์นี้").pack(pady=20); return
        email, shipm, addr, total, slip, st, shipst, track, created = head
        ctk.CTkLabel(self._order_detail_panel, text=f"ออเดอร์ #{order_id}", font=("Oswald", 20, "bold")).pack(pady=(10,6))
        ctk.CTkLabel(self._order_detail_panel, text=f"ลูกค้า: {email}").pack(anchor="w", padx=12)
        ctk.CTkLabel(self._order_detail_panel, text=f"วิธีจัดส่ง: {shipm}").pack(anchor="w", padx=12)
        ctk.CTkLabel(self._order_detail_panel, text=f"ยอดรวม: {total:,.2f} บาท").pack(anchor="w", padx=12)
        ctk.CTkLabel(self._order_detail_panel, text=f"ที่อยู่: {addr}").pack(anchor="w", padx=12, pady=(0,8))
        ctk.CTkLabel(self._order_detail_panel, text=f"สถานะ: {st} | จัดส่ง: {shipst}").pack(anchor="w", padx=12)
        items_box = ctk.CTkScrollableFrame(self._order_detail_panel, width=520, height=220, label_text="รายการสินค้า"); items_box.pack(fill="x", padx=12, pady=8)
        c.execute("SELECT product_id, name, price, qty FROM order_items WHERE order_id=?", (order_id,)); its = c.fetchall(); conn.close()
        if not its:
            ctk.CTkLabel(items_box, text="(ไม่มีรายการ)").pack(pady=10)
        else:
            headf = ctk.CTkFrame(items_box, fg_color="transparent"); headf.pack(fill="x", padx=6, pady=(4,2))
            for i, txt, w in [(0,"สินค้า",260),(1,"ราคา",120),(2,"จำนวน",120)]:
                ctk.CTkLabel(headf, text=txt, width=w, anchor=("w" if i==0 else "e"), font=("Arial", 14, "bold")).grid(row=0, column=i, sticky="we")
            for pid, name, price, qty in its:
                row = ctk.CTkFrame(items_box, fg_color="white", corner_radius=6); row.pack(fill="x", padx=6, pady=3)
                ctk.CTkLabel(row, text=name, width=260, anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=6)
                ctk.CTkLabel(row, text=f"{float(price):,.2f}", width=120, anchor="e").grid(row=0, column=1, sticky="e")
                ctk.CTkLabel(row, text=str(qty), width=120, anchor="e").grid(row=0, column=2, sticky="e")

        btns = ctk.CTkFrame(self._order_detail_panel, fg_color="transparent"); btns.pack(fill="x", padx=12, pady=(8,0))
        ctk.CTkButton(btns, text="อนุมัติ", fg_color="#2e7d32", command=lambda: self._approve_order(order_id)).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="ปฏิเสธ", fg_color="#b00020", command=lambda: self._reject_order(order_id)).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="ออกใบเสร็จ (PNG)", fg_color="#0288D1", command=lambda oid=order_id: self._generate_invoice_and_store(oid)).pack(side="left", padx=4)

        ship = ctk.CTkFrame(self._order_detail_panel, fg_color="transparent"); ship.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(ship, text="สถานะจัดส่ง:").pack(side="left", padx=(0,6))
        self._ship_status_var = ctk.StringVar(value=shipst or "draft")
        ctk.CTkOptionMenu(ship, values=["draft","processing","shipped","delivered"], variable=self._ship_status_var, width=180).pack(side="left", padx=(0,10))
        ctk.CTkLabel(ship, text="Tracking:").pack(side="left", padx=(10,6))
        self._tracking_entry = ctk.CTkEntry(ship, width=220); 
        if track: self._tracking_entry.insert(0, track)
        self._tracking_entry.pack(side="left", padx=(0,10))
        ctk.CTkButton(ship, text="บันทึกจัดส่ง", command=lambda: self._save_shipping(order_id)).pack(side="left")

    def _approve_order(self, order_id: int):
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            c.execute("SELECT product_id, qty FROM order_items WHERE order_id=?", (order_id,))
            rows = c.fetchall()
            for pid, qty in rows:
                c.execute("SELECT name, stock FROM products WHERE id=?", (pid,))
                r = c.fetchone()
                if not r: raise Exception(f"ไม่พบสินค้า ID {pid}")
                name, stock = r[0], int(r[1] or 0)
                if int(qty) > stock: raise Exception(f"สต็อก {name} เหลือ {stock} ไม่พอ {qty}")
            for pid, qty in rows:
                c.execute("UPDATE products SET stock = stock - ? WHERE id=?", (int(qty), pid))
            now = datetime.datetime.now().isoformat(timespec="seconds")
            conn.commit()  # ให้สถานะสินค้า up-to-date ก่อนทำใบเสร็จ
        except Exception as e:
            conn.rollback(); conn.close(); messagebox.showerror("อนุมัติล้มเหลว", str(e)); return
        # สร้างใบเสร็จ + แนบลงคำสั่งซื้อ
        invoice_path = self._generate_invoice_png(order_id)
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("UPDATE orders SET status='approved', shipping_status='processing', updated_at=?, invoice_path=? WHERE id=?", (datetime.datetime.now().isoformat(timespec="seconds"), invoice_path, order_id))
        conn.commit(); conn.close()
        messagebox.showinfo("ออเดอร์", "อนุมัติและตัดสต็อกเรียบร้อย (สร้างใบเสร็จแล้ว)")
        self._admin_refresh_orders()

    def _reject_order(self, order_id: int):
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            now = datetime.datetime.now().isoformat(timespec="seconds")
            c.execute("UPDATE orders SET status='rejected', updated_at=? WHERE id=?", (now, order_id))
            conn.commit(); messagebox.showinfo("ออเดอร์", "ปฏิเสธออเดอร์เรียบร้อย")
        except Exception as e:
            conn.rollback(); messagebox.showerror("ผิดพลาด", str(e))
        finally:
            conn.close()
        self._admin_refresh_orders()

    def _save_shipping(self, order_id: int):
        shipst = self._ship_status_var.get() if hasattr(self, "_ship_status_var") else "draft"
        track = self._tracking_entry.get().strip() if hasattr(self, "_tracking_entry") else ""
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            now = datetime.datetime.now().isoformat(timespec="seconds")
            c.execute("UPDATE orders SET shipping_status=?, tracking_no=?, updated_at=? WHERE id=?", (shipst, track, now, order_id))
            conn.commit(); messagebox.showinfo("อัปเดตจัดส่ง", "บันทึกสถานะจัดส่งเรียบร้อย")
        except Exception as e:
            conn.rollback(); messagebox.showerror("ผิดพลาด", str(e))
        finally:
            conn.close()
        self._admin_open_order(order_id)

    # --------------------- Invoice generation ----------------------
    def _generate_invoice_png(self, order_id: int, vat_rate: float = 0.07):
        os.makedirs(DIR_INVOICES, exist_ok=True)
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT user_email, shipping_address, grand_total, created_at, subtotal, discount, shipping_fee, vat FROM orders WHERE id=?", (order_id,))
        head = c.fetchone()
        if not head:
            conn.close(); messagebox.showerror("ใบเสร็จ", "ไม่พบออเดอร์"); return None
        user_email, ship_addr, grand_total, created_at, subtotal, discount, shipping_fee, vat = head
        c.execute("SELECT name, price, qty, line_total FROM order_items WHERE order_id=?", (order_id,))
        items = c.fetchall(); conn.close()
        if subtotal is None:
            subtotal = sum((it[3] if it[3] is not None else float(it[1]) * int(it[2])) for it in items)
        if discount is None: discount = 0.0
        if shipping_fee is None: shipping_fee = 0.0
        if vat is None:
            vat = round((subtotal - discount + shipping_fee) * vat_rate, 2)
        grand_total = round(subtotal - discount + shipping_fee + vat, 2)

        W, H = 1000, 140 + 40*len(items) + 260
        img = Image.new("RGB", (W, H), "white"); draw = ImageDraw.Draw(img)
        try:
            font_b = ImageFont.truetype("THSarabunNew.ttf", 40)
            font_m = ImageFont.truetype("THSarabunNew.ttf", 30)
            font_s = ImageFont.truetype("THSarabunNew.ttf", 26)
        except Exception:
            font_b = ImageFont.load_default(); font_m = ImageFont.load_default(); font_s = ImageFont.load_default()
        x, y = 60, 40
        draw.text((x, y), f"{APP_TITLE} (ใบเสร็จรับเงิน/ใบกำกับภาษี)", fill="black", font=font_b); y += 48
        draw.text((x, y), f"เลขที่ออเดอร์: #{order_id}", fill="black", font=font_m); y += 34
        draw.text((x, y), f"วันที่: {created_at}", fill="black", font=font_m); y += 34
        draw.text((x, y), f"ลูกค้า: {user_email}", fill="black", font=font_m); y += 34
        draw.text((x, y), f"ที่อยู่จัดส่ง: {ship_addr or '-'}", fill="black", font=font_m); y += 48
        draw.line((x, y, W-60, y), fill="#333", width=2); y += 8
        draw.text((x, y), "สินค้า", font=font_m, fill="black")
        draw.text((W-480, y), "ราคา", font=font_m, fill="black")
        draw.text((W-320, y), "จำนวน", font=font_m, fill="black")
        draw.text((W-160, y), "รวมย่อย", font=font_m, fill="black"); y += 36
        draw.line((x, y, W-60, y), fill="#333", width=1); y += 8
        for name, price, qty, line_total in items:
            line_total = (line_total if line_total is not None else float(price)*int(qty))
            draw.text((x, y), str(name), font=font_s, fill="black")
            draw.text((W-480, y), f"{float(price):,.2f}", font=font_s, fill="black")
            draw.text((W-320, y), str(int(qty)), font=font_s, fill="black")
            draw.text((W-160, y), f"{line_total:,.2f}", font=font_s, fill="black")
            y += 34
        y += 12; draw.line((x, y, W-60, y), fill="#333", width=2); y += 18
        def row(label, value):
            nonlocal y
            draw.text((W-360, y), label, font=font_m, fill="black")
            draw.text((W-160, y), f"{value:,.2f}", font=font_m, fill="black"); y += 34
        row("Subtotal", float(subtotal))
        row("ส่วนลด", -float(discount))
        row("ค่าส่ง", float(shipping_fee))
        row("VAT 7%", float(vat))
        draw.line((W-360, y, W-60, y), fill="#333", width=1); y += 16
        draw.text((W-360, y), "ยอดสุทธิ (Grand Total)", font=font_b, fill="black")
        draw.text((W-160, y), f"{grand_total:,.2f}", font=font_b, fill="black"); y += 48
        draw.text((x, y), f"ขอบคุณที่อุดหนุนร้าน {APP_TITLE}", font=font_m, fill="#333")
        out_path = os.path.join(DIR_INVOICES, f"invoice_{order_id}.png")
        img.save(out_path)
        return out_path

    def _generate_invoice_and_store(self, order_id: int):
        path = self._generate_invoice_png(order_id)
        if not path:
            return
        conn = sqlite3.connect(DB); c = conn.cursor(); c.execute("UPDATE orders SET invoice_path=?, updated_at=? WHERE id=?", (path, datetime.datetime.now().isoformat(timespec="seconds"), order_id)); conn.commit(); conn.close()
        messagebox.showinfo("ใบเสร็จ", f"สร้างใบเสร็จแล้ว\n{path}")

    




# ------------------------------ RUN -------------------------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")       # ธีมเริ่มต้น (light/dark ได้)
    ctk.set_default_color_theme("green")   # โทนสีหลัก
    root = ctk.CTk()
    app = PharmaApp(root)                  # สร้างอินสแตนซ์แอป
    root.mainloop()                        # เริ่มรัน UI

