import customtkinter as ctk
from tkinter import messagebox

# -------------------------------
# ตั้งค่าเบื้องต้น
# -------------------------------
ctk.set_appearance_mode("light")  # โหมด light/dark
ctk.set_default_color_theme("blue")  # ธีมสี

app = ctk.CTk()
app.title("PharmaCare+")
app.geometry("600x400")

# -------------------------------
# ข้อมูลสินค้า
# -------------------------------
products = {
    "เสื้อยืด": 250,
    "กางเกงยีนส์": 800,
    "รองเท้า": 1200,
    "หมวก": 150,
    "กระเป๋า": 500
}

cart = {}  # เก็บสินค้าในตะกร้า


# -------------------------------
# ฟังก์ชัน
# -------------------------------
def add_to_cart(item):
    if item in cart:
        cart[item] += 1
    else:
        cart[item] = 1
    update_cart()


def update_cart():
    cart_list.delete("1.0", "end")
    total = 0
    for item, qty in cart.items():
        price = products[item] * qty
        total += price
        cart_list.insert("end", f"{item} x{qty} = {price} บาท\n")
    total_label.configure(text=f"ราคารวม: {total} บาท")


def checkout():
    if not cart:
        messagebox.showinfo("ตะกร้าว่าง", "กรุณาเลือกสินค้าก่อนชำระเงิน")
        return
    total = sum(products[item] * qty for item, qty in cart.items())
    messagebox.showinfo("การชำระเงิน", f"ยอดรวมที่ต้องชำระ: {total} บาท\nขอบคุณที่อุดหนุน!")
    cart.clear()
    update_cart()


# -------------------------------
# ส่วนแสดงสินค้า
# -------------------------------
frame_products = ctk.CTkFrame(app)
frame_products.pack(side="left", fill="both", expand=True, padx=10, pady=10)

ctk.CTkLabel(frame_products, text="สินค้า", font=("TH Sarabun New", 20, "bold")).pack(pady=5)

for item, price in products.items():
    btn = ctk.CTkButton(
        frame_products,
        text=f"{item} - {price} บาท",
        command=lambda i=item: add_to_cart(i),
        corner_radius=15
    )
    btn.pack(pady=5, fill="x")


# -------------------------------
# ส่วนตะกร้า
# -------------------------------
frame_cart = ctk.CTkFrame(app)
frame_cart.pack(side="right", fill="both", expand=True, padx=10, pady=10)

ctk.CTkLabel(frame_cart, text="ตะกร้าสินค้า", font=("TH Sarabun New", 20, "bold")).pack(pady=5)

cart_list = ctk.CTkTextbox(frame_cart, width=250, height=200)
cart_list.pack(pady=5)

total_label = ctk.CTkLabel(frame_cart, text="ราคารวม: 0 บาท", font=("TH Sarabun New", 16, "bold"))
total_label.pack(pady=5)

checkout_btn = ctk.CTkButton(frame_cart, text="ชำระเงิน", command=checkout, fg_color="green")
checkout_btn.pack(pady=5)

# -------------------------------
# รันโปรแกรม
# -------------------------------
app.mainloop()
