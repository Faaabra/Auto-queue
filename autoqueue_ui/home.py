"""Home dashboard; all system behavior stays in the application controller."""
import os
import tkinter as tk
import customtkinter as ctk
from PIL import Image
from ctk_scrollable_dropdown import CTkScrollableDropdown
from .design import *


def build_home(app, get_asset_path, Tooltip):
    page = ctk.CTkScrollableFrame(app.container_frame, fg_color=BG, corner_radius=0,
                                  scrollbar_button_color=LINE, scrollbar_button_hover_color=QUIET)
    app.pages['home'] = page
    page.grid_columnconfigure(0, weight=1)
    outer = ctk.CTkFrame(page, fg_color='transparent')
    outer.grid(row=0, column=0, sticky='nsew', padx=28, pady=(26, 24))
    outer.grid_columnconfigure(0, weight=1)

    top = ctk.CTkFrame(outer, fg_color='transparent')
    top.grid(row=0, column=0, sticky='ew', pady=(0, 24))
    label(top, 'TU PRÓXIMA SESIÓN', 10, ACCENT, True, anchor='w').pack(fill='x')
    label(top, 'Menos espera. Más Rust.', 30, bold=True, anchor='w').pack(fill='x', pady=(6, 4))
    label(top, 'Prepara tu conexión y deja que Auto-Queue se encargue del arranque.', 13, MUTED, anchor='w').pack(fill='x')

    body = ctk.CTkFrame(outer, fg_color='transparent')
    body.grid(row=1, column=0, sticky='nsew')
    body.grid_columnconfigure(0, weight=6, uniform='home')
    body.grid_columnconfigure(1, weight=5, uniform='home')
    left = ctk.CTkFrame(body, fg_color='transparent')
    left.grid(row=0, column=0, sticky='nsew', padx=(0, 18))
    right = ctk.CTkFrame(body, fg_color='transparent')
    right.grid(row=0, column=1, sticky='nsew')

    server = card(left)
    server.pack(fill='x', pady=(0, 16))
    head = section(server, '01', 'Tu servidor')
    ctk.CTkButton(head, text='Gestionar  ↗', width=86, height=28, fg_color='transparent',
                   hover_color=RAISED, text_color=MUTED, font=font(11), command=lambda: app.switch_page('servers')).pack(side='right')
    app.ip_frame = ctk.CTkFrame(server, fg_color='transparent')
    app.ip_frame.pack(fill='x', padx=20, pady=(0, 14))
    aliases = list(app.servers_data) or ["💡 Añade un servidor (Pestaña 'Servidores')"]
    app.ip_entry = ctk.CTkOptionMenu(app.ip_frame, values=aliases, height=46, font=font(13),
                                    fg_color=FIELD, button_color=RAISED, button_hover_color=LINE, corner_radius=8)
    app.ip_entry.pack(fill='x')
    app.ip_entry.set('Selecciona un servidor...' if app.servers_data else aliases[0])
    app.ip_dropdown = CTkScrollableDropdown(app.ip_entry, values=aliases, command=app.on_home_server_selected,
        fg_color=SURFACE, button_color='transparent', hover_color=RAISED, frame_border_color=LINE,
        frame_corner_radius=10, text_color=TEXT, alpha=1.0)
    app.home_card = ctk.CTkFrame(server, fg_color=FIELD, corner_radius=8)
    app.hc_title = label(app.home_card, 'Esperando selección', 12, TEXT, True, anchor='w')
    app.hc_title.pack(fill='x', padx=12, pady=(10, 4))
    stats = ctk.CTkFrame(app.home_card, fg_color='transparent')
    stats.pack(fill='x', padx=12, pady=(0, 8))
    app.hc_status = label(stats, 'Sin datos', 10, QUIET)
    app.hc_status.pack(side='left')
    app.hc_ping = label(stats, 'Ping: —', 11, MUTED)
    app.hc_ping.pack(side='right')
    app.hc_players = label(app.home_card, '— / — jugadores', 12, MUTED, anchor='w')
    app.hc_players.pack(fill='x', padx=12, pady=(0, 10))
    label(server, 'Elige un favorito o añade un servidor desde su dirección.', 11, QUIET, anchor='w').pack(fill='x', padx=20, pady=(0, 18))

    launch = card(left)
    launch.pack(fill='x', pady=(0, 16))
    section(launch, '02', 'Al iniciar el PC')
    row = ctk.CTkFrame(launch, fg_color='transparent')
    row.pack(fill='x', padx=20)
    label(row, 'Esperar antes de abrir Rust', 12, MUTED).pack(side='left')
    delay = app.settings.get('delay', 10)
    app.delay_value_label = label(row, f'{delay}s', 12, TEXT, True, width=48, fg_color=RAISED, corner_radius=6)
    app.delay_value_label.pack(side='right')
    app.delay_slider = ctk.CTkSlider(launch, from_=5, to=300, number_of_steps=295, height=18,
        command=app.update_delay_label, progress_color=ACCENT, button_color=ACCENT, button_hover_color=ACCENT_HOVER)
    app.delay_slider.set(delay)
    app.delay_slider.pack(fill='x', padx=18, pady=(10, 4))
    label(launch, 'Da tiempo a Windows y a la conexión de red.', 11, QUIET, anchor='w').pack(fill='x', padx=20, pady=(0, 18))
    label(launch, 'Cuenta de Steam', 12, MUTED, anchor='w').pack(fill='x', padx=20, pady=(0, 6))
    app.settings_frame = ctk.CTkFrame(launch, fg_color='transparent')
    app.settings_frame.pack(fill='x', padx=20, pady=(0, 20))
    choices, selected, most_recent = [], None, None
    for user in app.steam_users:
        display = f"{user['persona_name']} ({user['account_name']})"
        choices.append(display)
        if user.get('most_recent'):
            most_recent = display
        if user['account_name'] == app.settings.get('active_steam_user'):
            selected = display
    choices = choices or ['No se detectaron cuentas locales']
    app.steam_dropdown = ctk.CTkOptionMenu(app.settings_frame, values=choices, height=40, font=font(12),
        fg_color=FIELD, button_color=RAISED, button_hover_color=LINE)
    app.steam_dropdown.set(selected or most_recent or choices[0])
    app.steam_dropdown.pack(fill='x')
    CTkScrollableDropdown(app.steam_dropdown, values=choices, command=app.on_steam_user_changed,
        fg_color=SURFACE, button_color='transparent', hover_color=RAISED, frame_border_color=LINE,
        frame_corner_radius=10, text_color=TEXT, alpha=1.0)

    options = card(left)
    options.pack(fill='x')
    app.one_time_var = tk.BooleanVar(value=app.settings.get('one_time_mode', False))
    app.smart_wipe_var = tk.BooleanVar(value=app.settings.get('smart_wipe', False))
    for index, (title, description, variable, command, attribute) in enumerate([
        ('Una sola sesión', 'El arranque automático se elimina tras ejecutarse.', app.one_time_var, app._save_one_time_setting, 'chk_one_time'),
        ('Wipe inteligente', 'Espera al reinicio del servidor antes de conectar.', app.smart_wipe_var, app._save_smart_wipe_setting, 'chk_smart_wipe')]):
        option = ctk.CTkFrame(options, fg_color='transparent')
        option.pack(fill='x', padx=20, pady=(14, 14))
        toggle = ctk.CTkSwitch(option, text='', variable=variable, command=command, width=38, switch_width=36,
            switch_height=20, progress_color=ACCENT, button_color=TEXT, button_hover_color='#ffffff')
        toggle.pack(side='right', padx=(12, 0))
        setattr(app, attribute, toggle)
        label(option, title, 13, bold=True, anchor='w').pack(fill='x')
        label(option, description, 11, MUTED, anchor='w', wraplength=340, justify='left').pack(fill='x', pady=(2, 0))
        if index == 0:
            ctk.CTkFrame(options, height=1, fg_color=LINE).pack(fill='x', padx=20)

    app.status_frame = card(right)
    app.status_frame.pack(fill='x', pady=(0, 16))
    status_head = ctk.CTkFrame(app.status_frame, fg_color='transparent')
    status_head.pack(fill='x', padx=20, pady=(16, 4))
    label(status_head, 'ESTADO DE LA AUTO-COLA', 10, QUIET, True).pack(side='left')
    app.status_dot = label(status_head, '●', 12, QUIET, width=18)
    app.status_dot.pack(side='right')
    app.status_label = label(app.status_frame, 'Sin activar', 21, TEXT, True, anchor='w', wraplength=300, justify='left')
    app.status_label.pack(fill='x', padx=20, pady=(0, 4))
    app.status_wake_label = label(app.status_frame, 'Sin despertador configurado', 11, MUTED, anchor='w')
    app.status_wake_label.pack(fill='x', padx=20, pady=(0, 16))

    identity = card(right)
    identity.pack(fill='x', pady=(0, 16))
    section(identity, '03', 'Inicio de Windows')
    label(identity, 'Opcional · Para entrar sin intervención al encender.', 11, MUTED, anchor='w').pack(fill='x', padx=20, pady=(0, 16))
    label(identity, 'Usuario o correo de Windows', 12, MUTED, anchor='w').pack(fill='x', padx=20, pady=(0, 6))
    app.user_entry = ctk.CTkEntry(identity, placeholder_text='Tu usuario de Windows', height=40, font=font(12))
    app.user_entry.insert(0, app.settings.get('saved_sys_user', app.sys_user))
    app.user_entry.pack(fill='x', padx=20, pady=(0, 12))
    Tooltip(app.user_entry, 'Cuenta local: tu usuario. Cuenta Microsoft: tu correo completo.')
    label(identity, 'Contraseña', 12, MUTED, anchor='w').pack(fill='x', padx=20, pady=(0, 6))
    pw = ctk.CTkFrame(identity, fg_color='transparent')
    pw.pack(fill='x', padx=20, pady=(0, 10))
    app.pw_entry = ctk.CTkEntry(pw, placeholder_text='Contraseña, no PIN', show='*', height=40, font=font(12))
    app.pw_entry.pack(side='left', fill='x', expand=True, padx=(0, 6))
    Tooltip(app.pw_entry, 'AutoLogon guarda esta contraseña en el registro de Windows. Actívalo solo si aceptas ese comportamiento.')
    def toggle_password():
        shown = app.pw_entry.cget('show') == ''
        app.pw_entry.configure(show='*' if shown else '')
        eye.configure(text='◉' if shown else '○')
    eye = ctk.CTkButton(pw, text='◉', width=38, height=40, fg_color=RAISED, hover_color=LINE,
                        text_color=MUTED, font=font(16), command=toggle_password)
    eye.pack(side='right')
    ctk.CTkButton(identity, text='Verificar credenciales  →', height=28, fg_color='transparent',
        hover_color=RAISED, text_color=MUTED, font=font(11), anchor='w', command=app.test_windows_password).pack(fill='x', padx=16, pady=(0, 10))
    note = ctk.CTkFrame(identity, fg_color='#28251e', corner_radius=7)
    note.pack(fill='x', padx=20, pady=(0, 18))
    label(note, 'AutoLogon almacena la contraseña en el registro.\nPuedes activar la cola sin configurarlo.', 11, '#c1b595',
          justify='left', anchor='w').pack(fill='x', padx=10, pady=9)

    app.btn_activate = button(right, 'Activar auto-cola  →', app.activate_auto_queue, primary=True)
    app.btn_activate.configure(height=48)
    app.btn_activate.pack(fill='x', pady=(0, 8))
    app.btn_deactivate = button(right, 'Desactivar y limpiar', app.deactivate_auto_queue)
    app.btn_deactivate.configure(fg_color='transparent', border_width=1, border_color=LINE, text_color=MUTED)
    app.btn_deactivate.pack(fill='x', pady=(0, 12))
    app.btn_auto_wake = button(right, 'Configurar auto-despertar  ↗', lambda: app.switch_page('wake'))
    app.btn_auto_wake.configure(height=34, fg_color='transparent', border_width=0, text_color=MUTED)
    app.btn_auto_wake.pack(fill='x', pady=(0, 2))
    button(right, 'Probar conexión ahora  ↗', app.test_connection).pack(fill='x')
    footer = label(outer, '01  Servidor    /    02  Arranque    /    03  Windows                         Configura una vez. Juega cuando quieras.', 11, QUIET, anchor='w')
    footer.grid(row=2, column=0, sticky='ew', pady=(24, 0))
    return page
