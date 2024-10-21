import os
import socket
import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import simpledialog, filedialog
# Global variables
client_name = None
client_socket = None
chat_history = {}
current_recipient = None

def receive_messages(client_socket):
    while True:
        try:
            message = client_socket.recv(1024).decode('utf-8')
            if message.startswith("/file"):
                parts = message.split(" ")
                file_name = parts[1]
                file_size = int(parts[2])

                # Hỏi người dùng vị trí lưu file
                save_path = filedialog.asksaveasfilename(defaultextension=".dat",
                                                       filetypes=[("All Files", "*.*")],
                                                       initialfile=file_name)

                if save_path:
                    remaining = file_size
                    with open(save_path, "wb") as f:
                        while remaining > 0:
                            chunk = client_socket.recv(min(1024, remaining))
                            f.write(chunk)
                            remaining -= len(chunk)
                    add_message_to_chat("Server", f"Đã tải file về {save_path}", "left")
            
            # Hiển thị thông báo nhận file
            elif message.startswith("Đã nhận file"):
                add_message_to_chat("Server", message, "left")

            elif message.startswith("Danh sách người dùng:"):
                update_client_list(message)
            elif message.startswith("Lịch sử chat:"):
                for widget in message_frame.winfo_children():
                    widget.destroy()

                chat_history = message.split(": ")[1]
                for msg in chat_history.split("\n"):
                    if msg.strip():
                        add_message_to_chat("System", msg, "left")
            elif "Private" in message:
                handle_private_message(message)
            else:
                add_message_to_chat("Server", message, "left")
        
        except Exception as e:
            print(f"Error receiving message: {e}")
            break

def handle_private_message(message):
    sender, msg = message.split(" (Private): ", 1)
    if sender not in chat_history:
        chat_history[sender] = []
    chat_history[sender].append(f"{sender}: {msg}")
    
    # Hiển thị tin nhắn nếu đang trong phòng chat với người gửi
    if current_recipient == sender:
        update_chat_box(sender)

def update_chat_box(recipient):
    # Clear previous messages in the message frame
    for widget in message_frame.winfo_children():
        widget.destroy()  # Remove old messages

    # Add chat history messages
    if recipient in chat_history:
        for entry in chat_history[recipient]:
            sender, msg = entry.split(": ", 1)
            alignment = "left" if sender != "You" else "right"
            add_message_to_chat(sender, msg, alignment)

def update_client_list(message):
    client_list.delete(0, tk.END)  # Xóa danh sách cũ
    users = message.split(": ")[1].split(",")  # Tách danh sách người dùng
    for user in users:
        user = user.strip()
        if user and user != client_name:
            client_list.insert(tk.END, user)

def on_user_select(event):
    global current_recipient
    selection = client_list.curselection()  # Get the selected user
    if selection:
        current_recipient = client_list.get(selection[0])
        update_chat_box(current_recipient)

def send_message():
    if current_recipient:
        message = message_entry.get()
        client_socket.send(f"/private {current_recipient} {message}".encode())
        
        # Add to local chat history
        if current_recipient not in chat_history:
            chat_history[current_recipient] = []
        chat_history[current_recipient].append(f"You: {message}")
        
        # Add your message to the chat (aligned to the right)
        add_message_to_chat("You", message, "right")
    
    # Clear the input field
    message_entry.delete(0, ctk.END)

def send_file():
    file_path = filedialog.askopenfilename()  # Chọn file để gửi
    if file_path:
        recipient = client_list.get(tk.ACTIVE)
        if recipient:
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            
            # Gửi thông tin file trước
            client_socket.send(f"/send_file {recipient} {file_name} {file_size}".encode())
            
            # Bắt đầu gửi dữ liệu file
            with open(file_path, "rb") as f:
                while (data := f.read(1024)):
                    client_socket.sendall(data)  # Gửi từng khối dữ liệu 1024 bytes
                
            add_message_to_chat("You", f"Đã gửi file {file_name} ({file_size} bytes)", "right")
            print(f"Đã gửi file {file_name} ({file_size} bytes) tới {recipient}")

def request_client_list():
    client_socket.send("/request_list".encode('utf-8')) 

def add_message_to_chat(sender, message, alignment):
    if alignment == 'right':
        fg_color = "#4a90e2"  
        anchor = "e"  
    else:
        fg_color = "#808080"  
        anchor = "w"  

    # Kiểm tra nếu message là tên file
    if message.endswith(('.txt', '.png', '.jpg', '.pdf', '.docx', '.dat')):  # Định dạng file tùy bạn mở rộng thêm
        # Tạo label có thể click vào để tải file
        msg_label = ctk.CTkLabel(message_frame, text=f"{message}", wraplength=300,
                                 fg_color=fg_color, text_color="blue",  # Đổi màu chữ để nhìn rõ là file
                                 corner_radius=16, width=200, anchor=anchor)
        msg_label.pack(padx=10, pady=5, anchor=anchor)
        
        # Gắn sự kiện click để tải file
        msg_label.bind("<Button-1>", lambda e: download_file(message))
    else:
        # Xử lý tin nhắn bình thường
        msg_label = ctk.CTkLabel(message_frame, text=f"{message}", wraplength=300,
                                 fg_color=fg_color, text_color="white",
                                 corner_radius=16, width=200, anchor=anchor)
        msg_label.pack(padx=10, pady=5, anchor=anchor)
    
    # Cập nhật khung chat
    message_frame.update_idletasks()
    message_frame._parent_canvas.yview_moveto(1)
def download_file(file_name):
    # Yêu cầu chọn thư mục để lưu file
    save_dir = filedialog.askdirectory()  # Người dùng chọn thư mục lưu
    if save_dir:
        save_path = os.path.join(save_dir, file_name)
        with open(save_path, "wb") as f:
            while True:
                data = client_socket.recv(1024)
                if not data:
                    break
                f.write(data)
        add_message_to_chat("Server", f"Đã tải file về {save_path}", "left")
def start_client():
    HOST = '192.168.1.9'
    global client_socket, client_name
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect((HOST, 12345))
    
    client_name = simpledialog.askstring("Tên người dùng", "Nhập tên của bạn:")
    if client_name:
        client_socket.send(client_name.encode())
        label_name.configure(text=f"Tên người dùng: {client_name}")
        request_client_list()
    thread = threading.Thread(target=receive_messages, args=(client_socket,))
    thread.start()
    
# Tạo giao diện Tkinter
root = ctk.CTk()
root.title("Chat Application")

# Cấu hình bố cục lưới cho root
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

# Frame bên trái: Danh sách người dùng
user_list_frame = ctk.CTkFrame(root, fg_color="#B1CAE9", width=200)
user_list_frame.grid(row=0, column=0, sticky="nsew")

client_list_label = ctk.CTkLabel(user_list_frame, text="Danh sách người dùng:")
client_list_label.pack(pady=10)

client_list = tk.Listbox(user_list_frame,width=25, height=15,font=("Arial", 15))  # Use tk.Listbox for selection
client_list.pack(fill="both", expand=True, padx=10, pady=10)
client_list.bind('<<ListboxSelect>>', on_user_select) 

update_button = ctk.CTkButton(user_list_frame, text="Cập nhật", command=request_client_list)
update_button.pack(pady=10)

# Frame bên phải: Khung chat
chat_frame = ctk.CTkFrame(root, fg_color="#F5F5F5")
chat_frame.grid(row=0, column=1, sticky="nsew")

label_name = ctk.CTkLabel(chat_frame, text=f"Tên người dùng: {client_name}")
label_name.pack(pady=10)

message_frame = ctk.CTkScrollableFrame(chat_frame, height=400,fg_color="#FFFFFF")
message_frame.pack(fill="both", expand=True, padx=10, pady=10)

message_entry_frame = ctk.CTkFrame(chat_frame)  # Separate frame for input and buttons
message_entry_frame.pack(fill="x", padx=10, pady=10)

message_entry = ctk.CTkEntry(message_entry_frame, width=250)
message_entry.pack(side="left", padx=10, pady=10)

send_button = ctk.CTkButton(message_entry_frame, text="Gửi", command=send_message)
send_button.pack(side="left", padx=10)

file_button = ctk.CTkButton(message_entry_frame, text="Gửi tệp", command=send_file)
file_button.pack(side="left", padx=10)

# Bắt đầu client
start_client()

root.mainloop()