import tkinter as tk
import customtkinter as ctk
import requests
import socket
import threading
import concurrent.futures
from urllib.parse import urlparse, parse_qs

# Настройки стиля "Matrix"
MATRIX_GREEN = "#00FF41"
MATRIX_DARK = "#0A0A0A"
MATRIX_LOW_GREEN = "#002200"
MATRIX_HOVER = "#005F00"
TEXT_COLOR = "#D1FFD6"

class MTProtoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("MTproto_Harvester")
        self.geometry("850x750")
        self.configure(fg_color=MATRIX_DARK)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        # Переменные состояния
        self.is_checking = False
        self.stop_event = threading.Event()
        self.active_count = 0

        # Заголовок
        self.label_title = ctk.CTkLabel(
            self, 
            text="[ Down_the_proxies_Rabbit_Hole 🕳️🐇 v1.01 ]", 
            font=ctk.CTkFont(family="Courier New", size=26, weight="bold"),
            text_color=MATRIX_GREEN
        )
        self.label_title.pack(pady=(20, 10))

        # Контейнер для элементов управления
        self.control_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.control_frame.pack(fill="x", padx=40)

        self.btn_start = ctk.CTkButton(
            self.control_frame, 
            text="ENTER THE MATRIX", 
            command=self.start_checking,
            fg_color="transparent",
            border_color=MATRIX_GREEN,
            border_width=2,
            text_color=MATRIX_GREEN,
            hover_color=MATRIX_HOVER,
            font=ctk.CTkFont(family="Courier New", size=16, weight="bold"),
            height=45
        )
        self.btn_start.pack(expand=True, fill="x")

        # Информационная панель
        self.status_label = ctk.CTkLabel(
            self, 
            text="> System Idle... Ready to initialize.", 
            text_color=MATRIX_GREEN,
            font=ctk.CTkFont(family="Courier New", size=13)
        )
        self.status_label.pack(pady=(10, 5))

        # Список результатов (Scrollable Frame)
        self.result_frame = ctk.CTkScrollableFrame(
            self, 
            fg_color="#0D0D0D", 
            border_color=MATRIX_GREEN,
            border_width=1,
            label_text=" ACTIVE NODES FOUND (CLICK TO COPY) ",
            label_text_color=MATRIX_GREEN,
            label_font=ctk.CTkFont(family="Courier New", size=14, weight="bold")
        )
        self.result_frame.pack(expand=True, fill="both", padx=30, pady=(5, 10))

        # Индикатор копирования
        self.copy_notify = ctk.CTkLabel(
            self, 
            text="", 
            text_color=TEXT_COLOR,
            font=ctk.CTkFont(family="Courier New", size=12, weight="bold")
        )
        self.copy_notify.pack(pady=0)

        # Кнопка переключения логов
        self.btn_toggle_log = ctk.CTkButton(
            self,
            text="TOGGLE DEBUG LOGS",
            command=self.toggle_logs,
            fg_color=MATRIX_LOW_GREEN,
            text_color=MATRIX_GREEN,
            hover_color=MATRIX_HOVER,
            font=ctk.CTkFont(family="Courier New", size=12),
            height=25,
            width=150
        )
        self.btn_toggle_log.pack(pady=5)

        # Текстовое поле для логов (скрыто по умолчанию)
        self.log_visible = False
        self.log_box = ctk.CTkTextbox(
            self,
            fg_color="#050505",
            text_color="#00CC33",
            border_color=MATRIX_LOW_GREEN,
            border_width=1,
            font=ctk.CTkFont(family="Courier New", size=11),
            state="disabled"
        )

        # === ПАСХАЛКА / ВОТЕРМАРКА ===
        # Используем place, чтобы прикрепить её ровно в правый нижний угол
        self.watermark_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.watermark_frame.place(relx=1.0, rely=1.0, anchor="se", x=-15, y=-10)

        self.wm_label1 = ctk.CTkLabel(
            self.watermark_frame,
            text="I know kung fu | Tualatin",
            text_color=MATRIX_GREEN,
            font=ctk.CTkFont(family="Courier New", size=12, weight="bold")
        )
        self.wm_label1.pack(anchor="e")

        self.wm_label2 = ctk.CTkLabel(
            self.watermark_frame,
            text="[With love for free net by HDD40gb]",
            text_color="#00AA33", # Чуть более темный зеленый для акцента
            font=ctk.CTkFont(family="Courier New", size=10)
        )
        self.wm_label2.pack(anchor="e", pady=(0, 0))

    def on_closing(self):
        """Безопасное закрытие приложения и остановка потоков"""
        self.stop_event.set()
        self.destroy()

    def toggle_logs(self):
        """Показать/скрыть окно логов"""
        if self.log_visible:
            self.log_box.pack_forget()
            self.log_visible = False
        else:
            self.log_box.pack(expand=True, fill="both", padx=30, pady=(0, 20))
            self.log_visible = True

    def log(self, message):
        """Потокобезопасное добавление сообщений в лог"""
        self.after(0, self._append_log, message)

    def _append_log(self, message):
        """Внутренний метод для отрисовки лога"""
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{message}\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    def update_status(self, text):
        """Безопасное обновление статуса из любых потоков"""
        self.status_label.configure(text=f"> {text}")

    def parse_proxy_link(self, link):
        """Извлекает сервер, порт и секрет из ссылки"""
        try:
            link = link.strip()
            # Поддержка обоих форматов ссылок
            if "t.me/proxy" in link:
                query = link.split('?')[1] if '?' in link else ''
            else:
                parsed = urlparse(link)
                query = parsed.query

            params = parse_qs(query)
            
            server = params.get('server', [None])[0]
            port_str = params.get('port', [0])[0]
            secret = params.get('secret', [None])[0]

            if not server or not port_str:
                self.log(f"[WARN] Failed to extract server/port from: {link}")
                return None
                
            return {
                'server': server,
                'port': int(port_str),
                'secret': secret,
                'full_link': link
            }
        except Exception as e:
            self.log(f"[ERROR] Parse exception for {link}: {str(e)}")
            return None

    def check_connection(self, proxy):
        """TCP-пинг порта сервера"""
        if not proxy or not proxy.get('server') or not proxy.get('port'):
            return None
            
        server = proxy['server']
        port = proxy['port']
        
        try:
            # Создаем сокет, пытаемся подключиться. Таймаут 2.5 секунды
            with socket.create_connection((server, port), timeout=2.5):
                self.log(f"[+] ALIVE: {server}:{port} responded successfully.")
                return proxy
        except socket.timeout:
            self.log(f"[-] TIMEOUT: {server}:{port} (No response in 2.5s)")
            return None
        except ConnectionRefusedError:
            self.log(f"[-] REFUSED: {server}:{port} (Port closed/Connection refused)")
            return None
        except OSError as e:
            self.log(f"[-] ERROR: {server}:{port} - {str(e)}")
            return None

    def copy_to_clipboard(self, text_to_copy, item_type):
        """Копирует переданный текст и показывает уведомление"""
        self.clipboard_clear()
        self.clipboard_append(str(text_to_copy))
        self.copy_notify.configure(text=f"[ {item_type} SECURED IN CLIPBOARD ]", text_color=MATRIX_GREEN)
        self.after(2000, lambda: self.copy_notify.configure(text=""))

    def add_proxy_widget(self, proxy):
        """Добавляет рабочий прокси в UI-список с раздельными колонками"""
        
        # Создаем контейнер-строку для кнопок
        row_frame = ctk.CTkFrame(self.result_frame, fg_color="transparent")
        row_frame.pack(fill="x", pady=2, padx=5)

        # Вычисляем визуально обрезанный секрет, чтобы не ломать ширину интерфейса
        secret_display = proxy['secret']
        if secret_display and len(secret_display) > 12:
            secret_display = secret_display[:10] + "..."

        # 1. Кнопка сервера
        btn_server = ctk.CTkButton(
            row_frame,
            text=f"SRV: {proxy['server']}",
            anchor="w",
            fg_color=MATRIX_LOW_GREEN,
            border_color=MATRIX_HOVER,
            border_width=1,
            text_color=TEXT_COLOR,
            hover_color=MATRIX_HOVER,
            font=ctk.CTkFont(family="Courier New", size=12),
            command=lambda: self.copy_to_clipboard(proxy['server'], "SERVER")
        )
        btn_server.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # 2. Кнопка порта
        btn_port = ctk.CTkButton(
            row_frame,
            text=f"PORT: {proxy['port']}",
            width=80,
            fg_color=MATRIX_LOW_GREEN,
            border_color=MATRIX_HOVER,
            border_width=1,
            text_color=TEXT_COLOR,
            hover_color=MATRIX_HOVER,
            font=ctk.CTkFont(family="Courier New", size=12),
            command=lambda: self.copy_to_clipboard(proxy['port'], "PORT")
        )
        btn_port.pack(side="left", padx=(0, 5))

        # 3. Кнопка секрета
        btn_secret = ctk.CTkButton(
            row_frame,
            text=f"SEC: {secret_display}",
            width=130,
            fg_color=MATRIX_LOW_GREEN,
            border_color=MATRIX_HOVER,
            border_width=1,
            text_color=TEXT_COLOR,
            hover_color=MATRIX_HOVER,
            font=ctk.CTkFont(family="Courier New", size=12),
            command=lambda: self.copy_to_clipboard(proxy['secret'], "SECRET")
        )
        btn_secret.pack(side="right")

    def start_checking(self):
        if self.is_checking:
            return
        
        self.is_checking = True
        self.stop_event.clear()
        self.active_count = 0
        self.btn_start.configure(state="disabled", text="SCANNING NETWORK...")
        
        # Очищаем таблицу от старых результатов (и фреймы, и кнопки)
        for widget in self.result_frame.winfo_children():
            if isinstance(widget, (ctk.CTkButton, ctk.CTkFrame)):
                widget.destroy()
                
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        self.log("=== INITIATING MATRIX SCAN ===")

        # Запускаем парсинг и проверку в фоновом потоке
        threading.Thread(target=self.process_workflow, daemon=True).start()

    def process_workflow(self):
        try:
            self.after(0, self.update_status, "Downloading target list from mainframe...")
            url = "https://raw.githubusercontent.com/SoliSpirit/mtproto/master/all_proxies.txt"
            self.log(f"[*] Fetching proxy list from: {url}")
            
            # Скачиваем список с небольшим таймаутом
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            lines = response.text.splitlines()
            self.log(f"[*] Fetched {len(lines)} lines from source.")
            
            # Парсим ссылки (tg:// или https://t.me/proxy)
            raw_proxies = []
            for line in lines:
                if line.startswith('tg://') or 't.me/proxy' in line:
                    parsed = self.parse_proxy_link(line)
                    if parsed:
                        raw_proxies.append(parsed)
                        
            total_candidates = len(raw_proxies)
            self.log(f"[*] Successfully parsed {total_candidates} valid proxy links.")
            
            if total_candidates == 0:
                self.log("[!] WARNING: No valid proxies found to check! Source might be empty or format changed.")
                self.after(0, self.update_status, "Scan aborted. 0 candidates found.")
                return

            self.after(0, self.update_status, f"Found {total_candidates} targets. Initiating TCP handshake protocol...")
            self.log(f"[*] Starting concurrent checks with 60 workers...")

            # Многопоточная проверка с динамическим добавлением
            with concurrent.futures.ThreadPoolExecutor(max_workers=60) as executor:
                futures = {executor.submit(self.check_connection, p): p for p in raw_proxies}
                checked = 0
                
                for future in concurrent.futures.as_completed(futures):
                    if self.stop_event.is_set():
                        self.log("[!] Scan interrupted by user.")
                        break
                        
                    checked += 1
                    res = future.result()
                    
                    if res:
                        self.active_count += 1
                        self.after(0, self.add_proxy_widget, res)
                    
                    # Обновляем прогресс каждые 5 проверенных прокси
                    if checked % 5 == 0 or checked == total_candidates:
                        status_msg = f"Scanning: {checked}/{total_candidates} | Alive nodes: {self.active_count}"
                        self.after(0, self.update_status, status_msg)

            if not self.stop_event.is_set():
                self.log(f"=== SCAN COMPLETE. {self.active_count} ALIVE NODES ===")
                self.after(0, self.update_status, f"Scan complete. {self.active_count} nodes are successfully validated.")
            
        except requests.exceptions.RequestException as e:
            self.log(f"[FATAL] Network Error: Unable to fetch target list. Details: {str(e)}")
            self.after(0, self.update_status, f"Network Error: Unable to fetch target list.")
        except Exception as e:
            self.log(f"[FATAL] System Error: {str(e)}")
            self.after(0, self.update_status, f"System Error: {str(e)}")
        finally:
            if not self.stop_event.is_set():
                self.is_checking = False
                self.after(0, lambda: self.btn_start.configure(state="normal", text="RE-ENTER THE MATRIX"))

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = MTProtoApp()
    app.mainloop()