# Dump Project

Minimal helper to turn any folder of source files into **one text blob** ready for ChatGPT / Gemini / Claude.

## Why?

Large-language models understand a codebase better when they see every file at once. Copy-pasting folders is a pain.  
`dump_project` prints a clean tree view plus the contents of every readable, non-binary file—nothing more, nothing less.

# Usage

## Run as a Python script

```bash
# grab the script
curl -LO https://raw.githubusercontent.com/isaturk66/Dump-Project/main/dump_project.py

# run it on a repo
python3 dump_project.py /path/to/project > project.txt
```

Upload `project.txt` to your favourite LLM and start asking questions.

### Ignore stuff you don’t want to share

Create a `.dumpignore` in the project root (same syntax as `.gitignore`):

```
# ignore generated files
dist/
*.log

# but keep the README
!README.md
```

Hidden folders (`.git/`, `.idea/`, …) are skipped automatically.

---

## Pre‑built binaries

Download the binary for your OS from the GitHub **Releases** page and make it executable.

### Linux

```bash
chmod +x dump_project-linux
./dump_project-linux /path/to/project > project.txt
```

(Optional) move it to your PATH:

```bash
sudo mv dump_project-linux /usr/local/bin/dump_project
```

### macOS

```bash
chmod +x dump_project-macos          # make it executable
xattr -d com.apple.quarantine dump_project-macos  # remove Gatekeeper quarantine
./dump_project-macos /path/to/project > project.txt
```

*(If you prefer the GUI, right‑click → **Open** once, then macOS will remember.)*

### Windows

```powershell
# If SmartScreen complains, click “More info” → “Run anyway”
# or unblock via PowerShell:
Unblock-File .\dump_project-win.exe

.\dump_project-win.exe C:\path\to\project > project.txt
```

Add the folder to your **Environment Variables → Path** for convenience.

---

## Build your own binary (optional)

```bash
python3 -m pip install pyinstaller
pyinstaller --onefile dump_project.py         # binary appears in dist/
```


## License

MIT © 2025 İsa Türk
