import customtkinter as ctk
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

CURRENT_VERSION = "2.0.3"
# --- INFO DE ACTUALIZACIONES ---
GITHUB_REPO = "Faaabra/Auto-queue"

# ==========================================
# SOLICITUD DE PRIVILEGIOS DE ADMINISTRADOR
# ==========================================
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
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

# Rutas - Guardamos las IPs en AppData
APPDATA_DIR = os.path.join(os.environ["APPDATA"], "RustAutoQueue")
CONFIG_FILE = os.path.join(APPDATA_DIR, "servers.json")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Rust Auto-Queue Launcher - V2")
        
        # Centrar en la pantalla
        window_width = 480
        window_height = 800
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        
        self.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        self.resizable(False, False)

        if not os.path.exists(APPDATA_DIR):
            os.makedirs(APPDATA_DIR)

        self.servers_data = self.load_servers()

        self.sys_user = os.environ.get('USERNAME', '')
        self.sys_domain = os.environ.get('USERDOMAIN', os.environ.get('COMPUTERNAME', ''))

        font_title = ctk.CTkFont(family="Segoe UI", size=42, weight="bold")
        font_subtitle = ctk.CTkFont(family="Segoe UI", size=15, weight="bold")
        font_label = ctk.CTkFont(family="Segoe UI", size=13, weight="bold")
        font_text = ctk.CTkFont(family="Segoe UI", size=13)
        font_small = ctk.CTkFont(family="Segoe UI", size=12)

        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'rust.ico')
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rust.ico')
        if os.path.exists(icon_path):
            try:
                self.iconbitmap(icon_path)
            except:
                pass

        self.startup_path = os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\AutoRustLauncher.bat")

        # --- HEADER ---
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=30, pady=(20, 10))

        self.title_label = ctk.CTkLabel(self.header_frame, text="RUST", font=font_title, text_color=COLOR_RUST_RED)
        self.title_label.pack()
        
        self.subtitle_label = ctk.CTkLabel(self.header_frame, text="AUTO-QUEUE LAUNCHER", font=font_subtitle, text_color="white")
        self.subtitle_label.pack(pady=(0, 5))

        self.status_label = ctk.CTkLabel(self.header_frame, text="Estado: VERIFICANDO...", font=font_small)
        self.status_label.pack()

        # --- AUTO LOGON WINDOWS ---
        self.req_frame = ctk.CTkFrame(self, corner_radius=12, border_width=1, border_color="#333333")
        self.req_frame.pack(fill="x", padx=30, pady=(0, 20))
        
        self.req_label = ctk.CTkLabel(self.req_frame, text="🔑 AUTO-INICIO DE WINDOWS", font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"), text_color="#ffcc00")
        self.req_label.pack(pady=(15, 0))
        
        self.req_desc = ctk.CTkLabel(self.req_frame, text="Imprescindible para que el PC inicie sesión solo al despertarse.", font=font_small, text_color="#aaaaaa")
        self.req_desc.pack(pady=(0, 5))
        
        cred_frame = ctk.CTkFrame(self.req_frame, fg_color="transparent")
        cred_frame.pack(fill="x", padx=15, pady=(0, 10))

        # Cajas visuales de solo lectura (simuladas) para mostrar Equipo y Usuario
        ud_frame = ctk.CTkFrame(cred_frame, fg_color="transparent")
        ud_frame.pack(fill="x", pady=(5, 5))
        
        lbl_domain = ctk.CTkLabel(ud_frame, text=f"Equipo: {self.sys_domain}", font=font_small, text_color="#888")
        lbl_domain.pack(side="left", padx=10)
        
        lbl_user = ctk.CTkLabel(ud_frame, text=f"Usuario: {self.sys_user}", font=font_small, text_color="#888")
        lbl_user.pack(side="right", padx=10)

        # Contraseña Entry
        pw_inner_frame = ctk.CTkFrame(cred_frame, fg_color="transparent")
        pw_inner_frame.pack(fill="x", pady=(5, 0))

        self.btn_check_pw = ctk.CTkButton(pw_inner_frame, text="✅ Verificar", height=35, width=90, fg_color="#333333", hover_color="#555555", font=font_small, command=self.test_windows_password)
        self.btn_check_pw.pack(side="right")

        self.pw_entry = ctk.CTkEntry(pw_inner_frame, placeholder_text="Contraseña de inicio de Windows", show="*", font=font_text, height=35)
        self.pw_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))

        # Botón Modo Auto-Despertar (NUEVO)
        self.btn_auto_wake = ctk.CTkButton(self.req_frame, text="⏰ Modo Auto-Despertar", 
                                        font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                                        fg_color="#1a1a1a", border_width=1, border_color=COLOR_RUST_RED, 
                                        text_color="white", hover_color="#333", height=35, 
                                        command=self.open_auto_wake)
        self.btn_auto_wake.pack(padx=15, pady=(0, 15), fill="x")

        # --- SETTINGS FRAME ---
        self.settings_frame = ctk.CTkFrame(self, corner_radius=12)
        self.settings_frame.pack(fill="x", padx=30, pady=(0, 20))

        self.ip_label = ctk.CTkLabel(self.settings_frame, text="IP del Servidor de Rust:", font=font_label, text_color=COLOR_LIGHT_TEXT)
        self.ip_label.pack(anchor="w", padx=20, pady=(15, 5))
        
        self.ip_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.ip_frame.pack(fill="x", padx=20, pady=(0, 10))

        self.ip_entry = ctk.CTkEntry(self.ip_frame, placeholder_text="Ej: connect 192.168.1.1:28015", font=font_text, height=38, corner_radius=6, border_width=1)
        self.ip_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        self.btn_save_current = ctk.CTkButton(self.ip_frame, text="Guardar IP", width=70, height=38, 
                                              fg_color="#333333", hover_color="#555555", font=font_small, 
                                              command=self.save_current_ip)
        self.btn_save_current.pack(side="left", padx=(0, 10))
        
        self.btn_manage_servers = ctk.CTkButton(self.ip_frame, text="📚 Mis Servidores", width=110, height=38, 
                                                fg_color="#2b2b2b", hover_color="#444444", border_width=1, border_color="#555555", font=font_small, 
                                                command=self.open_server_manager)
        self.btn_manage_servers.pack(side="right")

        self.delay_label = ctk.CTkLabel(self.settings_frame, text="Retraso antes de abrir el juego (segundos):", font=font_label, text_color=COLOR_LIGHT_TEXT)
        self.delay_label.pack(anchor="w", padx=20, pady=(5, 5))
        
        self.slider_frame = ctk.CTkFrame(self.settings_frame, fg_color="transparent")
        self.slider_frame.pack(fill="x", padx=20, pady=(0, 20))
        
        self.delay_slider = ctk.CTkSlider(self.slider_frame, from_=0, to=120, number_of_steps=120, 
                                          button_color=COLOR_RUST_RED, button_hover_color=COLOR_RUST_HOVER, progress_color=COLOR_RUST_RED)
        self.delay_slider.pack(side="left", fill="x", expand=True)
        self.delay_slider.set(10)
        
        self.delay_value_label = ctk.CTkLabel(self.slider_frame, text="10s", font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), width=35)
        self.delay_value_label.pack(side="right", padx=(10, 0))
        self.delay_slider.configure(command=self.update_delay_label)

        # --- ACTIONS FRAME ---
        self.actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_frame.pack(fill="x", padx=30, pady=(0, 10))
        
        self.btn_activate = ctk.CTkButton(self.actions_frame, text="ACTIVAR AUTO-COLA", font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                                          fg_color=COLOR_RUST_RED, hover_color=COLOR_RUST_HOVER, height=45, corner_radius=8,
                                          command=self.activate_auto_queue)
        self.btn_activate.pack(fill="x", pady=(0, 12))

        self.btn_test = ctk.CTkButton(self.actions_frame, text="Probar Conexión Ahora", font=font_text,
                                      fg_color="#333333", hover_color="#444444", height=38, corner_radius=8,
                                      command=self.test_connection)
        self.btn_test.pack(fill="x", pady=(0, 12))

        self.btn_deactivate = ctk.CTkButton(self.actions_frame, text="Desactivar y Borrar", font=font_text,
                                            fg_color="transparent", hover_color="#2b2b2b", border_width=1, border_color="#555555",
                                            text_color="#999999", height=38, corner_radius=8,
                                            command=self.deactivate_auto_queue)
        self.btn_deactivate.pack(fill="x")

        self.check_status()

        # --- FIRMA DEVELOPED BY ---
        self.footer_label = ctk.CTkLabel(self, text="Developed by faabra", font=ctk.CTkFont(family="Segoe UI", size=11, slant="italic"), text_color="#555555")
        self.footer_label.pack(side="bottom", pady=(0, 10))
        
        def on_enter_footer(e):
            self.footer_label.configure(text_color=COLOR_RUST_RED)
        def on_leave_footer(e):
            self.footer_label.configure(text_color="#555555")
            
        self.footer_label.bind("<Enter>", on_enter_footer)
        self.footer_label.bind("<Leave>", on_leave_footer)
        
        # Iniciar comprobador de actualizaciones
        self.check_for_updates()

        # Quitar el foco (cursor) si se hace clic fuera del campo de texto
        def un_focus(event):
            try:
                if event.widget.winfo_class() not in ["Entry", "Text"]:
                    event.widget.focus_set()
            except:
                pass
        self.bind_all("<Button-1>", un_focus)

    # --- SISTEMA DE ACTUALIZACIONES ---
    def check_for_updates(self):
        def check_logic():
            try:
                import urllib.request
                import json
                
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
        
        x = int(self.winfo_x() + (self.winfo_width() / 2) - 210)
        y = int(self.winfo_y() + (self.winfo_height() / 2) - 140)
        w.geometry(f"+{x}+{y}")
        w.transient(self)
        w.grab_set() # Foco obligatorio
        
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
                self.after(0, lambda: messagebox.showinfo("Info de Desarrollo", "La función de auto-parche solo funciona si ejecutas el código compilado como .exe de Windows."))
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
            self.after(0, lambda error=e: messagebox.showerror("Error", f"Fallo al actualizar: {error}"))
            self.after(0, window.destroy)

    # --- LÓGICA DE SERVIDORES ---
    def load_servers(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except: pass
        return {}

    def save_servers(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.servers_data, f, indent=4)
        except: pass

    def save_current_ip(self):
        raw_ip = self.ip_entry.get().strip()
        ip = raw_ip.replace("connect", "").strip() if raw_ip.startswith("connect") else raw_ip
        if not ip:
            messagebox.showwarning("Falta IP", "Introduce o pega una IP en la barra antes de pulsar Guardar.")
            return
            
        dialog = ctk.CTkInputDialog(text="Introduce un nombre (Alias) para tu servidor:", title="Guardar IP")
        
        try:
            icon_path = os.path.join(sys._MEIPASS, 'rust.ico') if hasattr(sys, '_MEIPASS') else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rust.ico')
            if os.path.exists(icon_path):
                dialog.iconbitmap(icon_path)
        except: pass
            
        alias = dialog.get_input()
        if alias:
            self.servers_data[alias] = ip
            self.save_servers()
            messagebox.showinfo("Guardado", f"¡'{alias}' guardado en tus servidores!")

    def test_windows_password(self):
        password = self.pw_entry.get()
        if not password:
            messagebox.showwarning("Aviso", "Por favor, escribe tu contraseña antes de verificar.")
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
            messagebox.showinfo("¡Correcto!", "Verificación exitosa. Esta contraseña es válida y funcionará perfectamente para el arranque automático.")
            self.pw_entry.configure(border_color="#28a745")
        else:
            messagebox.showerror("Clave Incorrecta", "La autenticación ha fallado, esa no es la contraseña.\n\nNOTA: Si ingresas en Windows usando un PIN, huella o Windows Hello, la contraseña real oculta de tu cuenta Microsoft puede ser diferente.")
            self.pw_entry.configure(border_color=COLOR_RUST_RED)

    # --- MÉTODOS DE LA UI PRINCIPAL ---
    def update_delay_label(self, value):
        self.delay_value_label.configure(text=f"{int(value)}s")

    def get_active_ip_from_bat(self):
        try:
            with open(self.startup_path, "r", encoding="utf-8") as f:
                match = re.search(r'\+connect\s+([^\s"]+)', f.read())
                if match: return match.group(1)
        except: pass
        return None

    def check_status(self):
        # Primero miramos si el .bat existe
        if os.path.exists(self.startup_path):
            active_ip = self.get_active_ip_from_bat()
            alias_display = active_ip
            for alias, ip in self.servers_data.items():
                if ip == active_ip:
                    alias_display = alias
                    break
                    
            status_text = f"● ACTIVO ({alias_display}) ●" if alias_display else "● ACTIVO ●"
            self.status_label.configure(text=status_text, text_color="#28a745")
            self.btn_activate.configure(text="ACTUALIZAR CONFIGURACIÓN")
        else:
            self.status_label.configure(text="○  INACTIVO  ○", text_color="#888888")
            self.btn_activate.configure(text="ACTIVAR AUTO-COLA")

    def activate_auto_queue(self):
        # 1. Validación de IP de Servidor
        raw_ip = self.ip_entry.get().strip()
        ip = raw_ip.replace("connect", "").strip() if raw_ip.startswith("connect") else raw_ip
        
        if not ip:
            messagebox.showwarning("Falta IP", "Por favor, introduce la IP del servidor de Rust.")
            return

        # 2. Validación de Contraseña
        password = self.pw_entry.get()
        if not password:
            if not messagebox.askyesno("Aviso", "No has introducido tu contraseña de Windows de AutoLogon. ¿Quieres activar la auto-cola sin configurar el AutoLogon de la cuenta? (Si tienes el PC con código/clave el arranque se quedará bloqueado en la pantalla)."):
                return

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
                messagebox.showerror("Error Sistema", f"No se pudo modificar el registro de AutoLogon.\nPor favor reinicia la aplicación asegurándote de que aceptaste los permisos de Administrador.\nError: {e}")
                return

        # ACCIÓN B: Generar .bat
        delay = int(self.delay_slider.get())
        bat_content = f'@echo off\ntimeout /t {delay} /nobreak\nstart explorer.exe "steam://run/252490//+connect {ip}"\n'
        
        try:
            with open(self.startup_path, "w", encoding="utf-8") as f:
                f.write(bat_content)
            self.check_status()
            messagebox.showinfo("Éxito", "¡Operación completada con éxito!\n\nSe ha configurado el inicio automático de usuario de Windows y se lanzará Rust automáticamente al encender.")
        except Exception as e:
            messagebox.showerror("Error Archivo", f"No se pudo crear el archivo:\n{str(e)}")

    def deactivate_auto_queue(self):
        # ACCIÓN A: Limpiar Registro (Winlogon)
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Winlogon", 0, winreg.KEY_SET_VALUE)
            winreg.SetValueEx(key, "AutoAdminLogon", 0, winreg.REG_SZ, "0")
            try:
                winreg.DeleteValue(key, "DefaultPassword")
            except:
                pass
            winreg.CloseKey(key)
        except:
            pass

        # ACCIÓN B: Borrar .bat
        try:
            if os.path.exists(self.startup_path):
                os.remove(self.startup_path)
            self.check_status()
            messagebox.showinfo("Desactivado", "Todo se ha limpiado correctamente. Tu ordenador volverá a pedir contraseña como de costumbre al arrancar.")
        except: pass

    def test_connection(self):
        raw_ip = self.ip_entry.get().strip()
        ip = raw_ip.replace("connect", "").strip() if raw_ip.startswith("connect") else raw_ip
        if not ip: return
        os.system(f'start explorer.exe "steam://run/252490//+connect {ip}"')

    # --- PESTAÑA GESTOR DE SERVIDORES ---
    def open_server_manager(self):
        w = ctk.CTkToplevel(self)
        w.title("Mis Servidores Guardados")
        
        window_width = 520
        window_height = 550
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        x_cordinate = int((screen_width / 2) - (window_width / 2))
        y_cordinate = int((screen_height / 2) - (window_height / 2))
        w.geometry(f"{window_width}x{window_height}+{x_cordinate}+{y_cordinate}")
        w.resizable(False, False)
        
        import sys
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'rust.ico')
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rust.ico')
        if os.path.exists(icon_path):
            try: 
                w.iconbitmap(icon_path)
                w.after(200, lambda: w.iconbitmap(icon_path))
            except: pass
            
        w.transient(self)
        
        title = ctk.CTkLabel(w, text="Mis Servidores Guardados", font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"), text_color="white")
        title.pack(pady=(20, 10))
        
        desc = ctk.CTkLabel(w, text="Selecciona un alias de tu lista para usar su IP, o añade uno nuevo:", font=ctk.CTkFont(family="Segoe UI", size=13), text_color="#aaaaaa")
        desc.pack(pady=(0, 15))
        
        self.scroll_servers = ctk.CTkScrollableFrame(w, width=450, height=350)
        self.scroll_servers.pack(padx=20, pady=(0, 15), fill="both", expand=True)
        
        self.refresh_server_list(w)

    def refresh_server_list(self, w):
        for widget in self.scroll_servers.winfo_children():
            widget.destroy()
            
        if not self.servers_data:
            empty_lbl = ctk.CTkLabel(self.scroll_servers, text="Aún no tienes ningún servidor guardado en tu lista.\nAñade el primero usando el formulario de abajo.", text_color="#777777")
            empty_lbl.pack(pady=40)
            return

        for alias, ip in self.servers_data.items():
            row = ctk.CTkFrame(self.scroll_servers, fg_color="transparent")
            row.pack(fill="x", pady=5)
            
            info_frame = ctk.CTkFrame(row, fg_color="transparent")
            info_frame.pack(side="left", fill="x", expand=True)
            
            lbl_alias = ctk.CTkLabel(info_frame, text=alias, font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"), text_color="white", anchor="w")
            lbl_alias.pack(fill="x")
            
            lbl_ip = ctk.CTkLabel(info_frame, text=ip, font=ctk.CTkFont(family="Segoe UI", size=12), text_color="#aaaaaa", anchor="w")
            lbl_ip.pack(fill="x")

            def select_cmd(target_ip=ip, window=w):
                self.ip_entry.delete(0, 'end')
                self.ip_entry.insert(0, target_ip)
                window.destroy()

            def delete_cmd(target_alias=alias, window=w):
                if messagebox.askyesno("Eliminar", f"¿Estás seguro de que quieres borrar el servidor '{target_alias}'?"):
                    del self.servers_data[target_alias]
                    self.save_servers()
                    self.refresh_server_list(window)
                else:
                    window.attributes("-topmost", True)
            
            btn_sel = ctk.CTkButton(row, text="📋 Usar", width=70, font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"), 
                                    fg_color="#333333", hover_color="#555555", command=select_cmd)
            btn_sel.pack(side="left", padx=5)
            
            btn_del = ctk.CTkButton(row, text="Borrar", width=50, font=ctk.CTkFont(family="Segoe UI", size=11), 
                                    fg_color="transparent", border_width=1, border_color=COLOR_RUST_RED, text_color=COLOR_RUST_RED, hover_color="#3a1e1b", command=delete_cmd)
            btn_del.pack(side="left", padx=(0, 5))

    # --- NUEVAS GUÍAS ---
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

    # --- LÓGICA DEL MODO AUTO-DESPERTAR ---
    def cancel_wake_task(self, silent=False):
        try:
            subprocess.run(["schtasks", "/delete", "/tn", "RustAutoQueueWake", "/f"], 
                           capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            if not silent:
                messagebox.showinfo("Cancelado", "Despertador cancelado correctamente.")
        except:
            if not silent:
                messagebox.showerror("Error", "No se pudo cancelar la tarea.")

    def create_wake_task(self, h, m):
        import datetime
        now = datetime.datetime.now()
        wake_time = now.replace(hour=int(h), minute=int(m), second=0, microsecond=0)
        
        # Si la hora ya pasó hoy, programar para mañana
        if wake_time <= now:
            wake_time += datetime.timedelta(days=1)
            
        time_str = wake_time.strftime("%Y-%m-%dT%H:%M:%S")
        
        # XML para la tarea programada con WakeToRun activado
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
            # Guardar XML temporal con encoding UTF-16 necesario para schtasks
            tmp_xml = os.path.join(tempfile.gettempdir(), "wake_task.xml")
            with open(tmp_xml, "w", encoding="utf-16") as f:
                f.write(xml_template)
            
            # Crear la tarea
            res = subprocess.run(["schtasks", "/create", "/tn", "RustAutoQueueWake", "/xml", tmp_xml, "/f"], 
                                 capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
            
            if res.returncode == 0:
                messagebox.showinfo("Programado", f"¡Listo! El PC se despertará y reiniciará a las {h}:{m}.\n\nRECUERDA: Ahora debes darle a 'Suspender' o 'Hibernar' en Windows.")
            else:
                messagebox.showerror("Error", f"No se pudo crear la tarea:\n{res.stderr.decode(errors='ignore')}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al generar despertador: {e}")

    def open_auto_wake(self):
        w = ctk.CTkToplevel(self)
        w.title("⏰ Modo Auto-Despertar")
        w.geometry("560x650")
        w.resizable(False, False)
        
        # Centrar
        x = int(self.winfo_x() + (self.winfo_width() / 2) - 280)
        y = int(self.winfo_y() + (self.winfo_height() / 2) - 325)
        w.geometry(f"+{x}+{y}")
        w.transient(self)
        
        # Icono (Corregido para que aparezca siempre)
        if hasattr(sys, '_MEIPASS'):
            icon_path = os.path.join(sys._MEIPASS, 'rust.ico')
        else:
            icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rust.ico')
            
        if os.path.exists(icon_path):
            try: 
                w.iconbitmap(icon_path)
                # Truco de Tkinter para forzar el icono en Toplevel
                w.after(200, lambda: w.iconbitmap(icon_path))
            except: pass

        # Título
        ctk.CTkLabel(w, text="⏰ MODO AUTO-DESPERTAR", font=ctk.CTkFont(size=24, weight="bold"), text_color=COLOR_RUST_RED).pack(pady=(20, 5))
        ctk.CTkLabel(w, text="Cómo entrar al server mientras duermes", font=ctk.CTkFont(size=14), text_color="#aaa").pack(pady=(0, 20))

        # Pestañas
        tabview = ctk.CTkTabview(w, width=500, height=480, segmented_button_selected_color=COLOR_RUST_RED, segmented_button_selected_hover_color=COLOR_RUST_HOVER)
        tabview.pack(padx=20, pady=10)

        t1 = tabview.add("🔌 Enchufe Inteligente")
        t2 = tabview.add("⏱️ BIOS RTC")
        t3 = tabview.add("🌙 Software (Beta)")

        # CONTENIDO TAB 1: ENCHUFE INTELIGENTE
        txt1 = ("Esta es la opción recomendada de Diego (faabra).\n\n"
                "1. Compra un enchufe inteligente (Alexa, Google, etc).\n"
                "2. En la BIOS de tu PC, busca la opción 'Restore on AC Power Loss' y ponla en 'Power On'.\n"
                "3. Apaga el PC al 100% por la noche.\n"
                "4. Programa en tu móvil que el enchufe se encienda a las 9:00 AM.\n\n"
                "¡Al recibir corriente, el PC detectará que debe encenderse solo y lanzará la cola de Rust!")
        ctk.CTkLabel(t1, text=txt1, justify="left", wraplength=440, font=ctk.CTkFont(size=13)).pack(pady=20, padx=20)

        # CONTENIDO TAB 2: BIOS RTC
        txt2 = ("Si no quieres comprar nada, usa el reloj interno de tu placa base.\n\n"
                "1. Entra a la BIOS (F2 o SUPR al arrancar).\n"
                "2. Busca 'Advanced' -> 'APM' o 'Power Management'.\n"
                "3. Activa 'Power On By RTC' o 'RTC Alarm'.\n"
                "4. Pon la hora exacta a la que quieres que el PC se despierte.\n"
                "5. Guarda y apaga el PC.\n\n"
                "El PC se encenderá físicamente a esa hora.")
        ctk.CTkLabel(t2, text=txt2, justify="left", wraplength=440, font=ctk.CTkFont(size=13)).pack(pady=20, padx=20)

        # CONTENIDO TAB 3: SOFTWARE (SLEEP TIMER)
        ctk.CTkLabel(t3, text="Usa este despertador si no quieres tocar la BIOS.\n\nIMPORTANTE: Para que funcione, debes darle a SUSPENDER o HIBERNAR en Windows, no a Apagar.", 
                     justify="left", wraplength=440, font=ctk.CTkFont(size=13, slant="italic"), text_color="#ffcc00").pack(pady=(10, 20))
        
        time_frame = ctk.CTkFrame(t3, fg_color="transparent")
        time_frame.pack(pady=10)
        
        ctk.CTkLabel(time_frame, text="Hora:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=5)
        self.combo_h = ctk.CTkComboBox(time_frame, values=[f"{i:02d}" for i in range(24)], width=70)
        self.combo_h.set("09")
        self.combo_h.pack(side="left", padx=5)
        
        ctk.CTkLabel(time_frame, text="Min:", font=ctk.CTkFont(size=13, weight="bold")).pack(side="left", padx=5)
        self.combo_m = ctk.CTkComboBox(time_frame, values=[f"{i:02d}" for i in range(60)], width=70)
        self.combo_m.set("30")
        self.combo_m.pack(side="left", padx=5)

        btn_prog = ctk.CTkButton(t3, text="⏰ Programar Despertador", fg_color=COLOR_RUST_RED, hover_color=COLOR_RUST_HOVER,
                                command=lambda: self.create_wake_task(self.combo_h.get(), self.combo_m.get()))
        btn_prog.pack(pady=20)

        btn_cancel = ctk.CTkButton(t3, text="Cancelar Tarea Actual", fg_color="transparent", border_width=1, border_color="#555",
                                   command=self.cancel_wake_task)
        btn_cancel.pack(pady=5)


if __name__ == "__main__":
    app = App()
    app.mainloop()
