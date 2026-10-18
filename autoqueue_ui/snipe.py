import customtkinter as ctk
from ctk_scrollable_dropdown import CTkScrollableDropdown
from .design import *


def build_snipe(app, RadarCanvas):
    page = ctk.CTkScrollableFrame(app.container_frame, fg_color=BG, corner_radius=0)
    app.pages['snipe'] = page
    page_heading(page, 'Wipe en vivo', 'Vigila el reinicio del servidor y conecta cuando vuelva a responder.')
    notice = ctk.CTkFrame(page, fg_color='#28251e', corner_radius=9)
    notice.pack(fill='x', padx=28, pady=(0, 20))
    label(notice, 'Mantén Rust abierto en el menú principal. La posición en la cola no está garantizada.',
          12, '#c1b595', anchor='w', wraplength=740, justify='left').pack(fill='x', padx=16, pady=13)
    body = ctk.CTkFrame(page, fg_color='transparent')
    body.pack(fill='x', padx=28)
    body.grid_columnconfigure((0, 1), weight=1, uniform='snipe')
    controls = card(body)
    controls.grid(row=0, column=0, sticky='nsew', padx=(0, 18))
    section(controls, '01', 'Configura la vigilancia')
    label(controls, 'Servidor objetivo', 12, MUTED, anchor='w').pack(fill='x', padx=20, pady=(4, 8))
    aliases = list(app.servers_data) or ['💡 Añade un servidor primero']
    app.snipe_ip_entry = ctk.CTkOptionMenu(controls, values=aliases, height=44, font=font(13),
        fg_color=FIELD, button_color=RAISED, button_hover_color=LINE)
    app.snipe_ip_entry.set('Selecciona un servidor...' if app.servers_data else aliases[0])
    app.snipe_ip_entry.pack(fill='x', padx=20, pady=(0, 28))
    app.snipe_dropdown = CTkScrollableDropdown(app.snipe_ip_entry, values=aliases, command=app.snipe_ip_entry.set,
        fg_color=SURFACE, button_color='transparent', hover_color=RAISED, frame_border_color=LINE,
        frame_corner_radius=10, text_color=TEXT, alpha=1)
    label(controls, 'Frecuencia de comprobación', 12, MUTED, anchor='w').pack(fill='x', padx=20)
    app.lbl_aggr_value = label(controls, 'Media · 0,5 s', 13, ACCENT, True, anchor='w')
    app.lbl_aggr_value.pack(fill='x', padx=20, pady=(4, 14))
    values = [2.0, 1.0, 0.5, 0.2, 0.05]
    names = ['Sutil · 2 s', 'Baja · 1 s', 'Media · 0,5 s', 'Alta · 0,2 s', 'Máxima · 50 ms']
    app.snipe_aggr_delay = 0.5
    def change(value):
        index = int(round(value))
        app.snipe_aggr_delay = values[index]
        app.lbl_aggr_value.configure(text=names[index])
    app.slider_aggr = ctk.CTkSlider(controls, from_=0, to=4, number_of_steps=4, command=change,
        progress_color=ACCENT, button_color=ACCENT)
    app.slider_aggr.set(2)
    app.slider_aggr.pack(fill='x', padx=18, pady=(0, 6))
    legend = ctk.CTkFrame(controls, fg_color='transparent')
    legend.pack(fill='x', padx=20, pady=(0, 22))
    label(legend, 'Menos frecuente', 10, QUIET).pack(side='left')
    label(legend, 'Más frecuente', 10, QUIET).pack(side='right')
    label(controls, 'Una frecuencia alta genera más consultas al servidor.', 11, QUIET,
          anchor='w', wraplength=320, justify='left').pack(fill='x', padx=20, pady=(0, 24))

    monitor = card(body)
    monitor.grid(row=0, column=1, sticky='nsew')
    label(monitor, 'MONITOR DEL SERVIDOR', 10, QUIET, True).pack(pady=(20, 4))
    radar_host = ctk.CTkFrame(monitor, fg_color=FIELD, corner_radius=100)
    radar_host.pack(pady=(12, 10))
    app.snipe_radar = RadarCanvas(radar_host, size=150)
    app.snipe_radar.pack(padx=6, pady=6)
    app.snipe_status_label = label(monitor, 'Esperando un servidor', 15, TEXT, True, wraplength=300, justify='center')
    app.snipe_status_label.pack(padx=16, pady=(0, 6))
    label(monitor, 'La vigilancia comienza cuando tú la activas.', 11, MUTED).pack(padx=16, pady=(0, 20))
    app.btn_snipe = button(controls, 'Iniciar vigilancia', lambda: app._toggle_snipe(app.snipe_status_label, app.btn_snipe), primary=True)
    app.btn_snipe.pack(fill='x', padx=20, pady=(0, 10))
    button(controls, 'Probar conexión  ↗', app._test_snipe_connection).pack(fill='x', padx=20, pady=(0, 20))
    guide = card(page)
    guide.pack(fill='x', padx=28, pady=(20, 24))
    row = ctk.CTkFrame(guide, fg_color='transparent')
    row.pack(fill='x', padx=22, pady=20)
    for number, title, description in [('01', 'Detectar', 'Esperamos a que el servidor se detenga.'),
                                       ('02', 'Vigilar', 'Comprobamos cuándo vuelve a responder.'),
                                       ('03', 'Conectar', 'Enviamos la conexión a Steam.')]:
        column = ctk.CTkFrame(row, fg_color='transparent')
        column.pack(side='left', expand=True, fill='x')
        label(column, number + '  /  ' + title, 12, TEXT, True, anchor='w').pack(fill='x')
        label(column, description, 11, MUTED, wraplength=220, justify='left', anchor='w').pack(fill='x', pady=(6, 0))
