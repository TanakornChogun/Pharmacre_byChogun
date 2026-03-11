import sqlite3 
import customtkinter as ctk
from tkinter import messagebox
from PIL import Image, ImageTk
import re

DB = "pharmacy.db"

class BasketPage:
    def __init__(self, root):
        self.root = root
        self.root.title("PharmaCare - Basket Page")
        self.root.geometry("900x600")

        self.main_frame = ctk.CTkFrame(root, fg_color="transparent")
        self.main_frame.pack(fill="both", expand=True)

        self.show_basket_page()  # เรียกแสดงหน้า

    def show_basket_page(self):
        # ล้างของเก่า
        for w in self.main_frame.winfo_children():
            w.destroy()

        # พื้นหลัง
        img_bg = Image.open(r"c:\Users\Lenovo\OneDrive\เดสก์ท็อป\PROJECT\background basketpage.png")
        img_bg = img_bg.resize((1920, 1000))
        self.bg_photo = ImageTk.PhotoImage(img_bg)
        bg = ctk.CTkLabel(self.main_frame, image=self.bg_photo, text="")
        bg.place(relx=0, rely=0, relwidth=1, relheight=1)

        # กรอบเนื้อหา
        

        


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = BasketPage(root)
    root.mainloop()