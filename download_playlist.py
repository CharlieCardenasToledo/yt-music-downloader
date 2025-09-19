#!/usr/bin/env python3
"""
YouTube / YouTube Music – Downloader por PLAYLIST con menú, progreso por pistas y deduplicación (car-friendly)

• Progreso por cantidad de playlists y por cantidad de canciones de cada playlist
• MP3 CBR 192 kbps @ 44.1 kHz + ID3v2.3 (compatible con autoradios)
• Nombres seguros sin acentos/raros (mejor para USB/FAT y radios)
• Auto-USB (Windows API) + selector manual
• Deduplicación por hash de audio + listas .m3u por carpeta
"""

from __future__ import annotations

import os
import re
import sys
import json
import shutil
import platform
import hashlib
import ctypes
import string
import unicodedata
import time
import socket
import signal
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any, Tuple
from functools import wraps

import typer
from typer import Option, Argument
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    TimeRemainingColumn,
    SpinnerColumn,
    TransferSpeedColumn,
)
from rich.align import Align
from rich.columns import Columns
from rich import box
import psutil
import yt_dlp

app = typer.Typer(add_completion=False, no_args_is_help=False)
console = Console()

CONFIG_PATH = Path.home() / ".ytmusic-dl.json"
STATE_PATH = Path.home() / ".ytmusic-dl-state.json"
DEFAULT_OPTS = {
    "audio_format": "mp3",
    "audio_quality": "192",
    "output_base": str((Path.cwd() / "downloads").resolve()),
    "generate_m3u": True,
    "auto_resume": True,
    "connectivity_check": True,
}

# Estados de descarga
class DownloadState:
    PENDING = "pending"
    DOWNLOADING = "downloading"
    COMPLETED = "completed"
    PAUSED = "paused"
    ERROR = "error"
    SKIPPED = "skipped"

YTM_PLAYLIST_RE = re.compile(r"^https?://(music\.)?youtube\.com/playlist\?list=", re.IGNORECASE)
YT_PLAYLIST_RE = re.compile(r"^https?://(www\.)?youtube\.com/playlist\?list=", re.IGNORECASE)

# ---------------------- Control de conectividad y pausa ----------------------

class DownloadController:
    """Controlador para pausar/reanudar descargas y verificar conectividad."""
    
    def __init__(self):
        self.paused = False
        self.should_stop = False
        self._pause_event = threading.Event()
        self._pause_event.set()  # Inicialmente no pausado
        
    def pause(self):
        """Pausa las descargas."""
        self.paused = True
        self._pause_event.clear()
        console.print("[yellow]⏸️ Descarga pausada por el usuario[/yellow]")
        
    def resume(self):
        """Reanuda las descargas."""
        self.paused = False
        self._pause_event.set()
        console.print("[green]▶️ Descarga reanudada[/green]")
        
    def stop(self):
        """Detiene completamente las descargas."""
        self.should_stop = True
        self._pause_event.set()  # Permitir que continúe para que pueda detenerse
        console.print("[red]⏹️ Deteniendo descarga...[/red]")
        
    def wait_if_paused(self):
        """Espera si está pausado o retorna si debe detenerse."""
        if self.should_stop:
            return False
        if self.paused:
            console.print("[yellow]⏸️ Descarga pausada. Presiona 'r' para reanudar o 's' para detener.[/yellow]")
        self._pause_event.wait()
        return not self.should_stop
        
    def is_running(self):
        """Verifica si la descarga debe continuar."""
        return not self.should_stop and self.wait_if_paused()

# Instancia global del controlador
download_controller = DownloadController()

def check_internet_connection(timeout: int = 5) -> bool:
    """Verifica la conectividad a internet."""
    try:
        # Intentar conectar a DNS público de Google
        socket.create_connection(("8.8.8.8", 53), timeout)
        return True
    except (socket.timeout, socket.gaierror, OSError):
        try:
            # Intentar con DNS de Cloudflare como backup
            socket.create_connection(("1.1.1.1", 53), timeout)
            return True
        except (socket.timeout, socket.gaierror, OSError):
            return False

def wait_for_internet_connection(max_wait_time: int = 300) -> bool:
    """Espera hasta que se restablezca la conexión a internet."""
    start_time = time.time()
    check_interval = 5  # segundos
    
    while time.time() - start_time < max_wait_time:
        if check_internet_connection():
            console.print("[green]✅ Conexión a internet restablecida[/green]")
            return True
            
        elapsed = int(time.time() - start_time)
        remaining = max_wait_time - elapsed
        console.print(f"[yellow]🌐 Sin conexión. Reintentando en {check_interval}s... (quedan {remaining}s)[/yellow]")
        
        # Verificar si el usuario quiere pausar/detener durante la espera
        if not download_controller.is_running():
            return False
            
        time.sleep(check_interval)
    
    console.print("[red]❌ Tiempo de espera agotado. No se pudo restablecer la conexión.[/red]")
    return False

def setup_signal_handlers():
    """Configura manejadores de señales para pausar/reanudar."""
    def signal_handler(signum, frame):
        if signum == signal.SIGUSR1:  # Señal personalizada para pausar
            if download_controller.paused:
                download_controller.resume()
            else:
                download_controller.pause()
        elif signum == signal.SIGINT:  # Ctrl+C
            download_controller.stop()
            
    if platform.system() != "Windows":
        signal.signal(signal.SIGUSR1, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)

# ---------------------- Guardado y carga de estado ----------------------

def save_download_state(state_data: Dict[str, Any]) -> bool:
    """Guarda el estado actual de descarga."""
    try:
        STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Crear backup si existe
        if STATE_PATH.exists():
            backup_path = STATE_PATH.with_suffix('.json.backup')
            shutil.copy2(STATE_PATH, backup_path)
        
        # Agregar timestamp
        state_data["last_updated"] = time.time()
        state_data["version"] = "1.0"
        
        STATE_PATH.write_text(json.dumps(state_data, indent=2, ensure_ascii=False), encoding='utf-8')
        return True
        
    except Exception as e:
        console.print(f"[yellow]⚠️ Error guardando estado: {e}[/yellow]")
        return False

def load_download_state() -> Dict[str, Any]:
    """Carga el estado de descarga guardado."""
    if not STATE_PATH.exists():
        return {}
    
    try:
        content = STATE_PATH.read_text(encoding='utf-8')
        if not content.strip():
            return {}
            
        state = json.loads(content)
        if not isinstance(state, dict):
            return {}
            
        return state
        
    except (json.JSONDecodeError, OSError) as e:
        console.print(f"[yellow]⚠️ Error cargando estado: {e}[/yellow]")
        return {}

def clear_download_state() -> bool:
    """Limpia el estado de descarga guardado."""
    try:
        if STATE_PATH.exists():
            STATE_PATH.unlink()
        return True
    except Exception as e:
        console.print(f"[yellow]⚠️ Error limpiando estado: {e}[/yellow]")
        return False

def should_resume_download() -> bool:
    """Verifica si hay una descarga pendiente de reanudar."""
    state = load_download_state()
    if not state:
        return False
        
    # Verificar si hay playlists pendientes o en progreso
    playlists = state.get("playlists", {})
    for playlist_data in playlists.values():
        tracks = playlist_data.get("tracks", {})
        for track_data in tracks.values():
            if track_data.get("status") in [DownloadState.PENDING, DownloadState.DOWNLOADING, DownloadState.PAUSED]:
                return True
    return False

# ---------------------- Decoradores y Utilidades ----------------------

def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """Decorador para reintentar funciones que pueden fallar."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    if attempt == max_retries - 1:
                        raise
                    console.print(f"[yellow]Intento {attempt + 1} falló: {e}. Reintentando en {delay}s...[/yellow]")
                    time.sleep(delay)
                    delay *= backoff
            return None
        return wrapper
    return decorator

def safe_path_join(base: Path, *parts: str) -> Path:
    """Une rutas de forma segura previniendo path traversal."""
    result = base
    for part in parts:
        # Sanitizar cada parte
        safe_part = re.sub(r'[<>:"|?*]', '_', part)
        safe_part = safe_part.replace('..', '_')
        result = result / safe_part
    
    # Verificar que el resultado está dentro del directorio base
    try:
        result.resolve().relative_to(base.resolve())
        return result
    except ValueError:
        raise ValueError(f"Ruta insegura detectada: {result}")

# ---------------------- Config ----------------------

def load_config() -> Dict[str, Any]:
    """Carga configuración con manejo robusto de errores."""
    if not CONFIG_PATH.exists():
        return DEFAULT_OPTS.copy()
    
    try:
        content = CONFIG_PATH.read_text(encoding='utf-8')
        if not content.strip():
            console.print("[yellow]Archivo de configuración vacío, usando valores por defecto[/yellow]")
            return DEFAULT_OPTS.copy()
            
        loaded = json.loads(content)
        if not isinstance(loaded, dict):
            raise ValueError("Configuración debe ser un objeto JSON")
            
        return {**DEFAULT_OPTS, **loaded}
        
    except json.JSONDecodeError as e:
        console.print(f"[red]Error en formato JSON del config:[/red] {e}")
        if Confirm.ask("¿Restaurar configuración por defecto?", default=True):
            save_config(DEFAULT_OPTS)
            return DEFAULT_OPTS.copy()
        console.print("[red]No se puede continuar con configuración inválida[/red]")
        sys.exit(1)
        
    except (OSError, PermissionError) as e:
        console.print(f"[red]Error accediendo al archivo de config:[/red] {e}")
        console.print("[yellow]Usando configuración por defecto[/yellow]")
        return DEFAULT_OPTS.copy()
        
    except Exception as e:
        console.print(f"[red]Error inesperado cargando config:[/red] {e}")
        return DEFAULT_OPTS.copy()

def save_config(cfg: Dict[str, Any]) -> bool:
    """Guarda configuración con validación y manejo de errores."""
    if not isinstance(cfg, dict):
        console.print("[red]Error: configuración debe ser un diccionario[/red]")
        return False
        
    try:
        # Validar que la carpeta padre existe
        CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
        
        # Crear backup si existe
        if CONFIG_PATH.exists():
            backup_path = CONFIG_PATH.with_suffix('.json.backup')
            shutil.copy2(CONFIG_PATH, backup_path)
        
        # Escribir nueva configuración
        CONFIG_PATH.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding='utf-8')
        console.print("[green]✅ Configuración guardada correctamente[/green]")
        return True
        
    except (OSError, PermissionError) as e:
        console.print(f"[red]Error guardando configuración:[/red] {e}")
        return False
    except Exception as e:
        console.print(f"[red]Error inesperado guardando config:[/red] {e}")
        return False

# ---------------------- Dependencias ----------------------

def which_ffmpeg() -> Optional[str]:
    return shutil.which("ffmpeg")

def check_dependencies_panel() -> Panel:
    ff = which_ffmpeg()
    status_ff = "[green]OK[/green]" if ff else "[red]FALTA[/red]"
    yt_ver = getattr(yt_dlp, "version", None)
    yt_ver_str = getattr(yt_ver, "__version__", None) or "(desconocido)"
    body = (
        f"ffmpeg: {status_ff} [dim]{ff or 'no encontrado en PATH'}[/dim]\n"
        f"yt-dlp: [green]{yt_ver_str}[/green]\n"
        f"Python: [cyan]{platform.python_version()}[/cyan]\n"
        f"Sistema: [cyan]{platform.system()} {platform.release()}[/cyan]"
    )
    return Panel(body, title="Chequeo de dependencias", border_style="magenta")

# ---------------------- Detección de USB ----------------------

def human_os() -> str:
    return {
        "Windows": "Windows",
        "Darwin": "macOS",
        "Linux": "Linux",
    }.get(platform.system(), platform.system())

def candidate_removable_paths() -> List[Path]:
    """
    Detecta unidades/montajes removibles.
    - Windows: usa GetDriveTypeW (DRIVE_REMOVABLE = 2), luego fallback psutil
    - macOS/Linux: psutil + raíces comunes
    """
    candidates: List[Path] = []
    sysname = platform.system()

    if sysname == "Windows":
        # API nativa
        try:
            DRIVE_REMOVABLE = 2
            GetDriveTypeW = ctypes.windll.kernel32.GetDriveTypeW
            for letter in string.ascii_uppercase:
                root = f"{letter}:\\"
                dtype = GetDriveTypeW(ctypes.c_wchar_p(root))
                if dtype == DRIVE_REMOVABLE:
                    candidates.append(Path(root))
        except Exception:
            pass
        # Fallback psutil (sin C:)
        try:
            for p in psutil.disk_partitions(all=False):
                mount = Path(p.mountpoint)
                if p.fstype and re.match(r"^(FAT|exFAT|NTFS)$", p.fstype, re.I):
                    if not str(mount).upper().startswith("C:"):
                        if mount not in candidates:
                            candidates.append(mount)
        except Exception:
            pass
        return candidates

    # macOS / Linux
    try:
        for p in psutil.disk_partitions(all=False):
            if any(s in p.mountpoint for s in ["/media/", "/mnt/", "/run/media/", "/Volumes/"]):
                candidates.append(Path(p.mountpoint))
    except Exception:
        pass
    for root in ["/media", "/mnt", "/run/media", "/Volumes"]:
        d = Path(root)
        if d.exists():
            for child in d.iterdir():
                if child.is_dir():
                    candidates.append(child)
    # de-dup
    seen = set()
    uniq: List[Path] = []
    for c in candidates:
        s = str(c)
        if s not in seen:
            seen.add(s)
            uniq.append(c)
    return uniq

def choose_output_folder(default_base: Path) -> Path:
    console.print(Panel.fit("Elige carpeta de salida (donde está montada tu USB)."))
    candidates = candidate_removable_paths()
    rows = []
    for idx, c in enumerate(candidates, 1):
        rows.append((idx, str(c)))
    if rows:
        table = Table(title="Montajes detectados", expand=False, box=box.SIMPLE_HEAVY)
        table.add_column("#", justify="right")
        table.add_column("Ruta")
        for idx, path in rows:
            table.add_row(str(idx), path)
        console.print(table)
    console.print("[dim]Enter acepta el valor por defecto, o escribe un número o ruta personalizada.[/dim]")
    default_str = str(default_base)
    choice = Prompt.ask("Carpeta de salida", default=default_str)
    if choice.isdigit() and rows:
        i = int(choice)
        for idx, path in rows:
            if idx == i:
                return Path(path)
    return Path(choice).expanduser()

def auto_choose_output_folder(default_base: Path) -> Path:
    """Detecta automáticamente una posible USB y pide confirmación. Si no, ofrece selector manual."""
    candidates = candidate_removable_paths()
    preferred = candidates[0] if candidates else None
    if preferred:
        if Confirm.ask(f"Se detectó una unidad/montaje: [bold]{preferred}[/bold]\n¿Quieres guardar ahí?", default=True):
            return Path(preferred)
        return choose_output_folder(default_base)
    console.print(Panel.fit("No se detectó USB automáticamente. Selecciona una carpeta.", border_style="yellow"))
    return choose_output_folder(default_base)

# ---------------------- Organización y nombres seguros ----------------------

SAFE_MAX_NAME = 60

def strip_accents(s: str) -> str:
    # NFKD + elimina diacríticos → USB/autoradios más felices
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))

def safe_name(s: str, default: str = "Playlist") -> str:
    if not s:
        return default
    s = strip_accents(s.strip())
    if not s:
        return default
    # Restringir a nombres amigables para FAT/Windows
    s = re.sub(r"[\\/:*?\"<>|]+", "_", s)
    # Espacios raros y comillas curvas
    s = s.replace("“", "").replace("”", "").replace("’", "'")
    s = re.sub(r"\s+", " ", s).strip()
    if len(s) > SAFE_MAX_NAME:
        s = s[:SAFE_MAX_NAME].rstrip()
    return s or default

def validate_playlist_url(url: str) -> Tuple[bool, str, str]:
    """Valida una URL de playlist con feedback específico.
    
    Returns:
        Tuple[bool, str, str]: (es_válida, mensaje_error, url_normalizada)
    """
    if not url or not url.strip():
        return False, "URL vacía", ""
    
    url = url.strip()
    
    # Verificar formato básico de URL
    if not re.match(r'^https?://', url, re.IGNORECASE):
        return False, "URL debe comenzar con http:// o https://", url
    
    # Verificar dominio YouTube
    if not re.search(r'(music\.)?youtube\.com', url, re.IGNORECASE):
        return False, "Solo se admiten URLs de YouTube/YouTube Music", url
    
    # Verificar que sea una playlist
    if 'list=' not in url:
        return False, "URL debe contener un parámetro 'list=' (playlist)", url
    
    # Normalizar URL (remover parámetros innecesarios)
    list_match = re.search(r'list=([a-zA-Z0-9_-]+)', url)
    if list_match:
        playlist_id = list_match.group(1)
        if 'music.youtube.com' in url.lower():
            normalized_url = f"https://music.youtube.com/playlist?list={playlist_id}"
        else:
            normalized_url = f"https://www.youtube.com/playlist?list={playlist_id}"
        return True, "URL válida", normalized_url
    
    return False, "No se pudo extraer ID de playlist", url

def validate_urls_enhanced(urls: List[str]) -> Tuple[List[str], List[Tuple[str, str]]]:
    """Valida URLs con reporte detallado de errores.
    
    Returns:
        Tuple[List[str], List[Tuple[str, str]]]: (urls_válidas, errores)
    """
    valid = []
    errors = []
    
    for i, url in enumerate(urls, 1):
        is_valid, message, normalized_url = validate_playlist_url(url)
        if is_valid:
            valid.append(normalized_url)
        else:
            error_msg = f"URL {i}: {message}"
            errors.append((error_msg, url[:80] + "..." if len(url) > 80 else url))
    
    return valid, errors

def validate_urls(urls: List[str]) -> List[str]:
    """Función de compatibilidad - valida URLs y muestra errores."""
    valid, errors = validate_urls_enhanced(urls)
    
    if errors:
        console.print("\n[yellow]⚠️ URLs con problemas encontradas:[/yellow]")
        error_table = Table(title="Errores de Validación", show_header=True, box=box.ROUNDED)
        error_table.add_column("Error", style="red")
        error_table.add_column("URL", style="dim")
        
        for error_msg, url in errors:
            error_table.add_row(error_msg, url)
        
        console.print(error_table)
        console.print(f"\n[green]✅ URLs válidas encontradas: {len(valid)}[/green]")
    
    return valid

# ---------------------- yt-dlp opciones ----------------------

class QuietLogger:
    """Silencia logs internos de yt-dlp para una experiencia más limpia."""
    def debug(self, msg):   pass
    def info(self, msg):    pass
    def warning(self, msg): pass
    def error(self, msg):   console.print(f"[red]{msg}[/red]")

def build_ydl_opts_for_playlist(output_dir: Path, audio_format: str, audio_quality: str) -> Dict[str, Any]:
    """
    Crea opciones de yt-dlp que guardan DIRECTO en la carpeta de la playlist.
    """
    outtmpl = str(output_dir / "%(title)s.%(ext)s")
    return {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "yes_playlist": False,     # vamos a descargar por-ítem manualmente
        "ignoreerrors": "only_download",  # salta errores por ítem
        "noplaylist": True,

        # Archivos y nombres compatibles con USB/FAT32/Windows
        "paths": {"home": str(output_dir)},
        "windowsfilenames": True,
        "restrictfilenames": True,
        "trim_file_name": SAFE_MAX_NAME,

        # Miniatura embebida (si tu estéreo falla, cambia a False)
        "writethumbnail": True,
        "embedthumbnail": True,

        # Silencio de consola de yt-dlp (mantenemos nuestros mensajes)
        "quiet": True,
        "logger": QuietLogger(),
        "noprogress": True,
        "no_warnings": True,
        "prefer_ffmpeg": True,

        # Post-procesado: MP3 CBR 192 kbps @ 44.1 kHz + ID3v2.3
        "postprocessors": [
            {"key": "FFmpegExtractAudio", "preferredcodec": audio_format, "preferredquality": audio_quality},
            {"key": "FFmpegMetadata", "add_metadata": True},
        ],
        "postprocessor_args": [
            "-codec:a", "libmp3lame",
            "-b:a", "192k",
            "-ar", "44100",
            "-write_id3v2", "1",
            "-id3v2_version", "3",
            "-map_metadata", "0",
        ],

        # Robustez
        "retries": 5,
        "fragment_retries": 5,
        "concurrent_fragments": 5,
        "skip_unavailable_fragments": True,
    }

# ---------------------- Deduplicación ----------------------

def _synchsafe_to_int(b: bytes) -> int:
    return ((b[0] & 0x7F) << 21) | ((b[1] & 0x7F) << 14) | ((b[2] & 0x7F) << 7) | (b[3] & 0x7F)

def mp3_audio_hash(path: Path, chunk_size: int = 1024 * 1024) -> Optional[str]:
    """MD5 del flujo de audio MP3 ignorando etiquetas ID3v2/ID3v1."""
    try:
        size = path.stat().st_size
        if size <= 0:
            return None
        start = 0
        end = size
        with path.open("rb") as f:
            header = f.read(10)
            if len(header) == 10 and header[:3] == b"ID3":
                tag_size = _synchsafe_to_int(header[6:10])
                start = 10 + tag_size
            if size >= 128:
                f.seek(-128, os.SEEK_END)
                if f.read(3) == b"TAG":
                    end = size - 128
            hasher = hashlib.md5()
            f.seek(start)
            remaining = max(0, end - start)
            while remaining > 0:
                to_read = min(chunk_size, remaining)
                chunk = f.read(to_read)
                if not chunk:
                    break
                hasher.update(chunk)
                remaining -= len(chunk)
            return hasher.hexdigest()
    except Exception:
        return None

def scan_duplicates(base: Path) -> Tuple[int, List[Tuple[Path, List[Path]]]]:
    files = list(base.glob("*/*.mp3"))
    by_hash: Dict[str, List[Path]] = {}
    for p in files:
        h = mp3_audio_hash(p)
        if not h:
            h = f"NAME::{p.name.lower()}"
        by_hash.setdefault(h, []).append(p)

    duplicates: List[Tuple[Path, List[Path]]] = []
    for _, paths in by_hash.items():
        if len(paths) > 1:
            paths_sorted = sorted(paths, key=lambda x: (x.stat().st_mtime, len(str(x))))
            keep = paths_sorted[0]
            dups = paths_sorted[1:]
            duplicates.append((keep, dups))
    return (len(files), duplicates)

def handle_duplicates(base: Path, move_to_folder: str = "_duplicates") -> int:
    """Maneja duplicados con interfaz mejorada y manejo de errores."""
    
    try:
        console.print("🔍 [bold]Escaneando archivos...[/bold]")
        total, dups = scan_duplicates(base)
        
        if not dups:
            console.print(Panel(
                f"✅ [bold green]No se encontraron duplicados[/bold green]\n"
                f"📊 Total de archivos escaneados: [bold]{total}[/bold]",
                title="🔍 Resultado del Escaneo",
                border_style="green"
            ))
            return 0

        # Mostrar duplicados encontrados
        console.print(f"\n[yellow]⚠️ Se encontraron {len(dups)} grupos de duplicados[/yellow]\n")
        
        table = Table(title="🔍 Duplicados Detectados", box=box.ROUNDED)
        table.add_column("Conservar", style="green")
        table.add_column("Mover duplicados", style="yellow")
        
        for keep, extras in dups:
            extras_text = "\n".join(f"• {e.name}" for e in extras)
            table.add_row(f"✅ {keep.name}", extras_text)
        
        console.print(table)
        
        # Estadísticas
        total_duplicates = sum(len(extras) for _, extras in dups)
        console.print(f"\n📊 [bold]Estadísticas:[/bold]")
        console.print(f"  • Archivos únicos a conservar: [green]{len(dups)}[/green]")
        console.print(f"  • Archivos duplicados a mover: [yellow]{total_duplicates}[/yellow]")

        target = base / move_to_folder
        
        if not Confirm.ask(f"\n🗂️ ¿Mover duplicados a '{target}'?", default=True):
            console.print("[dim]No se realizaron cambios.[/dim]")
            return 0
        
        # Crear carpeta de destino
        try:
            target.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            console.print(f"[red]❌ Error creando carpeta '{target}': {e}[/red]")
            return 0
        
        # Mover archivos con progreso
        moved = 0
        errors = 0
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]🗂️ Moviendo duplicados..."),
            BarColumn(),
            TextColumn("{task.completed}/{task.total}"),
        ) as progress:
            
            task = progress.add_task("Moviendo", total=total_duplicates)
            
            for keep, extras in dups:
                for e in extras:
                    try:
                        # Generar nombre único en destino
                        dest = target / e.name
                        i = 1
                        while dest.exists():
                            dest = target / f"{dest.stem} ({i}){dest.suffix}"
                            i += 1
                        
                        shutil.move(str(e), str(dest))
                        moved += 1
                        progress.console.print(f"[green]✅ Movido: {e.name}[/green]")
                        
                    except Exception as ex:
                        errors += 1
                        progress.console.print(f"[red]❌ Error moviendo {e.name}: {ex}[/red]")
                    finally:
                        progress.advance(task)
        
        # Resumen final
        if moved > 0:
            console.print(Panel(
                f"✅ [bold green]Operación completada[/bold green]\n"
                f"📁 Archivos movidos: [bold]{moved}[/bold]\n"
                f"📂 Destino: [bold]{target}[/bold]" + 
                (f"\n❌ Errores: [bold red]{errors}[/bold red]" if errors > 0 else ""),
                title="🗂️ Resultado",
                border_style="green" if errors == 0 else "yellow"
            ))
        
        return moved
        
    except Exception as e:
        console.print(f"[red]❌ Error procesando duplicados: {e}[/red]")
        return 0

# ---------------------- M3U mejorado con enlace global ----------------------

def update_global_m3u(base_path: Path, playlist_dir: Path, playlist_title: str):
    """Actualiza o crea un archivo M3U global que enlaza todas las playlists."""
    try:
        global_m3u = base_path / "all_playlists.m3u"
        playlist_m3u = playlist_dir / f"{playlist_dir.name}.m3u"
        
        # Leer el M3U global existente si existe
        existing_entries = set()
        if global_m3u.exists():
            try:
                existing_content = global_m3u.read_text(encoding='utf-8', errors='ignore')
                existing_entries = set(line.strip() for line in existing_content.splitlines() if line.strip())
            except Exception:
                pass
        
        # Agregar entrada para esta playlist si no existe
        playlist_entry = f"{playlist_dir.name}/{playlist_dir.name}.m3u"
        if playlist_entry not in existing_entries and playlist_m3u.exists():
            existing_entries.add(playlist_entry)
            
            # Escribir M3U global actualizado
            sorted_entries = sorted(existing_entries)
            global_content = "\n".join(sorted_entries)
            global_m3u.write_text(global_content, encoding='utf-8', errors='ignore')
            
            console.print(f"[green]📝 M3U global actualizado con '{playlist_title}'[/green]")
            
    except Exception as e:
        console.print(f"[yellow]⚠️ Error actualizando M3U global: {e}[/yellow]")

def create_master_m3u(base_path: Path):
    """Crea un archivo M3U maestro que incluye todas las canciones de todas las playlists."""
    try:
        master_m3u = base_path / "todas_las_canciones.m3u"
        all_songs = []
        
        # Recopilar todas las canciones de todas las carpetas
        for playlist_dir in sorted(base_path.iterdir()):
            if playlist_dir.is_dir() and not playlist_dir.name.startswith("_"):
                mp3_files = sorted(playlist_dir.glob("*.mp3"))
                for mp3_file in mp3_files:
                    # Ruta relativa desde el archivo M3U maestro
                    relative_path = f"{playlist_dir.name}/{mp3_file.name}"
                    all_songs.append(relative_path)
        
        if all_songs:
            # Crear contenido con metadatos
            content = "#EXTM3U\n"
            content += f"#EXTINF:-1,Todas las canciones ({len(all_songs)} tracks)\n"
            content += "\n".join(all_songs)
            
            master_m3u.write_text(content, encoding='utf-8', errors='ignore')
            console.print(f"[green]🎵 M3U maestro creado con {len(all_songs)} canciones[/green]")
            
    except Exception as e:
        console.print(f"[yellow]⚠️ Error creando M3U maestro: {e}[/yellow]")

def update_all_m3u_files(base_path: Path):
    """Actualiza todos los archivos M3U después de una descarga completa."""
    try:
        console.print("[cyan]📝 Actualizando archivos M3U...[/cyan]")
        
        # Actualizar M3U individual de cada playlist
        write_all_m3u(base_path)
        
        # Crear M3U maestro con todas las canciones
        create_master_m3u(base_path)
        
        # Crear M3U de índice de playlists
        create_playlist_index_m3u(base_path)
        
        console.print("[green]✅ Todos los archivos M3U actualizados[/green]")
        
    except Exception as e:
        console.print(f"[yellow]⚠️ Error actualizando M3U: {e}[/yellow]")

def create_playlist_index_m3u(base_path: Path):
    """Crea un índice M3U que lista todas las playlists disponibles."""
    try:
        index_m3u = base_path / "indice_playlists.m3u"
        playlists = []
        
        # Encontrar todas las carpetas de playlists
        for playlist_dir in sorted(base_path.iterdir()):
            if playlist_dir.is_dir() and not playlist_dir.name.startswith("_"):
                playlist_m3u = playlist_dir / f"{playlist_dir.name}.m3u"
                if playlist_m3u.exists():
                    # Contar canciones en la playlist
                    mp3_count = len(list(playlist_dir.glob("*.mp3")))
                    if mp3_count > 0:
                        playlists.append((playlist_dir.name, mp3_count, f"{playlist_dir.name}/{playlist_dir.name}.m3u"))
        
        if playlists:
            content = "#EXTM3U\n"
            content += "#PLAYLIST:INDICE DE PLAYLISTS\n"
            
            for playlist_name, count, path in playlists:
                content += f"#EXTINF:-1,{playlist_name} ({count} canciones)\n"
                content += f"{path}\n"
            
            index_m3u.write_text(content, encoding='utf-8', errors='ignore')
            console.print(f"[green]📁 Índice de playlists creado con {len(playlists)} playlists[/green]")
            
    except Exception as e:
        console.print(f"[yellow]⚠️ Error creando índice de playlists: {e}[/yellow]")

# ---------------------- Playlists .m3u ----------------------

def write_m3u_for_dir(folder: Path):
    """Escribe un archivo M3U mejorado para una carpeta con metadatos."""
    mp3s = sorted([p for p in folder.glob("*.mp3") if p.is_file()])
    if not mp3s:
        return
    
    m3u_path = folder / f"{folder.name}.m3u"
    try:
        # Crear contenido M3U con metadatos
        content = "#EXTM3U\n"
        content += f"#PLAYLIST:{folder.name}\n"
        
        for mp3_file in mp3s:
            # Agregar metadatos básicos (duración estimada y nombre)
            content += f"#EXTINF:-1,{mp3_file.stem}\n"
            content += f"{mp3_file.name}\n"
        
        m3u_path.write_text(content, encoding="utf-8", errors="ignore")
        
    except Exception as e:
        console.print(f"[yellow]No se pudo escribir {m3u_path}: {e}[/yellow]")

def write_all_m3u(base: Path):
    """Escribe archivos M3U para todas las carpetas de playlists."""
    for d in sorted(base.iterdir()):
        if d.is_dir() and d.name not in {"_duplicates"}:
            write_m3u_for_dir(d)

# ---------------------- Utilidades ----------------------

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)

# ---------------------- Sistema de Progreso Mejorado ----------------------

def create_enhanced_progress() -> Progress:
    """Crea barra de progreso con más información."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(bar_width=40),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TextColumn("•"),
        TextColumn("{task.completed}/{task.total}"),
        TextColumn("•"),
        TimeRemainingColumn(),
        TextColumn("•"),
        TransferSpeedColumn(),
        console=console,
        transient=False
    )

def show_download_dashboard(base_path: Path, urls: List[str], cfg: Dict[str, Any]) -> None:
    """Muestra dashboard antes de iniciar descarga."""
    
    # Verificar ffmpeg
    ffmpeg_status = "✅ Disponible" if which_ffmpeg() else "❌ Falta"
    ffmpeg_style = "green" if which_ffmpeg() else "red"
    
    # Panel de información del sistema
    system_info = Panel(
        f"🖥️  Sistema: [bold]{human_os()}[/bold]\n"
        f"📁 Carpeta: [bold]{base_path}[/bold]\n"
        f"🎵 Playlists: [bold]{len(urls)}[/bold]\n"
        f"⚙️  ffmpeg: [{ffmpeg_style}]{ffmpeg_status}[/{ffmpeg_style}]\n"
        f"🎶 Formato: [bold]{cfg['audio_format']}[/bold] @ [bold]{cfg['audio_quality']}[/bold] kbps\n"
        f"📝 Generar M3U: [bold]{'✅ Sí' if cfg.get('generate_m3u', True) else '❌ No'}[/bold]",
        title="📊 Información del Sistema",
        border_style="cyan"
    )
    
    # Panel de URLs
    url_table = Table(title="🎵 Playlists a Descargar", show_header=True, box=box.ROUNDED)
    url_table.add_column("#", style="cyan", width=3)
    url_table.add_column("URL", style="blue")
    url_table.add_column("Estado", style="green", width=12)
    
    for i, url in enumerate(urls, 1):
        display_url = url[:60] + "..." if len(url) > 60 else url
        url_table.add_row(str(i), display_url, "✅ Válida")
    
    console.print("\n")
    console.print(Columns([system_info, url_table]))
    console.print("\n")

def check_system_resources(base_path: Path, estimated_downloads: int) -> bool:
    """Verifica que hay suficientes recursos del sistema."""
    
    try:
        # Verificar espacio en disco
        free_space = shutil.disk_usage(base_path).free
        estimated_size = estimated_downloads * 5 * 1024 * 1024  # 5MB promedio por canción
        
        if free_space < estimated_size * 1.2:  # 20% de margen
            console.print(Panel(
                f"⚠️ Espacio en disco insuficiente\n"
                f"Disponible: [bold]{free_space // (1024**2):,} MB[/bold]\n"
                f"Estimado necesario: [bold]{estimated_size // (1024**2):,} MB[/bold]\n"
                f"Recomendado: [bold]{int(estimated_size * 1.2) // (1024**2):,} MB[/bold]",
                title="❌ Recursos Insuficientes",
                border_style="red"
            ))
            return False
        
        # Mostrar información de espacio disponible
        console.print(Panel(
            f"💾 Espacio disponible: [bold green]{free_space // (1024**2):,} MB[/bold green]\n"
            f"📊 Espacio estimado: [bold cyan]{estimated_size // (1024**2):,} MB[/bold cyan]\n"
            f"✅ Margen de seguridad: [bold]{((free_space - estimated_size) // (1024**2)):,} MB[/bold]",
            title="💽 Estado del Almacenamiento",
            border_style="green"
        ))
        
        return True
        
    except Exception as e:
        console.print(f"[yellow]No se pudo verificar espacio en disco: {e}[/yellow]")
        return True  # Continuar si no se puede verificar

def show_download_summary_enhanced(base_path: Path, downloaded: int, skipped: int, errors: int, unavailable_detected: int, start_time: float) -> None:
    """Muestra resumen de descarga con estadísticas completas incluyendo videos no disponibles."""
    
    try:
        # Calcular estadísticas
        total_files = sum(1 for _ in base_path.glob("**/*.mp3"))
        total_size = sum(f.stat().st_size for f in base_path.glob("**/*.mp3") if f.exists())
        total_size_mb = total_size / (1024 * 1024)
        
        # Tiempo transcurrido
        elapsed_time = time.time() - start_time
        elapsed_minutes = int(elapsed_time // 60)
        elapsed_seconds = int(elapsed_time % 60)
        
        # Panel de resultados mejorado
        results_table = Table(title="📊 Resumen de Descarga Completo", show_header=False, box=box.ROUNDED)
        results_table.add_column("Métrica", style="cyan", width=25)
        results_table.add_column("Valor", style="bold green")
        
        results_table.add_row("✅ Descargados exitosamente", str(downloaded))
        results_table.add_row("⏭️ Omitidos durante descarga", str(skipped))
        results_table.add_row("❌ Errores durante descarga", str(errors) if errors > 0 else "0")
        results_table.add_row("🚫 No disponibles detectados", str(unavailable_detected))
        results_table.add_row("📁 Total archivos MP3", str(total_files))
        results_table.add_row("💾 Tamaño total", f"{total_size_mb:.1f} MB")
        results_table.add_row("⏱️ Tiempo total", f"{elapsed_minutes}m {elapsed_seconds}s")
        
        if downloaded > 0:
            avg_time = elapsed_time / downloaded
            results_table.add_row("⚡ Promedio/canción", f"{avg_time:.1f}s")
        
        # Calcular totales
        total_processed = downloaded + skipped + errors + unavailable_detected
        results_table.add_row("🔢 Total procesados", str(total_processed))
        
        if total_processed > 0:
            success_rate = (downloaded / total_processed) * 100
            results_table.add_row("📈 Tasa de éxito", f"{success_rate:.1f}%")
        
        console.print("\n")
        console.print(results_table)
        
        # Alertas y consejos
        if unavailable_detected > 0:
            console.print(Panel(
                f"ℹ️ [bold cyan]{unavailable_detected}[/bold cyan] videos fueron detectados como no disponibles durante la lectura de playlists.\n"
                "Esto es normal y puede deberse a:\n"
                "• Videos eliminados por el usuario\n"
                "• Reclamos de derechos de autor (como Codiscos S.A.S.)\n"
                "• Videos privados o restringidos geográficamente\n"
                "• Content ID claims automáticos\n\n"
                "💡 [bold]Tip:[/bold] Estos videos se omiten automáticamente sin afectar el resto de la playlist.",
                title="ℹ️ Información",
                border_style="blue"
            ))
        
        if errors > 0:
            console.print(Panel(
                f"Se produjeron [bold red]{errors}[/bold red] errores durante la descarga de canciones individuales.\n"
                "Revisa los mensajes anteriores para más detalles.\n"
                "💡 Tip: Algunos videos pueden fallar por problemas temporales de red.",
                title="⚠️ Advertencia",
                border_style="yellow"
            ))
        
        if downloaded > 0:
            console.print(Panel(
                f"🎉 ¡Descarga completada exitosamente!\n"
                f"📂 Los archivos están en: [bold]{base_path}[/bold]\n"
                f"🎵 Total de canciones descargadas: [bold green]{downloaded}[/bold green]\n"
                f"🎶 Formato: MP3 CBR 192 kbps @ 44.1 kHz (ideal para autos)",
                title="✅ Éxito",
                border_style="green"
            ))
        elif total_processed > 0:
            console.print(Panel(
                f"⚠️ No se descargaron archivos nuevos.\n"
                f"Esto puede deberse a que:\n"
                f"• Los archivos ya existen en el destino\n"
                f"• Todos los videos estaban no disponibles\n"
                f"• Problemas de conectividad\n\n"
                f"📊 Total videos procesados: {total_processed}",
                title="ℹ️ Información",
                border_style="yellow"
            ))
            
    except Exception as e:
        console.print(f"[yellow]Error generando estadísticas: {e}[/yellow]")

def show_download_summary(base_path: Path, downloaded: int, skipped: int, errors: int, start_time: float) -> None:
    """Muestra resumen de descarga con estadísticas."""
    
    try:
        # Calcular estadísticas
        total_files = sum(1 for _ in base_path.glob("**/*.mp3"))
        total_size = sum(f.stat().st_size for f in base_path.glob("**/*.mp3") if f.exists())
        total_size_mb = total_size / (1024 * 1024)
        
        # Tiempo transcurrido
        elapsed_time = time.time() - start_time
        elapsed_minutes = int(elapsed_time // 60)
        elapsed_seconds = int(elapsed_time % 60)
        
        # Panel de resultados
        results_table = Table(title="📊 Resumen de Descarga", show_header=False, box=box.ROUNDED)
        results_table.add_column("Métrica", style="cyan", width=20)
        results_table.add_column("Valor", style="bold green")
        
        results_table.add_row("✅ Descargados", str(downloaded))
        results_table.add_row("⏭️ Omitidos", str(skipped))
        results_table.add_row("❌ Errores", str(errors) if errors > 0 else "0")
        results_table.add_row("📁 Total archivos", str(total_files))
        results_table.add_row("💾 Tamaño total", f"{total_size_mb:.1f} MB")
        results_table.add_row("⏱️ Tiempo total", f"{elapsed_minutes}m {elapsed_seconds}s")
        
        if downloaded > 0:
            avg_time = elapsed_time / downloaded
            results_table.add_row("⚡ Promedio/canción", f"{avg_time:.1f}s")
        
        console.print("\n")
        console.print(results_table)
        
        # Alertas adicionales
        if errors > 0:
            console.print(Panel(
                f"Se produjeron [bold red]{errors}[/bold red] errores durante la descarga.\n"
                "Revisa los mensajes anteriores para más detalles.\n"
                "💡 Tip: Algunos videos pueden no estar disponibles o ser privados.",
                title="⚠️ Advertencia",
                border_style="yellow"
            ))
        
        if downloaded > 0:
            console.print(Panel(
                f"🎉 ¡Descarga completada exitosamente!\n"
                f"📂 Los archivos están en: [bold]{base_path}[/bold]\n"
                f"🎵 Total de canciones: [bold green]{downloaded}[/bold green]",
                title="✅ Éxito",
                border_style="green"
            ))
            
    except Exception as e:
        console.print(f"[yellow]Error generando estadísticas: {e}[/yellow]")

# ---------------------- Flujo de descarga ----------------------

def interactive_config_setup() -> Dict[str, Any]:
    """Configuración interactiva paso a paso con validación."""
    
    console.print(Panel(
        "🔧 [bold]Configuración Interactiva[/bold]\n"
        "Te ayudamos a configurar la aplicación paso a paso",
        border_style="cyan"
    ))
    
    cfg = load_config()
    
    # 1. Carpeta de salida con validación
    console.print("\n[bold cyan]📁 Paso 1: Carpeta de Descarga[/bold cyan]")
    current_base = cfg.get("output_base", str(Path.cwd() / "downloads"))
    
    while True:
        console.print(f"\n💡 Carpeta actual: [bold]{current_base}[/bold]")
        
        choice = Prompt.ask(
            "¿Qué deseas hacer?",
            choices=["1", "2", "3"],
            default="1"
        )
        
        if choice == "1":  # Mantener actual
            new_base = current_base
            break
        elif choice == "2":  # Elegir manualmente
            new_base = Prompt.ask("📁 Nueva carpeta base", default=current_base)
        elif choice == "3":  # Auto-detectar USB
            usb_base = auto_choose_output_folder(Path(current_base))
            new_base = str(usb_base)
            break
        
        try:
            path = Path(new_base).expanduser().resolve()
            if not path.exists():
                if Confirm.ask(f"La carpeta no existe. ¿Crearla en {path}?", default=True):
                    path.mkdir(parents=True, exist_ok=True)
                    console.print(f"[green]✅ Carpeta creada: {path}[/green]")
                    break
                else:
                    continue
            else:
                console.print(f"[green]✅ Carpeta válida: {path}[/green]")
                new_base = str(path)
                break
        except Exception as e:
            console.print(f"[red]❌ Ruta inválida: {e}[/red]")
            continue
    
    # Mostrar opciones para carpeta
    console.print("\n[dim]1. Mantener actual[/dim]")
    console.print("[dim]2. Especificar manualmente[/dim]")
    console.print("[dim]3. Auto-detectar USB[/dim]")
    
    cfg["output_base"] = new_base
    
    # 2. Calidad de audio con explicación
    console.print("\n[bold cyan]🎵 Paso 2: Calidad de Audio[/bold cyan]")
    quality_options = {
        "1": ("128", "Calidad estándar - archivos más pequeños (~3MB/canción)"),
        "2": ("192", "Calidad alta - recomendado para autos (~4.5MB/canción)"),
        "3": ("256", "Calidad muy alta - excelente sonido (~6MB/canción)"),
        "4": ("320", "Calidad máxima - archivos más grandes (~7.5MB/canción)")
    }
    
    current_quality = cfg.get("audio_quality", "192")
    current_choice = "2"  # Default
    for k, (q, _) in quality_options.items():
        if q == current_quality:
            current_choice = k
            break
    
    console.print(f"\n💡 Calidad actual: [bold]{current_quality} kbps[/bold]\n")
    
    for key, (kbps, desc) in quality_options.items():
        style = "bold green" if key == current_choice else "dim"
        marker = "➤ " if key == current_choice else "  "
        console.print(f"[{style}]{marker}{key}. {kbps} kbps - {desc}[/{style}]")
    
    quality_choice = Prompt.ask(
        "\nSelecciona calidad de audio",
        choices=list(quality_options.keys()),
        default=current_choice
    )
    
    cfg["audio_quality"] = quality_options[quality_choice][0]
    
    # 3. Formato de audio
    console.print("\n[bold cyan]🎶 Paso 3: Formato de Audio[/bold cyan]")
    format_options = {
        "1": ("mp3", "MP3 - Compatible con todos los dispositivos"),
        "2": ("m4a", "M4A/AAC - Mejor calidad, compatible con Apple"),
        "3": ("opus", "Opus - Mejor compresión, dispositivos modernos")
    }
    
    current_format = cfg.get("audio_format", "mp3")
    current_fmt_choice = "1"
    for k, (f, _) in format_options.items():
        if f == current_format:
            current_fmt_choice = k
            break
    
    console.print(f"\n💡 Formato actual: [bold]{current_format.upper()}[/bold]\n")
    
    for key, (fmt, desc) in format_options.items():
        style = "bold green" if key == current_fmt_choice else "dim"
        marker = "➤ " if key == current_fmt_choice else "  "
        console.print(f"[{style}]{marker}{key}. {fmt.upper()} - {desc}[/{style}]")
    
    fmt_choice = Prompt.ask(
        "\nSelecciona formato de audio",
        choices=list(format_options.keys()),
        default=current_fmt_choice
    )
    
    cfg["audio_format"] = format_options[fmt_choice][0]
    
    # 4. Opciones adicionales
    console.print("\n[bold cyan]⚙️ Paso 4: Opciones Adicionales[/bold cyan]")
    
    cfg["generate_m3u"] = Confirm.ask(
        "📝 ¿Generar archivos .m3u (listas de reproducción)?",
        default=cfg.get("generate_m3u", True)
    )
    
    # Guardar configuración
    if save_config(cfg):
        console.print("\n[green]✅ Configuración guardada exitosamente[/green]")
    else:
        console.print("\n[yellow]⚠️ No se pudo guardar la configuración[/yellow]")
    
    # Mostrar resumen
    console.print(Panel(
        f"📁 Carpeta: [bold]{cfg['output_base']}[/bold]\n"
        f"🎵 Calidad: [bold]{cfg['audio_quality']} kbps[/bold]\n"
        f"🎶 Formato: [bold]{cfg['audio_format'].upper()}[/bold]\n"
        f"📝 Generar M3U: [bold]{'✅ Sí' if cfg['generate_m3u'] else '❌ No'}[/bold]",
        title="📋 Configuración Final",
        border_style="green"
    ))
    
    return cfg

def check_and_offer_resume():
    """Verifica si hay una descarga pendiente y ofrece reanudarla."""
    if should_resume_download():
        state = load_download_state()
        playlists_info = []
        
        for playlist_id, playlist_data in state.get("playlists", {}).items():
            pending_tracks = sum(1 for track in playlist_data.get("tracks", {}).values() 
                               if track.get("status") in [DownloadState.PENDING, DownloadState.DOWNLOADING, DownloadState.PAUSED])
            if pending_tracks > 0:
                playlists_info.append(f"• {playlist_data.get('title', 'Playlist')} ({pending_tracks} pendientes)")
        
        if playlists_info:
            console.print(Panel(
                f"🔄 [bold]Descarga pendiente detectada[/bold]\n\n"
                f"Playlists con descargas pendientes:\n" + "\n".join(playlists_info) + "\n\n"
                f"📁 Carpeta: {state.get('base_path', 'No especificada')}\n"
                f"⏰ Última actualización: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(state.get('last_updated', time.time())))}",
                title="🔄 Reanudar Descarga",
                border_style="cyan"
            ))
            
            if Confirm.ask("¿Deseas reanudar la descarga desde donde se quedó?", default=True):
                return state
            else:
                if Confirm.ask("¿Limpiar el estado de descarga y empezar desde cero?", default=False):
                    clear_download_state()
                    console.print("[green]✅ Estado de descarga limpiado[/green]")
    
    return None

def interactive_download():
    """Proceso de descarga interactivo mejorado con capacidad de reanudación."""
    # Verificar si hay una descarga para reanudar
    resume_state = check_and_offer_resume()
    
    if resume_state:
        # Reanudar descarga existente
        base_path = Path(resume_state["base_path"])
        cfg = resume_state.get("config", load_config())
        urls = [playlist_data["url"] for playlist_data in resume_state["playlists"].values()]
        
        console.print(f"[cyan]🔄 Reanudando {len(urls)} playlists...[/cyan]")
        download_playlists(urls, base_path, cfg, resume_state)
        return
    
    cfg = load_config()
    
    # Panel de bienvenida
    console.print(Panel(
        "🎵 [bold]Descarga Interactiva de Playlists[/bold]\n"
        "Pega las URLs de tus playlists de YouTube/YouTube Music\n"
        "[dim]Una por línea. Finaliza con línea vacía.[/dim]",
        border_style="blue"
    ))
    
    # Recolectar URLs con validación en tiempo real
    urls: List[str] = []
    console.print("\n📝 [bold]Ingresa las URLs:[/bold]")
    
    while True:
        line = Prompt.ask(f"URL {len(urls) + 1} (o Enter para finalizar)")
        if not line.strip():
            break
            
        # Validación inmediata
        is_valid, message, normalized_url = validate_playlist_url(line)
        if is_valid:
            urls.append(normalized_url)
            console.print(f"[green]✅ URL {len(urls)} añadida correctamente[/green]")
        else:
            console.print(f"[red]❌ {message}[/red]")
            if Confirm.ask("¿Intentar con otra URL?", default=True):
                continue
            else:
                break
    
    if not urls:
        console.print("[red]❌ No se recibieron URLs válidas de playlist.[/red]")
        return
    
    console.print(f"\n[green]✅ Total de playlists válidas: {len(urls)}[/green]")
    
    # Selección de carpeta
    base = Path(cfg.get("output_base", DEFAULT_OPTS["output_base"]))
    
    if Confirm.ask(f"¿Usar carpeta configurada? ({base})", default=True):
        selected_base = base
    else:
        selected_base = auto_choose_output_folder(base)
    
    # Verificación de dependencias
    if not which_ffmpeg():
        console.print(Panel(
            "❌ [bold]ffmpeg no encontrado[/bold]\n\n"
            "ffmpeg es requerido para convertir audio. Instálalo:\n\n"
            "🪟 Windows:\n"
            "  • winget install Gyan.FFmpeg\n"
            "  • choco install ffmpeg\n\n"
            "🍎 macOS:\n"
            "  • brew install ffmpeg\n\n"
            "🐧 Linux:\n"
            "  • sudo apt install ffmpeg (Debian/Ubuntu)\n"
            "  • sudo dnf install ffmpeg (Fedora)\n"
            "  • sudo pacman -S ffmpeg (Arch)\n\n"
            "💡 Reinicia la aplicación después de instalar ffmpeg",
            title="Dependencia Requerida",
            border_style="red"
        ))
        return
    
    # Crear directorio si no existe
    try:
        ensure_dir(selected_base)
    except Exception as e:
        console.print(f"[red]❌ Error creando directorio: {e}[/red]")
        return
    
    # Confirmación final con resumen
    console.print("\n")
    console.print(Panel(
        f"🖥️  Sistema: [bold]{human_os()}[/bold]\n"
        f"📁 Carpeta: [bold]{selected_base}[/bold]\n"
        f"🎵 Playlists: [bold]{len(urls)}[/bold]\n"
        f"🎶 Formato: [bold]{cfg['audio_format'].upper()}[/bold] @ [bold]{cfg['audio_quality']}[/bold] kbps\n"
        f"📝 Generar M3U: [bold]{'✅ Sí' if cfg.get('generate_m3u', True) else '❌ No'}[/bold]",
        title="📋 Resumen de Descarga",
        border_style="cyan"
    ))
    
    if not Confirm.ask("\n🚀 ¿Iniciar descarga?", default=True):
        console.print("[yellow]⏹️ Descarga cancelada por el usuario[/yellow]")
        return
    
    # Iniciar descarga
    download_playlists(urls, selected_base, cfg)

@retry_on_failure(max_retries=2, delay=1.0)  # Reducir reintentos para videos no disponibles
def download_single_track(ydl, entry: dict, idx: int, playlist_id: str = "") -> Tuple[bool, str]:
    """Descarga una pista individual con manejo robusto de errores."""
    title = entry.get("title") or entry.get("id") or f"item{idx}"
    
    # Construir URL de manera más robusta
    url = None
    if entry.get("webpage_url"):
        url = entry["webpage_url"]
    elif entry.get("url"):
        url = entry["url"]
    elif entry.get("id"):
        # Construir URL desde ID si es necesario
        video_id = entry["id"]
        if len(video_id) == 11:  # YouTube video ID típico
            url = f"https://www.youtube.com/watch?v={video_id}"
        else:
            url = video_id
    
    if not url:
        return False, "Sin URL válida"
    
    try:
        # Verificar conectividad antes de descargar
        if not check_internet_connection():
            console.print("[red]🌐 Sin conexión a internet. Esperando...[/red]")
            if not wait_for_internet_connection():
                return False, "Sin conexión a internet"
        
        # Verificar si la descarga debe continuar (no pausada/detenida)
        if not download_controller.is_running():
            return False, "Descarga pausada/detenida por el usuario"
        
        # Realizar la descarga con información adicional en caso de éxito
        ydl.extract_info(url, download=True)
        return True, "Descargado y convertido a MP3"
        
    except yt_dlp.utils.DownloadError as de:
        error_msg = str(de)
        error_lower = error_msg.lower()
        
        # Categorizar errores más específicamente
        if any(keyword in error_lower for keyword in ["copyright", "copyright claim"]):
            return False, "Copyright claim"
        elif any(keyword in error_lower for keyword in ["unavailable", "not available", "removed"]):
            return False, "Video no disponible"
        elif any(keyword in error_lower for keyword in ["private", "privado"]):
            return False, "Video privado"
        elif any(keyword in error_lower for keyword in ["blocked", "geo", "region"]):
            return False, "Bloqueado geográficamente"
        elif "premium" in error_lower:
            return False, "Requiere suscripción premium"
        else:
            # Error de descarga que podría resolverse con reintentos
            last_line = error_msg.splitlines()[-1] if error_msg.splitlines() else error_msg
            raise Exception(f"Error de descarga: {last_line[:80]}")
            
    except Exception as e:
        # Otros errores que podrían resolverse con reintentos
        raise Exception(f"Error inesperado: {str(e)[:80]}")

def download_playlists(urls: List[str], base: Path, cfg: Dict[str, Any], resume_state: Optional[Dict[str, Any]] = None) -> None:
    """Descarga playlists con manejo mejorado de errores, progreso y capacidad de reanudar."""
    
    # Configurar manejadores de señales para control de pausa
    setup_signal_handlers()
    
    start_time = time.time()
    total_downloaded = 0
    total_skipped = 0
    total_errors = 0
    total_unavailable_detected = 0  # Videos no disponibles detectados al leer playlists
    
    # Estado de descarga para reanudar
    download_state = resume_state or {
        "playlists": {},
        "total_downloaded": 0,
        "total_skipped": 0,
        "total_errors": 0,
        "start_time": start_time,
        "base_path": str(base),
        "config": cfg
    }
    
    # Restaurar contadores si es una reanudación
    if resume_state:
        total_downloaded = download_state.get("total_downloaded", 0)
        total_skipped = download_state.get("total_skipped", 0)
        total_errors = download_state.get("total_errors", 0)
        start_time = download_state.get("start_time", start_time)
        console.print("[cyan]🔄 Reanudando descarga desde estado guardado...[/cyan]")
    
    audio_format = cfg["audio_format"]
    audio_quality = cfg["audio_quality"]
    
    # Mostrar dashboard pre-descarga
    show_download_dashboard(base, urls, cfg)
    
    # Verificar recursos del sistema
    estimated_tracks = len(urls) * 20  # Estimación aproximada
    if not check_system_resources(base, estimated_tracks):
        if not Confirm.ask("¿Continuar de todos modos?", default=False):
            console.print("[yellow]Descarga cancelada por el usuario[/yellow]")
            return

    # Progreso mejorado
    with create_enhanced_progress() as progress:
        pl_task = progress.add_task("[bold blue]📦 Procesando Playlists", total=len(urls))

        for playlist_idx, u in enumerate(urls, 1):
            # Verificar si debemos continuar
            if not download_controller.is_running():
                console.print("[yellow]⏹️ Descarga detenida por el usuario[/yellow]")
                break
                
            console.print("\n")
            console.rule(f"[bold blue]🎵 INICIANDO PLAYLIST {playlist_idx}/{len(urls)}[/bold blue]")
            console.print(f"[dim]URL: {u}[/dim]")
            
            # Generar ID único para la playlist
            playlist_id = hashlib.md5(u.encode()).hexdigest()[:8]
            
            # 1) Extraer metadata de la playlist con configuración robusta
            try:
                progress.update(pl_task, description=f"[bold blue]📋 Leyendo playlist {playlist_idx}[/bold blue]")
                
                # Configuración robusta para leer playlists con errores individuales
                robust_opts = {
                    "quiet": True, 
                    "logger": QuietLogger(), 
                    "noprogress": True, 
                    "no_warnings": True,
                    "ignoreerrors": True,  # Ignorar errores en videos individuales
                    "extract_flat": False,  # Necesitamos metadata completa
                    "playlistend": None,  # Sin límite de videos
                    "skip_unavailable_fragments": True,
                    "extractor_retries": 3,
                    "retries": 3
                }
                
                with yt_dlp.YoutubeDL(robust_opts) as ytmp:
                    info = ytmp.extract_info(u, download=False)
                    
                # Verificar si tenemos información válida de la playlist
                if not info:
                    raise Exception("No se pudo obtener información de la playlist")
                    
            except Exception as e:
                console.print(f"[red]❌ Error leyendo playlist:[/red] {e}")
                console.print(f"[yellow]💡 Intentando método alternativo para playlist {playlist_idx}...[/yellow]")
                
                # Método alternativo: intentar extraer al menos algunas entradas
                try:
                    alt_opts = {
                        "quiet": True,
                        "extract_flat": True,  # Extracción básica
                        "ignoreerrors": True,
                        "no_warnings": True
                    }
                    with yt_dlp.YoutubeDL(alt_opts) as ytmp_alt:
                        info = ytmp_alt.extract_info(u, download=False)
                        
                    if not info or not info.get("entries"):
                        raise Exception("Método alternativo también falló")
                        
                    console.print(f"[green]✅ Método alternativo exitoso para playlist {playlist_idx}[/green]")
                    
                except Exception as e2:
                    console.print(f"[red]❌ Playlist {playlist_idx} completamente inaccesible: {e2}[/red]")
                    total_errors += 1
                    progress.advance(pl_task)
                    continue

            # Título y carpeta de la playlist
            playlist_title = info.get("title") or info.get("playlist_title") or info.get("playlist") or info.get("id") or "Playlist"
            playlist_folder = safe_name(str(playlist_title), "Playlist")
            
            # Inicializar estado de la playlist si no existe
            if playlist_id not in download_state["playlists"]:
                download_state["playlists"][playlist_id] = {
                    "url": u,
                    "title": playlist_title,
                    "folder": playlist_folder,
                    "tracks": {},
                    "status": DownloadState.PENDING,
                    "total_tracks": 0,
                    "downloaded": 0,
                    "skipped": 0,
                    "errors": 0
                }
            
            try:
                out_dir = safe_path_join(base, playlist_folder)
                ensure_dir(out_dir)
            except ValueError as e:
                console.print(f"[red]❌ Error creando carpeta:[/red] {e}")
                total_errors += 1
                progress.advance(pl_task)
                continue

            # Entradas (canciones) - filtrar entradas válidas
            all_entries = info.get("entries") or []
            # Filtrar entradas válidas (que tengan al menos ID o título)
            valid_entries = []
            unavailable_count = 0
            
            for entry in all_entries:
                if not entry:
                    unavailable_count += 1
                    continue
                    
                # Verificar si la entrada tiene información mínima necesaria
                if entry.get("id") or entry.get("title") or entry.get("url"):
                    valid_entries.append(entry)
                else:
                    unavailable_count += 1
            
            entries = valid_entries
            total_tracks = len(entries)
            
            if unavailable_count > 0:
                console.print(f"[yellow]⚠️ {unavailable_count} videos no disponibles detectados en la playlist[/yellow]")
                total_unavailable_detected += unavailable_count
            
            if total_tracks == 0:
                console.print(f"[yellow]⚠️ Playlist sin videos disponibles: {playlist_title}[/yellow]")
                progress.advance(pl_task)
                continue

            console.print(f"[green]📊 Encontradas {total_tracks} pistas disponibles en '{playlist_title}'[/green]")
            if unavailable_count > 0:
                console.print(f"[yellow]⚠️ {unavailable_count} videos omitidos automáticamente (no disponibles por copyright/privacidad)[/yellow]")
            
            console.print(f"[blue]🎵 Iniciando descarga de {total_tracks} canciones...[/blue]")

            # Progreso por pistas
            track_task = progress.add_task(f"🎵 {playlist_folder[:30]}", total=total_tracks)

            # 2) Opciones de descarga
            ydl_opts = build_ydl_opts_for_playlist(out_dir, audio_format, audio_quality)

            # 3) Descarga con manejo mejorado de errores
            playlist_downloaded = 0
            playlist_skipped = 0
            playlist_errors = 0
            
            try:
                # Actualizar estado de la playlist
                playlist_state = download_state["playlists"][playlist_id]
                playlist_state["total_tracks"] = total_tracks
                playlist_state["status"] = DownloadState.DOWNLOADING
                
                # Inicializar tracks en el estado si no existen
                for idx, entry in enumerate(entries, start=1):
                    track_id = entry.get("id") or f"track_{idx}"
                    if track_id not in playlist_state["tracks"]:
                        playlist_state["tracks"][track_id] = {
                            "title": entry.get("title") or f"Track {idx}",
                            "url": entry.get("webpage_url") or entry.get("url") or "",
                            "status": DownloadState.PENDING,
                            "index": idx
                        }
                
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    for idx, entry in enumerate(entries, start=1):
                        # Verificar si debemos continuar
                        if not download_controller.is_running():
                            console.print("[yellow]⏸️ Pausando descarga y guardando estado...[/yellow]")
                            # Guardar estado antes de pausar
                            download_state["total_downloaded"] = total_downloaded
                            download_state["total_skipped"] = total_skipped
                            download_state["total_errors"] = total_errors
                            save_download_state(download_state)
                            return
                        
                        track_id = entry.get("id") or f"track_{idx}"
                        track_state = playlist_state["tracks"][track_id]
                        
                        # Saltar si ya fue descargado o procesado
                        if track_state["status"] in [DownloadState.COMPLETED, DownloadState.SKIPPED]:
                            if track_state["status"] == DownloadState.COMPLETED:
                                playlist_downloaded += 1
                                total_downloaded += 1
                            else:
                                playlist_skipped += 1
                                total_skipped += 1
                            progress.advance(track_task)
                            continue
                        
                        title = entry.get("title") or entry.get("id") or f"Track {idx}"
                        short_title = title[:40] + "..." if len(title) > 40 else title
                        
                        # Actualizar estado del track
                        track_state["status"] = DownloadState.DOWNLOADING
                        
                        # Mostrar qué canción se está procesando actualmente
                        progress.update(track_task, description=f"🎵 Procesando: {short_title}")
                        
                        # Anunciar inicio de descarga con más detalle
                        progress.console.print(f"\n[cyan]🎵 [{idx:02d}/{total_tracks:02d}] Iniciando: [bold]{title}[/bold][/cyan]")
                        
                        try:
                            # Mostrar estado antes de descargar
                            progress.console.print(f"[dim]   🔄 Conectando y verificando disponibilidad...[/dim]")
                            
                            success, message = download_single_track(ydl, entry, idx, playlist_id)
                            
                            if success:
                                progress.console.print(f"[green]   ✅ DESCARGADO: {title}[/green]")
                                track_state["status"] = DownloadState.COMPLETED
                                playlist_downloaded += 1
                                total_downloaded += 1
                            else:
                                progress.console.print(f"[yellow]   ⏭️ OMITIDO: {title}[/yellow]")
                                progress.console.print(f"[yellow]   📝 Razón: {message}[/yellow]")
                                track_state["status"] = DownloadState.SKIPPED
                                playlist_skipped += 1
                                total_skipped += 1
                        except Exception as e:
                            progress.console.print(f"[red]   ❌ ERROR: {title}[/red]")
                            progress.console.print(f"[red]   📝 Detalle: {str(e)[:80]}...[/red]")
                            track_state["status"] = DownloadState.ERROR
                            playlist_errors += 1
                            total_errors += 1
                        finally:
                            # Guardar estado después de cada track
                            playlist_state["downloaded"] = playlist_downloaded
                            playlist_state["skipped"] = playlist_skipped
                            playlist_state["errors"] = playlist_errors
                            download_state["total_downloaded"] = total_downloaded
                            download_state["total_skipped"] = total_skipped
                            download_state["total_errors"] = total_errors
                            save_download_state(download_state)
                            
                            # Actualizar barra de progreso
                            progress.advance(track_task)
                            # Mostrar progreso actual de la playlist
                            completed = idx
                            remaining = total_tracks - idx
                            progress.console.print(f"[dim]   📊 Progreso de playlist: {completed}/{total_tracks} ({remaining} restantes)[/dim]")
                            
            except Exception as e:
                console.print(f"[red]❌ Error crítico en playlist:[/red] {e}")
                total_errors += 1

            # Resumen de la playlist con separador visual
            console.print("\n" + "="*80)
            console.print(f"[cyan]📋 PLAYLIST COMPLETADA: '{playlist_title}'[/cyan]")
            console.print(f"[green]   ✅ Descargadas: {playlist_downloaded}[/green]")
            console.print(f"[yellow]   ⏭️ Omitidas: {playlist_skipped}[/yellow]")
            console.print(f"[red]   ❌ Errores: {playlist_errors}[/red]")
            console.print("="*80 + "\n")

            # 4) Post-procesado de la playlist
            try:
                # Marcar playlist como completada
                playlist_state["status"] = DownloadState.COMPLETED
                
                # Generar archivo .m3u si está habilitado
                if cfg.get("generate_m3u", True) and playlist_downloaded > 0:
                    write_m3u_for_dir(out_dir)
                    console.print(f"[green]📝 Lista M3U generada para '{playlist_title}'[/green]")
            except Exception as e:
                console.print(f"[yellow]⚠️ Error generando M3U: {e}[/yellow]")

            progress.advance(pl_task)

    # Deduplicación final
    try:
        console.print("\n[cyan]🔍 Verificando duplicados...[/cyan]")
        duplicates_moved = handle_duplicates(base)
        if duplicates_moved > 0:
            console.print(f"[green]🗂️ Se movieron {duplicates_moved} archivos duplicados[/green]")
    except Exception as e:
        console.print(f"[yellow]⚠️ Error en deduplicación: {e}[/yellow]")
    
    # Actualizar todos los archivos M3U al final
    if cfg.get("generate_m3u", True):
        try:
            console.print("\n[cyan]📝 Actualizando archivos M3U finales...[/cyan]")
            update_all_m3u_files(base)
        except Exception as e:
            console.print(f"[yellow]⚠️ Error actualizando M3U finales: {e}[/yellow]")

    # Mostrar resumen final con información completa
    show_download_summary_enhanced(base, total_downloaded, total_skipped, total_errors, total_unavailable_detected, start_time)
    
    # Limpiar estado si la descarga se completó exitosamente
    if not download_controller.should_stop and not download_controller.paused:
        clear_download_state()
        console.print("[green]✅ Estado de descarga limpiado (descarga completada)[/green]")
        
        # Mostrar información sobre archivos M3U creados
        if cfg.get("generate_m3u", True) and total_downloaded > 0:
            m3u_files = list(base.glob("*.m3u"))
            if m3u_files:
                console.print(Panel(
                    f"🎵 [bold]Archivos M3U creados:[/bold]\n\n"
                    f"• todas_las_canciones.m3u - Todas las canciones en un solo archivo\n"
                    f"• indice_playlists.m3u - Índice de todas las playlists\n"
                    f"• [Carpeta]/[Carpeta].m3u - M3U individual por playlist\n\n"
                    f"📝 Total de archivos M3U: {len(m3u_files)}",
                    title="🎵 Archivos M3U",
                    border_style="green"
                ))

# ---------------------- Typer commands (modo script) ----------------------

@app.command(help="Descarga una o varias playlists y organiza MP3 por carpeta de PLAYLIST.")
def download(
    urls: List[str] = Argument(None, help="URLs de playlist. Si omites, se te pedirá."),
    output: Optional[Path] = Option(None, "-o", "--output", help="Carpeta base de salida (ej. tu USB)."),
    no_m3u: bool = Option(False, "--no-m3u", help="No generar listas .m3u por carpeta."),
    interactive_config: bool = Option(False, "--config", help="Ejecutar configuración interactiva antes de descargar."),
    resume: bool = Option(False, "--resume", "-r", help="Reanudar descarga desde estado guardado."),
    force_new: bool = Option(False, "--force-new", help="Forzar nueva descarga (ignorar estado guardado)."),
):
    """Comando principal de descarga con mejoras."""
    
    try:
        # Manejar reanudación o nueva descarga
        if force_new:
            clear_download_state()
            console.print("[green]✅ Estado de descarga limpiado[/green]")
        elif resume or should_resume_download():
            resume_state = load_download_state()
            if resume_state:
                base_path = Path(resume_state["base_path"])
                cfg = resume_state.get("config", load_config())
                urls = [playlist_data["url"] for playlist_data in resume_state["playlists"].values()]
                
                console.print(f"[cyan]🔄 Reanudando {len(urls)} playlists desde estado guardado...[/cyan]")
                download_playlists(urls, base_path, cfg, resume_state)
                return
            else:
                console.print("[yellow]⚠️ No hay estado de descarga para reanudar[/yellow]")
        
        cfg = load_config()
        
        # Configuración interactiva si se solicita
        if interactive_config:
            cfg = interactive_config_setup()
        
        if no_m3u:
            cfg["generate_m3u"] = False

        if not urls:
            console.print("[blue]ℹ️ No se proporcionaron URLs, iniciando modo interactivo...[/blue]")
            return interactive_download()

        # Validación mejorada de URLs
        console.print("🔍 [bold]Validando URLs...[/bold]")
        valid_urls, errors = validate_urls_enhanced(urls)
        
        if errors:
            console.print("\n[red]❌ Errores encontrados en las URLs:[/red]")
            for error_msg, url in errors:
                console.print(f"  • {error_msg}: {url}")
        
        if not valid_urls:
            console.print("[red]❌ No se recibieron URLs válidas de playlist.[/red]")
            raise typer.Exit(1)
        
        console.print(f"[green]✅ URLs válidas: {len(valid_urls)}[/green]")

        # Determinar carpeta de salida
        if output:
            base = output.resolve()
        else:
            base = Path(cfg.get("output_base", DEFAULT_OPTS["output_base"]))
            # En modo CLI no interactivo, usar la carpeta configurada directamente
            console.print(f"📁 Usando carpeta configurada: {base}")

        # Verificar ffmpeg
        if not which_ffmpeg():
            console.print(Panel(
                "❌ [bold]ffmpeg no encontrado en PATH[/bold]\n\n"
                "ffmpeg es requerido para procesar audio.\n"
                "Instálalo y vuelve a ejecutar el comando.",
                title="Dependencia Requerida", 
                border_style="red"
            ))
            raise typer.Exit(1)

        # Crear directorio y iniciar descarga
        try:
            ensure_dir(base)
            console.print(f"[green]✅ Directorio listo: {base}[/green]")
            download_playlists(valid_urls, base, cfg)
        except Exception as e:
            console.print(f"[red]❌ Error durante la descarga: {e}[/red]")
            raise typer.Exit(1)
            
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️ Descarga cancelada por el usuario[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]❌ Error inesperado: {e}[/red]")
        raise typer.Exit(1)

@app.command(help="Deduplica/chequea duplicados entre carpetas bajo la salida base.")
def dedup(
    base: Optional[Path] = Option(None, "-o", "--output", help="Carpeta base de salida (ej. tu USB)."),
    move_to: str = Option("_duplicates", "--move-to", help="Carpeta a donde mover duplicados"),
):
    """Comando de deduplicación mejorado."""
    try:
        cfg = load_config()
        base_dir = base or Path(cfg.get("output_base", DEFAULT_OPTS["output_base"]))
        
        if not base_dir.exists():
            console.print(f"[red]❌ La carpeta base no existe: {base_dir}[/red]")
            console.print("💡 Ejecuta primero una descarga o verifica la configuración")
            raise typer.Exit(1)
        
        console.print(f"🔍 [bold]Iniciando deduplicación en:[/bold] {base_dir}")
        moved = handle_duplicates(base_dir, move_to_folder=move_to)
        
        if moved > 0:
            console.print(f"[green]✅ Proceso completado: {moved} archivos procesados[/green]")
        else:
            console.print("[green]✅ No se encontraron duplicados o no se realizaron cambios[/green]")
            
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️ Deduplicación cancelada por el usuario[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]❌ Error durante la deduplicación: {e}[/red]")
        raise typer.Exit(1)

@app.command(help="Configuración interactiva de la aplicación.")
def config(
    set_output: Optional[Path] = Option(None, "--set-output", help="Definir carpeta base por defecto"),
    set_m3u: Optional[bool] = Option(None, "--set-m3u/--unset-m3u", help="Activar/desactivar generación de .m3u"),
    set_quality: Optional[str] = Option(None, "--set-quality", help="Calidad de audio (128, 192, 256, 320)"),
    set_format: Optional[str] = Option(None, "--set-format", help="Formato de audio (mp3, m4a, opus)"),
    interactive: bool = Option(False, "--interactive", "-i", help="Configuración interactiva paso a paso"),
    show: bool = Option(False, "--show", "-s", help="Mostrar configuración actual"),
):
    """Comando de configuración mejorado."""
    try:
        if interactive:
            console.print("🔧 [bold]Iniciando configuración interactiva...[/bold]\n")
            interactive_config_setup()
            return
        
        cfg = load_config()
        changes_made = False
        
        # Aplicar cambios individuales
        if set_output:
            try:
                output_path = Path(set_output).expanduser().resolve()
                cfg["output_base"] = str(output_path)
                changes_made = True
                console.print(f"[green]✅ Carpeta base actualizada: {output_path}[/green]")
            except Exception as e:
                console.print(f"[red]❌ Error con la ruta: {e}[/red]")
                raise typer.Exit(1)
        
        if set_m3u is not None:
            cfg["generate_m3u"] = bool(set_m3u)
            changes_made = True
            status = "activada" if set_m3u else "desactivada"
            console.print(f"[green]✅ Generación de M3U {status}[/green]")
        
        if set_quality:
            if set_quality in ["128", "192", "256", "320"]:
                cfg["audio_quality"] = set_quality
                changes_made = True
                console.print(f"[green]✅ Calidad de audio actualizada: {set_quality} kbps[/green]")
            else:
                console.print("[red]❌ Calidad inválida. Usa: 128, 192, 256, o 320[/red]")
                raise typer.Exit(1)
        
        if set_format:
            if set_format.lower() in ["mp3", "m4a", "opus"]:
                cfg["audio_format"] = set_format.lower()
                changes_made = True
                console.print(f"[green]✅ Formato de audio actualizado: {set_format.upper()}[/green]")
            else:
                console.print("[red]❌ Formato inválido. Usa: mp3, m4a, o opus[/red]")
                raise typer.Exit(1)
        
        # Guardar cambios
        if changes_made:
            if save_config(cfg):
                console.print("[green]💾 Configuración guardada exitosamente[/green]")
            else:
                console.print("[red]❌ Error guardando la configuración[/red]")
                raise typer.Exit(1)
        
        # Mostrar configuración actual
        if show or not changes_made:
            console.print("\n")
            table = Table(title="⚙️ Configuración Actual", box=box.ROUNDED)
            table.add_column("Configuración", style="cyan")
            table.add_column("Valor", style="bold green")
            
            config_labels = {
                "output_base": "📁 Carpeta base",
                "audio_format": "🎶 Formato de audio",
                "audio_quality": "🎵 Calidad (kbps)",
                "generate_m3u": "📝 Generar M3U"
            }
            
            for key, value in cfg.items():
                label = config_labels.get(key, key)
                display_value = str(value)
                if key == "generate_m3u":
                    display_value = "✅ Sí" if value else "❌ No"
                elif key == "audio_format":
                    display_value = value.upper()
                    
                table.add_row(label, display_value)
            
            console.print(table)
            
            if not changes_made:
                console.print("\n💡 [dim]Usa --interactive para configuración paso a paso[/dim]")
                console.print("💡 [dim]Usa --help para ver todas las opciones disponibles[/dim]")
    
    except KeyboardInterrupt:
        console.print("\n[yellow]⏹️ Configuración cancelada por el usuario[/yellow]")
        raise typer.Exit(0)
    except Exception as e:
        console.print(f"[red]❌ Error en configuración: {e}[/red]")
        raise typer.Exit(1)

# ---------------------- Menú interactivo ----------------------

def show_system_statistics(cfg: Dict[str, Any]) -> None:
    """Muestra estadísticas detalladas del sistema y archivos."""
    
    try:
        base_path = Path(cfg.get("output_base", DEFAULT_OPTS["output_base"]))
        
        # Estadísticas de archivos
        if base_path.exists():
            all_mp3 = list(base_path.glob("**/*.mp3"))
            total_files = len(all_mp3)
            total_size = sum(f.stat().st_size for f in all_mp3 if f.exists())
            total_size_mb = total_size / (1024 * 1024)
            
            # Estadísticas por carpeta
            folders = [d for d in base_path.iterdir() if d.is_dir() and not d.name.startswith("_")]
            
            # Panel principal
            stats_table = Table(title="📊 Estadísticas del Sistema", box=box.ROUNDED)
            stats_table.add_column("Métrica", style="cyan")
            stats_table.add_column("Valor", style="bold green")
            
            stats_table.add_row("📁 Carpeta base", str(base_path))
            stats_table.add_row("🎵 Total archivos MP3", str(total_files))
            stats_table.add_row("💾 Tamaño total", f"{total_size_mb:.1f} MB")
            stats_table.add_row("📂 Playlists", str(len(folders)))
            
            if total_files > 0:
                avg_size = total_size_mb / total_files
                stats_table.add_row("📏 Tamaño promedio", f"{avg_size:.1f} MB/archivo")
            
            console.print(stats_table)
            
            # Tabla de playlists
            if folders:
                console.print("\n")
                playlist_table = Table(title="📂 Desglose por Playlist", box=box.ROUNDED)
                playlist_table.add_column("Playlist", style="blue")
                playlist_table.add_column("Archivos", style="green")
                playlist_table.add_column("Tamaño (MB)", style="yellow")
                
                for folder in sorted(folders, key=lambda x: x.name.lower()):
                    folder_mp3s = list(folder.glob("*.mp3"))
                    folder_size = sum(f.stat().st_size for f in folder_mp3s if f.exists())
                    folder_size_mb = folder_size / (1024 * 1024)
                    
                    playlist_table.add_row(
                        folder.name[:40] + "..." if len(folder.name) > 40 else folder.name,
                        str(len(folder_mp3s)),
                        f"{folder_size_mb:.1f}"
                    )
                
                console.print(playlist_table)
        else:
            console.print(Panel(
                f"📁 La carpeta base no existe: {base_path}\n"
                "💡 Ejecuta una descarga primero para generar estadísticas",
                title="⚠️ Sin datos",
                border_style="yellow"
            ))
    
    except Exception as e:
        console.print(f"[red]❌ Error generando estadísticas: {e}[/red]")

def show_about_info() -> None:
    """Muestra información detallada sobre la aplicación."""
    
    version_info = Panel(
        "🎵 [bold]YT Music Downloader[/bold]\n\n"
        "Descargador avanzado de playlists de YouTube/YouTube Music\n"
        "con organización automática y optimización para sistemas de audio\n\n"
        "[bold cyan]Características:[/bold cyan]\n"
        "• Descarga y organiza playlists automáticamente\n"
        "• Formato MP3 optimizado para autos (CBR 192k @ 44.1kHz)\n"
        "• Deduplicación inteligente por contenido de audio\n"
        "• Detección automática de USB\n"
        "• Generación de listas M3U\n"
        "• Interfaz rica con progreso visual\n"
        "• Manejo robusto de errores y reintentos\n\n"
        f"[bold cyan]Sistema:[/bold cyan] {human_os()}\n"
        f"[bold cyan]Python:[/bold cyan] {platform.python_version()}\n"
        f"[bold cyan]ffmpeg:[/bold cyan] {'✅ Disponible' if which_ffmpeg() else '❌ Falta'}\n\n"
        "[dim]Desarrollado para uso personal y educativo[/dim]",
        title="📋 Información de la Aplicación",
        border_style="cyan"
    )
    
    console.print(version_info)
    
    # Información de configuración
    cfg = load_config()
    config_panel = Panel(
        f"📁 [bold]Carpeta base:[/bold] {cfg.get('output_base', 'No configurada')}\n"
        f"🎶 [bold]Formato:[/bold] {cfg.get('audio_format', 'mp3').upper()}\n"
        f"🎵 [bold]Calidad:[/bold] {cfg.get('audio_quality', '192')} kbps\n"
        f"📝 [bold]Generar M3U:[/bold] {'✅ Sí' if cfg.get('generate_m3u', True) else '❌ No'}",
        title="⚙️ Configuración Actual",
        border_style="green"
    )
    
    console.print("\n")
    console.print(config_panel)

def show_enhanced_menu():
    """Menú principal mejorado con iconos y mejor organización."""
    
    # Verificar si hay descarga para reanudar
    resume_available = should_resume_download()
    resume_indicator = " [bold red](Descarga pendiente)[/bold red]" if resume_available else ""
    
    # Logo con efectos
    logo_panel = Panel(
        Align.center(
            "[bold blue]🎵 YT Music Downloader 🎵[/bold blue]\n"
            "[dim]Descarga playlists organizadas por carpetas[/dim]"
        ),
        border_style="blue",
        padding=(1, 2)
    )
    
    console.print(logo_panel)
    
    # Menú con iconos y descripciones
    menu_options = [
        ("1", "🚀", f"Descargar playlists{resume_indicator}", "Descarga asistida con progreso visual"),
        ("2", "🔧", "Verificar sistema", "Comprobar dependencias (ffmpeg, yt-dlp)"),
        ("3", "💾", "Detectar USB", "Buscar y seleccionar unidad de almacenamiento"),
        ("4", "⚙️", "Configuración", "Ajustar preferencias y valores por defecto"),
        ("5", "🔍", "Duplicados", "Buscar y gestionar archivos duplicados"),
        ("6", "📊", "Estadísticas", "Ver información de archivos descargados"),
        ("7", "🔄", "Estado descarga", "Ver/gestionar estado de descarga"),
        ("8", "ℹ️", "Información", "Acerca de la aplicación"),
        ("0", "🚪", "Salir", "Cerrar la aplicación")
    ]
    
    table = Table(show_header=False, box=box.ROUNDED)
    table.add_column("", width=3, style="cyan")
    table.add_column("", width=3)
    table.add_column("Opción", style="bold")
    table.add_column("Descripción", style="dim")
    
    for num, icon, title, desc in menu_options:
        table.add_row(num, icon, title, desc)
    
    console.print(table)

def show_menu():
    logo = """
 __   __        _         _         _          _      
 \\ \\ / /  ___  | |  ___  | |  __ _ | |_   ___ | |__   
  \\ V /  / _ \\ | | / _ \\ | | / _` || __| / __|| '_ \\  
   | |  |  __/ | || (_) || || (_| || |_ | (__ | | | | 
   |_|   \\___| |_| \\___/ |_| \\__,_| \\__| \\___||_| |_|
    """
    console.print(Panel(Align.center(logo), border_style="blue", title="YT Music DL"))
    console.print(Align.center("[bold]Descarga playlists y organiza por [green]PLAYLIST[/green][/bold]\n"))

    while True:
        show_enhanced_menu()
        
        choice = Prompt.ask("Selecciona", choices=["1","2","3","4","5","6","7","8","0"], default="1")
        if choice == "1":
            interactive_download()
        elif choice == "2":
            console.print(check_dependencies_panel())
            if not which_ffmpeg():
                console.print(Panel(
                    "Instala ffmpeg y vuelve a correr el programa.\n\n"
                    "Windows: winget install Gyan.FFmpeg  (o choco install ffmpeg)\n"
                    "macOS:   brew install ffmpeg\n"
                    "Linux:   apt/dnf/pacman según tu distro",
                    title="Cómo instalar ffmpeg",
                    border_style="red",
                ))
        elif choice == "3":
            base_cfg = Path(load_config().get("output_base", DEFAULT_OPTS["output_base"]))
            chosen = auto_choose_output_folder(base_cfg)
            console.print(Panel(f"Seleccionado: [bold]{chosen}[/bold]", border_style="green"))
        elif choice == "4":
            cfg = load_config()
            new_out = Prompt.ask("Nueva carpeta base por defecto", default=cfg["output_base"])  # type: ignore
            m3u_toggle = Prompt.ask("¿Generar .m3u por carpeta? (y/n)", choices=["y","n"], default="y")
            cfg["output_base"], cfg["generate_m3u"] = (
                str(Path(new_out).expanduser()),
                True if m3u_toggle == "y" else False,
            )
            save_config(cfg)
            console.print(Panel("Preferencias guardadas.", border_style="green"))
        elif choice == "5":
            cfg = load_config()
            base_dir = Path(cfg.get("output_base", DEFAULT_OPTS["output_base"]))
            ensure_dir(base_dir)
            handle_duplicates(base_dir)
        elif choice == "6":
            cfg = load_config()
            show_system_statistics(cfg)
        elif choice == "7":
            # Gestión de estado de descarga
            state_data = load_download_state()
            if not state_data:
                console.print(Panel(
                    "✅ [bold]No hay estado de descarga activo[/bold]\n\n"
                    "No hay descargas pendientes o pausadas.",
                    title="📊 Estado de Descarga",
                    border_style="green"
                ))
            else:
                # Mostrar opciones de gestión
                console.print(Panel(
                    "🔄 [bold]Gestión de Estado de Descarga[/bold]\n\n"
                    "1. Ver estado detallado\n"
                    "2. Reanudar descarga\n"
                    "3. Limpiar estado",
                    title="🔄 Opciones",
                    border_style="cyan"
                ))
                
                state_choice = Prompt.ask("Selecciona opción", choices=["1", "2", "3"], default="1")
                
                if state_choice == "1":
                    # Mostrar estado detallado
                    table = Table(title="📊 Estado de Descarga", box=box.ROUNDED)
                    table.add_column("Información", style="cyan")
                    table.add_column("Valor", style="bold green")
                    
                    table.add_row("📁 Carpeta base", state_data.get("base_path", "No especificada"))
                    table.add_row("📊 Total descargados", str(state_data.get("total_downloaded", 0)))
                    table.add_row("⏭️ Total omitidos", str(state_data.get("total_skipped", 0)))
                    table.add_row("❌ Total errores", str(state_data.get("total_errors", 0)))
                    table.add_row("⏰ Última actualización", 
                                 time.strftime('%Y-%m-%d %H:%M:%S', 
                                              time.localtime(state_data.get('last_updated', time.time()))))
                    
                    console.print(table)
                    
                elif state_choice == "2":
                    # Reanudar descarga
                    base_path = Path(state_data["base_path"])
                    cfg = state_data.get("config", load_config())
                    urls = [playlist_data["url"] for playlist_data in state_data["playlists"].values()]
                    
                    console.print(f"[cyan]🔄 Reanudando {len(urls)} playlists...[/cyan]")
                    download_playlists(urls, base_path, cfg, state_data)
                    
                elif state_choice == "3":
                    # Limpiar estado
                    if Confirm.ask("¿Estás seguro de que quieres limpiar el estado?", default=False):
                        if clear_download_state():
                            console.print("[green]✅ Estado de descarga limpiado[/green]")
                        else:
                            console.print("[red]❌ Error limpiando el estado[/red]")
                            
        elif choice == "8":
            show_about_info()
        elif choice == "0":
            console.print("Hasta luego 👋")
            break

# Comando adicional para estadísticas
@app.command(help="Muestra estadísticas del sistema y archivos descargados.")
def stats(
    base: Optional[Path] = Option(None, "-o", "--output", help="Carpeta base a analizar."),
):
    """Comando para mostrar estadísticas."""
    try:
        cfg = load_config()
        base_dir = base or Path(cfg.get("output_base", DEFAULT_OPTS["output_base"]))
        
        console.print(f"📊 [bold]Generando estadísticas para:[/bold] {base_dir}\n")
        show_system_statistics(cfg)
        
    except Exception as e:
        console.print(f"[red]❌ Error generando estadísticas: {e}[/red]")
        raise typer.Exit(1)

# Comandos para manejo de estado
@app.command(help="Gestiona el estado de descarga (pausar, reanudar, limpiar).")
def state(
    action: str = Argument(help="Acción: resume, clear, status"),
):
    """Gestiona el estado de descarga."""
    try:
        if action == "resume":
            if should_resume_download():
                resume_state = load_download_state()
                base_path = Path(resume_state["base_path"])
                cfg = resume_state.get("config", load_config())
                urls = [playlist_data["url"] for playlist_data in resume_state["playlists"].values()]
                
                console.print(f"[cyan]🔄 Reanudando {len(urls)} playlists...[/cyan]")
                download_playlists(urls, base_path, cfg, resume_state)
            else:
                console.print("[yellow]⚠️ No hay estado de descarga para reanudar[/yellow]")
                
        elif action == "clear":
            if clear_download_state():
                console.print("[green]✅ Estado de descarga limpiado[/green]")
            else:
                console.print("[red]❌ Error limpiando el estado[/red]")
                
        elif action == "status":
            state_data = load_download_state()
            if not state_data:
                console.print("[green]✅ No hay estado de descarga activo[/green]")
                return
                
            # Mostrar información del estado
            table = Table(title="📊 Estado de Descarga", box=box.ROUNDED)
            table.add_column("Información", style="cyan")
            table.add_column("Valor", style="bold green")
            
            table.add_row("📁 Carpeta base", state_data.get("base_path", "No especificada"))
            table.add_row("📊 Total descargados", str(state_data.get("total_downloaded", 0)))
            table.add_row("⏭️ Total omitidos", str(state_data.get("total_skipped", 0)))
            table.add_row("❌ Total errores", str(state_data.get("total_errors", 0)))
            table.add_row("⏰ Última actualización", 
                         time.strftime('%Y-%m-%d %H:%M:%S', 
                                      time.localtime(state_data.get('last_updated', time.time()))))
            
            console.print(table)
            
            # Mostrar playlists
            playlists = state_data.get("playlists", {})
            if playlists:
                playlist_table = Table(title="🎵 Estado de Playlists", box=box.ROUNDED)
                playlist_table.add_column("Playlist", style="blue")
                playlist_table.add_column("Estado", style="green")
                playlist_table.add_column("Progreso", style="yellow")
                
                for playlist_data in playlists.values():
                    title = playlist_data.get("title", "Sin título")[:40]
                    status = playlist_data.get("status", "unknown")
                    total = playlist_data.get("total_tracks", 0)
                    downloaded = playlist_data.get("downloaded", 0)
                    
                    playlist_table.add_row(title, status, f"{downloaded}/{total}")
                
                console.print("\n")
                console.print(playlist_table)
                
        else:
            console.print("[red]❌ Acción inválida. Usa: resume, clear, status[/red]")
            raise typer.Exit(1)
            
    except Exception as e:
        console.print(f"[red]❌ Error en gestión de estado: {e}[/red]")
        raise typer.Exit(1)

# Comando de ayuda mejorado
@app.command(help="Muestra información sobre la aplicación.")
def about():
    """Muestra información sobre la aplicación."""
    show_about_info()

# Callback para mostrar menú cuando no hay subcomandos
@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """YT Music Downloader - Descarga y organiza playlists de YouTube/YouTube Music."""
    if ctx.invoked_subcommand is None:
        try:
            # Verificar si estamos en un entorno interactivo
            if sys.stdin.isatty():
                show_menu()
            else:
                # En modo no interactivo, mostrar ayuda
                console.print("[blue]YT Music Downloader[/blue] - Usa --help para ver comandos disponibles")
                console.print("💡 Para modo interactivo, ejecuta sin argumentos en una terminal")
        except KeyboardInterrupt:
            console.print("\n[yellow]👋 ¡Hasta luego![/yellow]")
        except Exception as e:
            console.print(f"[red]❌ Error inesperado: {e}[/red]")
            raise typer.Exit(1)

if __name__ == "__main__":
    app()
