import sqlite3
import customtkinter as ctk
from tkinter import messagebox
import hashlib
import os
import datetime
import qrcode
from io import BytesIO
from PIL import Image, ImageTk
import re

# ----------------- Database -----------------
DB = "pharmacy.db"

def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            username TEXT UNIQUE,
            password TEXT,
            birthday TEXT
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ----------------- Main App -----------------
class PharmaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PharmaCare Login")
        self.root.geometry("500x400")
        self.main_frame = ctk.CTkFrame(root)
        self.main_frame.pack(fill="both", expand=True)
        self.current_username = None
        self.current_email = None
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
            messagebox.showerror("Error", "กรุณากรอกรหัสผ่านใหม่")
        else:
            messagebox.showinfo("Success", f"เข้าสู่ระบบสำเร็จ ยินดีต้อนรับ {username}")
            self.current_username = username
            self.current_email = email
            
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

        ctk.CTkLabel(self.main_frame, text="สมัครสมาชิก", font=("Oswald", 20, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.25, anchor="center")

        # Email
        ctk.CTkLabel(self.main_frame, text="Email", font=("Oswald", 12, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.3, anchor="center")
        self.reg_email = ctk.CTkEntry(self.main_frame, width=250, placeholder_text="กรอก Email")
        self.reg_email.place(relx=0.5, rely=0.35, anchor="center")

        # Username
        ctk.CTkLabel(self.main_frame, text="Username", font=("Oswald", 12, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.4, anchor="center")
        self.reg_user = ctk.CTkEntry(self.main_frame, width=250, placeholder_text="กรอก Username")
        self.reg_user.place(relx=0.5, rely=0.45, anchor="center")

        # Password
        ctk.CTkLabel(self.main_frame, text="Password", font=("Oswald", 12, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.5, anchor="center")
        self.reg_pass = ctk.CTkEntry(self.main_frame, width=250, show="*", placeholder_text="กรอก Password")
        self.reg_pass.place(relx=0.5, rely=0.55, anchor="center")

        # Confirm Password
        ctk.CTkLabel(self.main_frame, text="Confirm Password", font=("Oswald", 12, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.6, anchor="center")
        self.reg_pass2 = ctk.CTkEntry(self.main_frame, width=250, show="*", placeholder_text="ยืนยัน Password")
        self.reg_pass2.place(relx=0.5, rely=0.65, anchor="center")

        # Birthday
        ctk.CTkLabel(self.main_frame, text="Birthday", font=("Oswald", 12, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.7, anchor="center")
        self.reg_birth = ctk.CTkEntry(self.main_frame, width=250, placeholder_text="(YYYY-MM-DD)")
        self.reg_birth.place(relx=0.5, rely=0.75, anchor="center")

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
        birthday = self.reg_birth.get().strip()

        # ตรวจสอบช่องว่าง
        if not email or not username or not password or not password2 or not birthday:
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

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (email, username, password, birthday) VALUES (?, ?, ?, ?)",
                      (email, username, password, birthday))
            conn.commit()
            messagebox.showinfo("Success", f"สมัครสมาชิกสำเร็จ ยินดีต้อนรับ {username}")
            self.current_username = username
            self.current_email = email
            self.main_page(username)
        except sqlite3.IntegrityError as e:
            if "email" in str(e):
                messagebox.showerror("Error", "Email ถูกใช้งานแล้ว")
            elif "username" in str(e):
                messagebox.showerror("Error", "Username ถูกใช้งานแล้ว")
        finally:
            conn.close()

#----------------------------------------------------------------------------------------------------------------------------------------------------------#
    































#----------------------------------------------------------------------------------------------------------------------------------------------------------#

    def main_page(self, username):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.main_frame, text=f"ยินดีต้อนรับ {username}", font=("Oswald", 20, "bold")).pack(pady=20)

         # ---------- Background ----------
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background mainpage.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        #self.current_user = username


        # ปุ่มโปรไฟล์
        ProfileButton = ctk.CTkButton(
            self.main_frame,
            text="👤",
            width=50, height=50,
            fg_color="green", 
            hover_color="darkgreen", 
            text_color="white",
            command=self.Profile_Page   # <--- ไม่ต้องใส่ args
        )
        ProfileButton.place(relx=0.85, rely=0.15, anchor="e")

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
        BusketButton.place(relx=0.9, rely=0.15, anchor="e")

        # ---------- Welcome Text ----------
        welcome = ctk.CTkLabel(
            self.main_frame,
            text=f"ยินดีต้อนรับ {username}",
            font=("Arial", 20, "bold"),
            text_color="black",
            fg_color="transparent"
        )
        welcome.place(relx=0.25, rely=0.15, anchor="e")
        
#----------------------------------------------------------------------------------------------------------------------------------------------------------#

        content_frame = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20)
        content_frame.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.77, relheight=0.7)

        # ซ้าย: หมวดหมู่
        left_panel = ctk.CTkFrame(content_frame, width=180, corner_radius=10)
        left_panel.pack(side="left", fill="y", padx=10, pady=10)

        ctk.CTkLabel(left_panel, text="หมวดหมู่", font=("Arial", 16, "bold")).pack(pady=10)

        # 🟩 เพิ่ม Panel สำหรับแสดงประเภท (อยู่ถัดจากหมวดหมู่)
        self.sub_panel = ctk.CTkFrame(content_frame, width=180, corner_radius=10)
        self.sub_panel.pack(side="left", fill="y", padx=10, pady=10)

        def show_subcategories(category):
            # เคลียร์ของเก่าทั้งหมดใน sub_panel ก่อน
            for w in self.sub_panel.winfo_children():
                w.destroy()

            # ดึงประเภทสินค้าย่อยที่เกี่ยวข้อง
            if category == "เวชสำอาง":
                subs = ["ครีมกันแดด", "โฟมล้างหน้า", "เซรั่ม", "มอยส์เจอร์ไรเซอร์"]
            elif category == "สินค้าเพื่อสุขภาพ":
                subs = ["วิตามิน", "อาหารเสริม", "เครื่องวัดความดัน", "สมุนไพร"]
            elif category == "ยา":
                subs = ["ยาแก้ปวด", "ยาลดไข้", "ยาแก้แพ้", "ยาฆ่าเชื้อ"]
            else:
                subs = ["สินค้าทั้งหมด"]

            ctk.CTkLabel(self.sub_panel, text=f" {category}", font=("Arial", 14, "bold")).pack(pady=8)
            for sub in subs:
                ctk.CTkButton(self.sub_panel, text=sub, width=150).pack(pady=5)

        # ปุ่มหมวดหมู่หลัก
        for cat in ["ทั้งหมด", "เวชสำอาง", "สินค้าเพื่อสุขภาพ", "ยา"]:
            ctk.CTkButton(left_panel, text=cat, width=150,
                          command=lambda c=cat: show_subcategories(c)).pack(pady=5)

        # กลาง: สินค้า
        center_panel = ctk.CTkFrame(content_frame, corner_radius=10)
        center_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self.products_container = ctk.CTkScrollableFrame(center_panel, label_text="สินค้า")
        self.products_container.pack(fill="both", expand=True, padx=10, pady=10)

        # ขวา: ตะกร้าสรุป
        right_panel = ctk.CTkFrame(content_frame, width=200, corner_radius=10)
        right_panel.pack(side="right", fill="y", padx=10, pady=10)

        ชำระ=ctk.CTkButton(right_panel,text = "ชำระสินค้า",width=150,
                      command=self.cart_page)
        ชำระ.place(relx=0.9, rely=0.5, anchor="e")
        
        ctk.CTkLabel(right_panel, text="ตะกร้าสรุป", font=("Arial", 16, "bold")).pack(pady=10)

        self.cart_summary = ctk.CTkTextbox(right_panel, width=180, height=180)
        self.cart_summary.pack(pady=10)
        self.cart_summary.insert("end", "ตะกร้าว่าง")

 #----------------------------------------------------------------------------------------------------------------------------------------------------------#
    def cart_page(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background mainpage.png")
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
            width=50,
            height=50,
            fg_color="green",
            hover_color="darkgreen",
            text_color="white",
            command=lambda: self.main_page(username)
        )
        BackButton.place(relx=0.9, rely=0.15, anchor="e")

        ctk.CTkLabel(content_frame, text="ตะกร้าสินค้า", font=("Arial", 20, "bold")).pack(pady=10)

            # กล่องตะกร้า
        self.cart_box = ctk.CTkFrame(content_frame, fg_color="#bdfcc9", corner_radius=25)
        self.cart_box.pack(fill="both", expand=True, padx=40, pady=10)
        ctk.CTkLabel(self.cart_box, text="ยังไม่มีสินค้าในตะกร้า", font=("Arial", 16)).pack(pady=20)

            # ปุ่มชำระเงิน
        pay_button = ctk.CTkButton(content_frame, text="ชำระสินค้า", fg_color="#9bffb2", text_color="black", width=120)
        pay_button.pack(pady=15, anchor="se", padx=60)

#----------------------------------------------------------------------------------------------------------------------------------------------------------#

    def Profile_Page(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # ---------- พื้นหลัง ----------
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background profile2.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        # ---------- ดึง username, email จาก current_user ----------
        
        username = getattr(self, "current_username", "Guest")
        email = getattr(self, "current_email", "ไม่พบข้อมูล")


        # ---------- ปุ่มย้อนกลับ ----------
        BackButton = ctk.CTkButton(
            self.main_frame,
            text="🔙",
            width=50,
            height=50,
            fg_color="green",
            hover_color="darkgreen",
            text_color="white",
            command=lambda: self.main_page(username)
        )
        BackButton.place(relx=0.9, rely=0.15, anchor="e")

        # ---------- แสดงชื่อผู้ใช้ + อีเมล ----------
        ctk.CTkLabel(
            self.main_frame,
            text=f"ชื่อผู้ใช้ : {username}",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.5, rely=0.3, anchor="center")

        ctk.CTkLabel(
            self.main_frame,
            text=f"Email : {email}",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.5, rely=0.4, anchor="center")

        # ---------- ส่วนที่อยู่ ----------
        ctk.CTkLabel(
            self.main_frame,
            text="ที่อยู่ :",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.5, rely=0.5, anchor="center")

        self.address_box = ctk.CTkTextbox(
            self.main_frame,
            width=380,
            height=100,
            border_width=2,
            border_color="gray30",
            fg_color="#F7F7F7",
            text_color="black"
        )
        self.address_box.place(relx=0.65, rely=0.55, anchor="center")
        self.address_box.insert("1.0", "กรอกที่อยู่ของคุณที่นี่...")
        self.address_box.configure(state="disabled")

        # ปุ่มแก้ไขที่อยู่
        self.btn_edit_addr = ctk.CTkButton(
            self.main_frame,
            text="แก้ไข",
            font=("Oswald", 14, "bold"),
            width=90, height=32,
            fg_color="#4CAF50", hover_color="#2E7D32",
            text_color="white",
            command=self._enter_edit_address_mode
        )
        self.btn_edit_addr.place(relx=0.74, rely=0.64, anchor="center")

        # ปุ่มบันทึกที่อยู่
        self.btn_save_addr = ctk.CTkButton(
            self.main_frame,
            text="บันทึก",
            font=("Oswald", 14, "bold"),
            width=90, height=32,
            fg_color="#007AFF", hover_color="#005BBB",
            text_color="white",
            command=self._save_address
        )
        self.btn_save_addr.place(relx=0.68, rely=0.64, anchor="center")
        self.btn_save_addr.configure(state="disabled")

        # ---------- ส่วนสะสมแต้ม / ติดต่อ / ประวัติ ----------
        ctk.CTkLabel(
            self.main_frame,
            text=" สะสมแต้ม ",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.32, rely=0.65, anchor="center")

        ctk.CTkButton(
            self.main_frame,
            text="ประวัติการสั่งซื้อ click here",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.32, rely=0.75, anchor="center")

        ctk.CTkButton(
            self.main_frame,
            text="ติดต่อสอบถามเพิ่มเติม click here",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.65, rely=0.75, anchor="center")

        # ค่าเริ่มต้นที่อยู่
        self._address_backup = "กรอกที่อยู่ของคุณที่นี่..."


    # ---------- โหมดแก้ไข ----------
    def _enter_edit_address_mode(self):
        self.address_box.configure(state="normal")
        # ถ้าเป็นข้อความ placeholder ให้ล้างออก
        current_text = self.address_box.get("1.0", "end").strip()
        if current_text == self._address_backup:
            self.address_box.delete("1.0", "end")

        # เปลี่ยนโทนสีให้เห็นว่าแก้ไขได้
        self.address_box.configure(
            fg_color="#E0F7FA",   # ฟ้าอ่อน
            border_color="#0288D1"
        )

        # ปุ่ม
        self.btn_edit_addr.configure(state="disabled")
        self.btn_save_addr.configure(state="normal")

    # ---------- โหมดบันทึก ----------
    def _save_address(self):
        address = self.address_box.get("1.0", "end").strip()
        if not address:
            messagebox.showwarning("แจ้งเตือน", "กรุณากรอกที่อยู่ก่อนบันทึก")
            return

        self._address_backup = address
        self.address_box.configure(state="disabled", fg_color="#F7F7F7", border_color="gray30")
        self.btn_edit_addr.configure(state="normal")
        self.btn_save_addr.configure(state="normal")

        messagebox.showinfo("สำเร็จ", f"ที่อยู่ถูกบันทึกแล้ว:\n{address}")

    


# ----------------- Run -----------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = PharmaApp(root)
    root.mainloop()
# ----------------- Run -----------------
