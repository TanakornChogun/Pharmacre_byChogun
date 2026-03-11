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
        shell = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20)
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
            ("สินค้า", 300, "w"),
            ("ราคา", 110, "e"),
            ("จำนวน", 140, "center"),
            ("รวมย่อย", 120, "e"),
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
        shell = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20)
        shell.place(relx=0.5, rely=0.62, anchor="center", relwidth=0.82, relheight=0.72)

        ctk.CTkLabel(shell, text="ตรวจสอบและยืนยันคำสั่งซื้อ", font=("Arial", 22, "bold")).pack(pady=(14, 6))

        body = ctk.CTkFrame(shell, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=16, pady=8)

        # ================= ซ้าย: บิล/สรุปรายการ =================
        left = ctk.CTkFrame(body, corner_radius=14, fg_color="#ECFFF1")
        left.pack(side="left", fill="both", expand=True, padx=(0, 8), pady=4)

        head = ctk.CTkFrame(left, fg_color="transparent")
        head.pack(fill="x", padx=12, pady=(10, 4))
        for i, (txt, anchor, w) in enumerate([("สินค้า", "w", 340), ("ราคา", "e", 110), ("จำนวน", "e", 110), ("รวมย่อย", "e", 120)]):
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
            fees = {"Kerry": 45.0, "J&T": 40.0, "ไปรษณีย์ไทย": 35.0, "Flash": 39.0}
            # เงื่อนไขส่งฟรี: ชิ้นรวม >= 2 หรือ ชนิดสินค้า >= 2
            free = (total_qty >= 2) or (len(self.cart) >= 2)
            ship_fee = 0.0 if free else fees.get(self._ship_method_var.get(), 40.0)
            vat = round(subtotal * 0.04, 2)  # 4%
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

        ctk.CTkLabel(bottom_left, text="VAT 4%:", anchor="e")\
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
    # อ่าน input
        address = self._addr_box_for_order.get("1.0", "end").strip() if hasattr(self, "_addr_box_for_order") else ""
        phone = self._phone_entry.get().strip() if hasattr(self, "_phone_entry") else ""
        ship_method = self._ship_method_var.get() if hasattr(self, "_ship_method_var") else "Kerry"

        if not re.fullmatch(r"0\d{9}", phone):
            messagebox.showwarning("ข้อมูล", "กรุณากรอกเบอร์โทรให้ถูกต้อง (เช่น 0812345678)")
            return
        if not address or address == "กรอกที่อยู่จัดส่งที่นี่...":
            messagebox.showwarning("ที่อยู่", "กรุณากรอกที่อยู่จัดส่ง")
            return
        if not self.cart:
            messagebox.showerror("ออเดอร์", "ตะกร้าว่าง")
            return

        # ค่าส่ง (ฟรีถ้า >=2 ชิ้น หรือ >=2 รายการ)
        _, total_qty = self._calc_cart_total()
        fees = {"Kerry": 45.0, "J&T": 40.0, "ไปรษณีย์ไทย": 35.0, "Flash": 39.0}
        ship_fee = 0.0 if (total_qty >= 2 or len(self.cart) >= 2) else fees.get(ship_method, 40.0)

        vat = round(subtotal * 0.04, 2)  # 4%
        grand_total = float(subtotal) + float(ship_fee) + float(vat)

        now = datetime.datetime.now().isoformat(timespec="seconds")
        order_id = None
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            # เพิ่มคอลัมน์ contact_phone ถ้ายังไม่มี
            try:
                c.execute("ALTER TABLE orders ADD COLUMN contact_phone TEXT")
            except Exception:
                pass

            c.execute("""
                INSERT INTO orders (
                    user_email, shipping_method, shipping_address, contact_phone,
                    total_price, status, shipping_status, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, 'pending', 'draft', ?, ?)
            """, (self.current_email, ship_method, address, phone, grand_total, now, now))
            order_id = c.lastrowid

            for pid, it in self.cart.items():
                c.execute("""
                    INSERT INTO order_items (order_id, product_id, name, price, qty, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (order_id, pid, it["name"], float(it["price"]), int(it["qty"]),
                    float(it["price"]) * int(it["qty"])))

            conn.commit()
        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            messagebox.showerror("ออเดอร์", f"ไม่สามารถสร้างออเดอร์ได้:\n{e}")
            conn.close()
            return
        finally:
            conn.close()

        # อัปเดตเบอร์/ที่อยู่ของผู้ใช้กลับฐาน (ให้โปรไฟล์ sync)
        try:
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("UPDATE users SET phone=?, address=? WHERE email=?", (phone, address, self.current_email))
            conn.commit()
        except Exception:
            pass
        finally:
            try: conn.close()
            except Exception: pass

        # ไปหน้าชำระเงินเดิมของคุณ (ถ้าต้องการใช้สลิปให้เรียก payment_page(order_id))
        self.Qrcode()

    def _export_invoice_image(self):
    #"""สร้างภาพ PNG ของบิลจากตะกร้าปัจจุบัน"""
        try:
            png_path, _ = self._build_invoice_bitmap()
            messagebox.showinfo("บันทึกบิล", f"บันทึก PNG แล้วที่:\n{png_path}")
        except Exception as e:
            messagebox.showerror("บันทึกบิล", f"ไม่สำเร็จ:\n{e}")

    def _export_invoice_pdf(self):
        """สร้าง PDF ของบิล (แปลงจาก PNG)"""
        try:
            png_path, img = self._build_invoice_bitmap()
            pdf_path = png_path.replace(".png", ".pdf")
            # บันทึก PDF ด้วย PIL (จะฝังหน้าเดียวจากภาพ)
            img.convert("RGB").save(pdf_path, "PDF", resolution=200.0)
            messagebox.showinfo("บันทึกบิล", f"บันทึก PDF แล้วที่:\n{pdf_path}")
        except Exception as e:
            messagebox.showerror("บันทึกบิล", f"ไม่สำเร็จ:\n{e}")

    def _build_invoice_bitmap(self):
        """วาดบิลเป็นภาพจาก self.cart + ข้อมูลลูกค้า -> (path, PIL.Image)"""
        from PIL import ImageDraw, ImageFont

        os.makedirs("invoices", exist_ok=True)
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        png_path = os.path.join("invoices", f"invoice_{ts}.png")

        # เตรียมข้อมูล
        username = getattr(self, "current_username", "Guest")
        email = getattr(self, "current_email", "")
        phone = self._phone_entry.get().strip() if hasattr(self, "_phone_entry") else ""
        address = self._addr_box_for_order.get("1.0", "end").strip() if hasattr(self, "_addr_box_for_order") else ""

        subtotal, total_qty = self._calc_cart_total()
        fees = {"Kerry": 45.0, "J&T": 40.0, "ไปรษณีย์ไทย": 35.0, "Flash": 39.0}
        ship_method = self._ship_method_var.get() if hasattr(self, "_ship_method_var") else "Kerry"
        ship_fee = 0.0 if (total_qty >= 2 or len(self.cart) >= 2) else fees.get(ship_method, 40.0)
        vat = round(subtotal * 0.04, 2)
        grand = subtotal + ship_fee + vat

        # สร้างภาพพื้นฐาน
        W, H = 900, 1200
        img = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(img)
        try:
            # หากไม่มีฟอนต์ TTF ก็จะใช้ default
            font_h1 = ImageFont.truetype("arial.ttf", 28)
            font_h2 = ImageFont.truetype("arial.ttf", 22)
            font_txt = ImageFont.truetype("arial.ttf", 18)
        except Exception:
            font_h1 = font_h2 = font_txt = None

        y = 40
        draw.text((40, y), "ใบยืนยันคำสั่งซื้อ (Invoice Preview)", fill="black", font=font_h1); y += 40
        draw.text((40, y), f"วันที่: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", fill="black", font=font_txt); y += 28
        draw.text((40, y), f"ลูกค้า: {username}   อีเมล: {email}", fill="black", font=font_txt); y += 28
        draw.text((40, y), f"เบอร์โทร: {phone}", fill="black", font=font_txt); y += 28
        draw.text((40, y), "ที่อยู่จัดส่ง:", fill="black", font=font_txt); y += 24

        # ที่อยู่หลายบรรทัด
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

        # แถวสินค้า
        for pid, it in self.cart.items():
            name = it["name"]; price = float(it["price"]); qty = int(it["qty"]); line_total = price * qty
            draw.text((40, y), name[:40], fill="black", font=font_txt)
            draw.text((500, y), f"{price:,.2f}", fill="black", font=font_txt)
            draw.text((620, y), f"{qty}", fill="black", font=font_txt)
            draw.text((720, y), f"{line_total:,.2f}", fill="black", font=font_txt); y += 24

        y += 10
        draw.line([(40, y), (W-40, y)], fill="black", width=1); y += 12
        draw.text((500, y), f"รวมสินค้า:", fill="black", font=font_txt)
        draw.text((720, y), f"{subtotal:,.2f}", fill="black", font=font_txt); y += 24

        draw.text((500, y), f"ค่าส่ง ({ship_method}):", fill="black", font=font_txt)
        draw.text((720, y), ("ฟรี" if ship_fee == 0 else f"{ship_fee:,.2f}"), fill="black", font=font_txt); y += 24

        draw.text((500, y), "VAT 4%:", fill="black", font=font_txt)
        draw.text((720, y), f"{vat:,.2f}", fill="black", font=font_txt); y += 24

        draw.line([(500, y), (W-40, y)], fill="black", width=1); y += 12
        draw.text((500, y), "ยอดชำระทั้งหมด:", fill="black", font=font_h2)
        draw.text((720, y), f"{grand:,.2f}", fill="black", font=font_h2)

        # เผื่อส่วนล่าง
        img.save(png_path)
        return png_path, img



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
            command=self.Confirm_items
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
        for pid, item in self.cart.items():
            subtotal += float(item["price"]) * int(item["qty"])
        # สมมติค่าส่ง 0 ตอนนี้ (อนาคตค่อยคิดตามจำนวน/บริษัทขนส่ง)
        shipping = 0.0
        tax_rate = 0.0
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
            self._summary_shipping_lbl.configure(text=f"ค่าส่ง: {shipping:,.2f} บาท")
            self._summary_tax_lbl.configure(text=f" ภาษี ({int(tax_rate*100)}%): {tax:,.2f} บาท")
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

