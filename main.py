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
from autoqueue_ui.design import install_theme
from autoqueue_ui.home import build_home
from autoqueue_ui.servers import build_servers
from autoqueue_ui.snipe import build_snipe
from autoqueue_ui.notifications import show_toast
from concurrent.futures import ThreadPoolExecutor
from logging.handlers import RotatingFileHandler
from autoqueue_core.storage import load_json, save_json, read_json
from autoqueue_core.validation import normalize_address, validate_servers, validate_settings, is_newer_version

# =========================================================
# SMOOTH SCROLL PATCH PARA CUSTOMTKINTER
# =========================================================

def apply_smooth_scroll():
    original_wheel = ctk.CTkScrollableFrame._mouse_wheel_all
    
    def _smooth_mouse_wheel(self, event):
        if self.check_if_master_is_canvas(event.widget):
            import sys
            if self._shift_pressed:
                original_wheel(self, event)
                return
                
            if sys.platform.startswith("win"):
                clicks = int(event.delta / 120)
            else:
                clicks = int(event.delta)
                
            if clicks == 0: return
            direction = -1 if clicks > 0 else 1
            
            if not hasattr(self, "_scroll_queue"):
                self._scroll_queue = 0
            
            # Sumar 20 unidades de scroll por click de rueda (más distancia)
            self._scroll_queue += direction * abs(clicks) * 20
            
            if getattr(self, "_scroll_active", False):
                return
                
            self._scroll_active = True
            
            def run_scroll():
                if not self.winfo_exists(): return
                if self._scroll_queue == 0:
                    self._scroll_active = False
                    return
                
                # Calcular velocidad: más rápido cuanta más cola haya
                queue_abs = abs(self._scroll_queue)
                step = 1 if self._scroll_queue > 0 else -1
                
                if queue_abs > 30: step *= 6
                elif queue_abs > 15: step *= 3
                elif queue_abs > 5: step *= 2
                
                # Ajustar para no pasarnos
                if abs(step) > queue_abs: step = self._scroll_queue
                
                if self._parent_canvas.yview() != (0.0, 1.0):
                    self._parent_canvas.yview("scroll", step, "units")
                    
                self._scroll_queue -= step
                self.after(10, run_scroll)
                
            run_scroll()

    ctk.CTkScrollableFrame._mouse_wheel_all = _smooth_mouse_wheel

apply_smooth_scroll()
# =========================================================
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

CURRENT_VERSION = "2.1.0"
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

if __name__ == "__main__" and not is_admin():
    # Si no somos admin, reiniciamos el programa pidiendo elevación (UAC)
    if hasattr(sys, '_MEIPASS'):
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, "", None, 1)
    else:
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{sys.argv[0]}"', None, 1)
    sys.exit()

ctk.set_appearance_mode("dark")
install_theme()

# Colores personalizados
COLOR_RUST_RED = "#df7957"
COLOR_RUST_HOVER = "#c96546"
COLOR_LIGHT_TEXT = "#f1eee7"
COLOR_DARK_FRAME = "#1b1e1d"
COLOR_BLUE = "#a0bbbe"
COLOR_GREEN = "#9dbb9d"
COLOR_YELLOW = "#d9bc7d"
COLOR_INACTIVE = "#a6aea7"

# Regex para validar formato IP/Dominio con o sin puerto
IP_PORT_RE = re.compile(r'^[a-zA-Z0-9._-]+(?::\d+)?$')

# --- SISTEMA DE LOGGING ---
APPDATA_DIR = os.path.join(os.environ["APPDATA"], "RustAutoQueue")
if not os.path.exists(APPDATA_DIR):
    os.makedirs(APPDATA_DIR)
LOG_FILE = os.path.join(APPDATA_DIR, "activity.log")
logging.basicConfig(
    handlers=[RotatingFileHandler(LOG_FILE, maxBytes=2 * 1024 * 1024, backupCount=3, encoding="utf-8")],
    level=logging.INFO,
    format="%(asctime)s  %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
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
        label = tk.Label(tw, text=self.text, background="#2a2a2a", foreground="#c9cfc8",
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
    show = staticmethod(show_toast)


class RadarCanvas(tk.Canvas):
    """
    Radar visual animado para el Wipe-Spam.
    Estados: 'idle', 'waiting_offline', 'offline', 'connecting'
    """
    # Paleta de colores por estado
    STATE_COLORS = {
        'idle':            {'arc': '#444447', 'glow': '#2a2a2c', 'text': '#555558', 'pulse': '#444447'},
        'waiting_offline': {'arc': '#e07b39', 'glow': '#3a2010', 'text': '#e07b39', 'pulse': '#c06020'},
        'offline':         {'arc': '#cc2222', 'glow': '#2a0808', 'text': '#ff4444', 'pulse': '#ff2222'},
        'connecting':      {'arc': '#22cc55', 'glow': '#082a12', 'text': '#22ff66', 'pulse': '#00ff44'},
    }
    STATE_LABELS = {
        'idle':            'Esperando objetivo...',
        'waiting_offline': 'Fase 1 — Servidor ONLINE, esperando wipe...',
        'offline':         'Fase 2 — WIPE EN PROCESO — Escaneando...',
        'connecting':      'Servidor disponible. Conectando…',
    }

    def __init__(self, parent, size=120, **kwargs):
        super().__init__(parent, width=size, height=size,
                         bg='#151817', highlightthickness=0, **kwargs)
        self.size = size
        self.cx = size / 2
        self.cy = size / 2
        self.r_outer = size / 2 - 8
        self.r_inner = self.r_outer - 10
        self._state = 'idle'
        self._angle = 0
        self._pulse_alpha = 0
        self._pulse_dir = 1
        self._running = True
        self._counter_label = None
        self._counter_text = ''
        self._animate()

    def set_state(self, state, extra_text=''):
        self._state = state
        self._counter_text = extra_text

    def stop(self):
        self._running = False

    def _hex_blend(self, c1, c2, t):
        """Blend two hex colors by factor t (0..1)."""
        try:
            r1,g1,b1 = int(c1[1:3],16), int(c1[3:5],16), int(c1[5:7],16)
            r2,g2,b2 = int(c2[1:3],16), int(c2[3:5],16), int(c2[5:7],16)
            r = int(r1 + (r2-r1)*t)
            g = int(g1 + (g2-g1)*t)
            b = int(b1 + (b2-b1)*t)
            return f'#{r:02x}{g:02x}{b:02x}'
        except:
            return c1

    def _animate(self):
        if not self._running:
            return
        try:
            self.winfo_exists()
        except:
            return

        app = self.winfo_toplevel()
        if self._state == 'idle' or getattr(app, 'active_page', None) != 'snipe' or getattr(app, 'settings', {}).get('reduce_motion', False):
            if getattr(self, '_static_state', None) == (self._state, self._counter_text):
                self.after(250, self._animate)
                return
        self._static_state = (self._state, self._counter_text)
        colors = self.STATE_COLORS.get(self._state, self.STATE_COLORS['idle'])
        label  = self.STATE_LABELS.get(self._state, '')
        s = self.size
        cx, cy = self.cx, self.cy
        ro, ri = self.r_outer, self.r_inner

        self.delete('all')

        # Glow background circle
        glow_r = ro + 4
        self.create_oval(cx-glow_r, cy-glow_r, cx+glow_r, cy+glow_r,
                         fill=colors['glow'], outline='')

        # Background ring
        self.create_oval(cx-ro, cy-ro, cx+ro, cy+ro,
                         outline='#222224', width=10, fill='#151817')

        # Spinning arc (sweep 120°)
        self.create_arc(cx-ro, cy-ro, cx+ro, cy+ro,
                        start=self._angle, extent=120,
                        outline=colors['arc'], width=10,
                        style='arc')

        # Pulse ring when offline
        if self._state in ('offline', 'connecting'):
            self._pulse_alpha += 0.06 * self._pulse_dir
            if self._pulse_alpha >= 1.0:
                self._pulse_dir = -1
            elif self._pulse_alpha <= 0.0:
                self._pulse_dir = 1
            p_color = self._hex_blend('#151817', colors['pulse'], self._pulse_alpha)
            pr = ro - 5
            self.create_oval(cx-pr, cy-pr, cx+pr, cy+pr,
                             outline=p_color, width=2, fill='')

        # Ping lines (3 equidistant)
        import math
        for i in range(3):
            a = math.radians(self._angle + i*120)
            x1 = cx + (ri-4) * math.cos(a)
            y1 = cy - (ri-4) * math.sin(a)
            x2 = cx + (ri+2) * math.cos(a)
            y2 = cy - (ri+2) * math.sin(a)
            self.create_line(x1,y1,x2,y2, fill=colors['arc'], width=2)

        # Counter text in center (small)
        if self._counter_text:
            # Puntito pequeño para no tapar el texto
            cd = 2
            self.create_oval(cx-cd, cy-cd, cx+cd, cy+cd,
                             fill=colors['arc'], outline='')
            self.create_text(cx, cy+2, text=self._counter_text,
                             fill=colors['text'],
                             font=('Consolas', 9, 'bold'))
        else:
            # Punto grande en idle
            cd = 6
            self.create_oval(cx-cd, cy-cd, cx+cd, cy+cd,
                             fill=colors['arc'], outline='')

        self._angle = (self._angle + 4) % 360

        try:
            self.after(50, self._animate)  # capped at 20 fps; hidden/reduced states are static
        except:
            pass


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
        self.configure(fg_color="#171919")
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
        divider = ctk.CTkFrame(container, fg_color="#303632", height=1)
        divider.pack(fill="x", pady=(0, 14))

        # Message body
        msg_lbl = ctk.CTkLabel(
            container, text=message,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color="#c9cfc8", wraplength=w - 80,
            justify="left", anchor="nw"
        )
        msg_lbl.pack(fill="x", pady=(0, 10))

        # Input field (only for 'input' type)
        if dialog_type == "input":
            self._entry = ctk.CTkEntry(
                container, height=38,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                fg_color="#222624", border_color="#303632",
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
                hover_color="#222624", text_color="#a6aea7",
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
                hover_color="#222624", text_color="#a6aea7",
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
                "info": "#303632",
                "warning": "#5a4a1a",
                "error": COLOR_RUST_RED
            }.get(dialog_type, "#303632")

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
        self.protocol("WM_Eliminar_WINDOW", self._on_cancel)

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


def styled_showinfo(parent, title, message, **kwargs):
    """Show a styled info dialog. Replaces messagebox.showinfo."""
    d = StyledDialog(parent, title, message, dialog_type="info", **kwargs)
    d.get_result()

def styled_showwarning(parent, title, message, **kwargs):
    """Show a styled warning dialog. Replaces messagebox.showwarning."""
    d = StyledDialog(parent, title, message, dialog_type="warning", **kwargs)
    d.get_result()

def styled_showerror(parent, title, message, **kwargs):
    """Show a styled error dialog. Replaces messagebox.showerror."""
    d = StyledDialog(parent, title, message, dialog_type="error", **kwargs)
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
    def __init__(self, smart_wipe_ip=None):
        super().__init__()
        
        self.smart_wipe_ip = smart_wipe_ip

        self.title("Auto-Queue · Rust")
        
        # Centrar en la pantalla (Landscape Dashboard layout)
        window_width = min(1160, self.winfo_screenwidth() - 80)
        window_height = min(870, self.winfo_screenheight() - 90)
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        self.resizable(True, True)
        self.minsize(960, 680)

        if not os.path.exists(APPDATA_DIR):
            os.makedirs(APPDATA_DIR)

        self._recovery_notices = []
        self._closing = False
        self._page_transition_id = 0
        self._server_executor = ThreadPoolExecutor(max_workers=6, thread_name_prefix="server-query")
        self._server_queries = []
        self.servers_data = self.load_servers()
        self.settings = self.load_settings()

        self.sys_user = os.environ.get('USERNAME', '')
        self.sys_domain = os.environ.get('USERDOMAIN', os.environ.get('COMPUTERNAME', ''))

        # Fuentes reutilizables
        self.font_title = ctk.CTkFont(family="Segoe UI", size=28, weight="bold")
        self.font_subtitle = ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
        self.font_label = ctk.CTkFont(family="Segoe UI", size=12, weight="bold")
        self.font_text = ctk.CTkFont(family="Segoe UI", size=13)
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

        # --- Reconexión Inteligente (modo oculto) ---
        self._reconnect_active = False
        self._reconnect_job = None
        self._reconnect_interval = self.settings.get("reconnect_interval", 30)  # minutos
        self._reconnect_panel_visible = False
        self._version_clicks = 0
        self._version_click_timer = None
        self._reconnect_toplevel = None

        # Variables para animaciones de Skeleton
        self._active_skeletons = set()
        self._skeleton_animator_running = False

        # Banner de Smart Bridge (oculto por defecto)
        self.smart_bridge_banner = ctk.CTkFrame(self, height=40, fg_color="#d46b08", corner_radius=0)
        self.smart_bridge_lbl = ctk.CTkLabel(self.smart_bridge_banner, text="⚡ MODO WIPE INTELIGENTE — Despertado por Auto-Queue", font=self.font_subtitle, text_color="white")
        self.smart_bridge_lbl.pack(pady=5)

        # --- ESTRUCTURA PRINCIPAL (SIDEBAR + CONTENEDOR) ---
        self.sidebar_frame = ctk.CTkFrame(self, width=210, corner_radius=0, fg_color="#171919")
        self.sidebar_frame.pack(side="left", fill="y")
        self.sidebar_frame.pack_propagate(False)
        
        brand = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(28, 10))
        self.brand_image = ctk.CTkImage(light_image=Image.open(get_asset_path("rust.ico")),
                                       dark_image=Image.open(get_asset_path("rust.ico")), size=(38, 38))
        ctk.CTkLabel(brand, text="", image=self.brand_image, width=38, height=38).pack(side="left", padx=(0, 10))
        self.brand_title = ctk.CTkLabel(brand, text="Auto-Queue", width=0, anchor="w",
            font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"), text_color="#f1eee7")
        self.brand_title.pack(side="left")
        ctk.CTkLabel(self.sidebar_frame, text="RUST COMPANION", anchor="w", font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color="#7e8981").pack(fill="x", padx=20, pady=(0, 34))
        ctk.CTkLabel(self.sidebar_frame, text="ESPACIO DE JUEGO", anchor="w", font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"), text_color="#7e8981").pack(fill="x", padx=24, pady=(0, 4))

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
            ("home", self.icon_home, "Inicio"),
            ("snipe", self.icon_snipe, "Wipe en vivo"),
            ("servers", self.icon_servers, "Servidores"),
            ("wake", self.icon_wake, "Auto-despertar"),
            ("logs", self.icon_logs, "Actividad"),
            ("discord", self.icon_discord, "Comunidad")
        ]

        # Contenedor para alinear los botones arriba
        self.nav_container = ctk.CTkFrame(self.sidebar_frame, fg_color="transparent")
        self.nav_container.pack(fill="both", expand=True, pady=(10, 0))
        self.nav_container.grid_columnconfigure(0, weight=1)

        for idx, (page_id, icon_img, text) in enumerate(btn_data):
            # Frame wrapper para el botón y la barra roja
            wrapper = ctk.CTkFrame(self.nav_container, fg_color="transparent", height=45)
            wrapper.grid(row=idx, column=0, sticky="ew", padx=12, pady=3)
            wrapper.pack_propagate(False)
            
            # Barra roja indicadora (oculta por defecto)
            bar = ctk.CTkFrame(wrapper, width=4, corner_radius=0, fg_color="transparent")
            bar.pack(side="left", fill="y")
            self.nav_bars[page_id] = bar

            btn = ctk.CTkButton(
                wrapper,
                text=f"  {text}",
                image=icon_img,
                height=45,
                corner_radius=8,
                fg_color="transparent",
                text_color="#a6aea7",
                hover_color="#222624",
                font=ctk.CTkFont(family="Segoe UI", size=13),
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
        settings_wrapper.pack(side="bottom", fill="x", padx=12, pady=10)
        settings_wrapper.pack_propagate(False)
        
        settings_bar = ctk.CTkFrame(settings_wrapper, width=4, corner_radius=0, fg_color="transparent")
        settings_bar.pack(side="left", fill="y")
        self.nav_bars["settings"] = settings_bar
        
        settings_btn = ctk.CTkButton(
            settings_wrapper,
            text="   Ajustes",
            image=self.icon_settings,
            height=45,
            corner_radius=8,
            fg_color="transparent",
            text_color="#a6aea7",
            hover_color="#222624",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            anchor="w",
            command=lambda: self.switch_page("settings")
        )
        settings_btn.pack(side="left", fill="x", expand=True)
        self.nav_buttons["settings"] = settings_btn

        # Footer in sidebar
        lbl_version = ctk.CTkLabel(self.sidebar_frame, text=f"v{CURRENT_VERSION}", font=ctk.CTkFont(size=10), text_color="#7e8981", cursor="hand2")
        lbl_version.pack(side="bottom", pady=(0, 10))
        lbl_version.bind("<Button-1>", self._on_version_click)
        self._lbl_version = lbl_version
        
        # Panel oculto de reconexión (inicialmente invisible)
        self._reconnect_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#222624", corner_radius=8, border_width=1, border_color="#303632")
        self._rc_toggle_var = ctk.BooleanVar(value=self.settings.get("reconnect_enabled", False))
        rc_title = ctk.CTkLabel(self._reconnect_frame, text="🔄 Reconexión", font=ctk.CTkFont(size=11, weight="bold"), text_color="#df7957")
        rc_title.pack(pady=(8, 2))
        rc_switch = ctk.CTkSwitch(self._reconnect_frame, text="Activa", variable=self._rc_toggle_var, command=self._on_reconnect_toggle,
                                  font=ctk.CTkFont(size=10), progress_color="#df7957", width=40, height=18)
        rc_switch.pack(pady=(0, 4))
        rc_interval_frame = ctk.CTkFrame(self._reconnect_frame, fg_color="transparent")
        rc_interval_frame.pack(fill="x", padx=8, pady=(0, 4))
        ctk.CTkLabel(rc_interval_frame, text="Cada", font=ctk.CTkFont(size=9), text_color="#888").pack(side="left")
        self._rc_interval_label = ctk.CTkLabel(rc_interval_frame, text=f"{self._reconnect_interval} min", font=ctk.CTkFont(size=9, weight="bold"), text_color="#c9cfc8")
        self._rc_interval_label.pack(side="right")
        self._rc_slider = ctk.CTkSlider(self._reconnect_frame, from_=5, to=60, number_of_steps=11, width=130, height=14,
                                        fg_color="#303632", progress_color="#df7957", button_color="#f1eee7",
                                        command=self._on_reconnect_interval_change)
        self._rc_slider.set(self._reconnect_interval)
        self._rc_slider.pack(padx=8, pady=(0, 8))
        # NO pack del frame aún - se muestra con el easter egg
        
        lbl_author = ctk.CTkLabel(self.sidebar_frame, text="Hecho por faabra · Windows", font=ctk.CTkFont(size=10), text_color="#7e8981")
        lbl_author.pack(side="bottom", pady=(0, 0))

        # Crear las páginas
        self.create_home_page()
        self.create_snipe_page()
        self.create_servers_page()
        self.create_wake_page()
        self.create_logs_page()
        self.create_discord_page()
        self.create_settings_page()

        # Inicializar Smart Bridge si corresponde
        if self.smart_wipe_ip:
            self.after(200, self._init_smart_bridge)
        else:
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

        self.protocol("WM_Eliminar_WINDOW", self._on_close)
        self.bind("<Control-f>", self._focus_server_search)
        if self._recovery_notices:
            self.after(800, lambda: styled_showwarning(self, "Configuración recuperada",
                "Se detectó un archivo de configuración dañado o se utilizó su copia .bak. "
                "Revisa tus servidores y preferencias. Los detalles están en el registro."))
        logger.info("Aplicación iniciada v%s", CURRENT_VERSION)

        # Restaurar reconexión inteligente si estaba activa (pero mantener panel oculto)
        if self.settings.get("reconnect_enabled", False):
            self._start_reconnect_loop()

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
                if is_newer_version(latest_tag, CURRENT_VERSION):
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
        w.configure(fg_color="#171919")
        
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
            
        btn_accept = ctk.CTkButton(btn_frame, text="✅ Actualizar", fg_color="#9dbb9d", hover_color="#218838", command=on_accept)
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
            with urllib.request.urlopen(req, timeout=30) as response:
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
                                
            if downloaded == 0 or (total_size > 0 and downloaded != total_size):
                raise ValueError("La descarga está incompleta. Vuelve a intentarlo.")
            with open(new_exe_path, "rb") as downloaded_file:
                if downloaded_file.read(2) != b"MZ":
                    raise ValueError("El archivo descargado no es un ejecutable de Windows.")
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
        return load_json(CONFIG_FILE, validate_servers, dict, self._recovery_notices.append)

    def save_servers(self):
        try:
            save_json(CONFIG_FILE, self.servers_data, validate_servers)
            return True
        except (OSError, ValueError) as error:
            logger.exception("Error guardando servidores")
            styled_showerror(self, "No se pudo guardar", f"Tus cambios no se han guardado.\n{error}")
            return False

    def load_settings(self):
        return load_json(SETTINGS_FILE, validate_settings, lambda: validate_settings({}), self._recovery_notices.append)

    def save_settings(self):
        try:
            save_json(SETTINGS_FILE, self.settings, validate_settings)
            return True
        except (OSError, ValueError) as error:
            logger.exception("Error guardando preferencias")
            styled_showerror(self, "No se pudo guardar", f"Tus preferencias no se han guardado.\n{error}")
            return False

    def _valid_address(self, value):
        try:
            return normalize_address(value)
        except ValueError as error:
            styled_showwarning(self, "Dirección incorrecta", str(error))
            return None

    def _on_close(self):
        if self._closing:
            return
        if self._delay_save_timer is not None:
            self.after_cancel(self._delay_save_timer)
            self._delay_save_timer = None
            if not self.save_settings():
                return
        self._closing = True
        self.is_sniping = False
        self.snipe_run_id = None
        self._stop_reconnect_loop()
        self.destroy()
        self._server_executor.shutdown(wait=False, cancel_futures=True)

    def report_callback_exception(self, exc_type, value, traceback):
        logger.error("Error de interfaz", exc_info=(exc_type, value, traceback))
        if not self._closing:
            styled_showerror(self, "Error inesperado", "No se pudo completar la acción. Consulta el registro para ver los detalles.")

    def _focus_server_search(self, event=None):
        self.switch_page("servers")
        self.server_search.focus_set()
        return "break"

    def _schedule_server_filter(self, *args):
        job = getattr(self, "_server_filter_job", None)
        if job is not None:
            self.after_cancel(job)
        self._server_filter_job = self.after(300, self._apply_server_filter)

    def _apply_server_filter(self):
        self._server_filter_job = None
        self.refresh_server_list(self.pages["servers"])

    def create_settings_page(self):
        page = ctk.CTkScrollableFrame(self.container_frame, fg_color="transparent")
        self.pages["settings"] = page
        ctk.CTkLabel(page, text="Ajustes", font=self.font_title, text_color=COLOR_RUST_RED).pack(anchor="w", padx=24, pady=(24, 8))
        ctk.CTkLabel(page, text="Preferencias y herramientas de mantenimiento", font=self.font_text, text_color="#a6aea7").pack(anchor="w", padx=24, pady=(0, 20))
        card = ctk.CTkFrame(page, fg_color="#1b1e1d", border_width=1, border_color="#303632")
        card.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(card, text="Interfaz", font=self.font_subtitle).pack(anchor="w", padx=18, pady=(16, 10))
        self.reduce_motion_var = ctk.BooleanVar(value=self.settings.get("reduce_motion", False))
        def save_motion():
            self.settings["reduce_motion"] = self.reduce_motion_var.get()
            self.save_settings()
        ctk.CTkSwitch(card, text="Reducir animaciones", variable=self.reduce_motion_var, command=save_motion,
                      progress_color=COLOR_RUST_RED).pack(anchor="w", padx=18, pady=(0, 16))
        reconnect = ctk.CTkFrame(page, fg_color="#1b1e1d", border_width=1, border_color="#303632")
        reconnect.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(reconnect, text="Reconexión", font=self.font_subtitle).pack(anchor="w", padx=18, pady=(16, 10))
        ctk.CTkSwitch(reconnect, text="Activar el vigilante de reconexión", variable=self._rc_toggle_var,
                      command=self._on_reconnect_toggle, progress_color=COLOR_RUST_RED).pack(anchor="w", padx=18, pady=8)
        ctk.CTkLabel(reconnect, text="Comprueba periódicamente si Rust está abierto y envía una conexión.\nNo confirma si ya estás dentro del servidor o en la cola.",
                     font=self.font_text, text_color="#a6aea7", justify="left").pack(anchor="w", padx=18, pady=8)
        self.settings_interval_label = ctk.CTkLabel(reconnect, text=f"Intervalo: {self._reconnect_interval} minutos", font=self.font_text)
        self.settings_interval_label.pack(anchor="w", padx=18)
        self.settings_interval_slider = ctk.CTkSlider(reconnect, from_=5, to=60, number_of_steps=11, command=self._on_reconnect_interval_change,
                                                    progress_color=COLOR_RUST_RED)
        self.settings_interval_slider.set(self._reconnect_interval)
        self.settings_interval_slider.pack(fill="x", padx=18, pady=(8, 18))
        tools = ctk.CTkFrame(page, fg_color="#1b1e1d", border_width=1, border_color="#303632")
        tools.pack(fill="x", padx=24, pady=8)
        ctk.CTkLabel(tools, text="Datos y diagnóstico", font=self.font_subtitle).pack(anchor="w", padx=18, pady=(16, 10))
        ctk.CTkButton(tools, text="Abrir carpeta de datos y copias", command=lambda: os.startfile(APPDATA_DIR),
                      fg_color="#2b2b30", hover_color="#3b3b40").pack(fill="x", padx=18, pady=6)
        ctk.CTkButton(tools, text="Ejecutar diagnóstico del sistema", command=self.run_system_diagnostic,
                      fg_color="#2b2b30", hover_color="#3b3b40").pack(fill="x", padx=18, pady=(6, 18))

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
            ctk.CTkLabel(tab_v.tab("Enchufe Inteligente"), text=active_text, text_color="#9dbb9d", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        elif method == "bios":
            ctk.CTkLabel(tab_v.tab("BIOS RTC"), text=active_text, text_color="#9dbb9d", font=ctk.CTkFont(weight="bold")).pack(pady=5)
        elif method == "software":
            ctk.CTkLabel(tab_v.tab("Software (Beta)"), text=active_text, text_color="#9dbb9d", font=ctk.CTkFont(weight="bold")).pack(pady=5)

    def get_current_ip_from_entry(self):
        raw_val = self.ip_entry.get().strip()
        if not raw_val or raw_val == "Selecciona un servidor..." or "💡" in raw_val: return ""
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
        try:
            ip = normalize_address(ip)
        except ValueError:
            return
        self.home_card.pack(fill="x", padx=20, pady=(0, 12), after=self.ip_frame)
        
        self.hc_title.configure(text=raw_val if raw_val in self.servers_data else "Servidor No Guardado")
        self.hc_status.configure(text="   COMPROBANDO   ", text_color="#aaa")
        
        self._home_query_id = getattr(self, "_home_query_id", 0) + 1
        query_id = self._home_query_id
        # Iniciar esqueletos
        self.hc_ping.configure(text="        ", text_color="#303632", fg_color="#303632", corner_radius=4)
        self.hc_players.configure(text="              ", text_color="#303632", fg_color="#303632", corner_radius=4)
        self._register_skeleton(self.hc_ping)
        self._register_skeleton(self.hc_players)
        
        
        def do_fetch():
            import socket, re, subprocess, threading
            host = ip.split(":")[0] if ":" in ip else ip
            port = int(ip.split(":")[1]) if ":" in ip else 28015
            
            a2s_data = None
            for test_port in list(dict.fromkeys([port, port + 1, port + 15, 28015])):
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
                    if self._closing or query_id != self._home_query_id or not self.hc_status.winfo_exists(): return
                    
                    self._unregister_skeleton(self.hc_ping)
                    self._unregister_skeleton(self.hc_players)
                    
                    if a2s_data:
                        self.hc_players.configure(text=a2s_data["players_text"], text_color="#ccc", fg_color="transparent")
                    else:
                        self.hc_players.configure(text="— / — jugadores", text_color="#ccc", fg_color="transparent")
                        
                    if is_online or a2s_data:
                        self.hc_status.configure(text=" ● Disponible ", text_color="#9dbb9d")
                        self.hc_ping.configure(text=f"Ping: {ms}ms" if ms else "Ping: <1ms", text_color="white", fg_color="transparent")
                    else:
                        self.hc_status.configure(text=" Sin respuesta ", text_color="#d9534f")
                        self.hc_ping.configure(text="Ping: FAIL", text_color="#d9534f", fg_color="transparent")
                except Exception: pass
            self.after(0, update_ui)
        import threading
        threading.Thread(target=do_fetch, daemon=True).start()

    def test_windows_password(self):
        password = self.pw_entry.get()
        user = self.user_entry.get().strip()
        if not password or not user:
            styled_showwarning(self, "Aviso", "Por favor, escribe tu usuario y contraseña antes de verificar.")
            return
            
        advapi32 = ctypes.WinDLL('advapi32', use_last_error=True)
        LOGON32_LOGON_NETWORK = 3
        LOGON32_PROVIDER_DEFAULT = 0
        token = ctypes.c_void_p()
        
        result = advapi32.LogonUserW(
            user,
            self.sys_domain,
            password,
            LOGON32_LOGON_NETWORK,
            LOGON32_PROVIDER_DEFAULT,
            ctypes.byref(token)
        )
        
        if result:
            ctypes.windll.kernel32.CloseHandle(token)
            ToastNotification.show(self, "Contraseña verificada", "success")
            self.pw_entry.configure(border_color="#9dbb9d")
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

    def _register_skeleton(self, widget):
        self._active_skeletons.add(widget)
        if self.settings.get("reduce_motion", False):
            widget.configure(fg_color="#303632")
            return
        if not self._skeleton_animator_running:
            self._skeleton_animator_running = True
            self._skeleton_animator_loop(0)

    def _unregister_skeleton(self, widget):
        if widget in self._active_skeletons:
            self._active_skeletons.remove(widget)

    def _skeleton_animator_loop(self, step):
        import math
        if self._closing or self.settings.get("reduce_motion", False):
            self._skeleton_animator_running = False
            return
        # Clean up destroyed widgets
        self._active_skeletons = {w for w in self._active_skeletons if w.winfo_exists()}
        
        if not self._active_skeletons:
            self._skeleton_animator_running = False
            return
            
        # Oscilar entre #202022 y #323238 usando un sin wave
        factor = (math.sin(step * 0.15) + 1) / 2  # de 0 a 1
        
        r1, g1, b1 = int("20", 16), int("20", 16), int("22", 16)
        r2, g2, b2 = int("32", 16), int("32", 16), int("38", 16)
        
        cr = int(r1 + (r2 - r1) * factor)
        cg = int(g1 + (g2 - g1) * factor)
        cb = int(b1 + (b2 - b1) * factor)
        
        color_hex = f"#{cr:02x}{cg:02x}{cb:02x}"
        
        for w in self._active_skeletons:
            try:
                w.configure(fg_color=color_hex)
            except Exception:
                pass
                
        self.after(50, lambda: self._skeleton_animator_loop(step + 1))

    def _init_smart_bridge(self):
        # 1. Ocultar sidebar
        self.sidebar_frame.pack_forget()
        
        # 2. Mostrar banner
        self.smart_bridge_banner.pack(side="top", fill="x", before=self.container_frame)
        
        # 3. Cambiar a Wipe-Spam
        self.switch_page("snipe")
        
        # 4. Configurar IP y arrancar
        self.snipe_ip_entry.set(self.smart_wipe_ip)
        self.toggle_snipe()

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
        if not self.settings.get("reduce_motion", False):
            self.btn_activate.configure(fg_color=COLOR_RUST_HOVER)
            self.after(100, lambda: self.btn_activate.configure(fg_color=COLOR_RUST_RED) if not self._closing else None)

    def _pulse_status(self):
        """Animación de pulso suave en el indicador de estado."""
        if self.settings.get("reduce_motion", False):
            return
        def animate_pulse(step):
            if not hasattr(self, 'status_dot') or not self.status_dot.winfo_exists(): return
            if step <= 10:
                # Crecer: de 18 a 22
                size = 18 + int(step * 0.4)
            elif step <= 20:
                # Encoger: de 22 a 18
                size = 22 - int((step - 10) * 0.4)
            else:
                self.status_dot.configure(font=ctk.CTkFont(size=12))
                return
                
            self.status_dot.configure(font=ctk.CTkFont(size=size))
            self.after(20, lambda: animate_pulse(step + 1))
            
        animate_pulse(1)

    def _show_saved_feedback(self):
        """Muestra feedback visual '✓ Guardado' temporal (A2)."""
        ToastNotification.show(self, "Guardado correctamente", "success")

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
                match = re.search(r'\+connect(?:%20|\s+)([^\s"%]+)', f.read())
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
                if (ip.get("ip") if isinstance(ip, dict) else ip) == active_ip:
                    alias_display = alias
                    break
            if self.btn_activate.cget("text") != "Actualizar configuración  →":
                self.btn_activate.configure(text="Actualizar configuración  →")
        else:
            if self.btn_activate.cget("text") != "Activar auto-cola  →":
                self.btn_activate.configure(text="Activar auto-cola  →")

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
            if self.status_label.cget("text") != "Sin activar":
                self.status_label.configure(text="Sin activar", text_color="#f1eee7")
                self.status_dot.configure(text_color=COLOR_INACTIVE)
                self.status_frame.configure(fg_color="#1b1e1d")
        elif queue_active and not logon_active:
            if self.status_label.cget("text") != "Revisa la configuración":
                self.status_label.configure(text="Revisa la configuración", text_color=COLOR_YELLOW)
                self.status_dot.configure(text_color=COLOR_YELLOW)
                self.status_frame.configure(fg_color="#28251e")
        else:
            display = f"({alias_display})" if alias_display else ""
            target_text = f"Auto-cola preparada {display}"
            if self.status_label.cget("text") != target_text:
                self.status_label.configure(text=target_text, text_color=COLOR_GREEN)
                self.status_dot.configure(text_color=COLOR_GREEN)
                self.status_frame.configure(fg_color="#1b251e")

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
                self.status_wake_label.configure(text="Sin despertador configurado", text_color="#7e8981")

        # 6. Resumen en el status principal si todo está OK
        if queue_active and logon_active:
            display = f"({alias_display})" if alias_display else ""
            target_text = f"Auto-cola preparada {display}"
            if self.status_label.cget("text") != target_text:
                self.status_label.configure(text=target_text, text_color=COLOR_GREEN)
                self.status_dot.configure(text_color=COLOR_GREEN)
                self.status_frame.configure(fg_color="#1b251e")

    def _get_steam_exe(self):
        """Devuelve la ruta completa del ejecutable de Steam."""
        import winreg
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            s_exe, _ = winreg.QueryValueEx(key, "SteamExe")
            winreg.CloseKey(key)
            if s_exe:
                return s_exe.replace('/', '\\')
        except Exception:
            pass
        return "steam.exe"

    def _ensure_steam_account(self):
        """Si hay cuenta activa seleccionada, cierra Steam y lo reabre con esa cuenta configurada."""
        import subprocess, time as _time
        active_steam_user = self.settings.get("active_steam_user")
        if not active_steam_user:
            return
        
        # Configurar registro y loginusers.vdf
        self.set_active_steam_account(active_steam_user)
        
        # Desactivar el selector de cuentas de Steam ("¿Quién va a jugar?")
        self._set_steam_user_chooser(False)
        
        # Comprobar si Steam está abierto
        try:
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq steam.exe', '/NH'],
                                  capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
            steam_running = 'steam.exe' in result.stdout.lower()
        except Exception:
            steam_running = False
        
        if steam_running:
            steam_exe = self._get_steam_exe()
            # Cerrar Steam limpiamente
            try:
                subprocess.run([steam_exe, '-shutdown'], creationflags=subprocess.CREATE_NO_WINDOW, timeout=5)
            except Exception:
                try:
                    subprocess.run(['taskkill', '/F', '/IM', 'steam.exe'], 
                                 creationflags=subprocess.CREATE_NO_WINDOW, timeout=5)
                except Exception:
                    pass
            
            # Esperar a que Steam cierre completamente
            for _ in range(15):  # max 7.5 segundos
                _time.sleep(0.5)
                try:
                    r = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq steam.exe', '/NH'],
                                     capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    if 'steam.exe' not in r.stdout.lower():
                        break
                except Exception:
                    break
            
            _time.sleep(1)  # margen extra
            
            # Relanzar Steam (sin juego, solo para que arranque con la cuenta correcta)
            try:
                subprocess.Popen([steam_exe], creationflags=subprocess.CREATE_NO_WINDOW)
                _time.sleep(3)  # dar tiempo a que Steam arranque
            except Exception:
                pass
        
        logger.info("Steam preparado con cuenta: %s", active_steam_user)

    def _set_steam_user_chooser(self, enabled):
        """Activa o desactiva el 'AlwaysShowUserChooser' en config.vdf de Steam."""
        import re
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            steam_path, _ = winreg.QueryValueEx(key, "SteamPath")
            winreg.CloseKey(key)
        except Exception:
            return
        
        config_path = os.path.join(steam_path, "config", "config.vdf")
        if not os.path.exists(config_path):
            return
        
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                content = f.read()
            
            new_val = "1" if enabled else "0"
            
            if '"AlwaysShowUserChooser"' in content:
                content = re.sub(
                    r'("AlwaysShowUserChooser"\s*)"[^"]*"',
                    rf'\1"{new_val}"',
                    content
                )
            else:
                # Insertar dentro del bloque "WebStorage" > "Auth" si existe, o crear
                if '"Auth"' in content:
                    content = re.sub(
                        r'("Auth"\s*\{)',
                        rf'\1\n\t\t\t"AlwaysShowUserChooser"\t\t"{new_val}"',
                        content
                    )
            
            with open(config_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info("Steam AlwaysShowUserChooser -> %s", new_val)
        except Exception as e:
            logger.error("Error modificando config.vdf: %s", e)

    def _get_steam_launch_cmd(self, ip, as_list=False):
        """Devuelve el comando para lanzar Rust via steam:// URL (para ejecución directa, NO para .bat)."""
        ip = normalize_address(ip)
        import time
        rust_args_url = f"+connect%20{ip}%20+aq%20{int(time.time())}"
        
        if as_list:
            return ['explorer.exe', f'steam://run/252490//{rust_args_url}']
        else:
            return f'start explorer.exe "steam://run/252490//{rust_args_url}"'

    def activate_auto_queue(self):
        # Animación visual del botón
        self._flash_activate_button()

        # 1. Validación de IP de Servidor
        raw_ip = self.get_current_ip_from_entry()
        ip = raw_ip
        ip = self._valid_address(ip)
        if ip is None:
            return
        
        if not ip:
            styled_showwarning(self, "Falta dirección", "Por favor, introduce la IP o dominio del servidor de Rust.")
            return
        if not IP_PORT_RE.match(ip):
            styled_showwarning(self, "Formato incorrecto",
                f"La dirección '{ip}' no parece válida.\nDebe ser una IP o dominio (con o sin puerto).\nEjemplos:\n- 192.168.1.100:28015\n- jugar.rustserver.com:28015")
            return

        # 2. Validación de Contraseña
        password = self.pw_entry.get()
        user = self.user_entry.get().strip()
        
        # Guardar usuario
        if user:
            self.settings["saved_sys_user"] = user
            self.save_settings()
            
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
        self._ensure_steam_account()

        # ACCIÓN A: Escribir credenciales en Registro (Winlogon)
        if password:
            try:
                key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, "AutoAdminLogon", 0, winreg.REG_SZ, "1")
                winreg.SetValueEx(key, "DefaultUserName", 0, winreg.REG_SZ, user)
                winreg.SetValueEx(key, "DefaultDomainName", 0, winreg.REG_SZ, self.sys_domain)
                winreg.SetValueEx(key, "DefaultPassword", 0, winreg.REG_SZ, password)
                winreg.CloseKey(key)
                
                # Deshabilitar pedir contraseña al despertar (AC y DC) - IMPORTANTE PARA SUSPENDER
                try:
                    import subprocess
                    subprocess.run("powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_NONE CONSOLELOCK 0", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    subprocess.run("powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_NONE CONSOLELOCK 0", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    subprocess.run("powercfg /SETACTIVE SCHEME_CURRENT", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                    
                    # Respaldo por registro por si powercfg falla (Políticas de grupo)
                    power_key_path = r"SOFTWARE\Policies\Microsoft\Power\PowerSettings\0e796bdb-100d-47d6-a2d5-f7d2daa51f51"
                    try:
                        winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, power_key_path)
                        power_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, power_key_path, 0, winreg.KEY_SET_VALUE)
                        winreg.SetValueEx(power_key, "ACSettingIndex", 0, winreg.REG_DWORD, 0)
                        winreg.SetValueEx(power_key, "DCSettingIndex", 0, winreg.REG_DWORD, 0)
                        winreg.CloseKey(power_key)
                    except Exception: pass
                except Exception as e:
                    logger.warning("No se pudo desactivar el bloqueo en suspensión: %s", e)
                    
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
            steam_preludio = ""
        else:
            # Usar steam://run/ con %%20 (escapado para batch) en vez de %20
            # En un .bat, %2 se interpreta como parámetro del script, así que
            # hay que escapar con %% para obtener un literal %
            rust_url = f'steam://run/252490//+connect%%20{ip}'
            exe_cmd = f'start explorer.exe "{rust_url}"'
            
            # Preparar preludio de cambio de cuenta Steam para el .bat
            active_steam_user = self.settings.get("active_steam_user")
            steam_preludio = ""
            if active_steam_user:
                steam_exe = self._get_steam_exe()
                steam_preludio = (
                    f'REM --- Cambio de cuenta Steam ---\n'
                    f'taskkill /F /IM steam.exe >nul 2>&1\n'
                    f'timeout /t 5 /nobreak >nul\n'
                    f'start "" "{steam_exe}"\n'
                    f'timeout /t 10 /nobreak >nul\n'
                    f'REM --- Fin cambio de cuenta ---\n'
                )

        # Añadir inicio de Auto-Queue si Reconexión está activa
        auto_queue_cmd = ""
        if self.settings.get("reconnect_enabled", False):
            import sys, os
            is_compiled = getattr(sys, 'frozen', False)
            if is_compiled:
                auto_queue_cmd = f'\nREM --- Iniciar vigilante de reconexión ---\nstart "" "{sys.executable}"\n'
            else:
                auto_queue_cmd = f'\nREM --- Iniciar vigilante de reconexión ---\nstart "" "{sys.executable}" "{os.path.abspath(__file__)}"\n'

        if one_time:
            bat_content = (
                f'@echo off\n'
                f'timeout /t {delay} /nobreak\n'
                f'{steam_preludio}'
                f'{exe_cmd}\n'
                f'{auto_queue_cmd}'
                f'timeout /t 5 /nobreak\n'
                f'del "%~f0"\n'
            )
        else:
            bat_content = f'@echo off\ntimeout /t {delay} /nobreak\n{steam_preludio}{exe_cmd}\n{auto_queue_cmd}'
        
        try:
            with open(self.startup_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
            self.check_status()
            logger.info("Auto-cola ACTIVADA - IP: %s, Delay: %ds, OneTime: %s", ip, delay, one_time)
            ToastNotification.show(self, "Auto-Cola activada correctamente", "success")
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
            
            # Restaurar pedir contraseña al despertar (AC y DC)
            try:
                import subprocess
                subprocess.run("powercfg /SETACVALUEINDEX SCHEME_CURRENT SUB_NONE CONSOLELOCK 1", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run("powercfg /SETDCVALUEINDEX SCHEME_CURRENT SUB_NONE CONSOLELOCK 1", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                subprocess.run("powercfg /SETACTIVE SCHEME_CURRENT", shell=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
                power_key_path = r"SOFTWARE\Policies\Microsoft\Power\PowerSettings\0e796bdb-100d-47d6-a2d5-f7d2daa51f51"
                try:
                    power_key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, power_key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.SetValueEx(power_key, "ACSettingIndex", 0, winreg.REG_DWORD, 1)
                    winreg.SetValueEx(power_key, "DCSettingIndex", 0, winreg.REG_DWORD, 1)
                    winreg.CloseKey(power_key)
                except Exception: pass
            except Exception: pass
        except Exception as e:
            logger.warning("Error limpiando registro Winlogon: %s", e)

        # Restaurar el selector de cuentas de Steam
        self._set_steam_user_chooser(True)
        # ACCIÓN B: Borrar .bat
        try:
            if os.path.exists(self.startup_path):
                os.remove(self.startup_path)
            self.check_status()
            logger.info("Auto-cola DESACTIVADA")
            ToastNotification.show(self, "Auto-Cola desactivada", "info")
        except Exception as e:
            logger.error("Error borrando .bat de startup: %s", e)

    def test_connection(self):
        """Prueba la conexión al servidor usando subprocess (D3)."""
        raw_ip = self.get_current_ip_from_entry()
        ip = raw_ip
        ip = self._valid_address(ip)
        if ip is None:
            return
            
        if not ip: return
        if not IP_PORT_RE.match(ip):
            styled_showwarning(self, "Formato incorrecto", f"La dirección '{ip}' no parece válida.")
            return

        # Aplicar la cuenta activa antes de probar
        self._ensure_steam_account()

        try:
            subprocess.Popen(self._get_steam_launch_cmd(ip, as_list=True),
                            creationflags=subprocess.CREATE_NO_WINDOW)
            logger.info("Test de conexión lanzado: %s", ip)
        except Exception as e:
            logger.error("Error al probar conexión: %s", e)

    def run_system_diagnostic(self):
        """Verifica todos los componentes críticos del sistema y muestra un resumen."""
        import winreg, os, subprocess
        results = []
        all_ok = True

        # 1. Permisos de administrador
        try:
            import ctypes as _ctypes
            is_admin = _ctypes.windll.shell32.IsUserAnAdmin() != 0
            if is_admin:
                results.append(("Permisos Admin", "✅ Ejecutándose como Administrador"))
            else:
                results.append(("Permisos Admin", "⚠️ Sin permisos elevados (algunas funciones pueden fallar)"))
                all_ok = False
        except:
            results.append(("Permisos Admin", "❌ No se pudo verificar"))
            all_ok = False

        # 2. Steam detectado
        try:
            import winreg as _reg
            key = _reg.OpenKey(_reg.HKEY_CURRENT_USER, r"Software\Valve\Steam")
            steam_path, _ = _reg.QueryValueEx(key, "SteamPath")
            if os.path.exists(steam_path):
                results.append(("Steam", f"✅ Encontrado en: {steam_path}"))
            else:
                results.append(("Steam", "❌ Ruta de Steam no existe"))
                all_ok = False
        except:
            results.append(("Steam", "⚠️ No se encontró Steam en el registro"))
            all_ok = False

        # 3. Archivo .bat de arranque
        try:
            if hasattr(self, 'startup_path') and os.path.exists(self.startup_path):
                results.append(("Archivo .bat", f"✅ Existe en Inicio de Windows"))
            else:
                results.append(("Archivo .bat", "❌ No configurado (Auto-Cola no activa)"))
        except:
            results.append(("Archivo .bat", "❌ No se pudo verificar"))

        # 4. AutoLogon en registro
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon",
                0, winreg.KEY_READ)
            auto_logon, _ = winreg.QueryValueEx(key, "AutoAdminLogon")
            default_user, _ = winreg.QueryValueEx(key, "DefaultUserName")
            if auto_logon == "1":
                results.append(("AutoLogon", f"✅ Activo para usuario: {default_user}"))
            else:
                results.append(("AutoLogon", "⚠️ No configurado"))
        except Exception as e:
            results.append(("AutoLogon", "❌ No configurado o sin acceso al registro"))

        # 5. Servidor guardado
        if self.servers_data:
            active_ip = self.get_active_ip_from_bat()
            if active_ip:
                results.append(("Servidor Objetivo", f"✅ IP configurada: {active_ip}"))
            else:
                results.append(("Servidor Objetivo", f"⚠️ Hay {len(self.servers_data)} servidor(es) pero ninguno activo en .bat"))
        else:
            results.append(("Servidor Objetivo", "❌ No hay servidores guardados"))
            all_ok = False

        # 6. Conectividad (ping rápido al primero)
        try:
            active_ip = self.get_active_ip_from_bat()
            if active_ip:
                import socket
                host = active_ip.split(":")[0]
                port = int(active_ip.split(":")[1]) if ":" in active_ip else 28015
                sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                sock.settimeout(1.5)
                sock.sendto(b'\xFF\xFF\xFF\xFFTSource Engine Query\x00', (host, port))
                data, _ = sock.recvfrom(256)
                sock.close()
                if data:
                    results.append(("Conectividad A2S", f"✅ Servidor responde ({host}:{port})"))
                else:
                    results.append(("Conectividad A2S", f"⚠️ Sin respuesta"))
            else:
                results.append(("Conectividad A2S", "➖ No hay IP activa para probar"))
        except Exception as e:
            results.append(("Conectividad A2S", f"❌ Sin respuesta (puede estar offline o wipeando)"))

        # Construir modal visual con CTkToplevel
        modal = ctk.CTkToplevel(self)
        modal.title("Diagnóstico del Sistema")
        modal.configure(fg_color="#121214")
        modal.resizable(False, False)
        modal.transient(self)
        modal.grab_set()
        
        self.update_idletasks()
        mw, mh = 500, min(120 + len(results) * 72, 560)
        x = self.winfo_x() + (self.winfo_width() - mw) // 2
        y = self.winfo_y() + (self.winfo_height() - mh) // 2
        modal.geometry(f"{mw}x{mh}+{x}+{y}")
        
        _icon_path = os.path.join(sys._MEIPASS, 'rust.ico') if hasattr(sys, '_MEIPASS') else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rust.ico')
        if os.path.exists(_icon_path):
            modal.after(50, lambda: modal.iconbitmap(_icon_path))
        
        header_color = "#9dbb9d" if all_ok else "#e09a20"
        header_text = "✅  Todo correcto" if all_ok else "⚠️  Se encontraron advertencias"
        
        header_frame = ctk.CTkFrame(modal, fg_color=header_color, corner_radius=0, height=56)
        header_frame.pack(fill="x")
        header_frame.pack_propagate(False)
        ctk.CTkLabel(header_frame, text=header_text, font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"), text_color="white").pack(expand=True)
        
        scroll = ctk.CTkScrollableFrame(modal, fg_color="transparent", scrollbar_button_color="#333", scrollbar_button_hover_color="#555")
        scroll.pack(fill="both", expand=True, padx=16, pady=12)
        
        icon_map = {"✅": "#9dbb9d", "⚠️": "#e09a20", "❌": "#df7957", "➖": "#7e8981"}
        
        for name, status in results:
            row = ctk.CTkFrame(scroll, fg_color="#222624", corner_radius=8, border_width=1, border_color="#303632")
            row.pack(fill="x", pady=4)
            
            # Determinar color del icono
            row_color = "#555"
            for symbol, color in icon_map.items():
                if symbol in status:
                    row_color = color
                    break
            
            accent = ctk.CTkFrame(row, fg_color=row_color, width=4, corner_radius=0)
            accent.pack(side="left", fill="y")
            
            txt_frame = ctk.CTkFrame(row, fg_color="transparent")
            txt_frame.pack(side="left", fill="x", expand=True, padx=12, pady=8)
            
            ctk.CTkLabel(txt_frame, text=name.upper(), font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), text_color="#a6aea7", anchor="w").pack(fill="x")
            ctk.CTkLabel(txt_frame, text=status, font=ctk.CTkFont(family="Segoe UI", size=13), text_color="white", anchor="w", wraplength=380).pack(fill="x")
        
        btn_close = ctk.CTkButton(modal, text="Cerrar", height=36, fg_color="#222624", hover_color="#303632", command=modal.destroy)
        btn_close.pack(fill="x", padx=16, pady=(0, 12))

    def create_home_page(self):
        build_home(self, get_asset_path, Tooltip)

    def _run_snipe_thread(self, ip, lbl_status, btn_snipe, run_id=None):
        import socket, time, subprocess
        host = ip.split(":")[0] if ":" in ip else ip
        port = int(ip.split(":")[1]) if ":" in ip else 28015
        radar = getattr(self, 'snipe_radar', None)
        
        def is_active():
            return self.is_sniping and (run_id is None or getattr(self, 'snipe_run_id', None) == run_id)

        def set_radar(state, extra=''):
            if radar:
                self.after(0, lambda s=state, e=extra: radar.set_state(s, e))

        # Fase 1: Esperar a que el servidor se apague
        set_radar('waiting_offline')
        self.after(0, lambda: is_active() and lbl_status.configure(text="Fase 1: Esperando Wipe (Servidor Online...)", text_color="#a6aea7"))
        
        def check_online():
            for test_port in list(dict.fromkeys([port, port + 1, port + 15, 28015])):
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
                self.after(0, lambda a=attempts: is_active() and lbl_status.configure(text=f"Fase 1: Esperando Wipe (Servidor Online...) | Intentos: {a}", text_color="#a6aea7"))
                set_radar('waiting_offline', f'ping {attempts}')
                time.sleep(3.0)
                
        if not is_active():
            return
            
        # Fase 2: El servidor está offline.
        set_radar('offline')
        self.after(0, lambda: is_active() and lbl_status.configure(text=f"Fase 2: Wipe en proceso. Esperando A2S...", text_color="#d9bc7d"))
        attempts = 0
        while is_active():
            attempts += 1
            if check_online():
                break
                
            msg = f"Fase 2: Wipe en proceso. Esperando A2S... | Pings: {attempts}"
            self.after(0, lambda m=msg: is_active() and lbl_status.configure(text=m, text_color="#d9bc7d"))
            set_radar('offline', f'{attempts}')
            time.sleep(getattr(self, 'snipe_aggr_delay', 0.5))
            
        if not is_active():
            return
            
        # Conectado!
        self.is_sniping = False
        set_radar('connecting')
        self.after(0, lambda: lbl_status.configure(text="¡SERVIDOR ONLINE! Conectando en 0ms...", text_color="#00ff00"))
        self.after(0, lambda: btn_snipe.configure(text="Iniciar vigilancia", fg_color=COLOR_RUST_RED, hover_color=COLOR_RUST_HOVER))
        self.after(3000, lambda: set_radar('idle') if not self.is_sniping else None)
        
        try:
            import winsound
            winsound.Beep(1000, 300)
            time.sleep(0.1)
            winsound.Beep(1500, 600)
        except: pass

        try:
            subprocess.Popen(self._get_steam_launch_cmd(ip, as_list=True), creationflags=subprocess.CREATE_NO_WINDOW)
            logger.info("Snipe Wipe: Conexión lanzada: %s", ip)
            
            # Cierre automático en modo Smart Bridge
            if getattr(self, 'smart_wipe_ip', None):
                logger.info("Smart Bridge: Conectado. Cerrando UI.")
                self.after(5000, self.destroy)
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
                
        ip = self._valid_address(ip)
        if ip is None:
            return
            
        if not ip or not IP_PORT_RE.match(ip):
            styled_showwarning(self, "Formato incorrecto", f"La dirección '{ip}' no parece válida.")
            return

        import subprocess
        try:
            subprocess.Popen(self._get_steam_launch_cmd(ip, as_list=True), creationflags=subprocess.CREATE_NO_WINDOW)
            styled_showinfo(self, "Prueba de Conexión", f"Se ha enviado la petición a Steam para conectar a:\n{ip}\n\nRevisa Rust, debería estar conectándose al servidor.")
        except Exception as e:
            from tkinter import messagebox
            messagebox.showerror("Error", f"No se pudo lanzar el juego:\n{e}")
            
    def _toggle_snipe(self, lbl_status, btn_snipe):
        if getattr(self, 'is_sniping', False):
            self.is_sniping = False
            self.snipe_run_id = None
            lbl_status.configure(text="Vigilancia detenida", text_color="#ff5555")
            btn_snipe.configure(text="Iniciar vigilancia", fg_color=COLOR_RUST_RED, hover_color=COLOR_RUST_HOVER)
            if hasattr(self, 'snipe_radar'): self.snipe_radar.set_state('idle')
            return

        raw_val = self.snipe_ip_entry.get().strip()
        if not raw_val or raw_val == "Selecciona un servidor..." or "💡" in raw_val:
            styled_showwarning(self, "Selecciona Servidor", "Por favor selecciona un servidor de la lista primero.")
            return
            
        ip = raw_val
        if raw_val in self.servers_data:
            data = self.servers_data[raw_val]
            ip = data["ip"] if isinstance(data, dict) else data
            
        ip = self._valid_address(ip)
        if ip is None:
            return
            
        if not ip or not IP_PORT_RE.match(ip):
            styled_showwarning(self, "Formato incorrecto", f"La dirección '{ip}' no parece válida.")
            return

        # Start sniping
        self.is_sniping = True
        import time
        self.snipe_run_id = time.time()
        lbl_status.configure(text="Iniciando motor de Spam...", text_color="#a6aea7")
        btn_snipe.configure(text="Detener vigilancia", fg_color="#ff5555", hover_color="#cc4444")
        
        import threading
        self.snipe_thread = threading.Thread(target=self._run_snipe_thread, args=(ip, lbl_status, btn_snipe, self.snipe_run_id), daemon=True)
        self.snipe_thread.start()

    def create_snipe_page(self):
        build_snipe(self, RadarCanvas)

    def create_servers_page(self):
        build_servers(self)

    def add_new_server_inline(self):
        alias = self.new_alias_entry.get().strip()
        ip = self.new_ip_entry.get().strip()
        
        ip = self._valid_address(ip)
        if ip is None:
            return
            
        if not alias or not ip:
            styled_showwarning(self, "Campos vacíos", "Por favor, introduce tanto el alias como la dirección IP/Dominio.")
            return
            
        if not IP_PORT_RE.match(ip):
            styled_showwarning(self, "Formato incorrecto",
                f"La dirección '{ip}' no parece válida.\nDebe ser una IP o dominio (con o sin puerto).\nEjemplos:\n- 192.168.1.100:28015\n- jugar.rustserver.com:28015")
            return
            
        if alias in self.servers_data:
            styled_showwarning(self, "Alias existente", "Ese nombre ya existe. Edita el servidor o elige otro alias.")
            return
        try:
            candidate = validate_servers({**self.servers_data, alias: {"ip": ip, "fav": False}})
        except ValueError as error:
            styled_showwarning(self, "Servidor incorrecto", str(error))
            return
        previous = self.servers_data
        self.servers_data = candidate
        if not self.save_servers():
            self.servers_data = previous
            return
        
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
        
        # Icono de la ventana
        import sys, os
        _icon = os.path.join(sys._MEIPASS, 'rust.ico') if hasattr(sys, '_MEIPASS') else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rust.ico')
        if os.path.exists(_icon):
            def _apply_icon():
                try: modal.iconbitmap(_icon)
                except: pass
            modal.after(50, _apply_icon)
            modal.after(250, _apply_icon)

        # Center the modal
        self.update_idletasks()
        x = self.winfo_x() + (self.winfo_width() - 600) // 2
        y = self.winfo_y() + (self.winfo_height() - 500) // 2
        modal.geometry(f"+{x}+{y}")

        title_lbl = ctk.CTkLabel(modal, text="🏆 SERVIDORES DESTACADOS", font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=COLOR_RUST_RED)
        title_lbl.pack(pady=(20, 10))

        subtitle_lbl = ctk.CTkLabel(modal, text="Selección Gourmet de las mejores redes de Rust. Añádelos con un solo clic.", font=self.font_text, text_color="#a6aea7")
        subtitle_lbl.pack(pady=(0, 20))

        scroll = ctk.CTkScrollableFrame(modal, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        def add_featured(srv_alias, srv_ip):
            if srv_alias in self.servers_data:
                styled_showinfo(modal, "Aviso", "¡Este servidor ya está en tu lista!")
                return
            self.servers_data[srv_alias] = {"ip": srv_ip, "fav": False}
            if not self.save_servers():
                del self.servers_data[srv_alias]
                return
            self.refresh_server_list(self.pages.get("servers", self))
            ToastNotification.show(modal, f"Añadido: {srv_alias}")

        for srv in FEATURED_SERVERS:
            row_frame = ctk.CTkFrame(scroll, fg_color="#222624", border_width=1, border_color="#303632", corner_radius=8)
            row_frame.pack(fill="x", pady=5)
            
            info_frame = ctk.CTkFrame(row_frame, fg_color="transparent")
            info_frame.pack(side="left", padx=15, pady=10, fill="x", expand=True)
            
            ctk.CTkLabel(info_frame, text=srv["alias"], font=ctk.CTkFont(size=15, weight="bold"), text_color="white", anchor="w").pack(fill="x")
            ctk.CTkLabel(info_frame, text=srv["desc"], font=ctk.CTkFont(size=12), text_color="#a6aea7", anchor="w").pack(fill="x")
            
            btn = ctk.CTkButton(row_frame, text="+ Añadir", width=80, height=30, fg_color="#9dbb9d", hover_color="#218838", font=ctk.CTkFont(weight="bold"), command=lambda a=srv["alias"], i=srv["ip"]: add_featured(a, i))
            btn.pack(side="right", padx=15)

    def refresh_server_list(self, w):
        for future in self._server_queries:
            future.cancel()
        self._server_queries.clear()
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
            
            icon_lbl = ctk.CTkLabel(empty_frame, text="＋", font=ctk.CTkFont(family="Segoe UI", size=40), text_color="#444444")
            icon_lbl.pack(pady=(30, 10))
            
            title_lbl = ctk.CTkLabel(empty_frame, text="Sin servidores guardados", font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"), text_color="#c9cfc8")
            title_lbl.pack(pady=(0, 6))
            
            empty_lbl = ctk.CTkLabel(empty_frame, text="Añade tu primer servidor usando el formulario superior\no explora los servidores destacados.", text_color="#7e8981", font=self.font_text, justify="center")
            empty_lbl.pack()
            
            btn_featured = ctk.CTkButton(
                empty_frame, text="Explorar servidores destacados  ↗",
                fg_color="#1e1e21", hover_color="#2b2b30",
                border_width=1, border_color="#303632",
                text_color="#a6aea7", height=38,
                font=ctk.CTkFont(family="Segoe UI", size=13),
                command=self.open_featured_servers_modal
            )
            btn_featured.pack(pady=20)
            self._add_press_effect(btn_featured)
            
            if hasattr(self, 'lbl_server_count') and self.lbl_server_count.winfo_exists():
                self.lbl_server_count.configure(text="0 servidores")
            return

        if hasattr(self, 'lbl_server_count') and self.lbl_server_count.winfo_exists():
            self.lbl_server_count.configure(text=f"{len(self.servers_data)} servidor(es)")

        active_ip = self.get_active_ip_from_bat()

        # Sort servers: Favorites first
        sorted_servers = sorted(self.servers_data.items(), key=lambda x: (not (x[1].get("fav", False) if isinstance(x[1], dict) else False), x[0].lower()))

        query = self.server_search_var.get().strip().casefold()
        favorites_only = self.favorites_only_var.get()
        sorted_servers = [(alias, data) for alias, data in sorted_servers
                          if (not favorites_only or data.get("fav", False))
                          and (not query or query in alias.casefold() or query in data["ip"].casefold())]
        self.lbl_server_count.configure(text=f"{len(sorted_servers)} / {len(self.servers_data)} servidores")
        if not sorted_servers:
            ctk.CTkLabel(self.scroll_servers, text="No hay coincidencias.\nPrueba otro nombre o desactiva el filtro de favoritos.",
                         text_color="#a6aea7", font=self.font_text).pack(pady=40)
        for alias, data in sorted_servers:
            ip = data["ip"] if isinstance(data, dict) else data
            is_fav = data.get("fav", False) if isinstance(data, dict) else False
            is_active = (ip == active_ip)
            
            # Main Card
            card = ctk.CTkFrame(self.scroll_servers, fg_color="#1b1e1d", border_width=1, border_color="#303632", corner_radius=12)
            card.pack(fill="x", pady=8, padx=10)

            # Glow hover effect robusto
            def _on_enter(e, c=card):
                try: c.configure(border_color="#526054")
                except: pass
                
            def _on_leave(e, c=card):
                try:
                    x, y = c.winfo_pointerxy()
                    cx, cy = c.winfo_rootx(), c.winfo_rooty()
                    cw, ch = c.winfo_width(), c.winfo_height()
                    if not (cx <= x <= cx + cw and cy <= y <= cy + ch):
                        c.configure(border_color="#303632")
                except: pass
                
            def bind_hover(widget):
                widget.bind("<Enter>", _on_enter, add="+")
                widget.bind("<Leave>", _on_leave, add="+")
                for child in widget.winfo_children():
                    bind_hover(child)
            
            # --- TOP SECTION (Avatar + Title + Favorite) ---
            top_frame = ctk.CTkFrame(card, fg_color="transparent")
            top_frame.pack(fill="x", padx=15, pady=(15, 10))
            
            # Avatar
            avatar = ctk.CTkFrame(top_frame, width=50, height=50, corner_radius=10, fg_color="#151817", border_width=1, border_color="#303632")
            avatar.pack(side="left")
            avatar.pack_propagate(False)
            lbl_avatar = ctk.CTkLabel(avatar, text=alias[:2].upper(), font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"), text_color=COLOR_RUST_RED)
            lbl_avatar.pack(expand=True)
            
            # Titles
            titles_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
            titles_frame.pack(side="left", padx=15, fill="x", expand=True)
            
            lbl_alias = ctk.CTkLabel(titles_frame, text=alias, font=ctk.CTkFont(family="Segoe UI", size=17, weight="bold"), text_color="#f1eee7", anchor="w")
            lbl_alias.pack(fill="x")
            
            lbl_subtitle = ctk.CTkLabel(titles_frame, text="                           ", font=self.font_small, text_color="#303632", fg_color="#303632", corner_radius=4, anchor="w")
            lbl_subtitle.pack(fill="x")
            
            self._register_skeleton(lbl_subtitle)
            
            # Favorite Star
            def toggle_fav_cmd(target_alias=alias):
                previous = dict(self.servers_data[target_alias])
                if isinstance(self.servers_data[target_alias], str):
                    self.servers_data[target_alias] = {"ip": self.servers_data[target_alias], "fav": True}
                else:
                    self.servers_data[target_alias]["fav"] = not self.servers_data[target_alias].get("fav", False)
                if not self.save_servers():
                    self.servers_data[target_alias] = previous
                    return
                self.refresh_server_list(w)

            star_color = COLOR_YELLOW if is_fav else "#444444"
            btn_fav = ctk.CTkButton(top_frame, text="★", width=40, height=40, font=ctk.CTkFont(size=24), fg_color="transparent", hover_color="#303632", text_color=star_color, command=toggle_fav_cmd)
            btn_fav.pack(side="right")
            
            # --- MIDDLE SECTION (Active + Players) ---
            mid_frame = ctk.CTkFrame(card, fg_color="transparent")
            mid_frame.pack(fill="x", padx=15, pady=5)
            
            status_badge = ctk.CTkLabel(mid_frame, text=" COMPROBANDO ", font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"), fg_color="#333333", text_color="#a6aea7", corner_radius=6, height=26, width=90)
            status_badge.pack(side="left")
            
            lbl_ping = ctk.CTkLabel(mid_frame, text="        ", font=ctk.CTkFont(size=11, weight="bold"), text_color="#303632", fg_color="#303632", corner_radius=4)
            lbl_ping.pack(side="left", padx=10)
            
            lbl_wipe = ctk.CTkLabel(mid_frame, text="", font=ctk.CTkFont(size=11), text_color="#a6aea7")
            lbl_wipe.pack(side="left", padx=(0, 10))
            
            lbl_players = ctk.CTkLabel(mid_frame, text="              ", font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), text_color="#303632", fg_color="#303632", corner_radius=4)
            lbl_players.pack(side="right")

            self._register_skeleton(lbl_ping)
            self._register_skeleton(lbl_players)
            
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
            
            btn_join = ctk.CTkButton(action_frame, text="Usar este servidor  →" if not is_active else "Servidor activo", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), height=36, fg_color="#392a24" if not is_active else "#27382b", hover_color=COLOR_RUST_HOVER if not is_active else "#218838", command=select_cmd)
            btn_join.pack(side="left", fill="x", expand=True, padx=(0, 5))
            
            def manual_smart_wipe_cmd(target_alias=alias):
                self.snipe_ip_entry.set(target_alias)
                self.switch_page("snipe")

            btn_smart = ctk.CTkButton(action_frame, text="Esperar wipe", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), height=40, width=110, fg_color="#222624", hover_color="#303632", command=manual_smart_wipe_cmd)
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
                    previous = self.servers_data.pop(target_alias)
                    if not self.save_servers():
                        self.servers_data[target_alias] = previous
                        return
                    self.refresh_server_list(window)
                    
            btn_copy = ctk.CTkButton(bottom_frame, text="Copiar IP", font=ctk.CTkFont(size=11, weight="bold"), width=80, height=28, fg_color="#151817", hover_color="#303632", border_width=1, border_color="#333", command=copy_cmd)
            btn_copy.pack(side="left")
            
            lbl_ip = ctk.CTkLabel(bottom_frame, text=ip, font=ctk.CTkFont(size=11), text_color="#777")
            lbl_ip.pack(side="left", padx=8)
            
            def stats_cmd(target_ip=ip):
                import webbrowser
                host = target_ip.split(":")[0] if ":" in target_ip else target_ip
                webbrowser.open(f"https://www.battlemetrics.com/servers/rust?q={host}")

            btn_stats = ctk.CTkButton(bottom_frame, text="Estadísticas", font=ctk.CTkFont(size=11, weight="bold"), width=60, height=28, fg_color="#151817", hover_color="#303632", border_width=1, border_color="#333", command=stats_cmd)
            btn_stats.pack(side="left", padx=10)

            btn_del = ctk.CTkButton(bottom_frame, text="Eliminar", font=ctk.CTkFont(size=11, weight="bold"), width=60, height=28, fg_color="#151817", hover_color="#3a1e1b", text_color=COLOR_RUST_RED, border_width=1, border_color="#333", command=delete_cmd)
            btn_del.pack(side="right")
            
            btn_edit = ctk.CTkButton(bottom_frame, text="Editar", font=ctk.CTkFont(size=11, weight="bold"), width=60, height=28, fg_color="#151817", hover_color="#303632", border_width=1, border_color="#333", command=edit_cmd)
            btn_edit.pack(side="right", padx=5)

            # Launch async data fetcher
            self._fetch_server_data_async(ip, lbl_subtitle, status_badge, lbl_players, lbl_ping, lbl_wipe, lbl_avatar)
            
            # Aplicar eventos de hover recursivamente a la tarjeta
            bind_hover(card)

    def _fetch_server_data_async(self, ip, lbl_subtitle, status_badge, lbl_players, lbl_ping, lbl_wipe, lbl_avatar):
        """Query A2S for players/name and ping for latency in a background thread."""
        def do_fetch():
            import socket, re
            host = ip.split(":")[0] if ":" in ip else ip
            port = int(ip.split(":")[1]) if ":" in ip else 28015
            
            a2s_data = None
            for test_port in list(dict.fromkeys([port, port + 1, port + 15, 28015])):
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
                                    
                                    # Create a solid background matching the CARD fg_color (#1b1e1d)
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
                            
                        # Parar esqueletos y mostrar datos
                        self._unregister_skeleton(lbl_subtitle)
                        self._unregister_skeleton(lbl_players)
                        lbl_subtitle.configure(text=base_text, text_color="#a6aea7", fg_color="transparent")
                        lbl_players.configure(text=a2s_data["players_text"], text_color="#dddddd", fg_color="transparent")
                        
                        if wipe_info:
                            lbl_wipe.configure(text=f"    {wipe_info}")
                        else:
                            lbl_wipe.configure(text="")
                    else:
                        self._unregister_skeleton(lbl_subtitle)
                        self._unregister_skeleton(lbl_players)
                        lbl_subtitle.configure(text="Rust Server (A2S Unreachable)", text_color="#a6aea7", fg_color="transparent")
                        lbl_players.configure(text="— / — jugadores", text_color="#dddddd", fg_color="transparent")
                        lbl_wipe.configure(text="")
                        
                    self._unregister_skeleton(lbl_ping)
                    if a2s_data:
                        status_badge.configure(text=" ACTIVE ● ", fg_color="#9dbb9d", text_color="white")
                        lbl_ping.configure(text=f"Ping: {ms}ms" if ms else "Ping: <1ms", text_color="#888", fg_color="transparent")
                    elif is_online:
                        status_badge.configure(text=" HOST OK ", fg_color="#e8a020", text_color="white")
                        lbl_ping.configure(text=f"Ping: {ms}ms" if ms else "Ping: <1ms", text_color="#888", fg_color="transparent")
                    else:
                        status_badge.configure(text=" Sin respuesta ", fg_color="#d9534f", text_color="white")
                        lbl_ping.configure(text="Ping: FAIL", text_color="#d9534f", fg_color="transparent")
                        
                    if pil_image:
                        import customtkinter as ctk
                        ctk_img = ctk.CTkImage(light_image=pil_image, dark_image=pil_image, size=(50, 50))
                        lbl_avatar.configure(image=ctk_img, text="")
                        lbl_avatar.master.configure(border_width=0)
                        
                except Exception:
                    pass

            self.after(0, update_ui)

        if not self._closing:
            self._server_queries.append(self._server_executor.submit(do_fetch))

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
        
        if new_alias != old_alias and new_alias in self.servers_data:
            styled_showwarning(self, "Alias existente", "Ya hay un servidor con ese nombre.")
            return
        new_ip = self._valid_address(new_ip)
        if new_ip is None:
            return
        try:
            validate_servers({new_alias: {"ip": new_ip}})
        except ValueError as error:
            styled_showwarning(self, "Servidor incorrecto", str(error))
            return
        previous = {key: dict(value) for key, value in self.servers_data.items()}
        server_obj = self.servers_data.pop(old_alias)
        if isinstance(server_obj, dict):
            server_obj["ip"] = new_ip
            self.servers_data[new_alias] = server_obj
        else:
            self.servers_data[new_alias] = new_ip
            
        if not self.save_servers():
            self.servers_data = previous
            return
        if self.ip_entry.get() == old_alias:
            self.ip_entry.set(new_alias)
        if self.snipe_ip_entry.get() == old_alias:
            self.snipe_ip_entry.set(new_alias)
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
                imported = validate_servers(read_json(path))
                if not isinstance(imported, dict):
                    styled_showerror(self, "Error", "El archivo no tiene el formato esperado.")
                    return
                previous = dict(self.servers_data)
                validate_servers({**imported, **self.servers_data})
                count_new = 0
                for alias, ip in imported.items():
                    if alias not in self.servers_data:
                        if isinstance(ip, str):
                            self.servers_data[alias] = {"ip": ip, "fav": False}
                        else:
                            self.servers_data[alias] = ip
                        count_new += 1
                if not self.save_servers():
                    self.servers_data = previous
                    return
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
        
        desc_lbl = ctk.CTkLabel(tf, text=normal_desc, font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#a6aea7", justify="left", wraplength=400)
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
                ToastNotification.show(self, f"Despertador a las {h}:{m} programado", "success")
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
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 8))
        
        lbl_title = ctk.CTkLabel(header, text="Auto-despertar", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color="#f1eee7")
        lbl_title.pack(side="left")
        
        lbl_subtitle = ctk.CTkLabel(wake_page, text="Elige cómo preparar el encendido del PC antes de tu sesión.", font=self.font_subtitle, text_color="#aaa")
        lbl_subtitle.grid(row=1, column=0, sticky="w", padx=20, pady=(0, 10))
        
        # Tabview
        tabview = ctk.CTkTabview(wake_page, segmented_button_selected_color=COLOR_RUST_RED, segmented_button_selected_hover_color=COLOR_RUST_HOVER)
        tabview.grid(row=2, column=0, sticky="nsew", padx=20, pady=5)
        
        t1 = tabview.add("Enchufe Inteligente")
        t2 = tabview.add("BIOS RTC")
        t3 = tabview.add("Software (Beta)")
        
        # TAB 1: SMART PLUG
        txt1 = ("Para encender el equipo mediante un enchufe inteligente.\n\n"
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
        self.combo_h = ctk.CTkOptionMenu(time_frame, values=[f"{i:02d}" for i in range(24)], width=70, fg_color="#222624", button_color="#222624", button_hover_color="#2a2a2c")
        self.combo_h.set("09")
        self.combo_h.pack(side="left", padx=5)
        CTkScrollableDropdown(self.combo_h, values=[f"{i:02d}" for i in range(24)],
                              fg_color="#1e1e1f", button_color="transparent", hover_color="#2b2b2d",
                              frame_border_color="#303632", frame_corner_radius=8, text_color="white", alpha=1.0)
        
        ctk.CTkLabel(time_frame, text="Min:", font=self.font_label).pack(side="left", padx=5)
        self.combo_m = ctk.CTkOptionMenu(time_frame, values=[f"{i:02d}" for i in range(60)], width=70, fg_color="#222624", button_color="#222624", button_hover_color="#2a2a2c")
        self.combo_m.set("30")
        self.combo_m.pack(side="left", padx=5)
        CTkScrollableDropdown(self.combo_m, values=[f"{i:02d}" for i in range(60)],
                              fg_color="#1e1e1f", button_color="transparent", hover_color="#2b2b2d",
                              frame_border_color="#303632", frame_corner_radius=8, text_color="white", alpha=1.0)
        
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
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 16))
        
        lbl_title = ctk.CTkLabel(header, text="Actividad", font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"), text_color="#f1eee7")
        lbl_title.pack(side="left")
        
        # Textbox for logs
        self.log_textbox = ctk.CTkTextbox(
            logs_page,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color="#151817",
            border_color="#303632",
            border_width=1,
            text_color="#c9cfc8",
            activate_scrollbars=True,
            scrollbar_button_color="#333",
            scrollbar_button_hover_color="#555",
            corner_radius=0
        )
        self.log_textbox.grid(row=1, column=0, sticky="nsew", padx=20, pady=5)
        
        # Configure color tags
        self.log_textbox.tag_config("time", foreground="#7e8981")
        self.log_textbox.tag_config("info", foreground="#ffffff")
        self.log_textbox.tag_config("warning", foreground="#d9bc7d")
        self.log_textbox.tag_config("error", foreground="#ff4444")
        self.log_textbox.tag_config("success", foreground="#9dbb9d")
        
        self.log_textbox.configure(state="disabled")
        
        # Footer buttons
        footer = ctk.CTkFrame(logs_page, fg_color="transparent")
        footer.grid(row=3, column=0, sticky="ew", padx=20, pady=(5, 20))
        
        btn_refresh = ctk.CTkButton(
            footer,
            text="Actualizar",
            width=100,
            height=32,
            fg_color="#222624",
            hover_color="#303632",
            font=self.font_label,
            command=self.refresh_log_viewer
        )
        btn_refresh.pack(side="left", padx=(0, 10))
        
        btn_copy = ctk.CTkButton(
            footer,
            text="Copiar Logs",
            width=100,
            height=32,
            fg_color="#222624",
            hover_color="#303632",
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
        from autoqueue_ui.design import page_heading, card, label, button
        import webbrowser
        page = ctk.CTkFrame(self.container_frame, fg_color="transparent")
        self.pages["discord"] = page
        page_heading(page, "Comunidad", "Un espacio para seguir mejorando Auto-Queue.")
        panel = card(page)
        panel.pack(fill="x", padx=28, pady=12)
        label(panel, "Construido para volver a jugar", 23, bold=True, anchor="w").pack(fill="x", padx=24, pady=(26, 10))
        label(panel, "Consulta novedades, comparte ideas o revisa el código del proyecto.", 13, "#a6aea7", anchor="w").pack(fill="x", padx=24, pady=(0, 24))
        button(panel, "Ver proyecto en GitHub  ↗", lambda: webbrowser.open("https://github.com/Faaabra/Auto-queue")).pack(anchor="w", padx=24, pady=(0, 24))

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

    def _add_press_effect(self, btn):
        """CustomTkinter handles hover/press states without resizing or stale color overrides."""
        pass

    def switch_page(self, page_id):
        if self.active_page == page_id:
            return
            
        for pid, btn in self.nav_buttons.items():
            bar = self.nav_bars.get(pid)
            if pid == page_id:
                btn.configure(fg_color="#392a24", text_color="#efb59f", hover_color="#493128")
                if bar: bar.configure(fg_color=COLOR_RUST_RED)
            else:
                btn.configure(fg_color="transparent", text_color="#a6aea7", hover_color="#222624")
                if bar: bar.configure(fg_color="transparent")
        old_page = self.pages.get(self.active_page)
        new_page = self.pages.get(page_id)
        
        if not new_page:
            return
            
        self.active_page = page_id
        self._page_transition_id += 1
        transition_id = self._page_transition_id
        
        target_height = min(self.winfo_screenheight() - 80, 810 if page_id == "snipe" else 740)
        if page_id == "snipe" and self.winfo_height() < target_height:
            w = self.winfo_width()
            if w <= 1: w = 820
            self.geometry(f"{w}x{target_height}")
        
        if page_id == "logs":
            self.refresh_log_viewer()
            
        for other_page in self.pages.values():
            if other_page not in (new_page, old_page):
                other_page.place_forget()
        new_page.lift()
        if self.settings.get("reduce_motion", False) or old_page is None:
            new_page.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
            if old_page and old_page != new_page:
                old_page.place_forget()
            return
        new_page.place(x=14, rely=0.0, relwidth=1.0, relheight=1.0)
        
        started = time.monotonic()
        def animate():
            if self._closing or transition_id != self._page_transition_id or not new_page.winfo_exists():
                return
            progress = min(1.0, (time.monotonic() - started) / 0.16)
            new_page.place(x=round(14 * (1 - progress) ** 3), rely=0.0, relwidth=1.0, relheight=1.0)
            if progress < 1.0:
                self.after(16, animate)
            else:
                for key, page in self.pages.items():
                    if key != self.active_page:
                        page.place_forget()
        animate()

    # ================================================================
    #  RECONEXIÓN INTELIGENTE (Easter Egg - 7 clics en versión)
    # ================================================================
    def _on_version_click(self, event=None):
        """Easter egg: 7 clics rápidos en la versión abren el panel oculto de reconexión."""
        self._version_clicks += 1
        
        if self._version_click_timer:
            self.after_cancel(self._version_click_timer)
        
        if self._version_clicks >= 7:
            self._version_clicks = 0
            self._toggle_reconnect_panel()
        else:
            # Reset después de 2 segundos sin clics
            self._version_click_timer = self.after(2000, self._reset_version_clicks)

    def _reset_version_clicks(self):
        self._version_clicks = 0

    def _toggle_reconnect_panel(self):
        """Muestra u oculta el panel de reconexión oculto."""
        if self._reconnect_panel_visible:
            self._reconnect_frame.pack_forget()
            self._reconnect_panel_visible = False
            self._lbl_version.configure(text_color="#7e8981")
        else:
            self._reconnect_frame.pack(side="bottom", fill="x", padx=8, pady=(0, 5), before=self._lbl_version)
            self._reconnect_panel_visible = True
            self._lbl_version.configure(text_color="#df7957")
            ToastNotification.show(self, "🔓 Modo Reconexión desbloqueado", "success")

    def _on_reconnect_toggle(self):
        """Callback cuando se activa/desactiva el switch de reconexión."""
        enabled = self._rc_toggle_var.get()
        self.settings["reconnect_enabled"] = enabled
        self.save_settings()
        
        if enabled:
            self._start_reconnect_loop()
            ToastNotification.show(self, f"🔄 Reconexión activa ({self._reconnect_interval} min)", "success")
        else:
            self._stop_reconnect_loop()
            ToastNotification.show(self, "Reconexión desactivada", "info")

    def _on_reconnect_interval_change(self, value):
        """Callback cuando se cambia el slider de intervalo."""
        interval = int(round(value))
        self._reconnect_interval = interval
        self._rc_interval_label.configure(text=f"{interval} min")
        self._rc_slider.set(interval)
        if hasattr(self, "settings_interval_label"):
            self.settings_interval_label.configure(text=f"Intervalo: {interval} minutos")
            self.settings_interval_slider.set(interval)
        self.settings["reconnect_interval"] = interval
        self.save_settings()
        
        # Si está activo, reiniciar el loop con el nuevo intervalo
        if self._reconnect_active:
            self._stop_reconnect_loop()
            self._start_reconnect_loop()

    def _start_reconnect_loop(self):
        """Inicia el loop de reconexión inteligente."""
        self._reconnect_active = True
        logger.info("Reconnect loop iniciado: cada %d minutos", self._reconnect_interval)
        
        # Mostrar ventana de aviso
        if self._reconnect_toplevel is None or not self._reconnect_toplevel.winfo_exists():
            self._reconnect_toplevel = ctk.CTkToplevel(self)
            self._reconnect_toplevel.title("Auto-Queue: Vigilando")
            self._reconnect_toplevel.geometry("380x100")
            self._reconnect_toplevel.attributes("-topmost", True)
            self._reconnect_toplevel.resizable(False, False)
            
            # Quitar de la barra de tareas (hacerla tool window)
            try:
                self._reconnect_toplevel.after(10, lambda: self._reconnect_toplevel.wm_attributes("-toolwindow", True))
            except Exception:
                pass

            lbl_title = ctk.CTkLabel(self._reconnect_toplevel, text="🛡️ Vigilando conexión de Rust...", font=ctk.CTkFont(size=14, weight="bold"), text_color="#a8a8ff")
            lbl_title.pack(pady=(15, 5))
            lbl_desc = ctk.CTkLabel(self._reconnect_toplevel, text="Si cierras esta ventana o el programa principal,\nla reconexión inteligente dejará de funcionar.", font=ctk.CTkFont(size=11), text_color="#a6aea7")
            lbl_desc.pack()
            
            # Si cierran la ventanita, desactivamos la reconexión
            def on_close():
                self._rc_toggle_var.set(False)
                self._on_reconnect_toggle()
            
            self._reconnect_toplevel.protocol("WM_Eliminar_WINDOW", on_close)
        
        self._reconnect_tick()

    def _stop_reconnect_loop(self):
        """Detiene el loop de reconexión."""
        self._reconnect_active = False
        if self._reconnect_job:
            try:
                self.after_cancel(self._reconnect_job)
            except Exception:
                pass
            self._reconnect_job = None
            
        if self._reconnect_toplevel and self._reconnect_toplevel.winfo_exists():
            self._reconnect_toplevel.destroy()
            self._reconnect_toplevel = None
            
        logger.info("Reconnect loop detenido")

    def _reconnect_tick(self):
        """Ejecuta una comprobación de reconexión y programa la siguiente."""
        if not self._reconnect_active:
            return
        
        import threading
        ip = self.get_current_ip_from_entry() or self.get_active_ip_from_bat()
        threading.Thread(target=self._do_reconnect_check, args=(ip,), daemon=True).start()
        
        # Programar siguiente tick
        interval_ms = self._reconnect_interval * 60 * 1000
        self._reconnect_job = self.after(interval_ms, self._reconnect_tick)

    def _do_reconnect_check(self, ip):
        """Comprueba si Rust esta corriendo y manda reconexion.

        Rust ignora steam://run/+connect si ya estas en cola o dentro del servidor.
        Solo actua si estas en el menu principal (kickeado por timeout/corte).
        Comportamiento confirmado por tests reales.
        """
        import subprocess

        if not ip:
            logger.info("Reconnect: No hay IP configurada, saltando")
            return

        # Comprobar si Rust esta corriendo
        try:
            result = subprocess.run(
                ['tasklist', '/FI', 'IMAGENAME eq RustClient.exe', '/NH'],
                capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            rust_running = 'rustclient.exe' in result.stdout.lower()
        except Exception:
            rust_running = False

        if not rust_running:
            logger.info("Reconnect: Rust no esta corriendo, nada que hacer")
            return

        # Rust abierto -> mandar reconexion
        # Si estas en cola o servidor -> Rust LO IGNORA (sin efecto)
        # Si te kickearon al menu -> Rust RECONECTA al servidor
        logger.info("Reconnect: Rust abierto, mandando +connect a %s", ip)
        if self._reconnect_active and not self._closing:
            self.after(0, lambda: self._reconnect_via_steam(ip) if self._reconnect_active else None)

    def _reconnect_via_steam(self, ip):
        """Reconecta lanzando steam://run/+connect IP."""
        import subprocess
        try:
            cmd = self._get_steam_launch_cmd(ip, as_list=True)
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            logger.info("Reconnect: steam://run/+connect lanzado a: %s", ip)
        except Exception as e:
            logger.error("Reconnect: Error: %s", e)


if __name__ == "__main__":
    if len(sys.argv) > 2 and sys.argv[1] == "--smart-wipe":
        app = App(smart_wipe_ip=sys.argv[2])
        app.mainloop()
    else:
        app = App()
        app.mainloop()
