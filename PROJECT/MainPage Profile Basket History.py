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

CATEGORY_MAP = {
    "เวชสำอาง": ["ครีมกันแดด", "โฟมล้างหน้า", "เซรั่ม", "มอยส์เจอร์ไรเซอร์"],
    "สินค้าเพื่อสุขภาพ": ["วิตามิน", "อาหารเสริม", "เครื่องวัดความดัน", "สมุนไพร"],
    "ยา": ["ยาแก้ปวด", "ยาลดไข้", "ยาแก้แพ้", "ยาฆ่าเชื้อ"],
}
ALL_CATEGORIES = ["ทั้งหมด"] + list(CATEGORY_MAP.keys())


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

        self.main_page()

    def main_page(self, ):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.main_frame, text=f"ยินดีต้อนรับ ", font=("Oswald", 20, "bold")).pack(pady=20)

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
            text=f"ยินดีต้อนรับ ",
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
            command=self.Qrcode  # ← ไม่ต้องส่งพารามิเตอร์
        )
        pay_button.pack(side="right", padx=(8, 0))

        status_bar = ctk.CTkLabel(content_frame, text=f"(DEBUG) items in cart: {sum(i['qty'] for i in self.cart.values())}",
                                  text_color="#666666")
        status_bar.pack(pady=(0, 4))

        self._render_cart_items()

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




# ----------------- Run -----------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = PharmaApp(root)
    root.mainloop()
# ----------------- Run -----------------
