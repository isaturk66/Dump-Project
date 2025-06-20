# Dump Project

Minimal helper to turn any folder of source files into **one text blob** ready for ChatGPT / Gemini / Claude.

## Why?

Large-language models understand a codebase better when they see every file at once. Copy-pasting folders is a pain.  
`dump_project` prints a clean tree view plus the contents of every readable, non-binary file—nothing more, nothing less.

## Usage

```bash
# grab the script
curl -LO https://raw.githubusercontent.com/your-org/dump_project/main/dump_project.py

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

## One-file binaries (optional)

Need to run on a machine without Python? Build once per OS with PyInstaller:

```bash
# inside the repo
python3 -m pip install pyinstaller
pyinstaller --onefile dump_project.py      # binary appears in dist/
```

Add the resulting binary to your PATH, or run it directly:

```bash
     dump_project .    
```


## License

MIT © 2025 İsa Türk
