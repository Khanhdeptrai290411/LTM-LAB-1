import os
import socket
import threading
from datetime import datetime
import customtkinter as ctk
from tkinter import messagebox

# Cấu hình CustomTkinter
ctk.set_appearance_mode("light")  # Giao diện tối
ctk.set_default_color_theme("green")  # Chủ đề màu

# Các biến toàn cục
clients = {}
client_names = {}
chat_history = {}
connection_times = {}

# Hàm cập nhật lịch sử chat
def update_chat_history(sender, recipient, message):
    """
    Cập nhật lịch sử chat cho hai người dùng (sender và recipient).
    """
    # Cập nhật lịch sử chat cho người gửi
    if sender not in chat_history:
        chat_history[sender] = []
    chat_history[sender].append(f"You to {recipient}: {message}")

    # Cập nhật lịch sử chat cho người nhận
    if recipient not in chat_history:
        chat_history[recipient] = []
    chat_history[recipient].append(f"{sender} (Private): {message}")

# Hàm gửi tin nhắn đến tất cả client
def broadcast(message, sender_socket=None):
    for client_socket in clients.values():
        if client_socket != sender_socket:
            try:
                client_socket.send(message.encode())
            except:
                client_socket.close()

# Xử lý từng client kết nối đến server
def handle_client(client_socket, addr):
    try:
        name = client_socket.recv(1024).decode()  # Nhận tên người dùng
        clients[name] = client_socket
        client_names[client_socket] = name
        connection_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        connection_times[name] = connection_time
        update_gui(f"{name} ({addr}) đã kết nối vào lúc {connection_time}.")
        
        # Gửi thông báo kết nối mới
        broadcast(f"{name} đã kết nối vào lúc {connection_time}")
        update_client_list()
        send_chat_history(client_socket, name)

        while True:
            try:
                message = client_socket.recv(1024).decode()  # Nhận tin nhắn từ client
                if message.startswith("/private"):
                    parts = message.split(" ", 2)
                    if len(parts) == 3:
                        _, recipient, private_message = parts
                        if recipient in clients:
                            clients[recipient].send(f"{name} (Private): {private_message}".encode())
                            client_socket.send(f"You (Private): {private_message}".encode())
                            update_chat_history(name, recipient, private_message)
                        else:
                            client_socket.send(f"Người dùng {recipient} không tồn tại.".encode())

                elif message == "/request_list":
                    send_client_list(client_socket)

                elif message.startswith("/send_file"):
                    parts = message.split(" ", 3)
                    if len(parts) == 4:
                        recipient, file_name, file_size = parts[1], parts[2], int(parts[3])
                        if recipient in clients:
                            file_path = receive_file(client_socket, recipient, file_name, file_size, name)
                            clients[recipient].send(f"/file {file_name} {file_size}".encode())  # Gửi thông báo về file
                        else:
                            client_socket.send(f"Người dùng {recipient} không tồn tại.".encode())

                else:
                    chat_history.setdefault(name, [])
                    chat_history[name].append(f"{name}: {message}")
                    broadcast(f"{name}: {message}", client_socket)
                    update_chat_history_gui(f"{name}: {message}")

            except Exception as e:
                print(f"Error handling client: {e}")
                break
    except Exception as e:
        print(f"Error: {e}")
    finally:
        update_gui(f"{name} đã ngắt kết nối.")
        broadcast(f"{name} đã ngắt kết nối")
        
        if name in clients:
            del clients[name]
        if client_socket in client_names:
            del client_names[client_socket]
            
        update_client_list()
        client_socket.close()

# Hàm nhận file
def receive_file(client_socket, recipient, file_name, file_size, sender):
    """
    Nhận file từ client và lưu lại tại server.
    """
    file_path = os.path.join("server_files", file_name)  # Tạo đường dẫn cho file

    # Kiểm tra xem thư mục 'server_files' đã tồn tại chưa, nếu chưa thì tạo mới.
    if not os.path.exists("server_files"):
        os.makedirs("server_files")

    # Nhận dữ liệu file từ client và ghi vào file.
    with open(file_path, "wb") as f:
        remaining = file_size
        while remaining > 0:
            chunk = client_socket.recv(min(1024, remaining))  # Nhận từng khối 1024 bytes
            if not chunk:
                break
            f.write(chunk)  # Ghi vào file
            remaining -= len(chunk)

    update_gui(f"Đã nhận file {file_name} từ {recipient}.")

    # Gửi thông báo tới người nhận rằng đã nhận file từ người gửi
    if recipient in clients:
        clients[recipient].send(f"Đã nhận file {file_name} từ {sender}.".encode())

    return file_path  # Trả về đường dẫn file đã lưu

# Hàm cập nhật danh sách người dùng
def update_client_list():
    other_users = list(clients.keys())
    for client_socket in list(client_names.keys()):
        client_list_str = "Danh sách người dùng: " + ",".join(other_users)
        try:
            client_socket.send(client_list_str.encode())
        except:
            client_socket.close()

# Gửi danh sách người dùng đến client
def send_client_list(client_socket):
    other_users = list(clients.keys())
    client_list_str = "Danh sách người dùng: " + ",".join(other_users)
    client_socket.send(client_list_str.encode())

# Gửi lịch sử chat cho client
def send_chat_history(client_socket, name):
    history_str = "Lịch sử chat:\n" + "\n".join(chat_history.get(name, []))
    client_socket.send(history_str.encode())

# Cập nhật giao diện CustomTkinter
def update_gui(message):
    chat_box.configure(state="normal")
    chat_box.insert(ctk.END, message + "\n")
    chat_box.configure(state="disabled")

# Cập nhật lịch sử chat trong giao diện
def update_chat_history_gui(message):
    chat_box.configure(state="normal")
    chat_box.insert(ctk.END, message + "\n")
    chat_box.configure(state="disabled")

# Khởi động server trong luồng nền
def start_server_background():
    threading.Thread(target=start_server, daemon=True).start()

# Hàm chạy server
def start_server():
    server_ip = '192.168.1.9'  # Địa chỉ IP của server
    PORT = 12345  # Cổng kết nối
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_ip, PORT))
    server_socket.listen(5)
    update_gui("Server đang lắng nghe...")

    while True:
        client_socket, addr = server_socket.accept()
        threading.Thread(target=handle_client, args=(client_socket, addr)).start()

# Giao diện CustomTkinter
root = ctk.CTk()
root.title("Chat Server")

# Khung lịch sử chat
chat_box = ctk.CTkTextbox(root, width=600, height=400, state="disabled")
chat_box.pack(pady=10)

# Nút bắt đầu server
start_button = ctk.CTkButton(root, text="Bắt đầu server", command=start_server_background)
start_button.pack()

# Khởi chạy giao diện
root.mainloop()
