import customtkinter as ctk
from ctk_scrollable_dropdown import CTkScrollableDropdown
import os
import subprocess
from tkinter import messagebox
import sys
import ctypes
import json
import re
import tkinter as tk
import winreg
import threading
import urllib.request
import urllib.error
import tempfile
import datetime
import logging
import time
from PIL import Image

def get_asset_path(filename):
    """Obtiene la ruta de un recurso, ya sea en dev o compilado por PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, filename)

CURRENT_VERSION = "2.0.6"
# --- INFO DE ACTUALIZACIONES ---
GITHUB_REPO = "Faaabra/Auto-queue"

# ==========================================
# SOLICITUD DE PRIVILEGIOS DE ADMINISTRADOR
# ==========================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

if not is_admin():
    # Si no somos admin, reiniciamos el programa pidiendo elevación (UAC)
    if hasattr(sys, '_MEIPASS'):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, "", None, 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1)
    sys.exit()

ctk.set_appearance_mode("dark")

# Colores personalizados
COLOR_RUST_RED = "#ce422b"
COLOR_RUST_HOVER = "#a3321f"
COLOR_LIGHT_TEXT = "#d1d1d1"
COLOR_DARK_FRAME = "#1e1e1e"
COLOR_BLUE = "#4db8ff"
COLOR_GREEN = "#28a745"
COLOR_YELLOW = "#ffcc00"
COLOR_INACTIVE = "#888888"

# Regex para validar formato IP/Dominio con o sin puerto
IP_PORT_RE = re.compile(r'^[a-zA-Z0-9._-]+(?::\d+)?$')

# --- SISTEMA DE LOGGING ---
APPDATA_DIR = os.path.join(os.environ["APPDATA"], "RustAutoQueue")
if not os.path.exists(APPDATA_DIR):
    os.makedirs(APPDATA_DIR)
LOG_FILE = os.path.join(APPDATA_DIR, "activity.log")
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    encoding="utf-8"
)
logger = logging.getLogger("RustAutoQueue")

# ===================================================================
# SERVIDORES DESTACADOS (CURATED LIST)
# ===================================================================
FEATURED_SERVERS = [
    {"alias": "RUSTORIA EU MAIN", "ip": "eu.rustoria.co:28015", "desc": "Wipe Semanal | Vanilla | Pop: Alta"},
    {"alias": "ATLAS X2 QUAD", "ip": "2xmonthlyquad.atlasrust.uk:28015", "desc": "Wipe Mensual | 2x | Max 4"},
    {"alias": "STEVIOUS 2X LARGE", "ip": "play.stevious.io:28015", "desc": "Wipe Bisemanal | 2x | Max 8"},
    {"alias": "RUSTAFIED EU MAIN", "ip": "eumain.rustafied.com:28015", "desc": "Wipe Semanal | Vanilla | Oficial"},
    {"alias": "WARBAND 2X SOLO/DUO", "ip": "play.warband.gg:28015", "desc": "Wipe Semanal | 2x | Max 2"},
    {"alias": "BLOO LAGOON", "ip": "play.bloolagoon.com:28015", "desc": "Wipe Semanal | 1.5x | Max 6"},
    {"alias": "VITAL RUST 10X", "ip": "play.vitalrust.com:28015", "desc": "Wipe Semanal | 10x | PvP/Clanes"},
    {"alias": "RENEGADE 2X MAIN", "ip": "eu.renegaderust.com:28015", "desc": "Wipe Semanal | 2x | No Limit"},
    {"alias": "ANDROMEDA 2X TRIO", "ip": "play.andromedarust.com:28015", "desc": "Wipe Semanal | 2x | Max 3"},
    {"alias": "LIMITLESS 2X", "ip": "play.limitlessrust.com:28015", "desc": "Wipe Bisemanal | 2x | Vanilla+"}
]

class Tooltip:
    """Tooltip que aparece al pasar el ratón sobre un widget."""
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip_window = None
        widget.bind("<Enter>", self._show)
        widget.bind("<Leave>", self._hide)

    def _show(self, event=None):
        if self.tip_window:
            return
        # Aparece junto al cursor para no tapar otros widgets
        x = (event.x_root + 14) if event else (self.widget.winfo_rootx() + 20)
        y = (event.y_root + 14) if event else (self.widget.winfo_rooty() + 30)
        self.tip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, background="#2a2a2a", foreground="#cccccc",
                         relief="flat", font=("Segoe UI", 11), padx=10, pady=6,
                         wraplength=300, justify="left")
        label.pack()

    def _hide(self, event=None):
        if self.tip_window:
            self.tip_window.destroy()
            self.tip_window = None


# ===================================================================
# ===================================================================
# SISTEMA DE NOTIFICACIONES TOAST Y DIÁLOGOS PERSONALIZADOS
# ===================================================================

class ToastNotification:
    """
    Notificación flotante no-bloqueante (Toast)
    Aparece en la esquina inferior derecha y desaparece tras unos segundos.
    """
    @staticmethod
    def show(parent, message, duration=2500):
        # Crear un frame flotante superior
        toast = ctk.CTkFrame(parent, fg_color="#2b2b2b", corner_radius=6, border_color="#3a3a3c", border_width=1)
        
        lbl = ctk.CTkLabel(toast, text=message, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="white")
        lbl.pack(padx=20, pady=10)
        
        # Posicionar en la esquina inferior derecha, por encima de todo
        toast.place(relx=0.95, rely=0.95, anchor="se")
        toast.lift()
        
        def _hide():
            try: toast.destroy()
            except: pass
            
        parent.after(duration, _hide)
class StyledDialog(ctk.CTkToplevel):
    """
    Diálogo modal personalizado con estilo oscuro premium.
    Tipos soportados: 'info', 'warning', 'error', 'confirm', 'input'
    """
    # Color del acento lateral por tipo
    ACCENT_COLORS = {
        "info":    COLOR_RUST_RED,
        "warning": "#d4a853",
        "error":   "#dc3545",
        "confirm": "#d4a853",
        "input":   COLOR_RUST_RED,
    }

    def __init__(self, parent, title, message, dialog_type="info", **kwargs):
        super().__init__(parent)

        self.result = None
        self._input_value = None

        # --- Window setup ---
        self.title(title)
        self.resizable(False, False)
        self.configure(fg_color="#141416")
        self.transient(parent)
        self.grab_set()

        # CustomTkinter overrides the icon at ~200ms internally.
        # To avoid the user seeing a "blink" or the blue default icon, we hide the window briefly.
        self.withdraw()
        
        try:
            import sys as _sys
            _icon = os.path.join(_sys._MEIPASS, 'rust.ico') if hasattr(_sys, '_MEIPASS') else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rust.ico')
            if os.path.exists(_icon):
                try: self.iconbitmap(_icon)
                except: pass
                
                def _apply_icon_and_show():
                    try: self.iconbitmap(_icon)
                    except: pass
                    self.deiconify()
                
                self.after(250, _apply_icon_and_show)
            else:
                self.after(10, self.deiconify)
        except Exception:
            self.after(10, self.deiconify)

        # --- Dimensions ---
        w = kwargs.get("width", 420)
        h = kwargs.get("height", 220 if dialog_type != "input" else 260)
        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        x = int((sw / 2) - (w / 2))
        y = int((sh / 2) - (h / 2))
        self.geometry(f"{w}x{h}+{x}+{y}")

        accent = self.ACCENT_COLORS.get(dialog_type, COLOR_RUST_RED)

        # --- Content container ---
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="both", expand=True, padx=28, pady=(22, 18))

        # Accent bar + Title
        header_frame = ctk.CTkFrame(container, fg_color="transparent")
        header_frame.pack(fill="x", pady=(0, 10))

        # Small colored accent bar
        accent_bar = ctk.CTkFrame(header_frame, fg_color=accent, width=4, height=22, corner_radius=2)
        accent_bar.pack(side="left", padx=(0, 12))

        title_lbl = ctk.CTkLabel(
            header_frame, text=title,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="white", anchor="w"
        )
        title_lbl.pack(side="left", fill="x", expand=True)

        # Divider line
        divider = ctk.CTkFrame(container, fg_color="#2b2b2f", height=1)
        divider.pack(fill="x", pady=(0, 14))

        # Message body
        msg_lbl = ctk.CTkLabel(
            container, text=message,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#cccccc", wraplength=w - 80,
            justify="left", anchor="nw"
        )
        msg_lbl.pack(fill="x", pady=(0, 10))

        # Input field (only for 'input' type)
        if dialog_type == "input":
            self._entry = ctk.CTkEntry(
                container, height=38,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="#1a1a1c", border_color="#333335",
                placeholder_text=kwargs.get("placeholder", "")
            )
            self._entry.pack(fill="x", pady=(0, 14))
            
            init_val = kwargs.get("initial_value", "")
            if init_val:
                self._entry.insert(0, init_val)
                
            self._entry.focus_set()
            self._entry.bind("<Return>", lambda e: self._on_ok())

        # --- Button area ---
        btn_frame = ctk.CTkFrame(container, fg_color="transparent")
        btn_frame.pack(fill="x", side="bottom")

        if dialog_type == "confirm":
            btn_cancel = ctk.CTkButton(
                btn_frame, text="Cancelar", width=120, height=38,
                fg_color="transparent", border_width=1, border_color="#444",
                hover_color="#2b2b2b", text_color="#aaaaaa",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=self._on_cancel
            )
            btn_cancel.pack(side="right", padx=(8, 0))

            btn_ok = ctk.CTkButton(
                btn_frame, text="Aceptar", width=120, height=38,
                fg_color=COLOR_RUST_RED, hover_color=COLOR_RUST_HOVER,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=self._on_ok
            )
            btn_ok.pack(side="right")

        elif dialog_type == "input":
            btn_cancel = ctk.CTkButton(
                btn_frame, text="Cancelar", width=120, height=38,
                fg_color="transparent", border_width=1, border_color="#444",
                hover_color="#2b2b2b", text_color="#aaaaaa",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=self._on_cancel
            )
            btn_cancel.pack(side="right", padx=(8, 0))

            btn_ok = ctk.CTkButton(
                btn_frame, text="Guardar", width=120, height=38,
                fg_color=COLOR_RUST_RED, hover_color=COLOR_RUST_HOVER,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=self._on_ok
            )
            btn_ok.pack(side="right")

        else:
            # Single "Entendido" button for info/warning/error
            btn_color = {
                "info": "#333335",
                "warning": "#5a4a1a",
                "error": COLOR_RUST_RED
            }.get(dialog_type, "#333335")

            btn_hover = {
                "info": "#444446",
                "warning": "#6b5a22",
                "error": COLOR_RUST_HOVER
            }.get(dialog_type, "#444446")

            btn_ok = ctk.CTkButton(
                btn_frame, text="Entendido", width=140, height=38,
                fg_color=btn_color, hover_color=btn_hover,
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                command=self._on_ok
            )
            btn_ok.pack(side="right")

        # Escape to close
        self.bind("<Escape>", lambda e: self._on_cancel())
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

        # Focus
        self.after(100, lambda: btn_ok.focus_set() if dialog_type != "input" else None)

    def _on_ok(self):
        if hasattr(self, '_entry'):
            self._input_value = self._entry.get()
        self.result = True
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self.result = False
        self._input_value = None
        self.grab_release()
        self.destroy()

    def get_result(self):
        """Block until dialog is closed, then return result."""
        self.wait_window()
        return self.result

    def get_input(self):
        """Block until dialog is closed, then return input text or None."""
        self.wait_window()
        return self._input_value


def styled_showinfo(parent, title, message):
    """Show a styled info dialog. Replaces messagebox.showinfo."""
    d = StyledDialog(parent, title, message, dialog_type="info")
    d.get_result()

def styled_showwarning(parent, title, message):
    """Show a styled warning dialog. Replaces messagebox.showwarning."""
    d = StyledDialog(parent, title, message, dialog_type="warning")
    d.get_result()

def styled_showerror(parent, title, message):
    """Show a styled error dialog. Replaces messagebox.showerror."""
    d = StyledDialog(parent, title, message, dialog_type="error")
    d.get_result()

def styled_askyesno(parent, title, message, **kwargs):
    """Show a styled confirm dialog. Returns True/False. Replaces messagebox.askyesno."""
    d = StyledDialog(parent, title, message, dialog_type="confirm", **kwargs)
    return d.get_result()

def styled_input(parent, title, message, placeholder="", initial_value=""):
    """Show a styled input dialog. Returns string or None. Replaces CTkInputDialog."""
    d = StyledDialog(parent, title, message, dialog_type="input", placeholder=placeholder, initial_value=initial_value)
    return d.get_input()


# Rutas - Guardamos las IPs en AppData (APPDATA_DIR ya se creó arriba para logging)
CONFIG_FILE = os.path.join(APPDATA_DIR, "servers.json")
# Nuevo archivo para preferencias de la app
SETTINGS_FILE = os.path.join(APPDATA_DIR, "settings.json")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Rust Auto-Queue Launcher - V2")
        
        # Centrar en la pantalla (Landscape Dashboard layout)
        window_width = 820
        window_height = 620
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        self.resizable(False, True)

        if not os.path.exists(APPDATA_DIR):
            os.makedirs(APPDATA_DIR)

        self.servers_data = self.load_servers()
        self.settings = self.load_settings()

        self.sys_user = os.environ.get('USERNAME', '')
        self.sys_domain = os.environ.get('USERDOMAIN', os.environ.get('COMPUTERNAME', ''))

        # Fuentes reutilizables
        self.font_title = ctk.CTkFont(family="Segoe UI", size=36, weight="bold")
        self.font_subtitle = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.font_label = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        self.font_text = ctk.CTkFont(family="Segoe UI", size=12)
        self.font_small = ctk.CTkFont(family="Segoe UI", size=11)

        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'rust.ico')
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rust.ico')
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except Exception:
                pass

        self.startup_path = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AutoRustLauncher.bat")

        # Timer para debounce del slider
        self._delay_save_timer = None

        # --- ESTRUCTURA PRINCIPAL (SIDEBAR + CONTENEDOR) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=170, corner_radius=0, fg_color="#141416")
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)
        
        # Logotipo en el sidebar
        logo_label = ctk.CTkLabel(self.sidebar_frame, text="RUST", font=ctk.CTkFont(family="Segoe UI", size=24, weight="bold"), text_color=COLOR_RUST_RED)
        logo_label.pack(pady=(25, 0))
        logo_sub = ctk.CTkLabel(self.sidebar_frame, text="AUTO-QUEUE V2", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="white")
        logo_sub.pack(pady=(0, 30))

        # Contenedor de paneles (Derecha)
        self.container_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.container_frame.pack(side="right", fill="both", expand=True)

        # Cargar datos de Steam
        self.steam_users = self.load_steam_accounts()

        # Configurar navegación
        self.pages = {}
        self.active_page = None
        self.nav_buttons = {}
        
        self.is_sniping = False
        self.snipe_thread = None
        self.snipe_ip = None
        self.nav_bars = {}

        def load_icon(name):
            try:
                img = Image.open(get_asset_path(f"icons/{name}.png"))
                return ctk.CTkImage(light_image=img, dark_image=img, size=(18, 18))
            except Exception as e:
                return None

        self.icon_home = load_icon("home")
        self.icon_snipe = load_icon("snipe")
        self.icon_servers = load_icon("servers")
        self.icon_wake = load_icon("wake")
        self.icon_logs = load_icon("logs")
        self.icon_discord = load_icon("discord")
        self.icon_settings = load_icon("settings")

        btn_data = [
            ("home", self.icon_home, "INICIO"),
            ("snipe", self.icon_snipe, "WIPE-SPAM"),
            ("servers", self.icon_servers, "SERVIDORES"),
            ("wake", self.icon_wake, "AUTO-DESPERTAR"),
            ("logs", self.icon_logs, "ACTIVIDAD"),
            ("discord", self.icon_discord, "DISCORD")
        ]

        # Contenedor para alinear los botones arriba
        self.nav_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.nav_container.pack(fill="both", expand=True, pady=(10, 0))
        self.nav_container.grid_columnconfigure(0, weight=1)

        for idx, (page_id, icon_img, text) in enumerate(btn_data):
            # Frame wrapper para el botón y la barra roja
            wrapper = ctk.CTkFrame(self.nav_container, fg_color="transparent", height=45)
            wrapper.grid(row=idx, column=0, sticky="ew", pady=2)
            wrapper.pack_propagate(False)
            
            # Barra roja indicadora (oculta por defecto)
            bar = ctk.CTkFrame(wrapper, width=4, corner_radius=0, fg_color="transparent")
            bar.pack(side="left", fill="y")
            self.nav_bars[page_id] = bar

            btn = ctk.CTkButton(
                wrapper,
                text=f"   {text}",
                image=icon_img,
                height=45,
                corner_radius=0,
                fg_color="transparent",
                text_color="#aaaaaa",
                hover_color="#1a1a1c",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                anchor="w",
                command=lambda p=page_id: self.switch_page(p)
            )
            btn.pack(side="left", fill="both", expand=True)
            self.nav_buttons[page_id] = btn

        # Spacer al fondo
        spacer = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent", height=20)
        spacer.pack(side="bottom")
        
        # Botón de SETTINGS al final
        settings_wrapper = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent", height=45)
        settings_wrapper.pack(side="bottom", fill="x", pady=2)
        settings_wrapper.pack_propagate(False)
        
        settings_bar = ctk.CTkFrame(settings_wrapper, width=4, corner_radius=0, fg_color="transparent")
        settings_bar.pack(side="left", fill="y")
        self.nav_bars["settings"] = settings_bar
        
        settings_btn = ctk.CTkButton(
            settings_wrapper,
            text=f"   SETTINGS",
            image=self.icon_settings,
            height=45,
            corner_radius=0,
            fg_color="transparent",
            text_color="#aaaaaa",
            hover_color="#1a1a1c",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            anchor="w",
            command=lambda: styled_showinfo(self, "Aviso", "Próximamente")
        )
        settings_btn.pack(side="left", fill="x", expand=True)
        self.nav_buttons["settings"] = settings_btn

        # Footer in sidebar
        lbl_version = ctk.CTkLabel(self.sidebar_frame, text=f"v{CURRENT_VERSION}", font=ctk.CTkFont(size=10), text_color="#555555")
        lbl_version.pack(side="bottom", pady=(0, 10))
        
        lbl_author = ctk.CTkLabel(self.sidebar_frame, text="Desarrollado por faabra", font=ctk.CTkFont(size=10), text_color="#555555")
        lbl_author.pack(side="bottom", pady=(0, 0))

        # Crear las páginas
        self.create_home_page()
        self.create_snipe_page()
        self.create_servers_page()
        self.create_wake_page()
        self.create_logs_page()
        self.create_discord_page()

        # Iniciar en la página principal
        self.switch_page("home")

        # Rellenar IP activa si existe
        self._populate_active_ip()
        self.check_status()

        # Iniciar comprobador de actualizaciones y Steam
        self.check_for_updates()
        self._check_steam_installed()

        # Quitar el foco si se hace clic fuera
        def un_focus(event):
            try:
                if event.widget.winfo_class() not in ["Entry", "Text"]:
                    event.widget.focus_set()
            except Exception:
                pass
        self.bind_all("<Button-1>", un_focus)

        logger.info("Aplicación iniciada v%s", CURRENT_VERSION)

    # --- SISTEMA DE ACTUALIZACIONES ---
    def check_for_updates(self):
        def check_logic():
            try:
                api_url = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
                req = urllib.request.Request(api_url, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req, timeout=5) as response:
                    data = json.loads(response.read().decode())
                    
                # Extraemos "v2.0.1" -> "2.0.1"
                latest_tag = data.get("tag_name", "").replace("v", "").strip()
                
                # Si la version de la release de github es diferente a la actual
                if latest_tag and latest_tag != CURRENT_VERSION:
                    download_url = ""
                    # Buscamos el ejecutable en los archivos subidos de la release
                    for asset in data.get("assets", []):
                        if asset.get("name", "").endswith(".exe"):
                            download_url = asset.get("browser_download_url")
                            break
                            
                    if download_url:
                        self.after(1000, lambda: self.show_update_prompt(latest_tag, download_url))
            except Exception:
                pass
                
        if GITHUB_REPO:
            threading.Thread(target=check_logic, daemon=True).start()

    def show_update_prompt(self, latest_version, download_url):
        w = ctk.CTkToplevel(self)
        w.title("¡Actualización Disponible!")
        w.geometry("420x280")
        w.resizable(False, False)
        w.configure(fg_color="#141416")
        
        x = int(self.winfo_x() + (self.winfo_width() / 2) - 210)
        y = int(self.winfo_y() + (self.winfo_height() / 2) - 140)
        w.geometry(f"+{x}+{y}")
        w.transient(self)
        w.grab_set() # Foco obligatorio

        # Set icon with multiple delays to override CTkToplevel's reset
        try:
            _icon = os.path.join(sys._MEIPASS, 'rust.ico') if hasattr(sys, '_MEIPASS') else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rust.ico')
            if os.path.exists(_icon):
                def _apply():
                    try: w.iconbitmap(_icon)
                    except: pass
                w.after(50, _apply)
                w.after(250, _apply)
                w.after(500, _apply)
        except Exception:
            pass
        
        title = ctk.CTkLabel(w, text="¡Nueva Versión Encontrada!", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=COLOR_BLUE)
        title.pack(pady=(25, 10))
        
        desc = ctk.CTkLabel(w, text=f"Hay una nueva versión ({latest_version}) para descargar.\nTienes instalada la {CURRENT_VERSION}.\n\n¿Deseas descargarla e instalarla ahora?", font=ctk.CTkFont(family="Segoe UI", size=13))
        desc.pack(pady=10)
        
        self.update_progress = ctk.CTkProgressBar(w, width=300, progress_color=COLOR_BLUE)
        self.update_progress.set(0)
        self.update_progress.pack(pady=10)
        self.update_progress.pack_forget()
        
        btn_frame = ctk.CTkFrame(w, fg_color="transparent")
        btn_frame.pack(pady=10)
        
        def on_accept():
            btn_cancel.pack_forget()
            btn_accept.configure(state="disabled", text="Descargando...")
            self.update_progress.pack(pady=10)
            threading.Thread(target=self.download_and_install_update, args=(download_url, w), daemon=True).start()
            
        btn_accept = ctk.CTkButton(btn_frame, text="✅ Actualizar", fg_color="#28a745", hover_color="#218838", command=on_accept)
        btn_accept.pack(side="left", padx=10)
        
        btn_cancel = ctk.CTkButton(btn_frame, text="❌ Más tarde", fg_color="#dc3545", hover_color="#c82333", command=w.destroy)
        btn_cancel.pack(side="left", padx=10)

    def download_and_install_update(self, download_url, window):
        try:
            if not hasattr(sys, '_MEIPASS'):
                self.after(0, lambda: styled_showinfo(self, "Info de Desarrollo", "La función de auto-parche solo funciona si ejecutas el código compilado como .exe de Windows."))
                self.after(0, window.destroy)
                return

            req = urllib.request.Request(download_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req) as response:
                total_size = int(response.info().get("Content-Length", -1))
                new_exe_path = os.path.join(tempfile.gettempdir(), "RustAutoQueue_new.exe")
                
                with open(new_exe_path, "wb") as f:
                    downloaded = 0
                    last_progress = -1
                    while True:
                        buffer = response.read(8192)
                        if not buffer:
                            break
                        downloaded += len(buffer)
                        f.write(buffer)
                        if total_size > 0:
                            progress = downloaded / total_size
                            # Actualizar barra de progreso solo cuando cambia en más de 1% para no ahogar a Tkinter
                            if progress - last_progress > 0.01:
                                last_progress = progress
                                self.after(0, lambda p=progress: self.update_progress.set(p))
                                
            current_exe = sys.executable
            
            # Preparar un archivo batch que se encargará de sustituir la app mientras está cerrada
            bat_path = os.path.join(tempfile.gettempdir(), "update_rust_autoqueue.bat")
            
            exe_dir = os.path.dirname(current_exe)
            bat_content = f"""@echo off
ping 127.0.0.1 -n 3 > nul
move /y "{new_exe_path}" "{current_exe}"
cd /d "{exe_dir}"
start "" "{current_exe}"
del "%~f0"
"""
            with open(bat_path, "w") as f:
                f.write(bat_content)

            # IMPORTANTE: Limpiar el entorno heredado de PyInstaller
            env = dict(os.environ)
            for k in list(env.keys()):
                key_up = k.upper()
                if 'MEI' in key_up or 'TCL' in key_up or 'TK' in key_up or 'PY' in key_up:
                    env.pop(k, None)
                    
            # Restaurar SYSTEMROOT y PATH si hubieran caido
            if 'SYSTEMROOT' not in env:
                env['SYSTEMROOT'] = os.environ.get('SYSTEMROOT', r'C:\Windows')

            # Lanzamos el proceso .bat de manera silenciosa para que haga el trabajo sucio
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            
            subprocess.Popen([bat_path], env=env, startupinfo=startupinfo, shell=True)
            
            # Suicidar la aplicación actual violentamente para destrabar los handles del exe actual
            os._exit(0)
            
        except Exception as e:
            self.after(0, lambda error=e: styled_showerror(self, "Error", f"Fallo al actualizar: {error}"))
            self.after(0, window.destroy)

    # --- LÓGICA DE SERVIDORES ---
    def load_servers(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if isinstance(v, str):
                            data[k] = {"ip": v, "fav": False}
                        elif isinstance(v, dict) and "fav" not in v:
                            data[k]["fav"] = False
                    return data
            except Exception as e:
                logger.warning("Error cargando servidores: %s", e)
        return {}

    def save_servers(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.servers_data, f, indent=4)
        except Exception as e:
            logger.error("Error guardando servidores: %s", e)

    # --- SISTEMA DE PREFERENCIAS ---
    def load_settings(self):
        default = {"wake_method": None, "delay": 10, "one_time_mode": False}
        if os.path.exists(SETTINGS_FILE):
            try:
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for k, v in default.items():
                        if k not in data: data[k] = v
                    return data
            except Exception as e:
                logger.warning("Error cargando settings: %s", e)
        return default

    def save_settings(self):
        try:
            with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                json.dump(self.settings, f, indent=4)
        except Exception as e:
            logger.error("Error guardando settings: %s", e)

    def set_wake_method(self, method, window=None):
        self.settings["wake_method"] = method
        self.save_settings()
        self.check_status()
        if window:
            self.refresh_auto_wake_ui(window)
        method_name = "NINGUNO" if method is None else method.replace('_', ' ').upper()
        styled_showinfo(self, "Configurado", f"Método de despertar guardado: {method_name}")

    def refresh_auto_wake_ui(self, window):
        # Buscamos el tabview dentro de la ventana
        tab_v = None
        for widget in window.winfo_children():
            if isinstance(widget, ctk.CTkTabview):
                tab_v = widget
                break
        
        if not tab_v: return
        
        method = self.settings.get("wake_method")
        active_text = "ESTE ES MI MÉTODO ACTIVO"
        
        # Limpiar etiquetas previas de "ACTIVO"
        for tab_name in ["Enchufe Inteligente", "BIOS RTC", "Software (Beta)"]:
            tab = tab_v.tab(tab_name)
            for child in tab.winfo_children():
                if isinstance(child, ctk.CTkLabel) and child.cget("text") == active_text:
                    child.destroy()
        
        # Añadir al tab correcto
        if method == "smart_plug":
            ctk.CTkLabel(tab_v.tab("Enchufe Inteligente"), text=active_text, text_color="#28a745", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        elif method == "bios":
            ctk.CTkLabel(tab_v.tab("BIOS RTC"), text=active_text, text_color="#28a745", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        elif method == "software":
            ctk.CTkLabel(tab_v.tab("Software (Beta)"), text=active_text, text_color="#28a745", font=ctk.CTkFont(weight="bold")).pack(pady=5)

    def get_current_ip_from_entry(self):
        raw_val = self.ip_entry.get().strip()
        if not raw_val or raw_val == "Selecciona un servidor...": return ""
        if raw_val in self.servers_data:
            data = self.servers_data[raw_val]
            return data["ip"] if isinstance(data, dict) else data
        return raw_val

    def on_home_server_selected(self, choice_or_event=None):
        if choice_or_event is not None and isinstance(choice_or_event, str):
            self.ip_entry.set(choice_or_event)
        raw_val = self.ip_entry.get().strip()
        if not raw_val or raw_val == "Selecciona un servidor..." or "💡" in raw_val or not hasattr(self, 'home_card'):
            if hasattr(self, 'home_card') and self.home_card.winfo_manager():
                self.home_card.pack_forget()
            return
            
        ip = self.get_current_ip_from_entry()
        self.home_card.pack(fill="x", pady=(0, 10), after=self.ip_frame)
        
        self.hc_title.configure(text=raw_val if raw_val in self.servers_data else "Servidor No Guardado")
        self.hc_status.configure(text=" ● COMPROBANDO ", text_color="#aaa")
        self.hc_ping.configure(text="Ping: --")
        self.hc_players.configure(text="--/-- PLAYERS")
        
        def do_fetch():
            import socket, re, subprocess, threading
            host = ip.split(":")[0] if ":" in ip else ip
            port = int(ip.split(":")[1]) if ":" in ip else 28015
            
            a2s_data = None
            for test_port in list(dict.fromkeys([port, port + 1, port + 15])):
                if a2s_data is not None: break
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1.0)
                try:
                    sock.sendto(b'\xFF\xFF\xFF\xFFTSource Engine Query\x00', (host, test_port))
                    data, _ = sock.recvfrom(4096)
                    if data.startswith(b'\xFF\xFF\xFF\xFFI'):
                        cp_m = re.search(rb'cp(\d+)', data)
                        mp_m = re.search(rb'mp(\d+)', data)
                        qp_m = re.search(rb'qp(\d+)', data)

                        cp = int(cp_m.group(1)) if cp_m else -1
                        mp = int(mp_m.group(1)) if mp_m else -1
                        qp = int(qp_m.group(1)) if qp_m else 0

                        if cp == -1 or mp == -1:
                            data_slice = data[5:]
                            protocol = data_slice[0]
                            data_slice = data_slice[1:]
                            name_end = data_slice.find(b'\x00')
                            data_slice = data_slice[name_end+1:]
                            data_slice = data_slice[data_slice.find(b'\x00')+1:]
                            data_slice = data_slice[data_slice.find(b'\x00')+1:]
                            data_slice = data_slice[data_slice.find(b'\x00')+1:]
                            import struct
                            app_id, cp, mp, bots = struct.unpack('<HBBb', data_slice[:5])

                        players_text = f"{cp}/{mp} PLAYERS"
                        if qp > 0:
                            players_text += f" (+{qp} EN COLA)"
                        a2s_data = {"players_text": players_text}
                except Exception: pass
                finally: sock.close()

            is_online = False
            ms = None
            try:
                result = subprocess.run(["ping", "-n", "1", "-w", "2000", host], capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                if result.returncode == 0:
                    is_online = True
                    out = result.stdout.decode('cp1252', errors='ignore')
                    m = re.search(r"(?:tiempo|time)[=<]\s*(\d+)\s*ms", out, re.IGNORECASE)
                    if m: ms = m.group(1)
            except Exception: pass

            def update_ui():
                try:
                    if not self.hc_status.winfo_exists(): return
                    if a2s_data:
                        self.hc_players.configure(text=a2s_data["players_text"])
                    else:
                        self.hc_players.configure(text="--/-- PLAYERS")
                        
                    if is_online or a2s_data:
                        self.hc_status.configure(text=" ● ACTIVE ", text_color="#28a745")
                        self.hc_ping.configure(text=f"Ping: {ms}ms" if ms else "Ping: <1ms")
                    else:
                        self.hc_status.configure(text=" ● OFFLINE ", text_color="#dc3545")
                        self.hc_ping.configure(text="Ping: Timeout")
                except Exception: pass
            self.after(0, update_ui)
        import threading
        threading.Thread(target=do_fetch, daemon=True).start()

    def test_windows_password(self):
        password = self.pw_entry.get()
        if not password:
            styled_showwarning(self, "Aviso", "Por favor, escribe tu contraseña antes de verificar.")
            return
            
        advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
        LOGON32_LOGON_NETWORK = 3
        LOGON32_PROVIDER_DEFAULT = 0
        token = ctypes.c_void_p()
        
        result = advapi32.LogonUserW(
            self.sys_user,
            self.sys_domain,
            password,
            LOGON32_LOGON_NETWORK,
            LOGON32_PROVIDER_DEFAULT,
            ctypes.byref(token)
        )
        
        if result:
            ctypes.windll.kernel32.CloseHandle(token)
            styled_showinfo(self, "¡Correcto!", "Verificación exitosa. Esta contraseña es válida y funcionará perfectamente para el arranque automático.")
            self.pw_entry.configure(border_color="#28a745")
        else:
            styled_showerror(self, "Clave Incorrecta", "La autenticación ha fallado, esa no es la contraseña.\n\nNOTA: Si ingresas en Windows usando un PIN, huella o Windows Hello, la contraseña real oculta de tu cuenta Microsoft puede ser diferente.")
            self.pw_entry.configure(border_color=COLOR_RUST_RED)

    # --- MÉTODOS DE LA UI PRINCIPAL ---
    def update_delay_label(self, value):
        """Actualiza el label del slider y guarda con debounce (C5)."""
        self.delay_value_label.configure(text=f"{int(value)}s")
        self.settings["delay"] = int(value)
        # Cancelar timer anterior si existe
        if self._delay_save_timer is not None:
            self.after_cancel(self._delay_save_timer)
        # Guardar a disco solo 500ms después del último movimiento
        self._delay_save_timer = self.after(500, self._save_delay_to_disk)

    def _save_delay_to_disk(self):
        """Guarda el delay a disco (llamado por el debounce)."""
        self._delay_save_timer = None
        self.save_settings()

    def _populate_active_ip(self):
        """No pre-rellenar el campo con sesiones antiguas."""
        pass

    def _save_one_time_setting(self):
        self.settings["one_time_mode"] = self.one_time_var.get()
        self.save_settings()

    def _save_smart_wipe_setting(self):
        self.settings["smart_wipe"] = self.smart_wipe_var.get()
        self.save_settings()

    def _flash_activate_button(self):
        """Breve animación visual al pulsar el botón de activar."""
        self.btn_activate.configure(fg_color="#e8a020")
        self.after(160, lambda: self.btn_activate.configure(fg_color=COLOR_RUST_RED))

    def _pulse_status(self):
        """Animación de pulso suave en el indicador de estado."""
        def animate_pulse(step):
            if not hasattr(self, 'status_dot') or not self.status_dot.winfo_exists(): return
            if step <= 10:
                # Crecer: de 18 a 22
                size = 18 + int(step * 0.4)
            elif step <= 20:
                # Encoger: de 22 a 18
                size = 22 - int((step - 10) * 0.4)
            else:
                self.status_dot.configure(font=ctk.CTkFont(size=18))
                return
                
            self.status_dot.configure(font=ctk.CTkFont(size=size))
            self.after(20, lambda: animate_pulse(step + 1))
            
        animate_pulse(1)

    def _show_saved_feedback(self):
        """Muestra feedback visual '✓ Guardado' temporal (A2)."""
        if hasattr(self, '_saved_label') and self._saved_label.winfo_exists():
            self._saved_label.destroy()
        self._saved_label = ctk.CTkLabel(self.settings_frame, text="✓ Guardado", 
                                         font=ctk.CTkFont(size=11), text_color=COLOR_GREEN)
        self._saved_label.pack(anchor="e", padx=20)
        self.after(2000, lambda: self._saved_label.destroy() if self._saved_label.winfo_exists() else None)

    def _check_steam_installed(self):
        """Verifica que Steam esté instalado en el sistema (B3)."""
        def check():
            steam_found = False
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", 0, winreg.KEY_READ)
                winreg.CloseKey(key)
                steam_found = True
            except Exception:
                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", 0, winreg.KEY_READ)
                    winreg.CloseKey(key)
                    steam_found = True
                except Exception:
                    pass
            if not steam_found:
                # Fallback: buscar en rutas comunes
                common_paths = [
                    os.path.expandvars(r"%ProgramFiles(x86)%\Steam\steam.exe"),
                    os.path.expandvars(r"%ProgramFiles%\Steam\steam.exe"),
                ]
                for p in common_paths:
                    if os.path.exists(p):
                        steam_found = True
                        break
            if not steam_found:
                self.after(0, lambda: styled_showwarning(self, "Steam no detectado", 
                    "No se ha detectado Steam instalado en este equipo.\n\n"
                    "La aplicación necesita Steam para lanzar Rust automáticamente.\n"
                    "Si Steam está instalado en una ubicación no estándar, puedes ignorar este aviso."))
                logger.warning("Steam no detectado en el sistema")
        threading.Thread(target=check, daemon=True).start()

    def load_steam_accounts(self):
        """Carga y parsea el archivo loginusers.vdf de Steam."""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
            winreg.CloseKey(key)
        except Exception:
            return []
        
        vdf_path = os.path.join(steam_path, "config", "loginusers.vdf")
        if not os.path.exists(vdf_path):
            return []
            
        try:
            with open(vdf_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error("Error leyendo loginusers.vdf: %s", e)
            return []
            
        import re
        users = []
        # Buscar bloques de cada SteamID de 17 dígitos
        blocks = re.findall(r'"(\d{17})"\s*\{([^}]+)\}', content, re.DOTALL)
        for steam_id, block_content in blocks:
            acc_match = re.search(r'"AccountName"\s*"([^"]+)"', block_content)
            pers_match = re.search(r'"PersonaName"\s*"([^"]+)"', block_content)
            mr_match = re.search(r'"MostRecent"\s*"([^"]+)"', block_content)
            
            if acc_match:
                account_name = acc_match.group(1)
                persona_name = pers_match.group(1) if pers_match else account_name
                is_most_recent = (mr_match.group(1) == "1") if mr_match else False
                users.append({
                    "steam_id": steam_id,
                    "account_name": account_name,
                    "persona_name": persona_name,
                    "most_recent": is_most_recent
                })
        return users

    def set_active_steam_account(self, target_account_name):
        """Configura el usuario por defecto en el registro y en loginusers.vdf."""
        # 1. Actualizar Registro (HKCU\Software\Valve\Steam)
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "AutoLoginUser", 0, winreg.REG_SZ, target_account_name)
            winreg.SetValueEx(key, "RememberPassword", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            logger.info("Registro Steam AutoLoginUser cambiado a: %s", target_account_name)
        except Exception as e:
            logger.error("Error al escribir registro de auto-inicio de Steam: %s", e)
            
        # 2. Actualizar loginusers.vdf (MostRecent y AllowAutoLogin)
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
            winreg.CloseKey(key)
        except Exception:
            return
            
        vdf_path = os.path.join(steam_path, "config", "loginusers.vdf")
        if not os.path.exists(vdf_path):
            return
            
        try:
            with open(vdf_path, "r", encoding="utf-8") as f:
                content = f.read()
                
            import re
            
            def replace_block(match):
                steam_id = match.group(1)
                block_content = match.group(2)
                
                acc_match = re.search(r'"AccountName"\s*"([^"]+)"', block_content)
                if acc_match:
                    acc_name = acc_match.group(1)
                    # Comparamos quitando espacios para evitar desajustes
                    is_target = (acc_name.strip() == target_account_name.strip())
                    
                    if re.search(r'"MostRecent"', block_content):
                        block_content = re.sub(r'("MostRecent"\s*)"[^"]+"', r'\1"{}"'.format("1" if is_target else "0"), block_content)
                    else:
                        block_content += f'\n\t\t"MostRecent"\t\t"{1 if is_target else 0}"'
                        
                    if re.search(r'"AllowAutoLogin"', block_content):
                        block_content = re.sub(r'("AllowAutoLogin"\s*)"[^"]+"', r'\1"{}"'.format("1" if is_target else "0"), block_content)
                    else:
                        block_content += f'\n\t\t"AllowAutoLogin"\t\t"{1 if is_target else 0}"'
                
                return f'"{steam_id}"\n\t{{{block_content}}}'
                
            new_content = re.sub(r'"(\d{17})"\s*\{([^}]+)\}', replace_block, content, flags=re.DOTALL)
            
            with open(vdf_path, "w", encoding="utf-8") as f:
                f.write(new_content)
            logger.info("loginusers.vdf actualizado correctamente para: %s", target_account_name)
        except Exception as e:
            logger.error("Error escribiendo en loginusers.vdf: %s", e)

    def on_steam_user_changed(self, choice_str):
        """Callback cuando el usuario cambia su cuenta de Steam en el combobox."""
        self.steam_dropdown.set(choice_str)
        import re
        match = re.search(r'\(([^)]+)\)$', choice_str)
        if match:
            account_name = match.group(1)
            self.settings["active_steam_user"] = account_name
            self.save_settings()
            
            self.set_active_steam_account(account_name)
            self._show_saved_feedback()

    def get_active_ip_from_bat(self):
        try:
            with open(self.startup_path, "r", encoding="utf-8") as f:
                match = re.search(r'\+connect\s+([^\s"]+)', f.read())
                if match: return match.group(1)
        except Exception: pass
        return None

    def check_status(self):
        # 1. Verificar Auto-Cola
        queue_active = False
        alias_display = ""
        if os.path.exists(self.startup_path):
            queue_active = True
            active_ip = self.get_active_ip_from_bat()
            alias_display = active_ip
            for alias, ip in self.servers_data.items():
                if ip == active_ip:
                    alias_display = alias
                    break
            if self.btn_activate.cget("text") != "ACTUALIZAR CONFIGURACIÓN":
                self.btn_activate.configure(text="ACTUALIZAR CONFIGURACIÓN")
        else:
            if self.btn_activate.cget("text") != "ACTIVAR AUTO-COLA":
                self.btn_activate.configure(text="ACTIVAR AUTO-COLA")

        # 2. Verificar Auto-Logon
        logon_active = False
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", 0, winreg.KEY_READ)
            val, _ = winreg.QueryValueEx(key, "AutoAdminLogon")
            winreg.CloseKey(key)
            if val == "1":
                logon_active = True
        except Exception: pass

        # 3. Lógica de TEXTO de Estado + indicador visual (A1)
        if not queue_active:
            if self.status_label.cget("text") != "INACTIVO":
                self.status_label.configure(text="INACTIVO", text_color=COLOR_INACTIVE)
                self.status_dot.configure(text_color=COLOR_INACTIVE)
                self.status_frame.configure(fg_color="#1a1a1a")
        elif queue_active and not logon_active:
            if self.status_label.cget("text") != "PENDIENTE DE CONFIGURACIÓN":
                self.status_label.configure(text="PENDIENTE DE CONFIGURACIÓN", text_color=COLOR_YELLOW)
                self.status_dot.configure(text_color=COLOR_YELLOW)
                self.status_frame.configure(fg_color="#2a2510")
        else:
            display = f"({alias_display})" if alias_display else ""
            target_text = f"TODO LISTO {display}"
            if self.status_label.cget("text") != target_text:
                self.status_label.configure(text=target_text, text_color=COLOR_GREEN)
                self.status_dot.configure(text_color=COLOR_GREEN)
                self.status_frame.configure(fg_color="#1a2a1a")

        # 4. Verificar Despertador (Software + Manual)
        wake_method = self.settings.get("wake_method")
        wake_active = False
        wake_label_text = "Modo Auto-Despertar"
        wake_color = "white"
        wake_border = COLOR_RUST_RED

        if wake_method == "software":
            try:
                res = subprocess.run(["schtasks", "/query", "/tn", "RustAutoQueueWake", "/fo", "LIST"], 
                                     capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW, text=True)
                if res.returncode == 0:
                    wake_active = True
                    match = re.search(r'(\d{1,2}:\d{2})', res.stdout)
                    t_str = f" ({match.group(1)})" if match else " (ON)"
                    wake_label_text = f"Auto-Despertar: SOFTWARE{t_str}"
            except Exception: pass
        elif wake_method == "smart_plug":
            wake_active = True
            wake_label_text = "Auto-Despertar: ENCHUFE SMART"
        elif wake_method == "bios":
            wake_active = True
            wake_label_text = "Auto-Despertar: BIOS RTC"

        if wake_active:
            wake_color = COLOR_GREEN
            wake_border = COLOR_GREEN
            
        if self.btn_auto_wake.cget("text") != wake_label_text:
            self.btn_auto_wake.configure(text=wake_label_text, border_color=wake_border, text_color=wake_color)

        # 5. Actualizar status_wake_label (segunda línea del header)
        if wake_active:
            if self.status_wake_label.cget("text") != wake_label_text:
                self.status_wake_label.configure(text=wake_label_text, text_color=COLOR_GREEN)
        else:
            if self.status_wake_label.cget("text") != "Sin despertador configurado":
                self.status_wake_label.configure(text="Sin despertador configurado", text_color="#555555")

        # 6. Resumen en el status principal si todo está OK
        if queue_active and logon_active:
            display = f"({alias_display})" if alias_display else ""
            target_text = f"TODO LISTO {display}"
            if self.status_label.cget("text") != target_text:
                self.status_label.configure(text=target_text, text_color=COLOR_GREEN)
                self.status_dot.configure(text_color=COLOR_GREEN)
                self.status_frame.configure(fg_color="#1a2a1a")

    def activate_auto_queue(self):
        # Animación visual del botón
        self._flash_activate_button()

        # 1. Validación de IP de Servidor
        raw_ip = self.get_current_ip_from_entry()
        ip = raw_ip
        if ip.startswith("client.connect"):
            ip = ip[14:].strip()
        elif ip.startswith("connect"):
            ip = ip[7:].strip()
        
        if not ip:
            styled_showwarning(self, "Falta dirección", "Por favor, introduce la IP o dominio del servidor de Rust.")
            return
        if not IP_PORT_RE.match(ip):
            styled_showwarning(self, "Formato incorrecto",
                f"La dirección '{ip}' no parece válida.\nDebe ser una IP o dominio (con o sin puerto).\nEjemplos:\n- 192.168.1.100:28015\n- jugar.rustserver.com:28015")
            return

        # 2. Validación de Contraseña
        password = self.pw_entry.get()
        if not password:
            if not styled_askyesno(self, "Aviso", "No has introducido tu contraseña de Windows de AutoLogon. ¿Quieres activar la auto-cola sin configurar el AutoLogon de la cuenta? (Si tienes el PC con código/clave el arranque se quedará bloqueado en la pantalla).", height=280):
                return

        # Aviso de seguridad sobre contraseña en el registro (D1)
        if password and not self.settings.get("password_warning_shown", False):
            if not styled_askyesno(self, "⚠️ Aviso de Seguridad",
                "Tu contraseña se almacenará en el registro de Windows (Winlogon).\n\n"
                "Esto es el comportamiento estándar del AutoLogon de Windows,\n"
                "pero implica que cualquier persona con acceso al PC podría leerla.\n\n"
                "¿Deseas continuar?", height=280):
                return
            self.settings["password_warning_shown"] = True
            self.save_settings()

        # Asegurar que se configure la cuenta de Steam elegida
        active_steam_user = self.settings.get("active_steam_user")
        if active_steam_user:
            self.set_active_steam_account(active_steam_user)

        # ACCIÓN A: Escribir credenciales en Registro (Winlogon)
        if password:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "AutoAdminLogon", 0, winreg.REG_SZ, "1")
                winreg.SetValueEx(key, "DefaultUserName", 0, winreg.REG_SZ, self.sys_user)
                winreg.SetValueEx(key, "DefaultDomainName", 0, winreg.REG_SZ, self.sys_domain)
                winreg.SetValueEx(key, "DefaultPassword", 0, winreg.REG_SZ, password)
                winreg.CloseKey(key)
            except Exception as e:
                styled_showerror(self, "Error Sistema", f"No se pudo modificar el registro de AutoLogon.\nPor favor reinicia la aplicación asegurándote de que aceptaste los permisos de Administrador.\nError: {e}")
                return

        # ACCIÓN B: Generar .bat
        delay = int(self.delay_slider.get())
        one_time = self.one_time_var.get()
        smart_wipe = self.smart_wipe_var.get()
        
        if smart_wipe:
            import sys, os
            is_compiled = getattr(sys, 'frozen', False)
            if is_compiled:
                exe_cmd = f'start "" "{sys.executable}" --smart-wipe {ip}'
            else:
                exe_cmd = f'start "" "{sys.executable}" "{os.path.abspath(__file__)}" --smart-wipe {ip}'
        else:
            exe_cmd = f'start explorer.exe "steam://run/252490//+connect%20{ip}%20+aq%20{int(time.time())}"'

        if one_time:
            bat_content = (
                f'@echo off\n'
                f'timeout /t {delay} /nobreak\n'
                f'{exe_cmd}\n'
                f'timeout /t 5 /nobreak\n'
                f'del "%~f0"\n'
            )
        else:
            bat_content = f'@echo off\ntimeout /t {delay} /nobreak\n{exe_cmd}\n'
        
        try:
            with open(self.startup_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
            self.check_status()
            logger.info("Auto-cola ACTIVADA - IP: %s, Delay: %ds, OneTime: %s", ip, delay, one_time)
            styled_showinfo(self, "Éxito", "¡Operación completada con éxito!\n\nSe ha configurado el inicio automático de usuario de Windows y se lanzará Rust automáticamente al encender.")
        except Exception as e:
            styled_showerror(self, "Error Archivo", f"No se pudo crear el archivo:\n{str(e)}")

    def deactivate_auto_queue(self):
        # ACCIÓN A: Limpiar Registro (Winlogon)
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "AutoAdminLogon", 0, winreg.REG_SZ, "0")
            try:
                winreg.DeleteValue(key, "DefaultPassword")
            except Exception:
                pass
            winreg.CloseKey(key)
        except Exception as e:
            logger.warning("Error limpiando registro Winlogon: %s", e)

        # ACCIÓN B: Borrar .bat
        try:
            if os.path.exists(self.startup_path):
                os.remove(self.startup_path)
            self.check_status()
            logger.info("Auto-cola DESACTIVADA")
            styled_showinfo(self, "Desactivado", "Todo se ha limpiado correctamente. Tu ordenador volverá a pedir contraseña como de costumbre al arrancar.")
        except Exception as e:
            logger.error("Error borrando .bat de startup: %s", e)

    def test_connection(self):
        """Prueba la conexión al servidor usando subprocess (D3)."""
        raw_ip = self.get_current_ip_from_entry()
        ip = raw_ip
        if ip.startswith("client.connect"):
            ip = ip[14:].strip()
        elif ip.startswith("connect"):
            ip = ip[7:].strip()
            
        if not ip: return
        if not IP_PORT_RE.match(ip):
            styled_showwarning(self, "Formato incorrecto", f"La dirección '{ip}' no parece válida.")
            return

        # Aplicar la cuenta activa antes de probar
        active_steam_user = self.settings.get("active_steam_user")
        if active_steam_user:
            self.set_active_steam_account(active_steam_user)

        try:
            subprocess.Popen(['explorer.exe', f'steam://run/252490//+connect%20{ip}%20+aq%20{int(time.time())}'],
                            creationflags=subprocess.CREATE_NO_WINDOW)
            logger.info("Test de conexión lanzado: %s", ip)
        except Exception as e:
            logger.error("Error al probar conexión: %s", e)

    def create_home_page(self):
        home_page = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        self.pages["home"] = home_page
        
        home_page.grid_columnconfigure(0, weight=1, uniform="col")
        home_page.grid_columnconfigure(1, weight=1, uniform="col")
        home_page.grid_rowconfigure(0, weight=1)
        
        # Column 0: Configuration
        col0 = ctk.CTkFrame(home_page, fg_color="transparent")
        col0.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        lbl_title = ctk.CTkLabel(col0, text="PARÁMETROS", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=COLOR_RUST_RED)
        lbl_title.pack(anchor="w", pady=(0, 15))
        
        # Section 1: Server Selection
        ip_label = ctk.CTkLabel(col0, text="Seleccionar Servidor:", font=self.font_label, text_color="white")
        ip_label.pack(anchor="w", pady=(5, 2))
        
        self.ip_frame = ctk.CTkFrame(col0, fg_color="transparent")
        self.ip_frame.pack(fill="x", pady=(0, 10))
        
        server_aliases = list(self.servers_data.keys())
        if not server_aliases:
            server_aliases = ["💡 Añade un servidor (Pestaña 'Servidores')"]
            
        self.ip_entry = ctk.CTkOptionMenu(
            self.ip_frame,
            values=server_aliases,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color="#101012",
            button_color="#2b2b2b",
            button_hover_color="#3b3b3b"
        )
        self.ip_entry.pack(fill="x", expand=True)
        
        self.ip_dropdown = CTkScrollableDropdown(self.ip_entry, values=server_aliases, command=self.on_home_server_selected,
                              fg_color="#18181a", button_color="transparent", hover_color="#2b2b2f",
                              frame_border_color="#333335", frame_corner_radius=8, text_color="white", alpha=1.0)

        if not self.servers_data:
            self.ip_entry.set("💡 Añade un servidor (Pestaña 'Servidores')")
        else:
            self.ip_entry.set("Selecciona un servidor...")

        self.home_card = ctk.CTkFrame(col0, fg_color="#18181a", border_width=1, border_color="#2b2b2f", corner_radius=8)
        
        self.hc_title = ctk.CTkLabel(self.home_card, text="Esperando selección...", font=self.font_label, text_color="#aaaaaa", anchor="w")
        self.hc_title.pack(fill="x", padx=10, pady=(8, 2))
        
        hc_stats = ctk.CTkFrame(self.home_card, fg_color="transparent")
        hc_stats.pack(fill="x", padx=10, pady=(2, 2))
        
        self.hc_status = ctk.CTkLabel(hc_stats, text=" ● ", font=ctk.CTkFont(size=10, weight="bold"), text_color="#555")
        self.hc_status.pack(side="left")
        
        self.hc_ping = ctk.CTkLabel(hc_stats, text="Ping: --", font=ctk.CTkFont(size=11), text_color="#888")
        self.hc_ping.pack(side="left", padx=(5, 0))
        
        hc_players_frame = ctk.CTkFrame(self.home_card, fg_color="transparent")
        hc_players_frame.pack(fill="x", padx=10, pady=(0, 8))
        
        self.hc_players = ctk.CTkLabel(hc_players_frame, text="--/-- PLAYERS", font=ctk.CTkFont(size=11, weight="bold"), text_color="#ccc")
        self.hc_players.pack(side="left", padx=(5, 0))
        
        # Section 2: Delay Slider
        delay_lbl = ctk.CTkLabel(col0, text="Retraso de Inicio (segundos):", font=self.font_label, text_color="white")
        delay_lbl.pack(anchor="w", pady=(10, 2))
        
        delay_frame = ctk.CTkFrame(col0, fg_color="transparent")
        delay_frame.pack(fill="x", pady=(0, 10))
        
        start_delay = self.settings.get("delay", 10)
        
        self.delay_slider = ctk.CTkSlider(
            delay_frame,
            from_=5,
            to=300,
            number_of_steps=295,
            command=self.update_delay_label,
            progress_color=COLOR_RUST_RED,
            button_color=COLOR_RUST_RED,
            button_hover_color=COLOR_RUST_HOVER
        )
        self.delay_slider.set(start_delay)
        self.delay_slider.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.delay_value_label = ctk.CTkLabel(delay_frame, text=f"{start_delay}s", font=self.font_subtitle, text_color="white", width=40)
        self.delay_value_label.pack(side="right")
        
        # Section 3: Steam Switcher (combobox)
        steam_lbl = ctk.CTkLabel(col0, text="Cuenta de Steam Activa:", font=self.font_label, text_color="white")
        steam_lbl.pack(anchor="w", pady=(10, 2))
        
        self.settings_frame = ctk.CTkFrame(col0, fg_color="transparent")
        self.settings_frame.pack(fill="x", pady=(0, 10))
        
        steam_choices = []
        default_choice = None
        
        for user in self.steam_users:
            display_str = f"{user['persona_name']} ({user['account_name']})"
            steam_choices.append(display_str)
            if user.get("most_recent") or user['account_name'] == self.settings.get("active_steam_user"):
                default_choice = display_str
                
        if not steam_choices:
            steam_choices = ["No se detectaron cuentas locales"]
            default_choice = steam_choices[0]
        elif not default_choice:
            default_choice = steam_choices[0]
            
        self.steam_dropdown = ctk.CTkOptionMenu(
            self.settings_frame,
            values=steam_choices,
            height=36,
            font=self.font_text,
            fg_color="#1a1a1c",
            button_color="#1a1a1c",
            button_hover_color="#2a2a2c"
        )
        self.steam_dropdown.set(default_choice)
        self.steam_dropdown.pack(fill="x")
        
        CTkScrollableDropdown(self.steam_dropdown, values=steam_choices, command=self.on_steam_user_changed,
                              fg_color="#1e1e1f", button_color="transparent", hover_color="#2b2b2d",
                              frame_border_color="#333335", frame_corner_radius=8, text_color="white", alpha=1.0)
        
        # Section 4: One-time checkbox
        self.one_time_var = tk.BooleanVar(value=self.settings.get("one_time_mode", False))
        self.chk_one_time = ctk.CTkCheckBox(
            col0,
            text="Ejecutar una sola vez y desactivar",
            variable=self.one_time_var,
            onvalue=True,
            offvalue=False,
            command=self._save_one_time_setting,
            font=self.font_text,
            fg_color=COLOR_RUST_RED,
            border_color="#333335",
            hover_color="#2b2b2b"
        )
        self.chk_one_time.pack(anchor="w", pady=(15, 10))
        
        # Section 5: Smart Wipe Mode
        smart_wipe_frame = ctk.CTkFrame(col0, fg_color="transparent")
        smart_wipe_frame.pack(fill="x", pady=(0, 10))
        
        self.smart_wipe_var = tk.BooleanVar(value=self.settings.get("smart_wipe", False))
        self.chk_smart_wipe = ctk.CTkSwitch(
            smart_wipe_frame,
            text="Modo Wipe Inteligente",
            variable=self.smart_wipe_var,
            onvalue=True,
            offvalue=False,
            command=self._save_smart_wipe_setting,
            font=self.font_text,
            button_color=COLOR_RUST_RED,
            button_hover_color="#b3241b",
            progress_color="#441a18"
        )
        self.chk_smart_wipe.pack(side="left")
        
        # Info box explaining how it works (Moved to right column)
        
        # (Info box removed to keep UI clean and avoid squishing)
        
        # Column 1: System Status & Activation
        col1 = ctk.CTkFrame(home_page, fg_color="transparent")
        col1.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        
        lbl_status_title = ctk.CTkLabel(col1, text="ESTADO DEL SISTEMA", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=COLOR_RUST_RED)
        lbl_status_title.pack(anchor="w", pady=(0, 15))
        
        self.status_frame = ctk.CTkFrame(col1, fg_color="#1a1a1a", border_width=1, border_color="#2d2d2d", corner_radius=10, height=80)
        self.status_frame.pack(fill="x", pady=(0, 15))
        self.status_frame.pack_propagate(False)
        
        status_inner = ctk.CTkFrame(self.status_frame, fg_color="transparent")
        status_inner.pack(side="left", fill="both", expand=True, padx=15, pady=12)
        
        status_title_frame = ctk.CTkFrame(status_inner, fg_color="transparent")
        status_title_frame.pack(fill="x", anchor="w")
        
        self.status_dot = ctk.CTkLabel(status_title_frame, text="●", font=ctk.CTkFont(size=18), text_color=COLOR_INACTIVE, width=24)
        self.status_dot.pack(side="left", padx=(0, 8))
        
        self.status_label = ctk.CTkLabel(status_title_frame, text="INACTIVO", font=self.font_subtitle, text_color=COLOR_INACTIVE, anchor="w")
        self.status_label.pack(side="left")
        
        self.status_wake_label = ctk.CTkLabel(status_inner, text="Sin despertador configurado", font=self.font_small, text_color="#555555", anchor="w")
        self.status_wake_label.pack(fill="x", anchor="w", padx=(22, 0))
        
        # Windows password
        pw_label = ctk.CTkLabel(col1, text="Contraseña de Windows (AutoLogon):", font=self.font_label, text_color="white")
        pw_label.pack(anchor="w", pady=(5, 2))
        
        pw_frame = ctk.CTkFrame(col1, fg_color="transparent")
        pw_frame.pack(fill="x", pady=(0, 10))
        
        self.pw_entry = ctk.CTkEntry(
            pw_frame,
            placeholder_text="Contraseña de Windows",
            show="*",
            height=36,
            font=self.font_text,
            fg_color="#1a1a1c",
            border_color="#333335"
        )
        self.pw_entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        Tooltip(self.pw_entry, "La contraseña del usuario de Windows para iniciar sesión de forma automática tras encender.")
        
        self.icon_eye = ctk.CTkImage(light_image=Image.open(get_asset_path("icons/eye.png")), size=(18, 18)) if os.path.exists(get_asset_path("icons/eye.png")) else None
        self.icon_eye_off = ctk.CTkImage(light_image=Image.open(get_asset_path("icons/eye_off.png")), size=(18, 18)) if os.path.exists(get_asset_path("icons/eye_off.png")) else None
        
        def toggle_password():
            if self.pw_entry.cget("show") == "*":
                self.pw_entry.configure(show="")
                btn_toggle_pw.configure(image=self.icon_eye_off)
            else:
                self.pw_entry.configure(show="*")
                btn_toggle_pw.configure(image=self.icon_eye)
                
        btn_toggle_pw = ctk.CTkButton(
            pw_frame,
            text="",
            image=self.icon_eye,
            width=36,
            height=36,
            fg_color="#2b2b2b",
            hover_color="#3b3b3b",
            command=toggle_password
        )
        btn_toggle_pw.pack(side="left", padx=(0, 5))
        
        btn_verify_pw = ctk.CTkButton(
            pw_frame,
            text="Verificar",
            width=80,
            height=36,
            fg_color="#2b2b2b",
            hover_color="#3b3b3b",
            font=self.font_label,
            command=self.test_windows_password
        )
        btn_verify_pw.pack(side="right")
        
        # Action Buttons
        self.btn_activate = ctk.CTkButton(
            col1,
            text="ACTIVAR AUTO-COLA",
            height=48,
            fg_color=COLOR_RUST_RED,
            hover_color=COLOR_RUST_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            command=self.activate_auto_queue
        )
        self.btn_activate.pack(fill="x", pady=(20, 8))
        
        self.btn_deactivate = ctk.CTkButton(
            col1,
            text="DESACTIVAR Y LIMPIAR",
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color="#333335",
            hover_color="#1f1f21",
            text_color="#aaaaaa",
            font=self.font_label,
            command=self.deactivate_auto_queue
        )
        self.btn_deactivate.pack(fill="x", pady=0)
        
        self.btn_auto_wake = ctk.CTkButton(
            col1,
            text="Configurar Auto-Despertar",
            height=36,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_RUST_RED,
            hover_color="#2b1e1b",
            text_color="white",
            font=self.font_label,
            command=lambda: self.switch_page("wake")
        )
        self.btn_auto_wake.pack(fill="x", pady=(8, 8))
        
        btn_test = ctk.CTkButton(
            col1,
            text="PROBAR CONEXIÓN AHORA",
            height=36,
            fg_color="#1a2b3a",
            hover_color="#203a50",
            border_width=1,
            border_color=COLOR_BLUE,
            text_color=COLOR_BLUE,
            font=self.font_label,
            command=self.test_connection
        )
        btn_test.pack(fill="x", pady=0)
        
        # Info Box (Bottom Right)
        info_card = ctk.CTkFrame(col1, fg_color="#18181b", border_width=1, border_color="#2b2b2f", corner_radius=8)
        info_card.pack(fill="both", expand=True, pady=(20, 0))
        
        info_txt = ("ℹ️ ¿Cómo funciona?\n\n"
                    "Al encender el PC, se iniciará sesión automáticamente y Steam abrirá directamente el servidor elegido.\n\n"
                    "💡 Modo Wipe Inteligente:\n"
                    "Espera de forma invisible al reinicio del servidor y te conecta al milisegundo exacto.")
        ctk.CTkLabel(info_card, text=info_txt, font=self.font_small, text_color="#888888", justify="left", wraplength=260).pack(padx=12, pady=12, anchor="nw")

    def _run_snipe_thread(self, ip, lbl_status, btn_snipe, run_id=None):
        import socket, time, subprocess
        host = ip.split(":")[0] if ":" in ip else ip
        port = int(ip.split(":")[1]) if ":" in ip else 28015
        
        def is_active():
            return self.is_sniping and (run_id is None or getattr(self, 'snipe_run_id', None) == run_id)

        # Fase 1: Esperar a que el servidor se apague
        self.after(0, lambda: is_active() and lbl_status.configure(text="Fase 1: Esperando Wipe (Servidor Online...)", text_color="#aaaaaa"))
        
        def check_online():
            for test_port in list(dict.fromkeys([port, port + 1, port + 15])):
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(0.5)
                try:
                    sock.sendto(b'\xFF\xFF\xFF\xFFTSource Engine Query\x00', (host, test_port))
                    data, _ = sock.recvfrom(4096)
                    if data.startswith(b'\xFF\xFF\xFF\xFFI'):
                        try:
                            idx = 5
                            for _ in range(4): idx = data.find(b'\x00', idx) + 1
                            idx += 9
                            idx = data.find(b'\x00', idx) + 1
                            if idx < len(data):
                                edf = data[idx]
                                idx += 1
                                if edf & 0x80:
                                    import struct
                                    reported_port = struct.unpack_from('<H', data, idx)[0]
                                    if test_port != port and reported_port != port: 
                                        continue
                        except: pass
                        return True
                except Exception: pass
                finally: sock.close()
            return False

        attempts = 0
        was_online = False
        if check_online():
            was_online = True
            failed_pings = 0
            while is_active():
                if not check_online():
                    failed_pings += 1
                    if failed_pings >= 3:
                        break
                else:
                    failed_pings = 0
                    
                attempts += 1
                self.after(0, lambda a=attempts: is_active() and lbl_status.configure(text=f"Fase 1: Esperando Wipe (Servidor Online...) | Intentos: {a}", text_color="#aaaaaa"))
                time.sleep(3.0)
                
        if not is_active():
            return
            
        # Fase 2: El servidor está offline.
        self.after(0, lambda: is_active() and lbl_status.configure(text=f"Fase 2: Wipe en proceso. Esperando A2S...", text_color="#ffcc00"))
        attempts = 0
        while is_active():
            attempts += 1
            if check_online():
                break
                
            msg = f"Fase 2: Wipe en proceso. Esperando A2S... | Pings: {attempts}"
            self.after(0, lambda m=msg: is_active() and lbl_status.configure(text=m, text_color="#ffcc00"))
            time.sleep(0.5)
            
        if not is_active():
            return
            
        # Conectado!
        self.is_sniping = False
        self.after(0, lambda: lbl_status.configure(text="¡SERVIDOR ONLINE! Conectando en 0ms...", text_color="#00ff00"))
        self.after(0, lambda: btn_snipe.configure(text="COMENZAR SPAM", fg_color=COLOR_RUST_RED, hover_color=COLOR_RUST_HOVER))
        
        try:
            import winsound
            winsound.Beep(1000, 300)
            time.sleep(0.1)
            winsound.Beep(1500, 600)
        except: pass

        try:
            subprocess.Popen(['explorer.exe', f'steam://run/252490//+connect%20{ip}%20+aq%20{int(time.time())}'], creationflags=subprocess.CREATE_NO_WINDOW)
            logger.info("Snipe Wipe: Conexión lanzada: %s", ip)
        except Exception as e:
            logger.error("Error al probar conexión: %s", e)
            
    def _test_snipe_connection(self):
        raw_val = self.snipe_ip_entry.get().strip()
        if not raw_val or raw_val == "Selecciona un servidor..." or "💡" in raw_val:
            styled_showwarning(self, "Selecciona Servidor", "Por favor selecciona un servidor de la lista primero.")
            return
            
        ip = raw_val
        if ip in self.servers_data:
            s_data = self.servers_data[ip]
            if isinstance(s_data, dict):
                ip = s_data.get("ip", "")
            else:
                ip = s_data
                
        if ip.startswith("client.connect"):
            ip = ip[14:].strip()
        elif ip.startswith("connect"):
            ip = ip[7:].strip()
            
        if not ip or not IP_PORT_RE.match(ip):
            styled_showwarning(self, "Formato incorrecto", f"La dirección '{ip}' no parece válida.")
            return

        import subprocess
        try:
            subprocess.Popen(['explorer.exe', f'steam://run/252490//+connect%20{ip}%20+aq%20{int(time.time())}'], creationflags=subprocess.CREATE_NO_WINDOW)
            styled_showinfo(self, "Prueba de Conexión", f"Se ha enviado la petición a Steam para conectar a:\n{ip}\n\nRevisa Rust, debería estar conectándose al servidor.")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"No se pudo lanzar el juego:\n{e}")
            
    def _toggle_snipe(self, lbl_status, btn_snipe):
        if getattr(self, 'is_sniping', False):
            self.is_sniping = False
            self.snipe_run_id = None
            lbl_status.configure(text="Spam Cancelado.", text_color="#ff5555")
            btn_snipe.configure(text="COMENZAR SPAM", fg_color=COLOR_RUST_RED, hover_color=COLOR_RUST_HOVER)
            return

        raw_val = self.snipe_ip_entry.get().strip()
        if not raw_val or raw_val == "Selecciona un servidor..." or "💡" in raw_val:
            styled_showwarning(self, "Selecciona Servidor", "Por favor selecciona un servidor de la lista primero.")
            return
            
        ip = raw_val
        if raw_val in self.servers_data:
            data = self.servers_data[raw_val]
            ip = data["ip"] if isinstance(data, dict) else data
            
        if ip.startswith("client.connect"):
            ip = ip[14:].strip()
        elif ip.startswith("connect"):
            ip = ip[7:].strip()
            
        if not ip or not IP_PORT_RE.match(ip):
            styled_showwarning(self, "Formato incorrecto", f"La dirección '{ip}' no parece válida.")
            return

        # Start sniping
        self.is_sniping = True
        import time
        self.snipe_run_id = time.time()
        lbl_status.configure(text="Iniciando motor de Spam...", text_color="#aaaaaa")
        btn_snipe.configure(text="CANCELAR SPAM", fg_color="#ff5555", hover_color="#cc4444")
        
        import threading
        self.snipe_thread = threading.Thread(target=self._run_snipe_thread, args=(ip, lbl_status, btn_snipe, self.snipe_run_id), daemon=True)
        self.snipe_thread.start()

    def create_snipe_page(self):
        snipe_page = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        self.pages["snipe"] = snipe_page
        
        snipe_page.grid_columnconfigure(0, weight=1)
        snipe_page.grid_rowconfigure(2, weight=1)
        
        # Header
        header = ctk.CTkFrame(snipe_page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        lbl_title = ctk.CTkLabel(header, text="WIPE-SPAM", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=COLOR_RUST_RED)
        lbl_title.pack(side="left")
        
        # Info Box
        info_card = ctk.CTkFrame(snipe_page, fg_color="#18181b", border_width=1, border_color="#2b2b2f", corner_radius=8)
        info_card.grid(row=1, column=0, sticky="ew", padx=20, pady=(10, 20))
        
        info_txt = ("⚡ ¿Qué es el Wipe-Spam?\n\n"
                    "Esta herramienta está diseñada para usarse en vivo mientras estás frente a tu PC. "
                    "Al activarla, bombardeará el servidor con pings invisibles cada pocos milisegundos. "
                    "En el instante exacto en que el servidor reinicie por el wipe, la app lanzará la conexión en 0ms, "
                    "permitiéndote saltarte la cola de espera y entrar de los primeros.\n\n"
                    "💡 Recomendación: Ten el juego abierto en el menú principal para que la conexión sea instantánea.")
        ctk.CTkLabel(info_card, text=info_txt, font=self.font_small, text_color="#aaaaaa", justify="left", wraplength=480).pack(padx=15, pady=15, anchor="nw")
        
        # Main controls
        controls_frame = ctk.CTkFrame(snipe_page, fg_color="#141416", border_width=1, border_color="#2b2b2f", corner_radius=8)
        controls_frame.grid(row=2, column=0, sticky="nsew", padx=20, pady=(0, 20))
        controls_frame.grid_columnconfigure(0, weight=1)
        
        ctk.CTkLabel(controls_frame, text="1. Selecciona tu Servidor Objetivo", font=ctk.CTkFont(size=14, weight="bold"), text_color="white").pack(pady=(30, 10))
        
        server_aliases = list(self.servers_data.keys())
        if not server_aliases:
            server_aliases = ["💡 Añade un servidor primero"]
            
        self.snipe_ip_entry = ctk.CTkOptionMenu(
            controls_frame,
            values=server_aliases,
            height=45, width=300,
            font=ctk.CTkFont(size=14),
            fg_color="#101012",
            button_color="#2b2b2b",
            button_hover_color="#3b3b3b"
        )
        self.snipe_ip_entry.pack(pady=(0, 30))
        
        def on_snipe_server_selected(choice_str):
            self.snipe_ip_entry.set(choice_str)
            
        self.snipe_dropdown = CTkScrollableDropdown(self.snipe_ip_entry, values=server_aliases, command=on_snipe_server_selected,
                              fg_color="#18181a", button_color="transparent", hover_color="#2b2b2f",
                              frame_border_color="#333335", frame_corner_radius=8, text_color="white", alpha=1.0)
                              
        if not self.servers_data:
            self.snipe_ip_entry.set("💡 Añade un servidor primero")
        else:
            self.snipe_ip_entry.set("Selecciona un servidor...")
            
        # Status Radar
        radar_frame = ctk.CTkFrame(controls_frame, fg_color="#0a0a0c", border_width=1, border_color="#1f1f22", corner_radius=8, height=80)
        radar_frame.pack(fill="x", padx=40, pady=(10, 30))
        radar_frame.pack_propagate(False)
        
        lbl_status = ctk.CTkLabel(radar_frame, text="Esperando objetivo...", font=ctk.CTkFont(family="Consolas", size=14), text_color="#555555")
        lbl_status.pack(expand=True)
        
        button_frame = ctk.CTkFrame(controls_frame, fg_color="transparent")
        button_frame.pack(pady=(0, 30))
        
        # Modo selector removido
        
        actions_frame = ctk.CTkFrame(button_frame, fg_color="transparent")
        actions_frame.pack(side="top")
        btn_snipe = ctk.CTkButton(
            actions_frame,
            text="COMENZAR SPAM",
            height=55, width=160,
            fg_color=COLOR_RUST_RED,
            hover_color=COLOR_RUST_HOVER,
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
        )
        btn_snipe.configure(command=lambda: self._toggle_snipe(lbl_status, btn_snipe))
        btn_snipe.pack(side="left", padx=(0, 10))
        
        btn_test = ctk.CTkButton(
            actions_frame,
            text="PROBAR CONEXIÓN\n(RUST ABIERTO)",
            height=55, width=130,
            fg_color="#184a8c",
            hover_color="#123768",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._test_snipe_connection
        )
        btn_test.pack(side="left")

    def create_servers_page(self):
        servers_page = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        self.pages["servers"] = servers_page
        
        servers_page.grid_columnconfigure(0, weight=1)
        servers_page.grid_rowconfigure(2, weight=1)
        
        # Header
        header = ctk.CTkFrame(servers_page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        lbl_title = ctk.CTkLabel(header, text="MIS SERVIDORES", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=COLOR_RUST_RED)
        lbl_title.pack(side="left")
        
        btn_refresh = ctk.CTkButton(header, text="↻ Refresh", width=70, height=28, fg_color="transparent", border_width=1, border_color="#333", hover_color="#222", font=ctk.CTkFont(size=12, weight="bold"), command=lambda: self.refresh_server_list(servers_page))
        btn_refresh.pack(side="right")
        
        # Add server inline frame (form)
        form_frame = ctk.CTkFrame(servers_page, fg_color="#18181b", border_width=1, border_color="#2b2b2f", corner_radius=8)
        form_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=5)
        
        ctk.CTkLabel(form_frame, text="Añadir Servidor:", font=self.font_label, text_color="white").grid(row=0, column=0, columnspan=3, sticky="w", padx=12, pady=(8, 2))
        
        self.new_alias_entry = ctk.CTkEntry(form_frame, placeholder_text="Alias (Ej. Rustafied EU)", font=self.font_text, height=32, fg_color="#101012", border_color="#333")
        self.new_alias_entry.grid(row=1, column=0, sticky="ew", padx=(12, 5), pady=(0, 12))
        
        self.new_ip_entry = ctk.CTkEntry(form_frame, placeholder_text="IP:Puerto o Dominio", font=self.font_text, height=32, fg_color="#101012", border_color="#333")
        self.new_ip_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=(0, 12))
        
        btn_add = ctk.CTkButton(form_frame, text="Añadir", font=self.font_label, fg_color=COLOR_RUST_RED, hover_color=COLOR_RUST_HOVER, height=32, command=self.add_new_server_inline)
        btn_add.grid(row=1, column=2, sticky="e", padx=(5, 12), pady=(0, 12))
        
        disclaimer_lbl = ctk.CTkLabel(form_frame, text="💡 Consejo: Si la app identifica un servidor erróneo o no carga la imagen,\nasegúrate de incluir el puerto numérico al final de la IP o dominio (ej. :28024).", font=ctk.CTkFont(size=11, slant="italic"), text_color="#cccccc", justify="left")
        disclaimer_lbl.grid(row=2, column=0, columnspan=3, sticky="w", padx=12, pady=(0, 10))
        
        btn_explore = ctk.CTkButton(form_frame, text="🔍 Explorar Servidores Destacados", font=self.font_label, fg_color="#2b2b2b", hover_color="#3b3b3b", border_width=1, border_color="#444", height=32, command=self.open_featured_servers_modal)
        btn_explore.grid(row=3, column=0, columnspan=3, sticky="ew", padx=12, pady=(0, 12))
        
        form_frame.grid_columnconfigure(0, weight=1)
        form_frame.grid_columnconfigure(1, weight=1)
        
        # Scrollable list frame
        self.scroll_servers = ctk.CTkScrollableFrame(servers_page, fg_color="transparent")
        self.scroll_servers.grid(row=2, column=0, sticky="nsew", padx=20, pady=10)
        
        # Footer / Import/Export Controls
        footer = ctk.CTkFrame(servers_page, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(5, 20))
        
        btn_export = ctk.CTkButton(footer, text="Exportar Lista", width=120, height=32,
                                    fg_color="#2b2b2b", hover_color="#3b3b3b", border_width=1, border_color="#444",
                                    font=self.font_label, command=self._export_servers)
        btn_export.pack(side="left", padx=(0, 10))
        
        btn_import = ctk.CTkButton(footer, text="Importar Lista", width=120, height=32,
                                    fg_color="#2b2b2b", hover_color="#3b3b3b", border_width=1, border_color="#444",
                                    font=self.font_label, command=lambda: self._import_servers(servers_page))
        btn_import.pack(side="left")
        
        self.lbl_server_count = ctk.CTkLabel(footer, text="0 servidores", font=self.font_small, text_color="#777")
        self.lbl_server_count.pack(side="right")
        
        self.refresh_server_list(servers_page)

    def add_new_server_inline(self):
        alias = self.new_alias_entry.get().strip()
        ip = self.new_ip_entry.get().strip()
        
        if ip.startswith("client.connect"):
            ip = ip[14:].strip()
        elif ip.startswith("connect"):
            ip = ip[7:].strip()
            
        if not alias or not ip:
            styled_showwarning(self, "Campos vacíos", "Por favor, introduce tanto el alias como la dirección IP/Dominio.")
            return
            
        if not IP_PORT_RE.match(ip):
            styled_showwarning(self, "Formato incorrecto",
                f"La dirección '{ip}' no parece válida.\nDebe ser una IP o dominio (con o sin puerto).\nEjemplos:\n- 192.168.1.100:28015\n- jugar.rustserver.com:28015")
            return
            
        self.servers_data[alias] = {"ip": ip, "fav": False}
        self.save_servers()
        
        self.new_alias_entry.delete(0, 'end')
        self.new_ip_entry.delete(0, 'end')
        
        self.refresh_server_list(self.pages["servers"])
        ToastNotification.show(self, f"Servidor añadido: {alias}")

    def open_featured_servers_modal(self):
        modal = ctk.CTkToplevel(self)
        modal.title("Servidores Destacados")
        modal.geometry("600x500")
        modal.configure(fg_color="#121212")
        modal.transient(self)
        modal.grab_set()

        # Center the modal
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 600) // 2
        y = self.winfo_y() + (self.winfo_height() - 500) // 2
        modal.geometry(f"+{x}+{y}")

        title_lbl = ctk.CTkLabel(modal, text="🏆 SERVIDORES DESTACADOS", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=COLOR_RUST_RED)
        title_lbl.pack(pady=(20, 10))

        subtitle_lbl = ctk.CTkLabel(modal, text="Selección Gourmet de las mejores redes de Rust. Añádelos con un solo clic.", font=self.font_text, text_color="#aaaaaa")
        subtitle_lbl.pack(pady=(0, 20))

        scroll = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        def add_featured(srv_alias, srv_ip):
            if srv_alias in self.servers_data:
                styled_showinfo(modal, "Aviso", "¡Este servidor ya está en tu lista!")
                return
            self.servers_data[srv_alias] = {"ip": srv_ip, "fav": False}
            self.save_servers()
            self.refresh_server_list(self.pages.get("servers", self))
            ToastNotification.show(modal, f"Añadido: {srv_alias}")

        for srv in FEATURED_SERVERS:
            row_frame = ctk.CTkFrame(scroll, fg_color="#1a1a1c", border_width=1, border_color="#2b2b2f", corner_radius=8)
            row_frame.pack(fill="x", pady=5)
            
            info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            info_frame.pack(side="left", padx=15, pady=10, fill="x", expand=True)
            
            ctk.CTkLabel(info_frame, text=srv["alias"], font=ctk.CTkFont(size=15, weight="bold"), text_color="white", anchor="w").pack(fill="x")
            ctk.CTkLabel(info_frame, text=srv["desc"], font=ctk.CTkFont(size=12), text_color="#aaaaaa", anchor="w").pack(fill="x")
            
            btn = ctk.CTkButton(row_frame, text="+ Añadir", width=80, height=30, fg_color="#28a745", hover_color="#218838", font=ctk.CTkFont(weight="bold"), command=lambda a=srv["alias"], i=srv["ip"]: add_featured(a, i))
            btn.pack(side="right", padx=15)

    def refresh_server_list(self, w):
        # Update home dropdown if it exists
        if hasattr(self, 'ip_dropdown') and hasattr(self, 'ip_entry'):
            aliases = list(self.servers_data.keys())
            if not aliases:
                self.ip_dropdown.configure(values=["💡 Añade un servidor (Pestaña 'Servidores')"])
                self.ip_entry.configure(values=["💡 Añade un servidor (Pestaña 'Servidores')"])
                self.ip_entry.set("💡 Añade un servidor (Pestaña 'Servidores')")
                if hasattr(self, 'snipe_dropdown') and hasattr(self, 'snipe_ip_entry'):
                    self.snipe_dropdown.configure(values=["💡 Añade un servidor primero"])
                    self.snipe_ip_entry.configure(values=["💡 Añade un servidor primero"])
                    self.snipe_ip_entry.set("💡 Añade un servidor primero")
            else:
                self.ip_dropdown.configure(values=aliases)
                self.ip_entry.configure(values=aliases)
                if self.ip_entry.get() not in aliases:
                    self.ip_entry.set("Selecciona un servidor...")
                if hasattr(self, 'snipe_dropdown') and hasattr(self, 'snipe_ip_entry'):
                    self.snipe_dropdown.configure(values=aliases)
                    self.snipe_ip_entry.configure(values=aliases)
                    if self.snipe_ip_entry.get() not in aliases:
                        self.snipe_ip_entry.set("Selecciona un servidor...")

        for widget in self.scroll_servers.winfo_children():
            widget.destroy()
            
        if not self.servers_data:
            empty_frame = ctk.CTkFrame(self.scroll_servers, fg_color="transparent")
            empty_frame.pack(expand=True, fill="both", pady=40)
            
            icon_lbl = ctk.CTkLabel(empty_frame, text="\uE83B", font=ctk.CTkFont(family="Segoe UI", size=48), text_color="#333333")
            icon_lbl.pack(pady=(20, 10))
            
            empty_lbl = ctk.CTkLabel(empty_frame, text="Aún no tienes ningún servidor guardado.\nAñade el primero usando el formulario superior.", text_color="#777777", font=self.font_text)
            empty_lbl.pack()
            
            btn_featured = ctk.CTkButton(empty_frame, text="Explorar Destacados", fg_color="#2b2b2b", hover_color="#3b3b3b", command=self.open_featured_servers_modal)
            btn_featured.pack(pady=20)
            
            if hasattr(self, 'lbl_server_count') and self.lbl_server_count.winfo_exists():
                self.lbl_server_count.configure(text="0 servidores")
            return

        if hasattr(self, 'lbl_server_count') and self.lbl_server_count.winfo_exists():
            self.lbl_server_count.configure(text=f"{len(self.servers_data)} servidor(es)")

        active_ip = self.get_active_ip_from_bat()

        # Sort servers: Favorites first
        sorted_servers = sorted(self.servers_data.items(), key=lambda x: (not (x[1].get("fav", False) if isinstance(x[1], dict) else False), x[0].lower()))

        for alias, data in sorted_servers:
            ip = data["ip"] if isinstance(data, dict) else data
            is_fav = data.get("fav", False) if isinstance(data, dict) else False
            is_active = (ip == active_ip)
            
            # Main Card
            card = ctk.CTkFrame(self.scroll_servers, fg_color="#18181A", border_width=1, border_color="#2b2b2f", corner_radius=12)
            card.pack(fill="x", pady=8, padx=10)
            
            # --- TOP SECTION (Avatar + Title + Favorite) ---
            top_frame = ctk.CTkFrame(card, fg_color="transparent")
            top_frame.pack(fill="x", padx=15, pady=(15, 10))
            
            # Avatar
            avatar = ctk.CTkFrame(top_frame, width=50, height=50, corner_radius=10, fg_color="#101012", border_width=1, border_color="#2b2b2f")
            avatar.pack(side="left")
            avatar.pack_propagate(False)
            lbl_avatar = ctk.CTkLabel(avatar, text=alias[:2].upper(), font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=COLOR_RUST_RED)
            lbl_avatar.pack(expand=True)
            
            # Titles
            titles_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
            titles_frame.pack(side="left", padx=15, fill="x", expand=True)
            
            lbl_alias = ctk.CTkLabel(titles_frame, text=alias.upper(), font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color="white", anchor="w")
            lbl_alias.pack(fill="x")
            
            lbl_subtitle = ctk.CTkLabel(titles_frame, text="Consultando servidor...", font=self.font_small, text_color="#aaaaaa", anchor="w")
            lbl_subtitle.pack(fill="x")
            
            # Favorite Star
            def toggle_fav_cmd(target_alias=alias):
                if isinstance(self.servers_data[target_alias], str):
                    self.servers_data[target_alias] = {"ip": self.servers_data[target_alias], "fav": True}
                else:
                    self.servers_data[target_alias]["fav"] = not self.servers_data[target_alias].get("fav", False)
                self.save_servers()
                self.refresh_server_list(w)

            star_color = COLOR_YELLOW if is_fav else "#444444"
            btn_fav = ctk.CTkButton(top_frame, text="★", width=40, height=40, font=ctk.CTkFont(size=24), fg_color="transparent", hover_color="#2b2b2f", text_color=star_color, command=toggle_fav_cmd)
            btn_fav.pack(side="right")
            
            # --- MIDDLE SECTION (Active + Players) ---
            mid_frame = ctk.CTkFrame(card, fg_color="transparent")
            mid_frame.pack(fill="x", padx=15, pady=5)
            
            status_badge = ctk.CTkLabel(mid_frame, text=" COMPROBANDO ", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), fg_color="#333333", text_color="#aaaaaa", corner_radius=6, height=26, width=90)
            status_badge.pack(side="left")
            
            lbl_ping = ctk.CTkLabel(mid_frame, text="Ping: --", font=ctk.CTkFont(size=11, weight="bold"), text_color="#888")
            lbl_ping.pack(side="left", padx=10)
            
            lbl_wipe = ctk.CTkLabel(mid_frame, text="", font=ctk.CTkFont(size=11), text_color="#aaaaaa")
            lbl_wipe.pack(side="left", padx=(0, 10))
            
            lbl_players = ctk.CTkLabel(mid_frame, text="--/-- PLAYERS", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#dddddd")
            lbl_players.pack(side="right")
            
            # --- ACTION SECTION (Join Server) ---
            action_frame = ctk.CTkFrame(card, fg_color="transparent")
            action_frame.pack(fill="x", padx=15, pady=(10, 5))
            
            def select_cmd(target_ip=ip, target_alias=alias, window=w):
                self.ip_entry.set(target_alias)
                self.on_home_server_selected()
                if window and not isinstance(window, (ctk.CTkFrame, tk.Frame)):
                    window.destroy()
                else:
                    self.switch_page("home")
            
            btn_join = ctk.CTkButton(action_frame, text="SELECCIONAR SERVIDOR" if not is_active else "SERVIDOR ACTIVO", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), height=40, fg_color=COLOR_RUST_RED if not is_active else "#28a745", hover_color=COLOR_RUST_HOVER if not is_active else "#218838", command=select_cmd)
            btn_join.pack(side="left", fill="x", expand=True, padx=(0, 5))
            
            def manual_smart_wipe_cmd(target_alias=alias):
                self.snipe_ip_entry.set(target_alias)
                self.switch_page("snipe")

            btn_smart = ctk.CTkButton(action_frame, text="ESPERAR WIPE", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), height=40, width=110, fg_color="#184a8c", hover_color="#123768", command=manual_smart_wipe_cmd)
            btn_smart.pack(side="right")
            
            # --- BOTTOM SECTION (Copy IP, Delete, Edit, Ping) ---
            bottom_frame = ctk.CTkFrame(card, fg_color="transparent")
            bottom_frame.pack(fill="x", padx=15, pady=(5, 15))
            
            def copy_cmd(target_ip=ip):
                self.clipboard_clear()
                self.clipboard_append(target_ip)
                ToastNotification.show(self, "IP copiada al portapapeles")
            
            def edit_cmd(target_alias=alias, window=w):
                self._edit_server_alias(target_alias, window)

            def delete_cmd(target_alias=alias, window=w):
                if styled_askyesno(self, "Eliminar", f"¿Estás seguro de que quieres borrar el servidor '{target_alias}'?"):
                    del self.servers_data[target_alias]
                    self.save_servers()
                    self.refresh_server_list(window)
                    
            btn_copy = ctk.CTkButton(bottom_frame, text="COPY IP", font=ctk.CTkFont(size=11, weight="bold"), width=80, height=28, fg_color="#101012", hover_color="#2b2b2f", border_width=1, border_color="#333", command=copy_cmd)
            btn_copy.pack(side="left")
            
            lbl_ip = ctk.CTkLabel(bottom_frame, text=ip, font=ctk.CTkFont(size=11), text_color="#777")
            lbl_ip.pack(side="left", padx=8)
            
            def stats_cmd(target_ip=ip):
                import webbrowser
                host = target_ip.split(":")[0] if ":" in target_ip else target_ip
                webbrowser.open(f"https://www.battlemetrics.com/servers/rust?q={host}")

            btn_stats = ctk.CTkButton(bottom_frame, text="STATS", font=ctk.CTkFont(size=11, weight="bold"), width=60, height=28, fg_color="#101012", hover_color="#2b2b2f", border_width=1, border_color="#333", command=stats_cmd)
            btn_stats.pack(side="left", padx=10)

            btn_del = ctk.CTkButton(bottom_frame, text="DELETE", font=ctk.CTkFont(size=11, weight="bold"), width=60, height=28, fg_color="#101012", hover_color="#3a1e1b", text_color=COLOR_RUST_RED, border_width=1, border_color="#333", command=delete_cmd)
            btn_del.pack(side="right")
            
            btn_edit = ctk.CTkButton(bottom_frame, text="EDIT", font=ctk.CTkFont(size=11, weight="bold"), width=60, height=28, fg_color="#101012", hover_color="#2b2b2f", border_width=1, border_color="#333", command=edit_cmd)
            btn_edit.pack(side="right", padx=5)

            # Launch async data fetcher
            self._fetch_server_data_async(ip, lbl_subtitle, status_badge, lbl_players, lbl_ping, lbl_wipe, lbl_avatar)

    def _fetch_server_data_async(self, ip, lbl_subtitle, status_badge, lbl_players, lbl_ping, lbl_wipe, lbl_avatar):
        """Query A2S for players/name and ping for latency in a background thread."""
        def do_fetch():
            import socket, re
            host = ip.split(":")[0] if ":" in ip else ip
            port = int(ip.split(":")[1]) if ":" in ip else 28015
            
            a2s_data = None
            for test_port in list(dict.fromkeys([port, port + 1, port + 15])):
                if a2s_data is not None: break
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1.0)
                try:
                    sock.sendto(b'\xFF\xFF\xFF\xFFTSource Engine Query\x00', (host, test_port))
                    data, _ = sock.recvfrom(4096)
                    if data.startswith(b'\xFF\xFF\xFF\xFFI'):
                        data_slice = data[5:]
                        protocol = data_slice[0]
                        data_slice = data_slice[1:]
                        name_end = data_slice.find(b'\x00')
                        name = data_slice[:name_end].decode('utf-8', errors='ignore')
                        
                        # Extraer jugadores via regex para evitar el overflow del byte de Rust
                        cp_m = re.search(rb'cp(\d+)', data)
                        mp_m = re.search(rb'mp(\d+)', data)
                        qp_m = re.search(rb'qp(\d+)', data)

                        cp = int(cp_m.group(1)) if cp_m else -1
                        mp = int(mp_m.group(1)) if mp_m else -1
                        qp = int(qp_m.group(1)) if qp_m else 0

                        if cp == -1 or mp == -1:
                            # Fallback estandar
                            import struct
                            data_slice = data_slice[name_end+1:]
                            data_slice = data_slice[data_slice.find(b'\x00')+1:]
                            data_slice = data_slice[data_slice.find(b'\x00')+1:]
                            data_slice = data_slice[data_slice.find(b'\x00')+1:]
                            app_id, cp, mp, bots = struct.unpack('<HBBb', data_slice[:5])

                        players_text = f"{cp}/{mp} PLAYERS"
                        if qp > 0:
                            players_text += f" (+{qp} EN COLA)"

                        a2s_data = {"name": name, "players_text": players_text}
                except Exception:
                    pass
                finally:
                    sock.close()

            # Now ping
            is_online = False
            ms = None
            try:
                result = subprocess.run(
                    ["ping", "-n", "1", "-w", "2000", host],
                    capture_output=True,
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                is_online = (result.returncode == 0)
                if is_online:
                    import re
                    out = result.stdout.decode('cp1252', errors='ignore')
                    m = re.search(r"(?:tiempo|time)[=<]\s*(\d+)\s*ms", out, re.IGNORECASE)
                    if m: ms = m.group(1)
            except Exception:
                pass

            # Battlemetrics Wipe Info
            wipe_info = ""
            try:
                import urllib.request, json
                from datetime import datetime, timezone
                bm_ip = socket.gethostbyname(host)
                url = f"https://api.battlemetrics.com/servers?filter[search]={bm_ip}&page[size]=100"
                req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
                res = urllib.request.urlopen(req, timeout=2.0)
                bm_data = json.loads(res.read())
                
                pil_image = None
                if bm_data.get('data'):
                    wipe_str = None
                    test_ports = list(dict.fromkeys([port, port + 1, port + 15, 28015]))
                    for srv in bm_data['data']:
                        attrs = srv.get('attributes', {})
                        s_port = attrs.get('port')
                        s_qport = attrs.get('portQuery')
                        if attrs.get('ip') == bm_ip and attrs.get('status') == 'online' and (s_port in test_ports or s_qport in test_ports):
                            wipe_str = attrs.get('details', {}).get('rust_last_wipe')
                            bm_full_name = attrs.get('name')
                            img_url = attrs.get('details', {}).get('rust_headerimage')
                            if bm_full_name and a2s_data:
                                a2s_data["name"] = bm_full_name
                            
                            if img_url:
                                try:
                                    import io
                                    req_img = urllib.request.Request(img_url, headers={'User-Agent': 'Mozilla/5.0'})
                                    res_img = urllib.request.urlopen(req_img, timeout=2.0)
                                    raw_data = res_img.read()
                                    from PIL import Image
                                    img = Image.open(io.BytesIO(raw_data))
                                    w, h = img.size
                                    min_dim = min(w, h)
                                    left = (w - min_dim) / 2
                                    top = (h - min_dim) / 2
                                    right = (w + min_dim) / 2
                                    bottom = (h + min_dim) / 2
                                    # Crop to square, resize to 50x50
                                    pil_image = img.crop((left, top, right, bottom)).resize((50, 50), Image.Resampling.LANCZOS)
                                    
                                    # Create a solid background matching the CARD fg_color (#18181A)
                                    bg = Image.new('RGBA', (50, 50), (24, 24, 26, 255))
                                    
                                    # Create mask for rounded corners
                                    from PIL import ImageDraw
                                    mask = Image.new("L", (50, 50), 0)
                                    draw = ImageDraw.Draw(mask)
                                    # Use exactly 0 to 49 for 50x50 image
                                    draw.rounded_rectangle((0, 0, 49, 49), radius=10, fill=255)
                                    
                                    # Paste the image onto the solid background using the mask
                                    pil_image = pil_image.convert("RGBA")
                                    bg.paste(pil_image, (0, 0), mask)
                                    pil_image = bg
                                except Exception: pass
                                
                            if wipe_str: break
                        
                    if wipe_str:
                        wipe_dt = datetime.strptime(wipe_str, '%Y-%m-%dT%H:%M:%S.%fZ').replace(tzinfo=timezone.utc)
                        now = datetime.now(timezone.utc)
                        diff = now - wipe_dt
                        hours = diff.total_seconds() / 3600
                        if hours < 24:
                            wipe_info = f"Wiped {int(hours)} hrs ago"
                        else:
                            days = round(hours / 24)
                            wipe_info = f"Wiped {days} days ago"
            except Exception:
                pass

            def update_ui():
                try:
                    if not status_badge.winfo_exists(): return
                    
                    if a2s_data:
                        base_text = a2s_data["name"][:150] + ("..." if len(a2s_data["name"]) > 150 else "")
                        # Easter egg fix for the 63-byte limit cutting "Wipes" to "Wip"
                        if base_text.endswith(" No BP Wip"):
                            base_text += "es"
                        elif base_text.endswith("Wip"):
                            base_text += "es"
                            
                        lbl_subtitle.configure(text=base_text)
                        lbl_players.configure(text=a2s_data["players_text"])
                        if wipe_info:
                            lbl_wipe.configure(text=f"•   {wipe_info}")
                        else:
                            lbl_wipe.configure(text="")
                    else:
                        lbl_subtitle.configure(text="Rust Server (A2S Unreachable)")
                        lbl_players.configure(text="--/-- PLAYERS")
                        lbl_wipe.configure(text="")
                        
                    if a2s_data:
                        status_badge.configure(text=" ACTIVE ● ", fg_color="#28a745", text_color="white")
                        lbl_ping.configure(text=f"Ping: {ms}ms" if ms else "Ping: <1ms")
                    elif is_online:
                        status_badge.configure(text=" HOST OK ", fg_color="#e8a020", text_color="white")
                        lbl_ping.configure(text=f"Ping: {ms}ms" if ms else "Ping: <1ms")
                    else:
                        status_badge.configure(text=" OFFLINE ", fg_color="#dc3545", text_color="white")
                        lbl_ping.configure(text="Ping: Timeout")
                        
                    if pil_image:
                        import customtkinter as ctk
                        ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(50, 50))
                        lbl_avatar.configure(image=ctk_img, text="")
                        lbl_avatar.master.configure(border_width=0)
                        
                except Exception:
                    pass

            self.after(0, update_ui)

        threading.Thread(target=do_fetch, daemon=True).start()

    def _edit_server_alias(self, old_alias, window):
        server_obj = self.servers_data.get(old_alias)
        old_ip = server_obj.get("ip", "") if isinstance(server_obj, dict) else server_obj
        
        new_alias = styled_input(self, "Editar Servidor", f"Editar alias de '{old_alias}':", placeholder="Nuevo alias", initial_value=old_alias)
        if new_alias is None: return
        new_alias = new_alias.strip()
        if not new_alias: return
        
        new_ip = styled_input(self, "Editar IP", f"Editar IP o Dominio para '{new_alias}':", placeholder="IP:Puerto", initial_value=old_ip)
        if new_ip is None: return
        new_ip = new_ip.strip()
        if not new_ip: return
        
        server_obj = self.servers_data.pop(old_alias)
        if isinstance(server_obj, dict):
            server_obj["ip"] = new_ip
            self.servers_data[new_alias] = server_obj
        else:
            self.servers_data[new_alias] = new_ip
            
        self.save_servers()
        self.refresh_server_list(window)

    def _export_servers(self):
        """Exporta la lista de servidores a un archivo JSON."""
        if not self.servers_data:
            styled_showwarning(self, "Sin datos", "No tienes servidores guardados para exportar.")
            return
        from tkinter import filedialog
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="rust_servidores_backup.json",
            title="Exportar servidores"
        )
        if path:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(self.servers_data, f, indent=4, ensure_ascii=False)
                logger.info("Servidores exportados a: %s (%d servidores)", path, len(self.servers_data))
                ToastNotification.show(self, f"Exportados {len(self.servers_data)} servidores")
            except Exception as e:
                styled_showerror(self, "Error", f"No se pudo exportar: {e}")

    def _import_servers(self, manager_window=None):
        """Importa servidores desde un archivo JSON."""
        from tkinter import filedialog
        path = filedialog.askopenfilename(
            filetypes=[("JSON", "*.json")],
            title="Importar servidores"
        )
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    imported = json.load(f)
                if not isinstance(imported, dict):
                    styled_showerror(self, "Error", "El archivo no tiene el formato esperado.")
                    return
                count_new = 0
                for alias, ip in imported.items():
                    if alias not in self.servers_data:
                        if isinstance(ip, str):
                            self.servers_data[alias] = {"ip": ip, "fav": False}
                        else:
                            self.servers_data[alias] = ip
                        count_new += 1
                self.save_servers()
                logger.info("Servidores importados: %d nuevos de %d totales", count_new, len(imported))
                styled_showinfo(self, "Éxito", f"Se han importado {count_new} servidor(es) nuevos.\n({len(imported) - count_new} ya existían y se omitieron.)")
                if manager_window:
                    self.refresh_server_list(manager_window)
            except json.JSONDecodeError:
                styled_showerror(self, "Error", "El archivo no es un JSON válido.")
            except Exception as e:
                styled_showerror(self, "Error", f"No se pudo importar: {e}")

    def build_step(self, parent, number, bold_title, normal_desc, color):
        f = ctk.CTkFrame(parent, fg_color="transparent")
        f.pack(fill="x", padx=15, pady=4)
        
        num_lbl = ctk.CTkLabel(f, text=f"{number}.", font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"), text_color=color, width=25)
        num_lbl.pack(side="left", anchor="n", pady=(2,0))
        
        tf = ctk.CTkFrame(f, fg_color="transparent")
        tf.pack(side="left", fill="x", expand=True)
        
        title_lbl = ctk.CTkLabel(tf, text=bold_title, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="white", justify="left")
        title_lbl.pack(anchor="w")
        
        desc_lbl = ctk.CTkLabel(tf, text=normal_desc, font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#aaaaaa", justify="left", wraplength=400)
        desc_lbl.pack(anchor="w")

    def create_wake_task(self, h, m):
        now = datetime.datetime.now()
        wake_time = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        
        if wake_time <= now:
            wake_time += datetime.timedelta(days=1)
            
        time_str = wake_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        xml_template = f"""<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <Triggers>
    <TimeTrigger>
      <StartBoundary>{time_str}</StartBoundary>
      <Enabled>true</Enabled>
    </TimeTrigger>
  </Triggers>
  <Principals>
    <Principal id="Author">
      <LogonType>InteractiveToken</LogonType>
      <RunLevel>HighestAvailable</RunLevel>
    </Principal>
  </Principals>
  <Settings>
    <MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy>
    <DisallowStartIfOnBatteries>false</DisallowStartIfOnBatteries>
    <StopIfGoingOnBatteries>false</StopIfGoingOnBatteries>
    <AllowHardTerminate>true</AllowHardTerminate>
    <StartWhenAvailable>false</StartWhenAvailable>
    <RunOnlyIfNetworkAvailable>false</RunOnlyIfNetworkAvailable>
    <IdleSettings>
      <StopOnIdleEnd>true</StopOnIdleEnd>
      <RestartOnIdle>false</RestartOnIdle>
    </IdleSettings>
    <AllowStartOnDemand>true</AllowStartOnDemand>
    <Enabled>true</Enabled>
    <Hidden>false</Hidden>
    <RunOnlyIfIdle>false</RunOnlyIfIdle>
    <WakeToRun>true</WakeToRun>
    <ExecutionTimeLimit>PT72H</ExecutionTimeLimit>
    <Priority>7</Priority>
  </Settings>
  <Actions Context="Author">
    <Exec>
      <Command>shutdown.exe</Command>
      <Arguments>/r /t 0 /f</Arguments>
    </Exec>
  </Actions>
</Task>"""
        
        try:
            tmp_xml = os.path.join(tempfile.gettempdir(), "wake_task.xml")
            with open(tmp_xml, "w", encoding="utf-16") as f:
                f.write(xml_template)
            
            res = subprocess.run(["schtasks", "/create", "/tn", "RustAutoQueueWake", "/xml", tmp_xml, "/f"], 
                                 capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if res.returncode == 0:
                styled_showinfo(self, "Programado", f"¡Listo! El PC se despertará y reiniciará a las {h}:{m}.\n\nRECUERDA: Ahora debes darle a 'Suspender' o 'Hibernar' en Windows.")
                self.settings["wake_method"] = "software"
                self.save_settings()
                self.check_status()
            else:
                styled_showerror(self, "Error", f"No se pudo crear la tarea:\n{res.stderr.decode(errors='ignore')}")
        except Exception as e:
            styled_showerror(self, "Error", f"Error al generar despertador: {e}")
            
    def cancel_wake_task(self, silent=False):
        try:
            subprocess.run(["schtasks", "/delete", "/tn", "RustAutoQueueWake", "/f"], 
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if self.settings.get("wake_method") == "software":
                self.settings["wake_method"] = None
                self.save_settings()
            self.check_status()
            if not silent:
                logger.info("Despertador cancelado")
                ToastNotification.show(self, "Despertador cancelado")
        except Exception as e:
            logger.error("Error cancelando despertador: %s", e)
            if not silent:
                styled_showerror(self, "Error", "No se pudo cancelar la tarea.")

    def create_wake_page(self):
        wake_page = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        self.pages["wake"] = wake_page
        
        wake_page.grid_columnconfigure(0, weight=1)
        wake_page.grid_rowconfigure(2, weight=1)
        
        # Header
        header = ctk.CTkFrame(wake_page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 5))
        
        lbl_title = ctk.CTkLabel(header, text="AUTO-DESPERTAR", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=COLOR_RUST_RED)
        lbl_title.pack(side="left")
        
        lbl_subtitle = ctk.CTkLabel(wake_page, text="Elige cómo encender el PC automáticamente para saltarte las colas.", font=self.font_subtitle, text_color="#aaa")
        lbl_subtitle.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))
        
        # Tabview
        tabview = ctk.CTkTabview(wake_page, segmented_button_selected_color=COLOR_RUST_RED, segmented_button_selected_hover_color=COLOR_RUST_HOVER)
        tabview.grid(row=2, column=0, sticky="nsew", padx=20, pady=5)
        
        t1 = tabview.add("Enchufe Inteligente")
        t2 = tabview.add("BIOS RTC")
        t3 = tabview.add("Software (Beta)")
        
        # TAB 1: SMART PLUG
        txt1 = ("Esta es la opción recomendada de Diego (faabra).\n\n"
                "1. Compra un enchufe inteligente (Alexa, Google, etc).\n"
                "2. En la BIOS de tu PC, busca la opción 'Restore on AC Power Loss' y ponla en 'Power On'.\n"
                "3. Apaga el PC al 100% por la noche.\n"
                "4. Programa en tu móvil que el enchufe se encienda a la hora deseada.\n\n"
                "¡Al recibir corriente, el PC se encenderá solo y lanzará la cola de Rust!")
        ctk.CTkLabel(t1, text=txt1, justify="left", wraplength=520, font=self.font_text).pack(pady=20, padx=20)
        ctk.CTkButton(t1, text="Usar este método (Enchufe)", font=self.font_label, fg_color="#333", border_width=1, border_color="#555",
                      command=lambda: self.set_wake_method("smart_plug", wake_page)).pack(pady=5)
                      
        # TAB 2: BIOS RTC
        txt2 = ("Si no quieres comprar nada, usa el reloj interno de tu placa base.\n\n"
                "1. Entra a la BIOS (F2 o SUPR al arrancar).\n"
                "2. Busca 'Advanced' -> 'APM' o 'Power Management'.\n"
                "3. Activa 'Power On By RTC' o 'RTC Alarm'.\n"
                "4. Pon la hora exacta a la que quieres que el PC se despierte.\n"
                "5. Guarda y apaga el PC.\n\n"
                "El PC se encenderá físicamente a esa hora.")
        ctk.CTkLabel(t2, text=txt2, justify="left", wraplength=520, font=self.font_text).pack(pady=20, padx=20)
        ctk.CTkButton(t2, text="Usar este método (BIOS)", font=self.font_label, fg_color="#333", border_width=1, border_color="#555",
                      command=lambda: self.set_wake_method("bios", wake_page)).pack(pady=5)
                      
        # TAB 3: SOFTWARE
        ctk.CTkLabel(t3, text="Usa este despertador si no quieres tocar la BIOS.\n\nIMPORTANTE: Para que funcione, debes darle a SUSPENDER o HIBERNAR en Windows, no a Apagar.", 
                     justify="left", wraplength=520, font=ctk.CTkFont(size=13, slant="italic"), text_color=COLOR_YELLOW).pack(pady=(10, 20))
        
        time_frame = ctk.CTkFrame(t3, fg_color="transparent")
        time_frame.pack(pady=10)
        
        ctk.CTkLabel(time_frame, text="Hora:", font=self.font_label).pack(side="left", padx=5)
        self.combo_h = ctk.CTkOptionMenu(time_frame, values=[f"{i:02d}" for i in range(24)], width=70, fg_color="#1a1a1c", button_color="#1a1a1c", button_hover_color="#2a2a2c")
        self.combo_h.set("09")
        self.combo_h.pack(side="left", padx=5)
        CTkScrollableDropdown(self.combo_h, values=[f"{i:02d}" for i in range(24)],
                              fg_color="#1e1e1f", button_color="transparent", hover_color="#2b2b2d",
                              frame_border_color="#333335", frame_corner_radius=8, text_color="white", alpha=1.0)
        
        ctk.CTkLabel(time_frame, text="Min:", font=self.font_label).pack(side="left", padx=5)
        self.combo_m = ctk.CTkOptionMenu(time_frame, values=[f"{i:02d}" for i in range(60)], width=70, fg_color="#1a1a1c", button_color="#1a1a1c", button_hover_color="#2a2a2c")
        self.combo_m.set("30")
        self.combo_m.pack(side="left", padx=5)
        CTkScrollableDropdown(self.combo_m, values=[f"{i:02d}" for i in range(60)],
                              fg_color="#1e1e1f", button_color="transparent", hover_color="#2b2b2d",
                              frame_border_color="#333335", frame_corner_radius=8, text_color="white", alpha=1.0)
        
        btn_prog = ctk.CTkButton(t3, text="Programar Despertador", font=self.font_label, fg_color=COLOR_RUST_RED, hover_color=COLOR_RUST_HOVER,
                                command=lambda: self.create_wake_task(self.combo_h.get(), self.combo_m.get()))
        btn_prog.pack(pady=10)
        
        btn_cancel = ctk.CTkButton(t3, text="Cancelar Tarea de Windows", font=self.font_label, fg_color="transparent", border_width=1, border_color="#555",
                                   command=self.cancel_wake_task)
        btn_cancel.pack(pady=5)
        
        # Bottom Actions
        footer = ctk.CTkFrame(wake_page, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(5, 20))
        
        ctk.CTkButton(footer, text="Desactivar Todos los Métodos", fg_color="transparent", text_color="#777", font=self.font_small,
                      command=lambda: self.set_wake_method(None, wake_page)).pack(side="left", padx=(0, 10))
                      
        ctk.CTkButton(footer, text="💤 Suspender el PC Ahora",
                      font=self.font_label,
                      fg_color="#1a2a3a", hover_color="#243550",
                      border_width=1, border_color=COLOR_BLUE, text_color=COLOR_BLUE,
                      height=36,
                      command=lambda: subprocess.run(["rundll32.exe", "powrprof.dll,SetSuspendState", "0", "1", "0"],
                                                    creationflags=subprocess.CREATE_NO_WINDOW)
                      ).pack(side="right")
                      
        self.refresh_auto_wake_ui(wake_page)

    def create_logs_page(self):
        logs_page = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        self.pages["logs"] = logs_page
        
        logs_page.grid_columnconfigure(0, weight=1)
        logs_page.grid_rowconfigure(1, weight=1)
        
        # Header
        header = ctk.CTkFrame(logs_page, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=20, pady=(20, 10))
        
        lbl_title = ctk.CTkLabel(header, text="REGISTRO DE ACTIVIDAD", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color=COLOR_RUST_RED)
        lbl_title.pack(side="left")
        
        # Textbox for logs
        self.log_textbox = ctk.CTkTextbox(
            logs_page,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#101012",
            border_color="#2b2b2f",
            border_width=1,
            text_color="#cccccc",
            activate_scrollbars=True
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=20, pady=5)
        
        # Configure color tags
        self.log_textbox.tag_config("time", foreground="#555555")
        self.log_textbox.tag_config("info", foreground="#ffffff")
        self.log_textbox.tag_config("warning", foreground="#ffcc00")
        self.log_textbox.tag_config("error", foreground="#ff4444")
        self.log_textbox.tag_config("success", foreground="#28a745")
        
        self.log_textbox.configure(state="disabled")
        
        # Footer buttons
        footer = ctk.CTkFrame(logs_page, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(5, 20))
        
        btn_refresh = ctk.CTkButton(
            footer,
            text="Actualizar",
            width=100,
            height=32,
            fg_color="#2b2b2b",
            hover_color="#3b3b3b",
            font=self.font_label,
            command=self.refresh_log_viewer
        )
        btn_refresh.pack(side="left", padx=(0, 10))
        
        btn_copy = ctk.CTkButton(
            footer,
            text="Copiar Logs",
            width=100,
            height=32,
            fg_color="#2b2b2b",
            hover_color="#3b3b3b",
            font=self.font_label,
            command=lambda: self.clipboard_clear() or self.clipboard_append(self.log_textbox.get("1.0", "end-1c")) if hasattr(self, "log_textbox") else None
        )
        btn_copy.pack(side="left", padx=(0, 10))
        
        import os
        btn_open = ctk.CTkButton(
            footer,
            text="Abrir en Bloc de Notas",
            width=160,
            height=32,
            fg_color="#1a2b3a",
            border_width=1,
            border_color="#2b4c6b",
            hover_color="#203a50",
            font=self.font_label,
            command=lambda: os.startfile(LOG_FILE) if os.path.exists(LOG_FILE) else None
        )
        btn_open.pack(side="left", padx=(0, 10))
        
        btn_clear = ctk.CTkButton(
            footer,
            text="Borrar Historial",
            width=130,
            height=32,
            fg_color="transparent",
            border_width=1,
            border_color=COLOR_RUST_RED,
            text_color=COLOR_RUST_RED,
            hover_color="#2b1e1b",
            font=self.font_label,
            command=self.clear_log_file
        )
        btn_clear.pack(side="left")
        
        self.refresh_log_viewer()
        self.auto_refresh_logs()
        
    def create_discord_page(self):
        discord_page = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        self.pages["discord"] = discord_page
        
        discord_page.grid_columnconfigure(0, weight=1)
        discord_page.grid_rowconfigure(0, weight=1)
        
        # Inner Frame
        inner = ctk.CTkFrame(discord_page, fg_color="#18191c", corner_radius=15, border_width=1, border_color="#5865F2")
        inner.grid(row=0, column=0, padx=40, pady=40, sticky="nsew")
        
        inner.grid_columnconfigure(0, weight=1)
        inner.grid_rowconfigure((0, 1, 2, 3, 4), weight=1)
        
        icon_lbl = ctk.CTkLabel(inner, text="\uE8F2", font=ctk.CTkFont(family="Segoe UI", size=64), text_color="#5865F2")
        icon_lbl.grid(row=1, column=0, pady=(0, 0))
        
        title = ctk.CTkLabel(inner, text="UNIRSE AL DISCORD", font=ctk.CTkFont(size=28, weight="bold"), text_color="white")
        title.grid(row=2, column=0, pady=(10, 0), sticky="n")
        
        desc = ctk.CTkLabel(inner, text="Únete a la comunidad oficial.\nRecibe soporte técnico, enterate de actualizaciones\ny participa en el desarrollo de la herramienta.", font=ctk.CTkFont(size=15), text_color="#aaaaaa")
        desc.grid(row=3, column=0, pady=0, sticky="n")
        
        import webbrowser
        btn_join = ctk.CTkButton(
            inner, 
            text="Abrir Discord", 
            fg_color="#5865F2", 
            hover_color="#4752C4", 
            font=ctk.CTkFont(size=15, weight="bold"), 
            height=45, 
            width=200, 
            command=lambda: webbrowser.open("https://discord.com/")
        )
        btn_join.grid(row=4, column=0, pady=(0, 20), sticky="n")
    def auto_refresh_logs(self):
        if hasattr(self, 'pages') and self.pages.get("logs") and self.pages["logs"].winfo_exists():
            try:
                import os
                if os.path.exists(LOG_FILE):
                    current_size = os.path.getsize(LOG_FILE)
                    if not hasattr(self, 'last_log_size') or self.last_log_size != current_size:
                        self.last_log_size = current_size
                        self.refresh_log_viewer()
            except Exception:
                pass
            self.after(2000, self.auto_refresh_logs)

    def refresh_log_viewer(self):
        if not hasattr(self, 'log_textbox') or not self.log_textbox.winfo_exists():
            return
            
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("1.0", "end")
        
        import os
        if os.path.exists(LOG_FILE):
            try:
                with open(LOG_FILE, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                tail_lines = lines[-200:]
                
                for line in tail_lines:
                    parts = line.split(" - ", 2)
                    if len(parts) >= 3:
                        time_part = parts[0] + " - "
                        level_part = parts[1]
                        msg_part = " - " + parts[2]
                        
                        self.log_textbox.insert("end", time_part, "time")
                        
                        if "ERROR" in level_part or "CRITICAL" in level_part:
                            self.log_textbox.insert("end", level_part, "error")
                            self.log_textbox.insert("end", msg_part, "error")
                        elif "WARNING" in level_part:
                            self.log_textbox.insert("end", level_part, "warning")
                            self.log_textbox.insert("end", msg_part, "warning")
                        elif "SUCCESS" in level_part or "EXITO" in msg_part.upper() or "EXITOSAMENTE" in msg_part.upper():
                            self.log_textbox.insert("end", level_part, "success")
                            self.log_textbox.insert("end", msg_part, "success")
                        else:
                            self.log_textbox.insert("end", level_part, "info")
                            self.log_textbox.insert("end", msg_part, "info")
                    else:
                        self.log_textbox.insert("end", line, "info")
                        
            except Exception as e:
                self.log_textbox.insert("1.0", f"Error al leer el archivo de registros: {e}", "error")
        else:
            self.log_textbox.insert("1.0", "No hay registros de actividad todavía.", "time")
            
        self.log_textbox.configure(state="disabled")
        self.log_textbox.see("end")

    def clear_log_file(self):
        if styled_askyesno(self, "Confirmar", "¿Seguro que quieres borrar el archivo de actividad?"):
            try:
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("")
                logger.info("Historial de actividad limpiado por el usuario")
                self.refresh_log_viewer()
            except Exception as e:
                styled_showerror(self, "Error", f"No se pudo limpiar el archivo: {e}")

    def switch_page(self, page_id):
        if self.active_page == page_id:
            return
            
        for pid, btn in self.nav_buttons.items():
            bar = self.nav_bars.get(pid)
            if pid == page_id:
                btn.configure(fg_color="#2b2b2b", text_color="white", hover_color="#333333")
                if bar: bar.configure(fg_color=COLOR_RUST_RED)
            else:
                btn.configure(fg_color="transparent", text_color="#aaaaaa", hover_color="#1a1a1c")
                if bar: bar.configure(fg_color="transparent")
        old_page = self.pages.get(self.active_page)
        new_page = self.pages.get(page_id)
        
        if not new_page:
            return
            
        self.active_page = page_id
        
        if page_id == "logs":
            self.refresh_log_viewer()
            
        new_page.lift()
        new_page.place(relx=1.0, rely=0.0, relwidth=1.0, relheight=1.0)
        
        steps = 20
        step_duration = 16 # approx 60 FPS
        
        def animate(step):
            if not new_page.winfo_exists():
                return
            if step > steps:
                new_page.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
                if old_page and old_page.winfo_exists() and old_page != new_page:
                    old_page.place_forget()
                return
            progress = step / steps
            # Cubic ease out para un deslizamiento muy elegante
            factor = 1.0 - (1.0 - progress) ** 3
            current_x = 1.0 - factor
            new_page.place(relx=current_x, rely=0.0, relwidth=1.0, relheight=1.0)
            self.after(step_duration, lambda: animate(step + 1))
            
        animate(1)

def run_smart_wipe_daemon(ip):
    """Monitor in background for wipe restarts."""
    import time, socket, re, subprocess, logging, sys
    
    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s [WIPE_DAEMON] %(message)s")
    logger = logging.getLogger("SmartWipe")
    
    logger.info("Iniciando Smart Wipe Daemon para IP: %s", ip)
    
    host = ip.split(":")[0] if ":" in ip else ip
    port = int(ip.split(":")[1]) if ":" in ip else 28015
    
    def check_online():
        for test_port in list(dict.fromkeys([port, port + 1, port + 15])):
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1.5)
            try:
                sock.sendto(b'\xFF\xFF\xFF\xFFTSource Engine Query\x00', (host, test_port))
                data, _ = sock.recvfrom(4096)
                if data.startswith(b'\xFF\xFF\xFF\xFFI'):
                    try:
                        idx = 5
                        for _ in range(4): idx = data.find(b'\x00', idx) + 1
                        idx += 9
                        idx = data.find(b'\x00', idx) + 1
                        if idx < len(data):
                            edf = data[idx]
                            idx += 1
                            if edf & 0x80:
                                import struct
                                reported_port = struct.unpack_from('<H', data, idx)[0]
                                if test_port != port and reported_port != port: 
                                    continue
                    except: pass
                    return True
            except Exception: pass
            finally: sock.close()
        return False

    # Fase 1: Esperar a que el servidor SE APAGUE
    logger.info("Fase 1: Comprobando estado actual...")
    
    if check_online():
        logger.info("El servidor está ONLINE. Esperando a que se APAGUE para el wipe...")
        failed_pings = 0
        while True:
            if not check_online():
                failed_pings += 1
                if failed_pings >= 3:
                    break
            else:
                failed_pings = 0
            time.sleep(4.0)
    
    logger.info("El servidor está OFFLINE. (Wipe en proceso...)")
    
    # Fase 2: Esperar a que vuelva ONLINE
    logger.info("Fase 2: Esperando a que el servidor vuelva a estar ONLINE...")
    
    while True:
        if check_online():
            break
        time.sleep(1.0)
        
    logger.info("¡SERVIDOR ONLINE! Lanzando Rust inmediatamente...")
    
    try:
        import winsound
        winsound.Beep(1000, 300)
        time.sleep(0.1)
        winsound.Beep(1500, 600)
    except: pass

    subprocess.Popen(['explorer.exe', f'steam://run/252490//+connect%20{ip}%20+aq%20{int(time.time())}'], creationflags=subprocess.CREATE_NO_WINDOW)
    logger.info("Misión cumplida. Cerrando daemon.")
    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--smart-wipe":
        run_smart_wipe_daemon(sys.argv[2])
    else:
        app = App()
        app.mainloop()
