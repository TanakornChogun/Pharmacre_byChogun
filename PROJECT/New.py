import sqlite3
import customtkinter as ctk
from tkinter import messagebox
from tkinter import filedialog  # ← เพิ่ม
import hashlib
import os
import datetime
import qrcode
from io import BytesIO
from PIL import Image, ImageTk, ImageOps
import re
import shutil
from tkinter import filedialog


# ----------------- Database -----------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "pharmacy.db")




# ----------------- ประเภทสินค้า -----------------
CATEGORY_MAP = {
    "เวชสำอาง": ["ครีมกันแดด", "โฟมล้างหน้า", "เซรั่ม", "มอยส์เจอร์ไรเซอร์"],
    "สินค้าเพื่อสุขภาพ": ["วิตามิน", "อาหารเสริม", "เครื่องวัดความดัน", "สมุนไพร"],
    "ยา": ["ยาแก้ปวด", "ยาลดไข้", "ยาแก้แพ้", "ยาฆ่าเชื้อ"],
}
ALL_CATEGORIES = ["ทั้งหมด"] + list(CATEGORY_MAP.keys())

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # ---------- users ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    for col, coltype in [
        ("phone", "TEXT"),
        ("address", "TEXT"),
        ("profile_image", "TEXT"),
    ]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {coltype}")
        except Exception:
            pass

    # ---------- products ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            description TEXT,
            image_path TEXT
        )
    """)
    def add_prod_col(col, coltype):
        try:
            c.execute(f"ALTER TABLE products ADD COLUMN {col} {coltype}")
        except Exception:
            pass
    add_prod_col("category", "TEXT")
    add_prod_col("subcategory", "TEXT")
    add_prod_col("stock", "INTEGER NOT NULL DEFAULT 0")

    # ---------- orders ----------
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            shipping_method TEXT,
            shipping_address TEXT,
            total_price REAL NOT NULL DEFAULT 0,
            slip_path TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            shipping_status TEXT NOT NULL DEFAULT 'draft',
            tracking_no TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT
        )
    """)
    # เพิ่มสองคอลัมน์สำรอง
    try:
        c.execute("ALTER TABLE orders ADD COLUMN total_amount REAL NOT NULL DEFAULT 0")
    except Exception:
        pass

    try:
        c.execute("ALTER TABLE orders ADD COLUMN total_price REAL NOT NULL DEFAULT 0")
    except Exception:
        pass

    # ---------- order_items ----------
    c.execute("""
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
    """)
    try:
        c.execute("ALTER TABLE order_items ADD COLUMN line_total REAL DEFAULT 0")
    except Exception:
        pass

        # ========== SAFE MIGRATIONS ==========
    # รองรับทั้ง total_amount และ total_price
    try:
        c.execute("ALTER TABLE orders ADD COLUMN total_amount REAL NOT NULL DEFAULT 0")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN total_price REAL NOT NULL DEFAULT 0")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN slip_path TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE orders ADD COLUMN tracking_no TEXT")
    except Exception:
        pass

    # เก็บรวมย่อยต่อแถวสินค้า (ใช้ตอนโชว์บิลสวยๆ)
    try:
        c.execute("ALTER TABLE order_items ADD COLUMN line_total REAL")
    except Exception:
        pass

    conn.commit()
    

    conn.close()

init_db()

# ---------- รายชื่อแอดมิน (ปรับได้) ----------
ADMIN_EMAILS = {"Admin@pharma.local"}      # ใส่ email แอดมินที่อนุญาต
ADMIN_USERNAMES = {"Admin1234"}            # หรือ username แอดมิน
ADMIN_PASSWORD = {"admin1234"}

# ----------------- Main App -----------------
class PharmaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PharmaCare Login")
        self.root.geometry("1920x1080")
        self.main_frame = ctk.CTkFrame(root)
        self.main_frame.pack(fill="both", expand=True)

        self.cart = {}              # ใช้เก็บสินค้าที่ถูกเพิ่มลงตะกร้า
        self._is_on_cart_page = False

        self.current_username = None
        self.current_email = None
        self.is_admin = False   # ← เพิ่มสถานะแอดมิน

        self.login_page()
        

#----------------------------------------------------------------------------------------------------------------------------------------------------------#
    # ----------- หน้า Login -----------
    def login_page(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background whiteBG.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        # ----- ช่องกรอก Email -----
        ctk.CTkLabel(
            self.main_frame,
            text="Email                                                             ",
            font=("Oswald", 12, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.9, rely=0.40, anchor="e")

        self.email_entry = ctk.CTkEntry(
            self.main_frame,
            width=220,
            placeholder_text="กรอก Email",
            bg_color="#fefefe"
        )
        self.email_entry.place(relx=0.9, rely=0.43, anchor="e")

        # ----- ช่องกรอก Username -----
        ctk.CTkLabel(
            self.main_frame,
            text="Username                                                      ",
            font=("Oswald", 12, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.9, rely=0.50, anchor="e")

        self.username_entry = ctk.CTkEntry(
            self.main_frame,
            width=220,
            placeholder_text="กรอก Username",
            bg_color="#fefefe"
        )
        self.username_entry.place(relx=0.9, rely=0.53, anchor="e")

        # ----- ช่องกรอก Password -----
        ctk.CTkLabel(
            self.main_frame,
            text="Password                                                       ",
            font=("Oswald", 12, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.9, rely=0.60, anchor="e")

        self.password_entry = ctk.CTkEntry(
            self.main_frame,
            width=220,
            show="*",
            placeholder_text="กรอก Password",
            bg_color="#fefefe"
        )
        self.password_entry.place(relx=0.9, rely=0.63, anchor="e")

        # ----- ปุ่ม -----
        login_btn = ctk.CTkButton(
            self.main_frame,
            text="เข้าสู่ระบบ",
            fg_color="green",
            text_color="white",
            command=self.login   # เรียกใช้ฟังก์ชัน login
        )
        login_btn.place(relx=0.875, rely=0.80, anchor="e")

        register_btn = ctk.CTkButton(
            self.main_frame,
            text="สมัครบัญชี",
            fg_color="green",
            text_color="white",
            command=self.register_page
        )
        register_btn.place(relx=0.875, rely=0.85, anchor="e")

        forgot_btn = ctk.CTkButton(
            self.main_frame,
            text="ลืมรหัสผ่าน",
            font=("Oswald", 14, "bold"),
            fg_color="transparent",
            bg_color="white",
            text_color="red",
            hover_color="white",
            command=self.forgot_password_page
        )
        forgot_btn.place(relx=0.875, rely=0.68, anchor="e")
#----------------------------------------------------------------------------------------------------------------------------------------------------------#

    # ===================== FORGOT PASSWORD =====================
    def forgot_password_page(self):
        # เคลียร์หน้า
        for w in self.main_frame.winfo_children():
            w.destroy()

        # พื้นหลัง
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background register1.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        # ปุ่มกลับหน้า Login
        ctk.CTkButton(self.main_frame, text="⬅ กลับสู่หน้าหลัก", command=self.login_page)\
            .place(relx=0.5, rely=0.90, anchor="center")

        # กล่องเนื้อหา
        box = ctk.CTkFrame(self.main_frame, corner_radius=20, fg_color="white", bg_color="white")
        box.place(relx=0.5, rely=0.55, anchor="center", relwidth=0.3, relheight=0.6)

        ctk.CTkLabel(box, text="ลืมรหัสผ่าน", font=("Oswald", 24, "bold")).pack(pady=(18, 8))

        # Email
        ctk.CTkLabel(box, text="Email", font=("Oswald", 12, "bold")).pack(pady=(6, 0))
        self.fp_email = ctk.CTkEntry(box, width=320, placeholder_text="กรอก Email ที่ลงทะเบียน")
        self.fp_email.pack(pady=(4, 8))

        # (ตัด Username ออก)

        # Phone (สำคัญ: ใช้ตรวจยืนยันร่วมกับ Email)
        ctk.CTkLabel(box, text="เบอร์โทร", font=("Oswald", 12, "bold")).pack(pady=(6, 0))
        self.fp_phone = ctk.CTkEntry(box, width=320, placeholder_text="เช่น 0812345678")
        self.fp_phone.pack(pady=(4, 8))

        # New Password
        ctk.CTkLabel(box, text="รหัสผ่านใหม่", font=("Oswald", 12, "bold")).pack(pady=(6, 0))
        self.fp_newpass = ctk.CTkEntry(box, width=320, show="*", placeholder_text="อย่างน้อย 8 ตัว (มีตัวเลข+ตัวอักษร)")
        self.fp_newpass.pack(pady=(4, 6))

        # Confirm Password
        ctk.CTkLabel(box, text="ยืนยันรหัสผ่านใหม่", font=("Oswald", 12, "bold")).pack(pady=(6, 0))
        self.fp_confpass = ctk.CTkEntry(box, width=320, show="*", placeholder_text="พิมพ์ซ้ำรหัสผ่านใหม่")
        self.fp_confpass.pack(pady=(4, 10))

        # สวิตช์โชว์/ซ่อนรหัสผ่าน
        self._fp_show_var = ctk.IntVar(value=0)
        ctk.CTkCheckBox(
            box, text="แสดงรหัสผ่าน",
            variable=self._fp_show_var,
            command=self._toggle_fp_password_visibility
        ).pack(pady=(0, 10))

        # ปุ่มยืนยันเปลี่ยนรหัส
        ctk.CTkButton(box, text="รีเซ็ตรหัสผ่าน", fg_color="green", text_color="white",
                      command=self._reset_password_submit).pack(pady=(4, 6))


    def _toggle_fp_password_visibility(self):
        """สลับโชว์/ซ่อนรหัสผ่านในหน้า Forgot Password"""
        show_char = "" if self._fp_show_var.get() == 1 else "*"
        try:
            self.fp_newpass.configure(show=show_char)
            self.fp_confpass.configure(show=show_char)
        except Exception:
            pass


    def _reset_password_submit(self):
        email   = self.fp_email.get().strip() if hasattr(self, "fp_email") else ""
        phone   = self.fp_phone.get().strip() if hasattr(self, "fp_phone") else ""
        newpass = self.fp_newpass.get().strip() if hasattr(self, "fp_newpass") else ""
        conf    = self.fp_confpass.get().strip() if hasattr(self, "fp_confpass") else ""

        # ตรวจค่าว่าง
        if not email or not phone or not newpass or not conf:
            messagebox.showerror("Error", "กรุณากรอกข้อมูลให้ครบทุกช่อง (Email / เบอร์โทร / รหัสผ่านใหม่)")
            return

        # ตรวจรูปแบบเบอร์โทร (ไทย 10 หลักขึ้นต้น 0)
        if not re.fullmatch(r"0\d{9}", phone):
            messagebox.showerror("Error", "เบอร์โทรไม่ถูกต้อง (เช่น 0812345678)")
            return

        # ตรวจรูปแบบรหัสผ่าน (≥8 ตัว มีตัวอักษรและตัวเลข)
        if len(newpass) < 8 or not re.search("[a-zA-Z]", newpass) or not re.search("[0-9]", newpass):
            messagebox.showerror("Error", "รหัสผ่านใหม่ต้องยาวอย่างน้อย 8 ตัว และมีทั้งตัวอักษร + ตัวเลข")
            return

        if newpass != conf:
            messagebox.showerror("Error", "รหัสผ่านใหม่และยืนยันรหัสผ่านไม่ตรงกัน")
            return

        # ตรวจสอบว่ามีผู้ใช้นี้จริงไหม
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=? AND phone=?", (email, phone))
        row = c.fetchone()

        if not row:
            conn.close()
            messagebox.showerror("Error", "ไม่พบผู้ใช้ตาม Email/เบอร์โทร ที่ระบุ")
            return

        # อัปเดตรหัสผ่าน (หมายเหตุ: ตอนนี้เก็บรหัสแบบ plain-text ตามโค้ดเดิม)
        try:
            c.execute("UPDATE users SET password=? WHERE id=?", (newpass, row[0]))
            conn.commit()
            messagebox.showinfo("สำเร็จ", "เปลี่ยนรหัสผ่านเรียบร้อย! โปรดเข้าสู่ระบบด้วยรหัสใหม่")
        except Exception as e:
            messagebox.showerror("Error", f"ไม่สามารถเปลี่ยนรหัสผ่านได้:\n{e}")
        finally:
            conn.close()

        self.login_page()

#----------------------------------------------------------------------------------------------------------------------------------------------------------#
    def login(self):
        email = self.email_entry.get().strip()
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()

        if not email or not username or not password:
            messagebox.showerror("Error", "กรุณากรอกข้อมูลให้ครบ")
            return

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT email, username, password FROM users WHERE email=?", (email,))
        user = c.fetchone()
        conn.close()

        if not user:
            messagebox.showerror("Error", "กรุณาสมัครสมาชิก")
            return
        elif username != user[1]:
            messagebox.showerror("Error", "Username ไม่ถูกต้อง")
            return
        elif password != user[2]:
            messagebox.showerror("Error", "รหัสผ่านไม่ถูกต้อง")
            return

        # ---- ผ่านทั้งหมดจึงมาถึงตรงนี้ ----
        messagebox.showinfo("Success", f"เข้าสู่ระบบสำเร็จ ยินดีต้อนรับ {username}")

        # ตั้งค่าผู้ใช้ + reset session
        self.current_username = username
        self.current_email = email
        self.is_admin = (email in ADMIN_EMAILS) or (username in ADMIN_USERNAMES) or (password in ADMIN_PASSWORD)
        self._reset_session()

        # ส่งไปหน้า Admin หรือ Mainpage
        if self.is_admin:
            self.open_admin()
        else:
            self.main_page(username)



#----------------------------------------------------------------------------------------------------------------------------------------------------------# 
    def register_page(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background register1.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        ctk.CTkLabel(
            self.main_frame, 
            text="สมัครสมาชิก", 
            font=("Oswald", 20, "bold"), 
            bg_color="#fefefe"
        ).place(relx=0.5, rely=0.25, anchor="center")

        # Email
        ctk.CTkLabel(
            self.main_frame, 
            text="Email", 
            font=("Oswald", 12, "bold"), 
            bg_color="#fefefe"
        ).place(relx=0.5, rely=0.3, anchor="center")

        self.reg_email = ctk.CTkEntry(
            self.main_frame, 
            width=250, 
            placeholder_text="กรอก Email"
        )
        self.reg_email.place(relx=0.5, rely=0.35, anchor="center")

        # Username
        ctk.CTkLabel(self.main_frame, text="Username | มีทั้งตัวอักษร-ตัวเลข 8 ตัว ขึ้นไป", font=("Oswald", 12, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.4, anchor="center")
        self.reg_user = ctk.CTkEntry(self.main_frame, width=250, placeholder_text="กรอก Username")
        self.reg_user.place(relx=0.5, rely=0.45, anchor="center")

        # Password
        ctk.CTkLabel(self.main_frame, text="Password | มีทั้งตัวอักษร-ตัวเลข 8 ตัว ขึ้นไป", font=("Oswald", 12, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.5, anchor="center")
        self.reg_pass = ctk.CTkEntry(self.main_frame, width=250, show="*", placeholder_text="กรอก Password")
        self.reg_pass.place(relx=0.5, rely=0.55, anchor="center")

        # Confirm Password
        ctk.CTkLabel(self.main_frame, text="Confirm Password", font=("Oswald", 12, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.6, anchor="center")
        self.reg_pass2 = ctk.CTkEntry(self.main_frame, width=250, show="*", placeholder_text="ยืนยัน Password")
        self.reg_pass2.place(relx=0.5, rely=0.65, anchor="center")

        # Phone
        ctk.CTkLabel(self.main_frame, text="Phone", font=("Oswald", 12, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.7, anchor="center")
        self.reg_phone = ctk.CTkEntry(self.main_frame, width=250, placeholder_text="เช่น 0xxxxxxxxxx")
        self.reg_phone.place(relx=0.5, rely=0.75, anchor="center")

        # ปุ่ม
        LoginButton = ctk.CTkButton(self.main_frame, text="สมัครสมาชิก", fg_color="green", command=self.register)
        LoginButton.place(relx=0.5, rely=0.85, anchor="center")

        RegisterButton = ctk.CTkButton(self.main_frame, text="กลับหน้าแรก", command=self.login_page)
        RegisterButton.place(relx=0.5, rely=0.90, anchor="center")
#----------------------------------------------------------------------------------------------------------------------------------------------------------#
    def register(self):
        email = self.reg_email.get().strip()
        username = self.reg_user.get().strip()
        password = self.reg_pass.get().strip()
        password2 = self.reg_pass2.get().strip()
        phone = self.reg_phone.get().strip()

        # ตรวจสอบช่องว่าง
        if not email or not username or not password or not password2 or not phone:
            messagebox.showerror("Error", "กรุณากรอกข้อมูลให้ครบทุกช่อง")
            return

        # ตรวจสอบ Password + Username ต้อง >=8 ตัว และมีทั้งตัวเลข+อักษร
        if len(username) < 8 or not re.search("[a-zA-Z]", username) or not re.search("[0-9]", username):
            messagebox.showerror("Error", "Username ต้องมีอย่างน้อย 8 ตัว และมีทั้งตัวเลข+อักษร")
            return
        if len(password) < 8 or not re.search("[a-zA-Z]", password) or not re.search("[0-9]", password):
            messagebox.showerror("Error", "Password ต้องมีอย่างน้อย 8 ตัว และมีทั้งตัวเลข+อักษร")
            return

        # ตรวจสอบรหัสผ่านตรงกัน
        if password != password2:
            messagebox.showerror("Error", "Password ไม่ตรงกัน")
            return
        
        if not re.fullmatch(r"0\d{9}", phone):
            messagebox.showerror("Error", "เบอร์โทรไม่ถูกต้อง (เช่น 0812345678)")
            return

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute(
                "INSERT INTO users (email, username, password, phone) VALUES (?, ?, ?, ?)",
                (email, username, password, phone)
            )
            conn.commit()
            messagebox.showinfo("DEBUG", f"DB Path:\n{os.path.abspath(DB)}")

            messagebox.showinfo("Success", f"สมัครสมาชิกสำเร็จ ยินดีต้อนรับ {username}")

            # เซตสถานะผู้ใช้ + รีเซ็ต session
            self.current_username = username
            self.current_email = email
            self.is_admin = (email in ADMIN_EMAILS) or (username in ADMIN_USERNAMES) or(password in ADMIN_PASSWORD)
            self._reset_session()

            self.main_page(username)
        except sqlite3.IntegrityError as e:
            if "email" in str(e):
                messagebox.showerror("Error", "Email ถูกใช้งานแล้ว")
            elif "username" in str(e):
                messagebox.showerror("Error", "Username ถูกใช้งานแล้ว")
        finally:
            conn.close()

    # ---------------- Session helpers ----------------
    def _reset_session(self):
        # ใช้เฉพาะตอน: login สำเร็จ, register สำเร็จ, logout, ชำระเงินเสร็จ
        if not hasattr(self, "cart") or self.cart is None:
            self.cart = {}
        else:
            self.cart.clear()

        self._is_on_cart_page = False

        # ถ้ามี textbox สรุปตะกร้าอยู่แล้วให้เคลียร์ด้วย
        if hasattr(self, "cart_summary") and self.cart_summary:
            try:
                self.cart_summary.configure(state="normal")
                self.cart_summary.delete("1.0", "end")
                self.cart_summary.insert("end", "ตะกร้าว่าง")
                self.cart_summary.configure(state="disabled")
            except Exception:
                pass

    def _ensure_dir(self, path: str):
        try:
            os.makedirs(path, exist_ok=True)
        except Exception:
            pass

    # ★ NEW: สร้างตะกร้าถ้ายังไม่มี (กัน None/ไม่ได้สร้าง)
    def _ensure_cart(self):
        if not hasattr(self, "cart") or self.cart is None:
            self.cart = {}

    def _get_stock(self, pid: int) -> int:
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT stock FROM products WHERE id=?", (pid,))
        row = c.fetchone()
        conn.close()
        return int(row[0]) if row and row[0] is not None else 0

    def _logout(self):
        self._reset_session()
        self.current_username = None
        self.current_email = None
        self.is_admin = False
        self.login_page()

#----------------------------------------------------------------------------------------------------------------------------------------------------------#
    def admin(self):
        pass  # (คงไว้ตามเดิม ไม่ใช้งาน)

#----------------------------------------------------------------------------------------------------------------------------------------------------------#

    def main_page(self, username):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.main_frame, text=f"ยินดีต้อนรับ {username}", font=("Oswald", 20, "bold")).pack(pady=20)

        # ---------- Background ----------
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\New2Background.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        BackLogpage = ctk.CTkButton(
            self.main_frame,
            text ="🔙 Log out",
            fg_color="#ff0000",
            hover_color="#5e0303",
            text_color="white",
            command=self._logout
        )
        BackLogpage.place(relx=0.88, rely=0.95, anchor="e")

        # ✅ แสดงเฉพาะลูกค้าปกติเท่านั้น
        if not getattr(self, "is_admin", False):
            # ปุ่มโปรไฟล์
            ProfileButton = ctk.CTkButton(
                self.main_frame,
                text="👤",
                width=50, height=50,
                fg_color="#0f057a",
                hover_color="#55ccff",
                text_color="white",
                command=self.Profile_Page
            )
            ProfileButton.place(relx=0.99, rely=0.05, anchor="e")

            # ปุ่มตะกร้า
            BusketButton = ctk.CTkButton(
                self.main_frame,
                text="🛒",
                width=50,
                height=50,
                fg_color="green",
                hover_color="darkgreen",
                text_color="white",
                command=self.cart_page
            )
            BusketButton.place(relx=0.99, rely=0.13, anchor="e")

        # ปุ่ม Admin (เฉพาะแอดมิน)
        if getattr(self, "is_admin", False):
            AdminButton = ctk.CTkButton(
                self.main_frame,
                text="🛠 Admin",
                width=80, height=36,
                fg_color="#444", hover_color="#222",
                command=self.open_admin
            )
            AdminButton.place(relx=0.8, rely=0.09, anchor="e")
        is_admin = getattr(self, "is_admin", False)

        # ---------- Welcome Text ----------
        welcome = ctk.CTkLabel(
            self.main_frame,
            text=f"ยินดีต้อนรับ {username}",
            font=("Arial", 20, "bold"),
            text_color="black",
            fg_color="transparent"
        )
        welcome.place(relx=0.25, rely=0.09, anchor="e")

        content_frame = ctk.CTkFrame(
            self.main_frame, 
            fg_color="white", 
            corner_radius=20,
            bg_color="white"
        )
        content_frame.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.77, relheight=0.7)

        # state กรอง
        self.selected_category = "ทั้งหมด"
        self.selected_subcategory = None

        # ซ้าย: หมวดหมู่
        left_panel = ctk.CTkFrame(content_frame, width=180, height=450, corner_radius=10, bg_color="white")
        left_panel.pack(side="left", fill="y", padx=10, pady=10)
        left_panel.pack_propagate(False)
        ctk.CTkLabel(left_panel, text="หมวดหมู่", font=("Arial", 16, "bold")).pack(pady=10)

        # ถัดไป: ประเภท
        self.sub_panel = ctk.CTkFrame(content_frame, width=180, height=450, corner_radius=10, bg_color="white")
        self.sub_panel.pack(side="left", fill="y", padx=10, pady=10)
        self.sub_panel.pack_propagate(False)
        ctk.CTkLabel(self.sub_panel, text="ประเภท", font=("Arial", 16, "bold")).pack(pady=10)

        def show_subcategories(category):
            # ล้างของเก่าใน sub_panel ทั้งหมดยกเว้นหัวข้อ "ประเภท"
            for w in self.sub_panel.winfo_children():
                if isinstance(w, ctk.CTkLabel) and w.cget("text") == "ประเภท":
                    continue
                w.destroy()

            self.selected_category = category
            self.selected_subcategory = None

            subs = CATEGORY_MAP.get(category, [])
            ctk.CTkLabel(self.sub_panel, text=f"{category}", font=("Arial", 14, "bold")).pack(pady=(0, 6))

            if subs:
                ctk.CTkButton(self.sub_panel, text="ทั้งหมด", width=150,
                              command=lambda: (setattr(self, "selected_subcategory", None), self.render_products())
                              ).pack(pady=5)
                for sub in subs:
                    ctk.CTkButton(self.sub_panel, text=sub, width=150,
                                  command=lambda s=sub: (setattr(self, "selected_subcategory", s), self.render_products())
                                  ).pack(pady=5)

            self.render_products()

        # ปุ่มหมวดหมู่หลัก
        for cat in ALL_CATEGORIES:
            ctk.CTkButton(left_panel, text=cat, width=150,
                          command=lambda c=cat: show_subcategories(c)).pack(pady=5)

        # กลาง: สินค้า
        center_panel = ctk.CTkFrame(content_frame, corner_radius=10, bg_color="white")
        center_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.products_container = ctk.CTkScrollableFrame(center_panel, label_text="สินค้า", fg_color="white")
        self.products_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ✅ ขวา: ตะกร้าสรุป เฉพาะผู้ใช้ทั่วไปเท่านั้น
        if not is_admin:
            right_panel = ctk.CTkFrame(content_frame, width=200, height=450, corner_radius=10, bg_color="white")
            right_panel.pack(side="right", fill="y", padx=10, pady=10)
            right_panel.pack_propagate(False)

            ชำระ = ctk.CTkButton(right_panel, text="ชำระสินค้า", width=150, command=self.cart_page)
            ชำระ.place(relx=0.9, rely=0.5, anchor="e")

            ctk.CTkLabel(right_panel, text="ตะกร้าสรุป", font=("Arial", 16, "bold")).pack(pady=10)
            self.cart_summary = ctk.CTkTextbox(right_panel, width=180, height=180)
            self.cart_summary.pack(pady=10)
            self.cart_summary.insert("end", "ตะกร้าว่าง")

            self._update_cart_summary()

        # แสดงสินค้าครั้งแรก (ทั้งหมด)
        show_subcategories("ทั้งหมด")

 #----------------------------------------------------------------------------------------------------------------------------------------------------------#
    def add_to_cart(self, pid, name, price, qty=1):
        self._ensure_cart()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT stock FROM products WHERE id=?", (pid,))
        row = c.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("ตะกร้า", "ไม่พบข้อมูลสินค้า")
            return

        stock = int(row[0])
        current_qty = self.cart.get(pid, {}).get("qty", 0)
        if current_qty + qty > stock:
            messagebox.showwarning("ตะกร้า", f"❌ สินค้าหมดหรือมีไม่เพียงพอ (เหลือ {stock} ชิ้น)")
            return

        if pid in self.cart:
            self.cart[pid]["qty"] += qty
        else:
            self.cart[pid] = {"name": name, "price": price, "qty": qty}

        messagebox.showinfo("ตะกร้า", f"เพิ่ม {name} x{qty} ลงตะกร้าแล้ว")
        self._update_cart_summary()
        if hasattr(self, "_is_on_cart_page") and self._is_on_cart_page:
            self._render_cart_items()

#----------------------------------------------------------------------------------------------------------------------------------------------------------#
    def cart_page(self):
        """หน้าแสดงตะกร้าสินค้า + รวมเงิน"""
        self._is_on_cart_page = True  # flag บอกว่าตอนนี้อยู่หน้าตะกร้า
        self._ensure_cart()

        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # ---------- พื้นหลังเดิม ----------
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\New2Background.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        content_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20)
        content_frame.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.77, relheight=0.7)

        username = getattr(self, "current_username", "Guest")

        BackButton = ctk.CTkButton(
            self.main_frame,
            text="🔙",
            width=50, height=50,
            fg_color="green", hover_color="darkgreen", text_color="white",
            command=lambda: (setattr(self, "_is_on_cart_page", False), self.main_page(username))
        )
        BackButton.place(relx=0.99, rely=0.13, anchor="e")

        ctk.CTkLabel(content_frame, text="ตะกร้าสินค้า", font=("Arial", 20, "bold")).pack(pady=10)

        # กล่องตะกร้าสินค้า
        self.cart_box = ctk.CTkScrollableFrame(content_frame, fg_color="#bdfcc9", corner_radius=25, width=600, height=360)
        self.cart_box.pack(fill="both", expand=True, padx=40, pady=10)

        # แถบสรุปด้านล่าง
        footer = ctk.CTkFrame(content_frame, fg_color="transparent")
        footer.pack(fill="x", padx=40, pady=(4, 8))

        self.total_label = ctk.CTkLabel(footer, text="รวม: 0.00 บาท", font=("Arial", 16, "bold"))
        self.total_label.pack(side="left")

        clear_btn = ctk.CTkButton(footer, text="ล้างตะกร้า", fg_color="#aaaaaa", command=self._clear_cart)
        clear_btn.pack(side="right", padx=(8, 0))

        pay_button = ctk.CTkButton(
            footer,
            text="ชำระสินค้า",
            fg_color="#9bffb2",
            text_color="black",
            width=120,
            command=self.review_order_page  # ← ไม่ต้องส่งพารามิเตอร์
        )
        pay_button.pack(side="right", padx=(8, 0))

        status_bar = ctk.CTkLabel(content_frame, text=f"(DEBUG) items in cart: {sum(i['qty'] for i in self.cart.values())}",
                                  text_color="#666666")
        status_bar.pack(pady=(0, 4))

        self._render_cart_items()

        # ---------- NEW: หน้า Review/บิล ก่อนจ่าย ----------
        # ---------- NEW: หน้า 'สรุปบิล' ก่อนจ่าย ----------
    def review_order_page(self):
        self._ensure_cart()
        if not self.cart:
            messagebox.showinfo("ตะกร้า", "ตะกร้าว่าง")
            return

        # ดึงที่อยู่ผู้ใช้
        email = getattr(self, "current_email", "")
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT address FROM users WHERE email=?", (email,))
        row = c.fetchone()
        conn.close()
        current_address = (row[0].strip() if row and row[0] else "")

        # เคลียร์หน้า
        for w in self.main_frame.winfo_children():
            w.destroy()

        # BG
        img_bg = Image.open(r"c:\\Users\\Lenovo\\OneDrive\\เดสก์ท็อป\\PROJECT\\New2Background.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="").place(relx=0, rely=0, relwidth=1, relheight=1)

        # Back
        ctk.CTkButton(self.main_frame, text="🔙", width=50, height=50,
                      fg_color="green", hover_color="darkgreen", text_color="white",
                      command=self.cart_page).place(relx=0.99, rely=0.13, anchor="e")

        wrap = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=16)
        wrap.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.75, relheight=0.7)

        ctk.CTkLabel(wrap, text="สรุปคำสั่งซื้อ (บิล)", font=("Arial", 20, "bold")).pack(pady=(14, 10))

        # ตารางรายการ
        box = ctk.CTkScrollableFrame(wrap, width=900, height=300, corner_radius=12)
        box.pack(padx=16, pady=8, fill="x")

        header = ctk.CTkFrame(box, fg_color="transparent")
        header.pack(fill="x", pady=(4, 6), padx=8)
        for idx, txt, w in [(0,"สินค้า",260),(1,"ราคา",120),(2,"จำนวน",120),(3,"รวมย่อย",120)]:
            ctk.CTkLabel(header, text=txt, width=w, anchor="w" if idx==0 else "e",
                         font=("Arial", 14, "bold")).grid(row=0, column=idx, sticky="we")

        total = 0.0
        for pid, item in self.cart.items():
            sub = float(item["price"]) * int(item["qty"]); total += sub
            row = ctk.CTkFrame(box, fg_color="white", corner_radius=8)
            row.pack(fill="x", padx=8, pady=4)
            ctk.CTkLabel(row, text=item["name"], anchor="w", width=260).grid(row=0, column=0, sticky="w", padx=(8,4), pady=6)
            ctk.CTkLabel(row, text=f"{float(item['price']):,.2f}", anchor="e", width=120).grid(row=0, column=1, sticky="e")
            ctk.CTkLabel(row, text=str(item["qty"]), anchor="e", width=120).grid(row=0, column=2, sticky="e")
            ctk.CTkLabel(row, text=f"{sub:,.2f}", anchor="e", width=120).grid(row=0, column=3, sticky="e")

        # ยอดรวม + ขนส่ง + ที่อยู่
        bottom = ctk.CTkFrame(wrap, fg_color="transparent"); bottom.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(bottom, text=f"ยอดรวม: {total:,.2f} บาท", font=("Arial", 16, "bold")).pack(anchor="w")

        line2 = ctk.CTkFrame(bottom, fg_color="transparent"); line2.pack(fill="x", pady=(8, 6))
        ctk.CTkLabel(line2, text="วิธีจัดส่ง:", width=100, anchor="w").pack(side="left", padx=(0,8))
        self._ship_method_var = ctk.StringVar(value="Kerry")
        ctk.CTkOptionMenu(line2, values=["Kerry","J&T","ไปรษณีย์ไทย","Flash"],
                          variable=self._ship_method_var, width=160).pack(side="left", padx=(0,20))

        addr_frame = ctk.CTkFrame(bottom, fg_color="transparent"); addr_frame.pack(fill="x")
        ctk.CTkLabel(addr_frame, text="ที่อยู่จัดส่ง:", anchor="w").pack(anchor="w")
        self._addr_box_for_order = ctk.CTkTextbox(addr_frame, width=600, height=90)
        self._addr_box_for_order.pack(anchor="w", pady=(4,0))
        self._addr_box_for_order.insert("1.0", current_address or "กรอกที่อยู่จัดส่งที่นี่...")

        ctk.CTkButton(
            addr_frame,
            text="ยืนยันการสั่งซื้อ",
            fg_color="green",
            text_color="white",
            command=lambda: self._create_order_and_go_payment(total)
        ).place(relx=0.88, rely=0.75, anchor="e")

    def _create_order_and_go_payment(self, total_price: float):
        ship_method = self._ship_method_var.get() if hasattr(self, "_ship_method_var") else "Kerry"
        address = self._addr_box_for_order.get("1.0", "end").strip() if hasattr(self, "_addr_box_for_order") else ""
        if not address or address == "กรอกที่อยู่จัดส่งที่นี่...":
            messagebox.showwarning("ที่อยู่", "กรุณากรอกที่อยู่จัดส่ง")
            return
        if not self.cart:
            messagebox.showerror("ออเดอร์", "ตะกร้าว่าง")
            return

        now = datetime.datetime.now().isoformat(timespec="seconds")
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            # 1) สร้างออเดอร์ก่อน (พยายามใส่ทั้ง total_amount และ total_price ถ้าตารางรองรับ)
            try:
                c.execute("""
                    INSERT INTO orders (
                        user_email, shipping_method, shipping_address,
                        total_amount, total_price,
                        status, shipping_status, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'pending', 'draft', ?, ?)
                """, (self.current_email, ship_method, address,
                    float(total_price), float(total_price), now, now))
            except sqlite3.OperationalError:
                # ตารางเก่าไม่มี total_amount → ใช้เฉพาะ total_price
                c.execute("""
                    INSERT INTO orders (
                        user_email, shipping_method, shipping_address,
                        total_price, status, shipping_status, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, 'pending', 'draft', ?, ?)
                """, (self.current_email, ship_method, address,
                    float(total_price), now, now))

            order_id = c.lastrowid  # ← ได้ id แล้วค่อยไปข้อ 2

            # 2) บันทึกรายการสินค้า (พร้อม line_total เพื่อทำบิลสวย ๆ)
            for pid, it in self.cart.items():
                c.execute("""
                    INSERT INTO order_items (order_id, product_id, name, price, qty, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (order_id, pid, it["name"], float(it["price"]), int(it["qty"]),
                    float(it["price"]) * int(it["qty"])))

            conn.commit()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("ออเดอร์", f"ไม่สามารถสร้างออเดอร์ได้:\n{e}")
            return
        finally:
            conn.close()

        # ไปหน้าชำระเงิน/อัปสลิป
        self.payment_page(order_id)



    # ---------- NEW: หน้า 'ชำระเงิน/อัปสลิป' ----------
        # ========= PAYMENT PAGE =========
    def payment_page(self, order_id: int):
        # เคลียร์หน้า
        for w in self.main_frame.winfo_children():
            w.destroy()

        # พื้นหลัง
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\New2Background.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="").place(relx=0, rely=0, relwidth=1, relheight=1)

        # ปุ่มกลับ
        ctk.CTkButton(self.main_frame, text="🔙", width=50, height=50,
                      fg_color="green", hover_color="darkgreen", text_color="white",
                      command=self.cart_page).place(relx=0.99, rely=0.13, anchor="e")

        # โหลดยอดรวม + slip path ปัจจุบัน
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT total_amount, total_price, slip_path FROM orders WHERE id=?", (order_id,))
        row = c.fetchone()
        conn.close()
        total = (row[0] or row[1] or 0.0) if row else 0.0
        slip_path = row[2] if row else None

        ctk.CTkLabel(self.main_frame, text="ชำระเงิน / อัปโหลดสลีป", font=("Oswald", 28, "bold"),
                     bg_color="#ffffff").place(relx=0.5, rely=0.22, anchor="center")
        ctk.CTkLabel(self.main_frame, text=f"ยอดที่ต้องชำระ: {float(total):,.2f} บาท",
                     font=("Oswald", 18, "bold"), bg_color="#ffffff").place(relx=0.5, rely=0.28, anchor="center")

        # กรอบสลีป
        slip_frame = ctk.CTkFrame(self.main_frame, corner_radius=16, fg_color="white")
        slip_frame.place(relx=0.5, rely=0.58, anchor="center", relwidth=0.55, relheight=0.5)

        ctk.CTkLabel(slip_frame, text="แนบสลีปโอนเงิน", font=("Oswald", 18, "bold")).pack(pady=(12, 8))

        self.slip_preview_label = ctk.CTkLabel(slip_frame, text="(ยังไม่มีสลีป)", width=380, height=280,
                                               fg_color="#f2f2f2", corner_radius=12)
        self.slip_preview_label.pack(pady=8)

        # เก็บอ้างอิงภาพ พรีวิว (กัน GC)
        self._slip_preview_img = None

        # ถ้ามีสลีปอยู่แล้ว แสดงทันที
        if slip_path and os.path.exists(slip_path):
            try:
                im = Image.open(slip_path)
                im.thumbnail((380, 280))
                self._slip_preview_img = ImageTk.PhotoImage(im)
                self.slip_preview_label.configure(image=self._slip_preview_img, text="")
            except Exception:
                pass

        # ปุ่มอัปโหลด
        def _upload():
            path = filedialog.askopenfilename(
                title="เลือกสลีปโอนเงิน",
                filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
            )
            if not path:
                return
            # เซฟสำเนา
            self._ensure_dir("slips")
            ext = os.path.splitext(path)[1].lower()
            safe_name = f"order_{order_id}{ext}"
            dest = os.path.join("slips", safe_name)
            try:
                shutil.copy2(path, dest)
            except Exception as e:
                messagebox.showerror("อัปโหลดสลีป", f"บันทึกไฟล์ไม่ได้:\n{e}")
                return
            # อัปเดต DB
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("UPDATE orders SET slip_path=?, updated_at=? WHERE id=?",
                      (dest, datetime.datetime.now().isoformat(timespec="seconds"), order_id))
            conn.commit(); conn.close()
            # พรีวิว
            try:
                im = Image.open(dest)
                im.thumbnail((380, 280))
                self._slip_preview_img = ImageTk.PhotoImage(im)
                self.slip_preview_label.configure(image=self._slip_preview_img, text="")
            except Exception:
                self.slip_preview_label.configure(text="แสดงรูปไม่ได้")

            messagebox.showinfo("อัปโหลดสลีป", "อัปโหลดสลีปเรียบร้อยแล้ว")

        ctk.CTkButton(slip_frame, text="อัปโหลดสลีป", fg_color="#0288D1", text_color="white",
                      command=_upload).pack(pady=(4, 10))

        # ปุ่มส่งคำสั่งชำระเสร็จ (ให้ลูกค้ากดยืนยันว่าอัปโหลดแล้ว)
        ctk.CTkButton(self.main_frame, text="ส่งสลีปให้แอดมินตรวจ",
                      fg_color="green", text_color="white",
                      command=lambda: self._payment_submit_done(order_id)).place(relx=0.5, rely=0.86, anchor="center")

    def _payment_submit_done(self, order_id: int):
        # ไม่เปลี่ยนสถานะเป็น paid จนกว่าแอดมินอนุมัติ
        messagebox.showinfo("ส่งสลีปแล้ว", "ส่งสลีปเรียบร้อย รอแอดมินตรวจสอบนะครับ/ค่ะ")
        self._reset_session()
        self.main_page(getattr(self, "current_username", "Guest"))


    def _choose_slip(self, order_id: int):
        fpath = filedialog.askopenfilename(
            title="เลือกไฟล์สลิป",
            filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"), ("All files", "*.*")]
        )
        if not fpath:
            return
        # โฟลเดอร์เก็บสลิป
        os.makedirs("slips", exist_ok=True)
        ext = os.path.splitext(fpath)[1].lower()
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        dest = os.path.join("slips", f"order_{order_id}_{ts}{ext}")
        try:
            shutil.copyfile(fpath, dest)
            # เก็บ path ชั่วคราวไว้ก่อนจนกด "ยืนยันส่งสลิป"
            self._pending_slip_path = dest
            self._slip_label.configure(text=f"สลิป: {os.path.basename(dest)}")
        except Exception as e:
            messagebox.showerror("สลิป", f"อัปโหลดล้มเหลว: {e}")

    def _submit_payment(self, order_id: int):
        slip = getattr(self, "_pending_slip_path", None)
        if not slip or not os.path.exists(slip):
            # เผื่อเคยบันทึก slip แล้วใน DB
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("SELECT slip_path FROM orders WHERE id=?", (order_id,))
            row = c.fetchone(); conn.close()
            if not row or not row[0] or not os.path.exists(row[0]):
                messagebox.showwarning("สลิป", "กรุณาอัปโหลดสลิปก่อน")
                return
            slip = row[0]

        now = datetime.datetime.now().isoformat(timespec="seconds")
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            c.execute("UPDATE orders SET slip_path=?, status='submitted', updated_at=? WHERE id=?",
                      (slip, now, order_id))
            conn.commit()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("ออเดอร์", f"บันทึกสลิปล้มเหลว:\n{e}")
            return
        finally:
            conn.close()

        # ล้างตะกร้า (session ใหม่) และกลับหน้าแรก
        self._reset_session()
        messagebox.showinfo("ส่งสลิปแล้ว", "เราได้รับสลิปของคุณแล้ว รอแอดมินตรวจสอบค่ะ/ครับ")
        self.main_page(getattr(self, "current_username","Guest"))

        # ไปหน้


#----------------------------------------------------------------------------------------------------------------------------------------------------------#

    def Qrcode(self):
        # เคลียร์หน้า
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # ---------- พื้นหลัง ----------
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\New2Background.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        # ---------- ปุ่มย้อนกลับ (กลับไป 'ตะกร้าสินค้า') ----------
        BackButton = ctk.CTkButton(
            self.main_frame, text="🔙", width=50, height=50,
            fg_color="green", hover_color="darkgreen", text_color="white",
            command=self.cart_page
        )
        BackButton.place(relx=0.99, rely=0.13, anchor="e")

        # ---------- ข้อความ ----------
        ctk.CTkLabel(
            self.main_frame, text="ขอบคุณที่ไว้วางใจ",
            font=("Oswald", 36, "bold"), bg_color="#fefefe"
        ).place(relx=0.6, rely=0.28, anchor="center")

        # ---------- คำนวณยอดที่ต้องชำระ ----------
        total_price = sum(float(item["price"]) * int(item["qty"]) for item in self.cart.values())
        ctk.CTkLabel(
            self.main_frame, text=f"ยอดที่ต้องชำระ: {total_price:,.2f} บาท",
            font=("Oswald", 20, "bold"), bg_color="#fefefe"
        ).place(relx=0.6, rely=0.36, anchor="center")

        # ---------- แสดงรูป QR ----------
        try:
            img_qr = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\Qrcode.png")
            img_qr = img_qr.resize((400, 250))
            self.qr_photo = ImageTk.PhotoImage(img_qr)

            qr_label = ctk.CTkLabel(self.main_frame, image=self.qr_photo, text="")
            qr_label.place(relx=0.6, rely=0.55, anchor="center")
        except Exception:
            qr_label = ctk.CTkLabel(self.main_frame, text="(ไม่พบไฟล์ QRcode.png)", font=("Arial", 16, "bold"))
            qr_label.place(relx=0.6, rely=0.58, anchor="center")

        # ---------- ปุ่มยืนยัน ----------
        ยืนยัน = ctk.CTkButton(
            self.main_frame,
            text="  ยืนยัน  ",
            font=("Oswald", 18, "bold"),
            fg_color="green",
            text_color="white",
            command=self._confirm_payment_and_back_to_main
        )
        ยืนยัน.place(relx=0.6, rely=0.8, anchor="center")
        ยืนยัน.lift()

        # ปลดบล็อกหลังรอ 2 วินาที
        def _unblock():
            ยืนยัน.configure(state="normal")
            ยืนยัน.lift()

        self.root.after(2000, _unblock)
     
    # ★ NEW: ตรวจสต็อกอีกรอบ + ตัดสต็อก
    def _confirm_payment_and_back_to_main(self):
        # ตรวจสอบความพร้อมของสต็อก
        conn = sqlite3.connect(DB)
        c = conn.cursor()

        for pid, item in self.cart.items():
            qty_needed = int(item["qty"])
            c.execute("SELECT stock, name FROM products WHERE id=?", (pid,))
            row = c.fetchone()
            if not row:
                conn.close()
                messagebox.showerror("ชำระเงิน", f"ไม่พบสินค้า ID {pid}")
                self.cart_page()
                return
            stock_now, name = int(row[0]), row[1]
            if qty_needed > stock_now:
                conn.close()
                messagebox.showerror("ชำระเงิน", f"❌ {name} เหลือ {stock_now} ชิ้น ไม่พอสำหรับ {qty_needed} ชิ้น")
                self.cart_page()
                return

        # ตัดสต็อก
        try:
            for pid, item in self.cart.items():
                c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (int(item["qty"]), pid))
            conn.commit()
        except Exception as e:
            conn.rollback()
            conn.close()
            messagebox.showerror("ชำระเงิน", f"เกิดข้อผิดพลาดในการตัดสต็อก:\n{e}")
            self.cart_page()
            return
        finally:
            conn.close()

        # แจ้งผลและกลับหน้าหลัก
        messagebox.showinfo("ชำระเงิน", "กรุณารอตรวจสอบ ขอบคุณค่ะ/ครับ")
        messagebox.showinfo("ชำระเงิน", "ชำระเงินสำเร็จ ขอบคุณค่ะ/ครับ")

        self.cart.clear()
        self._update_cart_summary()

        username = getattr(self, "current_username", "Guest")
        self._is_on_cart_page = False
        self.main_page(username)

#----------------------------------------------------------------------------------------------------------------------------------------------------------#

    def _update_cart_summary(self):
        # ถ้าไม่มี widget นี้ (เช่นยังไม่อยู่ main_page) ก็ข้าม
        if not hasattr(self, "cart_summary"):
            return

        total_qty = sum(item["qty"] for item in self.cart.values())
        total_price = sum(float(item["price"]) * item["qty"] for item in self.cart.values())

        # แสดงไม่เกิน 6 รายการ เพื่อให้อ่านง่าย
        lines = []
        for pid, item in list(self.cart.items())[:6]:
            lines.append(f"- {item['name']} x{item['qty']}")

        self.cart_summary.configure(state="normal")
        self.cart_summary.delete("1.0", "end")

        if not self.cart:
            self.cart_summary.insert("end", "ตะกร้าว่าง")
        else:
            if lines:
                self.cart_summary.insert("end", "\n".join(lines) + "\n\n")
            self.cart_summary.insert("end", f"รวม {total_qty} ชิ้น\n{total_price:,.2f} บาท")

        self.cart_summary.configure(state="disabled")

#----------------------------------------------------------------------------------------------------------------------------------------------------------#

    def _render_cart_items(self):
        """วาดรายการสินค้าในตะกร้า + อัปเดตรวมเงิน"""
        self._ensure_cart()

        for w in self.cart_box.winfo_children():
            w.destroy()

        if not self.cart:
            ctk.CTkLabel(self.cart_box, text="ยังไม่มีสินค้าในตะกร้า", font=("Arial", 16)).pack(pady=20)
            if hasattr(self, "total_label"):
                self.total_label.configure(text="รวม: 0.00 บาท")
            # ซิงก์สรุปด้านขวา
            self._update_cart_summary()
            return

        header = ctk.CTkFrame(self.cart_box, fg_color="transparent")
        header.pack(fill="x", pady=(4, 6), padx=14)
        ctk.CTkLabel(header, text="สินค้า", width=280, anchor="w", font=("Arial", 14, "bold")).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(header, text="ราคา", width=80, anchor="e", font=("Arial", 14, "bold")).grid(row=0, column=1, sticky="e")
        ctk.CTkLabel(header, text="จำนวน", width=140, anchor="center", font=("Arial", 14, "bold")).grid(row=0, column=2)
        ctk.CTkLabel(header, text="รวมย่อย", width=100, anchor="e", font=("Arial", 14, "bold")).grid(row=0, column=3, sticky="e")
        ctk.CTkLabel(header, text="", width=60).grid(row=0, column=4)

        total = 0.0
        for pid, item in list(self.cart.items()):
            name = item["name"]
            price = float(item["price"])
            qty = int(item["qty"])
            sub = price * qty
            total += sub

            row = ctk.CTkFrame(self.cart_box, fg_color="white", corner_radius=10)
            row.pack(fill="x", padx=12, pady=5)

            ctk.CTkLabel(row, text=name, anchor="w").grid(row=0, column=0, sticky="w", padx=(10, 4), pady=8)
            ctk.CTkLabel(row, text=f"{price:,.2f}", anchor="e", width=80).grid(row=0, column=1, sticky="e", padx=6)

            # ★ NEW: แสดงปุ่ม + ปิดเมื่อถึงสต็อก
            qty_box = ctk.CTkFrame(row, fg_color="transparent")
            qty_box.grid(row=0, column=2, padx=6)

            stock_now = self._get_stock(pid)

            btn_minus = ctk.CTkButton(qty_box, text="-", width=28,
                                      command=lambda p=pid: self._change_qty(p, -1))
            btn_minus.pack(side="left", padx=4)

            ctk.CTkLabel(qty_box, text=str(qty), width=36, anchor="center").pack(side="left", padx=4)

            btn_plus = ctk.CTkButton(qty_box, text="+", width=28,
                                     command=lambda p=pid: self._change_qty(p, +1))
            btn_plus.pack(side="left", padx=4)

            if qty >= stock_now:
                btn_plus.configure(state="disabled")

            ctk.CTkLabel(row, text=f"{sub:,.2f}", anchor="e", width=100).grid(row=0, column=3, sticky="e", padx=6)
            ctk.CTkButton(row, text="ลบ", fg_color="#b00020", command=lambda p=pid: self._remove_item(p)).grid(row=0, column=4, padx=(6, 10))
            row.grid_columnconfigure(0, weight=1)

        if hasattr(self, "total_label"):
            self.total_label.configure(text=f"รวม: {total:,.2f} บาท")

        # ซิงก์สรุปด้านขวา
        self._update_cart_summary()

    # ★ NEW: เช็คสต็อกก่อนเปลี่ยนจำนวน
    def _change_qty(self, pid, delta):
        if pid not in self.cart:
            return
        current = int(self.cart[pid]["qty"])
        new_qty = current + int(delta)

        if new_qty <= 0:
            del self.cart[pid]
        else:
            stock = self._get_stock(pid)
            if new_qty > stock:
                messagebox.showwarning("ตะกร้า", f"❌ สินค้ามีเพียง {stock} ชิ้นในสต็อก")
                return
            self.cart[pid]["qty"] = new_qty

        self._render_cart_items()
        self._update_cart_summary()

    # ★ NEW: ล้างตะกร้า & ลบรายการเดี่ยว
    def _clear_cart(self):
        """ล้างตะกร้าทั้งหมด"""
        self._ensure_cart()
        if not self.cart:
            messagebox.showinfo("ตะกร้า", "ตะกร้าว่างอยู่แล้ว")
            return
        if not messagebox.askyesno("ยืนยัน", "ต้องการล้างตะกร้าหรือไม่?"):
            return
        self.cart.clear()
        if hasattr(self, "_is_on_cart_page") and self._is_on_cart_page:
            self._render_cart_items()
        self._update_cart_summary()

    def _remove_item(self, pid):
        """ลบรายการเดี่ยวออกจากตะกร้า"""
        self._ensure_cart()
        if pid in self.cart:
            del self.cart[pid]
            if hasattr(self, "_is_on_cart_page") and self._is_on_cart_page:
                self._render_cart_items()
            self._update_cart_summary()

#----------------------------------------------------------------------------------------------------------------------------------------------------------#
       # ========================== PROFILE PAGE ==========================
    def Profile_Page(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # ---------- พื้นหลัง ----------
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\New2Background.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        username = self.current_username
        email = self.current_email

        # ---------- โหลดข้อมูลผู้ใช้จากฐานข้อมูล ----------
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT address, profile_image, phone FROM users WHERE email=?", (email,))
        row = c.fetchone()
        conn.close()

        placeholder = "กรอกที่อยู่ของคุณที่นี่..."
        current_address = (row[0] or "").strip() if row else ""
        if not current_address:
            current_address = placeholder
        current_image = row[1] if row and row[1] and os.path.exists(row[1]) else None
        phone = (row[2] or "ยังไม่ได้ระบุ") if row else "ยังไม่ได้ระบุ"
        
        # ---------- ปุ่มย้อนกลับ ----------
        ctk.CTkButton(
            self.main_frame,
            text="🔙", width=50, height=50,
            fg_color="green", hover_color="darkgreen", text_color="white",
            command=lambda: self.main_page(username)
        ).place(relx=0.99, rely=0.13, anchor="e")

        # ---------- โปรไฟล์รูปภาพ (พอดีกรอบ 150x150) ----------
        self.profile_img_label = ctk.CTkLabel(
            self.main_frame,
            text="(ไม่มีรูป)",
            width=150, height=150,
            fg_color="#EEE",
            corner_radius=12
        )
        self.profile_img_label.place(relx=0.3, rely=0.5, anchor="center")

        if current_image:
            try:
                im = Image.open(current_image)
                im = ImageOps.fit(im, (150, 150), Image.LANCZOS)  # ครอป/ย่อให้พอดีกรอบ
                self.profile_img = ImageTk.PhotoImage(im)
                self.profile_img_label.configure(image=self.profile_img, text="")
            except Exception:
                pass

        ctk.CTkButton(
            self.main_frame,
            text="เลือกรูปโปรไฟล์",
            fg_color="#0288D1", text_color="white",
            command=self._choose_profile_image
        ).place(relx=0.3, rely=0.65, anchor="center")

        # ---------- ชื่อ/อีเมล ----------
        ctk.CTkLabel(self.main_frame, text=f"ชื่อผู้ใช้ : {username}", font=("Oswald", 18, "bold"), bg_color="white").place(relx=0.5, rely=0.45, anchor="w")
        ctk.CTkLabel(self.main_frame, text=f"Email : {email}", font=("Oswald", 18, "bold"), bg_color="white").place(relx=0.5, rely=0.5, anchor="w")
        ctk.CTkLabel(self.main_frame, text=f"เบอร์ : {phone}", font=("Oswald", 18, "bold"), bg_color="white").place(relx=0.5, rely=0.75, anchor="w")

        self.phone_entry = ctk.CTkEntry(
            self.main_frame,
            width=150,
            placeholder_text="กรอกเบอร์ใหม่หรือแก้ไขเบอร์",
            bg_color="white"
        )
        self.phone_entry.place(relx=0.53, rely=0.8, anchor="w")

        ctk.CTkButton(
            self.main_frame,
            text="บันทึกเบอร์ใหม่",
            fg_color="green",
            text_color="white",
            bg_color="white",
            command=lambda: self.update_phone(self.phone_entry.get().strip())
        ).place(relx=0.65, rely=0.8, anchor="w")

        # ---------- ที่อยู่ + ปุ่ม แก้ไข/บันทึก ----------
        ctk.CTkLabel(self.main_frame, text="ที่อยู่ :", font=("Oswald", 18, "bold"), bg_color="white").place(relx=0.5, rely=0.55, anchor="w")

        self.address_box = ctk.CTkTextbox(
            self.main_frame, width=380, height=100,
            border_width=2, border_color="gray30",
            fg_color="#F7F7F7", text_color="black"
        )
        self.address_box.place(relx=0.66, rely=0.6, anchor="center")
        self.address_box.insert("1.0", current_address)
        self.address_box.configure(state="disabled")

        # ปุ่มบันทึก (เริ่มปิด)
        self.btn_save_addr = ctk.CTkButton(
            self.main_frame,
            text="บันทึก",
            width=90, height=32,
            fg_color="#007AFF", hover_color="#005BBB", text_color="white",
            command=self._save_address
        )
        self.btn_save_addr.place(relx=0.66, rely=0.7, anchor="center")
        self.btn_save_addr.configure(state="disabled")

        # ปุ่มแก้ไข
        self.btn_edit_addr = ctk.CTkButton(
            self.main_frame,
            text="แก้ไข",
            width=90, height=32,
            fg_color="#4CAF50", hover_color="#2E7D32", text_color="white",
            command=self._enter_edit_address_mode
        )
        self.btn_edit_addr.place(relx=0.72, rely=0.7, anchor="center")

        # เก็บ placeholder ไว้ตรวจตอนเปิดแก้ไข
        self._address_placeholder = placeholder

    def update_phone(self, new_phone):
        # ตรวจสอบรูปแบบเบอร์ (เบอร์ไทย 10 หลัก)
        if not re.fullmatch(r"0\d{9}", new_phone):
            messagebox.showerror("Error", "เบอร์โทรไม่ถูกต้อง (เช่น 0812345678)")
            return

        # อัปเดตลงฐานข้อมูล
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE users SET phone=? WHERE email=?", (new_phone, self.current_email))
        conn.commit()
        conn.close()

        messagebox.showinfo("สำเร็จ", "บันทึกเบอร์โทรใหม่เรียบร้อยแล้ว")
        self.Profile_Page()

    def _enter_edit_address_mode(self):
        self.address_box.configure(state="normal")
        current_text = self.address_box.get("1.0", "end").strip()
        if current_text == self._address_placeholder:
            self.address_box.delete("1.0", "end")
        # โทนสีตอนแก้ไข
        self.address_box.configure(fg_color="#E0F7FA", border_color="#0288D1")
        self.btn_edit_addr.configure(state="disabled")
        self.btn_save_addr.configure(state="normal")

    def _save_address(self):
        address = self.address_box.get("1.0", "end").strip()
        if not address:
            messagebox.showwarning("แจ้งเตือน", "กรุณากรอกที่อยู่ก่อนบันทึก")
            return

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE users SET address=? WHERE email=?", (address, self.current_email))
        conn.commit()
        conn.close()

        # ล็อกกลับโหมดอ่าน
        self.address_box.configure(state="disabled", fg_color="#F7F7F7", border_color="gray30")
        self.btn_edit_addr.configure(state="normal")
        self.btn_save_addr.configure(state="disabled")

        messagebox.showinfo("สำเร็จ", "บันทึกที่อยู่เรียบร้อย")

    def _choose_profile_image(self):
        file_path = filedialog.askopenfilename(
            title="เลือกรูปโปรไฟล์",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        if not file_path:
            return

        try:
            im = Image.open(file_path)
            im = ImageOps.fit(im, (150, 150), Image.LANCZOS)  # พอดีกรอบ 150x150
            self.profile_img = ImageTk.PhotoImage(im)
            self.profile_img_label.configure(image=self.profile_img, text="")
        except Exception as e:
            messagebox.showerror("รูปภาพ", f"ไม่สามารถโหลดรูปภาพได้: {e}")
            return

        # บันทึก path ลง DB
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("UPDATE users SET profile_image=? WHERE email=?", (file_path, self.current_email))
        conn.commit()
        conn.close()

        messagebox.showinfo("สำเร็จ", "อัปเดตรูปโปรไฟล์เรียบร้อย")

#----------------------------------------------------------------------------------------------------------------------------------------------------------#
# ========================== ADMIN PAGE (CRUD PRODUCTS) ==========================
    def open_admin(self):
        # ล้างหน้าปัจจุบัน
        for w in self.main_frame.winfo_children():
            w.destroy()

        # พื้นหลัง
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\New2Background.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        # เก็บ state ของแบบฟอร์ม
        self.selected_product_id = None
        self.product_image_path = None
        self.admin_img_photo = None

        # ปุ่มย้อนกลับ
        back_btn = ctk.CTkButton(
            self.main_frame, text="🔙",
            width=50, height=50, fg_color="green",
            hover_color="darkgreen", text_color="white",
            command=lambda: self.main_page(getattr(self, "current_username", "Guest"))
        )
        back_btn.place(relx=0.99, rely=0.13, anchor="e")
                # ปุ่มไปหน้า 'จัดการออเดอร์'
        ctk.CTkButton(
            self.main_frame, text="🧾 จัดการออเดอร์",
            fg_color="#6A1B9A", hover_color="#4A148C", text_color="white",
            command=self.admin_orders_page
        ).place(relx=0.8, rely=0.15, anchor="e")


        # กรอบใหญ่
        container = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20, bg_color="white")
        container.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.80, relheight=0.70)

        # ซ้าย: รายการสินค้า
        left = ctk.CTkFrame(container, width=280, corner_radius=12)
        left.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(left, text="รายการสินค้า", font=("Oswald", 18, "bold")).pack(pady=(12,6))
        self.list_panel = ctk.CTkScrollableFrame(left, width=260, height=420)
        self.list_panel.pack(fill="both", expand=True, padx=10, pady=10)

        refresh_btn = ctk.CTkButton(left, text="รีเฟรชรายการ", command=self._admin_refresh_products)
        refresh_btn.pack(pady=(0,10))

        # ขวา: ฟอร์มสินค้า
        right = ctk.CTkFrame(container, corner_radius=12)
        right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        ctk.CTkButton(self.main_frame, text="เช็คออเดอร์",
                      fg_color="#555", hover_color="#333",
                      command=self.open_orders_admin)\
            .place(relx=0.74, rely=0.09, anchor="e")
        

        ctk.CTkLabel(right, text="จัดการสินค้า", font=("Oswald", 18, "bold")).grid(row=0, column=0, columnspan=4, pady=(12,8), sticky="w")

        # ฟิลด์กรอก
        ctk.CTkLabel(right, text="ชื่อสินค้า").grid(row=1, column=0, sticky="e", padx=8, pady=6)
        self.p_name = ctk.CTkEntry(right, width=320, placeholder_text="เช่น วิตามินซี 500mg")
        self.p_name.grid(row=1, column=1, columnspan=2, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(right, text="ราคา (บาท)").grid(row=2, column=0, sticky="e", padx=8, pady=6)
        self.p_price = ctk.CTkEntry(right, width=160, placeholder_text="เช่น 199")
        self.p_price.grid(row=2, column=1, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(right, text="สต็อก").grid(row=2, column=2, sticky="e", padx=8, pady=6)
        self.p_stock = ctk.CTkEntry(right, width=120, placeholder_text="เช่น 50")
        self.p_stock.grid(row=2, column=3, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(right, text="รายละเอียด").grid(row=3, column=0, sticky="ne", padx=8, pady=6)
        self.p_desc = ctk.CTkTextbox(right, width=320, height=120)
        self.p_desc.grid(row=3, column=1, columnspan=2, sticky="w", padx=8, pady=6)

        # รูปภาพ + ปุ่มเลือกไฟล์
        self.preview = ctk.CTkLabel(right, text="(ยังไม่มีรูป)", width=160, height=160, fg_color="#f1f1f1", corner_radius=12)
        self.preview.grid(row=1, column=4, rowspan=3, padx=(16,8), pady=6)

        ctk.CTkLabel(right, text="หมวดหมู่").grid(row=4, column=0, sticky="e", padx=8, pady=6)
        self.p_cat = ctk.CTkOptionMenu(right, values=list(CATEGORY_MAP.keys()), width=160, command=self._on_admin_cat_change)
        self.p_cat.grid(row=4, column=1, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(right, text="ประเภทย่อย").grid(row=4, column=2, sticky="e", padx=8, pady=6)
        self.p_subcat = ctk.CTkOptionMenu(right, values=[""], width=160)
        self.p_subcat.grid(row=4, column=3, sticky="w", padx=8, pady=6)

        choose_img = ctk.CTkButton(right, text="เลือกรูปภาพ…", command=self._admin_pick_image)
        choose_img.grid(row=5, column=4, sticky="n", padx=8, pady=(0,12))

        # ปุ่มคำสั่ง
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.grid(row=6, column=0, columnspan=4, sticky="we", padx=8, pady=(10,0))
        ctk.CTkButton(btn_row, text="เพิ่มใหม่", fg_color="#2e7d32", command=self._admin_create).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="บันทึก", fg_color="#1976d2", command=self._admin_save).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="ลบ", fg_color="#b00020", command=self._admin_delete).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="ล้างฟอร์ม", command=self._admin_clear_form).pack(side="left", padx=6)

        # default หมวด/ประเภทย่อย
        first_cat = list(CATEGORY_MAP.keys())[0]
        self.p_cat.set(first_cat)
        self._on_admin_cat_change(first_cat)

        # โหลดรายการ
        self._admin_refresh_products()


        # ---------- NEW: หน้าแอดมินเช็คออเดอร์ ----------
    def open_orders_admin(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

        # BG
        img_bg = Image.open(r"c:\\Users\\Lenovo\\OneDrive\\เดสก์ท็อป\\PROJECT\\New2Background.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="").place(relx=0, rely=0, relwidth=1, relheight=1)

        # Back
        ctk.CTkButton(self.main_frame, text="🔙", width=50, height=50,
                      fg_color="green", hover_color="darkgreen", text_color="white",
                      command=lambda: self.open_admin()).place(relx=0.99, rely=0.13, anchor="e")

        # คอนเทนเนอร์
        wrap = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=16)
        wrap.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.82, relheight=0.72)

        ctk.CTkLabel(wrap, text="เช็คออเดอร์", font=("Oswald", 22, "bold")).pack(pady=(14,8))

        # ฟิลเตอร์สถานะ
        top = ctk.CTkFrame(wrap, fg_color="transparent"); top.pack(fill="x", padx=10, pady=(0,8))
        ctk.CTkLabel(top, text="สถานะ:").pack(side="left", padx=(0,6))
        self._order_status_var = ctk.StringVar(value="submitted")
        ctk.CTkOptionMenu(top, values=["submitted","pending","approved","rejected"],
                          variable=self._order_status_var, width=160).pack(side="left", padx=(0,10))
        ctk.CTkButton(top, text="รีเฟรช", command=self._admin_refresh_orders).pack(side="left")

        # ซ้าย: รายการออเดอร์
        body = ctk.CTkFrame(wrap, fg_color="transparent"); body.pack(fill="both", expand=True, padx=10, pady=10)
        left = ctk.CTkScrollableFrame(body, width=280, height=420, label_text="รายการออเดอร์")
        left.pack(side="left", fill="y")
        self._orders_list_panel = left

        # ขวา: รายละเอียด
        right = ctk.CTkFrame(body, corner_radius=12); right.pack(side="left", fill="both", expand=True, padx=10)
        self._order_detail_panel = right
        ctk.CTkLabel(self._order_detail_panel, text="เลือกรายการทางซ้ายเพื่อดูรายละเอียด").pack(pady=20)

        self._admin_refresh_orders()

    def _admin_refresh_orders(self):
        # เคลียร์ฝั่งซ้าย
        for w in self._orders_list_panel.winfo_children():
            if isinstance(w, ctk.CTkLabel):  # label title of scrollable
                continue
            w.destroy()

        status = self._order_status_var.get() if hasattr(self, "_order_status_var") else "submitted"
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("""
            SELECT id, user_email, total_price, status, shipping_status, created_at
            FROM orders
            WHERE status=?
            ORDER BY id DESC
        """, (status,))
        rows = c.fetchall(); conn.close()

        if not rows:
            ctk.CTkLabel(self._orders_list_panel, text="(ไม่พบออเดอร์)").pack(pady=10)
            return

        for oid, email, total, st, shipst, created in rows:
            ctk.CTkButton(self._orders_list_panel,
                          text=f"#{oid} | {email}\n฿{total:,.2f} | {st} | {shipst}",
                          command=lambda o=oid: self._admin_open_order(o)).pack(fill="x", padx=6, pady=6)

    def _admin_open_order(self, order_id: int):
        # เคลียร์รายละเอียดขวา
        for w in self._order_detail_panel.winfo_children():
            w.destroy()

        # ดึงข้อมูลหัวออเดอร์
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("""
            SELECT user_email, shipping_method, shipping_address, total_price, slip_path, status, shipping_status, tracking_no, created_at
            FROM orders WHERE id=?
        """, (order_id,))
        head = c.fetchone()
        if not head:
            conn.close()
            ctk.CTkLabel(self._order_detail_panel, text="ไม่พบออเดอร์นี้").pack(pady=20)
            return

        email, shipm, addr, total, slip, st, shipst, track, created = head

        ctk.CTkLabel(self._order_detail_panel, text=f"ออเดอร์ #{order_id}", font=("Oswald", 20, "bold")).pack(pady=(10,6))
        ctk.CTkLabel(self._order_detail_panel, text=f"ลูกค้า: {email}").pack(anchor="w", padx=12)
        ctk.CTkLabel(self._order_detail_panel, text=f"วิธีจัดส่ง: {shipm}").pack(anchor="w", padx=12)
        ctk.CTkLabel(self._order_detail_panel, text=f"ยอดรวม: {total:,.2f} บาท").pack(anchor="w", padx=12)
        ctk.CTkLabel(self._order_detail_panel, text=f"ที่อยู่: {addr}").pack(anchor="w", padx=12, pady=(0,8))
        ctk.CTkLabel(self._order_detail_panel, text=f"สถานะ: {st} | จัดส่ง: {shipst}").pack(anchor="w", padx=12)

        # สินค้าในออเดอร์
        items_box = ctk.CTkScrollableFrame(self._order_detail_panel, width=520, height=220, label_text="รายการสินค้า")
        items_box.pack(fill="x", padx=12, pady=8)
        c.execute("SELECT product_id, name, price, qty FROM order_items WHERE order_id=?", (order_id,))
        its = c.fetchall()
        conn.close()
        if not its:
            ctk.CTkLabel(items_box, text="(ไม่มีรายการ)").pack(pady=10)
        else:
            headf = ctk.CTkFrame(items_box, fg_color="transparent"); headf.pack(fill="x", padx=6, pady=(4,2))
            for i, txt, w in [(0,"สินค้า",260),(1,"ราคา",120),(2,"จำนวน",120)]:
                ctk.CTkLabel(headf, text=txt, width=w, anchor="w" if i==0 else "e",
                             font=("Arial", 14, "bold")).grid(row=0, column=i, sticky="we")
            for pid, name, price, qty in its:
                row = ctk.CTkFrame(items_box, fg_color="white", corner_radius=6); row.pack(fill="x", padx=6, pady=3)
                ctk.CTkLabel(row, text=name, width=260, anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=6)
                ctk.CTkLabel(row, text=f"{float(price):,.2f}", width=120, anchor="e").grid(row=0, column=1, sticky="e")
                ctk.CTkLabel(row, text=str(qty), width=120, anchor="e").grid(row=0, column=2, sticky="e")

        # สลิป
        slip_row = ctk.CTkFrame(self._order_detail_panel, fg_color="transparent"); slip_row.pack(fill="x", padx=12, pady=6)
        ctk.CTkLabel(slip_row, text=f"สลิป: {os.path.basename(slip) if slip else '—'}").pack(side="left")
        if slip and os.path.exists(slip):
            try:
                im = Image.open(slip); im.thumbnail((240, 160))
                self._slip_preview = ImageTk.PhotoImage(im)
                ctk.CTkLabel(self._order_detail_panel, image=self._slip_preview, text="").pack(padx=12)
            except Exception:
                pass

        # ปุ่มอนุมัติ/ปฏิเสธ
        btns = ctk.CTkFrame(self._order_detail_panel, fg_color="transparent"); btns.pack(fill="x", padx=12, pady=(8,0))
        ctk.CTkButton(btns, text="อนุมัติ", fg_color="#2e7d32", command=lambda: self._approve_order(order_id)).pack(side="left", padx=4)
        ctk.CTkButton(btns, text="ปฏิเสธ", fg_color="#b00020", command=lambda: self._reject_order(order_id)).pack(side="left", padx=4)

        # อัปเดตสถานะจัดส่ง + Tracking
        ship = ctk.CTkFrame(self._order_detail_panel, fg_color="transparent"); ship.pack(fill="x", padx=12, pady=10)
        ctk.CTkLabel(ship, text="สถานะจัดส่ง:").pack(side="left", padx=(0,6))
        self._ship_status_var = ctk.StringVar(value=shipst or "draft")
        ctk.CTkOptionMenu(ship, values=["draft","processing","shipped","delivered"],
                          variable=self._ship_status_var, width=180).pack(side="left", padx=(0,10))
        ctk.CTkLabel(ship, text="Tracking:").pack(side="left", padx=(10,6))
        self._tracking_entry = ctk.CTkEntry(ship, width=220); 
        if track: self._tracking_entry.insert(0, track)
        self._tracking_entry.pack(side="left", padx=(0,10))
        ctk.CTkButton(ship, text="บันทึกจัดส่ง",
                      command=lambda: self._save_shipping(order_id)).pack(side="left")

    def _approve_order(self, order_id: int):
        """อนุมัติ: ตรวจสต็อก → ตัดสต็อก → เปลี่ยนสถานะ"""
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            # เอารายการไปเทียบสต็อก
            c.execute("SELECT product_id, qty FROM order_items WHERE order_id=?", (order_id,))
            rows = c.fetchall()
            # เช็คก่อน
            for pid, qty in rows:
                c.execute("SELECT name, stock FROM products WHERE id=?", (pid,))
                r = c.fetchone()
                if not r:
                    raise Exception(f"ไม่พบสินค้า ID {pid}")
                name, stock = r[0], int(r[1] or 0)
                if int(qty) > stock:
                    raise Exception(f"สต็อก {name} เหลือ {stock} ไม่พอ {qty}")

            # ตัดสต็อก
            for pid, qty in rows:
                c.execute("UPDATE products SET stock = stock - ? WHERE id=?", (int(qty), pid))

            now = datetime.datetime.now().isoformat(timespec="seconds")
            c.execute("UPDATE orders SET status='approved', shipping_status='processing', updated_at=? WHERE id=?",
                      (now, order_id))
            conn.commit()
            messagebox.showinfo("ออเดอร์", "อนุมัติและตัดสต็อกเรียบร้อย")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("อนุมัติล้มเหลว", str(e))
        finally:
            conn.close()
        self._admin_refresh_orders()

    def _reject_order(self, order_id: int):
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            now = datetime.datetime.now().isoformat(timespec="seconds")
            c.execute("UPDATE orders SET status='rejected', updated_at=? WHERE id=?", (now, order_id))
            conn.commit()
            messagebox.showinfo("ออเดอร์", "ปฏิเสธออเดอร์เรียบร้อย")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("ผิดพลาด", str(e))
        finally:
            conn.close()
        self._admin_refresh_orders()

    def _save_shipping(self, order_id: int):
        shipst = self._ship_status_var.get() if hasattr(self, "_ship_status_var") else "draft"
        track = self._tracking_entry.get().strip() if hasattr(self, "_tracking_entry") else ""
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            now = datetime.datetime.now().isoformat(timespec="seconds")
            c.execute("UPDATE orders SET shipping_status=?, tracking_no=?, updated_at=? WHERE id=?",
                      (shipst, track, now, order_id))
            conn.commit()
            messagebox.showinfo("อัปเดตจัดส่ง", "บันทึกสถานะจัดส่งเรียบร้อย")
        except Exception as e:
            conn.rollback()
            messagebox.showerror("ผิดพลาด", str(e))
        finally:
            conn.close()
        # รีโหลดหน้าเดิมเพื่อสะท้อนค่าล่าสุด
        self._admin_open_order(order_id)


    # ---------- helpers (Admin) ----------
    def _on_admin_cat_change(self, selected):
        subs = CATEGORY_MAP.get(selected, [])
        if not subs:
            subs = [""]
        self.p_subcat.configure(values=subs)
        self.p_subcat.set(subs[0] if subs else "")

    def _admin_pick_image(self):
        path = filedialog.askopenfilename(
            title="เลือกรูปสินค้า",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        if not path:
            return

        try:
            im = Image.open(path)
            im.thumbnail((180, 180))

            # ✅ สร้างอ็อบเจกต์รูปภาพ
            photo = ImageTk.PhotoImage(im)

            # ✅ แสดงรูปใน Label
            self.preview.configure(image=photo, text="")

            # ✅ เก็บอ้างอิงไว้ใน instance variable
            self.preview.image = photo          # ป้องกัน GC เก็บรูป
            self.admin_img_photo = photo        # กันรูปหายเมื่อเปลี่ยนหน้า

            # ✅ เก็บพาธไว้ใช้ตอนบันทึกสินค้า
            self.product_image_path = path

        except Exception as e:
            messagebox.showerror("รูปภาพ", f"แสดงตัวอย่างรูปไม่ได้:\n{e}")

    def _admin_refresh_products(self):
        # เคลียร์ปุ่มเดิม
        for w in self.list_panel.winfo_children():
            w.destroy()
        # ดึงจาก DB
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id, name, price FROM products ORDER BY id DESC")
        rows = c.fetchall()
        conn.close()

        if not rows:
            ctk.CTkLabel(self.list_panel, text="(ยังไม่มีสินค้า)").pack(pady=10)
            return

        for pid, name, price in rows:
            btn = ctk.CTkButton(
                self.list_panel,
                text=f"  {name} - {price:.2f} บาท",
                width=240,
                command=lambda p=pid: self._admin_load_into_form(p)
            )
            btn.pack(fill="x", padx=6, pady=4)

    def _admin_load_into_form(self, product_id: int):
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""
            SELECT id, name, price, description, image_path, category, subcategory, stock
            FROM products WHERE id=?
        """, (product_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("โหลดสินค้า", "ไม่พบข้อมูลสินค้า")
            return

        self.selected_product_id = row[0]
        name     = row[1] or ""
        price    = row[2] or 0
        desc     = row[3] or ""
        img_path = row[4]
        cat      = row[5] or list(CATEGORY_MAP.keys())[0]
        sub      = row[6] or (CATEGORY_MAP.get(cat, [""])[0] if CATEGORY_MAP.get(cat) else "")
        stock    = int(row[7] or 0)

        # ใส่ลงฟอร์ม
        self.p_name.delete(0, "end");  self.p_name.insert(0, name)
        self.p_price.delete(0, "end"); self.p_price.insert(0, f"{price:g}")
        self.p_desc.delete("1.0", "end"); self.p_desc.insert("1.0", desc)
        self.p_stock.delete(0, "end"); self.p_stock.insert(0, str(stock))
        self.product_image_path = img_path

        # พรีวิวรูป
        self.preview.configure(image=None, text="(ยังไม่มีรูป)")
        self.admin_img_photo = None
        if img_path and os.path.exists(img_path):
            try:
                im = Image.open(img_path)
                im.thumbnail((180, 180))
                self.admin_img_photo = ImageTk.PhotoImage(im)
                self.preview.configure(image=self.admin_img_photo, text="")
                self.preview.image = self.admin_img_photo  # กัน GC
            except Exception:
                self.preview.configure(text="(ยังไม่มีรูป)")
                self.preview.image = None

        # เมนูหมวด/ประเภทย่อย
        if cat not in CATEGORY_MAP:
            self.p_cat.configure(values=list(CATEGORY_MAP.keys()) + [cat])
        else:
            self.p_cat.configure(values=list(CATEGORY_MAP.keys()))
        self.p_cat.set(cat)
        subs = CATEGORY_MAP.get(cat, [])
        self.p_subcat.configure(values=subs if subs else [""])
        self.p_subcat.set(sub if sub in subs else (subs[0] if subs else ""))

    def _admin_create(self):
        # เคลียร์ฟอร์มแล้วเริ่มกรอกใหม่
        self.selected_product_id = None
        self.p_name.delete(0, "end")
        self.p_price.delete(0, "end")
        self.p_desc.delete("1.0", "end")
        try:
            self.p_stock.delete(0, "end")
        except Exception:
            pass
        self.product_image_path = None
        self.preview.configure(image=None, text="(ยังไม่มีรูป)")
        self.preview.image = None
        self.admin_img_photo = None
        first_cat = list(CATEGORY_MAP.keys())[0]
        self.p_cat.set(first_cat)
        self._on_admin_cat_change(first_cat)

    def _admin_save(self):
        name      = self.p_name.get().strip()
        price_txt = self.p_price.get().strip() or "0"
        stock_txt = (self.p_stock.get() or "0").strip()
        desc      = self.p_desc.get("1.0", "end").strip()
        cat       = self.p_cat.get().strip()
        sub       = self.p_subcat.get().strip()

        try:
            price = float(price_txt)
            stock = int(stock_txt)
            if stock < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("บันทึก", "ราคา/สต็อกไม่ถูกต้อง")
            return

        # ถ้ายังไม่ได้เลือกรูปใหม่ตอนแก้ไข → ใช้ path เดิม
        if self.selected_product_id is not None and not self.product_image_path:
            conn_old = sqlite3.connect(DB)
            c_old = conn_old.cursor()
            c_old.execute("SELECT image_path FROM products WHERE id=?", (self.selected_product_id,))
            old = c_old.fetchone()
            conn_old.close()
            if old and old[0]:
                self.product_image_path = old[0]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            if self.selected_product_id is None:
                c.execute(
                    "INSERT INTO products (name, price, description, image_path, category, subcategory, stock) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, price, desc, self.product_image_path, cat, sub, stock)
                )
                conn.commit()
                self.selected_product_id = c.lastrowid
                messagebox.showinfo("บันทึก", "เพิ่มสินค้าเรียบร้อย")
            else:
                c.execute(
                    "UPDATE products SET name=?, price=?, description=?, image_path=?, category=?, subcategory=?, stock=? WHERE id=?",
                    (name, price, desc, self.product_image_path, cat, sub, stock, self.selected_product_id)
                )
                conn.commit()
                messagebox.showinfo("บันทึก", "อัปเดตสินค้าเรียบร้อย")
        finally:
            conn.close()

        self._admin_refresh_products()
        self._admin_load_into_form(self.selected_product_id)

    def _admin_delete(self):
        if self.selected_product_id is None:
            messagebox.showwarning("ลบสินค้า", "กรุณาเลือกสินค้าที่จะลบก่อน")
            return
        if not messagebox.askyesno("ยืนยัน", "ต้องการลบสินค้านี้หรือไม่?"):
            return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("DELETE FROM products WHERE id=?", (self.selected_product_id,))
        conn.commit()
        conn.close()
        messagebox.showinfo("ลบสินค้า", "ลบสินค้าเรียบร้อย")
        self._admin_refresh_products()
        _ = self._admin_create()  # เคลียร์ฟอร์ม

    # ----------- แสดงสินค้าในหน้า Main ตามตัวกรอง -----------
    def render_products(self):
        # เคลียร์เดิม
        for w in self.products_container.winfo_children():
            w.destroy()

        # ====== สร้าง query + params ตามตัวกรอง ======
        where = []
        params = []
        if getattr(self, "selected_category", "ทั้งหมด") != "ทั้งหมด":
            where.append("category = ?")
            params.append(self.selected_category)
            if getattr(self, "selected_subcategory", None):
                where.append("subcategory = ?")
                params.append(self.selected_subcategory)

        sql = "SELECT id, name, price, description, image_path, stock FROM products"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC"

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()

        if not rows:
            ctk.CTkLabel(self.products_container, text="(ยังไม่มีสินค้าในหมวดนี้)").pack(pady=12)
            return

        # helper ตัดข้อความ
        def _shorten(text, n=160):
            text = (text or "").strip()
            return text if len(text) <= n else text[:n-1] + "…"

        # ตรึงสถานะแอดมิน (True = แอดมิน → ไม่แสดงปุ่มตะกร้า)
        is_admin = bool(getattr(self, "is_admin", False))

        for pid, name, price, desc, img_path, stock in rows:
            card = ctk.CTkFrame(self.products_container, corner_radius=12)
            card.pack(fill="x", pady=8, padx=8)

            # รูปสินค้า
            img_label = ctk.CTkLabel(card, text="")
            img_label.pack(side="left", padx=10, pady=10)
            try:
                if img_path and os.path.exists(img_path):
                    im = Image.open(img_path); im.thumbnail((80, 80))
                    photo = ImageTk.PhotoImage(im)
                    img_label.configure(image=photo)
                    img_label.image = photo  # กัน GC
                else:
                    img_label.configure(text="(no image)")
            except Exception:
                img_label.configure(text="(no image)")

            # ข้อความรายละเอียด
            texts = ctk.CTkFrame(card, fg_color="transparent")
            texts.pack(side="left", fill="x", expand=True, padx=8, pady=10)
            ctk.CTkLabel(texts, text=f"{name}", font=("Arial", 14, "bold")).pack(anchor="w")
            ctk.CTkLabel(texts, text=f"{price:.2f} บาท").pack(anchor="w")
            ctk.CTkLabel(texts, text=f"สต็อกคงเหลือ: {int(stock)} ชิ้น").pack(anchor="w")
            ctk.CTkLabel(texts, text=_shorten(desc, 160), justify="left", anchor="w", wraplength=420)\
                .pack(anchor="w", pady=(2, 6))

            # ===== ปุ่มเพิ่มตะกร้า (แสดงเฉพาะผู้ใช้ทั่วไป) =====
            if not is_admin:
                btn_add = ctk.CTkButton(
                    card,
                    text="เพิ่มลงตะกร้า" if int(stock) > 0 else "สินค้าหมด",
                    width=120,
                    fg_color="#4CAF50" if int(stock) > 0 else "#9E9E9E",
                    text_color="white",
                    command=(lambda pid=pid, name=name, price=price: self.add_to_cart(pid, name, price, qty=1))
                            if int(stock) > 0 else None
                )
                btn_add.pack(side="right", padx=10)
                if int(stock) <= 0:
                    btn_add.configure(state="disabled")
            else:
                # โหมดแอดมิน: ไม่แสดงปุ่มเพิ่มตะกร้า
                ctk.CTkLabel(card, text="โหมดแอดมิน", text_color="#666666").pack(side="right", padx=10)

        # ========== ADMIN ORDERS ==========
    def admin_orders_page(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

        # พื้นหลัง
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\New2Background.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="").place(relx=0, rely=0, relwidth=1, relheight=1)

        # ปุ่มกลับ
        ctk.CTkButton(self.main_frame, text="🔙", width=50, height=50,
                      fg_color="green", hover_color="darkgreen", text_color="white",
                      command=lambda: self.open_admin()).place(relx=0.99, rely=0.13, anchor="e")

        container = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20)
        container.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.82, relheight=0.72)

        ctk.CTkLabel(container, text="จัดการออเดอร์", font=("Oswald", 22, "bold")).pack(pady=(10, 4))

        body = ctk.CTkFrame(container, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=8)

        # ซ้าย: รายการออเดอร์
        left = ctk.CTkFrame(body, width=280)
        left.pack(side="left", fill="y", padx=(0, 8))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="รายการออเดอร์", font=("Oswald", 16, "bold")).pack(pady=(10, 6))
        self.order_list_panel = ctk.CTkScrollableFrame(left, width=260, height=420)
        self.order_list_panel.pack(fill="both", expand=True, padx=6, pady=6)

        # ขวา: รายละเอียด
        right = ctk.CTkFrame(body)
        right.pack(side="left", fill="both", expand=True)
        right.grid_rowconfigure(2, weight=1)
        right.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(right, text="รายละเอียดออเดอร์", font=("Oswald", 16, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 0))

        # กล่องรายละเอียด
        self.order_detail_box = ctk.CTkFrame(right)
        self.order_detail_box.grid(row=1, column=0, sticky="we", padx=10, pady=8)

        # รายการสินค้า
        self.order_items_box = ctk.CTkScrollableFrame(right, label_text="สินค้าในออเดอร์")
        self.order_items_box.grid(row=2, column=0, sticky="nsew", padx=10, pady=8)

        # โซนสลีป + จัดส่ง
        bottom = ctk.CTkFrame(right)
        bottom.grid(row=3, column=0, sticky="we", padx=10, pady=(6, 10))

        # พรีวิวสลีป
        slip_col = ctk.CTkFrame(bottom)
        slip_col.pack(side="left", padx=8, pady=8)
        ctk.CTkLabel(slip_col, text="สลีปชำระเงิน", font=("Oswald", 14, "bold")).pack(anchor="w")
        self.admin_slip_preview = ctk.CTkLabel(slip_col, text="(ไม่มีสลีป)", width=240, height=160, fg_color="#f3f3f3", corner_radius=12)
        self.admin_slip_preview.pack(pady=(6, 4))
        self._admin_slip_img = None

        # ปุ่มอนุมัติ/ปฏิเสธ
        action_col = ctk.CTkFrame(bottom)
        action_col.pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(action_col, text="การตรวจสอบ", font=("Oswald", 14, "bold")).pack(anchor="w")
        ctk.CTkButton(action_col, text="✔ อนุมัติ (paid)", fg_color="#2E7D32", text_color="white",
                      command=lambda: self._admin_set_paid_rejected("paid")).pack(fill="x", pady=(6, 4))
        ctk.CTkButton(action_col, text="✖ ปฏิเสธ (rejected)", fg_color="#B00020", text_color="white",
                      command=lambda: self._admin_set_paid_rejected("rejected")).pack(fill="x")

        # โซนจัดส่ง
        ship_col = ctk.CTkFrame(bottom)
        ship_col.pack(side="left", padx=12, pady=8)
        ctk.CTkLabel(ship_col, text="การจัดส่ง", font=("Oswald", 14, "bold")).pack(anchor="w")

        self._ship_status_var = ctk.StringVar(value="draft")
        self._ship_status_menu = ctk.CTkOptionMenu(ship_col, values=["draft", "processing", "shipped", "delivered"],
                                                   variable=self._ship_status_var)
        self._ship_status_menu.pack(fill="x", pady=(6, 4))

        ctk.CTkLabel(ship_col, text="เลขพัสดุ").pack(anchor="w")
        self._tracking_entry = ctk.CTkEntry(ship_col, width=220, placeholder_text="ใส่เลขพัสดุ")
        self._tracking_entry.pack(fill="x", pady=(2, 6))

        ctk.CTkButton(ship_col, text="บันทึกสถานะจัดส่ง", fg_color="#1976D2", text_color="white",
                      command=self._admin_save_shipping).pack(fill="x")

        # โหลดรายการออเดอร์
        self._admin_refresh_orders()
        self._admin_selected_order_id = None

    def _admin_refresh_orders(self):
        # ล้างเก่า
        for w in self.order_list_panel.winfo_children():
            w.destroy()
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("""
            SELECT id, user_email, status, shipping_status, total_amount, total_price, created_at
            FROM orders ORDER BY id DESC
        """)
        rows = c.fetchall(); conn.close()

        if not rows:
            ctk.CTkLabel(self.order_list_panel, text="(ยังไม่มีออเดอร์)").pack(pady=8)
            return

        for oid, email, st, sst, ta, tp, created in rows:
            total = ta or tp or 0
            btn = ctk.CTkButton(
                self.order_list_panel,
                text=f"#{oid} • {email}\nสถานะ:{st}/{sst} • {float(total):,.2f}฿",
                width=240,
                command=lambda x=oid: self._admin_load_order(x)
            )
            btn.pack(fill="x", padx=6, pady=4)

    def _admin_load_order(self, order_id: int):
        self._admin_selected_order_id = order_id

        # รายละเอียดออเดอร์
        for w in self.order_detail_box.winfo_children():
            w.destroy()
        for w in self.order_items_box.winfo_children():
            w.destroy()
        self._admin_slip_img = None
        self.admin_slip_preview.configure(image=None, text="(ไม่มีสลีป)")

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("""SELECT user_email, shipping_method, shipping_address, status, shipping_status,
                            tracking_no, total_amount, total_price, slip_path, created_at, updated_at
                     FROM orders WHERE id=?""", (order_id,))
        od = c.fetchone()

        if not od:
            conn.close()
            return

        (email, ship_m, addr, st, sst, tracking, ta, tp, slip_path, created, updated) = od
        total = ta or tp or 0.0

        # แสดงหัวข้อ
        lines = [
            f"Order ID: #{order_id}",
            f"ลูกค้า: {email}",
            f"การจัดส่ง: {ship_m}",
            f"สถานะ: {st} / {sst}",
            f"เลขพัสดุ: {tracking or '-'}",
            f"ยอดรวม: {float(total):,.2f} บาท",
            f"สร้างเมื่อ: {created or '-'}",
            f"อัปเดตเมื่อ: {updated or '-'}",
            "ที่อยู่จัดส่ง:",
            f"{addr or '-'}"
        ]
        for t in lines:
            ctk.CTkLabel(self.order_detail_box, text=t, anchor="w").pack(fill="x", padx=10, pady=2)

        # รายการสินค้า
        c.execute("""SELECT name, price, qty, line_total FROM order_items WHERE order_id=?""", (order_id,))
        items = c.fetchall(); conn.close()
        if not items:
            ctk.CTkLabel(self.order_items_box, text="(ไม่มีรายการสินค้า)").pack(pady=8)
        else:
            header = ctk.CTkFrame(self.order_items_box, fg_color="transparent"); header.pack(fill="x", padx=8, pady=(4, 2))
            ctk.CTkLabel(header, text="สินค้า", width=260, anchor="w").grid(row=0, column=0, sticky="w")
            ctk.CTkLabel(header, text="ราคา", width=80, anchor="e").grid(row=0, column=1, sticky="e")
            ctk.CTkLabel(header, text="จำนวน", width=80, anchor="center").grid(row=0, column=2)
            ctk.CTkLabel(header, text="รวมย่อย", width=100, anchor="e").grid(row=0, column=3, sticky="e")

            for name, price, qty, line_total in items:
                row = ctk.CTkFrame(self.order_items_box, fg_color="white", corner_radius=10); row.pack(fill="x", padx=8, pady=4)
                ctk.CTkLabel(row, text=name, anchor="w").grid(row=0, column=0, sticky="w", padx=10, pady=6)
                ctk.CTkLabel(row, text=f"{float(price):,.2f}", anchor="e").grid(row=0, column=1, sticky="e", padx=6)
                ctk.CTkLabel(row, text=str(int(qty)), anchor="center").grid(row=0, column=2)
                lt = line_total if line_total is not None else float(price) * int(qty)
                ctk.CTkLabel(row, text=f"{float(lt):,.2f}", anchor="e").grid(row=0, column=3, sticky="e", padx=6)

        # พรีวิวสลีป (ถ้ามี)
        if slip_path and os.path.exists(slip_path):
            try:
                im = Image.open(slip_path); im.thumbnail((240, 160))
                self._admin_slip_img = ImageTk.PhotoImage(im)
                self.admin_slip_preview.configure(image=self._admin_slip_img, text="")
            except Exception:
                self.admin_slip_preview.configure(text="แสดงรูปไม่ได้")

        # เซตค่าเริ่มสำหรับจัดส่ง
        self._ship_status_var.set(sst or "draft")
        self._tracking_entry.delete(0, "end")
        if tracking:
            self._tracking_entry.insert(0, tracking)

    def _admin_set_paid_rejected(self, new_status: str):
        oid = getattr(self, "_admin_selected_order_id", None)
        if not oid:
            messagebox.showwarning("ออเดอร์", "กรุณาเลือกออเดอร์ก่อน")
            return
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            c.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?",
                      (new_status, datetime.datetime.now().isoformat(timespec="seconds"), oid))
            conn.commit()
        finally:
            conn.close()
        self._admin_load_order(oid)
        self._admin_refresh_orders()
        messagebox.showinfo("ออเดอร์", "อัปเดตสถานะสำเร็จ")

    def _admin_save_shipping(self):
        oid = getattr(self, "_admin_selected_order_id", None)
        if not oid:
            messagebox.showwarning("จัดส่ง", "กรุณาเลือกออเดอร์ก่อน")
            return
        sst = self._ship_status_var.get()
        tracking = self._tracking_entry.get().strip()
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            c.execute("""UPDATE orders
                         SET shipping_status=?, tracking_no=?, updated_at=?
                         WHERE id=?""", (sst, tracking, datetime.datetime.now().isoformat(timespec="seconds"), oid))
            conn.commit()
        finally:
            conn.close()
        self._admin_load_order(oid)
        self._admin_refresh_orders()
        messagebox.showinfo("จัดส่ง", "บันทึกสถานะจัดส่งเรียบร้อย")




# ----------------- Run -----------------
if __name__ == "__main__":
    init_db()
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = PharmaApp(root)
    root.mainloop()
# ----------------- Run -----------------
