import sqlite3
import customtkinter as ctk
from tkinter import messagebox, filedialog
from PIL import Image, ImageTk
import os, datetime

DB = "pharmacy.db"

# ----------------- DB bootstrap -----------------
def init_db():
    conn = sqlite3.connect(DB)
    c = conn.cursor()

    # เดโมไม่พึ่ง users/products จริง สร้างเฉพาะตารางออเดอร์/จ่าย/ไอเท็ม
    c.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            shipping_method TEXT NOT NULL,
            shipping_address TEXT NOT NULL,
            total_amount REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',             -- pending / paid / cancelled
            shipping_status TEXT NOT NULL DEFAULT 'waiting',    -- waiting / packing / shipped / delivered
            created_at TEXT NOT NULL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            price REAL NOT NULL,
            qty INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            method TEXT NOT NULL,       -- 'qr'
            slip_path TEXT,             -- ไฟล์สลิป
            status TEXT NOT NULL DEFAULT 'pending', -- pending / approved / rejected
            created_at TEXT NOT NULL,
            FOREIGN KEY(order_id) REFERENCES orders(id)
        )
    """)

    conn.commit()
    conn.close()

def ensure_media():
    os.makedirs("media/slips", exist_ok=True)

# ----------------- App -----------------
class Qrcode_page:
    def __init__(self, root):
        self.root = root
        self.root.title("PharmaCare - Demo Flow")
        self.root.geometry("1000x680")
        self.main_frame = ctk.CTkFrame(root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)

        init_db()
        ensure_media()

        # ตะกร้าทดลอง (สมมติผู้ใช้เลือกสินค้าบางอย่างไว้แล้ว)
        self.demo_cart = [
            {"product_id": 101, "name": "วิตามินซี 500mg", "price": 199.0, "qty": 2},
            {"product_id": 202, "name": "เจลล้างมือ 70%", "price": 59.0, "qty": 1},
        ]
        self.current_email = "demo_user@pharma.local"  # เดโมกำหนดให้ตายตัว

        self.main_menu()

    # ----------------- ภาพพื้นหลัง helper -----------------
    def _bg(self, parent):
        try:
            im = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background profile2.png")
            ctkimg = ctk.CTkImage(light_image=im, dark_image=im, size=(1920, 1000))
            bg = ctk.CTkLabel(parent, image=ctkimg, text="")
            bg.image = ctkimg
            bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception:
            pass

    # ----------------- เมนูหลัก -----------------
    def main_menu(self):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg(self.main_frame)

        box = ctk.CTkFrame(self.main_frame, corner_radius=16)
        box.place(relx=0.5, rely=0.55, anchor="center", relwidth=0.8, relheight=0.7)

        ctk.CTkLabel(box, text="Demo: ออเดอร์ → อัปสลิป → อนุมัติ/ปฏิเสธ → จัดส่ง", font=("Oswald", 24, "bold")).pack(pady=18)

        # แสดงตะกร้าทดลอง
        sc = ctk.CTkScrollableFrame(box, width=600, height=240)
        sc.pack(pady=(0, 8), padx=20)
        total = 0.0
        for item in self.demo_cart:
            sub = item["price"] * item["qty"]
            total += sub
            row = ctk.CTkFrame(sc, fg_color="white", corner_radius=10)
            row.pack(fill="x", padx=6, pady=6)
            ctk.CTkLabel(row, text=item["name"]).grid(row=0, column=0, sticky="w", padx=10, pady=8)
            ctk.CTkLabel(row, text=f"{item['price']:,.2f} x {item['qty']}").grid(row=0, column=1, padx=10)
            ctk.CTkLabel(row, text=f"{sub:,.2f} บาท").grid(row=0, column=2, padx=10)
            row.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(box, text=f"รวมทั้งสิ้น: {total:,.2f} บาท", font=("Oswald", 18, "bold")).pack(pady=6)

        btns = ctk.CTkFrame(box, fg_color="transparent")
        btns.pack(pady=8)
        ctk.CTkButton(btns, text="➡ ไปหน้า Checkout", fg_color="green", text_color="white",
                      command=self.checkout_page).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="🧰 Admin: จัดการออเดอร์", command=self.open_admin_orders).pack(side="left", padx=6)

    # ----------------- Checkout: วิธีส่ง + ที่อยู่ -----------------
    def checkout_page(self):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg(self.main_frame)

        box = ctk.CTkFrame(self.main_frame, corner_radius=16)
        box.place(relx=0.5, rely=0.55, anchor="center", relwidth=0.82, relheight=0.72)

        ctk.CTkButton(self.main_frame, text="🔙", width=48, height=48, fg_color="green",
                      hover_color="darkgreen", text_color="white",
                      command=self.main_menu).place(relx=0.95, rely=0.15, anchor="e")

        ctk.CTkLabel(box, text="Checkout", font=("Oswald", 24, "bold")).pack(pady=(16, 8))

        wrap = ctk.CTkFrame(box, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=16, pady=8)

        left = ctk.CTkFrame(wrap, corner_radius=10)
        left.pack(side="left", fill="y", padx=10, pady=10)
        ctk.CTkLabel(left, text="ข้อมูลจัดส่ง", font=("Oswald", 18, "bold")).pack(pady=(10, 8))

        self.ship_method_var = ctk.StringVar(value="ไปรษณีย์ลงทะเบียน")
        ctk.CTkLabel(left, text="วิธีจัดส่ง").pack(anchor="w", padx=10)
        ctk.CTkOptionMenu(left, values=["ไปรษณีย์ลงทะเบียน", "EMS", "ขนส่งเอกชน"], variable=self.ship_method_var,
                          width=240).pack(padx=10, pady=6)

        ctk.CTkLabel(left, text="ที่อยู่จัดส่ง").pack(anchor="w", padx=10, pady=(6, 0))
        self.ship_address_box = ctk.CTkTextbox(left, width=280, height=120)
        self.ship_address_box.pack(padx=10, pady=6)
        self.ship_address_box.insert("1.0", "บ้านเลขที่ 123/45 ถ.ตัวอย่าง ต.ทดสอบ อ.ตัวอย่าง จ.กรุงเทพฯ 10110")

        right = ctk.CTkFrame(wrap, corner_radius=10)
        right.pack(side="left", fill="both", expand=True, padx=10, pady=10)
        ctk.CTkLabel(right, text="รายการสินค้า", font=("Oswald", 18, "bold")).pack(pady=(10, 8))

        sc = ctk.CTkScrollableFrame(right, width=520, height=260)
        sc.pack(fill="both", expand=True, padx=10, pady=6)

        total = 0.0
        for it in self.demo_cart:
            sub = it["price"] * it["qty"]
            total += sub
            row = ctk.CTkFrame(sc, fg_color="white", corner_radius=8)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=it["name"]).grid(row=0, column=0, sticky="w", padx=10, pady=6)
            ctk.CTkLabel(row, text=f"{it['price']:,.2f} x {it['qty']}").grid(row=0, column=1, padx=10)
            ctk.CTkLabel(row, text=f"{sub:,.2f} บาท").grid(row=0, column=2, padx=10)
            row.grid_columnconfigure(0, weight=1)

        self.checkout_total = total
        ctk.CTkLabel(right, text=f"รวมทั้งสิ้น: {total:,.2f} บาท", font=("Oswald", 16, "bold")).pack(pady=6)

        ctk.CTkButton(box, text="ยืนยันและไปชำระเงิน (อัปสลิป)", fg_color="green", text_color="white",
                      command=self._create_order_and_goto_payment).pack(pady=(4, 14))

    def _create_order_and_goto_payment(self):
        addr = self.ship_address_box.get("1.0", "end").strip() if hasattr(self, "ship_address_box") else ""
        method = self.ship_method_var.get() if hasattr(self, "ship_method_var") else "ไปรษณีย์ลงทะเบียน"
        if not addr:
            messagebox.showerror("ข้อมูลไม่ครบ", "กรุณากรอกที่อยู่จัดส่ง")
            return

        total = float(getattr(self, "checkout_total", 0.0))
        if total <= 0:
            messagebox.showerror("ตะกร้า", "ยอดรวมไม่ถูกต้อง")
            return

        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("""
                INSERT INTO orders (user_email, shipping_method, shipping_address, total_amount, status, shipping_status, created_at)
                VALUES (?, ?, ?, ?, 'pending', 'waiting', ?)
            """, (self.current_email, method, addr, total, now))
            order_id = c.lastrowid

            for it in self.demo_cart:
                c.execute("""
                    INSERT INTO order_items (order_id, product_id, name, price, qty)
                    VALUES (?, ?, ?, ?, ?)
                """, (order_id, it["product_id"], it["name"], it["price"], it["qty"]))

            c.execute("""
                INSERT INTO payments (order_id, method, slip_path, status, created_at)
                VALUES (?, 'qr', NULL, 'pending', ?)
            """, (order_id, now))

            conn.commit()
        except Exception as e:
            conn.rollback()
            messagebox.showerror("Order", f"สร้างออเดอร์ล้มเหลว:\n{e}")
            return
        finally:
            conn.close()

        # ไปหน้า payment
        self.payment_page(order_id, total)

    # ----------------- Payment: สแกน QR + อัปสลิป -----------------
    def payment_page(self, order_id: int, total_amount: float):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg(self.main_frame)

        ctk.CTkButton(self.main_frame, text="🔙", width=48, height=48, fg_color="green",
                      hover_color="darkgreen", text_color="white",
                      command=self.main_menu).place(relx=0.95, rely=0.15, anchor="e")

        box = ctk.CTkFrame(self.main_frame, corner_radius=16)
        box.place(relx=0.5, rely=0.55, anchor="center", relwidth=0.82, relheight=0.72)

        ctk.CTkLabel(box, text=f"ออเดอร์ #{order_id}", font=("Oswald", 22, "bold")).pack(pady=(16, 6))
        ctk.CTkLabel(box, text=f"ยอดที่ต้องชำระ: {total_amount:,.2f} บาท").pack()

        wrap = ctk.CTkFrame(box, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=16, pady=10)

        # QR
        left = ctk.CTkFrame(wrap, corner_radius=10)
        left.pack(side="left", padx=10, pady=10)
        ctk.CTkLabel(left, text="สแกนชำระเงิน", font=("Oswald", 18, "bold")).pack(pady=(10, 6))
        try:
            qr_im = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\Qrcode.png")
            qr_ctk = ctk.CTkImage(light_image=qr_im, dark_image=qr_im, size=(380, 240))
            qr_lbl = ctk.CTkLabel(left, image=qr_ctk, text="")
            qr_lbl.image = qr_ctk
            qr_lbl.pack(padx=12, pady=10)
        except Exception:
            ctk.CTkLabel(left, text="(ไม่พบไฟล์ Qrcode.png)").pack(pady=30)

        # Slip upload
        right = ctk.CTkFrame(wrap, corner_radius=10)
        right.pack(side="left", fill="y", padx=10, pady=10)
        ctk.CTkLabel(right, text="อัปโหลดสลิปโอนเงิน", font=("Oswald", 18, "bold")).pack(pady=(10, 6))

        self.slip_path = None
        self.slip_preview = ctk.CTkLabel(right, text="(ยังไม่เลือกไฟล์)", width=320, height=180, fg_color="#f1f1f1", corner_radius=12)
        self.slip_preview.pack(padx=12, pady=8)

        def choose_slip():
            path = filedialog.askopenfilename(
                title="เลือกไฟล์สลิป",
                filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
            )
            if not path:
                return
            try:
                im = Image.open(path)
                ctkimg = ctk.CTkImage(light_image=im, dark_image=im, size=(320, 180))
                self.slip_preview.configure(image=ctkimg, text="")
                self.slip_preview.image = ctkimg
                self.slip_path = path
            except Exception as e:
                messagebox.showerror("สลิป", f"แสดงสลิปไม่ได้:\n{e}")

        ctk.CTkButton(right, text="เลือกไฟล์สลิป…", command=choose_slip).pack(pady=(0, 8))

        def submit_slip():
            if not self.slip_path:
                messagebox.showerror("สลิป", "กรุณาอัปโหลดสลิปก่อน")
                return
            ensure_media()
            ext = os.path.splitext(self.slip_path)[1].lower() or ".png"
            save_path = os.path.join("media", "slips", f"order_{order_id}{ext}")
            try:
                Image.open(self.slip_path).save(save_path)
            except Exception as e:
                messagebox.showerror("สลิป", f"บันทึกไฟล์สลิปล้มเหลว:\n{e}")
                return

            conn = sqlite3.connect(DB)
            c = conn.cursor()
            try:
                c.execute("UPDATE payments SET slip_path=?, status='pending' WHERE order_id=?", (save_path, order_id))
                conn.commit()
            finally:
                conn.close()

            messagebox.showinfo("ส่งหลักฐาน", "ส่งสลิปเรียบร้อย รอแอดมินตรวจสอบ")
            self.main_menu()

        ctk.CTkButton(box, text="ส่งหลักฐานการโอน", fg_color="green", text_color="white",
                      command=submit_slip).pack(pady=(0, 14))

    # ----------------- Admin: จัดการออเดอร์ -----------------
    def open_admin_orders(self):
        for w in self.main_frame.winfo_children():
            w.destroy()
        self._bg(self.main_frame)

        ctk.CTkButton(self.main_frame, text="🔙", width=48, height=48, fg_color="green",
                      hover_color="darkgreen", text_color="white",
                      command=self.main_menu).place(relx=0.95, rely=0.15, anchor="e")

        container = ctk.CTkFrame(self.main_frame, corner_radius=16)
        container.place(relx=0.5, rely=0.55, anchor="center", relwidth=0.86, relheight=0.74)

        ctk.CTkLabel(container, text="จัดการออเดอร์ (Admin)", font=("Oswald", 22, "bold")).pack(pady=(14, 6))

        # กรองสถานะชำระเงิน
        filt_row = ctk.CTkFrame(container, fg_color="transparent")
        filt_row.pack(pady=(0, 6))
        ctk.CTkLabel(filt_row, text="กรองสถานะชำระเงิน: ").pack(side="left", padx=6)
        self.pay_filter = ctk.StringVar(value="ทั้งหมด")
        ctk.CTkOptionMenu(filt_row, values=["ทั้งหมด", "pending", "approved", "rejected"],
                          variable=self.pay_filter, width=160,
                          command=lambda _=None: self._reload_orders(list_panel)).pack(side="left", padx=6)

        body = ctk.CTkFrame(container, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=10)

        list_panel = ctk.CTkScrollableFrame(body, width=300, height=420)
        list_panel.pack(side="left", fill="y", padx=10, pady=10)

        self.detail_panel = ctk.CTkFrame(body, corner_radius=12)
        self.detail_panel.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        self._reload_orders(list_panel)

    def _reload_orders(self, list_panel):
        for w in list_panel.winfo_children():
            w.destroy()
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("""
            SELECT o.id, o.user_email, o.total_amount, o.status, o.shipping_status, 
                   COALESCE(p.status, 'pending') as pay_status
            FROM orders o
            LEFT JOIN payments p ON p.order_id = o.id
            ORDER BY o.id DESC
        """)
        rows = c.fetchall()
        conn.close()

        f = self.pay_filter.get() if hasattr(self, "pay_filter") else "ทั้งหมด"
        if not rows:
            ctk.CTkLabel(list_panel, text="(ยังไม่มีออเดอร์)").pack(pady=8)
            return

        for oid, email, total, o_status, ship_status, pay_status in rows:
            if f != "ทั้งหมด" and pay_status != f:
                continue
            txt = f"#{oid} | {email}\nยอด {total:,.2f} บาท\nชำระ:{pay_status} / ออเดอร์:{o_status} / จัดส่ง:{ship_status}"
            ctk.CTkButton(list_panel, text=txt, width=260, height=64,
                          command=lambda x=oid: self._view_order_detail(x)).pack(fill="x", padx=6, pady=6)

    def _view_order_detail(self, order_id: int):
        for w in self.detail_panel.winfo_children():
            w.destroy()

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute("SELECT user_email, shipping_method, shipping_address, total_amount, status, shipping_status, created_at FROM orders WHERE id=?", (order_id,))
        o = c.fetchone()
        c.execute("SELECT product_id, name, price, qty FROM order_items WHERE order_id=?", (order_id,))
        items = c.fetchall()
        c.execute("SELECT method, slip_path, status, created_at FROM payments WHERE order_id=?", (order_id,))
        p = c.fetchone()
        conn.close()

        if not o:
            ctk.CTkLabel(self.detail_panel, text="ไม่พบออเดอร์").pack(pady=10)
            return

        email, ship_method, ship_addr, total, o_status, ship_status, created_at = o
        pay_method, slip_path, pay_status, pay_time = (p or ("qr", None, "pending", None))

        ctk.CTkLabel(self.detail_panel, text=f"รายละเอียดออเดอร์ #{order_id}", font=("Oswald", 20, "bold")).pack(pady=(8, 6))

        info = ctk.CTkFrame(self.detail_panel, corner_radius=10)
        info.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(info, text=f"ผู้สั่ง: {email} | วันที่: {created_at}").pack(anchor="w", padx=10, pady=2)
        ctk.CTkLabel(info, text=f"วิธีจัดส่ง: {ship_method} | สถานะออเดอร์: {o_status} | จัดส่ง: {ship_status}").pack(anchor="w", padx=10, pady=2)
        ctk.CTkLabel(info, text=f"ที่อยู่จัดส่ง:\n{ship_addr}").pack(anchor="w", padx=10, pady=6)
        ctk.CTkLabel(info, text=f"ยอดรวม: {total:,.2f} บาท").pack(anchor="w", padx=10, pady=2)

        list_box = ctk.CTkScrollableFrame(self.detail_panel, height=180)
        list_box.pack(fill="x", padx=10, pady=6)
        for pid, name, price, qty in items:
            row = ctk.CTkFrame(list_box, fg_color="white", corner_radius=8)
            row.pack(fill="x", pady=4)
            ctk.CTkLabel(row, text=name).grid(row=0, column=0, sticky="w", padx=10, pady=6)
            ctk.CTkLabel(row, text=f"{price:,.2f} x {qty}").grid(row=0, column=1, padx=10)
            row.grid_columnconfigure(0, weight=1)

        slip_box = ctk.CTkFrame(self.detail_panel, corner_radius=10)
        slip_box.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(slip_box, text=f"สถานะการชำระเงิน: {pay_status}", font=("Oswald", 16, "bold")).pack(anchor="w", padx=10, pady=6)
        prev = ctk.CTkLabel(slip_box, text="(ไม่มีสลิป)", width=320, height=180, fg_color="#f1f1f1", corner_radius=12)
        prev.pack(padx=10, pady=6)
        if slip_path and os.path.exists(slip_path):
            try:
                sim = Image.open(slip_path)
                sctk = ctk.CTkImage(light_image=sim, dark_image=sim, size=(320, 180))
                prev.configure(image=sctk, text="")
                prev.image = sctk
            except Exception:
                pass

        btns = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        btns.pack(pady=6)
        ctk.CTkButton(btns, text="อนุมัติการชำระเงิน", fg_color="green", text_color="white",
                      command=lambda: self._set_payment_status(order_id, "approved")).pack(side="left", padx=6)
        ctk.CTkButton(btns, text="ปฏิเสธการชำระเงิน", fg_color="#b00020", text_color="white",
                      command=lambda: self._set_payment_status(order_id, "rejected")).pack(side="left", padx=6)

        ship_row = ctk.CTkFrame(self.detail_panel, fg_color="transparent")
        ship_row.pack(pady=8)
        ctk.CTkLabel(ship_row, text="สถานะจัดส่ง: ").pack(side="left", padx=6)
        self.ship_status_var = ctk.StringVar(value=ship_status)
        ctk.CTkOptionMenu(ship_row, values=["waiting", "packing", "shipped", "delivered"],
                          variable=self.ship_status_var, width=160).pack(side="left", padx=6)
        ctk.CTkButton(ship_row, text="อัปเดต",
                      command=lambda: self._set_shipping_status(order_id, self.ship_status_var.get())).pack(side="left", padx=6)

    def _set_payment_status(self, order_id: int, new_status: str):
        if new_status not in ("approved", "rejected"):
            return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("UPDATE payments SET status=? WHERE order_id=?", (new_status, order_id))
            if new_status == "approved":
                c.execute("UPDATE orders SET status='paid' WHERE id=?", (order_id,))
            else:
                c.execute("UPDATE orders SET status='cancelled' WHERE id=?", (order_id,))
            conn.commit()
        finally:
            conn.close()
        messagebox.showinfo("ชำระเงิน", f"อัปเดตสถานะการชำระเงินเป็น {new_status}")
        self._view_order_detail(order_id)

    def _set_shipping_status(self, order_id: int, new_status: str):
        if new_status not in ("waiting", "packing", "shipped", "delivered"):
            return
        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            c.execute("UPDATE orders SET shipping_status=? WHERE id=?", (new_status, order_id))
            conn.commit()
        finally:
            conn.close()
        messagebox.showinfo("จัดส่ง", f"อัปเดตสถานะจัดส่งเป็น {new_status}")
        self._view_order_detail(order_id)


# ----------------- Run -----------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = Qrcode_page(root)
    root.mainloop()
