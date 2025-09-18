#!/usr/bin/env python3
"""
Setup script for YT Music Downloader
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README for long description
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    requirements = [
        line.strip() 
        for line in requirements_file.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("#")
    ]

setup(
    name="yt-music-downloader",
    version="1.0.0",
    author="YT Music Downloader Contributors",
    author_email="",
    description="Advanced YouTube/YouTube Music playlist downloader with rich CLI interface and car audio optimization",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/tu-usuario/yt-music-downloader",
    project_urls={
        "Bug Reports": "https://github.com/tu-usuario/yt-music-downloader/issues",
        "Source": "https://github.com/tu-usuario/yt-music-downloader",
        "Documentation": "https://github.com/tu-usuario/yt-music-downloader/wiki",
    },
    packages=find_packages(),
    py_modules=["download_playlist"],
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: End Users/Desktop",
        "Topic :: Multimedia :: Sound/Audio",
        "Topic :: Multimedia :: Video",
        "Topic :: Internet :: WWW/HTTP",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: MacOS",
        "Operating System :: POSIX :: Linux",
        "Environment :: Console",
        "Natural Language :: English",
        "Natural Language :: Spanish",
    ],
    keywords="youtube music downloader playlist mp3 audio car automotive cli rich",
    python_requires=">=3.8",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "audio": [
            "mutagen>=1.47.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "yt-music-dl=download_playlist:app",
            "ytmusic-dl=download_playlist:app",
        ],
    },
    include_package_data=True,
    zip_safe=False,
    platforms=["any"],
)