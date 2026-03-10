# System Preparation

Before installing **Raman-Map-GUI**, a few basic tools must be available on your system.  
This guide explains how to install the required software:

- **Git** – for downloading the source code  
  More information: https://git-scm.com/

- **uv** – recommended Python package and environment manager  
  More information: https://docs.astral.sh/uv/

*(Alternatively, you can install Python and pip manually.)*

---

# Install Git

Git is used to download the project source code from the repository.

## Linux (Ubuntu / Debian)

```bash
sudo apt update
sudo apt install git
```

## macOS

If you use **Homebrew**:

```bash
brew install git
```

Alternatively, install Git from the official website:

https://git-scm.com/downloads

## Windows

Download and install Git from:

https://git-scm.com/download/win

After installation, verify that Git works:

```bash
git --version
```

You should see an output similar to:

```text
git version 2.x.x
```

---

# Install uv (Recommended)

The recommended way to manage Python dependencies for **Raman-Map-GUI** is using **uv**.  
It automatically handles virtual environments and package installation.

Install **uv** using the official installation script:

## Linux / macOS

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Restart your terminal after installation.

Verify installation:

```bash
uv --version
```

---

## Windows

Install uv using PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Then verify:

```powershell
uv --version
```

---

# Alternative: Install Python and pip

If you prefer not to use **uv**, you can install **Python**, **pip** and **venv** manually.

## Linux (Ubuntu / Debian)

```bash
sudo apt install python3 python3-pip python3-venv
```

## macOS

Using Homebrew:

```bash
brew install python
```

## Windows

Download Python from:

https://www.python.org/downloads/

During installation, make sure to enable:

```
Add Python to PATH
```

Verify installation:

```bash
python --version
pip --version
```

---

# Next Step

Once the system preparation is complete, continue with:

➡ **[Installation Guide](installation.md)**