import sqlite3
import customtkinter as ctk
from tkinter import messagebox, filedialog  # ← เพิ่ม filedialog
from PIL import Image, ImageTk, ImageOps   # ← เพิ่ม ImageOps
import os                                   # ← เพิ่ม os
# import re  # ไม่ได้ใช้ในไฟล์นี้ สามารถลบออกได้

DB = "pharmacy.db"

# --- ให้ไฟล์นี้รันเดี่ยวๆ ได้: สร้างตาราง users และคอลัมน์ที่ต้องใช้ ---
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE,
            username TEXT,
            password TEXT,
            birthday TEXT
        )
    """)
    # เพิ่มคอลัมน์ address / profile_image ถ้ายังไม่มี
    try:
        c.execute("ALTER TABLE users ADD COLUMN address TEXT")
    except Exception:
        pass
    try:
        c.execute("ALTER TABLE users ADD COLUMN profile_image TEXT")
    except Exception:
        pass
    conn.commit()
    # ถ้ายังไม่มีผู้ใช้ตัวอย่าง ให้ใส่ 1 แถวเพื่อทดสอบ
    c.execute("SELECT 1 FROM users WHERE email=?", ("guest@example.com",))
    if not c.fetchone():
        c.execute("INSERT INTO users (email, username, password, birthday, address, profile_image) VALUES (?, ?, ?, ?, ?, ?)",
                  ("guest@example.com", "Guest", "", "", "", ""))
        conn.commit()
    conn.close()

init_db()


class ProfilePage:
    def __init__(self, root, email="guest@example.com", username="Guest"):
        self.root = root
        self.root.title("PharmaCare - Profile Page")
        self.root.geometry("900x600")
        self.main_frame = ctk.CTkFrame(root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)

        # สำหรับไฟล์เดี่ยว: กำหนดผู้ใช้ปัจจุบันตรงนี้
        self.current_email = email
        self.current_username = username

        self.Profile_Page()

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
        c.execute("SELECT address, profile_image FROM users WHERE email=?", (email,))
        row = c.fetchone()
        conn.close()

        placeholder = "กรอกที่อยู่ของคุณที่นี่..."
        current_address = (row[0] or "").strip() if row else ""
        if not current_address:
            current_address = placeholder
        current_image = row[1] if row and row[1] and os.path.exists(row[1]) else None

        # ---------- ปุ่มย้อนกลับ ----------
        ctk.CTkButton(
            self.main_frame,
            text="🔙", width=50, height=50,
            fg_color="green", hover_color="darkgreen", text_color="white",
            # ในไฟล์เดี่ยวๆ ยังไม่มี main_page ให้ย้อนเป็นรีเฟรชหน้านี้แทน หรือปิดหน้าต่าง
            command=self.Profile_Page
            # หรือใช้ command=self.root.destroy
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
        ctk.CTkLabel(self.main_frame, text=f"ชื่อผู้ใช้ : {username}", font=("Oswald", 18, "bold"),bg_color="white").place(relx=0.5, rely=0.45, anchor="w")
        ctk.CTkLabel(self.main_frame, text=f"Email : {email}", font=("Oswald", 18, "bold"),bg_color="white").place(relx=0.5, rely=0.5, anchor="w")

        # ---------- ที่อยู่ + ปุ่ม แก้ไข/บันทึก ----------
        ctk.CTkLabel(self.main_frame, text="ที่อยู่ :", font=("Oswald", 18, "bold"),bg_color="white").place(relx=0.5, rely=0.55, anchor="w")

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


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = ProfilePage(root)  # ใช้ guest@example.com ที่ init_db() เตรียมไว้
    root.mainloop()
