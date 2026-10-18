import customtkinter as ctk
from .design import *


def build_servers(app):
    page = ctk.CTkFrame(app.container_frame, fg_color=BG, corner_radius=0)
    app.pages['servers'] = page
    page.grid_columnconfigure(0, weight=1)
    page.grid_rowconfigure(3, weight=1)
    header = page_heading(page, 'Tus servidores', 'Guarda tus destinos habituales. Encuentra tu próxima partida.',
                          row=0, column=0, sticky='ew', padx=28, pady=(26, 20))
    actions = ctk.CTkFrame(header, fg_color='transparent')
    actions.pack(fill='x', pady=(16, 0))
    button(actions, 'Explorar destacados  ↗', app.open_featured_servers_modal).pack(side='left')
    button(actions, '↻  Actualizar datos', lambda: app.refresh_server_list(page)).pack(side='right')
    form = card(page)
    form.grid(row=1, column=0, sticky='ew', padx=28, pady=(0, 16))
    form.grid_columnconfigure((0, 1), weight=1)
    label(form, 'AÑADIR UN SERVIDOR', 10, QUIET, True).grid(row=0, column=0, columnspan=3, sticky='w', padx=16, pady=(12, 8))
    app.new_alias_entry = ctk.CTkEntry(form, placeholder_text='Nombre · p. ej. Rustoria EU', height=40, font=font(12))
    app.new_alias_entry.grid(row=1, column=0, sticky='ew', padx=(16, 10), pady=(0, 14))
    app.new_ip_entry = ctk.CTkEntry(form, placeholder_text='IP o dominio:puerto', height=40, font=font(12))
    app.new_ip_entry.grid(row=1, column=1, sticky='ew', padx=(0, 10), pady=(0, 14))
    button(form, '+  Añadir', app.add_new_server_inline, primary=True, width=104).grid(row=1, column=2, padx=(0, 16), pady=(0, 14))
    search = ctk.CTkFrame(page, fg_color='transparent')
    search.grid(row=2, column=0, sticky='ew', padx=28, pady=(0, 12))
    app.server_search_var = ctk.StringVar()
    app.server_search = ctk.CTkEntry(search, textvariable=app.server_search_var,
        placeholder_text='Buscar por nombre o dirección · Ctrl+F', height=38, font=font(12))
    app.server_search.pack(side='left', fill='x', expand=True, padx=(0, 18))
    app.favorites_only_var = ctk.BooleanVar(value=False)
    ctk.CTkSwitch(search, text='Solo favoritos', variable=app.favorites_only_var, command=app._schedule_server_filter,
                   font=font(12), progress_color=ACCENT, width=140).pack(side='right')
    app.server_search_var.trace_add('write', app._schedule_server_filter)
    app.new_ip_entry.bind('<Return>', lambda event: app.add_new_server_inline())
    app.new_alias_entry.bind('<Return>', lambda event: app.new_ip_entry.focus_set())
    app.scroll_servers = ctk.CTkScrollableFrame(page, fg_color='transparent', corner_radius=0,
        scrollbar_button_color=LINE, scrollbar_button_hover_color=QUIET)
    app.scroll_servers.grid(row=3, column=0, sticky='nsew', padx=(20, 22), pady=0)
    footer = ctk.CTkFrame(page, fg_color='transparent')
    footer.grid(row=4, column=0, sticky='ew', padx=28, pady=(14, 20))
    for title, command in [('Importar lista', lambda: app._import_servers(page)), ('Exportar lista', app._export_servers)]:
        ctk.CTkButton(footer, text=title, command=command, width=110, height=30, fg_color='transparent',
            hover_color=RAISED, text_color=MUTED, font=font(12)).pack(side='left', padx=(0, 8))
    app.lbl_server_count = label(footer, '0 servidores', 11, QUIET)
    app.lbl_server_count.pack(side='right')
    app.refresh_server_list(page)
