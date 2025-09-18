# 📦 Installation Guide

This guide will help you install YT Music Downloader on your system.

## 🎯 Quick Start

### 1. Install Python
YT Music Downloader requires Python 3.8 or newer.

**Check if Python is installed:**
```bash
python --version
# or
python3 --version
```

**Install Python if needed:**
- **Windows**: Download from [python.org](https://www.python.org/downloads/)
- **macOS**: Use [Homebrew](https://brew.sh/): `brew install python`
- **Linux**: Use your package manager: `sudo apt install python3 python3-pip`

### 2. Install ffmpeg
ffmpeg is required for audio conversion and processing.

#### Windows
**Option 1: Using winget (Windows 10+)**
```bash
winget install Gyan.FFmpeg
```

**Option 2: Using Chocolatey**
```bash
choco install ffmpeg
```

**Option 3: Manual Installation**
1. Download from [FFmpeg website](https://ffmpeg.org/download.html)
2. Extract to a folder (e.g., `C:\ffmpeg`)
3. Add `C:\ffmpeg\bin` to your PATH environment variable

#### macOS
**Using Homebrew (recommended):**
```bash
brew install ffmpeg
```

**Using MacPorts:**
```bash
sudo port install ffmpeg
```

#### Linux

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install ffmpeg
```

**Fedora:**
```bash
sudo dnf install ffmpeg
```

**Arch Linux:**
```bash
sudo pacman -S ffmpeg
```

**CentOS/RHEL:**
```bash
# Enable EPEL repository first
sudo yum install epel-release
sudo yum install ffmpeg
```

### 3. Verify ffmpeg Installation
```bash
ffmpeg -version
```
You should see version information if ffmpeg is properly installed.

### 4. Download YT Music Downloader
```bash
# Clone the repository
git clone https://github.com/tu-usuario/yt-music-downloader.git
cd yt-music-downloader

# Or download and extract ZIP file
```

### 5. Install Python Dependencies
```bash
# Install required packages
pip install -r requirements.txt

# On some systems, you might need to use pip3
pip3 install -r requirements.txt
```

### 6. Test Installation
```bash
# Test basic functionality
python download_playlist.py --help

# Test dependencies
python download_playlist.py about
```

## 🔧 Advanced Installation

### Virtual Environment (Recommended)
Using a virtual environment keeps your system Python clean:

```bash
# Create virtual environment
python -m venv ytmusic-env

# Activate virtual environment
# Windows:
ytmusic-env\Scripts\activate
# macOS/Linux:
source ytmusic-env/bin/activate

# Install dependencies
pip install -r requirements.txt

# When done, deactivate
deactivate
```

### Using setup.py
If you want to install as a Python package:

```bash
# Install in development mode
pip install -e .

# Or install normally
pip install .

# This allows you to use the command globally
yt-music-dl --help
ytmusic-dl --help
```

### Docker Installation (Optional)
If you prefer using Docker:

```dockerfile
# This is a future feature - Dockerfile not yet available
```

## 🛠️ Troubleshooting

### Common Issues

#### "ffmpeg not found"
- **Windows**: Make sure ffmpeg is in your PATH
- **macOS**: Try `brew reinstall ffmpeg`
- **Linux**: Try `which ffmpeg` to check if it's installed

#### "Permission denied" errors
```bash
# On Linux/macOS, you might need:
sudo pip install -r requirements.txt

# Or use user installation:
pip install --user -r requirements.txt
```

#### "No module named 'yt_dlp'"
```bash
# Update pip and reinstall
pip install --upgrade pip
pip install -r requirements.txt
```

#### SSL Certificate errors
```bash
# Update certificates
pip install --upgrade certifi

# Or on macOS:
/Applications/Python\ 3.x/Install\ Certificates.command
```

### Dependency Conflicts
If you have conflicts with existing Python packages:

```bash
# Use virtual environment (recommended)
python -m venv fresh-env
source fresh-env/bin/activate  # or fresh-env\Scripts\activate on Windows
pip install -r requirements.txt
```

### Updating
To update to the latest version:

```bash
# Pull latest changes
git pull origin main

# Update dependencies
pip install -r requirements.txt --upgrade
```

## 🔍 Verification

After installation, verify everything works:

### 1. Check Dependencies
```bash
python -c "import yt_dlp, typer, rich, psutil; print('✅ All Python dependencies OK')"
```

### 2. Check ffmpeg
```bash
ffmpeg -version
```

### 3. Test Basic Functionality
```bash
# Show help
python download_playlist.py --help

# Show system info
python download_playlist.py about

# Test configuration
python download_playlist.py config --show
```

### 4. Run Examples
```bash
python examples/basic_usage.py
```

## 🌐 Platform-Specific Notes

### Windows
- Use Command Prompt or PowerShell
- Make sure Python is added to PATH during installation
- Some antivirus software may flag downloaded files - this is normal

### macOS
- You might need to allow the application in System Preferences > Security
- Use Terminal for command-line operations
- Homebrew is the easiest way to install dependencies

### Linux
- Most distributions work out of the box
- You might need to install `python3-pip` separately
- Some distributions require `python3-venv` for virtual environments

## 📋 System Requirements

### Minimum Requirements
- **OS**: Windows 10, macOS 10.15, or Linux (any recent distribution)
- **Python**: 3.8+
- **RAM**: 512 MB available
- **Storage**: 50 MB for application, plus space for downloaded music
- **Network**: Internet connection for downloads

### Recommended Requirements
- **OS**: Latest stable version of your OS
- **Python**: 3.11+
- **RAM**: 2 GB available
- **Storage**: SSD for better performance
- **Network**: Broadband connection for faster downloads

## 🆘 Getting Help

If you're still having issues:

1. **Check the FAQ** in README.md
2. **Search existing issues** on GitHub
3. **Create a new issue** with:
   - Your operating system and version
   - Python version (`python --version`)
   - Complete error message
   - Steps you've tried

## ✅ Next Steps

Once installed successfully:
1. Read the **Usage Guide** in README.md
2. Try the **examples** in the `examples/` folder
3. Run the **interactive mode**: `python download_playlist.py`
4. Configure your preferences: `python download_playlist.py config --interactive`

Happy downloading! 🎵