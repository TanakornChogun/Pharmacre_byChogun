"""
PharmaCare - ตัวอย่างโปรเจคร้านขายยา (CustomTkinter + SQLite)
ไฟล์เดียว รันได้เลย (ต้องติดตั้ง customtkinter, pillow, qrcode)
"""

import sqlite3
import hashlib
import os
import datetime
import qrcode
from io import BytesIO
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import messagebox

# ---------- ตั้งค่า CustomTkinter ----------
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("green")

# ---------- Database helper ----------
DB_PATH = "pharmacare.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

#สร้างตาราง
def init_db():
    conn = get_db_connection()
    c = conn.cursor()
    # users: id, username, password_hash, is_admin
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
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
    # ถ้าไม่มี admin ให้เพิ่มตัวอย่าง (username: admin, password: admin)
    c.execute("SELECT * FROM users WHERE username = ?", ("admin",))
    if not c.fetchone():
        pw_hash = hash_password("admin")
        c.execute("INSERT INTO users (email, username, password_hash, is_admin) VALUES (?, ?, ?, ?)",
                  ("admin@local", "admin", pw_hash, 1))
        conn.commit()
    conn.close()

#รับค่า password ตรวจเช็คPassword
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


#หนา้ต่าง แสดงโปรแกรม login
class PharmaCareApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PharmaCare")
        self.root.geometry("900x600")
        self.current_user = None
        self.cart = {}

        self.main_frame = ctk.CTkFrame(root)
        self.main_frame.pack(fill="both", expand=True)

        self.show_login_screen()

    def clear_main(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    # ---------- Login ----------
    def show_login_screen(self):
        self.clear_main()

        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background3.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0.5, rely=0.5, anchor="center")

        frame = ctk.CTkFrame(self.main_frame, corner_radius=10, width=500, height=620,
                             fg_color="lightyellow", border_width=3, border_color="green")
        frame.place(relx=0.5, rely=0.5, anchor="center")
        frame.pack_propagate(False)

        img = Image.open(r"C:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\logo3.png")
        img = img.resize((340, 180))
        self.logo_img = ImageTk.PhotoImage(img)
        ctk.CTkLabel(frame, image=self.logo_img, text="").pack(side="top", ipady=40)

        ctk.CTkLabel(frame, text="Email", font=("Oswald", 12, "bold")).pack(pady=(5, 2))
        email_entry = ctk.CTkEntry(frame, width=150, placeholder_text="Email")
        email_entry.pack()

        ctk.CTkLabel(frame, text="Username", font=("Oswald", 12, "bold")).pack(pady=(10, 2))
        username_entry = ctk.CTkEntry(frame, width=150, placeholder_text="Username")
        username_entry.pack()

        ctk.CTkLabel(frame, text="Password", font=("Oswald", 12, "bold")).pack(pady=(10, 2))
        password_entry = ctk.CTkEntry(frame, width=150, show="*", placeholder_text="Password")
        password_entry.pack()

        def login_action():
            email = email_entry.get().strip()
            username = username_entry.get().strip()
            pw = password_entry.get().strip()

            if not email or not username or not pw:
                messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณากรอก email, username และ password")
                return

            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE email = ? AND username = ?", (email, username))
            row = c.fetchone()
            conn.close()

            if row:
                if verify_password(pw, row["password_hash"]):
                    self.current_user = row
                    self.cart = {}
                    self.show_home_screen()
                else:
                    messagebox.showerror("ล้มเหลว", "Password ไม่ถูกต้อง")
            else:
                messagebox.showerror("ล้มเหลว", "Email หรือ Username ไม่ถูกต้อง หรือไม่ตรงกัน")

        def register_screen():
            self.clear_main()

            img_bg2 = Image.open(r"C:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\Bgg.png")
            img_bg2 = img_bg2.resize((1960, 1000))
            self.bg_photo = ImageTk.PhotoImage(img_bg2)
            bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
            bg.place(relx=0.5, rely=0.5, anchor="center")

            frame2 = ctk.CTkFrame(self.main_frame, corner_radius=10, width=400, height=620,
                                  fg_color="lightyellow", border_width=3, border_color="green")
            frame2.place(relx=0.5, rely=0.5, anchor="center")
            frame2.pack_propagate(False)

            img2 = Image.open(r"C:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\logo3.png")
            img2 = img2.resize((140, 80))
            self.logo_img = ImageTk.PhotoImage(img2)
            ctk.CTkLabel(frame2, image=self.logo_img, text="").pack(side="top", ipady=5)

            ctk.CTkLabel(frame2, text="Email*", font=("Oswald", 12, "bold")).pack(pady=(3, 2))
            email_entry2 = ctk.CTkEntry(frame2, width=150, placeholder_text="กรุณากรอก Email")
            email_entry2.pack()

            ctk.CTkLabel(frame2, text="Username*", font=("Oswald", 12, "bold")).pack(pady=(3, 2))
            username_entry2 = ctk.CTkEntry(frame2, width=150, placeholder_text="กรุณากรอก Username")
            username_entry2.pack()

            ctk.CTkLabel(frame2, text="Password*", font=("Oswald", 12, "bold")).pack(pady=(3, 2))
            password_entry2 = ctk.CTkEntry(frame2, width=150, show="*", placeholder_text="กรุณากรอก Password")
            password_entry2.pack()

            ctk.CTkLabel(frame2, text="ยืนยัน Password*", font=("Oswald", 12, "bold")).pack(pady=(3, 2))
            confirm_entry2 = ctk.CTkEntry(frame2, width=150, show="*", placeholder_text="กรุณากรอก Password อีกครั้ง")
            confirm_entry2.pack()

            def register_action2():
                email = email_entry2.get().strip()
                username = username_entry2.get().strip()
                pw = password_entry2.get().strip()
                confirm_pw = confirm_entry2.get().strip()

                if not email or not username or not pw or not confirm_pw:
                    messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณากรอกให้ครบทุกช่อง")
                    return

                if pw != confirm_pw:
                    messagebox.showerror("รหัสผ่านไม่ตรงกัน", "กรุณากรอกรหัสผ่านใหม่ให้ตรงกัน")
                    return

                conn = get_db_connection()
                c = conn.cursor()
                c.execute("SELECT * FROM users WHERE email = ? OR username = ?", (email, username))
                existing = c.fetchone()

                if existing:
                    messagebox.showerror("ผิดพลาด", "Email หรือ Username นี้ถูกใช้แล้ว")
                else:
                    try:
                        c.execute("INSERT INTO users (email, username, password_hash) VALUES (?, ?, ?)",
                                  (email, username, hash_password(pw)))
                        conn.commit()
                        messagebox.showinfo("สำเร็จ", "สมัครสมาชิกเรียบร้อยแล้ว เข้าสู่ระบบได้เลย")
                        # login อัตโนมัติ
                        c.execute("SELECT * FROM users WHERE email = ? AND username = ?", (email, username))
                        self.current_user = c.fetchone()
                        self.show_home_screen()
                    except sqlite3.IntegrityError:
                        messagebox.showerror("ผิดพลาด", "เกิดข้อผิดพลาดในการบันทึกข้อมูล")
                conn.close()

            btn_register2 = ctk.CTkButton(frame2, text="Register (สร้างบัญชี)",
                                         font=("Oswald", 12, "bold"),
                                         fg_color="green", hover_color="pink", text_color="white",
                                         command=register_action2)
            btn_register2.pack(pady=(30, 6))

            btn_login2 = ctk.CTkButton(frame2, text="กลับไป Login",
                                       font=("Oswald", 12, "bold"),
                                       fg_color="green", hover_color="red", text_color="white",
                                       command=self.show_login_screen)
            btn_login2.pack(pady=(10, 1))

        btn_login = ctk.CTkButton(frame, text="Log in", font=("Oswald", 12, "bold"),
                                  fg_color="green", hover_color="pink", text_color="white",
                                  command=login_action)
        btn_login.pack(pady=(30, 1))

        btn_register = ctk.CTkButton(frame, text="Register (สร้างบัญชี)", font=("Oswald", 12, "bold"),
                                     fg_color="green", hover_color="pink", text_color="white",
                                     command=register_screen)
        btn_register.pack(pady=(10, 6))

    # ---------- Home ----------
    def show_home_screen(self):
        self.clear_main()
        ctk.CTkLabel(self.main_frame, text=f"ยินดีต้อนรับ {self.current_user['username']}!", font=("Oswald", 20, "bold")).pack(pady=20)

if __name__ == "__main__":
    root = ctk.CTk()
    init_db()
    app = PharmaCareApp(root)
    root.mainloop()