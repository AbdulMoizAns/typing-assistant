# Alpha AI Typing Assistant

Reserved by **Moiz Digital Service** — © 2026 All Rights Reserved

---

## Overview

Alpha is a Windows global typing assistant that provides **real-time autocomplete suggestions** and **auto-correction** in any application. It works system-wide — just start typing in any app and suggestions appear automatically.

## Features

- **Auto-Suggest** — Type anywhere, suggestions appear after 2+ characters
- **Auto-Correct** — 350+ common typo corrections (`teh` → `the`, `recieve` → `receive`)
- **Fuzzy Matching** — Even unknown typos get corrected via smart dictionary matching
- **370k English Dictionary** — Comprehensive word list for accurate suggestions
- **Custom Phrases** — Add your own shortcuts (greetings, email templates, code snippets)
- **Arrow Navigation** — Up/Down to navigate, Enter/Tab to select
- **Mouse Support** — Click any suggestion to insert
- **Double Ctrl** — Force-focus the suggestion popup
- **Customizable** — Edit `suggestions.json` and `errors.json` to add your own data

## Quick Start

1. **Double-click** `run_assistant.bat`  
   *(Auto-installs dependencies on first run)*

2. Start typing in any app (Notepad, browser, chat, etc.)

3. Suggestions appear automatically — press **↑/↓** to navigate, **Enter** to select

## Controls

| Key | Action |
|---|---|
| Type 2+ characters | Auto-show suggestions |
| ↑ / ↓ | Navigate suggestions |
| Enter / Tab | Select suggestion |
| Esc | Close popup |
| Double Ctrl | Force popup + keyboard focus |
| Mouse Click | Select suggestion |

## File Structure

```
├── deepseek_python_20260606_1c3626.py   Main application
├── run_assistant.bat                     Launcher (double-click to run)
├── suggestions.json                      Custom phrases & shortcuts
├── errors.json                           350+ typo corrections
├── dictionary.json                       370k English words
└── README.md                             This file
```

## Customization

### Add your own suggestions
Edit `suggestions.json`:
```json
{
  "greetings": ["Assalam-o-Alaikum", "Hello", "Hi"],
  "my_shortcuts": ["addr→my full address", "email→my@email.com"]
}
```

### Add typo corrections
Edit `errors.json`:
```json
{
  "teh": "the",
  "recieve": "receive"
}
```

## Requirements

- Windows 10/11
- Python 3.7+
- Dependencies (auto-installed): `pyautogui`, `pyperclip`, `pynput`

## License

© 2026 Moiz Digital Service. All Rights Reserved.
