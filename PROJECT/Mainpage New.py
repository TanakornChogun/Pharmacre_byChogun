import sqlite3
import customtkinter as ctk
from tkinter import messagebox, filedialog
import hashlib, os, datetime, qrcode, re, shutil
from io import BytesIO
from PIL import Image, ImageTk, ImageOps

#DB = "pharmacy.db"

class PharmaApp:
    def __init__(self, root):
        self.root = root
        self.root.title("PharmaCare Login")
        self.root.geometry("1720x880")
        self.main_frame = ctk.CTkFrame(root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)

    def Main_page(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

        try:
            img_path = r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\NewBG.png"
            # ใช้ CTkImage เพื่อให้ภาพคมและสเกลอัตโนมัติ
            ctk_img = ctk.CTkImage(light_image=Image.open(img_path), size=(1580, 810))
            self.bg_label = ctk.CTkLabel(self.main_frame, image=ctk_img, text="")
            self.bg_label.image = ctk_img   # กัน GC
            self.bg_label.place(relx=0, rely=0, relwidth=1, relheight=1)
        except Exception as e:
            messagebox.showerror("Background", f"โหลดรูปพื้นหลังไม่สำเร็จ:\n{e}")


        Profile = ctk.CTkButton(
            self.main_frame,
                text="👤",
                width=50, height=50,
                fg_color="#0f057a",
                hover_color="#55ccff",
                text_color="white",
                #command=self.Profile_Page
        )
        Profile.place(relx=0.99, rely=0.27, anchor="e")

        BusketButton = ctk.CTkButton(
                self.main_frame,
                text="🛒",
                width=50,
                height=50,
                fg_color="#0f057a",
                hover_color="#55ccff",
                text_color="white",
                #command=self.cart_page
        )
        BusketButton.place(relx=0.95, rely=0.27, anchor="e")

        welcome = ctk.CTkLabel(
            self.main_frame,
            text=f"ยินดีต้อนรับ ",
            font=("Arial", 20, "bold"),
            text_color="black",
            fg_color="white",
            #fg_color="transparent"
        )
        welcome.place(relx=0.1, rely=0.27, anchor="e")

        BackToLogin = ctk.CTkButton(
            content_frame,
            text ="🔙 Log out",
            fg_color="#E50808",
            hover_color="#5e0303",
            text_color="white",
            #command=self._logout
        )
        BackToLogin.place(relx=0.99, rely=0.8, anchor="e")


        content_frame = ctk.CTkFrame(
            self.main_frame, 
            fg_color="white", 
            corner_radius=20,
            bg_color="white",
            width=1530,
            height=550
        )
        content_frame.place(relx=0.5,rely=0.65,anchor="center")

        center = ctk.CTkScrollableFrame(
            content_frame,
            width=1030,
            height=510,
            fg_color="white"
        )
        center.place(relx=0.54,rely=0.52,anchor="center")

        

        left = ctk.CTkFrame(
            content_frame,
            width=270,
            height=510,
            fg_color="#d3f2ff",
            bg_color="#d3f2ff"

        )
        left.place(relx=0.1,rely=0.51,anchor="center")
        
        ctk.CTkLabel(left, text="หมวดหมู่", font=("Arial", 16, "bold")).pack(pady=10)

        right = ctk.CTkFrame(
            content_frame,
            width=150,
            height=300,
            fg_color="#d3f2ff",
            bg_color="#d3f2ff"

        )
        right.place(relx=0.94,rely=0.38,anchor="center")

        










if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = PharmaApp(root)
    app.Main_page()  # ← สำคัญ
    root.mainloop()
