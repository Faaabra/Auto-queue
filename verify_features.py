with open('main.py', 'r', encoding='utf-8') as f:
    src = f.read()

checks = [
    ('#1  Editar alias servidor',    '_edit_server_alias' in src),
    ('#2  Delay persistido',         'settings["delay"]' in src),
    ('#3  IP pre-rellenada',         '_populate_active_ip' in src),
    ('#4  Boton Suspender PC',       'SetSuspendState' in src),
    ('#5  Validacion regex IP',      'IP_PORT_RE' in src),
    ('#6  Modo una sola noche',      'one_time_mode' in src),
    ('#7  Badge servidor activo',    'ACTIVO' in src),
    ('#8  Status doble linea',       'status_wake_label' in src),
    ('#9  Animacion boton activar',  '_flash_activate_button' in src),
    ('#10 Ventana resizable',        'resizable(False, True)' in src),
    ('#11 Tooltip contrasena',       'Tooltip(self.pw_entry' in src),
]

print("=" * 45)
print("  VERIFICACION DE MEJORAS EN main.py")
print("=" * 45)
for name, ok in checks:
    mark = "OK   " if ok else "FALTA"
    print(f"  [{mark}]  {name}")
print("=" * 45)
missing = sum(1 for _, ok in checks if not ok)
print(f"  {len(checks) - missing}/11 mejoras encontradas en el codigo.")
