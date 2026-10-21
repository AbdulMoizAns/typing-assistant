"""Dashboard window: status, sandbox, live suggestions and activity feed."""
from __future__ import annotations

import os
import re
import tkinter as tk
from datetime import datetime
from tkinter import Listbox, Scrollbar

from . import config

BG = "#1e1e2e"
PANEL = "#181825"
FG = "#cdd6f4"
MUTED = "#a6adc8"
ACCENT = "#89b4fa"
GREEN = "#a6e3a3"
RED = "#f38ba8"
PURPLE = "#cba6f7"
CYAN = "#89dceb"

WORD_RE = re.compile(r"[a-zA-Z\u0600-\u06ff']+")


class DashboardUI:
    """The ALPHA control centre."""

    def __init__(self, root, assistant):
        self.root = root
        self.assistant = assistant
        self.assistant.dashboard_ui = self

        self.root.title("ALPHA Typing Assistant v6.0")
        self.root.configure(bg=BG)
        width, height = 660, 660
        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        self.root.geometry(f"{width}x{height}+{(screen_w - width) // 2}+{(screen_h - height) // 2}")
        self.root.minsize(600, 580)

        self.logo_img = None
        self._load_icons()
        self._build_ui()

    # ----------------------------------------------------------------- icons
    def _load_icons(self):
        icon_ico = os.path.join(config.BASE_DIR, "app_icon.ico")
        icon_32 = os.path.join(config.BASE_DIR, "app_icon_32.png")
        icon_png = os.path.join(config.BASE_DIR, "app_icon.png")

        if os.path.exists(icon_ico):
            try:
                self.root.iconbitmap(icon_ico)
            except Exception:
                pass

        for candidate in (icon_32, icon_png):
            if os.path.exists(candidate):
                try:
                    self.logo_img = tk.PhotoImage(file=candidate)
                    self.root.iconphoto(True, self.logo_img)
                    break
                except Exception:
                    continue

    # ------------------------------------------------------------------- ui
    def _build_ui(self):
        header = tk.Frame(self.root, bg=PANEL, padx=16, pady=12)
        header.pack(fill=tk.X)

        if self.logo_img:
            tk.Label(header, image=self.logo_img, bg=PANEL).pack(side=tk.LEFT, padx=(0, 10))

        tk.Label(
            header, text="ALPHA Typing Assistant", font=("Segoe UI", 16, "bold"),
            bg=PANEL, fg=ACCENT,
        ).pack(side=tk.LEFT)

        self.status_lbl = tk.Label(
            header, text="", font=("Segoe UI", 11, "bold"), bg=PANEL, fg=GREEN
        )
        self.status_lbl.pack(side=tk.LEFT, padx=(15, 6))

        self.mode_lbl = tk.Label(
            header, text="", font=("Segoe UI", 9, "bold"), bg=PANEL, fg=CYAN
        )
        self.mode_lbl.pack(side=tk.LEFT, padx=4)

        self.toggle_btn = tk.Button(
            header, text="Pause Assistant", font=("Segoe UI", 9, "bold"),
            bg="#313244", fg=FG, activebackground="#45475a", activeforeground=ACCENT,
            bd=0, padx=10, pady=4, cursor="hand2", command=self.assistant.toggle_assistant,
        )
        self.toggle_btn.pack(side=tk.RIGHT)

        content = tk.Frame(self.root, bg=BG, padx=16, pady=10)
        content.pack(fill=tk.BOTH, expand=True)

        tk.Label(
            content, text="Interactive Test Sandbox (works here and in ANY Windows app):",
            font=("Segoe UI", 10, "bold"), bg=BG, fg=FG, anchor="w",
        ).pack(fill=tk.X, pady=(0, 4))

        self.sandbox_entry = tk.Text(
            content, font=("Segoe UI", 12), bg=PANEL, fg=FG,
            insertbackground=ACCENT, selectbackground="#313244", selectforeground=ACCENT,
            relief=tk.FLAT, bd=0, height=3, padx=10, pady=8, wrap=tk.WORD,
        )
        self.sandbox_entry.pack(fill=tk.X)
        self.sandbox_entry.insert(
            tk.END, "Try typing here! E.g. type 'teh ' or 'shukria ' or 'sig1', or type 'hel'..."
        )
        self.sandbox_entry.bind("<FocusIn>", self._clear_sandbox_placeholder)
        self.sandbox_entry.bind("<KeyRelease>", self._on_sandbox_key)

        chips_frame = tk.Frame(content, bg=BG)
        chips_frame.pack(fill=tk.X, pady=(6, 8))

        self.chips_label = tk.Label(
            chips_frame, text="Live Suggestions:", font=("Segoe UI", 9, "bold"),
            bg=BG, fg=MUTED,
        )
        self.chips_label.pack(side=tk.LEFT)

        self.chips_container = tk.Frame(chips_frame, bg=BG)
        self.chips_container.pack(side=tk.LEFT, padx=10)
        self._render_default_chips(["hello", "help", "thanks", "Shukriya", "Theek"])

        options_frame = tk.Frame(content, bg=BG)
        options_frame.pack(fill=tk.X, pady=(0, 6))

        self.auto_suggest_var = tk.BooleanVar(value=self.assistant.auto_suggest)
        tk.Checkbutton(
            options_frame, text="Auto-show popup suggestions while typing (no hotkey needed)",
            variable=self.auto_suggest_var, font=("Segoe UI", 9),
            bg=BG, fg=FG, selectcolor=PANEL, activebackground=BG, activeforeground=ACCENT,
            command=self._on_toggle_auto_suggest,
        ).pack(anchor="w")

        self.next_word_var = tk.BooleanVar(value=self.assistant.next_word_prediction)
        tk.Checkbutton(
            options_frame, text="Next-Word prediction on Space (Google Gboard style)",
            variable=self.next_word_var, font=("Segoe UI", 9),
            bg=BG, fg=FG, selectcolor=PANEL, activebackground=BG, activeforeground=PURPLE,
            command=self._on_toggle_next_word,
        ).pack(anchor="w")

        tk.Label(
            content, text="Recent Auto-Corrections & Activity Feed:",
            font=("Segoe UI", 10, "bold"), bg=BG, fg=FG, anchor="w",
        ).pack(fill=tk.X, pady=(4, 2))

        feed_frame = tk.Frame(content, bg=PANEL)
        feed_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 8))

        scrollbar = Scrollbar(feed_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.activity_listbox = Listbox(
            feed_frame, font=("Consolas", 10), bg=PANEL, fg=MUTED,
            selectbackground="#313244", selectforeground=ACCENT, bd=0, relief=tk.FLAT,
            yscrollcommand=scrollbar.set,
        )
        self.activity_listbox.pack(fill=tk.BOTH, expand=True, padx=8, pady=6)
        scrollbar.config(command=self.activity_listbox.yview)

        self.activity_listbox.insert(
            tk.END,
            f"[{datetime.now().strftime('%H:%M:%S')}] ALPHA engine online - "
            f"Notepad, Chrome, Word, VS Code, Discord, ...",
        )

        guide_frame = tk.Frame(content, bg=PANEL, padx=12, pady=6)
        guide_frame.pack(fill=tk.X)

        tk.Label(
            guide_frame,
            text=(
                "- Typing 2+ letters: suggestions popup appears automatically\n"
                "- Space: auto-corrects typos (teh -> the, shukria -> Shukriya)\n"
                "- Ctrl+Space or double-Ctrl: open the popup manually\n"
                "- Up/Down + Enter: pick a suggestion | Escape: close the popup\n"
                "- Ctrl+Alt+X: toggle assistant | Ctrl+Alt+S: session summary"
            ),
            font=("Segoe UI", 9), bg=PANEL, fg=MUTED, justify=tk.LEFT,
        ).pack(anchor="w")

        footer = tk.Frame(self.root, bg=PANEL, padx=16, pady=8)
        footer.pack(fill=tk.X)

        tk.Button(
            footer, text="Test Popup Now", font=("Segoe UI", 9, "bold"),
            bg=ACCENT, fg=BG, activebackground="#b4befe",
            bd=0, padx=12, pady=5, cursor="hand2", command=self._test_popup_manual,
        ).pack(side=tk.LEFT)

        tk.Button(
            footer, text="Clear Sandbox", font=("Segoe UI", 9),
            bg="#313244", fg=FG, activebackground="#45475a",
            bd=0, padx=10, pady=5, cursor="hand2", command=self._clear_sandbox,
        ).pack(side=tk.LEFT, padx=10)

        tk.Button(
            footer, text="Minimize to Background", font=("Segoe UI", 9),
            bg="#313244", fg=FG, activebackground="#45475a",
            bd=0, padx=10, pady=5, cursor="hand2", command=self.root.iconify,
        ).pack(side=tk.RIGHT)

        self.update_status_ui()

    # -------------------------------------------------------------- toggles
    def _on_toggle_auto_suggest(self):
        self.assistant.set_auto_suggest(self.auto_suggest_var.get())

    def _on_toggle_next_word(self):
        self.assistant.set_next_word_prediction(self.next_word_var.get())

    def _clear_sandbox_placeholder(self, event):
        text = self.sandbox_entry.get("1.0", tk.END).strip()
        if "Try typing here!" in text:
            self.sandbox_entry.delete("1.0", tk.END)

    def _clear_sandbox(self):
        self.sandbox_entry.delete("1.0", tk.END)
        self.sandbox_entry.focus()

    # ------------------------------------------------------------- sandbox
    def _on_sandbox_key(self, event):
        if event.keysym == "space" and self.assistant.next_word_prediction:
            self._trigger_sandbox_next_word()
            return

        text = self.sandbox_entry.get("1.0", "insert").strip()
        words = WORD_RE.findall(text)
        if words:
            last = words[-1]
            if len(last) >= 2:
                suggestions = self.assistant.dm.get_smart_matches_with_prediction(last)
                self.update_suggestion_chips(suggestions[:5], is_next=False)

    def _trigger_sandbox_next_word(self):
        text = self.sandbox_entry.get("1.0", "insert")
        words = WORD_RE.findall(text)
        if not words:
            return
        last_word = words[-1]
        prev_word = words[-2] if len(words) >= 2 else None
        next_words = self.assistant.dm.predict_next_words(last_word, prev_word=prev_word, limit=5)
        if next_words:
            self.update_suggestion_chips(next_words, is_next=True)

    # --------------------------------------------------------------- chips
    def _render_default_chips(self, items):
        self.update_suggestion_chips(items, is_next=False)

    def update_suggestion_chips(self, items, is_next=False):
        if not items:
            return
        for widget in self.chips_container.winfo_children():
            widget.destroy()

        if is_next:
            self.chips_label.config(text="⚡ Next Word:", fg=PURPLE)
            btn_bg, btn_fg, btn_active = "#2b2042", PURPLE, "#453266"
        else:
            self.chips_label.config(text="Live Suggestions:", fg=MUTED)
            btn_bg, btn_fg, btn_active = "#313244", ACCENT, "#45475a"

        for item in items[:5]:
            tk.Button(
                self.chips_container,
                text=f"> {item}" if is_next else item,
                font=("Segoe UI", 8, "bold" if is_next else "normal"),
                bg=btn_bg, fg=btn_fg, activebackground=btn_active,
                bd=0, padx=8, pady=2, cursor="hand2",
                command=lambda word=item, is_next_word=is_next: self._insert_chip(word, is_next_word),
            ).pack(side=tk.LEFT, padx=3)

    def _insert_chip(self, word, is_next=False):
        self.sandbox_entry.insert(tk.INSERT, f"{word} ")
        self.sandbox_entry.focus()
        if self.assistant.next_word_prediction:
            self.root.after(60, self._trigger_sandbox_next_word)

    # -------------------------------------------------------------- actions
    def _test_popup_manual(self):
        pos_x = self.root.winfo_rootx() + 150
        pos_y = self.root.winfo_rooty() + 180
        self.assistant.popup.show(
            ["hello", "help", "helpful", "thanks", "Shukriya", "Theek"],
            "hel", pos_x, pos_y,
        )

    def add_log_entry(self, entry):
        line = f"[{entry['time']}] Auto-corrected: '{entry['from']}' -> '{entry['to']}' ({entry['app']})"
        self.activity_listbox.insert(0, line)
        if self.activity_listbox.size() > 50:
            self.activity_listbox.delete(50, tk.END)

    def update_status_ui(self):
        if self.assistant.enabled:
            self.status_lbl.config(text="[ACTIVE]", fg=GREEN)
            self.toggle_btn.config(text="Pause Assistant")
        else:
            self.status_lbl.config(text="[PAUSED]", fg=RED)
            self.toggle_btn.config(text="Resume Assistant")

        injector = getattr(self.assistant, "injector", None)
        mode = getattr(injector, "mode", "unknown")
        privacy = "Clipboard-free" if mode == "unicode" else f"Insertion: {mode}"
        # Emoji are deliberately avoided here: rendering them forces a slow
        # system wide font fallback which freezes the UI for several seconds.
        self.mode_lbl.config(text=f"Air-Gap Locked | {privacy}", fg=CYAN)
