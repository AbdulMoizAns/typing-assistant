"""Floating suggestion popup rendered next to the caret."""
from __future__ import annotations

import tkinter as tk
from tkinter import Listbox

from . import config

BG = "#1e1e2e"
HEADER_BG = "#181825"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
NEXT_ACCENT = "#cba6f7"


class SuggestionPopup:
    """Dark themed listbox popup that follows the caret."""

    def __init__(self, root, on_select_callback):
        self.root = root
        self.on_select = on_select_callback
        self.top = None
        self.listbox = None
        self.header_lbl = None
        self.suggestions: list[str] = []
        self.current_word = ""
        self.active = False
        self.is_next_word = False

    # ------------------------------------------------------------------ show
    def show(self, suggestions, word, x, y, is_next_word=False):
        if not suggestions:
            self.close()
            return

        self.suggestions = list(suggestions)
        self.current_word = word
        self.is_next_word = is_next_word

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()

        visible = min(len(self.suggestions), config.MAX_VISIBLE_ROWS)
        height = visible * config.ROW_HEIGHT + config.POPUP_HEADER_HEIGHT

        popup_x = max(config.POPUP_MIN_GAP,
                      min(x, screen_w - config.POPUP_WIDTH - config.POPUP_MIN_GAP))

        below = y + height + config.POPUP_CARET_GAP
        if below > screen_h - config.POPUP_MIN_GAP:
            above = y - height - config.POPUP_CARET_GAP
            popup_y = above if above >= config.POPUP_MIN_GAP else config.POPUP_MIN_GAP
        else:
            popup_y = max(config.POPUP_MIN_GAP, y)

        # The window is created once and then re-used: rebuilding it on every
        # keystroke costs hundreds of milliseconds because of the window
        # manager round trips for topmost and deiconify.
        if self.top is None:
            self._build_window()

        if self.header_lbl:
            if self.is_next_word:
                # No emoji: rendering them stalls the UI for seconds.
                self.header_lbl.config(text="  NEXT WORD (Tab / Enter to insert)", fg=NEXT_ACCENT)
            else:
                self.header_lbl.config(text="  SUGGESTIONS", fg=ACCENT)

        self.top.geometry(f"{config.POPUP_WIDTH}x{height}+{popup_x}+{popup_y}")
        self.listbox.delete(0, tk.END)
        for index, item in enumerate(self.suggestions):
            display = item.replace("\n", " / ") if "\n" in item else item
            prefix = f"  {index + 1}. " if self.is_next_word else "  "
            self.listbox.insert(tk.END, f"{prefix}{display}")
        self.listbox.select_set(0)
        self.listbox.activate(0)

        self.top.deiconify()
        self.active = True

    def _build_window(self) -> None:
        self.top = tk.Toplevel(self.root)
        self.top.title("Alpha Suggestions")
        self.top.attributes("-topmost", True)
        self.top.overrideredirect(True)
        self.top.configure(bg=BG)
        self.top.withdraw()

        self.header_lbl = tk.Label(
            self.top, text="", font=("Segoe UI", 8, "bold"),
            bg=HEADER_BG, fg=ACCENT, anchor="w", padx=8, pady=3,
        )
        self.header_lbl.pack(fill=tk.X)

        self.listbox = Listbox(
            self.top, font=("Segoe UI", 11), selectmode=tk.SINGLE,
            bg=BG, fg=FG, selectbackground="#313244", selectforeground=ACCENT,
            activestyle="none", bd=0, highlightthickness=1, highlightbackground="#45475a",
        )
        self.listbox.pack(fill=tk.BOTH, expand=True, padx=3, pady=(0, 3))
        self.listbox.bind("<ButtonRelease-1>", self._on_mouse_click)

    # ----------------------------------------------------------------- close
    def close(self):
        """Hide the popup but keep the window around for instant re-use."""
        self.active = False
        if self.top is not None:
            try:
                self.top.withdraw()
            except Exception:
                pass

    # ------------------------------------------------------------ navigation
    def _on_mouse_click(self, event):
        index = self.listbox.nearest(event.y)
        if 0 <= index < len(self.suggestions):
            selected = self.suggestions[index]
            was_next = self.is_next_word
            original = self.current_word
            self.close()
            self.on_select(original, selected, is_next_word=was_next)

    def select_next(self):
        if not self.listbox or not self.suggestions:
            return
        index = self.listbox.curselection()
        if not index:
            self.listbox.select_set(0)
            self.listbox.activate(0)
        elif index[0] < len(self.suggestions) - 1:
            new_index = index[0] + 1
            self.listbox.select_clear(index[0])
            self.listbox.select_set(new_index)
            self.listbox.activate(new_index)
            self.listbox.see(new_index)

    def select_prev(self):
        if not self.listbox or not self.suggestions:
            return
        index = self.listbox.curselection()
        if index and index[0] > 0:
            new_index = index[0] - 1
            self.listbox.select_clear(index[0])
            self.listbox.select_set(new_index)
            self.listbox.activate(new_index)
            self.listbox.see(new_index)

    def confirm_selected(self):
        if not self.listbox or not self.suggestions:
            return
        index = self.listbox.curselection()
        selected_index = index[0] if index else 0
        if 0 <= selected_index < len(self.suggestions):
            word = self.suggestions[selected_index]
            was_next = self.is_next_word
            original = self.current_word
            self.close()
            self.on_select(original, word, is_next_word=was_next)

    def navigate(self, key):
        """Handle a navigation key.  Returns True when the key was consumed."""
        if not self.active:
            return False
        if key in ("up", "w"):
            self.select_prev()
            return True
        if key in ("down", "s"):
            self.select_next()
            return True
        if key in ("enter", "return", "tab"):
            self.confirm_selected()
            return True
        if key in ("escape", "esc"):
            self.close()
            return True
        return False
