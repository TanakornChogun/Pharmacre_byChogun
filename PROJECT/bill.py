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