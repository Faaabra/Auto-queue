import re

with open('main.py', 'r', encoding='utf-8') as f:
    src = f.read()

src = re.sub(
    r'btn_sel = ctk\.CTkButton\(row, text="Usar", width=70, height=32, font=self\.font_label,\s*fg_color="#333335", hover_color="#444446", command=select_cmd\)', 
    r'btn_sel = ctk.CTkButton(row, text=" Usar", width=80, height=32, font=self.font_label, image=self.icon_play, fg_color="#333335", hover_color="#444446", command=select_cmd)', src)

src = re.sub(
    r'btn_copy = ctk\.CTkButton\(row, text="Copiar", width=60, height=32, font=self\.font_label,\s*fg_color="#2b2b2d", hover_color="#3b3b3f", border_width=1, border_color="#555",\s*command=copy_cmd\)',
    r'btn_copy = ctk.CTkButton(row, text="", width=40, height=32, image=self.icon_copy, fg_color="#2b2b2d", hover_color="#3b3b3f", border_width=1, border_color="#555", command=copy_cmd)', src)

src = re.sub(
    r'btn_edit = ctk\.CTkButton\(row, text="Editar", width=60, height=32, font=self\.font_label,\s*fg_color="#2b2b2d", hover_color="#3b3b3f", border_width=1, border_color="#555",\s*command=edit_cmd\)',
    r'btn_edit = ctk.CTkButton(row, text="", width=40, height=32, image=self.icon_edit, fg_color="#2b2b2d", hover_color="#3b3b3f", border_width=1, border_color="#555", command=edit_cmd)', src)

src = re.sub(
    r'btn_delete = ctk\.CTkButton\(row, text="Borrar", width=60, height=32, font=self\.font_label,\s*fg_color="transparent", hover_color="#3d1e1a", border_width=1, border_color=COLOR_RUST_RED, text_color=COLOR_RUST_RED,\s*command=delete_cmd\)',
    r'btn_delete = ctk.CTkButton(row, text="", width=40, height=32, image=self.icon_delete, fg_color="transparent", hover_color="#3d1e1a", border_width=1, border_color=COLOR_RUST_RED, text_color=COLOR_RUST_RED, command=delete_cmd)', src)

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(src)
print('Replaced buttons')
