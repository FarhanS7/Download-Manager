# 🗂️ Downloads Organizer — Clean Your Downloads Folder Automatically

A simple, production-ready Python script that automatically organizes your Downloads folder into categories like **Documents**, **Images**, **Videos**, etc.

---

## 🚨 Problem

Your Downloads folder keeps getting messy — PDFs, images, videos, and installers all piling up.  
Finding one file becomes a mini treasure hunt. 🧭

---

## 💡 Solution

The **Downloads Organizer** script automates the cleanup.  
It scans your Downloads directory, categorizes each file by type, moves them into proper folders, and keeps logs — all safely, with preview and undo features.

---

## ⚙️ Features

| Feature | Description |
|----------|-------------|
| 🧠 Smart Categorization | Sorts files into folders (Documents, Images, Videos, etc.) |
| 🧪 Dry-Run Mode | Preview changes before moving any files |
| 🕹️ Undo Support | Revert the last *N* file moves easily |
| 🧩 Configurable | Customize file categories and paths via `config.json` |
| 💾 Logging | Detailed logs of every move and undo |
| 🧱 Cross-Platform | Works on Windows, macOS, and Linux |
| 🚀 No Dependencies | Uses only built-in Python libraries |

---

## 🧰 Tech Stack

- **Language:** Python 3.8+
- **Libraries:** `os`, `shutil`, `pathlib`, `json`, `argparse`, `logging`, `datetime`
- **Tools:** VS Code / PyCharm / Terminal

---

## 📁 Folder Structure

DownloadsOrganizer/
├── organize_downloads.py # Main script
├── config.json # Configuration for categories & paths
├── logs/ # Folder for logs
│ ├── organize.log
│ └── actions.jsonl
└── README.md

🚀 Usage
1️⃣ Preview (safe dry-run)
python organize_downloads.py --dry-run

2️⃣ Run for real
python organize_downloads.py

3️⃣ Undo last 10 moves
python organize_downloads.py --undo 10
