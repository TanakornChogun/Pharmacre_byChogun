import sqlite3 
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk
import re

DB = "pharmacy.db"

class MainPage:
    def __init__(self, root):
        self.root = root
        self.root.title("PharmaCare - Main Page")
        self.root.geometry("900x600")
        self.main_frame = ctk.CTkFrame(root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)
        self.main_page("DemoUser")

    def main_page(self, username="Demo"):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        # ---------- Background ----------
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\NewBackground.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)


        # ปุ่มโปรไฟล์
        BackLogpage = ctk.CTkButton(
            self.main_frame,
            text ="🔙 Log out",
            fg_color="red",
            hover_color="darkgreen",
            text_color="white",
            #command=self.login_page
        )
        BackLogpage.place(relx=0.88, rely=0.95, anchor="e")



        # ปุ่มโปรไฟล์
        ProfileButton = ctk.CTkButton(
            self.main_frame,
            text="👤",
            width=50, height=50,
            fg_color="#dcff5f",
            hover_color="darkgreen",
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
        # ---------- Welcome Text ----------
        welcome = ctk.CTkLabel(
            self.main_frame,
            text=f"ยินดีต้อนรับ {username}",
            font=("Arial", 20, "bold"),
            text_color="black",
            fg_color="transparent"
        )
        welcome.place(relx=0.25, rely=0.09, anchor="e")

 #----------------------------------------------------------------------------------------------------------------------------------------------------------#
                       # ---------- Main Content ----------
        
        left_panel = ctk.CTkFrame(
            self.main_frame,
            width=200, 
            height=450, 
            corner_radius=10,
            bg_color="white"
            
        )
        left_panel.place(relx=0.22, rely=0.55, anchor="e")

        ctk.CTkLabel(left_panel, text="หมวดหมู่", font=("Arial", 16, "bold")).place(relx=0.5, rely=0.08, anchor="center")

        # กล่องประเภท (อยู่ข้างกล่องหมวดหมู่)
        type_panel = ctk.CTkFrame(
            self.main_frame, 
            width=200, 
            height=450, 
            corner_radius=10,
            bg_color="white"
            )
        type_panel.place(relx=0.355, rely=0.55, anchor="e")

        ctk.CTkLabel(type_panel, text="ประเภท", font=("Arial", 16, "bold")).place(relx=0.5, rely=0.08, anchor="center")


        # ----------------- ฟังก์ชันแสดงประเภท -----------------
        def show_types(category):
            # ล้างของเก่าในกล่องประเภท (type_panel)
            for widget in type_panel.winfo_children():
                if isinstance(widget, ctk.CTkLabel) and widget.cget("text") == "ประเภท":
                    continue
                widget.destroy()

            # เลือกประเภทตามหมวดหมู่
            if category == "เวชสำอาง":
                types = ["ครีมกันแดด", "โฟมล้างหน้า", "เซรั่ม", "มอยส์เจอร์ไรเซอร์"]
            elif category == "สินค้าเพื่อสุขภาพ":
                types = ["วิตามิน", "อาหารเสริม", "เครื่องวัดความดัน", "สมุนไพร"]
            elif category == "ยา":
                types = ["ยาแก้ปวด", "ยาลดไข้", "ยาแก้แพ้", "ยาฆ่าเชื้อ"]
            else:
                types = ["สินค้าทั้งหมด"]

            # แสดงหัวข้อหมวดหมู่ที่เลือก
            ctk.CTkLabel(type_panel, text=f"{category}", font=("Arial", 14, "bold"),bg_color="white").place(relx=0.5, rely=0.18, anchor="center")

            # แสดงปุ่มประเภท
            y = 0.3
            for t in types:
                ctk.CTkButton(type_panel, text=t, width=150).place(relx=0.5, rely=y, anchor="center")
                y += 0.1
        # ----------------- ปุ่มหมวดหมู่หลัก -----------------
        y = 0.25
        for cat in ["ทั้งหมด", "เวชสำอาง", "สินค้าเพื่อสุขภาพ", "ยา"]:
            ctk.CTkButton(left_panel, text=cat, width=150,
                        command=lambda c=cat: show_types(c)).place(relx=0.5, rely=y, anchor="center")
            y += 0.12

        
        center_panel = ctk.CTkFrame(
            self.main_frame,
            width=600, 
            height=450, 
            corner_radius=10,
            bg_color="white"
            )
        center_panel.place(relx=0.75, rely=0.55, anchor="e")

        ctk.CTkLabel(center_panel, text="สินค้า", font=("Arial", 16, "bold")).place(relx=0.5, rely=0.08, anchor="center")
        scrollab = ctk.CTkScrollableFrame(
            center_panel,
            width=540,
            height=380 
            
        )
        scrollab.place(relx=0.5, rely=0.55, anchor="center")

        right_panel = ctk.CTkFrame(
            self.main_frame,
            width=240, 
            height=450, 
            corner_radius=10,
            bg_color="white"
        )
        right_panel.place(relx=0.91, rely=0.55, anchor="e")

        ctk.CTkLabel(right_panel, text="ตะกร้าสินค้า", font=("Arial", 16, "bold")).place(relx=0.5, rely=0.08, anchor="center")
        basketframe = ctk.CTkTextbox(
            right_panel,
            width=220,
            height=220,
            bg_color="white"
        )
        basketframe.place(relx=0.5 , rely=0.38 , anchor="center")

        ชำระ=ctk.CTkButton(
            right_panel,
            text = "ชำระสินค้า",
            width=150,
            command=self.cart_page
        )
        ชำระ.place(relx=0.5, rely=0.7, anchor="center")




        


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

        BackButton = ctk.CTkButton(
            self.main_frame,
            text="🔙",
            width=50,
            height=50,
            fg_color="green",
            hover_color="darkgreen",
            text_color="white",
            command=self.main_page
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

        # ---------- ปุ่มย้อนกลับ ----------
        BackButton = ctk.CTkButton(
            self.main_frame,
            text="🔙",
            width=50,
            height=50,
            fg_color="green",
            hover_color="darkgreen",
            text_color="white",
            command=self.main_page
        )
        BackButton.place(relx=0.9, rely=0.15, anchor="e")

        ctk.CTkLabel(
            self.main_frame,
            text="ชื่อผู้ใช้ :",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.5,rely=0.3,anchor="center")

        ctk.CTkLabel(
            self.main_frame,
            text="    Email :",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.5,rely=0.4,anchor="center")

        ctk.CTkLabel(
            self.main_frame,
            text="      ที่อยู่ :",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.5,rely=0.5,anchor="center")

        ctk.CTkButton(
            self.main_frame,
            text="ติดต่อสอบถามเพิ่มเติม click here",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.65,rely=0.75,anchor="center")

        ctk.CTkLabel(
            self.main_frame,
            text=" สะสมแต้ม ",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.32,rely=0.65,anchor="center")

        ctk.CTkButton(
            self.main_frame,
            text="ประวัติการสั่งซื้อ click here",
            font=("Oswald", 18, "bold"),
            bg_color="#fefefe"
        ).place(relx=0.32,rely=0.75,anchor="center")

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

        # ปุ่มแก้ไข
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

        # ปุ่มบันทึก
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
        self.btn_save_addr.configure(state="disabled")  # เริ่มต้นปิดไว้ก่อน

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


#----------------------------------------------------------------------------------------------------------------------------------------------------------#
    


        

# ---------------- Run Demo ----------------
if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = MainPage(root)
    root.mainloop()


