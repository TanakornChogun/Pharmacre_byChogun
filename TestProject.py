import sqlite3
import customtkinter as ctk
from tkinter import messagebox
from tkinter import filedialog  # ← เพิ่ม
import hashlib
import os
import datetime
import qrcode
from io import BytesIO
from PIL import Image, ImageTk, ImageOps ,ImageDraw, ImageFont
import re
import shutil
import webbrowser
import sys, subprocess
from tkcalendar import DateEntry  # ปฏิทิน
import calendar




# ----------------- Database -----------------
# โฟลเดอร์ที่เก็บไฟล์ pharmacy.db จริง ๆ
# (ให้แก้เป็นโฟลเดอร์ PROJECT ที่คุณใช้อยู่)
BASE_DIR = r"C:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT"

# path ของฐานข้อมูล (จะเป็น C:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\pharmacy.db)
DB = os.path.join(BASE_DIR, "pharmacy.db")

# เอาไว้เช็คให้ชัวร์ว่าใช้ไฟล์ไหน (รันดูสักครั้ง)
print("ใช้ฐานข้อมูลที่:", DB)


# ----------------- ประเภทสินค้า -----------------
CATEGORY_MAP = {
    "เวชสำอาง": ["ครีมกันแดด", "โฟมล้างหน้า", "เซรั่ม", "มอยส์เจอร์ไรเซอร์"],
    "สินค้าเพื่อสุขภาพ": ["วิตามิน", "อาหารเสริม", "เครื่องวัดความดัน", "สมุนไพร"],
    "ยา": ["ยาแก้ปวด", "ยาลดไข้", "ยาแก้แพ้", "ยาฆ่าเชื้อ"],
}
ALL_CATEGORIES = ["ทั้งหมด"] + list(CATEGORY_MAP.keys())

try:
    from tkcalendar import Calendar
    _HAS_TKCAL = True
except Exception:
    _HAS_TKCAL = False



APPROVED_STATUSES = (
        "approved", "paid", "completed", "success",
        "packed", "shipped", "delivered"
    )

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # --- users table ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            password TEXT
        )
    """)
    # คอลัมน์เสริมของ users
    for col, coltype in [
        ("phone", "TEXT"),
        ("address", "TEXT"),
        ("profile_image", "TEXT"),
        ("otp_code", "TEXT"),
        ("otp_expires", "TEXT"),
    ]:
        try:
            c.execute(f"ALTER TABLE users ADD COLUMN {col} {coltype}")
        except Exception:
            pass

    # --- products table ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            description TEXT,
            image_path TEXT
        )
    """)
    for col, coltype in [
        ("category", "TEXT"),
        ("subcategory", "TEXT"),
        ("stock", "INTEGER NOT NULL DEFAULT 0"),
    ]:
        try:
            c.execute(f"ALTER TABLE products ADD COLUMN {col} {coltype}")
        except Exception:
            pass

    # --- orders table (ออเดอร์) ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            shipping_method TEXT,
            shipping_address TEXT,
            contact_phone TEXT,
            total_amount REAL NOT NULL DEFAULT 0,
            total_price REAL NOT NULL DEFAULT 0,
            slip_path TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            shipping_status TEXT NOT NULL DEFAULT 'draft',
            tracking_no TEXT,
            created_at TEXT DEFAULT (datetime('now')),
            updated_at TEXT
        )
    """)
    # เผื่อกรณีมี DB เก่า — บังคับให้มีคอลัมน์เสมอ
    for col, coltype in [
        ("contact_phone", "TEXT"),
        ("total_amount", "REAL NOT NULL DEFAULT 0"),
        ("total_price", "REAL NOT NULL DEFAULT 0"),
    ]:
        try:
            c.execute(f"ALTER TABLE orders ADD COLUMN {col} {coltype}")
        except Exception:
            pass

    # --- order_items table (รายการสินค้าในออเดอร์) ---
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
    # กันกรณีฐานเก่าที่ไม่มี line_total
    try:
        c.execute("ALTER TABLE order_items ADD COLUMN line_total REAL DEFAULT 0")
    except Exception:
        pass

    # --- reports table (ข้อความลูกค้า ฯลฯ) ---
    c.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            user_name TEXT,
            contact TEXT,
            subject TEXT,
            message TEXT,
            status TEXT DEFAULT 'new'
        )
    """)

    conn.commit()
    conn.close()


# ✅ เรียกที่นี่เพื่อสร้างตารางก่อนเริ่มโปรแกรม
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
        # ใน __init__ ของ PharmaApp
        self._current_order_id = None

        

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
            .place(relx=0.5, rely=0.96, anchor="center")

        # กล่องเนื้อหา
        box = ctk.CTkFrame(self.main_frame, corner_radius=20, fg_color="white", bg_color="white")
        box.place(relx=0.5, rely=0.595, anchor="center", relwidth=0.3, relheight=0.70)

        ctk.CTkLabel(box, text="ลืมรหัสผ่าน", font=("Oswald", 24, "bold")).pack(pady=(18, 8))

        # Email
        ctk.CTkLabel(box, text="Email", font=("Oswald", 12, "bold")).pack(pady=(6, 0))
        self.fp_email = ctk.CTkEntry(box, width=320, placeholder_text="กรอก Email ที่ลงทะเบียน")
        self.fp_email.pack(pady=(4, 8))

        # Phone
        ctk.CTkLabel(box, text="เบอร์โทร", font=("Oswald", 12, "bold")).pack(pady=(6, 0))
        self.fp_phone = ctk.CTkEntry(box, width=320, placeholder_text="เช่น 0812345678")
        self.fp_phone.pack(pady=(4, 8))

        # --- OTP ---
        ctk.CTkLabel(box, text="รหัส OTP", font=("Oswald", 12, "bold")).pack(pady=(6, 0))
        self.fp_otp = ctk.CTkEntry(box, width=320, placeholder_text="กรอกรหัส 6 หลักหลังจากกด 'ส่ง OTP'")
        self.fp_otp.pack(pady=(4, 8))

        ctk.CTkButton(
            box, text="ส่ง OTP", fg_color="#0288D1", text_color="white",
            command=self._send_fp_otp
        ).pack(pady=(0, 8))

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
                    command=self._reset_password_submit).pack(pady=(4, 7))
        
        


    def _toggle_fp_password_visibility(self):
        show_char = "" if self._fp_show_var.get() == 1 else "*"
        try:
            self.fp_newpass.configure(show=show_char)
            self.fp_confpass.configure(show=show_char)
        except Exception:
            pass


    def _send_fp_otp(self):
        email = self.fp_email.get().strip() if hasattr(self, "fp_email") else ""
        phone = self.fp_phone.get().strip() if hasattr(self, "fp_phone") else ""

        if not email or not phone:
            messagebox.showwarning("OTP", "กรุณากรอก Email และ เบอร์โทร ก่อน")
            return
        if not re.fullmatch(r"0\d{9}", phone):
            messagebox.showerror("OTP", "เบอร์โทรไม่ถูกต้อง (เช่น 0812345678)")
            return

        # ตรวจว่ามีผู้ใช้งานอยู่จริง
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT id FROM users WHERE email=? AND phone=?", (email, phone))
        row = c.fetchone()
        if not row:
            conn.close()
            messagebox.showerror("OTP", "ไม่พบผู้ใช้ตาม Email/เบอร์โทร")
            return

        import random, datetime as dt
        code = f"{random.randint(0, 999999):06d}"
        expires = (dt.datetime.now() + dt.timedelta(minutes=10)).isoformat(timespec="seconds")

        try:
            c.execute("UPDATE users SET otp_code=?, otp_expires=? WHERE id=?", (code, expires, row[0]))
            conn.commit()
        finally:
            conn.close()

        # -------- ส่งจริงผ่าน Email / SMS --------
        subject = "PharmaCare OTP สำหรับรีเซ็ตรหัสผ่าน"
        body = f"""รหัส OTP ของคุณคือ: {code}
                ใช้ภายใน 10 นาที
                อีเมลที่ลงทะเบียน: {email}
                หมายเหตุ: หากไม่ได้ร้องขอ กรุณาเพิกเฉย
                """

        sent_email = False
        sent_sms   = False

        # ส่งอีเมล (เปิด/ปิดได้ตามต้องการ)
        try:
            sent_email = send_email(email, subject, body)
        except Exception:
            sent_email = False

        # ส่ง SMS (ถ้าต้องการเปิดใช้ และตั้งค่า Twilio แล้ว)
        try:
            # แปลงเบอร์ไทย 0xxxxxxxxx -> +66xxxxxxxxx ภายใน send_sms แล้วก็ได้
            sent_sms = send_sms(phone, f"OTP: {code} (หมดอายุ 10 นาที)")
        except Exception:
            sent_sms = False

        if sent_email or sent_sms:
            ok_via = []
            if sent_email: ok_via.append("Email")
            if sent_sms:   ok_via.append("SMS")
            messagebox.showinfo("OTP", f"ส่งรหัส OTP ไปที่ {', '.join(ok_via)} แล้ว")
        else:
            # กรณีส่งไม่สำเร็จ แสดงโค้ดเพื่อทดสอบชั่วคราว
            messagebox.showwarning("OTP (ทดสอบ)", f"ยังไม่ได้ตั้งค่า SMTP/SMS หรือส่งไม่สำเร็จ\nOTP ของคุณคือ: {code}")



    def _reset_password_submit(self):
        email   = self.fp_email.get().strip() if hasattr(self, "fp_email") else ""
        phone   = self.fp_phone.get().strip() if hasattr(self, "fp_phone") else ""
        otp     = self.fp_otp.get().strip()   if hasattr(self, "fp_otp") else ""
        newpass = self.fp_newpass.get().strip() if hasattr(self, "fp_newpass") else ""
        conf    = self.fp_confpass.get().strip() if hasattr(self, "fp_confpass") else ""

        # ตรวจค่าว่าง
        if not email or not phone or not otp or not newpass or not conf:
            messagebox.showerror("Error", "กรุณากรอกให้ครบ: Email / เบอร์โทร / OTP / รหัสใหม่ / ยืนยันรหัส")
            return

        # ตรวจรูปแบบเบอร์โทร
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

        import datetime as dt
        now = dt.datetime.now()

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT id, otp_code, otp_expires FROM users WHERE email=? AND phone=?", (email, phone))
        row = c.fetchone()

        if not row:
            conn.close()
            messagebox.showerror("Error", "ไม่พบผู้ใช้ตาม Email/เบอร์โทร")
            return

        uid, otp_code, otp_expires = row[0], row[1], row[2]
        if not otp_code or not otp_expires:
            conn.close()
            messagebox.showerror("OTP", "กรุณากด 'ส่ง OTP' ก่อน")
            return

        try:
            exp = dt.datetime.fromisoformat(otp_expires)
        except Exception:
            conn.close()
            messagebox.showerror("OTP", "รูปแบบเวลา OTP ไม่ถูกต้อง กรุณาส่งใหม่")
            return

        if otp != otp_code:
            conn.close()
            messagebox.showerror("OTP", "OTP ไม่ถูกต้อง")
            return
        if now > exp:
            conn.close()
            messagebox.showerror("OTP", "OTP หมดอายุ กรุณาส่งใหม่")
            return

        # ผ่าน OTP → อัปเดตรหัสผ่าน + ล้าง OTP
        try:
            c.execute("UPDATE users SET password=?, otp_code=NULL, otp_expires=NULL WHERE id=?", (newpass, uid))
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
        elif username != user[1]:
            messagebox.showerror("Error", "Username ไม่ถูกต้อง")
        elif password != user[2]:
            messagebox.showerror("Error", "รหัสผ่านไม่ถูกต้อง")
        else:
            messagebox.showinfo("Success", f"เข้าสู่ระบบสำเร็จ ยินดีต้อนรับ {username}")

            # ตั้งค่าผู้ใช้ก่อน
            self.current_username = username
            self.current_email = email
            self.is_admin = (email in ADMIN_EMAILS) or (username in ADMIN_USERNAMES)

            # แล้วค่อยรีเซ็ต session (กันตะกร้าค้าง)
            self._reset_session()

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
            messagebox.showinfo("Success", f"สมัครสมาชิกสำเร็จ ยินดีต้อนรับ {username}")

            # เซตสถานะผู้ใช้ + รีเซ็ต session
            self.current_username = username
            self.current_email = email
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
        # ใน __init__ ของ PharmaApp
        self._current_order_id = None


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

    # ====== DROP-IN MAIN PAGE (ใส่ภายใน class PharmaApp หลัง _logout) ======

    def Main_page(self, username=None):
        """alias เผื่อจุดอื่นเรียกชื่อเก่า —> ส่งต่อไป main_page"""
        if username is None:
            username = getattr(self, "current_username", "Guest")
        return self.main_page(username)

    def main_page(self, username):
        # เคลียร์หน้า
        for w in self.main_frame.winfo_children():
            w.destroy()

        # พื้นหลังแบบ CTkImage (ไม่ทับวิดเจ็ต)
        self._set_safe_background(self.main_frame)

        # ปุ่มบนขวา
        if not getattr(self, "is_admin", False):
            ctk.CTkButton(self.main_frame, text="👤", width=50, height=50,
                        fg_color="#0f057a", hover_color="#55ccff", text_color="white",
                        command=self.Profile_Page).place(relx=0.99, rely=0.27, anchor="e")
            ctk.CTkButton(self.main_frame, text="🛒", width=50, height=50,
                        fg_color="#0f057a", hover_color="#55ccff", text_color="white",
                        command=self.cart_page).place(relx=0.95, rely=0.27, anchor="e")
            
            HistoryBtn = ctk.CTkButton(
                self.main_frame, text="📜 ประวัติ", width=50, height=50,
                fg_color="#0f057a", hover_color="#55ccff", text_color="white",
                command=self.History_page
            )
            HistoryBtn.place(relx=0.91, rely=0.27, anchor="e")

            Contact = ctk.CTkButton(
                self.main_frame, text=" ติดต่อ", width=50, height=50,
                fg_color="#0f057a", hover_color="#55ccff", text_color="white",
                command=self.Contact_page
            )
            Contact.place(relx=0.87, rely=0.27, anchor="e")

        if getattr(self, "is_admin", False):
            ctk.CTkButton(self.main_frame, text="🛠 Admin", width=90, height=36,
                        fg_color="#444", hover_color="#222", command=self.open_admin)\
                .place(relx=0.82, rely=0.27, anchor="e")
    # ปุ่มไปหน้าเช็คออเดอร์โดยตรง
            OrdersButton = ctk.CTkButton(
                self.main_frame, text="🧾 เช็คออเดอร์", width=120, height=36,
                fg_color="#00796B", hover_color="#00564F", text_color="white",
                #command=self.open_orders_admin
                ) 
            OrdersButton.place(relx=0.70, rely=0.27, anchor="e")


        ctk.CTkButton(self.main_frame, text="🔙 Log out",
                    fg_color="#ff0000", hover_color="#5e0303", text_color="white",
                    command=self._logout).place(relx=1.0, rely=0.80, anchor="e")

        # ข้อความต้อนรับ
        ctk.CTkLabel(self.main_frame, text=f"ยินดีต้อนรับ {username}",
                    font=("Arial", 20, "bold"), text_color="black", fg_color="white")\
            .place(relx=0.25, rely=0.27, anchor="e")

        # ซ้าย: Accordion
        self.selected_category = getattr(self, "selected_category", "ทั้งหมด")
        self.selected_subcategory = getattr(self, "selected_subcategory", None)

        left = ctk.CTkFrame(self.main_frame, width=270, height=510, fg_color="#d3f2ff", bg_color="#d3f2ff")
        left.place(relx=0.09, rely=0.65, anchor="center")
        ctk.CTkLabel(left, text="หมวดหมู่สินค้า", font=("Arial", 16, "bold")).pack(pady=(10, 6), anchor="w", padx=10)

        self._accordion_area = ctk.CTkScrollableFrame(left, width=250, height=440, fg_color="#d3f2ff")
        self._accordion_area.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self._build_category_accordion()

        # กลาง: สินค้าแบบ Grid
        self._products_grid_container = ctk.CTkScrollableFrame(self.main_frame, width=1050, height=500, fg_color="white")
        self._products_grid_container.place(relx=0.54, rely=0.65, anchor="center")
        self._render_products_grid()

        # ขวา: ตะกร้าสรุป (เฉพาะลูกค้าปกติ)
        if not getattr(self, "is_admin", False):
            right = ctk.CTkFrame(self.main_frame, width=180, height=360, fg_color="#d3f2ff", bg_color="#d3f2ff")
            right.place(relx=0.95, rely=0.55, anchor="center")
            ctk.CTkLabel(right, text="ตะกร้าสรุป", font=("Arial", 16, "bold")).pack(pady=(12, 8))
            self.cart_summary = ctk.CTkTextbox(right, width=160, height=220); self.cart_summary.pack(pady=6)
            self._update_cart_summary()
            ctk.CTkButton(right, text="ชำระสินค้า", width=150, command=self.cart_page).pack(pady=(8, 10))

    def _set_safe_background(self, parent):
        try:
            bg_path = getattr(self, "_BG_PATH_OVERRIDE", None) or r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\NewBG.png"
            self._bg_ctk = ctk.CTkImage(light_image=Image.open(bg_path), size=(1580, 810))
            ctk.CTkLabel(parent, image=self._bg_ctk, text="").place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception:
            pass

    def _build_category_accordion(self):
        for w in self._accordion_area.winfo_children():
            w.destroy()
        self._add_accordion_section("ทั้งหมด", [])
        for cat, subs in CATEGORY_MAP.items():
            self._add_accordion_section(cat, subs)

    def _add_accordion_section(self, title: str, sub_list: list[str]):
        section = ctk.CTkFrame(self._accordion_area, fg_color="#c6ecff", corner_radius=8)
        section.pack(fill="x", padx=6, pady=6)

        header = ctk.CTkFrame(section, fg_color="#9bdcff", corner_radius=8); header.pack(fill="x", padx=6, pady=6)
        arrow_var = ctk.StringVar(value="▼")

        def _toggle():
            if body.winfo_viewable():
                body.forget(); arrow_var.set("►"); btn.configure(text=f"{arrow_var.get()}  {title}")
            else:
                body.pack(fill="x", padx=6, pady=(0, 8)); arrow_var.set("▼"); btn.configure(text=f"{arrow_var.get()}  {title}")

        btn = ctk.CTkButton(header, text=f"{arrow_var.get()}  {title}",
                            fg_color="transparent", hover_color="#7ccff9", text_color="black",
                            anchor="w", command=_toggle)
        btn.pack(fill="x", padx=6, pady=6)

        body = ctk.CTkFrame(section, fg_color="#eaf7ff", corner_radius=8)
        if title == "ทั้งหมด":
            ctk.CTkButton(body, text="ดูสินค้าทั้งหมด", width=180,
                        command=lambda: self._on_select_category("ทั้งหมด", None)).pack(pady=6, padx=10, anchor="w")
        else:
            ctk.CTkButton(body, text="ทั้งหมด", width=180,
                        command=lambda t=title: self._on_select_category(t, None)).pack(pady=(8, 2), padx=10, anchor="w")
            for sub in sub_list:
                ctk.CTkButton(body, text=sub, width=180,
                            command=lambda t=title, s=sub: self._on_select_category(t, s)).pack(pady=2, padx=18, anchor="w")
        body.pack(fill="x", padx=6, pady=(0, 8))

    def _on_select_category(self, cat: str, sub: str | None):
        self.selected_category = cat
        self.selected_subcategory = sub
        self._render_products_grid()

    def _render_products_grid(self):
        for w in self._products_grid_container.winfo_children():
            w.destroy()

        where, params = [], []
        if getattr(self, "selected_category", "ทั้งหมด") != "ทั้งหมด":
            where.append("category = ?"); params.append(self.selected_category)
            if getattr(self, "selected_subcategory", None):
                where.append("subcategory = ?"); params.append(self.selected_subcategory)

        sql = "SELECT id, name, price, description, image_path, stock FROM products"
        if where: sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC"

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute(sql, params); rows = c.fetchall(); conn.close()

        if not rows:
            ctk.CTkLabel(self._products_grid_container, text="(ยังไม่มีสินค้าในหมวดนี้)")\
                .grid(row=0, column=0, padx=12, pady=12, sticky="w")
            return

        cols = 4
        for idx, (pid, name, price, desc, img_path, stock) in enumerate(rows):
            r, col = divmod(idx, cols)
            card = ctk.CTkFrame(self._products_grid_container, corner_radius=12, fg_color="#ffffff")
            card.grid(row=r, column=col, padx=12, pady=12, sticky="n")

            img_lbl = ctk.CTkLabel(card, text=""); img_lbl.pack(padx=10, pady=(10, 6))
            try:
                if img_path and os.path.exists(img_path):
                    im = Image.open(img_path)
                    _im = ctk.CTkImage(light_image=im, size=(140, 140))
                    img_lbl.configure(image=_im); img_lbl.image = _im
                else:
                    img_lbl.configure(text="(no image)")
            except Exception:
                img_lbl.configure(text="(no image)")

            ctk.CTkLabel(card, text=name, font=("Arial", 14, "bold")).pack(pady=(4, 2))
            ctk.CTkLabel(card, text=f"{float(price):,.2f} บาท").pack()
            ctk.CTkLabel(card, text=f"สต็อก: {int(stock)} ชิ้น", text_color="#444").pack(pady=(0, 6))

            row_btn = ctk.CTkFrame(card, fg_color="transparent"); row_btn.pack(pady=(4, 10))
            ctk.CTkButton(row_btn, text="รายละเอียด", width=90,
                        command=lambda p=pid: self._open_product_dialog(p)
                        if hasattr(self, "_open_product_dialog") else self._open_product_dialog_from_grid(p))\
                .pack(side="left", padx=4)

            if not getattr(self, "is_admin", False):
                can_add = int(stock) > 0
                ctk.CTkButton(row_btn,
                            text=("เพิ่มลงตะกร้า" if can_add else "สินค้าหมด"),
                            width=90,
                            fg_color=("#4CAF50" if can_add else "#9E9E9E"),
                            text_color="white",
                            state=("normal" if can_add else "disabled"),
                            command=(lambda p=pid, n=name, pr=float(price): self.add_to_cart(p, n, pr, qty=1))
                                    if can_add else None)\
                    .pack(side="left", padx=4)

    def _open_product_dialog_from_grid(self, pid):
        win = ctk.CTkToplevel(self.root); win.title("รายละเอียดสินค้า"); win.geometry("520x420"); win.grab_set()
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("SELECT id, name, price, description, image_path, stock FROM products WHERE id=?", (pid,))
        row = c.fetchone(); conn.close()
        if not row:
            ctk.CTkLabel(win, text="ไม่พบสินค้า").pack(pady=20); return

        pid, name, price, desc, img_path, stock = row
        top = ctk.CTkFrame(win, fg_color="white"); top.pack(fill="both", expand=True, padx=12, pady=12)
        rowf = ctk.CTkFrame(top, fg_color="white"); rowf.pack(fill="x", pady=(6, 8))

        img_lbl = ctk.CTkLabel(rowf, text=""); img_lbl.pack(side="left", padx=10)
        try:
            if img_path and os.path.exists(img_path):
                im = Image.open(img_path)
                _im = ctk.CTkImage(light_image=im, size=(150, 150))
                img_lbl.configure(image=_im); img_lbl.image = _im
            else:
                img_lbl.configure(text="(no image)")
        except Exception:
            img_lbl.configure(text="(no image)")

        info = ctk.CTkFrame(rowf, fg_color="white"); info.pack(side="left", fill="both", expand=True, padx=10)
        ctk.CTkLabel(info, text=name, font=("Arial", 16, "bold")).pack(anchor="w", pady=(2, 4))
        ctk.CTkLabel(info, text=f"ราคา: {float(price):,.2f} บาท").pack(anchor="w")
        ctk.CTkLabel(info, text=f"สต็อก: {int(stock)} ชิ้น").pack(anchor="w")

        txt = ctk.CTkTextbox(top, height=140, width=460); txt.pack(padx=6, pady=6)
        txt.insert("end", (desc or "(ไม่มีรายละเอียด)")); txt.configure(state="disabled")

        btn_row = ctk.CTkFrame(top, fg_color="white"); btn_row.pack(pady=(6, 4))
        ctk.CTkButton(btn_row, text="ปิด", fg_color="#999999", command=win.destroy).pack(side="right", padx=6)

        if not getattr(self, "is_admin", False) and int(stock) > 0:
            ctk.CTkButton(btn_row, text="เพิ่มลงตะกร้า", fg_color="#4CAF50", text_color="white",
                        command=lambda: (self.add_to_cart(pid, name, float(price), 1), win.destroy()))\
                .pack(side="right", padx=6)
    # ====== END DROP-IN ======


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
    #"""หน้าแสดงตะกร้าสินค้าแบบ 2 คอลัมน์ (ซ้าย=รายการ, ขวา=สรุป)"""
        self._is_on_cart_page = True
        self._ensure_cart()

        # ล้างหน้า
        for w in self.main_frame.winfo_children():
            w.destroy()

        # ---------- พื้นหลัง (CTkImage ปลอดภัย HighDPI) ----------
        try:
            bg_path = r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\NewBG.png"
            self._bg_ctk = ctk.CTkImage(light_image=Image.open(bg_path), size=(1580, 810))
            ctk.CTkLabel(self.main_frame, image=self._bg_ctk, text="")\
                .place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception:
            pass

        # ---------- ปุ่มย้อนกลับลอย ----------
        username = getattr(self, "current_username", "Guest")
        ctk.CTkButton(
            self.main_frame, text="🔙", width=50, height=50,
            fg_color="#d60000", hover_color="#f30505", text_color="white",
            command=lambda: (setattr(self, "_is_on_cart_page", False), self.main_page(username))
        ).place(relx=0.99, rely=0.27, anchor="e")

        # ---------- โครงหลัก: กรอบใหญ่ ----------
        shell = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20,bg_color="white")
        shell.place(relx=0.5, rely=0.65, anchor="center", relwidth=0.82, relheight=0.72)

        # หัวเรื่อง
        ctk.CTkLabel(shell, text="ตะกร้าสินค้า", font=("Arial", 22, "bold")).pack(pady=(14, 8))

        # พื้นที่เนื้อหา 2 คอลัมน์
        body = ctk.CTkFrame(shell, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=18, pady=(6, 14))

        # ---------- ซ้าย: รายการสินค้า ----------
        left = ctk.CTkFrame(body, corner_radius=16, fg_color="#F4FFF7")
        left.pack(side="left", fill="both", expand=True)

        header = ctk.CTkFrame(left, fg_color="transparent")
        header.pack(fill="x", padx=16, pady=(12, 6))
        for i, (txt, w, anchor) in enumerate([
            ("สินค้า", 530, "w"),
            ("ราคา", 70, "w"),
            ("จำนวน", 160, "w"),
            ("รวมย่อย", 10, "w"),
            ("", 70, "e")
        ]):
            ctk.CTkLabel(header, text=txt, width=w, anchor=anchor, font=("Arial", 14, "bold"))\
            .grid(row=0, column=i, sticky="we")

        # กล่องรายการเลื่อน
        self.cart_box = ctk.CTkScrollableFrame(left, fg_color="#ECFFF1", corner_radius=14)
        self.cart_box.pack(fill="both", expand=True, padx=12, pady=(2, 14))

        # ---------- ขวา: การ์ดสรุป ----------
        right = ctk.CTkFrame(body, corner_radius=16, fg_color="#EAF7FF", width=280)
        right.pack(side="left", fill="y", padx=(12, 0))
        right.pack_propagate(False)

        ctk.CTkLabel(right, text="สรุปคำสั่งซื้อ", font=("Arial", 18, "bold")).pack(pady=(16, 8))

        # กล่องตัวเลขสรุป
        sum_box = ctk.CTkFrame(right, fg_color="white", corner_radius=12)
        sum_box.pack(fill="x", padx=12, pady=(0, 10))

        # แสดงรวม (จะอัปเดตใน _render_cart_items)
        self._summary_subtotal_lbl = ctk.CTkLabel(sum_box, text="ค่าสินค้า: 0.00 บาท", anchor="w")
        self._summary_subtotal_lbl.pack(fill="x", padx=12, pady=(10, 0))

        self._summary_shipping_lbl = ctk.CTkLabel(sum_box, text="ค่าส่ง: 0.00 บาท", anchor="w")
        self._summary_shipping_lbl.pack(fill="x", padx=12, pady=(4, 0))

        self._summary_tax_lbl = ctk.CTkLabel(sum_box, text="ภาษี (0%): 0.00 บาท", anchor="w")
        self._summary_tax_lbl.pack(fill="x", padx=12, pady=(4, 8))

        # เส้นแบ่ง
        ctk.CTkLabel(sum_box, text="────────────────────────", text_color="#BBBBBB")\
            .pack(padx=12, pady=(0, 4))

        self.total_label = ctk.CTkLabel(sum_box, text="รวมทั้งสิ้น: 0.00 บาท", font=("Arial", 16, "bold"), anchor="w")
        self.total_label.pack(fill="x", padx=12, pady=(0, 10))

        # ปุ่มแอคชัน
        btns = ctk.CTkFrame(right, fg_color="transparent")
        btns.pack(fill="x", padx=12)

        ctk.CTkButton(btns, text="ล้างตะกร้า", fg_color="#9E9E9E",
                    hover_color="#8A8A8A", command=self._clear_cart)\
            .pack(fill="x", pady=(0, 8))

        ctk.CTkButton(btns, text="ชำระสินค้า", fg_color="#00C853", text_color="white",
                    height=42, command=self.Confirm_items)\
            .pack(fill="x")

        # Render รายการ
        self._render_cart_items()

#----------------------------------------------------------------------------------------------------------------------------------------------------------#

    def Confirm_items(self):
    # ล้างหน้าและขึ้นพื้นหลัง
        for w in self.main_frame.winfo_children():
            w.destroy()
        try:
            bg_path = r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\NewBG.png"
            self._bg_ctk = ctk.CTkImage(light_image=Image.open(bg_path), size=(1580, 810))
            ctk.CTkLabel(self.main_frame, image=self._bg_ctk, text="")\
                .place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception:
            pass

        # ปุ่มกลับไปตะกร้า
        ctk.CTkButton(
            self.main_frame, text="🔙", width=50, height=50,
            fg_color="#d60000", hover_color="#f30505", text_color="white",
            command=self.cart_page
        ).place(relx=0.99, rely=0.27, anchor="e")

        # การ์ดหลัก
        shell = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20,bg_color="white")
        shell.place(relx=0.5, rely=0.62, anchor="center", relwidth=0.82, relheight=0.72)

        ctk.CTkLabel(shell, text="ตรวจสอบและยืนยันคำสั่งซื้อ", font=("Arial", 22, "bold")).pack(pady=(14, 6))

        body = ctk.CTkFrame(shell, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=8)

        # ================= ซ้าย: บิล/สรุปรายการ =================
        left = ctk.CTkFrame(body, corner_radius=14, fg_color="#ECFFF1")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=4)

        head = ctk.CTkFrame(left, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(10, 4))
        for i, (txt, anchor, w) in enumerate([("สินค้า", "w", 440), ("ราคา", "w", 110), ("จำนวน", "w", 105), ("รวมย่อย", "w", 20)]):
            ctk.CTkLabel(head, text=txt, anchor=anchor, width=w, font=("Arial", 14, "bold"))\
                .grid(row=0, column=i, sticky="we")

        items_box = ctk.CTkScrollableFrame(left, height=300, fg_color="white", corner_radius=10)
        items_box.pack(fill="both", expand=True, padx=12, pady=(0, 10))

        subtotal, total_qty = self._calc_cart_total()
        if not self.cart:
            ctk.CTkLabel(items_box, text="(ยังไม่มีสินค้าในตะกร้า)", font=("Arial", 14)).pack(pady=20)
        else:
            for pid, it in self.cart.items():
                name = it["name"]; price = float(it["price"]); qty = int(it["qty"])
                line = ctk.CTkFrame(items_box, fg_color="white")
                line.pack(fill="x", padx=10, pady=6)
                ctk.CTkLabel(line, text=name, anchor="w", width=340).grid(row=0, column=0, sticky="w")
                ctk.CTkLabel(line, text=f"{price:,.2f}", anchor="e", width=110).grid(row=0, column=1, sticky="e")
                ctk.CTkLabel(line, text=str(qty), anchor="e", width=110).grid(row=0, column=2, sticky="e")
                ctk.CTkLabel(line, text=f"{price*qty:,.2f}", anchor="e", width=120).grid(row=0, column=3, sticky="e")

        # ====== ค่าขนส่ง/ภาษี/รวมสุทธิ ======
        bottom_left = ctk.CTkFrame(left, fg_color="transparent")
        bottom_left.pack(fill="x", padx=12, pady=(0, 12))

        ctk.CTkLabel(bottom_left, text=f"รวมสินค้า ({total_qty} ชิ้น): {subtotal:,.2f} บาท", font=("Arial", 14, "bold"))\
            .grid(row=0, column=0, columnspan=4, sticky="w", pady=(2, 2))

        ctk.CTkLabel(bottom_left, text="วิธีจัดส่ง:", width=90, anchor="w").grid(row=1, column=0, sticky="w")
        self._ship_method_var = ctk.StringVar(value="Kerry")
        ship_menu = ctk.CTkOptionMenu(bottom_left, values=["Kerry", "J&T", "ไปรษณีย์ไทย", "Flash"],
                                    variable=self._ship_method_var, width=160)
        ship_menu.grid(row=1, column=1, sticky="w", padx=(6, 0))

        # แสดงค่าขนส่ง / VAT 4% / รวมสุดท้าย (ส่งฟรีถ้า >=2 ชิ้น หรือ >=2 รายการ)
        self._ship_fee_var = ctk.StringVar()
        self._vat_var = ctk.StringVar()
        self._confirm_total_var = ctk.StringVar()

        def _recompute_total(*_):
            fees = {"Kerry": 40.0, "J&T": 40.0, "ไปรษณีย์ไทย": 40.0, "Flash": 40.0}
            # เงื่อนไขส่งฟรี: ชิ้นรวม >= 2 หรือ ชนิดสินค้า >= 2
            free = (total_qty >= 2) or (len(self.cart) >= 2)
            ship_fee = 0.0 if free else fees.get(self._ship_method_var.get(), 40.0)
            vat = round(subtotal * 0.07, 2)  # 4%
            grand = subtotal + ship_fee + vat
            self._ship_fee_var.set("ฟรี" if free else f"{ship_fee:,.2f}")
            self._vat_var.set(f"{vat:,.2f}")
            self._confirm_total_var.set(f"{grand:,.2f}")

        _recompute_total()
        
        ship_menu.configure(command=lambda _v: _recompute_total())

        ctk.CTkLabel(bottom_left, text="ค่าจัดส่ง:", anchor="w")\
            .grid(row=2, column=0, sticky="w", pady=(6, 0))
        ctk.CTkLabel(bottom_left, textvariable=self._ship_fee_var, anchor="w", width=120)\
            .grid(row=2, column=1, sticky="w", padx=(6, 0), pady=(6, 0))

        ctk.CTkLabel(bottom_left, text="VAT 7%:", anchor="e")\
            .grid(row=1, column=2, sticky="e", padx=(0, 4))
        ctk.CTkLabel(bottom_left, textvariable=self._vat_var, anchor="e", width=100)\
            .grid(row=1, column=3, sticky="e")

        ctk.CTkLabel(bottom_left, text="รวมทั้งสิ้น:", font=("Arial", 16, "bold"), anchor="e")\
            .grid(row=2, column=2, sticky="e", padx=(0, 6), pady=(6, 0))
        ctk.CTkLabel(bottom_left, textvariable=self._confirm_total_var, font=("Arial", 16, "bold"),
                    anchor="e", width=120)\
            .grid(row=2, column=3, sticky="e", pady=(6, 0))

        for i in range(4):
            bottom_left.grid_columnconfigure(i, weight=1)

        # ================= ขวา: ข้อมูลลูกค้า/ที่อยู่/โทร =================
        right = ctk.CTkFrame(body, corner_radius=14, fg_color="#F6F9FF")
        right.pack(side="left", fill="y", padx=(8, 0), pady=4)

        username = getattr(self, "current_username", "Guest")
        email = getattr(self, "current_email", "")
        ctk.CTkLabel(right, text="ข้อมูลผู้สั่งซื้อ", font=("Arial", 16, "bold")).pack(pady=(12, 6))
        ctk.CTkLabel(right, text=f"ชื่อผู้ใช้: {username}").pack(anchor="w", padx=12)
        ctk.CTkLabel(right, text=f"อีเมล: {email}").pack(anchor="w", padx=12, pady=(0, 8))

        # ดึงที่อยู่/เบอร์เดิม
        current_address, current_phone = "", ""
        try:
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("SELECT address, phone FROM users WHERE email=?", (email,))
            r = c.fetchone(); conn.close()
            if r:
                current_address = (r[0] or "").strip()
                current_phone = (r[1] or "").strip()
        except Exception:
            pass

        # เบอร์โทร
        ctk.CTkLabel(right, text="เบอร์โทร", font=("Arial", 14, "bold")).pack(anchor="w", padx=12)
        self._phone_entry = ctk.CTkEntry(right, width=360, placeholder_text="เช่น 0812345678")
        self._phone_entry.pack(padx=12, pady=(4, 10))
        if current_phone:
            self._phone_entry.insert(0, current_phone)

        # ที่อยู่
        ctk.CTkLabel(right, text="ที่อยู่จัดส่ง", font=("Arial", 14, "bold")).pack(anchor="w", padx=12)
        self._addr_box_for_order = ctk.CTkTextbox(right, width=360, height=120)
        self._addr_box_for_order.pack(padx=12, pady=(4, 10))
        self._addr_box_for_order.insert("1.0", current_address or "กรอกที่อยู่จัดส่งที่นี่...")

        # ปุ่มยืนยัน + ดาวน์โหลดบิล
        btns = ctk.CTkFrame(right, fg_color="transparent"); btns.pack(pady=(6, 8))
        ctk.CTkButton(
            btns, text="ยืนยันการสั่งซื้อ", fg_color="green", text_color="white", width=180,
            command=lambda: self._create_order_and_go_payment(subtotal)
        ).pack(pady=(0, 6))

        

        ctk.CTkButton(
            btns, text="ดาวน์โหลดบิล (PNG)", width=180,
            command=lambda: self._export_invoice_image()
        ).pack(pady=4)

        ctk.CTkButton(
            btns, text="ดาวน์โหลดบิล (PDF)", width=180,
            command=lambda: self._export_invoice_pdf()
        ).pack(pady=4)



    def _calc_cart_total(self):
    #"""คำนวณยอดรวมสินค้า (ไม่รวมค่าส่ง/ภาษี) -> (subtotal, total_qty)"""
        self._ensure_cart()
        subtotal = 0.0
        total_qty = 0
        for pid, it in self.cart.items():
            qty = int(it["qty"]); price = float(it["price"])
            subtotal += price * qty
            total_qty += qty
        return subtotal, total_qty



    def _create_order_and_go_payment(self, subtotal: float):
    # อ่าน input (อ่านให้ครบ *ก่อน* เปลี่ยนหน้า เพื่อลด invalid command name)
        address = self._addr_box_for_order.get("1.0", "end").strip() if hasattr(self, "_addr_box_for_order") else ""
        phone   = self._phone_entry.get().strip() if hasattr(self, "_phone_entry") else ""
        ship_method = self._ship_method_var.get() if hasattr(self, "_ship_method_var") else "Kerry"

        if not re.fullmatch(r"0\d{9}", phone):
            messagebox.showwarning("ข้อมูล", "กรุณากรอกเบอร์โทรให้ถูกต้อง (เช่น 0812345678)")
            return
        if not address or address.strip() in ("กรอกที่อยู่จัดส่งที่นี่", "กรอกที่อยู่จัดส่งที่นี่..."):
            messagebox.showwarning("ที่อยู่", "กรุณากรอกที่อยู่จัดส่ง")
            return
        if not self.cart:
            messagebox.showerror("ออเดอร์", "ตะกร้าว่าง")
            return

        # ค่าส่ง (ฟรีถ้า >=2 ชิ้น หรือ >=2 รายการ)
        _, total_qty = self._calc_cart_total()
        fees = {"Kerry": 40.0, "J&T": 40.0, "ไปรษณีย์ไทย": 40.0, "Flash": 40.0}
        ship_fee = 0.0 if (total_qty >= 2 or len(self.cart) >= 2) else fees.get(ship_method, 40.0)

        vat = round(subtotal * 0.07, 2)  # 4%
        grand_total = float(subtotal) + float(ship_fee) + float(vat)
        now = datetime.datetime.now().isoformat(timespec="seconds")

        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            # ensure column
            try:
                c.execute("ALTER TABLE orders ADD COLUMN contact_phone TEXT")
            except Exception:
                pass

            if getattr(self, "_current_order_id", None) is None:
                # ----- INSERT ครั้งแรก -----
                c.execute("""
                    INSERT INTO orders (
                        user_email, shipping_method, shipping_address, contact_phone,
                        total_price, status, shipping_status, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'pending', 'draft', ?, ?)
                """, (self.current_email, ship_method, address, phone, grand_total, now, now))
                order_id = c.lastrowid
                self._current_order_id = order_id
            else:
                # ----- UPDATE ออเดอร์เดิม -----
                order_id = self._current_order_id
                c.execute("""
                    UPDATE orders
                    SET shipping_method=?, shipping_address=?, contact_phone=?,
                        total_price=?, status='pending', shipping_status='draft', updated_at=?
                    WHERE id=?
                """, (ship_method, address, phone, grand_total, now, order_id))
                # เคลียร์รายการเดิมแล้วใส่ใหม่ให้ตรงกับตะกร้า
                c.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))

            # ใส่รายการสินค้า
            for pid, it in self.cart.items():
                c.execute("""
                    INSERT INTO order_items (order_id, product_id, name, price, qty, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (order_id, pid, it["name"], float(it["price"]),
                    int(it["qty"]), float(it["price"]) * int(it["qty"])))
                
                


            conn.commit()

        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            messagebox.showerror("ออเดอร์", f"ไม่สามารถบันทึกออเดอร์ได้:\n{e}")
            return
        finally:
            conn.close()

        # sync เบอร์/ที่อยู่กลับโปรไฟล์ (ไม่ทำหลังจากเปลี่ยนหน้าเพื่อลด invalid command name)
        try:
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("UPDATE users SET phone=?, address=? WHERE email=?", (phone, address, self.current_email))
            conn.commit()
        except Exception:
            pass
        finally:
            try: conn.close()
            except Exception: pass

        # ไปหน้า QR/อัปสลิป ด้วย order_id เดิม (ห้ามสร้างซ้ำใน Qrcode)
        self.Qrcode(order_id)



    def _export_invoice_image(self):
    #"""สร้างภาพ PNG ของบิลจากตะกร้าปัจจุบัน แล้วเปิดให้ทันที"""
        try:
            png_path, _ = self._build_invoice_bitmap()
            # เปิดภาพทันที
            try:
                abs_path = os.path.abspath(png_path)
                if os.name == "nt":
                    os.startfile(abs_path)          # Windows
                elif sys.platform == "darwin":
                    subprocess.call(["open", abs_path])  # macOS
                else:
                    subprocess.call(["xdg-open", abs_path])  # Linux
            except Exception:
                messagebox.showinfo("บันทึกบิล", f"บันทึก PNG แล้วที่:\n{png_path}")
        except Exception as e:
            messagebox.showerror("บันทึกบิล", f"ไม่สำเร็จ:\n{e}")


    def _export_invoice_pdf(self):
        """สร้าง PDF ของบิล (แปลงจาก PNG) แล้วเปิดให้ทันที"""
        try:
            png_path, img = self._build_invoice_bitmap()
            pdf_path = png_path.replace(".png", ".pdf")
            img.convert("RGB").save(pdf_path, "PDF", resolution=200.0)

            # เปิด PDF ทันที
            try:
                abs_pdf = os.path.abspath(pdf_path)
                if os.name == "nt":
                    os.startfile(abs_pdf)                 # Windows
                elif sys.platform == "darwin":
                    subprocess.call(["open", abs_pdf])    # macOS
                else:
                    subprocess.call(["xdg-open", abs_pdf])# Linux
            except Exception:
                messagebox.showinfo("บันทึกบิล", f"บันทึก PDF แล้วที่:\n{pdf_path}")
        except Exception as e:
            messagebox.showerror("บันทึกบิล", f"ไม่สำเร็จ:\n{e}")


    def _build_invoice_bitmap(self):
        """วาดบิลเป็นภาพจาก self.cart + ข้อมูลลูกค้า -> (path, PIL.Image)"""
        from PIL import ImageDraw, ImageFont, ImageOps
        import os, datetime

        # ---------- ตัวช่วยฟอร์แมตจำนวนเงิน ----------
        def fmt_money(n: float) -> str:
            """
            < 1000  -> บังคับอย่างน้อย 2 หลักก่อนจุดทศนิยม + 2 หลักหลังจุด
                        ตัวอย่าง: 9.2 -> 09.20, 0.5 -> 00.50, 123.43 -> 123.43
            >= 1000 -> แสดงคอมม่าและทศนิยม 2 หลักตามปกติ เช่น 1,234.50
            """
            try:
                n = float(n)
            except Exception:
                return str(n)

            if abs(n) >= 1000:
                return f"{n:,.2f}"
            # ไม่มีคอมม่าสำหรับเลขหลักหน่วย/สิบ/ร้อย และเติมศูนย์ซ้ายให้ครบ 2 หลัก
            s = f"{n:.2f}"          # เช่น "9.20" , "0.50" , "123.43"
            pre, post = s.split(".")
            # รองรับค่าติดลบถ้ามี (แม้ในบิลปกติไม่น่ามี)
            sign = ""
            if pre.startswith("-"):
                sign, pre = "-", pre[1:]
            pre = pre.zfill(2)      # อย่างน้อย 2 หลัก
            return f"{sign}{pre}.{post}"

        os.makedirs("invoices", exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        png_path = os.path.join("invoices", f"invoice_{ts}.png")

        # --------- เตรียมข้อมูลลูกค้า ---------
        username = getattr(self, "current_username", "Guest")
        email = getattr(self, "current_email", "")
        phone = self._phone_entry.get().strip() if hasattr(self, "_phone_entry") else ""
        address = self._addr_box_for_order.get("1.0", "end").strip() if hasattr(self, "_addr_box_for_order") else ""

        subtotal, total_qty = self._calc_cart_total()
        fees = {"Kerry": 40.0, "J&T": 40.0, "ไปรษณีย์ไทย": 40.0, "Flash": 40.0}
        ship_method = self._ship_method_var.get() if hasattr(self, "_ship_method_var") else "Kerry"
        ship_fee = 0.0 if (total_qty >= 2 or len(self.cart) >= 2) else fees.get(ship_method, 40.0)
        vat = round(subtotal * 0.07, 2)  # ใช้ 7% ตามโค้ดปัจจุบันของคุณ
        grand = subtotal + ship_fee + vat

        # --------- สร้างภาพพื้นฐาน ---------
        W, H = 900, 1200
        img = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(img)

        font_path = r"c:\USERS\LENOVO\APPDATA\LOCAL\MICROSOFT\WINDOWS\FONTS\SARABUN-MEDIUM.TTF"
        if os.path.exists(font_path):
            font_h1 = ImageFont.truetype(font_path, 28)
            font_h2 = ImageFont.truetype(font_path, 22)
            font_txt = ImageFont.truetype(font_path, 18)
            font_small = ImageFont.truetype(font_path, 16)
        else:
            font_h1 = font_h2 = font_txt = font_small = ImageFont.load_default()

        # --------- (มีโลโก้ + กล่องข้อมูลร้านค้า เหมือนก่อนหน้า) ---------
        store = {
            "name": "PHARMACARE+",
            "addr": "968/27 ศิลา เมือง ขอนแก่น 40000",
            "phone": "โทร: 096-7296152",
            "line": "LINE: @pharmacareplus",
            "fb": "Facebook: Pharmacare+",
            "taxid": "เลขประจำตัวผู้เสียภาษี: -"
        }

        def draw_multiline(text, x, y, font, max_w, line_h):
            from textwrap import wrap
            avg_char_w = max(10, font.getlength("ก") or 10)
            chars_per_line = max(10, int(max_w / (avg_char_w * 0.6)))
            yy = y
            for line in wrap(text, width=chars_per_line, break_long_words=True, replace_whitespace=False):
                draw.text((x, yy), line, fill="black", font=font)
                yy += line_h
            return yy

        LOGO_PATH = r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\logo3.png"
        top_y = 20
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo = ImageOps.contain(logo, (160, 160))
            x_center = (W - logo.width) // 2
            img.paste(logo, (x_center, top_y), logo)
            logo_bottom = top_y + logo.height
        else:
            logo_bottom = top_y + 80

        right_block_w = 320
        right_x = W - right_block_w - 30
        y_store = top_y
        draw.text((right_x, y_store), store["name"], fill="black", font=font_h2); y_store += 28
        y_store = draw_multiline(store["addr"], right_x, y_store, font_small, right_block_w, 22)
        draw.text((right_x, y_store), store["phone"], fill="black", font=font_small); y_store += 22
        draw.text((right_x, y_store), store["line"],  fill="black", font=font_small); y_store += 22
        draw.text((right_x, y_store), store["fb"],    fill="black", font=font_small); y_store += 22
        draw.text((right_x, y_store), store["taxid"], fill="black", font=font_small); y_store += 22

        y = max(logo_bottom + 12, y_store + 12)

        # --------- หัวข้อและข้อมูลลูกค้า ---------
        draw.text((40, y), "ใบยืนยันคำสั่งซื้อ (Invoice Preview)", fill="black", font=font_h1); y += 40
        draw.text((40, y), f"วันที่: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill="black", font=font_txt); y += 28
        draw.text((40, y), f"ลูกค้า: {username}   อีเมล: {email}", fill="black", font=font_txt); y += 28
        draw.text((40, y), f"เบอร์โทร: {phone}", fill="black", font=font_txt); y += 28
        draw.text((40, y), "ที่อยู่จัดส่ง:", fill="black", font=font_txt); y += 24

        addr_lines = (address or "").splitlines()
        for line in addr_lines[:6]:
            draw.text((60, y), line, fill="black", font=font_txt); y += 22

        y += 10
        draw.line([(40, y), (W-40, y)], fill="black", width=2); y += 16
        draw.text((40, y), "สินค้า", fill="black", font=font_h2)
        draw.text((500, y), "ราคา", fill="black", font=font_h2)
        draw.text((600, y), "จำนวน", fill="black", font=font_h2)
        draw.text((720, y), "รวมย่อย", fill="black", font=font_h2); y += 30
        draw.line([(40, y), (W-40, y)], fill="black", width=1); y += 12

        # รายการสินค้า
        for pid, it in self.cart.items():
            name  = it["name"]
            price = float(it["price"])
            qty   = int(it["qty"])
            line_total = price * qty
            draw.text((40,  y), name[:40],         fill="black", font=font_txt)
            draw.text((500, y), fmt_money(price),   fill="black", font=font_txt)
            draw.text((620, y), f"{qty}",           fill="black", font=font_txt)
            draw.text((720, y), fmt_money(line_total), fill="black", font=font_txt)
            y += 24

        y += 10
        draw.line([(40, y), (W-40, y)], fill="black", width=1); y += 12
        draw.text((500, y), "รวมสินค้า:", fill="black", font=font_txt)
        draw.text((720, y), fmt_money(subtotal), fill="black", font=font_txt); y += 24

        draw.text((500, y), f"ค่าส่ง ({ship_method}):", fill="black", font=font_txt)
        draw.text((720, y), ("ฟรี" if ship_fee == 0 else fmt_money(ship_fee)), fill="black", font=font_txt); y += 24

        draw.text((500, y), "VAT 7%:", fill="black", font=font_txt)
        draw.text((720, y), fmt_money(vat), fill="black", font=font_txt); y += 24

        draw.line([(500, y), (W-40, y)], fill="black", width=1); y += 12
        draw.text((500, y), "ยอดชำระทั้งหมด:", fill="black", font=font_h2)
        draw.text((720, y), fmt_money(grand), fill="black", font=font_h2)

        # --------- ข้อความท้ายใบเสร็จ ---------
        thanks = "ขอบคุณที่ไว้วางใจ PHARMACARE+"
        kept   = "หากท่านยืนยันสลิป/ชำระเงินแล้ว *กรุณาเก็บใบยืนยันคำสั่งซื้อไว้ หากเกิดปัญหาโปรดติดต่อเรา*"
        y_footer = H - 80
        draw.text((40, y_footer), thanks, fill="black", font=font_txt); y_footer += 24
        _ = draw_multiline(kept, 40, y_footer, font=font_txt, max_w=W-80, line_h=22)

        img.save(png_path)
        return png_path, img




        



#----------------------------------------------------------------------------------------------------------------------------------------------------------#

    def Qrcode(self, order_id=None):
        order_id = order_id or getattr(self, "_current_order_id", None)
        if not order_id:
            messagebox.showerror("ออเดอร์", "ไม่พบหมายเลขออเดอร์"); return
        self._current_order_id = order_id

        # เคลียร์หน้า
        for w in self.main_frame.winfo_children():
            w.destroy()

        # ---------- พื้นหลัง ----------
        try:
            img_path = r"d:\PROJECT\NewBG.png"
            ctk_img = ctk.CTkImage(light_image=Image.open(img_path), size=(1580, 810))
            bg = ctk.CTkLabel(self.main_frame, image=ctk_img, text="")
            bg.image = ctk_img
            bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as e:
            messagebox.showerror("Background", f"โหลดพื้นหลังไม่ได้:\n{e}")

        # ปุ่มย้อนกลับ (ตำแหน่งเดิม)
        ctk.CTkButton(
            self.main_frame, text="🔙", width=50, height=50,
            fg_color="#d60000", hover_color="#f30505", text_color="white",
            command=self.Confirm_items if hasattr(self, "Confirm_items") else self.cart_page
        ).place(relx=0.99, rely=0.27, anchor="e")

        # ---------- คำนวณยอด ----------
        subtotal = sum(float(it["price"]) * int(it["qty"]) for it in self.cart.values())
        total_qty = sum(int(it["qty"]) for it in self.cart.values())
        free_ship = (total_qty >= 2) or (len(self.cart) >= 2)
        base_ship = 40.0
        ship_fee = 0.0 if free_ship else base_ship
        vat = round(subtotal * 0.07, 2)
        grand = round(subtotal + ship_fee + vat, 2)

        # ================== การ์ดกลางจอ (ระบุ width/height ใน constructor) ==================
        container = ctk.CTkFrame(self.main_frame, width=1400, height=640, corner_radius=18, fg_color="white",bg_color="white")
        container.place(relx=0.5, rely=0.61, anchor="center")

        # หัวข้อ
        header = ctk.CTkFrame(container, fg_color="white")
        header.pack(fill="x", padx=24, pady=(18, 4))
        ctk.CTkLabel(header, text="ขอบคุณที่ไว้วางใจ", font=("Oswald", 34, "bold")).pack(anchor="center")

        # เส้นคั่น
        ctk.CTkFrame(container, height=1, fg_color="#e5e7eb").pack(fill="x", padx=24, pady=(8, 18))

        # โซนเนื้อหา 2 คอลัมน์
        body = ctk.CTkFrame(container, fg_color="white")
        body.pack(fill="both", expand=True, padx=24, pady=(0, 24))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=1)
        body.grid_rowconfigure(0, weight=1)

        # ===== ซ้าย: กล่อง QR =====
        qr_card = ctk.CTkFrame(body, corner_radius=16, fg_color="#F8FAFC")
        qr_card.grid(row=0, column=0, sticky="nsew", padx=(0, 12))

        ctk.CTkLabel(qr_card, text="สแกนเพื่อชำระเงิน", font=("Oswald", 18, "bold")).pack(pady=(16, 8))

        qr_wrap = ctk.CTkFrame(qr_card, fg_color="white", corner_radius=14)
        qr_wrap.pack(padx=18, pady=(8, 18), fill="both", expand=True)

        try:
            qr_img = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\Qrcode.png")
            self._qr_ctk = ctk.CTkImage(light_image=qr_img, dark_image=qr_img, size=(350, 350))
            ctk.CTkLabel(qr_wrap, image=self._qr_ctk, text="").pack(padx=18, pady=18)
        except Exception:
            ctk.CTkLabel(qr_wrap, text="(ไม่พบไฟล์ Qrcode.png)", font=("", 15, "bold")).pack(pady=18)

        # ===== ขวา: สรุปยอด + อัปโหลดสลิป + ปุ่มยืนยัน =====
        right_col = ctk.CTkFrame(body, fg_color="white")
        right_col.grid(row=0, column=1, sticky="nsew", padx=(12, 0))

        # สรุปยอด (กล่องเทาอ่อน)
        summary = ctk.CTkFrame(right_col, fg_color="#F3F4F6", corner_radius=14)
        summary.pack(fill="x", pady=(0, 12))

        def _line(parent, left, right, bold=False, pad=(8,4)):
            f = ctk.CTkFrame(parent, fg_color="#F3F4F6")
            f.pack(fill="x", padx=14, pady=pad)
            ctk.CTkLabel(f, text=left, font=("", 15, "bold" if bold else "normal")).pack(side="left")
            ctk.CTkLabel(f, text=right, font=("", 15, "bold" if bold else "normal")).pack(side="right")

        _line(summary, "ยอดสินค้า:", f"{subtotal:,.2f} บาท")
        _line(summary, "VAT 7%:", f"{vat:,.2f} บาท")
        _line(summary, "ค่าส่ง:", "ฟรี" if ship_fee == 0 else f"{ship_fee:,.2f} บาท")
        ctk.CTkFrame(summary, height=1, fg_color="#e5e7eb").pack(fill="x", padx=14, pady=(6, 4))
        _line(summary, "รวมชำระ:", f"{grand:,.2f} บาท", bold=True, pad=(4,10))

        # อัปโหลดสลิป
        slip_box = ctk.CTkFrame(right_col, corner_radius=14, fg_color="white", border_width=1, border_color="#E5E7EB")
        slip_box.pack(fill="x", pady=(4, 12))
        ctk.CTkLabel(slip_box, text="อัปโหลดสลิปโอนเงิน", font=("Oswald", 16, "bold")).pack(pady=(12, 6))
        self._slip_name_var = getattr(self, "_slip_name_var", ctk.StringVar(value="ยังไม่เลือกไฟล์"))
        ctk.CTkLabel(slip_box, textvariable=self._slip_name_var, text_color="#555").pack(pady=(0, 6))

        def _choose_slip():
            from tkinter import filedialog
            fpath = filedialog.askopenfilename(
                title="เลือกไฟล์สลิป",
                filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"), ("All files", "*.*")]
            )
            if not fpath: return
            self._pending_slip_path = fpath
            import os
            self._slip_name_var.set(os.path.basename(fpath))

        ctk.CTkButton(
            slip_box, text="เลือกไฟล์...", fg_color="#0288D1", hover_color="#0277BD", text_color="white",
            height=38, corner_radius=10, command=_choose_slip
        ).pack(pady=(4, 14))

        # ปุ่มยืนยันใหญ่ด้านล่าง
        ctk.CTkButton(
            right_col, text="ยืนยันชำระเงิน ✅",
            fg_color="#16A34A", hover_color="#0F7A39", text_color="white",
            font=("Oswald", 18, "bold"), height=44, corner_radius=12,
            command=self._submit_payment_now
        ).pack(fill="x", pady=(2, 4))



        # ---------- ปุ่มยืนยันชำระเงิน ----------
    def _submit_payment_now(self):
    # ต้องมีสลิป
        slip_src = getattr(self, "_pending_slip_path", None)
        if not slip_src or not os.path.exists(slip_src):
            messagebox.showwarning("สลิป", "กรุณาแนบสลิปก่อนยืนยัน")
            return

        # ต้องมี order เดิมที่สร้างมาจาก _create_order_and_go_payment
        order_id = getattr(self, "_current_order_id", None)
        if not order_id:
            messagebox.showerror("ออเดอร์", "ไม่พบหมายเลขออเดอร์ (กรุณาคอนเฟิร์มสินค้าก่อน)")
            return

        now = datetime.datetime.now().isoformat(timespec="seconds")
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            # 1) ดูสถานะเดิมไว้ก่อน เพื่อจะได้ "ตัดสต็อก" แค่ครั้งแรกที่เปลี่ยนเป็น submitted
            c.execute("SELECT status FROM orders WHERE id=?", (order_id,))
            row = c.fetchone()
            prev_status = row[0] if row else None

            # 2) เก็บไฟล์สลิปลงโฟลเดอร์โปรเจ็กต์
            os.makedirs("slips", exist_ok=True)
            ext = os.path.splitext(slip_src)[1].lower() or ".png"
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            slip_dst = os.path.join("slips", f"order_{order_id}_{ts}{ext}")
            shutil.copyfile(slip_src, slip_dst)

            # 3) อัปเดตออเดอร์เดิม → แนบสลิป + ปรับเป็น submitted (ไม่มี INSERT ออเดอร์ใหม่!!)
            c.execute(
                "UPDATE orders SET slip_path=?, status='submitted', updated_at=? WHERE id=?",
                (slip_dst, now, order_id)
            )

            # 4) ตัดสต็อกเฉพาะครั้งแรกที่เปลี่ยนเป็น submitted (กันตัดซ้ำ)
            if prev_status != "submitted":
                c.execute("SELECT product_id, qty FROM order_items WHERE order_id=?", (order_id,))
                for pid, qty in c.fetchall():
                    c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (int(qty), int(pid)))

            conn.commit()
            self._pending_slip_path = None
            self._current_order_id = None

            # (ถ้ามีระบบออกใบเสร็จ PDF เดิม) เรียกใช้ต่อได้
            # self._export_invoice_pdf()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("ชำระเงิน", f"บันทึกสลิป/อัปเดตออเดอร์ล้มเหลว:\n{e}")
            return
        finally:
            conn.close()

        # 5) เคลียร์ตะกร้า + แจ้งผล + ไปหน้า History/หลัก เหมือนเดิม
        self.cart.clear()
        if hasattr(self, "_update_cart_summary"):
            try: self._update_cart_summary()
            except Exception: pass

        messagebox.showinfo("ส่งสลิปแล้ว", "ระบบได้รับสลิปแล้วค่ะ/ครับ\nสถานะ: รออนุมัติจากแอดมิน")
        try:
            self.History_page()
        except Exception:
            self.main_page(getattr(self, "current_username", "Guest"))


    


     
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
    #"""วาดแถวสินค้า, อัปเดตสรุปยอดฝั่งขวา"""
        self._ensure_cart()

        # ล้างของเดิมในกล่องรายการ
        for w in self.cart_box.winfo_children():
            w.destroy()

        # ถ้าไม่มีสินค้า
        if not self.cart:
            ctk.CTkLabel(self.cart_box, text="ยังไม่มีสินค้าในตะกร้า", font=("Arial", 16)).pack(pady=24)
            # อัปเดตสรุป
            if hasattr(self, "_summary_subtotal_lbl"):
                self._summary_subtotal_lbl.configure(text="ค่าสินค้า: 0.00 บาท")
                self._summary_shipping_lbl.configure(text="ค่าส่ง: 0.00 บาท")
                self._summary_tax_lbl.configure(text="ภาษี (0%): 0.00 บาท")
            if hasattr(self, "total_label"):
                self.total_label.configure(text="รวมทั้งสิ้น: 0.00 บาท")
            # ซิงก์สรุปด้านขวา (textbox เล็ก ๆ ที่ main)
            self._update_cart_summary()
            return

        # คำนวณรวม
        subtotal = 0.0
        total_qty = 0
        for pid, item in self.cart.items():
            qty = int(item["qty"])
            subtotal += float(item["price"]) * qty
            total_qty += qty

        # ----- ค่าส่ง: 2 ชิ้นขึ้นไปฟรี / 1 ชิ้น 40 บาท -----
        shipping = 0.0 if total_qty >= 2 else 40.0

        # ภาษี 7% ตามโค้ดคุณ
        tax_rate = 0.07
        tax = subtotal * tax_rate
        grand = subtotal + shipping + tax

        # วาดรายการเป็นการ์ด
        for pid, item in list(self.cart.items()):
            name = item["name"]
            price = float(item["price"])
            qty = int(item["qty"])
            sub = price * qty

            row = ctk.CTkFrame(self.cart_box, fg_color="white", corner_radius=12)
            row.pack(fill="x", padx=12, pady=6)

            # ชื่อสินค้า (ซ้าย)
            ctk.CTkLabel(row, text=name, anchor="w", width=300).grid(row=0, column=0, sticky="w", padx=(12, 6), pady=10)

            # ราคา
            ctk.CTkLabel(row, text=f"{price:,.2f}", anchor="e", width=110)\
            .grid(row=0, column=1, sticky="e", padx=6)

            # จำนวน (มีปุ่ม ➖qty➕)
            qty_box = ctk.CTkFrame(row, fg_color="transparent")
            qty_box.grid(row=0, column=2)
            ctk.CTkButton(qty_box, text="➖", width=32, command=lambda p=pid: self._change_qty(p, -1))\
            .pack(side="left", padx=(0, 6))
            ctk.CTkLabel(qty_box, text=str(qty), width=34, anchor="center").pack(side="left")
            # ปิดปุ่ม ➕ เมื่อถึงสต็อก
            stock_now = self._get_stock(pid)
            plus_btn = ctk.CTkButton(qty_box, text="➕", width=32,
                                    command=lambda p=pid: self._change_qty(p, +1))
            plus_btn.pack(side="left", padx=(6, 0))
            if qty >= stock_now:
                plus_btn.configure(state="disabled")

            # รวมย่อย
            ctk.CTkLabel(row, text=f"{sub:,.2f}", anchor="e", width=120)\
            .grid(row=0, column=3, sticky="e", padx=6)

            # ลบ
            ctk.CTkButton(row, text="🗑️", width=36, fg_color="#b00020",
                        command=lambda p=pid: self._remove_item(p))\
            .grid(row=0, column=4, sticky="e", padx=(6, 12))

            row.grid_columnconfigure(0, weight=1)

        # อัปเดตตัวเลขสรุปด้านขวา
        if hasattr(self, "_summary_subtotal_lbl"):
            self._summary_subtotal_lbl.configure(text=f"ค่าสินค้า: {subtotal:,.2f} บาท")
            # เปลี่ยนข้อความให้ชัดเจนตามกติกา
            self._summary_shipping_lbl.configure(
                text=f"ค่าส่ง (2 ชิ้นขึ้นไปส่งฟรี): {shipping:,.2f} บาท"
            )
            self._summary_tax_lbl.configure(text=f"ภาษี ({int(tax_rate*100)}%): {tax:,.2f} บาท")
        if hasattr(self, "total_label"):
            self.total_label.configure(text=f"รวมทั้งสิ้น: {grand:,.2f} บาท")
        # ซิงก์สรุปเล็ก (textbox ด้านขวาของ main page ถ้ามี)
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
    # -------------------- IMPORTS (ถ้ามีแล้วข้ามได้) --------------------
    

    # ต้องมีตัวแปร DB อยู่แล้ว เช่น:
    # BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    # DB = os.path.join(BASE_DIR, "pharmacy.db")


    # -------------------- DROP-IN: PROFILE PAGE --------------------
    def Profile_Page(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

        # ---------- พื้นหลัง ----------
        try:
            img_path = r"d:\PROJECT\NewBG.png"
            ctk_img = ctk.CTkImage(light_image=Image.open(img_path), size=(1580, 810))
            bg = ctk.CTkLabel(self.main_frame, image=ctk_img, text="")
            bg.image = ctk_img
            bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as e:
            messagebox.showerror("Background", f"โหลดพื้นหลังไม่ได้:\n{e}")

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

        # ---------- ปุ่มย้อนกลับ (ตำแหน่งเดิม) ----------
        ctk.CTkButton(
            self.main_frame,
            text="🔙", width=50, height=50,
            fg_color="#A40707", hover_color="#FF0101", text_color="white",
            command=lambda: self.main_page(username)
        ).place(relx=0.99, rely=0.27, anchor="e")

        # ====== การ์ดกลางจอ: ย้าย width/height ไปไว้ตอนสร้างวิดเจ็ต ======
        shadow = ctk.CTkFrame(self.main_frame, fg_color="#FFFFFF",bg_color="#FFFFFF", width=980, height=520)
        shadow.place(relx=0.5, rely=0.6, anchor="center")

        card = ctk.CTkFrame(self.main_frame, fg_color="white",bg_color="#FFFFFF", corner_radius=18, width=980, height=520)
        card.place(relx=0.5, rely=0.56, anchor="center")

        # ทำให้ Grid ใช้งานได้ในเฟรมที่กำหนดขนาดไว้
        card.grid_propagate(False)

        # โครง Grid ของการ์ด
        card.grid_rowconfigure(0, weight=0)   # Header
        card.grid_rowconfigure(1, weight=1)   # Content
        card.grid_columnconfigure(0, minsize=300, weight=0)  # ซ้าย (รูป+ปุ่ม)
        card.grid_columnconfigure(1, weight=1)               # ขวา (ข้อมูล)

        # ---------- Header ในการ์ด ----------
        head = ctk.CTkFrame(card, fg_color="white")
        head.grid(row=0, column=0, columnspan=2, sticky="we", padx=22, pady=(16, 0))
        ctk.CTkLabel(head, text="โปรไฟล์ผู้ใช้", font=("Oswald", 22, "bold")).pack(side="left")
        #ctk.CTkLabel(head, text=f"{username} · {email}", font=("", 14)).pack(side="left", padx=12)
        ctk.CTkFrame(card, fg_color="#e5e7eb", height=1).grid(
            row=0, column=0, columnspan=2, sticky="we", padx=22, pady=(46, 0)
        )

        # ---------- คอลัมน์ซ้าย: รูปโปรไฟล์ + ปุ่มเลือกรูป ----------
        left = ctk.CTkFrame(card, fg_color="white")
        left.grid(row=1, column=0, sticky="nsew", padx=(22, 12), pady=22)

        avatar_wrap = ctk.CTkFrame(left, fg_color="#f3f4f6", corner_radius=100)
        avatar_wrap.pack(pady=(4, 12))

        self.profile_img_label = ctk.CTkLabel(
            avatar_wrap,
            text="(ไม่มีรูป)",
            width=150, height=150,
            fg_color="#EEE",
            corner_radius=12
        )
        self.profile_img_label.pack(padx=12, pady=12)

        if current_image:
            try:
                im = Image.open(current_image)
                # ใช้ CTkImage เพื่อเลิก warning และสเกลสวย
                self.profile_ctkimg = ctk.CTkImage(light_image=im, dark_image=im, size=(150, 180))
                self.profile_img_label.configure(image=self.profile_ctkimg, text="")
            except Exception:
                pass

        ctk.CTkButton(
            left,
            text="เลือกรูปโปรไฟล์",
            fg_color="#0288D1", text_color="white",
            command=self._choose_profile_image,
            height=38, corner_radius=12
        ).pack(fill="x")

        # ---------- คอลัมน์ขวา: รายละเอียด ----------
        right = ctk.CTkFrame(card, fg_color="white")
        right.grid(row=1, column=1, sticky="nsew", padx=(12, 22), pady=22)
        right.grid_columnconfigure(0, minsize=130, weight=0)
        right.grid_columnconfigure(1, weight=1)

        # ชื่อ/อีเมล
        ctk.CTkLabel(right, text="ชื่อผู้ใช้ :", font=("Oswald", 18, "bold")).grid(row=0, column=0, sticky="w", pady=(0,6))
        ctk.CTkLabel(right, text=f"{username}", font=("Oswald", 18, "bold")).grid(row=0, column=1, sticky="w", pady=(0,6))

        ctk.CTkLabel(right, text="Email :", font=("Oswald", 18, "bold")).grid(row=1, column=0, sticky="w", pady=(0,6))
        ctk.CTkLabel(right, text=f"{email}", font=("Oswald", 18, "bold")).grid(row=1, column=1, sticky="w", pady=(0,6))

        ctk.CTkFrame(right, fg_color="#e5e7eb", height=1).grid(row=2, column=0, columnspan=2, sticky="we", pady=(10, 12))

        # เบอร์โทร
        ctk.CTkLabel(right, text="เบอร์ :", font=("Oswald", 18, "bold")).grid(row=3, column=0, sticky="w")
        phone_row = ctk.CTkFrame(right, fg_color="white")
        phone_row.grid(row=3, column=1, sticky="we")
        phone_row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(phone_row, text=f"{phone}", font=("Oswald", 18, "bold")).grid(row=0, column=0, sticky="w", pady=(0,6))

        self.phone_entry = ctk.CTkEntry(
            phone_row,
            width=150,
            placeholder_text="กรอกเบอร์ใหม่หรือแก้ไขเบอร์"
        )
        self.phone_entry.grid(row=1, column=0, sticky="we")

        ctk.CTkButton(
            phone_row,
            text="บันทึกเบอร์ใหม่",
            fg_color="green",
            text_color="white",
            command=lambda: self.update_phone(self.phone_entry.get().strip()),
            height=34, corner_radius=10
        ).grid(row=1, column=1, padx=(8,0))

        ctk.CTkFrame(right, fg_color="#e5e7eb", height=1).grid(row=4, column=0, columnspan=2, sticky="we", pady=(12, 12))

        # ที่อยู่
        ctk.CTkLabel(right, text="ที่อยู่ :", font=("Oswald", 18, "bold")).grid(row=5, column=0, sticky="nw")

        addr_area = ctk.CTkFrame(right, fg_color="white")
        addr_area.grid(row=5, column=1, sticky="nsew")
        addr_area.grid_rowconfigure(0, weight=1)
        addr_area.grid_columnconfigure(0, weight=1)

        self.address_box = ctk.CTkTextbox(
            addr_area, width=380, height=100,
            border_width=2, border_color="gray30",
            fg_color="#F7F7F7", text_color="black"
        )
        self.address_box.grid(row=0, column=0, columnspan=3, sticky="nsew")
        self.address_box.insert("1.0", current_address)
        self.address_box.configure(state="disabled")

        self.btn_save_addr = ctk.CTkButton(
            addr_area,
            text="บันทึก",
            width=90, height=32,
            fg_color="#007AFF", hover_color="#005BBB", text_color="white",
            command=self._save_address
        )
        self.btn_save_addr.grid(row=1, column=1, sticky="w", padx=(8,0), pady=(8,0))
        self.btn_save_addr.configure(state="disabled")

        self.btn_edit_addr = ctk.CTkButton(
            addr_area,
            text="แก้ไข",
            width=90, height=32,
            fg_color="#4CAF50", hover_color="#2E7D32", text_color="white",
            command=self._enter_edit_address_mode
        )
        self.btn_edit_addr.grid(row=1, column=0, sticky="w", pady=(8,0))

        self._address_placeholder = placeholder



    # -------------------- DROP-IN: OTHER METHODS (คงเดิม) --------------------
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
        # โทนสีตอนแก้ไข (เหมือนเดิม)
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


    def History_page(self, on_back=None):
    # ล้างหน้าจอ
        for w in self.main_frame.winfo_children():
            w.destroy()

        # BG (ใช้ CTkImage ให้คมบน HiDPI)
        try:
            bg_path = r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\NewBG.png"
            _bg = ctk.CTkImage(light_image=Image.open(bg_path), size=(1580, 810))
            bg = ctk.CTkLabel(self.main_frame, image=_bg, text="")
            bg.image = _bg
            bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as e:
            messagebox.showerror("Background", f"โหลดรูปพื้นหลังไม่สำเร็จ:\n{e}")

        # ปุ่มกลับ
        ctk.CTkButton(
            self.main_frame, text="🔙", width=50, height=50,
            fg_color="#d60000", hover_color="#f30505", text_color="white",
            command=(on_back if on_back else lambda: self.main_page(getattr(self, "current_username", "Guest")))
        ).place(relx=0.99, rely=0.27, anchor="e")

        # กรอบหลัก
        wrap = ctk.CTkFrame(self.main_frame, corner_radius=18, fg_color="white",bg_color="white")
        wrap.place(relx=0.5, rely=0.65, anchor="center", relwidth=0.86, relheight=0.72)

        ctk.CTkLabel(wrap, text="ประวัติคำสั่งซื้อของฉัน", font=("Oswald", 24, "bold")).pack(pady=(14, 8))

        # Header (grid คงที่)
        header = ctk.CTkFrame(wrap, fg_color="#EEF6FF", corner_radius=10)
        header.pack(fill="x", padx=14, pady=(4, 6))
        cols = [
            ("เลขออเดอร์", 180, "w"),
            ("เวลา",       210, "w"),
            ("ยอดสุทธิ",   55, "w"),
            ("สถานะ",      75, "w"),
            ("จัดส่ง",     115, "w"),
            ("สลิป",       200,  "w"),
            ("การทำงาน",   260, "w"),
        ]
        for i, (txt, width, anchor) in enumerate(cols):
            ctk.CTkLabel(header, text=txt, width=width, anchor=anchor).grid(
                row=0, column=i,
                sticky="w" if anchor=="w" else "e" if anchor=="e" else "we",
                padx=8, pady=6
            )
            header.grid_columnconfigure(i, minsize=width)

        # รายการ (scroll)
        body = ctk.CTkScrollableFrame(wrap, fg_color="white", corner_radius=12)
        body.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        # ดึงข้อมูลออเดอร์ของ user
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("""
            SELECT id, created_at,
                COALESCE(total_price, total_amount, 0) AS total_price,
                status, shipping_status, slip_path
            FROM orders
            WHERE user_email=?
            ORDER BY id DESC
        """, (self.current_email,))
        rows = c.fetchall()
        conn.close()

        if not rows:
            ctk.CTkLabel(body, text="(ยังไม่มีคำสั่งซื้อ)", text_color="#666").pack(pady=18)
            return

        def _chip(parent, text, fg="#E5F3FF", color="#0B74DE"):
            f = ctk.CTkFrame(parent, fg_color=fg, corner_radius=999)
            ctk.CTkLabel(f, text=text, text_color=color, padx=10, pady=4).pack()
            return f

        for r, (oid, ts, total, st, shipst, slip) in enumerate(rows):
            row = ctk.CTkFrame(body, fg_color="#F8FBFF" if r % 2 else "white", corner_radius=10)
            row.pack(fill="x", padx=6, pady=4)

            # คอลัมน์คงที่
            ctk.CTkLabel(row, text=f"#{oid}", width=100, anchor="w").grid(row=0, column=0, padx=8, pady=8, sticky="w")
            ctk.CTkLabel(row, text=str(ts or ""), width=170, anchor="w").grid(row=0, column=1, padx=8, pady=8, sticky="w")
            ctk.CTkLabel(row, text=f"{float(total or 0):,.2f}", width=110, anchor="e").grid(row=0, column=2, padx=8, pady=8, sticky="e")

            _chip(row, st or "-").grid(row=0, column=3, padx=6, sticky="nsew")
            _chip(row, shipst or "-", fg="#EAFCEF", color="#0A7F3F" if (shipst or "") != "draft" else "#666")\
                .grid(row=0, column=4, padx=6, sticky="nsew")

            ctk.CTkLabel(row, text=("มี" if slip else "–"), width=90, anchor="center").grid(row=0, column=5, padx=8, pady=8)

            # ปุ่มการทำงาน
            btns = ctk.CTkFrame(row, fg_color="transparent")
            btns.grid(row=0, column=6, padx=6, pady=6, sticky="e")

            ctk.CTkButton(btns, text="รายละเอียด", width=96,
                        command=lambda o=oid: self._open_order_detail(o)).pack(side="left", padx=4)

            ctk.CTkButton(btns, text="แนบสลิป", width=96,
                        fg_color="#0B74DE", hover_color="#095FB5",
                        command=lambda o=oid: self._upload_slip_from_history(o)).pack(side="left", padx=4)

            can_cancel = (st in ("pending", "submitted")) and (shipst not in ("shipped", "delivered"))
            ctk.CTkButton(
                btns, text="ยกเลิก", width=80,
                fg_color=("#B00020" if can_cancel else "#C9C9C9"),
                state=("normal" if can_cancel else "disabled"),
                command=(lambda o=oid: self._cancel_order(o)) if can_cancel else None
            ).pack(side="left", padx=4)

            for i, (_, w, _) in enumerate(cols):
                row.grid_columnconfigure(i, minsize=w)




    def _open_order_detail(self, order_id: int):
        win = ctk.CTkToplevel(self.root)
        win.title(f"Order #{order_id}")
        win.geometry("760x520")
        win.grab_set()

        top = ctk.CTkFrame(win, fg_color="white")
        top.pack(fill="both", expand=True, padx=12, pady=12)

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("""
            SELECT o.user_email, o.shipping_method,
                COALESCE(NULLIF(o.shipping_address,''), u.address, '') AS addr,
                COALESCE(o.total_price, o.total_amount, 0) AS total_price,
                o.status, o.shipping_status, o.created_at, o.slip_path
            FROM orders o
            LEFT JOIN users u ON u.email = o.user_email
            WHERE o.id=?
        """, (order_id,))
        head = c.fetchone()
        if not head:
            conn.close()
            ctk.CTkLabel(top, text="ไม่พบออเดอร์").pack(pady=20)
            return
        email, shipm, addr, total, status, shipst, created, slip = head

        ctk.CTkLabel(top, text=f"Order #{order_id}", font=("Oswald", 20, "bold")).pack(anchor="w", pady=(4, 6))
        ctk.CTkLabel(top, text=f"ผู้สั่งซื้อ: {email}").pack(anchor="w")
        ctk.CTkLabel(top, text=f"วิธีจัดส่ง: {shipm or '-'}").pack(anchor="w")
        ctk.CTkLabel(top, text=f"ที่อยู่: {addr or '-'}").pack(anchor="w")
        ctk.CTkLabel(top, text=f"ยอดสุทธิ: {float(total or 0):,.2f} บาท").pack(anchor="w")
        ctk.CTkLabel(top, text=f"สถานะ: {status or '-'} | จัดส่ง: {shipst or '-'}").pack(anchor="w")
        ctk.CTkLabel(top, text=f"เวลา: {created or '-'}").pack(anchor="w", pady=(0,4))

        box = ctk.CTkScrollableFrame(top, width=680, height=240, label_text="รายการสินค้า")
        box.pack(fill="x", pady=8)
        c.execute("SELECT name, price, qty FROM order_items WHERE order_id=?", (order_id,))
        items = c.fetchall()
        conn.close()

        if not items:
            ctk.CTkLabel(box, text="(ไม่มีรายการ)").pack(pady=10)
        else:
            headf = ctk.CTkFrame(box, fg_color="transparent"); headf.pack(fill="x", padx=6, pady=(4,2))
            for i,(txt,w) in enumerate([("สินค้า",320),("ราคา",120),("จำนวน",120),("รวมย่อย",120)]):
                ctk.CTkLabel(headf, text=txt, width=w, font=("Arial", 14, "bold")).grid(row=0, column=i, sticky="we")
            for name, price, qty in items:
                row = ctk.CTkFrame(box, fg_color="white", corner_radius=6); row.pack(fill="x", padx=6, pady=3)
                sub = float(price or 0)*int(qty or 0)
                ctk.CTkLabel(row, text=name, width=320, anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=6)
                ctk.CTkLabel(row, text=f"{float(price or 0):,.2f}", width=120, anchor="e").grid(row=0, column=1, sticky="e")
                ctk.CTkLabel(row, text=str(qty or 0), width=120, anchor="e").grid(row=0, column=2, sticky="e")
                ctk.CTkLabel(row, text=f"{sub:,.2f}", width=120, anchor="e").grid(row=0, column=3, sticky="e")

        # สลิปพรีวิว (ถ้ามี)
        if slip and os.path.exists(slip):
            try:
                im = Image.open(slip); im.thumbnail((340, 220))
                self._hist_slip_img = ImageTk.PhotoImage(im)
                ctk.CTkLabel(top, image=self._hist_slip_img, text="").pack(pady=8)
            except Exception:
                pass

        ctk.CTkButton(top, text="ปิด", command=win.destroy).pack(pady=(6, 2))


    def _upload_slip_from_history(self, order_id: int):

        path = filedialog.askopenfilename(
            title="เลือกสลิป (PNG/JPG)",
            filetypes=[("Images","*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif")]
        )
        if not path:
            return
        try:
            os.makedirs("slips", exist_ok=True)
            ext = os.path.splitext(path)[1].lower() or ".png"
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            dest = os.path.join("slips", f"order_{order_id}_{ts}{ext}")
            shutil.copyfile(path, dest)

            conn = sqlite3.connect(DB); c = conn.cursor()
            now = datetime.datetime.now().isoformat(timespec="seconds")
            c.execute("UPDATE orders SET slip_path=?, status='submitted', updated_at=? WHERE id=?",
                    (dest, now, order_id))
            conn.commit(); conn.close()
            messagebox.showinfo("สลิป", "อัปโหลดสลิปสำเร็จ รอแอดมินตรวจสอบ")
        except Exception as e:
            try:
                conn.rollback(); conn.close()
            except Exception:
                pass
            messagebox.showerror("ผิดพลาด", str(e))
        self.History_page()

    def _cancel_order(self, order_id: int):
        if not messagebox.askyesno("ยืนยัน", "ต้องการยกเลิกออเดอร์นี้ใช่หรือไม่?"):
            return
        try:
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("SELECT status, shipping_status FROM orders WHERE id=?", (order_id,))
            row = c.fetchone()
            if not row:
                conn.close(); messagebox.showerror("ผิดพลาด","ไม่พบออเดอร์"); return
            status, shipst = row
            if status not in ("pending", "submitted") or (shipst or "draft") not in ("draft", "pending"):
                conn.close(); messagebox.showwarning("ยกเลิกไม่ได้", "ออเดอร์นี้ไม่อยู่ในสถานะที่ยกเลิกได้"); return

            # คืนสต็อก
            c.execute("SELECT product_id, qty FROM order_items WHERE order_id=?", (order_id,))
            for pid, qty in c.fetchall():
                c.execute("UPDATE products SET stock = stock + ? WHERE id=?", (int(qty or 0), pid))

            now = datetime.datetime.now().isoformat(timespec="seconds")
            c.execute("UPDATE orders SET status='cancelled', updated_at=? WHERE id=?", (now, order_id))
            conn.commit(); conn.close()
            messagebox.showinfo("สำเร็จ", "ยกเลิกออเดอร์เรียบร้อย และคืนสต็อกแล้ว")
        except Exception as e:
            try:
                conn.rollback(); conn.close()
            except Exception:
                pass
            messagebox.showerror("ผิดพลาด", str(e))
        self.History_page()

    def Contact_page(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

        # BG (ใช้ CTkImage ให้คมบน HiDPI)
        try:
            bg_path = r"d:\PROJECT\NewBG.png"
            _bg = ctk.CTkImage(light_image=Image.open(bg_path), size=(1580, 810))
            bg = ctk.CTkLabel(self.main_frame, image=_bg, text="")
            bg.image = _bg
            bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as e:
            messagebox.showerror("Background", f"โหลดรูปพื้นหลังไม่สำเร็จ:\n{e}")

        # ปุ่มกลับ
        ctk.CTkButton(
            self.main_frame, text="🔙", width=50, height=50,
            fg_color="#d60000", hover_color="#f30505", text_color="white",
            command=lambda: self.main_page(getattr(self, "current_username", "Guest"))
        ).place(relx=0.99, rely=0.27, anchor="e")

        head = ctk.CTkFrame(self.main_frame, fg_color="#ffffff",bg_color="white", corner_radius=16)
        head.place(relx=0.5, rely=0.65, anchor="center", relwidth=0.9, relheight=0.12)

        # โลโก้
        try:
            logo_path = r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\logo3.png"
            _logo = ctk.CTkImage(light_image=Image.open(logo_path), size=(90, 90))
            ctk.CTkLabel(head, image=_logo, text="").pack(side="left", padx=18, pady=10)
        except Exception:
            ctk.CTkLabel(head, text="PHARMACARE+", font=("Oswald", 28, "bold")).pack(side="left", padx=18, pady=10)

        ctk.CTkLabel(head, text="ติดต่อร้าน PHARMACARE+", font=("Oswald", 28, "bold"), anchor="w")\
            .pack(side="left", padx=10)

        # ---------- 2 คอลัมน์ ----------
        wrap = ctk.CTkFrame(self.main_frame, fg_color="transparent",bg_color="white",)
        wrap.place(relx=0.5, rely=0.65, anchor="center", relwidth=0.86, relheight=0.72)

        # ซ้าย: ข้อมูลร้าน
        left = ctk.CTkFrame(wrap, fg_color="#e1f7fe",bg_color="#ffffff", corner_radius=20)
        left.pack(side="left", fill="both", expand=True, padx=(0, 10), pady=4)

        ctk.CTkLabel(left, text="ข้อมูลติดต่อร้าน", font=("Oswald", 22, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        shop_name = "PHARMACARE+"
        shop_addr = "968/27 ศิลา เมือง ขอนแก่น 40000"
        shop_phone = "096-7296152"
        shop_email = "tanakorn.ja@kkumail.com"
        maps_url = "https://maps.app.goo.gl/A1hNB57Zo3Z1F9bC8"
        fb_url   = "https://web.facebook.com/tanakorn.jannongwa?locale=th_TH"
        line_url = "https://line.me/ti/p/BZGPHOl0L-"
        hrs = [
            ("ทุกวัน", "09:00 - 00:00"),
            ("*เร่งด่วน*", "ติดต่อผ่าน Email ,Facebook ,Line"),
            
        ]

        info = ctk.CTkFrame(left, fg_color="#f8f9fb", corner_radius=14)
        info.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(info, text=f"🏪 {shop_name}", font=("Sarabun", 18, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(info, text=f"📍 {shop_addr}", wraplength=520, justify="left").pack(anchor="w", padx=14, pady=2)

        # แถวเบอร์/อีเมล + ปุ่มคัดลอก
        row1 = ctk.CTkFrame(info, fg_color="transparent"); row1.pack(fill="x", padx=10, pady=(8, 0))
        ctk.CTkLabel(row1, text=f"📞 {shop_phone}").pack(side="left", padx=6)
        ctk.CTkButton(row1, text="คัดลอก", width=70, command=lambda: self._copy_clip(shop_phone)).pack(side="left", padx=6)

        row2 = ctk.CTkFrame(info, fg_color="transparent"); row2.pack(fill="x", padx=10, pady=(6, 12))
        ctk.CTkLabel(row2, text=f"✉️  {shop_email}").pack(side="left", padx=6)
        ctk.CTkButton(row2, text="คัดลอก", width=70, command=lambda: self._copy_clip(shop_email)).pack(side="left", padx=6)

        # เวลาทำการ
        hrs_box = ctk.CTkFrame(left, fg_color="#f8f9fb", corner_radius=14)
        hrs_box.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkLabel(hrs_box, text="🕘 ติดต่อสอบถาม", font=("Sarabun", 18, "bold")).pack(anchor="w", padx=14, pady=(12, 6))
        for d, t in hrs:
            ctk.CTkLabel(hrs_box, text=f"• {d}: {t}").pack(anchor="w", padx=20, pady=2)

        # ปุ่มโซเชียล/แผนที่
        btns = ctk.CTkFrame(left, fg_color="transparent"); btns.pack(fill="x", padx=16, pady=(6, 16))
        ctk.CTkButton(btns, text="🌏 แผนที่ (Google Maps)", fg_color="#0B57D0", text_color="white",
              command=lambda: self._open_url(maps_url)).pack(side="left", padx=6)

        ctk.CTkButton(btns, text="💬 LINE", fg_color="#06C755", text_color="white",
                    command=lambda: self._open_url(line_url)).pack(side="left", padx=6)

        ctk.CTkButton(btns, text="📘 Facebook", fg_color="#1877F2", text_color="white",
                    command=lambda: self._open_url(fb_url)).pack(side="left", padx=6)

        # ขวา: ฟอร์มส่งข้อความ
        right = ctk.CTkFrame(wrap, fg_color="#e1f7fe",bg_color="#ffffff", corner_radius=20)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=4)

        ctk.CTkLabel(right, text="ส่งข้อความถึงเรา", font=("Oswald", 22, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        form = ctk.CTkFrame(right, fg_color="#f8f9fb", corner_radius=14)
        form.pack(fill="both", expand=True, padx=16, pady=(0, 16))

        # ช่องกรอก
        ctk.CTkLabel(form, text="ชื่อ-นามสกุล").pack(anchor="w", padx=14, pady=(14, 4))
        name_e = ctk.CTkEntry(form, placeholder_text="ชื่อของคุณ"); name_e.pack(fill="x", padx=14)

        ctk.CTkLabel(form, text="อีเมล/เบอร์โทร").pack(anchor="w", padx=14, pady=(10, 4))
        email_e = ctk.CTkEntry(form, placeholder_text="example@email.com"); email_e.pack(fill="x", padx=14)

        ctk.CTkLabel(form, text="เรื่องที่ติดต่อ").pack(anchor="w", padx=14, pady=(10, 4))
        subject_e = ctk.CTkEntry(form, placeholder_text="เช่น สอบถามสินค้า / แจ้งปัญหา / อื่น ๆ")
        subject_e.pack(fill="x", padx=14)

        ctk.CTkLabel(form, text="ข้อความ").pack(anchor="w", padx=14, pady=(10, 4))
        msg_t = ctk.CTkTextbox(form, height=180); msg_t.pack(fill="both", expand=True, padx=14, pady=(0, 12))

        # ปุ่มส่ง/ล้าง
        btn_row = ctk.CTkFrame(form, fg_color="transparent"); btn_row.pack(fill="x", padx=14, pady=(0, 14))
        def _send():
            ok = self._send_contact_message(name_e.get(), email_e.get(), subject_e.get(), msg_t.get("1.0","end"))
            if ok:
                name_e.delete(0,"end"); email_e.delete(0,"end"); subject_e.delete(0,"end"); msg_t.delete("1.0","end")
                messagebox.showinfo("ขอบคุณครับ", "ส่งข้อความเรียบร้อย เราจะติดต่อกลับโดยเร็วที่สุด")

        ctk.CTkButton(btn_row, text="ส่งข้อความ", fg_color="green", text_color="white", command=_send)\
            .pack(side="left")
        ctk.CTkButton(btn_row, text="ล้างฟอร์ม", fg_color="#b00020", text_color="white",
                    command=lambda:(name_e.delete(0,"end"), email_e.delete(0,"end"),
                                    subject_e.delete(0,"end"), msg_t.delete("1.0","end")))\
            .pack(side="left", padx=8)

    def _open_url(self, url: str):
     #"""เปิด URL ผ่านเบราว์เซอร์"""
        try:
            webbrowser.open_new(url)
        except Exception as e:
            messagebox.showerror("เปิดลิงก์ไม่ได้", f"{url}\n\n{e}")

    def _copy_clip(self, text: str):
        """คัดลอกข้อความ"""
        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            self.root.update()
            messagebox.showinfo("คัดลอกแล้ว", text)
        except Exception as e:
            messagebox.showerror("คัดลอกไม่ได้", f"{e}")

    def _send_contact_message(self, name: str, contact: str, subject: str, message: str) -> bool:
        """บันทึกข้อความลงฐาน และเปิดหน้าเมลผู้ใช้"""
        import sqlite3, datetime, urllib.parse

        name = name.strip()
        contact = contact.strip()
        subject = subject.strip()
        message = message.strip()

        if not (name and contact and message):
            messagebox.showwarning("กรอกไม่ครบ", "กรุณากรอก ชื่อ, ช่องติดต่อ, และข้อความ")
            return False

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("""
            CREATE TABLE IF NOT EXISTS contact_messages(
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, contact TEXT, subject TEXT, message TEXT, created_at TEXT
            )
        """)
        c.execute("""
            INSERT INTO contact_messages(name, contact, subject, message, created_at)
            VALUES (?,?,?,?,?)
        """, (name, contact, subject, message, datetime.datetime.now().isoformat(timespec="seconds")))
        conn.commit()
        conn.close()

        # เปิดหน้าอีเมล (ให้ลูกค้ากดส่งจริง ถ้ามี)
        shop_email = "tanakorn.ja@kkumail.com"
        mailto = f"mailto:{shop_email}?subject={urllib.parse.quote(subject)}&body={urllib.parse.quote(message)}"
        webbrowser.open_new(mailto)

        return True
    
    def _send_contact_message(self, name: str, contact: str, subject: str, message: str) -> bool:
        """บันทึกรายงานจากลูกค้าเข้าสู่ตาราง reports แล้วให้แอดมินเปิดดูใน open_admin_report ได้"""
        name = (name or "").strip()
        contact = (contact or "").strip()
        subject = (subject or "").strip()
        message = (message or "").strip()

        if not message:
            messagebox.showwarning("ส่งข้อความ", "กรุณากรอกข้อความ"); return False
        if not contact:
            # ถ้าไม่กรอก ให้ fallback เป็นอีเมลล็อกอิน (ถ้ามี)
            contact = getattr(self, "current_email", "") or "-"

        now = datetime.datetime.now().isoformat(timespec="seconds")
        try:
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("""INSERT INTO reports (created_at, user_name, contact, subject, message, status)
                        VALUES (?, ?, ?, ?, ?, 'new')""",
                    (now, name, contact, subject, message))
            conn.commit()
            return True
        except Exception as e:
            try: conn.rollback()
            except: pass
            messagebox.showerror("ส่งข้อความ", f"บันทึกไม่สำเร็จ:\n{e}")
            return False
        finally:
            try: conn.close()
            except: pass




    
        









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


        ctk.CTkButton(self.main_frame, text="🔙 Log out",
                    fg_color="#ff0000", hover_color="#5e0303", text_color="white",
                    command=self._logout).place(relx=0.7, rely=0.95, anchor="e")
        
        OrdersButton = ctk.CTkButton(
                self.main_frame, 
                text="🧾 เช็คออเดอร์", 
                width=120, height=36,
                fg_color="#00796B", 
                hover_color="#00564F", 
                text_color="white",
                command=self.open_orders_admin
                ) 
        OrdersButton.place(relx=0.6, rely=0.95, anchor="e")

        Report = ctk.CTkButton(
                self.main_frame, 
                text="Report", 
                width=120, height=36,
                fg_color="#00796B", 
                hover_color="#00564F", 
                text_color="white",
                command=self.open_admin_report
                ) 
        Report.place(relx=0.5, rely=0.95, anchor="e")

        seller = ctk.CTkButton(
            self.main_frame,
            text="🧾 สรุปยอดขาย", 
                width=120, height=36,
                fg_color="#00796B", 
                hover_color="#00564F", 
                text_color="white",
                command=self.admin_sales_report
                ) 
        seller.place(relx=0.4, rely=0.95, anchor="e")

        # ปุ่มย้อนกลับ
        """back_btn = ctk.CTkButton(
            self.main_frame, text="🔙",
            width=50, height=50, fg_color="green",
            hover_color="darkgreen", text_color="white",
            command=lambda: self.main_page(getattr(self, "current_username", "Guest"))
        )
        back_btn.place(relx=0.99, rely=0.13, anchor="e")"""

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

    # ---------- helpers (Admin) ----------
    def _on_admin_cat_change(self, selected):
        subs = CATEGORY_MAP.get(selected, [])
        if not subs:
            subs = [""]
        self.p_subcat.configure(values=subs)
        self.p_subcat.set(subs[0] if subs else "")

    def open_orders_admin(self):
        """หน้าเช็คออเดอร์สำหรับแอดมิน"""
        # ล้างหน้า
        for w in self.main_frame.winfo_children():
            w.destroy()

        # พื้นหลัง (ใช้ภาพเดียวกับหน้า admin หลักของคุณ)
        try:
            bg_path = r"d:\PROJECT\NewBG.png"
            _bg = Image.open(bg_path).resize((1920, 1000))
            self.bg_photo = ImageTk.PhotoImage(_bg)
            ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="").place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception:
            pass

        # ปุ่มกลับสู่หน้า Admin (จัดการสินค้า)
        
        
        BackButton = ctk.CTkButton(
                self.main_frame, 
                text="Back", 
                width=50, height=50,
                fg_color="#790800", 
                hover_color="#F61111", 
                text_color="white",
                command=self.open_admin
                ) 
        BackButton.place(relx=1.0, rely=0.27, anchor="e")

        # กรอบเนื้อหา
        wrap = ctk.CTkFrame(self.main_frame, fg_color="white",bg_color="white", corner_radius=18)
        wrap.place(relx=0.5, rely=0.62, anchor="center", relwidth=0.9, relheight=0.75)

        ctk.CTkLabel(wrap, text="เช็คออเดอร์ลูกค้า", font=("Oswald", 24, "bold")).pack(pady=(14, 8))

        # แถบตัวกรอง
        filter_bar = ctk.CTkFrame(wrap, fg_color="#F6FAFF", corner_radius=10)
        filter_bar.pack(fill="x", padx=12, pady=(4, 8))

        ctk.CTkLabel(filter_bar, text="สถานะ:").pack(side="left", padx=(8, 6))
        self._adm_order_status = ctk.StringVar(value="ทั้งหมด")
        ctk.CTkOptionMenu(filter_bar, variable=self._adm_order_status,
                        values=["ทั้งหมด", "pending", "submitted", "approved", "cancelled"]
                        ).pack(side="left")

        ctk.CTkLabel(filter_bar, text="   สลิป:").pack(side="left", padx=(12, 6))
        self._adm_slip_filter = ctk.StringVar(value="ทั้งหมด")
        ctk.CTkOptionMenu(filter_bar, variable=self._adm_slip_filter,
                        values=["ทั้งหมด", "มีสลิป", "ไม่มีสลิป"]
                        ).pack(side="left")

        ctk.CTkButton(filter_bar, text="รีเฟรช", command=self._admin_orders_refresh).pack(side="right", padx=8)

        # รายการออเดอร์
        self._orders_list = ctk.CTkScrollableFrame(wrap, fg_color="white", corner_radius=10)
        self._orders_list.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        # โหลดครั้งแรก
        self._admin_orders_refresh()

    def _admin_orders_refresh(self):
   
        for w in self._orders_list.winfo_children():
            w.destroy()

        status = self._adm_order_status.get() if hasattr(self, "_adm_order_status") else "ทั้งหมด"
        slip_f = self._adm_slip_filter.get() if hasattr(self, "_adm_slip_filter") else "ทั้งหมด"

        where, params = [], []
        if status != "ทั้งหมด":
            where.append("status=?"); params.append(status)
        if slip_f == "มีสลิป":
            where.append("slip_path IS NOT NULL AND slip_path <> ''")
        elif slip_f == "ไม่มีสลิป":
            where.append("(slip_path IS NULL OR slip_path='')")

        sql = """
            SELECT id, user_email, total_price, status, shipping_status, created_at, slip_path
            FROM orders
        """
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC"

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()

        if not rows:
            ctk.CTkLabel(self._orders_list, text="(ยังไม่มีออเดอร์ตามตัวกรอง)", text_color="#777").pack(pady=12)
            return

        # หัวตาราง
        header = ctk.CTkFrame(self._orders_list, fg_color="#EEF6FF", corner_radius=8)
        header.pack(fill="x", padx=6, pady=(4, 6))
        for i, (txt, w, anchor) in enumerate([
            ("เลข", 120, "w"), ("เวลา", 170, "w"), ("อีเมล", 190, "w"),
            ("ยอดสุทธิ", 110, "e"), ("สถานะ", 120, "center"),
            ("จัดส่ง", 110, "center"), ("สลิป", 90, "center"), ("จัดการ", 80, "e")
        ]):
            ctk.CTkLabel(header, text=txt, width=w, anchor=anchor).grid(row=0, column=i, padx=6, pady=6, sticky="w")

        # แถวข้อมูล
        for r, (oid, email, total, st, shipst, ts, slip) in enumerate(rows):
            row = ctk.CTkFrame(self._orders_list, fg_color=("#F9FCFF" if r % 2 else "white"), corner_radius=8)
            row.pack(fill="x", padx=6, pady=3)

            ctk.CTkLabel(row, text=f"#{oid}", width=70, anchor="w").grid(row=0, column=0, padx=6, pady=6, sticky="w")
            ctk.CTkLabel(row, text=str(ts or ""), width=170, anchor="w").grid(row=0, column=1, padx=6, sticky="w")
            ctk.CTkLabel(row, text=email or "-", width=240, anchor="w").grid(row=0, column=2, padx=6, sticky="w")
            ctk.CTkLabel(row, text=f"{float(total or 0):,.2f}", width=110, anchor="e").grid(row=0, column=3, padx=6, sticky="e")
            ctk.CTkLabel(row, text=st or "-", width=120, anchor="center").grid(row=0, column=4, padx=6)
            ctk.CTkLabel(row, text=shipst or "-", width=110, anchor="center").grid(row=0, column=5, padx=6)
            ctk.CTkLabel(row, text=("มี" if slip else "–"), width=90, anchor="center").grid(row=0, column=6, padx=6)

            # ปุ่มจัดการ
            btns = ctk.CTkFrame(row, fg_color="transparent")
            btns.grid(row=0, column=7, padx=6, sticky="e")

            ctk.CTkButton(btns, text="รายละเอียด", width=96,
                        command=lambda o=oid: self._admin_open_order_detail(o)).pack(side="left", padx=4)

            # อนุมัติได้ต่อเมื่อมีสลิปและยังไม่ถูกยกเลิก/อนุมัติ
            allow_approve = (st in ("submitted", "pending")) and bool(slip)
            ctk.CTkButton(btns, text="อนุมัติ", width=86,
                        fg_color=("#2E7D32" if allow_approve else "#C9C9C9"),
                        state=("normal" if allow_approve else "disabled"),
                        command=(lambda o=oid: self._admin_set_status(o, "approved")) if allow_approve else None
                        ).pack(side="left", padx=4)

            # ยกเลิก: หากยังไม่ shipped/delivered
            allow_cancel = (st != "cancelled") and (shipst not in ("shipped", "delivered"))
            ctk.CTkButton(btns, text="ยกเลิก", width=86,
                        fg_color=("#B00020" if allow_cancel else "#C9C9C9"),
                        state=("normal" if allow_cancel else "disabled"),
                        command=(lambda o=oid: self._admin_cancel_order(o)) if allow_cancel else None
                        ).pack(side="left", padx=4)
            
    def _admin_open_order_detail(self, order_id: int):
        """ป๊อปอัปแสดงหัวบิล + รายการสินค้า + พรีวิวสลิป"""
        win = ctk.CTkToplevel(self.root); win.title(f"Order #{order_id}")
        win.geometry("820x560"); win.grab_set()

        top = ctk.CTkFrame(win, fg_color="white"); top.pack(fill="both", expand=True, padx=12, pady=12)

        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("""
            SELECT o.user_email, o.shipping_method,
                COALESCE(NULLIF(o.shipping_address,''), u.address, '') AS addr,
                COALESCE(o.total_price, o.total_amount, 0) AS total_price,
                o.status, o.shipping_status, o.created_at, o.slip_path
            FROM orders o
            LEFT JOIN users u ON u.email = o.user_email
            WHERE o.id=?
        """, (order_id,))
        head = c.fetchone()
        if not head:
            conn.close()
            ctk.CTkLabel(top, text="ไม่พบออเดอร์").pack(pady=20)
            return
        email, shipm, addr, total, status, shipst, created, slip = head

        ctk.CTkLabel(top, text=f"Order #{order_id}", font=("Oswald", 20, "bold")).pack(anchor="w", pady=(4, 6))
        ctk.CTkLabel(top, text=f"ผู้สั่งซื้อ: {email}").pack(anchor="w")
        ctk.CTkLabel(top, text=f"วิธีจัดส่ง: {shipm or '-'}").pack(anchor="w")
        ctk.CTkLabel(top, text=f"ที่อยู่: {addr or '-'}").pack(anchor="w")
        ctk.CTkLabel(top, text=f"ยอดสุทธิ: {float(total or 0):,.2f} บาท").pack(anchor="w")
        ctk.CTkLabel(top, text=f"สถานะ: {status or '-'} | จัดส่ง: {shipst or '-'}").pack(anchor="w")
        ctk.CTkLabel(top, text=f"เวลา: {created or '-'}").pack(anchor="w", pady=(0,4))

        # รายการสินค้า
        box = ctk.CTkScrollableFrame(top, width=760, height=240, label_text="รายการสินค้า")
        box.pack(fill="x", pady=6)
        c.execute("SELECT name, price, qty FROM order_items WHERE order_id=?", (order_id,))
        items = c.fetchall()
        conn.close()

        headf = ctk.CTkFrame(box, fg_color="transparent"); headf.pack(fill="x", padx=6, pady=(4,2))
        for i,(txt,w) in enumerate([("สินค้า",420),("ราคา",120),("จำนวน",120)]):
            ctk.CTkLabel(headf, text=txt, width=w, font=("Arial", 14, "bold")).grid(row=0, column=i, sticky="we")

        if not items:
            ctk.CTkLabel(box, text="(ไม่มีรายการ)").pack(pady=10)
        else:
            for name, price, qty in items:
                row = ctk.CTkFrame(box, fg_color="white", corner_radius=6); row.pack(fill="x", padx=6, pady=3)
                ctk.CTkLabel(row, text=name, width=420, anchor="w").grid(row=0, column=0, sticky="w", padx=6, pady=6)
                ctk.CTkLabel(row, text=f"{float(price):,.2f}", width=120, anchor="e").grid(row=0, column=1, sticky="e")
                ctk.CTkLabel(row, text=str(qty), width=120, anchor="e").grid(row=0, column=2, sticky="e")

        # พรีวิวสลิป (ถ้ามี)
        if slip and os.path.exists(slip):
            try:
                im = Image.open(slip); im.thumbnail((360, 220))
                self._admin_slip_photo = ImageTk.PhotoImage(im)
                ctk.CTkLabel(top, text="สลิปที่แนบ", font=("Arial", 14, "bold")).pack(pady=(8, 4))
                ctk.CTkLabel(top, image=self._admin_slip_photo, text="").pack()
                # เปิดไฟล์สลิปด้วยแอปเริ่มต้น (Windows)
                ctk.CTkButton(top, text="เปิดสลิปด้วยโปรแกรมเริ่มต้น", command=lambda: os.startfile(slip)).pack(pady=6)
            except Exception:
                pass

        ctk.CTkButton(top, text="ปิด", command=win.destroy).pack(pady=(6, 2))

    def _admin_set_status(self, order_id: int, new_status: str):
     #"""อนุมัติออเดอร์ → เปลี่ยน status, อัปเดตเวลา"""
        try:
            now = datetime.datetime.now().isoformat(timespec="seconds")
            conn = sqlite3.connect(DB); c = conn.cursor()
            # อนุมัติ: ให้ shipping_status ขยับจาก draft → packed
            if new_status == "approved":
                c.execute("UPDATE orders SET status=?, shipping_status=CASE WHEN shipping_status='draft' THEN 'packed' ELSE shipping_status END, updated_at=? WHERE id=?",
                        (new_status, now, order_id))
            else:
                c.execute("UPDATE orders SET status=?, updated_at=? WHERE id=?", (new_status, now, order_id))
            conn.commit(); conn.close()
            messagebox.showinfo("สำเร็จ", f"อัปเดตออเดอร์ #{order_id} เป็น {new_status} แล้ว")
        except Exception as e:
            try:
                conn.rollback(); conn.close()
            except Exception:
                pass
            messagebox.showerror("ผิดพลาด", str(e))
        self._admin_orders_refresh()

    def _admin_cancel_order(self, order_id: int):
    #"""ยกเลิกออเดอร์ + คืนสต็อก ถ้ายังไม่จัดส่ง"""
        if not messagebox.askyesno("ยืนยัน", f"ต้องการยกเลิกออเดอร์ #{order_id} ใช่ไหม?"):
            return
        try:
            conn = sqlite3.connect(DB); c = conn.cursor()
            # ตรวจสถานะก่อน
            c.execute("SELECT status, shipping_status FROM orders WHERE id=?", (order_id,))
            row = c.fetchone()
            if not row:
                conn.close(); messagebox.showerror("ผิดพลาด", "ไม่พบออเดอร์"); return
            status, shipst = row
            if shipst in ("shipped", "delivered"):
                conn.close(); messagebox.showwarning("ยกเลิกไม่ได้", "ออเดอร์นี้จัดส่งไปแล้ว"); return

            # คืนสต็อก
            c.execute("SELECT product_id, qty FROM order_items WHERE order_id=?", (order_id,))
            for pid, qty in c.fetchall():
                c.execute("UPDATE products SET stock = stock + ? WHERE id=?", (int(qty or 0), pid))

            # อัปเดตสถานะ
            now = datetime.datetime.now().isoformat(timespec="seconds")
            c.execute("UPDATE orders SET status='cancelled', updated_at=? WHERE id=?", (now, order_id))
            conn.commit(); conn.close()
            messagebox.showinfo("สำเร็จ", "ยกเลิกออเดอร์และคืนสต็อกเรียบร้อย")
        except Exception as e:
            try:
                conn.rollback(); conn.close()
            except Exception:
                pass
            messagebox.showerror("ผิดพลาด", str(e))
        self._admin_orders_refresh()






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
                text=f"#{pid}  {name} - {price:.2f} บาท",
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

    # ---------- เติมลงในไฟล์เดิม (ภายในคลาส PharmaApp) ----------

# สถานะที่ถือว่า "อนุมัติแล้ว" / พร้อมนับยอดขาย
    

    # -------------------- (1) ด้านบนของคลาส: ค่าคงที่สำหรับการนับยอดขาย --------------------
  # ปรับเพิ่ม/ลดตามที่คุณใช้จริง

# -------------------- (2) index เร่งความเร็ว --------------------
    # ===== เพิ่มไว้ตอน import ส่วนบนของไฟล์ =====
  # ใช้ตอนเลื่อนเดือน

# ===== เพิ่มคงที่ (ไว้ใกล้ ๆ GLOBALS อื่น ๆ) =====


# ─────────────────────────────────────────────────────────────
# 1) ดัชนีฐานข้อมูล (เรียกใช้ได้ซ้ำ ปลอดภัย)
    def _ensure_indexes(self):
        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_orders_status     ON orders(status)")
            c.execute("CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items(order_id)")
            conn.commit()
        except Exception:
            pass
        finally:
            try: conn.close()
            except: pass
            
        
    # ─────────────────────────────────────────────────────────────
    # 2) คำนวณช่วงเวลา + ป้ายบอกช่วง + ฐานสำหรับปุ่มเลื่อนก่อนหน้า/ถัดไป
    def _calc_range(self, mode: str, start_text: str = "", end_text: str = "", base_date=None):
        """
        คืน (start_iso, end_iso, label_str, prev_base, next_base)
        - mode: day|week|month|year|custom
        - base_date: datetime.date ใช้เป็นฐานสำหรับ ⟨ ก่อนหน้า / ถัดไป ⟩
        """
        import datetime as dt
        def iso(d):
            return dt.datetime.combine(d, dt.time.min).strftime("%Y-%m-%dT00:00:00")

        today = dt.date.today() if base_date is None else base_date

        if mode == "day":
            s = today
            e = s + dt.timedelta(days=1)
            label = s.strftime("วัน %d/%m/%Y")
            prev_b = s - dt.timedelta(days=1)
            next_b = s + dt.timedelta(days=1)

        elif mode == "week":
            monday = today - dt.timedelta(days=today.weekday())  # จันทร์
            s = monday
            e = s + dt.timedelta(days=7)
            label = f"สัปดาห์ {s.strftime('%d/%m/%Y')} – {(e - dt.timedelta(days=1)).strftime('%d/%m/%Y')}"
            prev_b = s - dt.timedelta(days=7)
            next_b = s + dt.timedelta(days=7)

        elif mode == "month":
            first = today.replace(day=1)
            s = first
            # หาวันแรกของเดือนถัดไป
            if first.month == 12:
                first_next = first.replace(year=first.year + 1, month=1, day=1)
            else:
                first_next = first.replace(month=first.month + 1, day=1)
            e = first_next
            label = s.strftime("เดือน %m/%Y")
            prev_b = (first - dt.timedelta(days=1)).replace(day=1)
            next_b = first_next

        elif mode == "year":
            first = today.replace(month=1, day=1)
            s = first
            e = first.replace(year=first.year + 1)
            label = s.strftime("ปี %Y")
            prev_b = first.replace(year=first.year - 1)
            next_b = first.replace(year=first.year + 1)

        else:
            # custom โดยใช้ start_text/end_text (YYYY-MM-DD)
            try:
                sdate = dt.datetime.strptime(start_text.strip(), "%Y-%m-%d").date()
                edate = dt.datetime.strptime(end_text.strip(), "%Y-%m-%d").date()
                s, e = sdate, edate + dt.timedelta(days=1)  # [start, end)
                label = f"{sdate.strftime('%d/%m/%Y')} – {edate.strftime('%d/%m/%Y')}"
            except Exception:
                s = today
                e = today + dt.timedelta(days=1)
                label = s.strftime("วัน %d/%m/%Y")
            prev_b = next_b = today
        return iso(s), iso(e), label, prev_b, next_b

    # ─────────────────────────────────────────────────────────────
    # 3) Query: สรุปยอดรวมช่วงเวลา
    def _query_sales_summary(self, start_iso: str, end_iso: str):
        conn = sqlite3.connect(DB); c = conn.cursor()
        # จำนวนออเดอร์ที่ "นับยอด"
        c.execute(f"""
            SELECT COUNT(*)
            FROM orders
            WHERE created_at >= ? AND created_at < ?
            AND (
                    status IN ({",".join("?"*len(APPROVED_STATUSES))})
                OR status='approved'
                OR (status='submitted' AND shipping_status IN ('approved','packed','shipped','delivered'))
            )
        """, (start_iso, end_iso, *APPROVED_STATUSES))
        orders_count = int(c.fetchone()[0] or 0)

        # รวมบรรทัดสินค้า (ก่อน VAT) + จำนวนชิ้น
        c.execute(f"""
            SELECT 
                COALESCE(SUM(oi.qty * COALESCE(oi.price, p.price)), 0) AS items_total,
                COALESCE(SUM(oi.qty), 0) AS units_sold
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            LEFT JOIN products p ON p.id = oi.product_id
            WHERE o.created_at >= ? AND o.created_at < ?
            AND (
                    o.status IN ({",".join("?"*len(APPROVED_STATUSES))})
                OR o.status='approved'
                OR (o.status='submitted' AND o.shipping_status IN ('approved','packed','shipped','delivered'))
            )
        """, (start_iso, end_iso, *APPROVED_STATUSES))
        items_total, units_sold = c.fetchone()
        items_total = float(items_total or 0.0)
        units_sold  = int(units_sold or 0)

        # รวมเป็นยอดต่อบิล (คิด VAT 4% ต่อบิล แล้วค่อย SUM)
        c.execute(f"""
            WITH per_order AS (
                SELECT 
                    o.id,
                    COALESCE(SUM(oi.qty * COALESCE(oi.price, p.price)), 0) AS sum_items
                FROM orders o
                LEFT JOIN order_items oi ON oi.order_id = o.id
                LEFT JOIN products p ON p.id = oi.product_id
                WHERE o.created_at >= ? AND o.created_at < ?
                AND (
                        o.status IN ({",".join("?"*len(APPROVED_STATUSES))})
                    OR o.status='approved'
                    OR (o.status='submitted' AND o.shipping_status IN ('approved','packed','shipped','delivered'))
                )
                GROUP BY o.id
            )
            SELECT COALESCE(SUM(ROUND(sum_items * 1.07, 2)), 0)  -- VAT 7%
            FROM per_order
        """, (start_iso, end_iso, *APPROVED_STATUSES))
        order_total = float(c.fetchone()[0] or 0.0)

        conn.close()
        return {
            "orders_count": orders_count,
            "order_total": order_total,  # รวม VAT แล้ว
            "items_total": items_total,  # ก่อน VAT
            "units_sold": units_sold,
        }

    # ─────────────────────────────────────────────────────────────
    # 4) Query: Top สินค้าขายดี
    def _query_best_sellers(self, start_iso: str, end_iso: str, limit: int = 20):
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute(f"""
            SELECT 
                oi.product_id,
                COALESCE(oi.name, p.name) AS name,
                SUM(oi.qty) AS total_qty,
                COALESCE(SUM(oi.line_total), SUM(oi.qty * COALESCE(oi.price, p.price))) AS total_amount
            FROM order_items oi
            JOIN orders o ON o.id = oi.order_id
            LEFT JOIN products p ON p.id = oi.product_id
            WHERE o.created_at >= ? AND o.created_at < ?
            AND (
                    o.status IN ({",".join("?"*len(APPROVED_STATUSES))})
                OR o.status='approved'
                OR (o.status='submitted' AND (o.shipping_status IN ('approved','packed','shipped','delivered')))
            )
            GROUP BY oi.product_id, COALESCE(oi.name, p.name)
            HAVING total_qty > 0
            ORDER BY total_qty DESC, total_amount DESC
            LIMIT ?
        """, (start_iso, end_iso, *APPROVED_STATUSES, limit))
        rows = c.fetchall()
        conn.close()
        return rows  # [(pid, name, total_qty, total_amount), ...]

    # ─────────────────────────────────────────────────────────────
    # 5) Export CSV
    def _export_sales_csv(self, start_iso: str, end_iso: str, best_rows, summary):
        import csv, os, datetime
        os.makedirs("reports", exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = os.path.join("reports", f"sales_report_{ts}.csv")
        with open(path, "w", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            w.writerow(["ช่วงเวลา", start_iso, "ถึง (ไม่รวม)", end_iso])
            w.writerow([])
            w.writerow(["สรุปยอดขาย"])
            w.writerow(["จำนวนออเดอร์", summary["orders_count"]])
            w.writerow(["รวมเงินจาก Orders (รวม VAT 7%)", f"{summary['order_total']:.2f}"])
            w.writerow(["รวมเงินจาก Items (ก่อน VAT)", f"{summary['items_total']:.2f}"])
            w.writerow(["จำนวนชิ้นที่ขาย", summary["units_sold"]])
            w.writerow([])
            w.writerow(["Top สินค้าขายดี"])
            w.writerow(["product_id", "name", "total_qty", "total_amount"])
            for pid, name, qty, amt in best_rows:
                w.writerow([pid, name, qty, f"{amt:.2f}"])
        return path

    # ─────────────────────────────────────────────────────────────
    # 6) UI รายงานสรุปยอดขาย (มี Back, Export, ปฏิทิน, ปุ่มเลื่อนช่วง)
    def admin_sales_report(self):
        """หน้า UI รายงานยอดขาย + ปฏิทิน + Top สินค้าขายดี + กล่องยอดรวมสุทธิ (Items + VAT + ค่าส่ง)"""
        self._ensure_indexes()

        # เคลียร์หน้า
        for w in self.main_frame.winfo_children():
            w.destroy()

        # Header
        top = ctk.CTkFrame(self.main_frame); top.pack(fill="x", pady=8)
        ctk.CTkLabel(top, text="📈 รายงานสรุปยอดขาย", font=("", 20, "bold")).pack(side="left", padx=10)
        top_right = ctk.CTkFrame(top, fg_color="transparent"); top_right.pack(side="right", padx=8)

        # ปุ่ม Export (เปิดทีหลังเมื่อมี payload)
        self._export_btn = ctk.CTkButton(top_right, text="Export CSV", state="disabled",
                                        command=self._export_current_sales)
        self._export_btn.pack(side="right", padx=6)
        # ปุ่มกลับ
        self._back_btn = ctk.CTkButton(top_right, text="กลับไปจัดการสินค้า", command=self.open_admin)
        self._back_btn.pack(side="right", padx=6)

        # โหมดช่วงเวลา
        filt = ctk.CTkFrame(self.main_frame); filt.pack(fill="x", padx=10, pady=(0,8))
        self._period_var = ctk.StringVar(value="day")
        for val, txt in [("day","รายวัน"),("week","รายสัปดาห์"),("month","รายเดือน"),("year","รายปี"),("custom","กำหนดเอง")]:
            ctk.CTkRadioButton(filt, text=txt, variable=self._period_var, value=val).pack(side="left", padx=(6,2))

        # ช่วงกำหนดเอง + ปฏิทิน
        custom = ctk.CTkFrame(self.main_frame); custom.pack(fill="x", padx=10, pady=(6,8))
        ctk.CTkLabel(custom, text="เริ่ม:").pack(side="left")
        self._start_cal = DateEntry(custom, width=12, date_pattern='yyyy-mm-dd'); self._start_cal.pack(side="left", padx=(6,14))
        ctk.CTkLabel(custom, text="สิ้นสุด:").pack(side="left")
        self._end_cal = DateEntry(custom, width=12, date_pattern='yyyy-mm-dd'); self._end_cal.pack(side="left", padx=(6,14))
        ctk.CTkButton(custom, text="ดูรายงานช่วงนี้",
                    command=lambda: self._refresh_sales_ui(mode=self._period_var.get(), reset_base=True)).pack(side="left", padx=6)

        # ปุ่มลัด + ข้อความช่วง
        nav = ctk.CTkFrame(self.main_frame, fg_color="transparent"); nav.pack(fill="x", padx=10)
        ctk.CTkButton(nav, text="วันนี้",     command=lambda: self._refresh_sales_ui(mode="day",   reset_base=True)).pack(side="left", padx=4)
        ctk.CTkButton(nav, text="สัปดาห์นี้", command=lambda: self._refresh_sales_ui(mode="week",  reset_base=True)).pack(side="left", padx=4)
        ctk.CTkButton(nav, text="เดือนนี้",   command=lambda: self._refresh_sales_ui(mode="month", reset_base=True)).pack(side="left", padx=4)
        ctk.CTkButton(nav, text="ปีนี้",      command=lambda: self._refresh_sales_ui(mode="year",  reset_base=True)).pack(side="left", padx=4)

        bar = ctk.CTkFrame(self.main_frame); bar.pack(fill="x", padx=10, pady=(6,8))
        self._prev_btn = ctk.CTkButton(bar, text="⟨ ก่อนหน้า", width=110, command=lambda: self._shift_period(-1))
        self._next_btn = ctk.CTkButton(bar, text="ถัดไป ⟩",   width=110, command=lambda: self._shift_period(+1))
        self._label_period = ctk.CTkLabel(bar, text="—", font=("", 16, "bold"))
        self._prev_btn.pack(side="left"); self._next_btn.pack(side="right"); self._label_period.pack(side="left", padx=10)

        # สรุป + ตาราง
        body = ctk.CTkFrame(self.main_frame); body.pack(fill="both", expand=True, padx=10, pady=(0,12))
        self._summary_box = ctk.CTkFrame(body); self._summary_box.pack(fill="x", pady=(8,6))
        self._table_box   = ctk.CTkScrollableFrame(body, height=420, label_text="สินค้าขายดี"); self._table_box.pack(fill="both", expand=True)

        # Export / Back ด้านล่าง
        foot = ctk.CTkFrame(self.main_frame, fg_color="transparent"); foot.pack(fill="x", padx=10, pady=(0,10))
        ctk.CTkButton(foot, text="⬅ Back", fg_color="#B71C1C", hover_color="#7f1111", command=self.open_admin).pack(side="left")
        self._export_btn_bottom = ctk.CTkButton(foot, text="Export CSV", state="disabled", command=self._export_current_sales)
        self._export_btn_bottom.pack(side="right")

        # state ภายใน
        self._sales_base_date = None
        self._last_sales_payload = None

        # แสดงครั้งแรก
        self._refresh_sales_ui(mode=self._period_var.get(), reset_base=True)


    # ─────────────────────────────────────────────────────────────
    # 7) ปุ่มเลื่อนช่วง (ก่อนหน้า/ถัดไป)
    def _shift_period(self, step:int):
        mode = self._period_var.get() if hasattr(self, "_period_var") else "day"
        base = self._sales_base_date
        import datetime as dt
        if base is None:
            base = dt.date.today()

        if mode == "day":
            base = base + dt.timedelta(days=step)
        elif mode == "week":
            base = base + dt.timedelta(days=7*step)
        elif mode == "month":
            y, m = base.year, base.month
            m2 = m + step
            y += (m2 - 1) // 12
            m2 = ((m2 - 1) % 12) + 1
            day = min(base.day, calendar.monthrange(y, m2)[1])
            base = base.replace(year=y, month=m2, day=day)
        elif mode == "year":
            base = base.replace(year=base.year + step)

        self._sales_base_date = base
        self._refresh_sales_ui(mode=mode)

    def _shipping_total(self, start_iso: str, end_iso: str) -> float:
        """
        คิดค่าส่งรวมในช่วงเวลา:
        - ถ้าออเดอร์นั้น 'จำนวนชิ้นรวม' < 2 → ค่าส่ง 40 บาท
        - ถ้า 'จำนวนชิ้นรวม' >= 2 → ส่งฟรี
        นับเฉพาะออเดอร์สถานะที่ถือว่าอนุมัติ/นับยอดขาย
        """
        conn = sqlite3.connect(DB); c = conn.cursor()
        c.execute("""
            SELECT o.id, SUM(oi.qty) as total_qty
            FROM orders o
            JOIN order_items oi ON oi.order_id = o.id
            WHERE o.created_at >= ? AND o.created_at < ?
            AND (
                o.status IN ({sts})
                OR o.status='approved'
                OR (o.status='submitted' AND (o.shipping_status IN ('approved','packed','shipped','delivered')))
            )
            GROUP BY o.id
        """.format(sts=",".join(["?"]*len(APPROVED_STATUSES))),
        (start_iso, end_iso, *APPROVED_STATUSES))
        rows = c.fetchall(); conn.close()

        total_shipping = 0.0
        for _oid, qty in rows:
            qty = int(qty or 0)
            if qty < 2:
                total_shipping += 40.0
        return float(total_shipping)



    # ─────────────────────────────────────────────────────────────
    # 8) วาดสรุป + ตารางตามช่วงที่เลือก
    def _refresh_sales_ui(self, mode: str, reset_base: bool = False):
        import datetime as dt
        if reset_base:
            self._sales_base_date = dt.date.today()

        # อ่านวันจากปฏิทิน (ใช้เมื่อ custom)
        s_txt = self._start_cal.get_date().strftime("%Y-%m-%d") if hasattr(self, "_start_cal") else ""
        e_txt = self._end_cal.get_date().strftime("%Y-%m-%d")   if hasattr(self, "_end_cal") else ""

        start_iso, end_iso, label, _prev_b, _next_b = self._calc_range(
            mode,
            s_txt if mode == "custom" else "",
            e_txt if mode == "custom" else "",
            base_date=self._sales_base_date
        )
        self._label_period.configure(text=("(กำหนดเอง) " + label) if mode == "custom" else label)

        # ดึงข้อมูล
        summary = self._query_sales_summary(start_iso, end_iso)
        rows    = self._query_best_sellers(start_iso, end_iso, limit=20)

        # ---------- วาดสรุป ----------
        for w in self._summary_box.winfo_children():
            w.destroy()

        def _stat(parent, title, value):
            card = ctk.CTkFrame(parent, corner_radius=12, fg_color="#ffffff")
            card.pack(side="left", padx=6, pady=6, fill="x", expand=True)
            ctk.CTkLabel(card, text=title, font=("", 14, "bold")).pack(anchor="w", padx=12, pady=(10,2))
            ctk.CTkLabel(card, text=value, font=("", 18)).pack(anchor="w", padx=12, pady=(0,10))

        grid = ctk.CTkFrame(self._summary_box, fg_color="#F6FAFF"); grid.pack(fill="x", padx=6, pady=6)

        _stat(grid, "จำนวนออเดอร์", f"{summary['orders_count']:,}")
        _stat(grid, "รวมเงิน (Orders, รวม VAT)", f"{summary['order_total']:,.2f} บาท")
        _stat(grid, "รวมเงิน (Items, ก่อน VAT)", f"{summary['items_total']:,.2f} บาท")
        _stat(grid, "จำนวนชิ้นที่ขาย", f"{summary['units_sold']:,} ชิ้น")

        # ---- กล่องยอดรวมสุดท้าย: Items(ก่อน VAT) + VAT + ค่าส่ง ----
        VAT_RATE = 0.07  # <<<< ปรับเป็น 0.07 ถ้าอยากดู 7%
        base_before_vat = float(summary.get("items_total", 0.0))   # ใช้ Items เป็นฐานภาษี
        vat_amount = round(base_before_vat * VAT_RATE, 2)
        ship_total = self._shipping_total(start_iso, end_iso)
        grand_total = base_before_vat + vat_amount + ship_total

        card = ctk.CTkFrame(grid, corner_radius=12, fg_color="#ffffff")
        card.pack(side="left", padx=6, pady=6, fill="x", expand=True)
        ctk.CTkLabel(card, text="💰 ยอดรวมสุดท้าย (สุทธิ + VAT + ค่าส่ง)", font=("", 14, "bold")).pack(anchor="w", padx=12, pady=(10,2))
        ctk.CTkLabel(card, text=f"ยอดสุทธิ (ก่อน VAT): {base_before_vat:,.2f} บาท", font=("", 13)).pack(anchor="w", padx=12)
        ctk.CTkLabel(card, text=f"VAT {int(VAT_RATE*100)}%: {vat_amount:,.2f} บาท", font=("", 13)).pack(anchor="w", padx=12)
        ctk.CTkLabel(card, text=f"ค่าส่งรวม: {ship_total:,.2f} บาท", font=("", 13)).pack(anchor="w", padx=12)
        ctk.CTkLabel(card, text=f"รวมทั้งสิ้น: {grand_total:,.2f} บาท", font=("", 18, "bold")).pack(anchor="w", padx=12, pady=(0,10))

        # ---------- ตาราง Top สินค้าขายดี ----------
        for w in self._table_box.winfo_children():
            w.destroy()

        header = ctk.CTkFrame(self._table_box, fg_color="#EEF6FF", corner_radius=8)
        header.pack(fill="x", padx=8, pady=(6,4))
        for i,(txt,wid,anc) in enumerate([
            ("อันดับ",80,"center"),
            ("สินค้า",520,"w"),
            ("ชิ้นที่ขาย",140,"w"),
            ("ยอดรวม (บาท)",160,"w")
        ]):
            ctk.CTkLabel(header, text=txt, width=wid, anchor=anc, font=("", 13, "bold")).grid(row=0, column=i, sticky="we")

        if not rows:
            ctk.CTkLabel(self._table_box, text="(ไม่มีข้อมูลในช่วงนี้)", text_color="#666").pack(pady=10)
        else:
            for idx,(pid,name,qty,amt) in enumerate(rows, start=1):
                r = ctk.CTkFrame(self._table_box, corner_radius=10, fg_color="#ffffff")
                r.pack(fill="x", padx=8, pady=4)
                ctk.CTkLabel(r, text=str(idx), width=60, anchor="center").grid(row=0, column=0, sticky="we", padx=6, pady=8)
                ctk.CTkLabel(r, text=name or f"Product #{pid}", width=420, anchor="w").grid(row=0, column=1, sticky="we", padx=6)
                ctk.CTkLabel(r, text=f"{int(qty):,}", width=120, anchor="e").grid(row=0, column=2, sticky="we", padx=6)
                ctk.CTkLabel(r, text=f"{float(amt):,.2f}", width=160, anchor="e").grid(row=0, column=3, sticky="we", padx=6)

        # เก็บ payload + เปิดปุ่ม Export
        self._last_sales_payload = {
            "start_iso": start_iso,
            "end_iso": end_iso,
            "summary": summary,
            "rows": rows,
            # ใครอยาก export กล่องสุทธิด้วยก็เพิ่มค่าพวกนี้ลง payload ได้
            "grand_from_items": {
                "base_before_vat": base_before_vat,
                "vat_amount": vat_amount,
                "shipping": ship_total,
                "grand_total": grand_total,
                "vat_rate": VAT_RATE,
            }
        }
        self._export_btn.configure(state="normal")
        self._export_btn_bottom.configure(state="normal")


    # ─────────────────────────────────────────────────────────────
    # 9) Export ปัจจุบัน
    def _export_current_sales(self):
        if not getattr(self, "_last_sales_payload", None):
            return
        p = self._export_sales_csv(
            self._last_sales_payload["start_iso"],
            self._last_sales_payload["end_iso"],
            self._last_sales_payload["rows"],
            self._last_sales_payload["summary"],
        )
        try:
            if os.name == "nt":
                os.startfile(os.path.abspath(p))  # เปิดไฟล์ทันทีบน Windows
        except Exception:
            pass
        messagebox.showinfo("Export", f"บันทึกไฟล์รายงานแล้ว:\n{p}")

    

    def open_admin_report(self):
    # ล้างหน้า
        for w in self.main_frame.winfo_children():
            w.destroy()

        top = ctk.CTkFrame(self.main_frame); top.pack(fill="x", pady=8)
        ctk.CTkLabel(top, text="📮 กล่องข้อความลูกค้า (Reports)", font=("", 20, "bold")).pack(side="left", padx=12)
        ctk.CTkButton(top, text="Back", command=self.open_admin).pack(side="right", padx=6)
        ctk.CTkButton(top, text="รีเฟรช", command=self.open_admin_report).pack(side="right", padx=8)

        body = ctk.CTkScrollableFrame(self.main_frame, height=560)
        body.pack(fill="both", expand=True, padx=12, pady=8)

        # header
        hdr = ctk.CTkFrame(body, fg_color="#eef2f7"); hdr.pack(fill="x", pady=(0,6))
        for i, t in enumerate(["เวลา", "ชื่อผู้ติดต่อ", "อีเมล/โทร", "เรื่อง", "สถานะ", "การทำงาน"]):
            ctk.CTkLabel(hdr, text=t, width=[160,160,170,240,320,50][i], anchor="w").grid(row=0, column=i, padx=6, pady=6)

        # ดึงข้อมูล
        rows = []
        try:
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("SELECT id, created_at, user_name, contact, subject, message, status FROM reports ORDER BY id DESC")
            rows = c.fetchall()
        finally:
            try: conn.close()
            except: pass

        # แสดงทีละแถว
        for rid, created, uname, contact, subj, msg, status in rows:
            row = ctk.CTkFrame(body, fg_color="white"); row.pack(fill="x", padx=0, pady=4)
            ctk.CTkLabel(row, text=created, width=160, anchor="w").grid(row=0, column=0, padx=6, pady=8, sticky="w")
            ctk.CTkLabel(row, text=uname or "-", width=140, anchor="w").grid(row=0, column=1, padx=6, sticky="w")
            ctk.CTkLabel(row, text=contact or "-", width=180, anchor="w").grid(row=0, column=2, padx=6, sticky="w")
            ctk.CTkLabel(row, text=subj or "(ไม่ระบุ)", width=220, anchor="w").grid(row=0, column=3, padx=6, sticky="w")
            ctk.CTkLabel(row, text=status, width=90).grid(row=0, column=4, padx=6)

            btns = ctk.CTkFrame(row, fg_color="transparent"); btns.grid(row=0, column=5, padx=6, sticky="w")
            def _view(m=msg):
                # ป๊อปอัปอ่านข้อความฉบับเต็ม
                top = ctk.CTkToplevel(self.root); top.title("ข้อความลูกค้า"); top.geometry("620x420")
                t = ctk.CTkTextbox(top, wrap="word"); t.pack(fill="both", expand=True, padx=12, pady=12)
                t.insert("1.0", m or ""); t.configure(state="disabled")
            ctk.CTkButton(btns, text="อ่านข้อความ", command=_view).pack(side="left", padx=4)

            def _mark(s, id_=rid):
                try:
                    conn = sqlite3.connect(DB); c = conn.cursor()
                    c.execute("UPDATE reports SET status=?, message=message WHERE id=?", (s, id_))
                    conn.commit()
                finally:
                    try: conn.close()
                    except: pass
                self.open_admin_report()

            ctk.CTkButton(btns, text="กำลังดำเนินการ", fg_color="#0B57D0", text_color="white",
                        command=lambda id_=rid: _mark("in_progress", id_)).pack(side="left", padx=4)
            ctk.CTkButton(btns, text="ปิดงาน", fg_color="green", text_color="white",
                        command=lambda id_=rid: _mark("done", id_)).pack(side="left", padx=4)

            def _delete(id_=rid):
                if not messagebox.askyesno("ลบข้อความ", "ต้องการลบรายการนี้หรือไม่?"): return
                try:
                    conn = sqlite3.connect(DB); c = conn.cursor()
                    c.execute("DELETE FROM reports WHERE id=?", (id_,))
                    conn.commit()
                finally:
                    try: conn.close()
                    except: pass
                self.open_admin_report()
            ctk.CTkButton(btns, text="ลบ", fg_color="#b00020", text_color="white",
                        command=_delete).pack(side="left", padx=4)
            
# ---------------- Email Helper (SMTP) ----------------
# ---------------- OTP Utils ----------------
def generate_otp() -> str:
    import random
    return f"{random.randint(0, 999999):06d}"

# ---------------- Email Helper (SMTP) ----------------
def send_email(to_addr: str, subject: str, body: str) -> bool:
    """
    คืนค่า True เมื่อส่งได้, False ถ้ายังไม่ตั้งค่า/ส่งไม่สำเร็จ
    ต้องตั้งค่า SMTP_* ให้ตรงผู้ให้บริการของคุณ (เช่น Gmail SMTP + App Password)
    """
    SMTP_HOST = "smtp.gmail.com"      # ตัวอย่าง: Gmail
    SMTP_PORT = 587
    SMTP_USER = "tanakorn.ja@kkumail.com"   # <-- แก้
    SMTP_PASS = "acot riqp snpw jepx"        # <-- แก้ (App Password, ไม่ใช่รหัสปกติ)
    FROM_NAME = "PharmaCare"

    if "YOUR_ACCOUNT" in SMTP_USER or "YOUR_APP_PASSWORD" in SMTP_PASS:
        return False  # ยังไม่ตั้งค่า

    import smtplib
    from email.mime.text import MIMEText
    from email.utils import formataddr

    msg = MIMEText(body, _charset="utf-8")
    msg["Subject"] = subject
    msg["From"] = formataddr((FROM_NAME, SMTP_USER))
    msg["To"] = to_addr

    try:
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(SMTP_USER, [to_addr], msg.as_string())
        server.quit()
        return True
    except Exception:
        return False

# ---------------- SMS Helper (เช่น Twilio) ----------------
 



        



        


    

    
    
    



# ----------------- Run -----------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = PharmaApp(root)
    root.mainloop()
# ----------------- Run -----------------
