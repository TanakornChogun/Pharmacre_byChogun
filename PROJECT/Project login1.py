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

        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background whiteBG.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)


        
        # วางตรงบน self.main_frame ไม่ต้องใช้ frame2
        # ใช้ pack anchor="e" (east = ขวา)

        # ----- ช่องกรอก Email -----
        # ----- ช่องกรอก Email -----
        # ----- ช่องกรอก Email -----
        ctk.CTkLabel(
            self.main_frame,
            text="Email                                                             ",
            font=("Oswald", 12, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.9, rely=0.40, anchor="e")

        email_entry = ctk.CTkEntry(
            self.main_frame,
            width=220,
            placeholder_text="กรอก Email",
            bg_color="#fefefe"
        )
        email_entry.place(relx=0.9, rely=0.43, anchor="e")


        # ----- ช่องกรอก Username -----
        ctk.CTkLabel(
            self.main_frame,
            text="Username                                                      ",
            font=("Oswald", 12, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.9, rely=0.50, anchor="e")

        username_entry = ctk.CTkEntry(
            self.main_frame,
            width=220,
            placeholder_text="กรอก Username",
            bg_color="#fefefe"
        )
        username_entry.place(relx=0.9, rely=0.53, anchor="e")


        # ----- ช่องกรอก Password -----
        ctk.CTkLabel(
            self.main_frame,
            text="Password                                                       ",
            font=("Oswald", 12, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.9, rely=0.60, anchor="e")

        password_entry = ctk.CTkEntry(
            self.main_frame,
            width=220,
            show="*",
            placeholder_text="กรอก Password",
            bg_color="#fefefe"
        )
        password_entry.place(relx=0.9, rely=0.63, anchor="e")


        # ----- ปุ่มเข้าสู่ระบบ -----
        login_btn = ctk.CTkButton(
            self.main_frame,
            text="เข้าสู่ระบบ",
            fg_color="green",
            text_color="white",
            hover_color="#99ca30"
        )
        login_btn.place(relx=0.875, rely=0.80, anchor="e")

        register_btn = ctk.CTkButton(
            self.main_frame,
            text="สมัครบัญชี",
            fg_color="green",
            text_color="white",
            hover_color="#99ca30",
            command=self.register
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

    # ---------------- ฟีเจอร์ลืมรหัสผ่าน (Simple: ยืนยันด้วย email + birthday) ----------------
    def forgot_password_page(self):
        # เคลียร์หน้า
        for w in self.main_frame.winfo_children():
            w.destroy()

        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background register1.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        ctk.CTkLabel(self.main_frame,
                    text="กู้รหัสผ่าน (แบบรวดเร็ว)", 
                    font=("Oswald", 20, "bold")
                    ).place(relx=0.5, rely=0.25, anchor="center")
        
        ctk.CTkLabel(self.main_frame, 
                     text="กรอก Email ที่ลงทะเบียน", 
                     font=("Oswald", 12)
                     ).place(relx=0.4, rely=0.33, anchor="e")
        
        self.fp_email = ctk.CTkEntry(
            self.main_frame, 
            width=300, 
            placeholder_text="อีเมลของคุณ"
        )
        self.fp_email.place(relx=0.6, rely=0.33, anchor="w")

        ctk.CTkLabel(
            self.main_frame, 
            text="กรอกวันเกิด (YYYY-MM-DD)", 
            font=("Oswald", 12)
            ).place(relx=0.4, rely=0.40, anchor="e")
        
        self.fp_birth = ctk.CTkEntry(
            self.main_frame, 
            width=300, 
            placeholder_text="เช่น 1990-12-31"
        )
        self.fp_birth.place(relx=0.6, rely=0.40, anchor="w")

        # ปุ่มยืนยันตัวตน (จะพาไปหน้าตั้งรหัสผ่านใหม่)
        ctk.CTkButton(self.main_frame, text="ยืนยันตัวตน", fg_color="green",
                    command=self._verify_forget_by_email_and_birth).place(relx=0.5, rely=0.48, anchor="center")

        # ปุ่มกลับ
        ctk.CTkButton(self.main_frame, text="กลับหน้าเข้าสู่ระบบ", command=self.login_page).place(relx=0.5, rely=0.55, anchor="center")

    def _verify_forget_by_email_and_birth(self,DB):
        email = getattr(self, "fp_email", None) and self.fp_email.get().strip()
        birth = getattr(self, "fp_birth", None) and self.fp_birth.get().strip()

        if not email or not birth:
            messagebox.showerror("ไม่ครบ", "กรุณากรอก Email และ วันเกิดให้ครบ")
            return

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT id, username FROM users WHERE email=? AND birthday=?", (email, birth))
        row = c.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("ไม่พบข้อมูล", "ไม่พบข้อมูลผู้ใช้ที่ตรงกับ Email/วันเกิดที่ระบุ")
            return

        # ถ้าผ่าน -> ไปหน้าตั้งรหัสผ่านใหม่
        self._fp_user_id = row[0]
        self._fp_user_email = email
        self._fp_username = row[1] if len(row) > 1 else "User"
        self._reset_password_page()

    def _reset_password_page(self):
        # หน้าให้ตั้งรหัสผ่านใหม่ (หลังยืนยันตัวตน)
        for w in self.main_frame.winfo_children():
            w.destroy()

        ctk.CTkLabel(self.main_frame, text=f"ตั้งรหัสผ่านใหม่สำหรับ {getattr(self,'_fp_username','User')}", font=("Oswald", 16, "bold")).place(relx=0.5, rely=0.28, anchor="center")

        ctk.CTkLabel(self.main_frame, text="รหัสผ่านใหม่", font=("Oswald", 12)).place(relx=0.4, rely=0.36, anchor="e")
        self.fp_new1 = ctk.CTkEntry(self.main_frame, width=300, show="*", placeholder_text="รหัสผ่านใหม่")
        self.fp_new1.place(relx=0.6, rely=0.36, anchor="w")

        ctk.CTkLabel(self.main_frame, text="ยืนยันรหัสผ่านใหม่", font=("Oswald", 12)).place(relx=0.4, rely=0.42, anchor="e")
        self.fp_new2 = ctk.CTkEntry(self.main_frame, width=300, show="*", placeholder_text="ยืนยันรหัสผ่าน")
        self.fp_new2.place(relx=0.6, rely=0.42, anchor="w")

        ctk.CTkButton(self.main_frame, text="บันทึกรหัสผ่านใหม่", fg_color="green", command=self._do_reset_password).place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkButton(self.main_frame, text="ยกเลิก", command=self.login_page).place(relx=0.5, rely=0.57, anchor="center")

    def _do_reset_password(self,DB):
        new1 = getattr(self, "fp_new1", None) and self.fp_new1.get().strip()
        new2 = getattr(self, "fp_new2", None) and self.fp_new2.get().strip()
        if not new1 or not new2:
            messagebox.showerror("ไม่ครบ", "กรุณากรอกรหัสผ่านทั้ง 2 ช่อง")
            return
        if new1 != new2:
            messagebox.showerror("ไม่ตรงกัน", "รหัสผ่านทั้งสองช่องไม่ตรงกัน")
            return
        # ตรวจสอบความแข็งแรงรหัสผ่าน (พื้นฐาน)
        if len(new1) < 8 or not re.search("[0-9]", new1) or not re.search("[A-Za-z]", new1):
            messagebox.showerror("รหัสผ่านไม่ปลอดภัย", "รหัสผ่านต้องมีอย่างน้อย 8 ตัว และประกอบด้วยตัวอักษรและตัวเลข")
            return

        # อัปเดตใน DB
        try:
            conn = sqlite3.connect(DB)
            c = conn.cursor()
            c.execute("UPDATE users SET password=? WHERE id=?", (new1, getattr(self, "_fp_user_id", None)))
            conn.commit()
            conn.close()
        except Exception as e:
            messagebox.showerror("ผิดพลาด", f"อัปเดตรหัสผ่านไม่สำเร็จ: {e}")
            return

        messagebox.showinfo("สำเร็จ", "รหัสผ่านถูกเปลี่ยนเรียบร้อยแล้ว กรุณาเข้าสู่ระบบด้วยรหัสผ่านใหม่")
        # ล้างตัวแปรชั่วคราวแล้วกลับหน้า login
        self._fp_user_id = None
        self._fp_user_email = None
        self._fp_username = None
        self.show_login_screen()


    def register(self):
        # ล้างหน้าจอเก่าออกก่อน
        self.clear_main()

        # โหลดรูปพื้นหลัง
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background register1.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        # Label หัวข้อ
        ctk.CTkLabel(
            self.main_frame, 
            text="สมัครบัญชีผู้ใช้", 
            font=("Oswald", 20, "bold"),
            bg_color="transparent"
        ).place(relx=0.5, rely=0.2, anchor="center")

        # ช่องกรอก Email
        ctk.CTkLabel(self.main_frame, text="Email", font=("Oswald", 12, "bold"), bg_color="transparent")\
            .place(relx=0.5, rely=0.3, anchor="center")
        email_entry = ctk.CTkEntry(self.main_frame, width=250, placeholder_text="กรอก Email")
        email_entry.place(relx=0.5, rely=0.35, anchor="center")

        # ช่องกรอก Username
        ctk.CTkLabel(self.main_frame, text="Username", font=("Oswald", 12, "bold"), bg_color="transparent")\
            .place(relx=0.5, rely=0.4, anchor="center")
        username_entry = ctk.CTkEntry(self.main_frame, width=250, placeholder_text="กรอก Username")
        username_entry.place(relx=0.5, rely=0.45, anchor="center")

        # ช่องกรอก Password
        ctk.CTkLabel(self.main_frame, text="Password", font=("Oswald", 12, "bold"), bg_color="transparent")\
            .place(relx=0.5, rely=0.5, anchor="center")
        password_entry = ctk.CTkEntry(self.main_frame, width=250, show="*", placeholder_text="กรอก Password")
        password_entry.place(relx=0.5, rely=0.55, anchor="center")

        # ช่องยืนยัน Password
        ctk.CTkLabel(self.main_frame, text="Confirm Password", font=("Oswald", 12, "bold"), bg_color="transparent")\
            .place(relx=0.5, rely=0.6, anchor="center")
        confirm_entry = ctk.CTkEntry(self.main_frame, width=250, show="*", placeholder_text="ยืนยัน Password")
        confirm_entry.place(relx=0.5, rely=0.65, anchor="center")

        # ปุ่มสมัคร
        submit_btn = ctk.CTkButton(
            self.main_frame,
            text="สมัครสมาชิก",
            fg_color="green",
            text_color="white",
            command=lambda: self.save_register(email_entry.get(), username_entry.get(), password_entry.get(), confirm_entry.get())
        )
        submit_btn.place(relx=0.5, rely=0.75, anchor="center")

        # ปุ่มย้อนกลับไปหน้า Login
        back_btn = ctk.CTkButton(
            self.main_frame,
            text="กลับไปหน้าเข้าสู่ระบบ",
            fg_color="gray",
            text_color="white",
            command=self.show_login_screen
        )
        back_btn.place(relx=0.5, rely=0.82, anchor="center")

        





if __name__ == "__main__":
    root = ctk.CTk()
    #init_db()
    app = PharmaCareApp(root)
    root.mainloop()