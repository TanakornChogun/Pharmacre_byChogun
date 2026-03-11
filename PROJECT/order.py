def _create_order_and_go_payment(self, subtotal: float):
    # อ่าน input (อ่านให้ครบ *ก่อน* เปลี่ยนหน้า เพื่อลด invalid command name)
        address = self._addr_box_for_order.get("1.0", "end").strip() if hasattr(self, "_addr_box_for_order") else ""
        phone   = self._phone_entry.get().strip() if hasattr(self, "_phone_entry") else ""
        ship_method = self._ship_method_var.get() if hasattr(self, "_ship_method_var") else "Kerry"

        if not re.fullmatch(r"0\d{9}", phone):
            messagebox.showwarning("ข้อมูล", "กรุณากรอกเบอร์โทรให้ถูกต้อง (เช่น 0812345678)")
            return
        if not address or address.strip() in ("กรอกที่อยู่จัดส่งที่นี่", "กรอกที่อยู่จัดส่งที่นี่..."):
            messagebox.showwarning("ที่อยู่", "กรุณากรอกที่อยู่จัดส่ง")
            return
        if not self.cart:
            messagebox.showerror("ออเดอร์", "ตะกร้าว่าง")
            return

        # ค่าส่ง (ฟรีถ้า >=2 ชิ้น หรือ >=2 รายการ)
        _, total_qty = self._calc_cart_total()
        fees = {"Kerry": 40.0, "J&T": 40.0, "ไปรษณีย์ไทย": 40.0, "Flash": 40.0}
        ship_fee = 0.0 if (total_qty >= 2 or len(self.cart) >= 2) else fees.get(ship_method, 40.0)

        vat = round(subtotal * 0.04, 2)  # 4%
        grand_total = float(subtotal) + float(ship_fee) + float(vat)
        now = datetime.datetime.now().isoformat(timespec="seconds")

        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            # ensure column
            try:
                c.execute("ALTER TABLE orders ADD COLUMN contact_phone TEXT")
            except Exception:
                pass

            if getattr(self, "_current_order_id", None) is None:
                # ----- INSERT ครั้งแรก -----
                c.execute("""
                    INSERT INTO orders (
                        user_email, shipping_method, shipping_address, contact_phone,
                        total_price, status, shipping_status, created_at, updated_at
                    )
                    VALUES (?, ?, ?, ?, ?, 'pending', 'draft', ?, ?)
                """, (self.current_email, ship_method, address, phone, grand_total, now, now))
                order_id = c.lastrowid
                self._current_order_id = order_id
            else:
                # ----- UPDATE ออเดอร์เดิม -----
                order_id = self._current_order_id
                c.execute("""
                    UPDATE orders
                    SET shipping_method=?, shipping_address=?, contact_phone=?,
                        total_price=?, status='pending', shipping_status='draft', updated_at=?
                    WHERE id=?
                """, (ship_method, address, phone, grand_total, now, order_id))
                # เคลียร์รายการเดิมแล้วใส่ใหม่ให้ตรงกับตะกร้า
                c.execute("DELETE FROM order_items WHERE order_id=?", (order_id,))

            # ใส่รายการสินค้า
            for pid, it in self.cart.items():
                c.execute("""
                    INSERT INTO order_items (order_id, product_id, name, price, qty, line_total)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (order_id, pid, it["name"], float(it["price"]),
                    int(it["qty"]), float(it["price"]) * int(it["qty"])))
                
                


            conn.commit()

        except Exception as e:
            try: conn.rollback()
            except Exception: pass
            messagebox.showerror("ออเดอร์", f"ไม่สามารถบันทึกออเดอร์ได้:\n{e}")
            return
        finally:
            conn.close()

        # sync เบอร์/ที่อยู่กลับโปรไฟล์ (ไม่ทำหลังจากเปลี่ยนหน้าเพื่อลด invalid command name)
        try:
            conn = sqlite3.connect(DB); c = conn.cursor()
            c.execute("UPDATE users SET phone=?, address=? WHERE email=?", (phone, address, self.current_email))
            conn.commit()
        except Exception:
            pass
        finally:
            try: conn.close()
            except Exception: pass

        # ไปหน้า QR/อัปสลิป ด้วย order_id เดิม (ห้ามสร้างซ้ำใน Qrcode)
        self.Qrcode(order_id)



    def _export_invoice_image(self):
    #"""สร้างภาพ PNG ของบิลจากตะกร้าปัจจุบัน แล้วเปิดให้ทันที"""
        try:
            png_path, _ = self._build_invoice_bitmap()
            # เปิดภาพทันที
            try:
                abs_path = os.path.abspath(png_path)
                if os.name == "nt":
                    os.startfile(abs_path)          # Windows
                elif sys.platform == "darwin":
                    subprocess.call(["open", abs_path])  # macOS
                else:
                    subprocess.call(["xdg-open", abs_path])  # Linux
            except Exception:
                messagebox.showinfo("บันทึกบิล", f"บันทึก PNG แล้วที่:\n{png_path}")
        except Exception as e:
            messagebox.showerror("บันทึกบิล", f"ไม่สำเร็จ:\n{e}")


    def _export_invoice_pdf(self):
        """สร้าง PDF ของบิล (แปลงจาก PNG) แล้วเปิดให้ทันที"""
        try:
            png_path, img = self._build_invoice_bitmap()
            pdf_path = png_path.replace(".png", ".pdf")
            img.convert("RGB").save(pdf_path, "PDF", resolution=200.0)

            # เปิด PDF ทันที
            try:
                abs_pdf = os.path.abspath(pdf_path)
                if os.name == "nt":
                    os.startfile(abs_pdf)                 # Windows
                elif sys.platform == "darwin":
                    subprocess.call(["open", abs_pdf])    # macOS
                else:
                    subprocess.call(["xdg-open", abs_pdf])# Linux
            except Exception:
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
        fees = {"Kerry": 40.0, "J&T": 40.0, "ไปรษณีย์ไทย": 40.0, "Flash": 40.0}
        ship_method = self._ship_method_var.get() if hasattr(self, "_ship_method_var") else "Kerry"
        ship_fee = 0.0 if (total_qty >= 2 or len(self.cart) >= 2) else fees.get(ship_method, 40.0)
        vat = round(subtotal * 0.04, 2)
        grand = subtotal + ship_fee + vat

        # สร้างภาพพื้นฐาน
        W, H = 900, 1200
        img = Image.new("RGB", (W, H), "white")
        draw = ImageDraw.Draw(img)

        font_path = r"c:\USERS\LENOVO\APPDATA\LOCAL\MICROSOFT\WINDOWS\FONTS\SARABUN-MEDIUM.TTF"


        if os.path.exists(font_path):
            font_h1 = ImageFont.truetype(font_path, 28)
            font_h2 = ImageFont.truetype(font_path, 22)
            font_txt = ImageFont.truetype(font_path, 18)
        else:
            # กรณีฟอนต์หาไม่เจอ ยังให้แสดงข้อความได้
            font_h1 = font_h2 = font_txt = ImageFont.load_default()


        LOGO_PATH = r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\logo3.png"
        y = 20  # เริ่มห่างขอบบน
        if os.path.exists(LOGO_PATH):
            logo = Image.open(LOGO_PATH).convert("RGBA")
            logo = ImageOps.contain(logo, (160, 160))  # ย่อให้พอดี
            x_center = (W - logo.width) // 2
            img.paste(logo, (x_center, y), logo)
            y += logo.height + 12
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

        thanks = "ขอบคุณที่ไว้วางใจ PHARMACARE+"
        draw.text((40, H - 60), thanks, fill="black", font=font_txt)


        # เผื่อส่วนล่าง
        img.save(png_path)
        return png_path, img



#----------------------------------------------------------------------------------------------------------------------------------------------------------#

    def Qrcode(self, order_id=None):
        order_id = order_id or getattr(self, "_current_order_id", None)
        if not order_id:
            messagebox.showerror("ออเดอร์", "ไม่พบหมายเลขออเดอร์"); return

        self._current_order_id = order_id  # ยืนยันว่า context นี้ทำกับใบนี้

    # ... (render UI ตามเดิม)
    # ปุ่มยืนยันส่งสลิป: อย่า INSERT ออเดอร์ใหม่!
    # ตัวอย่าง:
    # confirm_btn = ctk.CTkButton(frame, text="ยืนยันสลิป", command=lambda: self._submit_payment(order_id))
    # confirm_btn.pack(...)

        for w in self.main_frame.winfo_children():
            w.destroy()

        # ---------- พื้นหลัง ----------
        try:
            img_path = r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\NewBG.png"
            ctk_img = ctk.CTkImage(light_image=Image.open(img_path), size=(1580, 810))
            bg = ctk.CTkLabel(self.main_frame, image=ctk_img, text="")
            bg.image = ctk_img
            bg.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as e:
            messagebox.showerror("Background", f"โหลดพื้นหลังไม่ได้:\n{e}")

        # ปุ่มย้อนกลับ
        ctk.CTkButton(self.main_frame, text="🔙", width=50, height=50,
                    fg_color="#d60000", hover_color="#f30505", text_color="white",
                    command=self.Confirm_items if hasattr(self, "Confirm_items") else self.cart_page)\
            .place(relx=0.99, rely=0.27, anchor="e")

        # ---------- คำนวณยอด (VAT4% + ค่าส่ง/ส่งฟรี) ----------
        subtotal = sum(float(it["price"])*int(it["qty"]) for it in self.cart.values())
        total_qty = sum(int(it["qty"]) for it in self.cart.values())
        free_ship = (total_qty >= 2) or (len(self.cart) >= 2)
        base_ship = 40.0  # ค่าส่งพื้นฐาน ถ้าไม่ฟรี
        ship_fee = 0.0 if free_ship else base_ship
        vat = round(subtotal * 0.04, 2)
        grand = round(subtotal + ship_fee + vat, 2)

        ctk.CTkLabel(self.main_frame, text="ขอบคุณที่ไว้วางใจ",
                    font=("Oswald", 36, "bold"), bg_color="#fefefe")\
            .place(relx=0.5, rely=0.27, anchor="center")

        info = (f"ยอดสินค้า: {subtotal:,.2f} บาท\n"
                f"VAT 4%: {vat:,.2f} บาท\n"
                f"ค่าส่ง: {'ฟรี' if ship_fee==0 else f'{ship_fee:,.2f} บาท'}\n"
                f"รวมชำระ: {grand:,.2f} บาท")
        ctk.CTkLabel(self.main_frame, text=info,
                    font=("Arial", 16, "bold"), bg_color="#fefefe", justify="left")\
            .place(relx=0.62, rely=0.38, anchor="center")

        # ---------- แสดง QR ----------
        try:
            img_qr = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\Qrcode.png").resize((360, 220))
            self.qr_photo = ImageTk.PhotoImage(img_qr)
            ctk.CTkLabel(self.main_frame, image=self.qr_photo, text="")\
                .place(relx=0.32, rely=0.52, anchor="center")
        except Exception:
            ctk.CTkLabel(self.main_frame, text="(ไม่พบไฟล์ Qrcode.png)", font=("Arial", 16, "bold"))\
                .place(relx=0.32, rely=0.52, anchor="center")

        # ---------- โซนอัปโหลดสลิป ----------
        slip_box = ctk.CTkFrame(self.main_frame, corner_radius=12, fg_color="white")
        slip_box.place(relx=0.62, rely=0.58, anchor="center", relwidth=0.30, relheight=0.22)

        ctk.CTkLabel(slip_box, text="อัปโหลดสลิปโอนเงิน", font=("Arial", 16, "bold")).pack(pady=(10, 6))
        self._slip_name_var = ctk.StringVar(value="ยังไม่เลือกไฟล์")
        ctk.CTkLabel(slip_box, textvariable=self._slip_name_var, text_color="#444").pack()

        def _choose_slip():
            from tkinter import filedialog
            fpath = filedialog.askopenfilename(
                title="เลือกไฟล์สลิป",
                filetypes=[("Images", "*.png;*.jpg;*.jpeg;*.webp;*.bmp;*.gif"), ("All files", "*.*")]
            )
            if not fpath:
                return
            self._pending_slip_path = fpath  # เก็บไว้ชั่วคราวก่อนกดยืนยัน
            self._slip_name_var.set(os.path.basename(fpath))

        ctk.CTkButton(slip_box, text="เลือกไฟล์...", fg_color="#0288D1",
                    text_color="white", command=_choose_slip).pack(pady=(8, 6))
        
        ctk.CTkButton(self.main_frame, text="ยืนยันชำระเงิน ✅",
            fg_color="green", text_color="white",
            font=("Oswald", 18, "bold"),
            command=self._submit_payment_now
        ).place(relx=0.62, rely=0.80, anchor="center")

        # ---------- ปุ่มยืนยันชำระเงิน ----------
    def _submit_payment_now(self):
    # ต้องมีสลิป
        slip_src = getattr(self, "_pending_slip_path", None)
        if not slip_src or not os.path.exists(slip_src):
            messagebox.showwarning("สลิป", "กรุณาแนบสลิปก่อนยืนยัน")
            return

        # ต้องมี order เดิมที่สร้างมาจาก _create_order_and_go_payment
        order_id = getattr(self, "_current_order_id", None)
        if not order_id:
            messagebox.showerror("ออเดอร์", "ไม่พบหมายเลขออเดอร์ (กรุณาคอนเฟิร์มสินค้าก่อน)")
            return

        now = datetime.datetime.now().isoformat(timespec="seconds")
        conn = sqlite3.connect(DB); c = conn.cursor()
        try:
            # 1) ดูสถานะเดิมไว้ก่อน เพื่อจะได้ "ตัดสต็อก" แค่ครั้งแรกที่เปลี่ยนเป็น submitted
            c.execute("SELECT status FROM orders WHERE id=?", (order_id,))
            row = c.fetchone()
            prev_status = row[0] if row else None

            # 2) เก็บไฟล์สลิปลงโฟลเดอร์โปรเจ็กต์
            os.makedirs("slips", exist_ok=True)
            ext = os.path.splitext(slip_src)[1].lower() or ".png"
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            slip_dst = os.path.join("slips", f"order_{order_id}_{ts}{ext}")
            shutil.copyfile(slip_src, slip_dst)

            # 3) อัปเดตออเดอร์เดิม → แนบสลิป + ปรับเป็น submitted (ไม่มี INSERT ออเดอร์ใหม่!!)
            c.execute(
                "UPDATE orders SET slip_path=?, status='submitted', updated_at=? WHERE id=?",
                (slip_dst, now, order_id)
            )

            # 4) ตัดสต็อกเฉพาะครั้งแรกที่เปลี่ยนเป็น submitted (กันตัดซ้ำ)
            if prev_status != "submitted":
                c.execute("SELECT product_id, qty FROM order_items WHERE order_id=?", (order_id,))
                for pid, qty in c.fetchall():
                    c.execute("UPDATE products SET stock = stock - ? WHERE id = ?", (int(qty), int(pid)))

            conn.commit()

            # (ถ้ามีระบบออกใบเสร็จ PDF เดิม) เรียกใช้ต่อได้
            # self._export_invoice_pdf()

        except Exception as e:
            conn.rollback()
            messagebox.showerror("ชำระเงิน", f"บันทึกสลิป/อัปเดตออเดอร์ล้มเหลว:\n{e}")
            return
        finally:
            conn.close()

        # 5) เคลียร์ตะกร้า + แจ้งผล + ไปหน้า History/หลัก เหมือนเดิม
        self.cart.clear()
        if hasattr(self, "_update_cart_summary"):
            try: self._update_cart_summary()
            except Exception: pass

        messagebox.showinfo("ส่งสลิปแล้ว", "ระบบได้รับสลิปแล้วค่ะ/ครับ\nสถานะ: รออนุมัติจากแอดมิน")
        try:
            self.History_page()
        except Exception:
            self.main_page(getattr(self, "current_username", "Guest"))o