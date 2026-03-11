import sqlite3
import hashlib
import os
import datetime
#import qrcode
from io import BytesIO
from PIL import Image, ImageTk
import customtkinter as ctk
from tkinter import messagebox

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")


#c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\2.db

def get_db_connection():
    conn = sqlite3.connect(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\2.db")
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
        c.execute("INSERT INTO users (username, password_hash, is_admin) VALUES (?, ?, ?)",
                  ("admin", pw_hash, 1))
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
        self.current_user = None  # dict row from users
        self.cart = {}  # product_id -> qty

        # Frames - we'll swap views inside main_frame
        self.main_frame = ctk.CTkFrame(root)
        self.main_frame.pack(fill="both", expand=True)

        # Start with login screen
        self.show_login_screen()

    def clear_main(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()
        

    def show_login_screen(self):
        self.clear_main()
        # <-- แก้ตรงนี้: ย้าย width/height ไปที่ constructor
        
        #logo = ctk.CTkImage(Image.open(""), size=(80, 80))
        #ctk.CTkLabel(frame, image=logo, text="").pack(pady=5)
        

        frame = ctk.CTkFrame(self.main_frame, corner_radius=20, width=420, height=320 ,fg_color=("beige"))
        frame.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(frame, text="              ", font=("Arial", 10, "bold")).pack()

        ctk.CTkLabel(frame, text="     PharmaCare +     ", font=("Arial", 40, "bold"),text_color=("green")).pack(pady=20)
        
        ctk.CTkLabel(frame, text="เพื่อสุขภาพที่ดี", font=("Arial", 20, "bold")).pack(pady=10)
        
        
        ctk.CTkLabel(frame, text="Username").pack(pady=(10, 2) )
        username_entry = ctk.CTkEntry(frame, width=150, placeholder_text="Username")
        username_entry.pack()

        ctk.CTkLabel(frame, text="Password").pack(pady=(10, 2))
        password_entry = ctk.CTkEntry(frame, width=150, show="*", placeholder_text="Password")
        password_entry.pack()

        def login_action():
            username = username_entry.get().strip()
            pw = password_entry.get().strip()
            if not username or not pw:
                messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณากรอก username และ password")
                return
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM users WHERE username = ?", (username,))
            row = c.fetchone()
            conn.close()
            if row and verify_password(pw, row["password_hash"]):
                self.current_user = row
                self.cart = {}
                self.show_home_screen()  #login to หน้าหลัก              
            else:
                messagebox.showerror("ล้มเหลว", "Username หรือ Password ไม่ถูกต้อง")

        def register_action():
            username = username_entry.get().strip()
            pw = password_entry.get().strip()
            if not username or not pw:
                messagebox.showwarning("ข้อมูลไม่ครบ", "กรุณากรอก username และ password")
                return
            conn = get_db_connection()
            c = conn.cursor()
            try:
                c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)",
                          (username, hash_password(pw)))
                conn.commit()
                messagebox.showinfo("สำเร็จ", "ลงทะเบียนเรียบร้อย ล็อกอินได้เลย")
            except sqlite3.IntegrityError:
                messagebox.showerror("ผิดพลาด", "Username นี้ถูกใช้แล้ว")
            finally:
                conn.close()

        btn_login = ctk.CTkButton(frame, text="Log in", fg_color=("blue"),text_color=("white"),command=login_action)
        btn_login.pack(pady=(30, 1)) #, ipadx=4, ipady=4

        btn_register = ctk.CTkButton(frame, text="Register (สร้างบัญชี)", fg_color=("blue"),text_color=("white"), command=register_action)
        btn_register.pack(pady=(10, 6))
        ctk.CTkLabel(frame, text="              ", font=("Arial", 50, "bold")).pack()

#หน้าหลัก หลังจากlogin 
    def show_home_screen(self):
        self.clear_main()
        # Top bar with username, profile, cart button
        top = ctk.CTkFrame(self.main_frame)
        top.pack(fill="x", side="top", padx=8, pady=8)
        ctk.CTkLabel(top, text=f"PharmaCare +    ผู้ใช้: {self.current_user['username']}", font=("Arial", 14, "bold")).pack(side="left")
        btn_profile = ctk.CTkButton(top, text="Profile", width=100)
        btn_profile.pack(side="right", padx=6)
        btn_cart = ctk.CTkButton(top, text=f"ตะกร้า ()", width=130)
        btn_cart.pack(side="right", padx=6)
        if self.current_user["is_admin"]:
            btn_admin = ctk.CTkButton(top, text="Admin", width=100, command=self.show_admin)
            btn_admin.pack(side="right", padx=6)
        left = ctk.CTkFrame(self.main_frame, width=180)
        left.pack(side="left", fill="y", padx=(8,4), pady=8)
        ctk.CTkLabel(left, text="หมวดหมู่", font=("Arial", 16, "bold")).pack(pady=6)
        selected_category = ctk.StringVar(value="ทั้งหมด")
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT DISTINCT category FROM products")
        cats = [r["category"] for r in c.fetchall()]
        conn.close()
        def select_cat(cat):
            selected_category.set(cat)
            self.display_products_frame(cat)
        btn_all = ctk.CTkButton(left, text="ทั้งหมด", width=150, command=lambda: select_cat("ทั้งหมด"))
        btn_all.pack(pady=4)
        btn_all = ctk.CTkButton(left, text="เวชสำอาง", width=150, command=lambda: select_cat("ทั้งหมด"))
        btn_all.pack(pady=4)
        btn_all = ctk.CTkButton(left, text="สินค้าเพื่อสุขภาพ", width=150, command=lambda: select_cat("ทั้งหมด"))
        btn_all.pack(pady=4)
        btn_all = ctk.CTkButton(left, text="ยา", width=150, command=lambda: select_cat("ทั้งหมด"))
        btn_all.pack(pady=4)
        for cat in cats:
            b = ctk.CTkButton(left, text=cat, width=150, command=lambda c=cat: select_cat(c))
            b.pack(pady=4)
            
        center = ctk.CTkFrame(self.main_frame)
        center.pack(side="left", fill="both", expand=True, padx=(4,4), pady=8)
        self.products_container = ctk.CTkScrollableFrame(center)
        self.products_container.pack(fill="both", expand=True, padx=10, pady=6)
        right = ctk.CTkFrame(self.main_frame, width=220)
        right.pack(side="right", fill="y", padx=(4,8), pady=8)
        ctk.CTkLabel(right, text="ตะกร้าสรุป", font=("Arial", 14, "bold")).pack(pady=6)
        self.cart_summary = ctk.CTkTextbox(right, width=200, height=150)
        self.cart_summary.pack(pady=6)
        self.update_cart_display_summary()
    
    def display_products_frame(self, category="ทั้งหมด"):
        # clear current product widgets
        for w in self.products_container.winfo_children():
            w.destroy()

        conn = get_db_connection()
        c = conn.cursor()
        if category == "ทั้งหมด":
            c.execute("SELECT * FROM products")
        else:
            c.execute("SELECT * FROM products WHERE category = ?", (category,))
        products = c.fetchall()
        conn.close()

        # display as cards
        for prod in products:
            card = ctk.CTkFrame(self.products_container, corner_radius=8)
            card.pack(fill="x", padx=8, pady=6)

            header = ctk.CTkFrame(card)
            header.pack(fill="x", pady=6, padx=6)
            ctk.CTkLabel(header, text=prod["name"], font=("Arial", 14, "bold")).pack(side="left")
            ctk.CTkLabel(header, text=f"{prod['price']:.2f} บาท", anchor="e").pack(side="right")

            body = ctk.CTkFrame(card)
            body.pack(fill="x", padx=6, pady=(0,8))
            ctk.CTkLabel(body, text=prod["description"] or "-", wraplength=500, justify="left").pack(side="left", padx=6)

            # qty selector + add to cart
            right_box = ctk.CTkFrame(body)
            right_box.pack(side="right", padx=10)
            qty_var = ctk.IntVar(value=1)
            qty_spinner = ctk.CTkEntry(right_box, width=60, textvariable=qty_var)
            qty_spinner.pack(pady=4)
            def add_this(p=prod, var=qty_var):
                try:
                    q = int(var.get())
                except:
                    messagebox.showerror("ผิดพลาด", "จำนวนไม่ถูกต้อง")
                    return
                if q <= 0:
                    messagebox.showwarning("ผิดพลาด", "จำนวนต้องมากกว่า 0")
                    return
                # check stock
                if p["stock"] < q:
                    messagebox.showwarning("สต็อกไม่พอ", f"สินค้าคงเหลือ {p['stock']} ชิ้น")
                    return
                self.add_to_cart(p["id"], q)
            btn = ctk.CTkButton(right_box, text="เพิ่มลงตะกร้า", command=add_this)
            btn.pack()


    def add_to_cart(self, product_id, qty=1):
        self.cart[product_id] = self.cart.get(product_id, 0) + qty
        # update button text
        self.update_cart_display_summary()
        # update cart button label at top (by re-rendering home screen top)
        self.show_home_screen()

    def cart_total_qty(self):
        return sum(self.cart.values())

    def update_cart_display_summary(self):
        self.cart_summary.delete("1.0", "end")
        if not self.cart:
            self.cart_summary.insert("end", "ตะกร้าว่าง")
            return
        conn = get_db_connection()
        c = conn.cursor()
        total = 0
        i = 1
        for pid, qty in self.cart.items():
            c.execute("SELECT name, price FROM products WHERE id = ?", (pid,))
            p = c.fetchone()
            if p:
                line_total = p["price"] * qty
                total += line_total
                self.cart_summary.insert("end", f"{i}. {p['name']} x{qty} = {line_total:.2f} บาท\n")
                i += 1
        self.cart_summary.insert("end", f"\nรวม: {total:.2f} บาท")
        conn.close()


    def show_cart(self):
        # opens a new window to show cart details and checkout
        cart_win = ctk.CTkToplevel(self.root)
        cart_win.title("ตะกร้าสินค้า")
        cart_win.geometry("600x500")

        top = ctk.CTkFrame(cart_win)
        top.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(top, text="ตะกร้าสินค้า", font=("Arial", 18, "bold")).pack(side="left")
        ctk.CTkLabel(top, text=f"ผู้ใช้: {self.current_user['username']}").pack(side="right")

        body = ctk.CTkFrame(cart_win)
        body.pack(fill="both", expand=True, padx=8, pady=8)

        # table-like display using Textbox
        tb = ctk.CTkTextbox(body, width=560, height=320)
        tb.pack(pady=6)

        conn = get_db_connection()
        c = conn.cursor()
        total = 0
        tb.insert("end", f"{'ลำดับ':<6}{'ชื่อ':<30}{'จำนวน':<8}{'ราคา/ชิ้น':<12}{'รวม':<10}\n")
        tb.insert("end", "-"*80 + "\n")
        i = 1
        for pid, qty in self.cart.items():
            c.execute("SELECT name, price FROM products WHERE id = ?", (pid,))
            p = c.fetchone()
            if p:
                line_total = p["price"] * qty
                total += line_total
                tb.insert("end", f"{i:<6}{p['name'][:28]:<30}{qty:<8}{p['price']:<12.2f}{line_total:<10.2f}\n")
                i += 1
        tb.insert("end", "\n")
        tb.insert("end", f"ราคารวมทั้งหมด: {total:.2f} บาท\n")
        conn.close()

    def show_admin(self):
        if not self.current_user or not self.current_user["is_admin"]:
            messagebox.showerror("สิทธิ์ไม่เพียงพอ", "ต้องเป็น Admin เท่านั้น")
            return
        win = ctk.CTkToplevel(self.root)
        win.title("Admin Panel - จัดการสินค้า")
        win.geometry("720x520")
        left = ctk.CTkFrame(win, width=360)
        left.pack(side="left", fill="y", padx=8, pady=8)
        right = ctk.CTkFrame(win)
        right.pack(side="left", fill="both", expand=True, padx=8, pady=8)

        # form to add or update product
        ctk.CTkLabel(left, text="ชื่อสินค้า").pack(pady=4)
        name_e = ctk.CTkEntry(left, width=300)
        name_e.pack()
        ctk.CTkLabel(left, text="หมวดหมู่").pack(pady=4)
        cat_e = ctk.CTkEntry(left, width=300)
        cat_e.pack()
        ctk.CTkLabel(left, text="ราคา").pack(pady=4)
        price_e = ctk.CTkEntry(left, width=300)
        price_e.pack()
        ctk.CTkLabel(left, text="สต็อก").pack(pady=4)
        stock_e = ctk.CTkEntry(left, width=300)
        stock_e.pack()
        ctk.CTkLabel(left, text="คำอธิบาย").pack(pady=4)
        desc_e = ctk.CTkEntry(left, width=300)
        desc_e.pack()

        selected_pid = [None]

        def load_product_to_form(pid):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM products WHERE id = ?", (pid,))
            p = c.fetchone()
            conn.close()
            if p:
                name_e.delete(0, "end"); name_e.insert(0, p["name"])
                cat_e.delete(0, "end"); cat_e.insert(0, p["category"])
                price_e.delete(0, "end"); price_e.insert(0, str(p["price"]))
                stock_e.delete(0, "end"); stock_e.insert(0, str(p["stock"]))
                desc_e.delete(0, "end"); desc_e.insert(0, p["description"] or "")
                selected_pid[0] = pid

        def refresh_product_list():
            for w in right.winfo_children():
                w.destroy()
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("SELECT * FROM products")
            prods = c.fetchall()
            conn.close()
            for p in prods:
                f = ctk.CTkFrame(right)
                f.pack(fill="x", padx=6, pady=6)
                ctk.CTkLabel(f, text=f"{p['name']} ({p['category']}) - {p['price']:.2f} บาท  [{p['stock']}]").pack(side="left")
                btn_load = ctk.CTkButton(f, text="แก้ไข", width=80, command=lambda pid=p["id"]: load_product_to_form(pid))
                btn_load.pack(side="right", padx=6)
                btn_delete = ctk.CTkButton(f, text="ลบ", width=80, fg_color="red",
                                           command=lambda pid=p["id"]: self.admin_delete_product(pid, refresh_product_list))
                btn_delete.pack(side="right", padx=6)

        def admin_add_update():
            name = name_e.get().strip(); cat = cat_e.get().strip()
            try:
                price = float(price_e.get().strip())
            except:
                messagebox.showerror("ผิดพลาด", "ราคาไม่ถูกต้อง")
                return
            try:
                stock = int(stock_e.get().strip())
            except:
                messagebox.showerror("ผิดพลาด", "สต็อกไม่ถูกต้อง")
                return
            desc = desc_e.get().strip()
            conn = get_db_connection()
            c = conn.cursor()
            if selected_pid[0]:
                c.execute("UPDATE products SET name=?, category=?, price=?, stock=?, description=? WHERE id=?",
                          (name, cat, price, stock, desc, selected_pid[0]))
                messagebox.showinfo("สำเร็จ", "อัพเดตสินค้าเรียบร้อย")
            else:
                c.execute("INSERT INTO products (name, category, price, stock, description) VALUES (?, ?, ?, ?, ?)",
                          (name, cat, price, stock, desc))
                messagebox.showinfo("สำเร็จ", "เพิ่มสินค้าเรียบร้อย")
            conn.commit()
            conn.close()
            # reset
            name_e.delete(0,"end"); cat_e.delete(0,"end"); price_e.delete(0,"end"); stock_e.delete(0,"end"); desc_e.delete(0,"end")
            selected_pid[0] = None
            refresh_product_list()

        ctk.CTkButton(left, text="เพิ่ม/บันทึก", command=admin_add_update).pack(pady=6)
        refresh_product_list()

    def admin_delete_product(self, pid, callback=None):
        if messagebox.askyesno("ยืนยัน", "ต้องการลบสินค้านี้จริงหรือไม่?"):
            conn = get_db_connection()
            c = conn.cursor()
            c.execute("DELETE FROM products WHERE id = ?", (pid,))
            conn.commit()
            conn.close()
            if callback:
                callback()


if __name__ == "__main__":
    root = ctk.CTk()
    app = PharmaCareApp(root)
    root.mainloop()


