# Installation

This project uses **uv** for fast and reproducible environment management.  
However, it can also be installed using **pip** and a standard Python virtual environment.

If you have not yet prepared your system, see:

➡ **[System Preparation](pre-install.md)**



---

# Quick Start (Recommended – Using uv)

The easiest way to run the application is with **uv**, which automatically creates an isolated environment and installs all dependencies.

Clone the repository and run the application:

```bash
git clone https://github.com/ph-schmidt/Raman-Map-GUI.git
cd Raman-Map-GUI
uv run ramangui
```

You can optionally set the GUI color theme (`dark` or `light`):

```bash
uv run ramangui --theme=light
```

---

# Development Mode

To run the application with more verbose logging:

```bash
uv run ramangui --log-level=DEBUG
```

---

# Alternative Installation (pip + virtual environment)

If you prefer not to use **uv**, you can install the project using **pip** and a standard Python virtual environment.

## 1. Clone the repository

```bash
git clone https://github.com/ph-schmidt/Raman-Map-GUI.git
cd Raman-Map-GUI
```

## 2. Create a virtual environment

```bash
python -m venv .venv
```

## 3. Activate the environment

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows (PowerShell)

```powershell
.venv\Scripts\Activate.ps1
```

### Windows (Command Prompt)

```cmd
.venv\Scripts\activate.bat
```

## 4. Install the project and dependencies

```bash
pip install -e .
```

The `-e` flag installs the project in **editable mode**, which is useful during development.

## 5. Run the application

```bash
ramangui
```

You can also specify a theme:

```bash
ramangui --theme=light
```

---

# Updating the Installation

To update the project:

```bash
git pull
```

If using **pip**, you may also reinstall dependencies:

```bash
pip install -e .
```

---

# Next Step

Once the installation is complete, continue with the:

➡ **[User Guide](userguide.md)**