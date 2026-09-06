<div align="center">

<img src="app_icon.png" width="120" height="120" alt="ALPHA Typing Assistant Logo" style="border-radius: 24px; margin-bottom: 10px;" />

# ⚡ ALPHA Typing Assistant v5.1

**The Intelligent, High-Speed, Offline System-Wide Typing Assistant for Windows**  
*Featuring Google Gboard-Style Next-Word Prediction & Two-Tier Frequency Word Prioritization*

[![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-0078D6?style=for-the-badge&logo=windows)](https://microsoft.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Privacy](https://img.shields.io/badge/Privacy-100%25%20Offline-9cf?style=for-the-badge)]()
[![Tests](https://img.shields.io/badge/Tests-69%2F69%20Passed-brightgreen?style=for-the-badge)]()

</div>

---

## 📖 Overview

**ALPHA Typing Assistant** is a lightweight, background Windows software designed to accelerate typing across **all applications** (Chrome, Notepad, Microsoft Word, WhatsApp Web, VS Code, Discord, Slack, etc.). 

It bridges the gap between desktop typing and modern mobile keyboards by introducing **Google Gboard-style next-word predictions**, **instant typo corrections**, and an **intelligent two-tier frequency engine** that prioritizes high-frequency everyday vocabulary while completely filtering out obscure and archaic dictionary noise.

It offers native, context-aware support for both **English** and **Roman Urdu**.

---

## ✨ Key Features

### 1. ⚡ Google Gboard-Style Next-Word Prediction
- **Spacebar Prediction**: As soon as you type a word and press `Space`, ALPHA immediately predicts the most likely next words based on context.
- **N-Gram Model (Bigrams & Trigrams)**: Combines single-word transitions and two-word context with weighted scoring ($3\times$ weight for trigrams):
  - Type `how ` $\rightarrow$ predicts: `are`, `to`, `do`, `is`, `can`
  - Type `how are ` $\rightarrow$ predicts: `you`, `things`, `they`, `we`
  - Type `thank you ` $\rightarrow$ predicts: `so`, `very`, `much`, `for`
  - Type `aap ` $\rightarrow$ predicts: `kaise`, `kahan`, `kya`, `ko`
  - Type `aap kaise ` $\rightarrow$ predicts: `ho`, `hain`
- **Continuous Sentence Chaining**: Selecting a predicted word (via `Enter` or `Tab`) cleanly inserts it and **instantly triggers suggestions for the following word**, allowing rapid sentence building with single keystrokes.
- **Zero-Backspace Safe Insertion**: Predictions are appended with a trailing space without removing previously typed words.

### 2. 🎯 Two-Tier Frequency Word Prioritization
- **No More Obscure Words**: Standard alphabetical dictionaries often suggest archaic words (e.g. typing `th` used to show `thackless` and `thackerayan`). ALPHA uses a **Two-Tier Engine**:
  - **Tier 1 (Everyday Vocabulary)**: 9,872 top English words + 154 Roman Urdu words ranked strictly by real-world usage frequency.
  - **Tier 2 (General Fallback)**: Deep 370,000-word fallback dictionary activated only for technical or rare terminology.
- **Immediate Gate**: When Tier 1 finds matches for common prefixes (`th` $\rightarrow$ `the`, `that`, `this`; `ap` $\rightarrow$ `apple`, `apply`), the raw dictionary is never touched.

### 3. 🌐 Native Roman Urdu & Multilingual Intelligence
- **Real-Time Language Detection**: Dynamically recognizes English, Roman Urdu, and Urdu script.
- **Phonetic Corrections**: Automatically fixes common Roman Urdu spellings:
  - `shukria` $\rightarrow$ `Shukriya`
  - `theek` / `thik` $\rightarrow$ `Theek`
  - `mei` $\rightarrow$ `mein`
  - `nhe` $\rightarrow$ `nahi`

### 4. 🪟 Universal Windows App Support
- Works seamlessly in any focused input field across Windows:
  - Text Editors: Notepad, Notepad++, Sublime Text, VS Code
  - Browsers: Google Chrome, Microsoft Edge, Brave, Firefox
  - Productivity: MS Word, Outlook, Excel, OneNote
  - Messaging: WhatsApp Desktop/Web, Discord, Telegram, Slack

### 5. 📍 Intelligent Caret & Cursor Tracking
- Floating suggestions popup automatically positions itself near the active text caret using Windows GUI APIs, with intelligent fallback to cursor position when caret API is suppressed by an application.

### 6. 🛡️ Zero-Trust Air-Gap Privacy Firewall (100% Offline & Isolated)
- **Hard Runtime Network Lock**: Built-in runtime firewall blocks all inbound and outbound socket creation, DNS resolution, and HTTP requests (`AirGapPrivacyViolation`).
- **Zero Keystroke Tracking or Leakage**: Keystrokes are processed solely in volatile RAM. No session logs are ever written to disk or transmitted across the network.
- **Zero Cloud & Telemetry**: 100% offline local operation. No external API, no background analytics, no ads.
- **Windows Defender Firewall Integration**: Includes `setup_airgap_firewall.bat` to enforce outbound network blocking at the Windows kernel firewall level.

### 7. 🖥️ Modern Dark-Mode Dashboard & Sandbox
- Styled with the Catppuccin Mocha palette (`#1e1e2e`).
- Includes an interactive **Test Sandbox** to experiment with suggestions and next-word chaining.
- **Quick Suggestion Bar** with one-click chips (`⚡ Next Word`).
- Real-time auto-correction and activity feed.

---

## ⌨️ Hotkeys & Shortcuts

| Shortcut | Action | Description |
| :--- | :--- | :--- |
| **`Space`** | **Auto-Correct / Predict** | Corrects typos and triggers Next-Word Predictions |
| **`Tab`** or **`Enter`** | **Insert Suggestion** | Accepts the highlighted word or prediction |
| **`Up` / `Down` Arrow** | **Navigate List** | Moves selection through the suggestion list |
| **`Escape`** | **Close Popup** | Dismisses the floating suggestion window |
| **`Ctrl + Space`** | **Manual Suggestion** | Opens suggestions popup near caret on demand |
| **`Double-Ctrl`** | **Quick Popup** | Quick double-tap of `Ctrl` opens the suggestion popup |
| **`Ctrl + Alt + X`** | **Toggle Assistant** | Pauses or resumes the assistant globally |
| **`Ctrl + Alt + S`** | **Session Summary** | Prints real-time analytics to the console |

---

## 🚀 Quick Start

### Prerequisites
- **Windows 10** or **Windows 11**
- **Python 3.10** or higher installed ([Download Python](https://www.python.org/downloads/))

### Installation

1. **Clone or Download the Repository**:
   ```bash
   git clone https://github.com/your-username/alpha-typing-assistant.git
   cd alpha-typing-assistant
   ```

2. **Install Required Python Packages**:
   ```bash
   pip install pynput pyperclip pywin32
   ```

3. **Launch ALPHA**:
   - Double-click **`run_alpha.bat`**  
   *or* run via command line:
   ```bash
   python alpha_assistant.py
   ```

---

## 📂 Project Structure

```
alpha-typing-assistant/
│
├── alpha_assistant.py         # Main application (Engine, Hooks, Caret, Popup, Dashboard)
├── run_alpha.bat              # Quick Windows launcher batch file
├── frequency_words.json       # Tier 1 high-frequency dataset (English + Roman Urdu)
├── dictionary.json            # Tier 2 fallback general dictionary (~370k words)
├── errors.json                # Common typo correction mappings
├── sequences.json             # N-Gram dataset (bigrams & trigrams for next-word prediction)
├── suggestions.json           # Custom user snippets and templates
├── recency.json               # Tracks recency scores for dynamic word weighting
├── usage_stats.json           # User usage frequencies for personalized ranking
└── README.md                  # Project documentation
```

---

## 🛠️ Customization & Snippets

### Expanding Text Snippets & Templates
You can configure custom shortcuts in `suggestions.json`. For example, typing `sig1` or `addr` in any application will suggest your pre-configured text:

```json
{
  "snippets": {
    "sig1": "Best regards,\nAbdul Moiz",
    "addr": "123, Main Street, Karachi, Pakistan",
    "email": "user@example.com"
  }
}
```

### Adding Custom Typo Corrections
Add your own common typos in `errors.json`:
```json
{
  "teh": "the",
  "shukria": "Shukriya",
  "wk": "week",
  "abt": "about"
}
```

---

## 🧪 Testing & Verification

ALPHA includes extensive automated test suites. To execute all unit and regression tests:

```bash
# Core regression tests (33 tests)
python scratch/verify_alpha.py

# Two-tier word frequency tests (19 tests)
python scratch/test_frequency_verification.py

# Next-word prediction verification (17 tests)
python scratch/test_next_word.py
```
> **Total: 69/69 automated tests passing (100% success rate).**

---

## 📜 License

This project is licensed under the **MIT License** - see the LICENSE file for details.

---

<div align="center">
  <sub>Built with ❤️ for ultra-fast, intelligent, and seamless typing.</sub>
</div>
