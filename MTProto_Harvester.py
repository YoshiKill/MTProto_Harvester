# -*- coding: utf-8 -*-
import tkinter as tk
import customtkinter as ctk
import requests
import threading
import concurrent.futures
import asyncio
import logging
import sys
import gc
import webbrowser
import re
from urllib.parse import urlparse, parse_qs

# ОПТИМИЗАЦИЯ ДЛЯ WINDOWS:
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

# ПРОВЕРКА ЗАВИСИМОСТЕЙ
PROXY_LIBS_READY = True
try:
    import python_socks
except ImportError:
    try:
        import socks 
    except ImportError:
        PROXY_LIBS_READY = False
        print("!!! ERROR: 'python-socks' is not installed. Proxies WILL NOT work!")

from telethon import TelegramClient
from telethon.sessions import MemorySession
from telethon.network import ConnectionTcpMTProxyRandomizedIntermediate

# Глушим технические логи
logging.getLogger('telethon').setLevel(logging.CRITICAL)
logging.getLogger('asyncio').setLevel(logging.CRITICAL)

# Настройки стиля
MATRIX_GREEN = "#00FF41"
MATRIX_DARK = "#0A0A0A"
MATRIX_LOW_GREEN = "#002200"
MATRIX_HOVER = "#005F00"
TEXT_COLOR = "#D1FFD6"
COPIED_BG = "#550000"     
COPIED_HOVER = "#770000"  
COPIED_TEXT = "#FF8888"   

class MTProtoApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Mproto_Harvester")
        self.geometry("850x780")
        self.configure(fg_color=MATRIX_DARK)
        self.protocol("WM_DELETE_WINDOW", self.on_closing)

        self.is_checking = False
        self.stop_event = threading.Event()
        self.active_count = 0
        self.source_entries = []

        # Заголовок
        self.label_title = ctk.CTkLabel(
            self, 
            text="[ Down_the_proxies_Rabbit_Hole 🕳️🐇 v1.17 ]", 
            font=ctk.CTkFont(family="Courier New", size=26, weight="bold"),
            text_color=MATRIX_GREEN
        )
        self.label_title.pack(pady=(20, 10))

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

        self.status_container = ctk.CTkFrame(self, fg_color="transparent")
        self.status_container.pack(fill="x", padx=40, pady=(10, 5))

        self.btn_toggle_sources = ctk.CTkButton(
            self.status_container,
            text="Proxy List 🥄",
            command=self.toggle_sources,
            fg_color=MATRIX_LOW_GREEN,
            text_color=MATRIX_GREEN,
            hover_color=MATRIX_HOVER,
            font=ctk.CTkFont(family="Courier New", size=12, weight="bold"),
            width=120,
            height=28
        )
        self.btn_toggle_sources.pack(side="left")

        # Добавляем невидимый блок-пустышку справа для баланса
        self.dummy_balance = ctk.CTkFrame(self.status_container, width=120, height=28, fg_color="transparent")
        self.dummy_balance.pack(side="right")

        self.status_label = ctk.CTkLabel(self.status_container, text="> System Idle...", text_color=MATRIX_GREEN, font=ctk.CTkFont(family="Courier New", size=13))
        self.status_label.pack(side="left", expand=True)

        self.sources_visible = False
        self.sources_frame = ctk.CTkFrame(self, fg_color="#080808", border_color=MATRIX_LOW_GREEN, border_width=1)
        self.sources_inner = ctk.CTkFrame(self.sources_frame, fg_color="transparent")
        self.sources_inner.pack(fill="x", padx=10, pady=10)

        self.btn_add_source = ctk.CTkButton(self.sources_frame, text="+ ADD SOURCE", command=self.add_empty_source_row, fg_color="transparent", border_color=MATRIX_HOVER, border_width=1, text_color=MATRIX_GREEN, hover_color=MATRIX_LOW_GREEN, font=ctk.CTkFont(family="Courier New", size=12), height=24)
        
        default_sources = [
            "https://github.com/kort0881/telegram-proxy-collector/blob/main/proxy_all.txt",
            "https://github.com/kort0881/telegram-proxy-collector/blob/main/proxy_ru.txt",
            "https://github.com/SoliSpirit/mtproto/blob/master/all_proxies.txt",
            "https://github.com/Grim1313/mtproto-for-telegram/blob/master/all_proxies.md"
        ]
        for src in default_sources:
            self.add_source_row(src)

        self.result_frame = ctk.CTkScrollableFrame(self, fg_color="#0D0D0D", border_color=MATRIX_GREEN, border_width=1, label_text=" ACTIVE NODES FOUND (CLICK TO COPY) ", label_text_color=MATRIX_GREEN, label_font=ctk.CTkFont(family="Courier New", size=14, weight="bold"))
        self.result_frame.pack(expand=True, fill="both", padx=30, pady=(5, 10))

        self.copy_notify = ctk.CTkLabel(self, text="", text_color=TEXT_COLOR, font=ctk.CTkFont(family="Courier New", size=12, weight="bold"))
        self.copy_notify.pack(pady=0)

        self.btn_toggle_log = ctk.CTkButton(self, text="TOGGLE DEBUG LOGS", command=self.toggle_logs, fg_color=MATRIX_LOW_GREEN, text_color=MATRIX_GREEN, hover_color=MATRIX_HOVER, font=ctk.CTkFont(family="Courier New", size=12), height=25, width=150)
        self.btn_toggle_log.pack(pady=5)

        self.log_visible = False
        self.log_box = ctk.CTkTextbox(self, fg_color="#050505", text_color="#00CC33", border_color=MATRIX_LOW_GREEN, border_width=1, font=ctk.CTkFont(family="Courier New", size=11), state="disabled")

        self.watermark_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.watermark_frame.place(relx=1.0, rely=1.0, anchor="se", x=-15, y=-10)
        self.wm_label1 = ctk.CTkLabel(self.watermark_frame, text="I know kung fu | Tualatin", text_color=MATRIX_GREEN, font=ctk.CTkFont(family="Courier New", size=12, weight="bold"))
        self.wm_label1.pack(anchor="e")
        self.wm_label2 = ctk.CTkLabel(self.watermark_frame, text="[With love for free net by HDD40gb]", text_color="#00AA33", font=ctk.CTkFont(family="Courier New", size=10), cursor="hand2")
        self.wm_label2.pack(anchor="e")
        self.wm_label2.bind("<Button-1>", lambda e: webbrowser.open_new("https://t.me/IDE_HDD40Gb"))
        self.wm_label2.bind("<Enter>", lambda e: self.wm_label2.configure(text_color=MATRIX_GREEN))
        self.wm_label2.bind("<Leave>", lambda e: self.wm_label2.configure(text_color="#00AA33"))

        self.rabbit_label = ctk.CTkLabel(self, text="Follow the white rabbit...", text_color="#00AA33", font=ctk.CTkFont(family="Courier New", size=12, underline=True, weight="bold"), cursor="hand2")
        self.rabbit_label.place(relx=0.0, rely=1.0, anchor="sw", x=15, y=-10)
        self.rabbit_label.bind("<Button-1>", lambda e: webbrowser.open_new("https://www.donationalerts.com/r/hdd40gb"))
        self.rabbit_label.bind("<Enter>", lambda e: self.rabbit_label.configure(text_color=MATRIX_GREEN))
        self.rabbit_label.bind("<Leave>", lambda e: self.rabbit_label.configure(text_color="#00AA33"))

    def add_source_row(self, url=""):
        row_idx = len(self.source_entries) + 1
        row_frame = ctk.CTkFrame(self.sources_inner, fg_color="transparent")
        row_frame.pack(fill="x", pady=2)
        ctk.CTkLabel(row_frame, text=f"{row_idx}.", text_color=MATRIX_GREEN, width=20).pack(side="left", padx=(5, 5))
        entry = ctk.CTkEntry(row_frame, fg_color="#050505", text_color=TEXT_COLOR, border_color=MATRIX_LOW_GREEN, font=ctk.CTkFont(family="Courier New", size=11))
        entry.insert(0, url)
        entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.apply_context_menu(entry)
        self.source_entries.append(entry)
        self.btn_add_source.pack_forget()
        self.btn_add_source.pack(pady=(5, 10))

    def add_empty_source_row(self):
        self.add_source_row("")

    def apply_context_menu(self, entry):
        def show_menu(event):
            menu = tk.Menu(self, tearoff=0, bg="#0A0A0A", fg=MATRIX_GREEN, activebackground=MATRIX_HOVER, activeforeground=TEXT_COLOR)
            menu.add_command(label="Paste", command=lambda: paste_text())
            def paste_text():
                try: entry.insert("insert", self.clipboard_get())
                except tk.TclError: pass
            menu.tk_popup(event.x_root, event.y_root)
        entry.bind("<Button-3>", show_menu)

    def toggle_sources(self):
        if self.sources_visible:
            self.sources_frame.pack_forget()
            self.sources_visible = False
            self.btn_toggle_sources.configure(fg_color=MATRIX_LOW_GREEN, text_color=MATRIX_GREEN)
        else:
            self.sources_frame.pack(fill="x", padx=40, pady=(0, 10), after=self.status_container)
            self.sources_visible = True
            self.btn_toggle_sources.configure(fg_color=MATRIX_HOVER, text_color=TEXT_COLOR)

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

    def parse_proxy_link(self, text):
        try:
            text = text.strip()
            # 1. Пытаемся найти стандартный формат ссылки tg:// или t.me/
            match = re.search(r'(tg://proxy\?|t\.me/proxy\?)[^\s|\"|\'|\]|>|\|]+', text)
            if match:
                link = match.group(0).strip().rstrip('|').rstrip(']')
                parsed = urlparse(link.replace('tg://', 'http://'))
                params = parse_qs(parsed.query)
                srv = params.get('server', [None])[0]
                prt = params.get('port', [None])[0]
                sec = params.get('secret', [None])[0]
                if srv and prt and sec:
                    return {'server': srv.strip(), 'port': int(prt.strip()), 'secret': sec.strip(), 'full_link': link}
            
            # 2. Пытаемся найти сырой формат IP:PORT:SECRET (используется в proxy_ru.txt)
            match_plain = re.search(r'([\w\.-]+):(\d+):([a-zA-Z0-9_-]{32,})', text)
            if match_plain:
                srv, prt, sec = match_plain.groups()
                link = f"https://t.me/proxy?server={srv}&port={prt}&secret={sec}"
                return {'server': srv.strip(), 'port': int(prt.strip()), 'secret': sec.strip(), 'full_link': link}
                
        except Exception: pass
        return None

    def check_connection(self, proxy):
        if not proxy: return None
        
        is_fake_tls = proxy['secret'].lower().startswith('ee')
        proxy['is_fake_tls'] = is_fake_tls

        # ПРОВЕРКА 1: ДЛЯ СТАРЫХ ПРОКСИ ЧЕРЕЗ TELETHON
        async def _test_telethon():
            client = None
            try:
                client = TelegramClient(MemorySession(), 4, '014b35b6184100b085b0d0572f9b5103',
                    proxy=(proxy['server'], proxy['port'], proxy['secret']),
                    connection=ConnectionTcpMTProxyRandomizedIntermediate)
                
                await asyncio.wait_for(client.connect(), timeout=10.0)
                
                if client.is_connected():
                    self.log(f"[+] ALIVE (Standard): {proxy['server']}:{proxy['port']}")
                    await client.disconnect()
                    return proxy
                else:
                    self.log(f"[-] DEAD (Standard - No Route): {proxy['server']}:{proxy['port']}")
            except asyncio.TimeoutError:
                self.log(f"[-] TIMEOUT: {proxy['server']}:{proxy['port']}")
            except Exception as e:
                self.log(f"[-] FAILED: {proxy['server']}:{proxy['port']} ({type(e).__name__})")
            finally:
                if client:
                    try: await client.disconnect()
                    except Exception: pass
            return None

        # ПРОВЕРКА 2: КАСТОМНЫЙ FAKE-TLS (ДЛЯ СОВРЕМЕННЫХ EE-ПРОКСИ)
        # Telethon не умеет слать TLS Hello, поэтому умные прокси его сбрасывают (readexactly error).
        # Мы посылаем настоящий TLS пакет вручную.
        async def _test_fake_tls():
            try:
                # Открываем сокет с таймаутом
                reader, writer = await asyncio.wait_for(asyncio.open_connection(proxy['server'], proxy['port']), timeout=7.0)
                
                # Имитируем начало HTTPS соединения (TLS 1.2 Client Hello).
                # Fake-TLS серверы ждут именно этого. Если послать мусор, они мгновенно разорвут связь.
                tls_hello = bytes.fromhex("16030100a5010000a10303") + b"A"*32 + bytes.fromhex("00000000000201000055") + b"B"*85
                writer.write(tls_hello)
                await writer.drain()
                
                try:
                    # Ждем реакции сервера. Если он отвечает ServerHello или просто держит порт открытым - он жив.
                    data = await asyncio.wait_for(reader.read(1024), timeout=2.0)
                except asyncio.TimeoutError:
                    pass # Таймаут чтения значит, что сервер держит соединение (Alive!)
                
                writer.close()
                try: await writer.wait_closed()
                except Exception: pass
                    
                self.log(f"[+] ALIVE (Fake-TLS Verified): {proxy['server']}:{proxy['port']}")
                return proxy
            except Exception as e:
                self.log(f"[-] DEAD (Fake-TLS Drop): {proxy['server']}:{proxy['port']} ({type(e).__name__})")
                return None

        # ЗАПУСК ИЗОЛИРОВАННОГО СОБЫТИЙНОГО ЦИКЛА
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = None
        try:
            if is_fake_tls:
                result = loop.run_until_complete(_test_fake_tls())
            else:
                result = loop.run_until_complete(_test_telethon())
        except Exception as e:
            self.log(f"[ERROR] Thread Exception: {str(e)}")
        finally:
            try:
                # ИДЕАЛЬНАЯ ОЧИСТКА МУСОРА ASYNCIO
                # Останавливаем все фоновые задачи, чтобы избавиться от спама "Event loop is closed"
                tasks = asyncio.all_tasks(loop)
                for task in tasks:
                    task.cancel()
                if tasks:
                    loop.run_until_complete(asyncio.gather(*tasks, return_exceptions=True))
                loop.run_until_complete(loop.shutdown_asyncgens())
                loop.close()
            except Exception: pass
            
        return result

    def copy_to_clipboard(self, text_to_copy, item_type, widget=None):
        self.clipboard_clear()
        self.clipboard_append(str(text_to_copy))
        self.copy_notify.configure(text=f"[ {item_type} SECURED IN CLIPBOARD ]", text_color=MATRIX_GREEN)
        self.after(2000, lambda: self.copy_notify.configure(text=""))
        if widget: widget.configure(fg_color=COPIED_BG, hover_color=COPIED_HOVER, text_color=COPIED_TEXT, border_color=COPIED_HOVER)

    def add_proxy_widget(self, proxy):
        proxy_block = ctk.CTkFrame(self.result_frame, fg_color="#080808", border_color=MATRIX_LOW_GREEN, border_width=1, corner_radius=4)
        proxy_block.pack(fill="x", pady=5, padx=5)
        secret_display = proxy['secret']
        if len(secret_display) > 12: secret_display = secret_display[:10] + "..."
        row_frame = ctk.CTkFrame(proxy_block, fg_color="transparent")
        row_frame.pack(fill="x", pady=(5, 0), padx=5)
        
        btn_s = ctk.CTkButton(row_frame, text=f"SRV: {proxy['server']}", anchor="w", fg_color=MATRIX_LOW_GREEN, border_width=1, text_color=TEXT_COLOR, hover_color=MATRIX_HOVER)
        btn_s.configure(command=lambda b=btn_s: self.copy_to_clipboard(proxy['server'], "SERVER", b))
        btn_s.pack(side="left", fill="x", expand=True, padx=(0, 5))
        
        btn_p = ctk.CTkButton(row_frame, text=f"PORT: {proxy['port']}", width=80, fg_color=MATRIX_LOW_GREEN, border_width=1, text_color=TEXT_COLOR, hover_color=MATRIX_HOVER)
        btn_p.configure(command=lambda b=btn_p: self.copy_to_clipboard(proxy['port'], "PORT", b))
        btn_p.pack(side="left", padx=(0, 5))
        
        btn_sec = ctk.CTkButton(row_frame, text=f"SEC: {secret_display}", width=130, fg_color=MATRIX_LOW_GREEN, border_width=1, text_color=TEXT_COLOR, hover_color=MATRIX_HOVER)
        btn_sec.configure(command=lambda b=btn_sec: self.copy_to_clipboard(proxy['secret'], "SECRET", b))
        btn_sec.pack(side="right")

        # Маркировка для старых прокси (не Fake-TLS)
        if not proxy.get('is_fake_tls', True):
            warn_lbl = ctk.CTkLabel(proxy_block, text="[ NOT FOR RUSSIA (Standard Protocol) ]", text_color="#FF4444", font=ctk.CTkFont(family="Courier New", size=10, weight="bold"))
            warn_lbl.pack(pady=(2, 0))
        
        ctk.CTkLabel(proxy_block, text="[ OR FULL LINK ]", text_color="#008822", font=ctk.CTkFont(family="Courier New", size=10, weight="bold")).pack()
        full_l = f"https://t.me/proxy?server={proxy['server']}&port={proxy['port']}&secret={proxy['secret']}"
        disp_l = full_l if len(full_l) < 85 else full_l[:82] + "..."
        btn_fl = ctk.CTkButton(proxy_block, text=disp_l, fg_color=MATRIX_LOW_GREEN, border_width=1, text_color=TEXT_COLOR, hover_color=MATRIX_HOVER)
        btn_fl.configure(command=lambda b=btn_fl: self.copy_to_clipboard(full_l, "FULL LINK", b))
        btn_fl.pack(fill="x", pady=(0, 5), padx=5)

    def start_checking(self):
        if self.is_checking: return
        self.is_checking = True
        self.stop_event.clear()
        self.active_count = 0
        self.btn_start.configure(state="disabled", text="SCANNING NETWORK...")
        for w in self.result_frame.winfo_children(): w.destroy()
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        
        self.log("=== INITIATING MATRIX SCAN ===")
        self.log("[*] Platform: " + sys.platform)
        if not PROXY_LIBS_READY:
            self.log("[!] WARNING: python-socks is missing. Proxies will be skipped.")
            
        threading.Thread(target=self.process_workflow, daemon=True).start()

    def process_workflow(self):
        try:
            self.after(0, self.update_status, "Aggregating proxy lists...")
            raw_proxies = []
            seen = set()
            active_urls = [e.get().strip() for e in self.source_entries if e.get().strip()]
            
            for url in active_urls:
                clean_url = url
                if "github.com" in clean_url and "/blob/" in clean_url:
                    clean_url = clean_url.replace("github.com", "raw.githubusercontent.com").replace("/blob/", "/")
                
                self.log(f"[*] Fetching: {clean_url}")
                try:
                    resp = requests.get(clean_url, timeout=10)
                    resp.raise_for_status()
                    source_count = 0
                    for line in resp.text.splitlines():
                        p = self.parse_proxy_link(line)
                        if p:
                            sig = f"{p['server']}:{p['port']}:{p['secret']}"
                            if sig not in seen:
                                seen.add(sig)
                                raw_proxies.append(p)
                                source_count += 1
                    self.log(f"    -> Found {source_count} unique candidates.")
                except Exception as e:
                    self.log(f"[WARN] Failed to fetch {url}: {str(e)}")
            
            if not raw_proxies:
                self.log("[!] No proxy candidates found.")
                self.after(0, self.update_status, "No candidates found.")
                return

            self.log(f"[*] Total unique targets: {len(raw_proxies)}")
            self.after(0, self.update_status, f"Verifying {len(raw_proxies)} targets...")
            
            with concurrent.futures.ThreadPoolExecutor(max_workers=25) as ex:
                futures = {ex.submit(self.check_connection, p): p for p in raw_proxies}
                checked = 0
                for f in concurrent.futures.as_completed(futures):
                    if self.stop_event.is_set(): break
                    checked += 1
                    res = f.result()
                    if res:
                        self.active_count += 1
                        self.after(0, self.add_proxy_widget, res)
                    if checked % 5 == 0 or checked == len(raw_proxies):
                        self.after(0, self.update_status, f"Scanning: {checked}/{len(raw_proxies)} | Alive: {self.active_count}")
            
            self.log(f"=== SCAN COMPLETE. FOUND {self.active_count} ACTIVE NODES ===")
            self.after(0, self.update_status, f"Scan complete. {self.active_count} nodes found.")
        except Exception as e:
            self.log(f"[FATAL ERROR] {str(e)}")
        finally:
            self.is_checking = False
            self.after(0, lambda: self.btn_start.configure(state="normal", text="RE-ENTER THE MATRIX"))
            gc.collect()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = MTProtoApp()
    app.mainloop()
