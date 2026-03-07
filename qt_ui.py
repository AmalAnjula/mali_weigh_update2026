#!/usr/bin/env python3
"""
OLS Monitor — Tkinter UI for Raspberry Pi 5
Mirrors the HTML dashboard exactly.
Polls /api/data at 1 Hz · POSTs to /api/control
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json, urllib.request, threading, os
from datetime import datetime

# ── Configuration ──────────────────────────────────────────────────
API_BASE   = "http://localhost:5000"
POLL_MS    = 1000
ADMIN_PASS = "1234"

# ── Palette ────────────────────────────────────────────────────────
BG       = "#f0f2f5"
SURFACE  = "#ffffff"
BORDER   = "#d0d5dd"
TEXT     = "#1a1d23"
MUTED    = "#6b7280"
GREEN    = "#16a34a";  GREEN_BG  = "#dcfce7"
RED      = "#dc2626";  RED_BG    = "#fee2e2"
AMBER    = "#d97706";  AMBER_BG  = "#fef3c7"
BLUE     = "#2563eb";  BLUE_BG   = "#dbeafe"

STATE_COLORS = {
    "green": (GREEN_BG, GREEN,  GREEN),
    "red":   (RED_BG,   RED,    RED),
    "amber": (AMBER_BG, AMBER,  AMBER),
    "blue":  (BLUE_BG,  BLUE,   BLUE),
    "":      (SURFACE,  TEXT,   BORDER),
}

# ── HTTP helpers (run in threads) ──────────────────────────────────
def _api(method, path, body=None):
    url  = API_BASE + path
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Content-Type": "application/json"} if data else {}
    req  = urllib.request.Request(url, data=data, headers=hdrs, method=method)
    with urllib.request.urlopen(req, timeout=2) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}

api_get    = lambda p:    _api("GET",    p)
api_post   = lambda p, b: _api("POST",   p, b)
api_delete = lambda p:    _api("DELETE", p)


# ── Reusable widget: clickable state button ────────────────────────
class CtrlBtn(tk.Frame):
    """Card-style clickable button: shows a small LABEL and big VALUE."""
    def __init__(self, parent, label, value, command=None, **kw):
        super().__init__(parent, bg=SURFACE,
                         highlightbackground=BORDER, highlightthickness=2,
                         cursor="hand2", **kw)
        self.columnconfigure(0, weight=1)
        self._command  = command
        self._disabled = False

        self._lbl = tk.Label(self, text=label.upper(), bg=SURFACE, fg=MUTED,
                             font=("Segoe UI", 8), cursor="hand2")
        self._lbl.grid(row=0, column=0, sticky="w", padx=10, pady=(8, 0))

        self._val = tk.Label(self, text=value, bg=SURFACE, fg=TEXT,
                             font=("Segoe UI", 17, "bold"), cursor="hand2")
        self._val.grid(row=1, column=0, sticky="w", padx=10, pady=(0, 8))

        for w in (self, self._lbl, self._val):
            w.bind("<Button-1>", self._on_click)
        self.bind("<Enter>", lambda e: self._hover(True))
        self.bind("<Leave>", lambda e: self._hover(False))

    def _on_click(self, _=None):
        if not self._disabled and self._command:
            self._command()

    def _hover(self, on):
        if not self._disabled:
            self.configure(highlightbackground=BLUE if on else self._bdr)

    def set_command(self, cmd):  self._command = cmd

    def set_value(self, text):   self._val.configure(text=text)

    def set_state(self, color, disabled=False):
        bg, fg, bdr = STATE_COLORS.get(color, STATE_COLORS[""])
        self._bdr = bdr
        self._disabled = disabled
        self.configure(bg=bg, highlightbackground=bdr,
                       cursor="arrow" if disabled else "hand2")
        self._lbl.configure(bg=bg)
        self._val.configure(bg=bg, fg=fg)


# ── Reusable: labelled entry row (for settings) ────────────────────
class SettingRow(tk.Frame):
    def __init__(self, parent, label, **kw):
        super().__init__(parent, bg=SURFACE, **kw)
        self.columnconfigure(0, weight=1)
        tk.Label(self, text=label, bg=SURFACE, fg=MUTED,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self.var = tk.StringVar()
        self.entry = tk.Entry(self, textvariable=self.var, bg=BG, fg=TEXT,
                              font=("Segoe UI", 11), relief="flat",
                              highlightbackground=BORDER, highlightthickness=1,
                              state="disabled")
        self.entry.grid(row=1, column=0, sticky="ew", ipady=4, pady=(1, 0))

    def enable(self):  self.entry.configure(state="normal")
    def disable(self): self.entry.configure(state="disabled")
    def get(self):     return self.var.get()
    def set(self, v):  self.var.set(v)


# ══════════════════════════════════════════════════════════════════
# MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════
class OLSApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OLS — Monitor")
        self.configure(bg=BG)
        self.geometry("1150x730")
        self.minsize(900, 600)

        self._data            = None
        self._admin           = False
        self._settings_synced = False
        self._toast_job       = None

        self._build_ui()
        self._tick_clock()
        self._schedule_poll()

    # ══ UI BUILD ══════════════════════════════════════════════════
    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self._build_header()
        self._build_notebook()
        self._build_statusbar()
        self._build_toast()

    # ── Header ────────────────────────────────────────────────────
    def _build_header(self):
        hdr = tk.Frame(self, bg=SURFACE,
                       highlightbackground=BORDER, highlightthickness=1)
        hdr.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 6))
        hdr.columnconfigure(1, weight=1)

        lf = tk.Frame(hdr, bg=SURFACE)
        lf.grid(row=0, column=0, sticky="w", padx=16, pady=10)
        tk.Label(lf, text="OLS — Monitor", bg=SURFACE, fg=TEXT,
                 font=("Segoe UI", 14, "bold")).pack(anchor="w")
        tk.Label(lf, text="Oil Level System", bg=SURFACE, fg=MUTED,
                 font=("Segoe UI", 9)).pack(anchor="w")

        rf = tk.Frame(hdr, bg=SURFACE)
        rf.grid(row=0, column=2, sticky="e", padx=16, pady=10)

        self._clock_lbl = tk.Label(rf, text="--:--:--", bg=SURFACE, fg=TEXT,
                                   font=("Segoe UI", 13, "bold"))
        self._clock_lbl.pack(side="left", padx=(0, 14))

        self._badge = tk.Frame(rf, bg=GREEN_BG,
                               highlightbackground=GREEN, highlightthickness=1)
        self._badge.pack(side="left")
        self._badge_dot = tk.Canvas(self._badge, width=10, height=10,
                                    bg=GREEN_BG, highlightthickness=0)
        self._badge_dot.pack(side="left", padx=(8, 3), pady=5)
        self._badge_dot_id = self._badge_dot.create_oval(1, 1, 9, 9,
                                                         fill=GREEN, outline="")
        self._badge_lbl = tk.Label(self._badge, text="ONLINE",
                                   bg=GREEN_BG, fg=GREEN,
                                   font=("Segoe UI", 10, "bold"))
        self._badge_lbl.pack(side="left", padx=(0, 10), pady=5)

    # ── Notebook ──────────────────────────────────────────────────
    def _build_notebook(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("OLS.TNotebook",     background=BG, borderwidth=0)
        style.configure("OLS.TNotebook.Tab", background=SURFACE, foreground=MUTED,
                        font=("Segoe UI", 10), padding=[16, 7])
        style.map("OLS.TNotebook.Tab",
                  background=[("selected", BLUE)],
                  foreground=[("selected", "white")])

        nb = ttk.Notebook(self, style="OLS.TNotebook")
        nb.grid(row=1, column=0, sticky="nsew", padx=12)

        self._frm_monitor  = tk.Frame(nb, bg=BG)
        self._frm_settings = tk.Frame(nb, bg=BG)
        self._frm_log      = tk.Frame(nb, bg=BG)

        nb.add(self._frm_monitor,  text="  Monitor  ")
        nb.add(self._frm_settings, text="  Settings  ")
        nb.add(self._frm_log,      text="  Log  ")

        self._build_monitor_tab()
        self._build_settings_tab()
        self._build_log_tab()

    # ══ MONITOR TAB ═══════════════════════════════════════════════
    def _build_monitor_tab(self):
        f = self._frm_monitor
        f.columnconfigure(0, weight=1)
        f.columnconfigure(1, weight=0)
        f.columnconfigure(2, weight=1)
        f.rowconfigure(0, weight=1)

        self._build_infeed_panel(f, col=0)
        self._build_tank_column(f, col=1)
        self._build_outfeed_panel(f, col=2)

    # ── Infeed Panel ──────────────────────────────────────────────
    def _build_infeed_panel(self, parent, col):
        card = tk.Frame(parent, bg=SURFACE,
                        highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=col, sticky="nsew", padx=(10, 4), pady=10)
        card.columnconfigure(0, weight=1)

        # Card header
        hdr = tk.Frame(card, bg=SURFACE,
                       highlightbackground=BORDER, highlightthickness=1)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="◀  INFEED", bg=SURFACE, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=6)

        body = tk.Frame(card, bg=SURFACE)
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        body.columnconfigure(0, weight=1)

        # Control buttons
        self._in_mode_btn = CtrlBtn(body, "Control Mode", "AUTO",
                                    command=lambda: self._ctrl("infeed", "mode"))
        self._in_mode_btn.grid(row=0, column=0, sticky="ew", pady=3)

        self._in_op_btn = CtrlBtn(body, "Operation", "LOCAL",
                                  command=lambda: self._ctrl("infeed", "operation"))
        self._in_op_btn.grid(row=1, column=0, sticky="ew", pady=3)

        self._in_run_btn = CtrlBtn(body, "Run State", "STOP",
                                   command=lambda: self._ctrl("infeed", "run"))
        self._in_run_btn.grid(row=2, column=0, sticky="ew", pady=3)

        # Volume input
        vol_f = tk.Frame(body, bg=SURFACE)
        vol_f.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        vol_f.columnconfigure(0, weight=1)
        tk.Label(vol_f, text="INFEED VOLUME (L)", bg=SURFACE, fg=MUTED,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self._in_vol = tk.StringVar(value="25.00")
        tk.Entry(vol_f, textvariable=self._in_vol, bg=BG, fg=TEXT,
                 font=("Segoe UI", 14, "bold"), justify="center", relief="flat",
                 highlightbackground=BORDER, highlightthickness=2
                 ).grid(row=1, column=0, sticky="ew", ipady=5, pady=2)
        tk.Button(vol_f, text="Apply Infeed", bg=BLUE, fg="white",
                  font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2",
                  command=lambda: self._apply_vol("infeed", self._in_vol)
                  ).grid(row=2, column=0, sticky="ew", ipady=6)

        # Weight tile
        self._wt_tile = tk.Frame(body, bg=SURFACE,
                                 highlightbackground=BORDER, highlightthickness=2)
        self._wt_tile.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        self._wt_tile.columnconfigure(0, weight=1)
        tk.Label(self._wt_tile, text="TANK WEIGHT", bg=SURFACE, fg=MUTED,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w", padx=10, pady=(8,0))
        self._wt_val = tk.Label(self._wt_tile, text="---", bg=SURFACE, fg=TEXT,
                                font=("Segoe UI", 28, "bold"))
        self._wt_val.grid(row=1, column=0, sticky="w", padx=10)
        self._wt_unit = tk.Label(self._wt_tile, text="KG", bg=SURFACE, fg=MUTED,
                                 font=("Segoe UI", 9))
        self._wt_unit.grid(row=2, column=0, sticky="w", padx=10, pady=(0, 8))

    # ── Outfeed Panel ─────────────────────────────────────────────
    def _build_outfeed_panel(self, parent, col):
        card = tk.Frame(parent, bg=SURFACE,
                        highlightbackground=BORDER, highlightthickness=1)
        card.grid(row=0, column=col, sticky="nsew", padx=(4, 10), pady=10)
        card.columnconfigure(0, weight=1)

        hdr = tk.Frame(card, bg=SURFACE,
                       highlightbackground=BORDER, highlightthickness=1)
        hdr.grid(row=0, column=0, sticky="ew")
        tk.Label(hdr, text="OUTFEED  ▶", bg=SURFACE, fg=MUTED,
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=10, pady=6)

        body = tk.Frame(card, bg=SURFACE)
        body.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        body.columnconfigure(0, weight=1)

        self._out_mode_btn = CtrlBtn(body, "Control Mode", "AUTO",
                                     command=lambda: self._ctrl("outfeed", "mode"))
        self._out_mode_btn.grid(row=0, column=0, sticky="ew", pady=3)

        self._out_op_btn = CtrlBtn(body, "Operation", "LOCAL",
                                   command=lambda: self._ctrl("outfeed", "operation"))
        self._out_op_btn.grid(row=1, column=0, sticky="ew", pady=3)

        self._out_run_btn = CtrlBtn(body, "Run State", "STOP",
                                    command=lambda: self._ctrl("outfeed", "run"))
        self._out_run_btn.grid(row=2, column=0, sticky="ew", pady=3)

        vol_f = tk.Frame(body, bg=SURFACE)
        vol_f.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        vol_f.columnconfigure(0, weight=1)
        tk.Label(vol_f, text="OUTFEED VOLUME (L)", bg=SURFACE, fg=MUTED,
                 font=("Segoe UI", 8)).grid(row=0, column=0, sticky="w")
        self._out_vol = tk.StringVar(value="0.00")
        tk.Entry(vol_f, textvariable=self._out_vol, bg=BG, fg=TEXT,
                 font=("Segoe UI", 14, "bold"), justify="center", relief="flat",
                 highlightbackground=BORDER, highlightthickness=2
                 ).grid(row=1, column=0, sticky="ew", ipady=5, pady=2)
        tk.Button(vol_f, text="Apply Outfeed", bg=BLUE, fg="white",
                  font=("Segoe UI", 11, "bold"), relief="flat", cursor="hand2",
                  command=lambda: self._apply_vol("outfeed", self._out_vol)
                  ).grid(row=2, column=0, sticky="ew", ipady=6)

        # Level info tile
        info = tk.Frame(body, bg=SURFACE,
                        highlightbackground=BORDER, highlightthickness=1)
        info.grid(row=4, column=0, sticky="ew", pady=(10, 0))
        info.columnconfigure(0, weight=1)

        bar_row = tk.Frame(info, bg=SURFACE)
        bar_row.grid(row=0, column=0, sticky="ew", padx=10, pady=(10, 4))
        bar_row.columnconfigure(0, weight=1)
        tk.Label(bar_row, text="LEVEL", bg=SURFACE, fg=MUTED,
                 font=("Segoe UI", 8)).pack(side="left")
        self._lvl_pct_lbl = tk.Label(bar_row, text="--%", bg=SURFACE, fg=BLUE,
                                     font=("Segoe UI", 13, "bold"))
        self._lvl_pct_lbl.pack(side="right")

        # Progress bar via Canvas
        bar_bg = tk.Canvas(info, height=14, bg="#e5e7eb",
                           highlightbackground=BORDER, highlightthickness=1)
        bar_bg.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 6))
        self._lvl_bar_canvas = bar_bg
        self._lvl_bar_rect   = bar_bg.create_rectangle(0, 0, 0, 14, fill=BLUE, outline="")
        bar_bg.bind("<Configure>", self._on_bar_resize)

        tk.Frame(info, bg=BORDER, height=1).grid(row=2, column=0, sticky="ew", padx=10)
        self._prod_tag = tk.Label(info, text="--", bg=SURFACE, fg=MUTED,
                                  font=("Segoe UI", 9, "bold"))
        self._prod_tag.grid(row=3, column=0, pady=(4, 8))

        self._lvl_pct_cache = 35

    def _on_bar_resize(self, e):
        self._redraw_bar(self._lvl_pct_cache)

    def _redraw_bar(self, pct):
        self._lvl_pct_cache = pct
        c = self._lvl_bar_canvas
        w = c.winfo_width()
        fill_w = int(w * pct / 100)
        c.coords(self._lvl_bar_rect, 0, 0, fill_w, 14)

    # ── Tank column ───────────────────────────────────────────────
    TANK_W = 200
    TANK_H = 300

    def _build_tank_column(self, parent, col):
        wrap = tk.Frame(parent, bg=BG)
        wrap.grid(row=0, column=col, pady=10, padx=4, sticky="ns")

        r = 0
        # HI sensor
        hi_row = tk.Frame(wrap, bg=BG)
        hi_row.grid(row=r, column=0, pady=(2, 2)); r += 1
        self._hi_dot_c = tk.Canvas(hi_row, width=13, height=13,
                                   bg=BG, highlightthickness=0)
        self._hi_dot_c.pack(side="left")
        self._hi_dot_o = self._hi_dot_c.create_oval(1, 1, 11, 11,
                                                     fill=BORDER, outline=BORDER)
        self._hi_lbl = tk.Label(hi_row, text="HI LEVEL", bg=BG, fg=MUTED,
                                font=("Segoe UI", 8, "bold"))
        self._hi_lbl.pack(side="left", padx=4)

        # Infeed valve row
        in_v = tk.Frame(wrap, bg=BG)
        in_v.grid(row=r, column=0, sticky="ew", pady=2); r += 1
        in_v.columnconfigure(0, weight=1)
        in_v.columnconfigure(2, weight=1)
        tk.Frame(in_v, bg="#e5e7eb", height=8,
                 highlightbackground=BORDER, highlightthickness=1
                 ).grid(row=0, column=0, sticky="ew")
        self._in_valve_c  = self._make_valve(in_v, col=1)
        self._in_valve_c.bind("<Button-1>", lambda e: self._ctrl_valve("infeed"))
        tk.Frame(in_v, bg="#e5e7eb", height=8,
                 highlightbackground=BORDER, highlightthickness=1
                 ).grid(row=0, column=2, sticky="ew")

        # Top port stub
        pt = tk.Canvas(wrap, width=24, height=16, bg=BG, highlightthickness=0)
        pt.grid(row=r, column=0); r += 1
        pt.create_rectangle(2, 0, 22, 16, fill="#e5e7eb", outline=BORDER)
        self._port_top_c = pt

        # Tank canvas
        tc = tk.Canvas(wrap, width=self.TANK_W, height=self.TANK_H,
                       bg=BG, highlightthickness=0)
        tc.grid(row=r, column=0); r += 1
        self._tank_canvas = tc
        self._draw_tank()

        # Bottom port stub
        pb = tk.Canvas(wrap, width=24, height=16, bg=BG, highlightthickness=0)
        pb.grid(row=r, column=0); r += 1
        pb.create_rectangle(2, 0, 22, 16, fill="#e5e7eb", outline=BORDER)
        self._port_bot_c = pb

        # Outfeed valve row
        out_v = tk.Frame(wrap, bg=BG)
        out_v.grid(row=r, column=0, sticky="ew", pady=2); r += 1
        out_v.columnconfigure(0, weight=1)
        out_v.columnconfigure(2, weight=1)
        tk.Frame(out_v, bg="#e5e7eb", height=8,
                 highlightbackground=BORDER, highlightthickness=1
                 ).grid(row=0, column=0, sticky="ew")
        self._out_valve_c = self._make_valve(out_v, col=1)
        self._out_valve_c.bind("<Button-1>", lambda e: self._ctrl_valve("outfeed"))
        tk.Frame(out_v, bg="#e5e7eb", height=8,
                 highlightbackground=BORDER, highlightthickness=1
                 ).grid(row=0, column=2, sticky="ew")

        # LO sensor
        lo_row = tk.Frame(wrap, bg=BG)
        lo_row.grid(row=r, column=0, pady=(2, 2)); r += 1
        self._lo_dot_c = tk.Canvas(lo_row, width=13, height=13,
                                   bg=BG, highlightthickness=0)
        self._lo_dot_c.pack(side="left")
        self._lo_dot_o = self._lo_dot_c.create_oval(1, 1, 11, 11,
                                                     fill=BORDER, outline=BORDER)
        self._lo_lbl = tk.Label(lo_row, text="LO LEVEL", bg=BG, fg=MUTED,
                                font=("Segoe UI", 8, "bold"))
        self._lo_lbl.pack(side="left", padx=4)

    def _make_valve(self, parent, col):
        """Draw a valve gate icon on a Canvas and return it."""
        c = tk.Canvas(parent, width=38, height=38, bg=BG,
                      highlightthickness=0, cursor="hand2")
        c.grid(row=0, column=col)
        c.create_rectangle(2, 2, 36, 36, fill=SURFACE, outline=BORDER,
                            width=2, tags="rect")
        # Down-arrow (valve open indicator)
        c.create_line(19, 8,  19, 26, fill=MUTED, width=2, tags="arrow")
        c.create_line(12, 20, 19, 28, fill=MUTED, width=2, tags="arrow")
        c.create_line(26, 20, 19, 28, fill=MUTED, width=2, tags="arrow")
        return c

    def _draw_tank(self):
        c  = self._tank_canvas
        W, H = self.TANK_W, self.TANK_H

        # Shell
        c.create_rectangle(2, 2, W-2, H-2, fill="#f8fafc",
                            outline=BORDER, width=2, tags="shell")

        # Oil fill (updated dynamically)
        self._oil_id = c.create_rectangle(3, H-3, W-3, H-3,
                                          fill="#d97706", outline="", tags="oil")

        # HI / LO threshold lines (positions updated on render)
        self._hi_line_id = c.create_line(3, 0, W-22, 0, fill=RED,   width=2, tags="thresh")
        self._hi_tag_id  = c.create_text(W-4, 0, text="HI", fill=RED,
                                         anchor="e", font=("Segoe UI", 7, "bold"))
        self._lo_line_id = c.create_line(3, 0, W-22, 0, fill=AMBER, width=2, tags="thresh")
        self._lo_tag_id  = c.create_text(W-4, 0, text="LO", fill=AMBER,
                                         anchor="e", font=("Segoe UI", 7, "bold"))

        # Scale
        for frac, label in ((1.0,"100%"),(0.75,"75%"),(0.5,"50%"),(0.25,"25%"),(0.0,"0%")):
            y = max(int(H * (1-frac)), 6)
            c.create_text(W-5, y, text=label, fill="#9ca3af",
                          anchor="e", font=("Segoe UI", 6))

    def _update_tank(self, level_pct, hi_alarm, lo_alarm, hi_thr, lo_thr):
        c  = self._tank_canvas
        W, H = self.TANK_W, self.TANK_H

        # Oil fill
        fill_h = max(0, int(H * level_pct / 100))
        y_top  = H - fill_h - 3
        oil_color = RED if hi_alarm else (AMBER if lo_alarm else "#d97706")
        c.coords(self._oil_id, 3, max(3, y_top), W-3, H-3)
        c.itemconfig(self._oil_id, fill=oil_color)

        # Threshold lines
        hi_y = int(H * (1 - hi_thr / 100))
        lo_y = int(H * (1 - lo_thr / 100))
        c.coords(self._hi_line_id, 3, hi_y, W-22, hi_y)
        c.coords(self._hi_tag_id,  W-4, hi_y)
        c.coords(self._lo_line_id, 3, lo_y, W-22, lo_y)
        c.coords(self._lo_tag_id,  W-4, lo_y)

    # ── Valve rendering ───────────────────────────────────────────
    def _render_valve(self, side, is_open):
        c = self._in_valve_c if side == "in" else self._out_valve_c
        if is_open:
            c.itemconfig("rect",  fill=GREEN_BG, outline=GREEN)
            c.itemconfig("arrow", fill=GREEN)
        else:
            c.itemconfig("rect",  fill=SURFACE,  outline=BORDER)
            c.itemconfig("arrow", fill=MUTED)

    # ── Port stub flowing indicator ───────────────────────────────
    def _render_port(self, canvas, flowing):
        canvas.delete("flow_dot")
        if flowing:
            canvas.create_oval(9, 3, 15, 9, fill=GREEN, outline="", tags="flow_dot")

    # ══ SETTINGS TAB ══════════════════════════════════════════════
    def _build_settings_tab(self):
        f = self._frm_settings
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        # Scrollable inner area
        canvas = tk.Canvas(f, bg=BG, highlightthickness=0)
        vsb    = ttk.Scrollbar(f, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = tk.Frame(canvas, bg=BG)
        wid   = canvas.create_window((0, 0), window=inner, anchor="nw")

        canvas.bind("<Configure>", lambda e: canvas.itemconfig(wid, width=e.width))
        inner.bind("<Configure>",  lambda e: canvas.configure(
                   scrollregion=canvas.bbox("all")))

        inner.columnconfigure(0, weight=1)

        # ── Admin gate ──
        self._admin_gate_frm = tk.Frame(inner, bg=SURFACE,
                                        highlightbackground=BORDER,
                                        highlightthickness=1)
        self._admin_gate_frm.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 8))
        self._admin_gate_frm.columnconfigure(0, weight=1)
        tk.Label(self._admin_gate_frm, text="🔒  Admin Login Required",
                 bg=SURFACE, fg=TEXT, font=("Segoe UI", 11, "bold")
                 ).grid(row=0, column=0, pady=(14, 8))
        pw_row = tk.Frame(self._admin_gate_frm, bg=SURFACE)
        pw_row.grid(row=1, column=0, pady=(0, 4))
        self._pass_entry = tk.Entry(pw_row, show="*", font=("Segoe UI", 14),
                                    width=14, justify="center", relief="flat",
                                    highlightbackground=BORDER, highlightthickness=2)
        self._pass_entry.pack(side="left", ipady=5, padx=(0, 6))
        self._pass_entry.bind("<Return>", lambda e: self._check_pass())
        tk.Button(pw_row, text="Unlock", bg=BLUE, fg="white",
                  font=("Segoe UI", 11, "bold"), relief="flat",
                  command=self._check_pass, cursor="hand2",
                  padx=12, pady=5).pack(side="left")
        self._admin_err_lbl = tk.Label(self._admin_gate_frm, text="",
                                       bg=SURFACE, fg=RED, font=("Segoe UI", 9))
        self._admin_err_lbl.grid(row=2, column=0, pady=(0, 12))

        # ── Admin open bar (hidden initially) ──
        self._admin_open_frm = tk.Frame(inner, bg=GREEN_BG,
                                        highlightbackground=GREEN,
                                        highlightthickness=1)
        # Will be grid()'d on unlock
        tk.Label(self._admin_open_frm, text="🔓  Admin Mode Active",
                 bg=GREEN_BG, fg=GREEN, font=("Segoe UI", 10, "bold")
                 ).pack(side="left", padx=14, pady=8)
        tk.Button(self._admin_open_frm, text="Lock", bg=RED_BG, fg=RED,
                  font=("Segoe UI", 9, "bold"), relief="flat",
                  highlightbackground=RED, highlightthickness=1,
                  command=self._lock_admin, cursor="hand2", padx=10
                  ).pack(side="right", padx=14)

        # ── Settings grid ──
        self._setting_rows: dict[str, SettingRow] = {}
        sg = tk.Frame(inner, bg=BG)
        sg.grid(row=2, column=0, sticky="ew", padx=16, pady=6)
        sg.columnconfigure(0, weight=1)
        sg.columnconfigure(1, weight=1)

        def card(parent, title, fields, r, c, save=False):
            frm = tk.Frame(parent, bg=SURFACE,
                           highlightbackground=BORDER, highlightthickness=1)
            frm.grid(row=r, column=c, sticky="nsew", padx=6, pady=6)
            frm.columnconfigure(0, weight=1)
            tk.Label(frm, text=title.upper(), bg=SURFACE, fg=MUTED,
                     font=("Segoe UI", 8, "bold")
                     ).grid(row=0, column=0, sticky="w", padx=12, pady=(12, 6))
            tk.Frame(frm, bg=BORDER, height=1
                     ).grid(row=1, column=0, sticky="ew", padx=12)
            for i, (lbl, sid) in enumerate(fields):
                sr = SettingRow(frm, lbl)
                sr.grid(row=i+2, column=0, sticky="ew", padx=12, pady=4)
                self._setting_rows[sid] = sr
            if save:
                self._save_btn = tk.Button(frm, text="Save Settings",
                                           bg=BLUE, fg="white",
                                           font=("Segoe UI", 10, "bold"),
                                           relief="flat", cursor="hand2",
                                           state="disabled",
                                           command=self._save_settings)
                self._save_btn.grid(row=len(fields)+2, column=0, sticky="ew",
                                    padx=12, pady=(8, 12), ipady=6)

        card(sg, "Product Info", [
            ("Product Code", "s-code"),
            ("Product Name", "s-name"),
        ], r=0, c=0)

        card(sg, "Tank Parameters", [
            ("Max Capacity (kg)",   "s-maxkg"),
            ("Oil Density (kg/L)",  "s-density"),
            ("Tare Weight (kg)",    "s-tare"),
        ], r=0, c=1)

        card(sg, "Alarm Thresholds", [
            ("Hi Level (%)", "s-hi"),
            ("Lo Level (%)", "s-lo"),
        ], r=1, c=0)

        card(sg, "Infeed Settings", [
            ("Default Volume (L)", "s-inf-def"),
            ("Max Volume (L)",     "s-inf-max"),
        ], r=1, c=1, save=True)

    # ══ LOG TAB ═══════════════════════════════════════════════════
    def _build_log_tab(self):
        f = self._frm_log
        f.columnconfigure(0, weight=1)
        f.rowconfigure(1, weight=1)

        tb = tk.Frame(f, bg=BG)
        tb.grid(row=0, column=0, sticky="ew", padx=12, pady=(10, 6))

        def ltb(text, cmd, danger=False):
            tk.Button(tb, text=text, bg=SURFACE,
                      fg=RED if danger else MUTED,
                      font=("Segoe UI", 10), relief="flat",
                      highlightbackground=BORDER, highlightthickness=1,
                      command=cmd, cursor="hand2", padx=12, pady=4
                      ).pack(side="left", padx=(0, 6))

        ltb("↓ Export JSON", self._export_json)
        ltb("✕ Clear Log",   self._clear_log, danger=True)
        self._log_ct = tk.Label(tb, text="0 events", bg=BG, fg=MUTED,
                                font=("Segoe UI", 9))
        self._log_ct.pack(side="right")

        style = ttk.Style()
        style.configure("Log.Treeview", background=SURFACE,
                        fieldbackground=SURFACE, rowheight=28,
                        font=("Segoe UI", 9))
        style.configure("Log.Treeview.Heading", background=BG,
                        foreground=MUTED, font=("Segoe UI", 8, "bold"))

        cols = ("Timestamp", "Event", "Infeed (L)", "Outfeed (L)",
                "Weight (kg)", "Level (%)")
        tree_wrap = tk.Frame(f, bg=SURFACE,
                             highlightbackground=BORDER, highlightthickness=1)
        tree_wrap.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 10))
        tree_wrap.columnconfigure(0, weight=1)
        tree_wrap.rowconfigure(0, weight=1)

        self._log_tree = ttk.Treeview(tree_wrap, columns=cols,
                                      show="headings", style="Log.Treeview")
        widths = [145, 210, 90, 90, 95, 80]
        for c, w in zip(cols, widths):
            self._log_tree.heading(c, text=c)
            self._log_tree.column(c, width=w, anchor="w")
        self._log_tree.tag_configure("alarm", foreground=RED)

        vsb = ttk.Scrollbar(tree_wrap, orient="vertical",
                            command=self._log_tree.yview)
        self._log_tree.configure(yscrollcommand=vsb.set)
        self._log_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

    # ── Status bar ────────────────────────────────────────────────
    def _build_statusbar(self):
        bar = tk.Frame(self, bg=SURFACE,
                       highlightbackground=BORDER, highlightthickness=1)
        bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(2, 10))

        def item(txt):
            f = tk.Frame(bar, bg=SURFACE)
            f.pack(side="left", padx=18, pady=6)
            return f

        def make_sb(label):
            f = item(label)
            tk.Label(f, text=label + ":", bg=SURFACE, fg=MUTED,
                     font=("Segoe UI", 9)).pack(side="left")
            lbl = tk.Label(f, text="--", bg=SURFACE, fg=TEXT,
                           font=("Segoe UI", 9, "bold"))
            lbl.pack(side="left", padx=(4, 0))
            return lbl

        self._sb_unit   = make_sb("Unit")
        self._sb_cap    = make_sb("Capacity")
        self._sb_status = make_sb("Status")
        self._sb_ts     = make_sb("Last update")

    # ── Toast ─────────────────────────────────────────────────────
    def _build_toast(self):
        self._toast_lbl = tk.Label(self, font=("Segoe UI", 11, "bold"),
                                   relief="flat", padx=18, pady=8)

    def _show_toast(self, msg, kind="ok"):
        bg, fg = (GREEN_BG, GREEN) if kind == "ok" else (RED_BG, RED)
        self._toast_lbl.configure(text=msg, bg=bg, fg=fg)
        self._toast_lbl.place(relx=1.0, rely=1.0, anchor="se", x=-24, y=-24)
        if self._toast_job:
            self.after_cancel(self._toast_job)
        self._toast_job = self.after(3000, self._toast_lbl.place_forget)

    # ══ CLOCK ═════════════════════════════════════════════════════
    def _tick_clock(self):
        self._clock_lbl.configure(text=datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self._tick_clock)

    # ══ POLLING ═══════════════════════════════════════════════════
    def _schedule_poll(self):
        threading.Thread(target=self._fetch, daemon=True).start()
        self.after(POLL_MS, self._schedule_poll)

    def _fetch(self):
        try:
            d = api_get("/api/data")
            self.after(0, lambda: self._render(d))
            self.after(0, lambda: self._set_conn(True))
        except Exception:
            self.after(0, lambda: self._set_conn(False))

    def _set_conn(self, ok):
        bg = GREEN_BG if ok else RED_BG
        fg = GREEN    if ok else RED
        self._badge.configure(bg=bg, highlightbackground=fg)
        self._badge_dot.configure(bg=bg)
        self._badge_dot.itemconfig(self._badge_dot_id, fill=fg, outline="")
        self._badge_lbl.configure(bg=bg, fg=fg,
                                  text="ONLINE" if ok else "OFFLINE")

    # ══ RENDER ════════════════════════════════════════════════════
    def _render(self, d):
        self._data = d
        tk_d  = d.get("tank",    {})
        ifd   = d.get("infeed",  {})
        ofd   = d.get("outfeed", {})
        hi_alarm = tk_d.get("hi_alarm", False)
        lo_alarm = tk_d.get("lo_alarm", False)
        pct      = tk_d.get("level_pct", 0)

        # ── Weight tile ──
        net = max(0, tk_d.get("weight_kg", 0) - tk_d.get("tare_kg", 0))
        self._wt_val.configure(text=f"{net:.2f}")
        if hi_alarm:
            self._wt_tile.configure(bg=RED_BG, highlightbackground=RED)
            for w in (self._wt_val, self._wt_unit):
                w.configure(bg=RED_BG)
            self._wt_val.configure(fg=RED)
        elif lo_alarm:
            self._wt_tile.configure(bg=AMBER_BG, highlightbackground=AMBER)
            for w in (self._wt_val, self._wt_unit):
                w.configure(bg=AMBER_BG)
            self._wt_val.configure(fg=AMBER)
        else:
            self._wt_tile.configure(bg=SURFACE, highlightbackground=BORDER)
            for w in (self._wt_val, self._wt_unit):
                w.configure(bg=SURFACE)
            self._wt_val.configure(fg=TEXT)

        # ── Level bar ──
        bar_color = RED if hi_alarm else (AMBER if lo_alarm else BLUE)
        self._lvl_pct_lbl.configure(text=f"{pct:.1f}%", fg=bar_color)
        self._lvl_bar_canvas.itemconfig(self._lvl_bar_rect, fill=bar_color)
        self._redraw_bar(pct)

        # ── Product ──
        self._prod_tag.configure(text=d.get("product") or "--")

        # ── Tank ──
        self._update_tank(pct, hi_alarm, lo_alarm,
                          tk_d.get("hi_threshold_pct", 80),
                          tk_d.get("lo_threshold_pct", 20))

        # ── Sensors ──
        if hi_alarm:
            self._hi_dot_c.itemconfig(self._hi_dot_o, fill=RED, outline=RED)
            self._hi_lbl.configure(fg=RED)
        else:
            self._hi_dot_c.itemconfig(self._hi_dot_o, fill=BORDER, outline=BORDER)
            self._hi_lbl.configure(fg=MUTED)

        if lo_alarm:
            self._lo_dot_c.itemconfig(self._lo_dot_o, fill=AMBER, outline=AMBER)
            self._lo_lbl.configure(fg=AMBER)
        else:
            self._lo_dot_c.itemconfig(self._lo_dot_o, fill=BORDER, outline=BORDER)
            self._lo_lbl.configure(fg=MUTED)

        # ── Valves ──
        flow_in  = ifd.get("valve_open") and ifd.get("running")
        flow_out = ofd.get("valve_open") and ofd.get("running")
        self._render_valve("in",  flow_in)
        self._render_valve("out", flow_out)
        self._render_port(self._port_top_c, flow_in)
        self._render_port(self._port_bot_c, flow_out)

        # ── Control panels ──
        self._render_panel("in",  ifd)
        self._render_panel("out", ofd)

        # ── Status bar ──
        self._sb_unit.configure(text="KG")
        self._sb_cap.configure(text=f"{tk_d.get('max_kg', '--')} kg")
        status = "HI ALARM" if hi_alarm else ("LO ALARM" if lo_alarm else "OK")
        self._sb_status.configure(
            text=status,
            fg=RED if "ALARM" in status else GREEN)
        ts = (d.get("timestamp") or "--").replace("T", " ")[:19]
        self._sb_ts.configure(text=ts)

        # ── Log ──
        self._render_log(d.get("log", []))

        # ── Settings sync (once) ──
        if not self._settings_synced:
            self._sync_settings(d)
            self._settings_synced = True

    def _render_panel(self, side, s):
        remote  = s.get("operation") == "REMOTE"
        running = s.get("running", False)

        if side == "in":
            mode_b, op_b, run_b = self._in_mode_btn, self._in_op_btn, self._in_run_btn
        else:
            mode_b, op_b, run_b = self._out_mode_btn, self._out_op_btn, self._out_run_btn

        mode_b.set_state("green" if s.get("mode") == "AUTO" else "blue",
                         disabled=remote)
        mode_b.set_value(s.get("mode", "AUTO"))

        op_b.set_state("amber" if remote else "")
        op_b.set_value(s.get("operation", "LOCAL"))

        run_b.set_state("green" if running else "red", disabled=remote)
        run_b.set_value("STOP" if running else "START")

    def _render_log(self, rows):
        self._log_ct.configure(text=f"{len(rows)} events")
        for item in self._log_tree.get_children():
            self._log_tree.delete(item)
        for r in reversed(rows):
            ts    = (r.get("ts") or "").replace("T", " ")[:19]
            evt   = r.get("evt", "")
            in_v  = f"{r['inVol']:.2f} L"  if r.get("inVol")  is not None else "—"
            out_v = f"{r['outVol']:.2f} L" if r.get("outVol") is not None else "—"
            wt    = f"{r['weight']} kg"    if r.get("weight") is not None else "—"
            lvl   = f"{r['level']}%"       if r.get("level")  is not None else "—"
            tag   = "alarm" if ("⚠" in evt or "ALARM" in evt) else ""
            self._log_tree.insert("", "end",
                                  values=(ts, evt, in_v, out_v, wt, lvl),
                                  tags=(tag,))

    # ══ API ACTIONS ═══════════════════════════════════════════════
    def _ctrl(self, side, action):
        threading.Thread(target=lambda: api_post("/api/control",
                         {"side": side, "action": action}),
                         daemon=True).start()

    def _ctrl_valve(self, side):
        if self._data:
            s = self._data.get(side, {})
            if s.get("operation") != "REMOTE":
                self._ctrl(side, "run")

    def _apply_vol(self, side, var):
        try:
            vol = float(var.get())
            if vol <= 0:
                raise ValueError
        except ValueError:
            self._show_toast("Enter a valid volume > 0", "warn")
            return

        def do():
            try:
                api_post("/api/control", {"side": side, "action": "apply", "vol": vol})
                density = (self._data or {}).get("tank", {}).get("density_kgl", 0.87)
                kg   = vol * density
                sign = "+" if side == "infeed" else "−"
                lbl  = "Infeed" if side == "infeed" else "Outfeed"
                self.after(0, lambda: self._show_toast(f"{lbl} {sign}{kg:.2f} kg"))
            except Exception as e:
                self.after(0, lambda: self._show_toast(str(e), "warn"))

        threading.Thread(target=do, daemon=True).start()

    # ── Admin / Settings ──────────────────────────────────────────
    def _check_pass(self):
        if self._pass_entry.get() == ADMIN_PASS:
            self._admin = True
            self._admin_gate_frm.grid_remove()
            self._admin_open_frm.grid(row=1, column=0, sticky="ew",
                                      padx=16, pady=(0, 8))
            for sr in self._setting_rows.values():
                sr.enable()
            self._save_btn.configure(state="normal")
            self._admin_err_lbl.configure(text="")
        else:
            self._admin_err_lbl.configure(text="Incorrect password")
            self._pass_entry.delete(0, "end")

    def _lock_admin(self):
        self._admin = False
        self._admin_open_frm.grid_remove()
        self._admin_gate_frm.grid(row=0, column=0, sticky="ew",
                                  padx=16, pady=(14, 8))
        self._pass_entry.delete(0, "end")
        for sr in self._setting_rows.values():
            sr.disable()
        self._save_btn.configure(state="disabled")
        self._settings_synced = False

    def _sync_settings(self, d):
        tk_d = d.get("tank", {})
        vals = {
            "s-code":    d.get("product_code", ""),
            "s-name":    d.get("product", ""),
            "s-maxkg":   str(tk_d.get("max_kg", "")),
            "s-density": str(tk_d.get("density_kgl", 0.87)),
            "s-tare":    str(tk_d.get("tare_kg", 0)),
            "s-hi":      str(tk_d.get("hi_threshold_pct", "")),
            "s-lo":      str(tk_d.get("lo_threshold_pct", "")),
            "s-inf-def": str(d.get("infeed", {}).get("manual_vol_L", 25)),
            "s-inf-max": "200",
        }
        for sid, val in vals.items():
            if sid in self._setting_rows:
                self._setting_rows[sid].set(str(val))

    def _save_settings(self):
        if not self._admin or not self._data:
            return
        d = self._data

        def fv(key, default):
            try:    return float(self._setting_rows[key].get())
            except: return default

        d["product_code"]              = self._setting_rows["s-code"].get()
        d["product"]                   = self._setting_rows["s-name"].get()
        d["tank"]["max_kg"]            = fv("s-maxkg",   d["tank"]["max_kg"])
        d["tank"]["density_kgl"]       = fv("s-density",  0.87)
        d["tank"]["tare_kg"]           = fv("s-tare",     0)
        d["tank"]["hi_threshold_pct"]  = fv("s-hi",       d["tank"]["hi_threshold_pct"])
        d["tank"]["lo_threshold_pct"]  = fv("s-lo",       d["tank"]["lo_threshold_pct"])
        d["infeed"]["manual_vol_L"]    = fv("s-inf-def",  25)

        def do():
            try:
                api_post("/api/control", {
                    "side":   "_settings",
                    "action": "save_settings",
                    "data":   d,
                })
                self.after(0, lambda: self._show_toast("Settings saved"))
                self._settings_synced = False
            except Exception as e:
                self.after(0, lambda: self._show_toast(str(e), "warn"))

        threading.Thread(target=do, daemon=True).start()

    # ── Log actions ───────────────────────────────────────────────
    def _export_json(self):
        if not self._data:
            return
        ts   = datetime.now().strftime("%Y-%m-%d")
        path = os.path.join(os.path.expanduser("~"), f"ols_{ts}.json")
        with open(path, "w") as fh:
            json.dump(self._data, fh, indent=2)
        self._show_toast(f"Exported → {path}")

    def _clear_log(self):
        if not messagebox.askyesno("Clear Log", "Clear all log entries?"):
            return
        def do():
            try:
                api_delete("/api/log")
                self.after(0, lambda: self._show_toast("Log cleared"))
            except Exception as e:
                self.after(0, lambda: self._show_toast(str(e), "warn"))
        threading.Thread(target=do, daemon=True).start()


# ══ ENTRY POINT ═══════════════════════════════════════════════════
if __name__ == "__main__":
    app = OLSApp()
    app.mainloop()