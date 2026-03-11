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


if __name__ == "__main__":
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("green")
    root = ctk.CTk()
    app = PharmaApp(root)
    root.mainloop()
# ----------------- Run -----------------