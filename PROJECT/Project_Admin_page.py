import sqlite3
import customtkinter as ctk
from tkinter import messagebox
from tkinter import filedialog  # ← เพิ่ม
import hashlib
import os
import datetime
import qrcode
from io import BytesIO
from PIL import Image, ImageTk
import re
DB = "pharmacy.db"
CATEGORY_MAP = {
    "เวชสำอาง": ["ครีมกันแดด", "โฟมล้างหน้า", "เซรั่ม", "มอยส์เจอร์ไรเซอร์"],
    "สินค้าเพื่อสุขภาพ": ["วิตามิน", "อาหารเสริม", "เครื่องวัดความดัน", "สมุนไพร"],
    "ยา": ["ยาแก้ปวด", "ยาลดไข้", "ยาแก้แพ้", "ยาฆ่าเชื้อ"],
}
ALL_CATEGORIES = ["ทั้งหมด"] + list(CATEGORY_MAP.keys())

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
    # ← ตารางสินค้าเริ่มต้น
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            price REAL NOT NULL DEFAULT 0,
            description TEXT,
            image_path TEXT
        )
    ''')
    conn.commit()

    # --- เพิ่มคอลัมน์ category / subcategory หากยังไม่มี (migration อัตโนมัติ) ---
    def add_col_if_missing(col, coltype):
        try:
            c.execute(f"ALTER TABLE products ADD COLUMN {col} {coltype}")
            conn.commit()
        except Exception:
            pass  # มีอยู่แล้ว

    add_col_if_missing("category", "TEXT")
    add_col_if_missing("subcategory", "TEXT")

    conn.close()

init_db()
class Admin_page:
    def __init__(self, root):
        self.root = root
        self.root.title("PharmaCare Admin")
        self.root.geometry("500x400")
        self.main_frame = ctk.CTkFrame(root)
        self.main_frame.pack(fill="both", expand=True)

        self.current_username = None
        self.current_email = None
        self.is_admin = False   # ← เพิ่มสถานะแอดมิน

        self.main_page()

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

        # ปุ่มโปรไฟล์

        # ปุ่ม Admin (เฉพาะแอดมิน)
        if getattr(self, "is_admin", False):
            AdminButton = ctk.CTkButton(
                self.main_frame,
                text="🛠 Admin",
                width=80, height=36,
                fg_color="#444", hover_color="#222",
                command=self.open_admin
            )
            AdminButton.place(relx=0.8, rely=0.15, anchor="e")

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

        # state กรอง
        self.selected_category = "ทั้งหมด"
        self.selected_subcategory = None

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

            self.selected_category = category
            self.selected_subcategory = None

            # ดึงประเภทสินค้าย่อยที่เกี่ยวข้อง
            if category in CATEGORY_MAP:
                subs = CATEGORY_MAP[category]
            else:
                subs = []

            ctk.CTkLabel(self.sub_panel, text=f" {category}", font=("Arial", 14, "bold")).pack(pady=8)
            if subs:
                ctk.CTkButton(self.sub_panel, text="ทั้งหมด", width=150,
                              command=lambda: (setattr(self, "selected_subcategory", None), self.render_products())
                              ).pack(pady=5)
            for sub in subs:
                ctk.CTkButton(self.sub_panel, text=sub, width=150,
                              command=lambda s=sub: (setattr(self, "selected_subcategory", s), self.render_products())
                              ).pack(pady=5)

            # รีเฟรชสินค้าเมื่อเปลี่ยนหมวด
            self.render_products()

        # ปุ่มหมวดหมู่หลัก
        for cat in ALL_CATEGORIES:
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

        # แสดงสินค้าครั้งแรก (ทั้งหมด)
        show_subcategories("ทั้งหมด")

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

        # ---------- ดึง username, email ----------
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

# ========================== ADMIN PAGE (CRUD PRODUCTS) ==========================
    def open_admin(self):
        # ล้างหน้าปัจจุบัน
        for w in self.main_frame.winfo_children():
            w.destroy()

        # พื้นหลัง (ใช้ภาพเดียวกับ mainpage เปลี่ยนได้)
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background mainpage.png")
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
        back_btn.place(relx=0.9, rely=0.15, anchor="e")

        # กรอบใหญ่
        container = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20)
        container.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.85, relheight=0.72)

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

        ctk.CTkLabel(right, text="รายละเอียด").grid(row=3, column=0, sticky="ne", padx=8, pady=6)
        self.p_desc = ctk.CTkTextbox(right, width=320, height=120)
        self.p_desc.grid(row=3, column=1, columnspan=2, sticky="w", padx=8, pady=6)

        # รูปภาพ + ปุ่มเลือกไฟล์ (ตำแหน่งเดิม)
        self.preview = ctk.CTkLabel(right, text="(ยังไม่มีรูป)", width=160, height=160, fg_color="#f1f1f1", corner_radius=12)
        self.preview.grid(row=1, column=3, rowspan=3, padx=(16,8), pady=6)

        # --- เพิ่มหมวด/ประเภทย่อยในแถวเดียวกับปุ่มเลือกรูป (ตำแหน่งคอลัมน์ว่าง) ---
        ctk.CTkLabel(right, text="หมวดหมู่").grid(row=4, column=0, sticky="e", padx=8, pady=6)
        self.p_cat = ctk.CTkOptionMenu(right, values=list(CATEGORY_MAP.keys()), width=160, command=self._on_admin_cat_change)
        self.p_cat.grid(row=4, column=1, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(right, text="ประเภทย่อย").grid(row=4, column=2, sticky="e", padx=8, pady=6)
        self.p_subcat = ctk.CTkOptionMenu(right, values=[""], width=160)
        self.p_subcat.grid(row=4, column=3, sticky="w", padx=8, pady=6)

        # ปุ่มเลือกภาพ (ยังอยู่ row เดิม แต่ขยับลงหนึ่งแถวเพื่อไม่ชน? -> คง row=5 ตามโครง)
        choose_img = ctk.CTkButton(right, text="เลือกรูปภาพ…", command=self._admin_pick_image)
        choose_img.grid(row=5, column=3, sticky="n", padx=8, pady=(0,12))

        # ปุ่มคำสั่ง (ตำแหน่งเดิม)
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.grid(row=6, column=0, columnspan=4, sticky="we", padx=8, pady=(10,0))

        ctk.CTkButton(btn_row, text="เพิ่มใหม่", fg_color="#2e7d32", command=self._admin_create).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="บันทึก", fg_color="#1976d2", command=self._admin_save).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="ลบ", fg_color="#b00020", command=self._admin_delete).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="ล้างฟอร์ม", command=self._admin_clear_form).pack(side="left", padx=6)

        # ตั้งค่า default ของเมนูหมวด/ประเภทย่อย
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

    def _admin_pick_image(self):
        path = filedialog.askopenfilename(
            title="เลือกรูปสินค้า",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        if not path:
            return
        self.product_image_path = path
        try:
            im = Image.open(path)
            im.thumbnail((180, 180))
            self.admin_img_photo = ImageTk.PhotoImage(im)
            self.preview.configure(image=self.admin_img_photo, text="")
        except Exception as e:
            messagebox.showerror("รูปภาพ", f"แสดงตัวอย่างรูปไม่ได้:\n{e}")

    def _admin_clear_form(self):
        self.selected_product_id = None
        self.p_name.delete(0, "end")
        self.p_price.delete(0, "end")
        self.p_desc.delete("1.0", "end")
        self.product_image_path = None
        self.preview.configure(image=None, text="(ยังไม่มีรูป)")
        self.admin_img_photo = None
        # reset หมวด
        first_cat = list(CATEGORY_MAP.keys())[0]
        self.p_cat.set(first_cat)
        self._on_admin_cat_change(first_cat)

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
            SELECT id, name, price, description, image_path, category, subcategory
            FROM products WHERE id=?
        """, (product_id,))
        row = c.fetchone()
        conn.close()
        if not row:
            messagebox.showerror("โหลดสินค้า", "ไม่พบข้อมูลสินค้า")
            return

        self.selected_product_id = row[0]
        name = row[1] or ""
        price = row[2] or 0
        desc = row[3] or ""
        img_path = row[4]
        cat = row[5] or list(CATEGORY_MAP.keys())[0]
        sub = row[6] or (CATEGORY_MAP.get(cat, [""])[0] if CATEGORY_MAP.get(cat) else "")

        # ใส่ลงฟอร์ม
        self.p_name.delete(0, "end"); self.p_name.insert(0, name)
        self.p_price.delete(0, "end"); self.p_price.insert(0, f"{price:g}")
        self.p_desc.delete("1.0", "end"); self.p_desc.insert("1.0", desc)
        self.product_image_path = img_path

        # พรีวิวรูป
        self.preview.configure(image=None, text="(ยังไม่มีรูป)")
        self.admin_img_photo = None
        if img_path and os.path.exists(img_path):
            try:
                im = Image.open(img_path); im.thumbnail((180, 180))
                self.admin_img_photo = ImageTk.PhotoImage(im)
                self.preview.configure(image=self.admin_img_photo, text="")
            except Exception:
                pass

        # ตั้งค่าหมวด/ประเภทย่อย
        self.p_cat.set(cat)
        self._on_admin_cat_change(cat)
        if sub:
            self.p_subcat.set(sub)

    def _admin_create(self):
        # สร้างใหม่ = เคลียร์ฟอร์มแล้วเริ่มกรอก
        self._admin_clear_form()

    def _admin_save(self):
        name = self.p_name.get().strip()
        price_txt = self.p_price.get().strip() or "0"
        desc = self.p_desc.get("1.0", "end").strip()
        cat = self.p_cat.get().strip()
        sub = self.p_subcat.get().strip()

        try:
            price = float(price_txt)
        except ValueError:
            messagebox.showerror("บันทึก", "ราคาไม่ถูกต้อง")
            return
        if not name:
            messagebox.showerror("บันทึก", "กรุณากรอกชื่อสินค้า")
            return

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        if self.selected_product_id is None:
            # INSERT
            c.execute(
                "INSERT INTO products (name, price, description, image_path, category, subcategory) VALUES (?, ?, ?, ?, ?, ?)",
                (name, price, desc, self.product_image_path, cat, sub)
            )
            conn.commit()
            messagebox.showinfo("บันทึก", "เพิ่มสินค้าเรียบร้อย")
        else:
            # UPDATE
            c.execute(
                "UPDATE products SET name=?, price=?, description=?, image_path=?, category=?, subcategory=? WHERE id=?",
                (name, price, desc, self.product_image_path, cat, sub, self.selected_product_id)
            )
            conn.commit()
            messagebox.showinfo("บันทึก", "อัปเดตสินค้าเรียบร้อย")
        conn.close()

        # กลับไปหน้า Main เพื่อเห็นสินค้าที่เพิ่มทันที (ตำแหน่ง UI เดิม)
        self._admin_clear_form()
        self.main_page(getattr(self, "current_username", "Guest"))

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
        self._admin_clear_form()

    # ----------- แสดงสินค้าในหน้า Main ตามตัวกรอง -----------
    def render_products(self):
        # เคลียร์เดิม
        for w in self.products_container.winfo_children():
            w.destroy()

        # สร้าง query + params
        where = []
        params = []
        if getattr(self, "selected_category", "ทั้งหมด") != "ทั้งหมด":
            where.append("category = ?")
            params.append(self.selected_category)
            if getattr(self, "selected_subcategory", None):
                where.append("subcategory = ?")
                params.append(self.selected_subcategory)

        sql = "SELECT id, name, price, description, image_path FROM products"
        if where:
            sql += " WHERE " + " ".join([" AND ".join(where)])
        sql += " ORDER BY id DESC"

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()

        if not rows:
            ctk.CTkLabel(self.products_container, text="(ยังไม่มีสินค้าในหมวดนี้)").pack(pady=12)
            return

        # ---- helper ตัดข้อความยาวให้พอดีการ์ด ----
        def _shorten(text, n=140):
            text = (text or "").strip()
            return text if len(text) <= n else text[:n-1] + "…"

        # แสดงเป็น card
        for pid, name, price, desc, img_path in rows:
            card = ctk.CTkFrame(self.products_container, corner_radius=12)
            card.pack(fill="x", pady=8, padx=8)

            # รูป
            img_label = ctk.CTkLabel(card, text="")
            img_label.pack(side="left", padx=10, pady=10)
            try:
                if img_path and os.path.exists(img_path):
                    im = Image.open(img_path)
                    im.thumbnail((80, 80))
                    photo = ImageTk.PhotoImage(im)
                    img_label.configure(image=photo)
                    img_label.image = photo
                else:
                    img_label.configure(text="(no image)")
            except Exception:
                img_label.configure(text="(no image)")

            # ข้อมูล
            texts = ctk.CTkFrame(card, fg_color="transparent")
            texts.pack(side="left", fill="x", expand=True, padx=8, pady=10)

            ctk.CTkLabel(texts, text=f"{name}", font=("Arial", 14, "bold")).pack(anchor="w")
            ctk.CTkLabel(texts, text=f"{price:.2f} บาท").pack(anchor="w")

            # 🟢 เพิ่มบรรทัดนี้: แสดงรายละเอียด (ตัดยาวและตัดบรรทัดอัตโนมัติ)
            ctk.CTkLabel(
                texts,
                text=_shorten(desc, 160),   # ปรับความยาวได้ตามต้องการ
                justify="left",
                anchor="w",
                wraplength=420              # ทำให้ตัดบรรทัดในกรอบการ์ด
            ).pack(anchor="w", pady=(2, 6))

            # ปุ่มเพิ่มลงตะกร้า
            ctk.CTkButton(card, text="เพิ่มลงตะกร้า", width=120).pack(side="right", padx=10)



# ----------------- Run -----------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = Admin_page(root)
    root.mainloop()
# ----------------- Run -----------------
