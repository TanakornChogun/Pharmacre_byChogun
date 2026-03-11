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

DB = "pharmacy.db"

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
        elif username != user[1]:
            messagebox.showerror("Error", "Username ไม่ถูกต้อง")
        elif password != user[2]:
            messagebox.showerror("Error", "รหัสผ่านไม่ถูกต้อง")
        else:
            messagebox.showinfo("Success", f"เข้าสู่ระบบสำเร็จ ยินดีต้อนรับ {username}")

            # ตั้งค่าผู้ใช้ก่อน
            self.current_username = username
            self.current_email = email
            #self.is_admin = (email in ADMIN_EMAILS) or (username in ADMIN_USERNAMES)

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
            #self.is_admin = (email in ADMIN_EMAILS) or (username in ADMIN_USERNAMES)
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
        self.login_page




# ----------------- Run -----------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = PharmaApp(root)
    root.mainloop()
# ----------------- Run -----------------
