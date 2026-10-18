"""One non-modal notification at a time, with restrained and optional motion."""
import time
import customtkinter as ctk
from .design import SURFACE, LINE, TEXT, MUTED, font


def show_toast(parent, message, toast_type='success', duration=3000):
    previous = getattr(parent, '_current_toast', None)
    if previous is not None and previous.winfo_exists():
        previous.destroy()
    colors = {'success': '#9dbb9d', 'info': '#a0bbbe', 'warning': '#d9bc7d', 'error': '#e49483'}
    toast = ctk.CTkFrame(parent, fg_color=SURFACE, border_color=LINE, border_width=1, corner_radius=10)
    parent._current_toast = toast
    ctk.CTkLabel(toast, text='●', text_color=colors.get(toast_type, MUTED), font=font(12)).pack(side='left', padx=(16, 10), pady=14)
    ctk.CTkLabel(toast, text=message, text_color=TEXT, font=font(12), wraplength=340, justify='left').pack(side='left', padx=(0, 8), pady=14)
    ctk.CTkButton(toast, text='×', width=26, height=26, fg_color='transparent', hover_color=LINE,
                   text_color=MUTED, font=font(17), command=toast.destroy).pack(side='right', padx=(0, 10))
    toast.lift()
    app = parent.winfo_toplevel()
    reduced = getattr(app, 'settings', {}).get('reduce_motion', False)
    start = time.monotonic()
    def enter():
        if not toast.winfo_exists():
            return
        progress = 1 if reduced else min(1, (time.monotonic() - start) / 0.14)
        toast.place(relx=1, rely=1, x=-24, y=-24 + round(10 * (1-progress)**3), anchor='se')
        if progress < 1:
            parent.after(16, enter)
    enter()
    def dismiss():
        if toast.winfo_exists():
            toast.destroy()
    parent.after(duration, dismiss)
