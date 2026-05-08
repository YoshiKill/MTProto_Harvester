import tkinter as tk
import customtkinter as ctk
import requests
import threading
import concurrent.futures
import asyncio
import logging
import sys
import gc  # Импортируем сборщик мусора
from urllib.parse import urlparse, parse_qs

# ОПТИМИЗАЦИЯ ДЛЯ WINDOWS:
# Отключаем ProactorEventLoop, который вешает GIL при закрытии сокетов в многопоточности.
# Это уберет зависания интерфейса при переключении окон после сканирования.
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# Импорты для имитации реального клиента Telegram
from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate

# Глушим технические логи Telethon, чтобы не спамить в консоль
logging.getLogger('telethon').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Настройки стиля "Matrix"
MATRIX_GREEN = "#00FF41"
MATRIX_DARK = "#0A0A0A"
MATRIX_LOW_GREEN = "#002200"
MATRIX_HOVER = "#005F00"
TEXT_COLOR = "#D1FFD6"

# Цвета для скопированных элементов
COPIED_BG = "#550000"     # Темно-красный фон
COPIED_HOVER = "#770000"  # Красный фон при наведении
COPIED_TEXT = "#FF8888"   # Светло-красный текст

class MTProtoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Mproto_Harvester")
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
            text="[ Down_the_proxies_Rabbit_Hole 🕳️🐇 v1.09 ]", 
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
            text_color="#00AA33", 
            font=ctk.CTkFont(family="Courier New", size=10)
        )
        self.wm_label2.pack(anchor="e", pady=(0, 0))

    def on_closing(self):
        self.stop_event.set()
        self.destroy()

    def toggle_logs(self):
        if self.log_visible:
            self.log_box.pack_forget()
            self.log_visible = False
        else:
            self.log_box.pack(expand=True, fill="both", padx=30, pady=(0, 20))
            self.log_visible = True

    def log(self, message):
        self.after(0, self._append_log, message)

    def _append_log(self, message):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", f"{message}\n")
        self.log_box.configure(state="disabled")
        self.log_box.see("end")

    def update_status(self, text):
        self.status_label.configure(text=f"> {text}")

    def parse_proxy_link(self, link):
        try:
            link = link.strip()
            if "t.me/proxy" in link:
                query = link.split('?')[1] if '?' in link else ''
            else:
                parsed = urlparse(link)
                query = parsed.query

            params = parse_qs(query)
            
            server = params.get('server', [None])[0]
            port_str = params.get('port', [0])[0]
            secret = params.get('secret', [None])[0]

            if not server or not port_str or not secret:
                self.log(f"[WARN] Failed to extract server/port/secret from: {link}")
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
        """ УЛЬТИМАТИВНАЯ ПРОВЕРКА ЧЕРЕЗ TELETHON """
        if not proxy:
            return None
            
        server = proxy['server']
        port = proxy['port']
        secret = proxy['secret']
        
        async def _test_telethon():
            api_id = 4
            api_hash = '014b35b6184100b085b0d0572f9b5103'
            
            client = TelegramClient(
                MemorySession(),
                api_id,
                api_hash,
                proxy=(server, port, secret),
                connection=ConnectionTcpMTProxyRandomizedIntermediate
            )
            
            try:
                await asyncio.wait_for(client.connect(), timeout=5.0)
                if client.is_connected():
                    await client.disconnect()
                    return proxy
            except Exception:
                pass
            finally:
                if client.is_connected():
                    await client.disconnect()
            
            return None

        try:
            result = asyncio.run(_test_telethon())
            if result:
                self.log(f"[+] ALIVE (Verified by Telegram DC): {server}:{port}")
                return proxy
            else:
                self.log(f"[-] DEAD (No route to Telegram): {server}:{port}")
                return None
        except Exception as e:
            self.log(f"[-] ERROR: {server}:{port} - {str(e)}")
            return None

    def copy_to_clipboard(self, text_to_copy, item_type, widget=None):
        self.clipboard_clear()
        self.clipboard_append(str(text_to_copy))
        
        self.copy_notify.configure(text=f"[ {item_type} SECURED IN CLIPBOARD ]", text_color=MATRIX_GREEN)
        self.after(2000, lambda: self.copy_notify.configure(text=""))
        
        if widget:
            widget.configure(
                fg_color=COPIED_BG,
                hover_color=COPIED_HOVER,
                text_color=COPIED_TEXT,
                border_color=COPIED_HOVER
            )

    def add_proxy_widget(self, proxy):
        proxy_block = ctk.CTkFrame(
            self.result_frame, 
            fg_color="#080808", 
            border_color=MATRIX_LOW_GREEN, 
            border_width=1, 
            corner_radius=4
        )
        proxy_block.pack(fill="x", pady=5, padx=5)

        secret_display = proxy['secret']
        if secret_display and len(secret_display) > 12:
            secret_display = secret_display[:10] + "..."

        row_frame = ctk.CTkFrame(proxy_block, fg_color="transparent")
        row_frame.pack(fill="x", pady=(5, 0), padx=5)

        btn_server = ctk.CTkButton(
            row_frame,
            text=f"SRV: {proxy['server']}",
            anchor="w",
            fg_color=MATRIX_LOW_GREEN,
            border_color=MATRIX_HOVER,
            border_width=1,
            text_color=TEXT_COLOR,
            hover_color=MATRIX_HOVER,
            font=ctk.CTkFont(family="Courier New", size=12)
        )
        btn_server.configure(command=lambda b=btn_server: self.copy_to_clipboard(proxy['server'], "SERVER", b))
        btn_server.pack(side="left", fill="x", expand=True, padx=(0, 5))

        btn_port = ctk.CTkButton(
            row_frame,
            text=f"PORT: {proxy['port']}",
            width=80,
            fg_color=MATRIX_LOW_GREEN,
            border_color=MATRIX_HOVER,
            border_width=1,
            text_color=TEXT_COLOR,
            hover_color=MATRIX_HOVER,
            font=ctk.CTkFont(family="Courier New", size=12)
        )
        btn_port.configure(command=lambda b=btn_port: self.copy_to_clipboard(proxy['port'], "PORT", b))
        btn_port.pack(side="left", padx=(0, 5))

        btn_secret = ctk.CTkButton(
            row_frame,
            text=f"SEC: {secret_display}",
            width=130,
            fg_color=MATRIX_LOW_GREEN,
            border_color=MATRIX_HOVER,
            border_width=1,
            text_color=TEXT_COLOR,
            hover_color=MATRIX_HOVER,
            font=ctk.CTkFont(family="Courier New", size=12)
        )
        btn_secret.configure(command=lambda b=btn_secret: self.copy_to_clipboard(proxy['secret'], "SECRET", b))
        btn_secret.pack(side="right")

        lbl_or = ctk.CTkLabel(
            proxy_block, 
            text="[ OR FULL LINK ]", 
            text_color="#008822", 
            font=ctk.CTkFont(family="Courier New", size=10, weight="bold")
        )
        lbl_or.pack(pady=(2, 0))

        full_https_link = f"https://t.me/proxy?server={proxy['server']}&port={proxy['port']}&secret={proxy['secret']}"
        
        display_full_link = full_https_link if len(full_https_link) < 85 else full_https_link[:82] + "..."

        btn_full_link = ctk.CTkButton(
            proxy_block,
            text=display_full_link,
            fg_color=MATRIX_LOW_GREEN,
            border_color=MATRIX_HOVER,
            border_width=1,
            text_color=TEXT_COLOR,
            hover_color=MATRIX_HOVER,
            font=ctk.CTkFont(family="Courier New", size=11)
        )
        btn_full_link.configure(command=lambda b=btn_full_link: self.copy_to_clipboard(full_https_link, "FULL LINK", b))
        btn_full_link.pack(fill="x", pady=(0, 5), padx=5)

    def start_checking(self):
        if self.is_checking:
            return
        
        self.is_checking = True
        self.stop_event.clear()
        self.active_count = 0
        self.btn_start.configure(state="disabled", text="SCANNING NETWORK...")
        
        for widget in self.result_frame.winfo_children():
            if isinstance(widget, (ctk.CTkButton, ctk.CTkFrame)):
                widget.destroy()
                
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")

        self.log("=== INITIATING MATRIX SCAN ===")

        threading.Thread(target=self.process_workflow, daemon=True).start()

    def process_workflow(self):
        try:
            self.after(0, self.update_status, "Downloading target list from mainframe...")
            url = "https://raw.githubusercontent.com/SoliSpirit/mtproto/master/all_proxies.txt"
            self.log(f"[*] Fetching proxy list from: {url}")
            
            response = requests.get(url, timeout=15)
            response.raise_for_status()
            
            lines = response.text.splitlines()
            self.log(f"[*] Fetched {len(lines)} lines from source.")
            
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

            self.after(0, self.update_status, f"Found {total_candidates} targets. Initiating Telegram DC routing check...")
            
            self.log(f"[*] Starting concurrent checks with 25 workers...")

            with concurrent.futures.ThreadPoolExecutor(max_workers=25) as executor:
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
                    
                    if checked % 5 == 0 or checked == total_candidates:
                        status_msg = f"Scanning: {checked}/{total_candidates} | Alive nodes: {self.active_count}"
                        self.after(0, self.update_status, status_msg)

                # Очищаем ссылки на объекты futures из памяти сразу после цикла
                futures.clear()

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
            
            # ОПТИМИЗАЦИЯ СБОРЩИКА МУСОРА (GC) ДЛЯ WINDOWS
            # Принудительно очищаем память от сотен мертвых объектов Telethon и asyncio сокетов 
            # прямо сейчас, в фоновом потоке, до того как пользователь начнет кликать по окну.
            # Это полностью исключает зависание интерфейса при переключении на Telegram.
            try:
                raw_proxies.clear()
                gc.collect()
            except Exception:
                pass

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = MTProtoApp()
    app.mainloop()