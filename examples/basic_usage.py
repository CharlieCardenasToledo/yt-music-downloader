#!/usr/bin/env python3
"""
Basic Usage Examples for YT Music Downloader

This file demonstrates common usage patterns for the YT Music Downloader.
"""

import sys
from pathlib import Path

# Add the parent directory to Python path to import our module
sys.path.insert(0, str(Path(__file__).parent.parent))

from download_playlist import (
    validate_playlist_url,
    load_config,
    save_config,
    auto_choose_output_folder,
    console
)

def example_url_validation():
    """Example: How to validate YouTube playlist URLs"""
    console.print("\n🔍 [bold]URL Validation Examples[/bold]\n")
    
    test_urls = [
        "https://music.youtube.com/playlist?list=PLrAXtmRdnEQy6SIH-G0r0PQnN_vdSP5WI",
        "https://www.youtube.com/playlist?list=PLrAXtmRdnEQy6SIH-G0r0PQnN_vdSP5WI",
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Single video (invalid)
        "not-a-url",  # Invalid URL
    ]
    
    for url in test_urls:
        is_valid, message, normalized = validate_playlist_url(url)
        status = "✅" if is_valid else "❌"
        console.print(f"{status} {message}")
        if is_valid:
            console.print(f"   [dim]Normalized: {normalized}[/dim]")
        console.print(f"   [dim]Original: {url[:60]}...[/dim]\n")

def example_configuration():
    """Example: How to manage configuration"""
    console.print("\n⚙️ [bold]Configuration Examples[/bold]\n")
    
    # Load current configuration
    config = load_config()
    console.print("Current configuration:")
    for key, value in config.items():
        console.print(f"  {key}: {value}")
    
    # Create a custom configuration
    custom_config = {
        "audio_format": "mp3",
        "audio_quality": "320",  # High quality
        "output_base": str(Path.home() / "Music" / "Downloaded"),
        "generate_m3u": True
    }
    
    console.print("\nCustom configuration example:")
    for key, value in custom_config.items():
        console.print(f"  {key}: {value}")
    
    # Note: This is just an example - we won't actually save it
    console.print("\n[dim]Use save_config(custom_config) to save this configuration[/dim]")

def example_usb_detection():
    """Example: How to detect USB drives"""
    console.print("\n💾 [bold]USB Detection Example[/bold]\n")
    
    # Get default output folder
    default_folder = Path.cwd() / "downloads"
    
    # This would show the USB detection dialog
    console.print(f"Default folder: {default_folder}")
    console.print("[dim]Call auto_choose_output_folder(default_folder) to show USB detection[/dim]")

def example_cli_commands():
    """Example: Common CLI command patterns"""
    console.print("\n🖥️ [bold]CLI Command Examples[/bold]\n")
    
    commands = [
        # Basic download
        "python download_playlist.py download \"https://music.youtube.com/playlist?list=PLxxxxx\"",
        
        # Download with custom output
        "python download_playlist.py download --output \"/path/to/usb\" \"https://music.youtube.com/playlist?list=PLxxxxx\"",
        
        # Multiple playlists
        "python download_playlist.py download \"https://music.youtube.com/playlist?list=PLxxxxx\" \"https://music.youtube.com/playlist?list=PLyyyyy\"",
        
        # Interactive configuration
        "python download_playlist.py config --interactive",
        
        # Set specific options
        "python download_playlist.py config --set-quality 320",
        "python download_playlist.py config --set-format mp3",
        "python download_playlist.py config --set-output \"/my/usb/drive\"",
        
        # Utility commands
        "python download_playlist.py dedup",  # Find duplicates
        "python download_playlist.py stats",  # Show statistics
        "python download_playlist.py about",  # About info
        
        # Interactive mode (recommended)
        "python download_playlist.py",  # Shows interactive menu
    ]
    
    for cmd in commands:
        console.print(f"[cyan]${cmd}[/cyan]")
    
    console.print("\n[yellow]💡 Tip: Run without arguments for interactive mode![/yellow]")

def example_error_scenarios():
    """Example: Common error scenarios and how they're handled"""
    console.print("\n🛡️ [bold]Error Handling Examples[/bold]\n")
    
    scenarios = [
        {
            "scenario": "Copyright Claim (like Codiscos S.A.S.)",
            "result": "⏭️ Video skipped with reason: 'Copyright claim'",
            "behavior": "Continues with next song in playlist"
        },
        {
            "scenario": "Private Video",
            "result": "⏭️ Video skipped with reason: 'Video privado'",
            "behavior": "Continues with next song in playlist"
        },
        {
            "scenario": "Video Unavailable",
            "result": "⏭️ Video skipped with reason: 'Video no disponible'",
            "behavior": "Continues with next song in playlist"
        },
        {
            "scenario": "Geographic Restriction",
            "result": "⏭️ Video skipped with reason: 'Bloqueado geográficamente'",
            "behavior": "Continues with next song in playlist"
        },
        {
            "scenario": "Network Error",
            "result": "🔄 Retries automatically with backoff",
            "behavior": "Up to 2 retries, then marked as error"
        }
    ]
    
    for scenario in scenarios:
        console.print(f"[bold]{scenario['scenario']}:[/bold]")
        console.print(f"  Result: {scenario['result']}")
        console.print(f"  Behavior: {scenario['behavior']}\n")

def main():
    """Run all examples"""
    console.print("🎵 [bold blue]YT Music Downloader - Usage Examples[/bold blue]")
    console.print("This demonstrates common usage patterns and features.\n")
    
    try:
        example_url_validation()
        example_configuration()
        example_usb_detection()
        example_cli_commands()
        example_error_scenarios()
        
        console.print("\n✨ [bold green]Examples completed![/bold green]")
        console.print("\n📚 For more information:")
        console.print("  • Run [cyan]python download_playlist.py --help[/cyan] for CLI help")
        console.print("  • Run [cyan]python download_playlist.py[/cyan] for interactive mode")
        console.print("  • Check README.md for detailed documentation")
        
    except Exception as e:
        console.print(f"\n❌ [bold red]Error running examples:[/bold red] {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())