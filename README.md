# ALPHA — Intelligent Typing Assistant

**Version 3.5 FINAL** | © 2026 Moiz Digital Service — All Rights Reserved

---

## Overview

ALPHA is a **global Windows typing assistant** that provides **real-time auto‑correction**, **smart suggestions**, and **next‑word prediction** in **any application**.  
Just type anywhere (browser, WhatsApp, VS Code, Notepad, MS Word) – suggestions appear instantly.

---

## ✨ Features

### Core
- **Auto‑Correct** – Fixes common typos instantly (`teh` → `the`, `recieve` → `receive`)
- **Smart Suggestions** – Prefix‑based, ranked by frequency & recency
- **Next‑Word Prediction** – Learns word pairs & trigrams (`how` → `are` → `you`)
- **Context Awareness** – Previous word influences suggestions
- **370K English Dictionary** – Fast bisect search

### Language Support
- **English** – Full dictionary + error correction
- **Roman Urdu** – Automatic detection + common corrections (`mei` → `mein`)
- **Urdu Script** – Basic detection fallback

### Navigation & Controls
| Key | Action |
|---|---|
| `↑` / `↓` | Navigate suggestions |
| `Enter` / `Tab` | Select suggestion |
| `Esc` | Close popup |
| `Mouse Click` | Select suggestion |
| `Double Ctrl` | Force‑show suggestions |
| `Ctrl+Alt+X` | Toggle assistant ON/OFF |
| `Ctrl+Alt+S` | Show session summary |

### Smart Features
- **Caret Tracking** – Popup follows your cursor via Win32 API (works in almost all apps)
- **Enter Suppression** – No accidental form submission when popup is active
- **Language Detector** – Scoring‑based detection (English / Roman Urdu / Urdu script)
- **Session Tracking** – Logs corrections per app; summary on exit; temp file auto‑deleted
- **Recency Ranking** – Recently used words rank higher
- **Usage Frequency** – Frequently used words surface first
- **Self‑Learning** – Learns from your typing & selections (saved locally)

---

## 🚀 Quick Start

1. **Double‑click** `run_assistant.bat` (or run `python alpha_assistant.py` as Administrator)
2. Start typing in any app – suggestions appear after 2+ characters
3. Use `↑`/`↓` to navigate, `Enter` to select

---

## 📁 File Structure

| File | Description |
|------|-------------|
| `alpha_assistant.py` | Main application (v3.5 FINAL) |
| `run_assistant.bat` | Launcher (auto‑installs dependencies) |
| `suggestions.json` | Custom phrases & shortcuts |
| `errors.json` | 500+ polished typo corrections |
| `dictionary.json` | 370k English words (optional) |
| `user_learning.json` | Words you’ve typed (auto‑created) |
| `usage_stats.json` | Usage frequency (auto‑created) |
| `ru_learning.json` | Roman Urdu learned words (auto‑created) |
| `word_pairs.json` | Context pairs (auto‑created) |
| `recency.json` | Recency timestamps (auto‑created) |
| `sequences.json` | Learned word pairs & trigrams (auto‑created) |
| `README.md` | This file |

---

## ⚙️ How It Works

### Suggestion Pipeline
1. **Key press** → captured by global `pynput` hook  
2. **Language detection** → scoring based on vowel ratio, patterns, common words  
3. **Error correction** → checks `errors.json` + Roman Urdu corrections  
4. **Sequence prediction** → looks up learned word pairs/trigrams (`sequences.json`)  
5. **Enhanced ranking** → weighted scores (exact match, context, recency, frequency, dictionary)  
6. **Popup** → dark themed Tkinter window shown at cursor position

### Ranking Weights (simplified)
| Factor | Approx. Weight | Source |
|--------|---------------|--------|
| Exact correction | 1000 | `errors.json` |
| Context match | 800 | `word_pairs.json` |
| User learning | 500 | `user_learning.json` |
| Recency | 400 | `recency.json` |
| Usage frequency | 300 | `usage_stats.json` |
| Dictionary prefix | 100 | `dictionary.json` |
| Custom phrases | 60 | `suggestions.json` |

---

## 🛠 Customization

### Add your own suggestions  
Edit `suggestions.json`:
```json
{
  "greetings": ["Assalam-o-Alaikum", "Hello", "Hi"],
  "my_shortcuts": ["addr→123 Main St", "email→my@email.com"]
}