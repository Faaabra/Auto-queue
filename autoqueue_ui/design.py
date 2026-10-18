"""Shared visual tokens and small, reusable presentation components."""
from pathlib import Path
import customtkinter as ctk

BG = '#111313'
SIDEBAR = '#171919'
SURFACE = '#1b1e1d'
RAISED = '#222624'
FIELD = '#151817'
LINE = '#303632'
TEXT = '#f1eee7'
MUTED = '#a6aea7'
QUIET = '#7e8981'
ACCENT = '#df7957'
ACCENT_HOVER = '#c96546'
ACCENT_SOFT = '#392a24'
GREEN = '#9dbb9d'


def install_theme():
    ctk.set_default_color_theme(str(Path(__file__).with_name('theme.json')))


def font(size=13, bold=False):
    return ctk.CTkFont(family='Segoe UI', size=size, weight='bold' if bold else 'normal')


def label(parent, text, size=13, color=TEXT, bold=False, **kwargs):
    return ctk.CTkLabel(parent, text=text, font=font(size, bold), text_color=color, **kwargs)


def card(parent, **kwargs):
    return ctk.CTkFrame(parent, fg_color=SURFACE, border_width=1, border_color=LINE, corner_radius=14, **kwargs)


def button(parent, text, command, primary=False, **kwargs):
    return ctk.CTkButton(parent, text=text, command=command, height=40, corner_radius=8,
        fg_color=ACCENT if primary else RAISED, hover_color=ACCENT_HOVER if primary else '#2d3430',
        text_color='#171a17' if primary else TEXT, font=font(13, primary), **kwargs)


def section(parent, number, title, subtitle=None):
    header = ctk.CTkFrame(parent, fg_color='transparent')
    header.pack(fill='x', padx=20, pady=(18, 14))
    label(header, number, 11, ACCENT, True, width=28, height=28, fg_color=ACCENT_SOFT, corner_radius=7).pack(side='left', padx=(0, 10))
    label(header, title, 16, bold=True).pack(side='left')
    if subtitle:
        label(parent, subtitle, 12, MUTED, anchor='w', justify='left').pack(fill='x', padx=20, pady=(0, 12))
    return header


def page_heading(parent, title, subtitle, **grid):
    header = ctk.CTkFrame(parent, fg_color='transparent')
    if grid:
        header.grid(**grid)
    else:
        header.pack(fill='x', padx=28, pady=(26, 20))
    label(header, title, 28, bold=True, anchor='w').pack(fill='x')
    label(header, subtitle, 13, MUTED, anchor='w').pack(fill='x', pady=(4, 0))
    return header
