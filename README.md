<div align="center">

<img src="app_icon.png" width="120" height="120" alt="ALPHA Typing Assistant Logo" style="border-radius: 24px; margin-bottom: 10px;" />

# ⚡ ALPHA Typing Assistant v6.0

**The Intelligent, High-Speed, Offline System-Wide Typing Assistant for Windows**
*Google Gboard-style next-word prediction, two-tier frequency prioritisation, clipboard-free insertion*

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows)](https://microsoft.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-9cf?style=for-the-badge)]()
[![Tests](https://img.shields.io/badge/Tests-60%20passed-brightgreen?style=for-the-badge)]()
[![Deps](https://img.shields.io/badge/Dependencies-2-brightgreen?style=for-the-badge)]()

</div>

---

## 📖 Overview

**ALPHA Typing Assistant** is a lightweight background Windows application that accelerates typing across
**every** application (Chrome, Notepad, Microsoft Word, WhatsApp, VS Code, Discord, Slack, terminals …).

It bridges the gap between desktop typing and modern mobile keyboards by adding **Google Gboard-style next-word
predictions**, **instant typo correction** and an **intelligent two-tier frequency engine** that surfaces everyday
vocabulary first while still allowing rare, technical and medical vocabulary to be found.

Native support for **English**, **Roman Urdu** and **Urdu script**.

---

## ✨ What's New in v6.0

v6.0 is a full rewrite of the engine internals. The feature set stayed, but the code base was made correct,
fast and testable.

### 🐛 Critical bug fixes

| Problem | Effect before | Fix |
| :--- | :--- | :--- |
| `import pyautogui` was not in `requirements.txt` | the whole insertion engine silently died on a fresh install | `pyautogui` removed – **two** dependencies are enough now |
| Roman-Urdu corrections applied to English | *"I saw ten men"* became *"I saw ten mein"* | corrections are split into *typo* and *Roman-Urdu-only* tables, English words are protected |
| Tkinter calls from the hook thread | random crashes and UI freezes | every UI call is marshalled through a queue onto the Tk main thread |
| `sequences.json` rewritten on every space press | constant disk I/O and inflated n-gram counters | incremental learning + coalesced, debounced writes |
| The whole typing buffer was cleared after a correction | next-word prediction lost all context | only the corrected word is replaced, the sentence context survives |
| `word_pairs` learning never ran | contextual learning was dead code | the previous word is now passed through correctly |
| Clipboard was hijacked for every insertion | clipboard content could be lost, private data was exposed | text is injected with `SendInput`/`KEYEVENTF_UNICODE` – **the clipboard is never touched** |
| `Enter` was swallowed in terminals | pressing Enter in a console inserted a suggestion | consoles keep `Enter`/`Tab`, the popup is simply dismissed |
| 8th suggestion was never visible | one suggestion could not be picked | the popup shows all eight rows |
| Popup disappeared near the bottom of the screen | suggestions unreachable | the popup now flips above the caret |
| Emoji in the UI headers | rendering them froze the UI for **15 seconds** | plain text everywhere in the UI |

### ⚡ Performance

| Operation | Before | After |
| :--- | :--- | :--- |
| Application start-up | 5.4 s | ~1.5 s (cached index) |
| Suggestion lookup | full dictionary scan | 4 ms (tier 1 short-circuit) |
| Popup appearance | 400 – 900 ms | ~55 ms (window is re-used) |
| Disk writes while typing | one full rewrite per space | coalesced batched writes |
| Keystroke → suggestion | linear scans of every user table | prefix indexed lookups |

### 🧪 Testability

* The 1 800 line monolith was split into a focused `alpha/` package.
* **60 automated tests** (`pytest`) cover the language engine, the suggestion tiers, the n-gram model, the
  buffer bookkeeping, the UI dispatcher and the settings store.
* A rotating log file (`logs/alpha.log`) replaces `print` statements.

---

## 🚀 Quick Start

### Prerequisites
* Windows 10 / 11
* Python 3.10 or newer

### Installation

```bash
git clone https://github.com/your-username/alpha-typing-assistant.git
cd alpha-typing-assistant
pip install -r requirements.txt
```

### Launch

Double-click **`run_alpha.bat`** or run:

```bash
python alpha_assistant.py
```

### Build a standalone executable

```bash
pip install -r requirements-dev.txt
pyinstaller alpha.spec
# -> dist/ALPHA_Typing_Assistant.exe
```

---

## ⌨️ Hotkeys & Shortcuts

| Shortcut | Action |
| :--- | :--- |
| **`Space`** | Auto-corrects typos and triggers next-word prediction |
| **`Tab`** / **`Enter`** | Accept the highlighted suggestion |
| **`Up`** / **`Down`** | Move through the suggestion list |
| **`Escape`** | Close the popup |
| **`Ctrl + Space`** | Open the popup manually at the caret |
| **Double `Ctrl`** | Quick popup |
| **`Alt + /`** | Quick popup |
| **`Ctrl + Alt + X`** | Toggle the assistant globally |
| **`Ctrl + Alt + S`** | Print the session summary |

---

## 🧠 How the engine works

### Two-tier frequency engine

1. **Tier 1 – everyday vocabulary**: 9 872 ranked English words + 154 Roman Urdu words.
   As soon as tier 1 produces four candidates the 370 000-word fallback dictionary is never even read, so
   obsolete words such as *thackless* never appear.
2. **Tier 2 – general fallback**: only consulted when tier 1 cannot fill the popup, which keeps rare,
   scientific and medical terminology reachable.

### N-gram next-word prediction

Bigrams are weighted `1x`, trigrams `3x`:

```
how       -> are, to, do, is, can
how are   -> you, things, they, we
thank you -> so, very, much, for
aap       -> kaise, kahan, kya, ko
aap kaise -> ho, hain
```

Learning is **incremental**: committing a word only touches the pair that was just completed, so counters stay
honest and the dataset is flushed at most every ten seconds.

### Roman Urdu intelligence

Phonetic corrections are applied automatically:

| Typed | Corrected |
| :--- | :--- |
| `shukria` | `Shukriya` |
| `theek` / `thik` | `Theek` |
| `mei` | `mein` |
| `nhe` | `nahi` |
| `krna` | `karna` |

Words that exist in English (`men`, `main`, `ap`, `ye`) are **never** rewritten by the Roman Urdu table.

---

## 🛡️ Privacy

* **100 % offline.** A runtime firewall (`alpha/airgap.py`) blocks socket creation, DNS resolution and HTTP
  requests. `setup_airgap_firewall.bat` enforces the same at the Windows kernel level.
* **No keystroke logging.** Corrections are processed in RAM only; the session statistics are never written to disk.
* **No clipboard usage.** Text is injected with `SendInput`/`KEYEVENTF_UNICODE`, so the clipboard is never read
  or overwritten.
* **No telemetry, no cloud, no ads.**

---

## 🗂️ Project Structure

```
alpha-typing-assistant/
├── alpha/
│   ├── __init__.py          # package entry point
│   ├── main.py              # bootstrap (window, hook, shutdown)
│   ├── config.py            # paths, tunables, defaults
│   ├── logging_setup.py     # rotating file logger
│   ├── airgap.py            # runtime network firewall
│   ├── ui_queue.py          # thread-safe Tk dispatcher
│   ├── insertion.py         # unicode / clipboard text injection
│   ├── dictionary.py        # prefix index + on-disk cache
│   ├── ngram.py             # bigram + trigram model
│   ├── language.py          # detection + correction tables
│   ├── store.py             # DataManager, learning, persistence
│   ├── popup.py             # floating suggestion popup
│   ├── dashboard.py         # control centre window
│   ├── session.py           # session statistics
│   ├── settings.py          # persisted preferences
│   └── win32.py             # caret tracking, console detection
├── alpha_assistant.py       # launcher
├── alpha.spec               # PyInstaller build script
├── tests/                   # 60 pytest tests
├── dictionary.json          # tier 2 fallback dictionary (~370k words)
├── frequency_words.json     # tier 1 ranked vocabulary
├── errors.json              # typo corrections
├── sequences.json           # learned n-gram dataset
├── suggestions.json         # snippets, templates and variables
├── setup_airgap_firewall.bat
└── run_alpha.bat
```

---

## ✏️ Customisation

### Snippets and templates – `suggestions.json`

```json
{
  "snippets": {
    "sig1": "Best regards,\nAbdul Moiz",
    "addr": "123, Main Street, Karachi, Pakistan"
  },
  "templates": ["Hello, {name}.", "Please find your {noun} attached."],
  "variables": { "name": "Moiz", "noun": "report" }
}
```

Placeholders such as `{name}` are expanded from the `variables` section.

### Custom corrections – `errors.json`

```json
{ "teh": "the", "wk": "week", "abt": "about" }
```

`suggestions.json` and `errors.json` are reloaded automatically while the assistant is running.

---

## 🧪 Testing

```bash
pip install -r requirements-dev.txt
python -m pytest
```

The suite covers the language detector, the correction tables, the tier-1/tier-2 gate, the n-gram model,
template expansion, the buffer bookkeeping, the thread-safe dispatcher and the settings store.

---

## 📜 License

MIT – see [LICENSE](LICENSE).

---

<div align="center">
  <sub>Built with ❤️ for ultra-fast, intelligent and seamless typing.</sub>
</div>
