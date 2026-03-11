def open_admin(self):
        # ล้างหน้าปัจจุบัน
        for w in self.main_frame.winfo_children():
            w.destroy()

        # พื้นหลัง
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\New2Background.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        # เก็บ state ของแบบฟอร์ม
        self.selected_product_id = None
        self.product_image_path = None
        self.admin_img_photo = None


        ctk.CTkButton(self.main_frame, text="🔙 Log out",
                    fg_color="#ff0000", hover_color="#5e0303", text_color="white",
                    command=self._logout).place(relx=1.0, rely=0.80, anchor="e")
        
        OrdersButton = ctk.CTkButton(
                self.main_frame, 
                text="🧾 เช็คออเดอร์", 
                width=120, height=36,
                fg_color="#00796B", 
                hover_color="#00564F", 
                text_color="white",
                command=self.open_orders_admin
                ) 
        OrdersButton.place(relx=1.0, rely=0.27, anchor="e")

        # ปุ่มย้อนกลับ
        """back_btn = ctk.CTkButton(
            self.main_frame, text="🔙",
            width=50, height=50, fg_color="green",
            hover_color="darkgreen", text_color="white",
            command=lambda: self.main_page(getattr(self, "current_username", "Guest"))
        )
        back_btn.place(relx=0.99, rely=0.13, anchor="e")"""

        # กรอบใหญ่
        container = ctk.CTkFrame(self.main_frame, fg_color="white", corner_radius=20, bg_color="white")
        container.place(relx=0.5, rely=0.56, anchor="center", relwidth=0.80, relheight=0.70)

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

        ctk.CTkLabel(right, text="สต็อก").grid(row=2, column=2, sticky="e", padx=8, pady=6)
        self.p_stock = ctk.CTkEntry(right, width=120, placeholder_text="เช่น 50")
        self.p_stock.grid(row=2, column=3, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(right, text="รายละเอียด").grid(row=3, column=0, sticky="ne", padx=8, pady=6)
        self.p_desc = ctk.CTkTextbox(right, width=320, height=120)
        self.p_desc.grid(row=3, column=1, columnspan=2, sticky="w", padx=8, pady=6)

        # รูปภาพ + ปุ่มเลือกไฟล์
        self.preview = ctk.CTkLabel(right, text="(ยังไม่มีรูป)", width=160, height=160, fg_color="#f1f1f1", corner_radius=12)
        self.preview.grid(row=1, column=4, rowspan=3, padx=(16,8), pady=6)

        ctk.CTkLabel(right, text="หมวดหมู่").grid(row=4, column=0, sticky="e", padx=8, pady=6)
        self.p_cat = ctk.CTkOptionMenu(right, values=list(CATEGORY_MAP.keys()), width=160, command=self._on_admin_cat_change)
        self.p_cat.grid(row=4, column=1, sticky="w", padx=8, pady=6)

        ctk.CTkLabel(right, text="ประเภทย่อย").grid(row=4, column=2, sticky="e", padx=8, pady=6)
        self.p_subcat = ctk.CTkOptionMenu(right, values=[""], width=160)
        self.p_subcat.grid(row=4, column=3, sticky="w", padx=8, pady=6)

        choose_img = ctk.CTkButton(right, text="เลือกรูปภาพ…", command=self._admin_pick_image)
        choose_img.grid(row=5, column=4, sticky="n", padx=8, pady=(0,12))

        # ปุ่มคำสั่ง
        btn_row = ctk.CTkFrame(right, fg_color="transparent")
        btn_row.grid(row=6, column=0, columnspan=4, sticky="we", padx=8, pady=(10,0))
        ctk.CTkButton(btn_row, text="เพิ่มใหม่", fg_color="#2e7d32", command=self._admin_create).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="บันทึก", fg_color="#1976d2", command=self._admin_save).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="ลบ", fg_color="#b00020", command=self._admin_delete).pack(side="left", padx=6)
        ctk.CTkButton(btn_row, text="ล้างฟอร์ม", command=self._admin_clear_form).pack(side="left", padx=6)

        # default หมวด/ประเภทย่อย
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

    def open_orders_admin(self):
        for w in self.main_frame.winfo_children():
            w.destroy()

        img_bg = Image.open(r"d:\PROJECT\NewBG.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

    def _admin_pick_image(self):
        path = filedialog.askopenfilename(
            title="เลือกรูปสินค้า",
            filetypes=[("Image files", "*.png;*.jpg;*.jpeg;*.webp;*.bmp")]
        )
        if not path:
            return

        try:
            im = Image.open(path)
            im.thumbnail((180, 180))

            # ✅ สร้างอ็อบเจกต์รูปภาพ
            photo = ImageTk.PhotoImage(im)

            # ✅ แสดงรูปใน Label
            self.preview.configure(image=photo, text="")

            # ✅ เก็บอ้างอิงไว้ใน instance variable
            self.preview.image = photo          # ป้องกัน GC เก็บรูป
            self.admin_img_photo = photo        # กันรูปหายเมื่อเปลี่ยนหน้า

            # ✅ เก็บพาธไว้ใช้ตอนบันทึกสินค้า
            self.product_image_path = path

        except Exception as e:
            messagebox.showerror("รูปภาพ", f"แสดงตัวอย่างรูปไม่ได้:\n{e}")

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
            SELECT id, name, price, description, image_path, category, subcategory, stock
            FROM products WHERE id=?
        """, (product_id,))
        row = c.fetchone()
        conn.close()

        if not row:
            messagebox.showerror("โหลดสินค้า", "ไม่พบข้อมูลสินค้า")
            return

        self.selected_product_id = row[0]
        name     = row[1] or ""
        price    = row[2] or 0
        desc     = row[3] or ""
        img_path = row[4]
        cat      = row[5] or list(CATEGORY_MAP.keys())[0]
        sub      = row[6] or (CATEGORY_MAP.get(cat, [""])[0] if CATEGORY_MAP.get(cat) else "")
        stock    = int(row[7] or 0)

        # ใส่ลงฟอร์ม
        self.p_name.delete(0, "end");  self.p_name.insert(0, name)
        self.p_price.delete(0, "end"); self.p_price.insert(0, f"{price:g}")
        self.p_desc.delete("1.0", "end"); self.p_desc.insert("1.0", desc)
        self.p_stock.delete(0, "end"); self.p_stock.insert(0, str(stock))
        self.product_image_path = img_path

        # พรีวิวรูป
        self.preview.configure(image=None, text="(ยังไม่มีรูป)")
        self.admin_img_photo = None
        if img_path and os.path.exists(img_path):
            try:
                im = Image.open(img_path)
                im.thumbnail((180, 180))
                self.admin_img_photo = ImageTk.PhotoImage(im)
                self.preview.configure(image=self.admin_img_photo, text="")
                self.preview.image = self.admin_img_photo  # กัน GC
            except Exception:
                self.preview.configure(text="(ยังไม่มีรูป)")
                self.preview.image = None

        # เมนูหมวด/ประเภทย่อย
        if cat not in CATEGORY_MAP:
            self.p_cat.configure(values=list(CATEGORY_MAP.keys()) + [cat])
        else:
            self.p_cat.configure(values=list(CATEGORY_MAP.keys()))
        self.p_cat.set(cat)
        subs = CATEGORY_MAP.get(cat, [])
        self.p_subcat.configure(values=subs if subs else [""])
        self.p_subcat.set(sub if sub in subs else (subs[0] if subs else ""))

    def _admin_create(self):
        # เคลียร์ฟอร์มแล้วเริ่มกรอกใหม่
        self.selected_product_id = None
        self.p_name.delete(0, "end")
        self.p_price.delete(0, "end")
        self.p_desc.delete("1.0", "end")
        try:
            self.p_stock.delete(0, "end")
        except Exception:
            pass
        self.product_image_path = None
        self.preview.configure(image=None, text="(ยังไม่มีรูป)")
        self.preview.image = None
        self.admin_img_photo = None
        first_cat = list(CATEGORY_MAP.keys())[0]
        self.p_cat.set(first_cat)
        self._on_admin_cat_change(first_cat)

    def _admin_save(self):
        name      = self.p_name.get().strip()
        price_txt = self.p_price.get().strip() or "0"
        stock_txt = (self.p_stock.get() or "0").strip()
        desc      = self.p_desc.get("1.0", "end").strip()
        cat       = self.p_cat.get().strip()
        sub       = self.p_subcat.get().strip()

        try:
            price = float(price_txt)
            stock = int(stock_txt)
            if stock < 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("บันทึก", "ราคา/สต็อกไม่ถูกต้อง")
            return

        # ถ้ายังไม่ได้เลือกรูปใหม่ตอนแก้ไข → ใช้ path เดิม
        if self.selected_product_id is not None and not self.product_image_path:
            conn_old = sqlite3.connect(DB)
            c_old = conn_old.cursor()
            c_old.execute("SELECT image_path FROM products WHERE id=?", (self.selected_product_id,))
            old = c_old.fetchone()
            conn_old.close()
            if old and old[0]:
                self.product_image_path = old[0]

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        try:
            if self.selected_product_id is None:
                c.execute(
                    "INSERT INTO products (name, price, description, image_path, category, subcategory, stock) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (name, price, desc, self.product_image_path, cat, sub, stock)
                )
                conn.commit()
                self.selected_product_id = c.lastrowid
                messagebox.showinfo("บันทึก", "เพิ่มสินค้าเรียบร้อย")
            else:
                c.execute(
                    "UPDATE products SET name=?, price=?, description=?, image_path=?, category=?, subcategory=?, stock=? WHERE id=?",
                    (name, price, desc, self.product_image_path, cat, sub, stock, self.selected_product_id)
                )
                conn.commit()
                messagebox.showinfo("บันทึก", "อัปเดตสินค้าเรียบร้อย")
        finally:
            conn.close()

        self._admin_refresh_products()
        self._admin_load_into_form(self.selected_product_id)

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
        _ = self._admin_create()  # เคลียร์ฟอร์ม

    # ----------- แสดงสินค้าในหน้า Main ตามตัวกรอง -----------
    def render_products(self):
        # เคลียร์เดิม
        for w in self.products_container.winfo_children():
            w.destroy()

        # ====== สร้าง query + params ตามตัวกรอง ======
        where = []
        params = []
        if getattr(self, "selected_category", "ทั้งหมด") != "ทั้งหมด":
            where.append("category = ?")
            params.append(self.selected_category)
            if getattr(self, "selected_subcategory", None):
                where.append("subcategory = ?")
                params.append(self.selected_subcategory)

        sql = "SELECT id, name, price, description, image_path, stock FROM products"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY id DESC"

        conn = sqlite3.connect(DB)
        c = conn.cursor()
        c.execute(sql, params)
        rows = c.fetchall()
        conn.close()

        if not rows:
            ctk.CTkLabel(self.products_container, text="(ยังไม่มีสินค้าในหมวดนี้)").pack(pady=12)
            return

        # helper ตัดข้อความ
        def _shorten(text, n=160):
            text = (text or "").strip()
            return text if len(text) <= n else text[:n-1] + "…"

        # ตรึงสถานะแอดมิน (True = แอดมิน → ไม่แสดงปุ่มตะกร้า)
        is_admin = bool(getattr(self, "is_admin", False))

        for pid, name, price, desc, img_path, stock in rows:
            card = ctk.CTkFrame(self.products_container, corner_radius=12)
            card.pack(fill="x", pady=8, padx=8)

            # รูปสินค้า
            img_label = ctk.CTkLabel(card, text="")
            img_label.pack(side="left", padx=10, pady=10)
            try:
                if img_path and os.path.exists(img_path):
                    im = Image.open(img_path); im.thumbnail((80, 80))
                    photo = ImageTk.PhotoImage(im)
                    img_label.configure(image=photo)
                    img_label.image = photo  # กัน GC
                else:
                    img_label.configure(text="(no image)")
            except Exception:
                img_label.configure(text="(no image)")

            # ข้อความรายละเอียด
            texts = ctk.CTkFrame(card, fg_color="transparent")
            texts.pack(side="left", fill="x", expand=True, padx=8, pady=10)
            ctk.CTkLabel(texts, text=f"{name}", font=("Arial", 14, "bold")).pack(anchor="w")
            ctk.CTkLabel(texts, text=f"{price:.2f} บาท").pack(anchor="w")
            ctk.CTkLabel(texts, text=f"สต็อกคงเหลือ: {int(stock)} ชิ้น").pack(anchor="w")
            ctk.CTkLabel(texts, text=_shorten(desc, 160), justify="left", anchor="w", wraplength=420)\
                .pack(anchor="w", pady=(2, 6))

            # ===== ปุ่มเพิ่มตะกร้า (แสดงเฉพาะผู้ใช้ทั่วไป) =====
            if not is_admin:
                btn_add = ctk.CTkButton(
                    card,
                    text="เพิ่มลงตะกร้า" if int(stock) > 0 else "สินค้าหมด",
                    width=120,
                    fg_color="#4CAF50" if int(stock) > 0 else "#9E9E9E",
                    text_color="white",
                    command=(lambda pid=pid, name=name, price=price: self.add_to_cart(pid, name, price, qty=1))
                            if int(stock) > 0 else None
                )
                btn_add.pack(side="right", padx=10)
                if int(stock) <= 0:
                    btn_add.configure(state="disabled")
            else:
                # โหมดแอดมิน: ไม่แสดงปุ่มเพิ่มตะกร้า
                ctk.CTkLabel(card, text="โหมดแอดมิน", text_color="#666666").pack(side="right", padx=10)