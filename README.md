# 🎵 YT Music Downloader

[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)](https://github.com)
[![Rich CLI](https://img.shields.io/badge/CLI-Rich-brightgreen)](https://github.com/Textualize/rich)

**Un descargador avanzado de playlists de YouTube/YouTube Music con interfaz rica, organización automática y optimización para sistemas de audio automotrices.**

## ✨ Características Principales

### 🎯 **Funcionalidad Core**
- 📱 **Interfaz CLI rica** con menús interactivos y progreso visual
- 🎵 **Descarga de playlists completas** de YouTube y YouTube Music
- 📁 **Organización automática** por carpetas de playlist
- 🎶 **Formato optimizado para autos** (MP3 CBR 192 kbps @ 44.1 kHz, ID3v2.3)
- 📝 **Generación de listas M3U** automática
- 🔄 **Deduplicación inteligente** por contenido de audio

### 🛡️ **Robustez y Manejo de Errores**
- ⚡ **Manejo robusto de errores** - videos no disponibles no interrumpen playlists
- 🔄 **Reintentos automáticos** con backoff exponencial
- 📊 **Feedback detallado** sobre copyright claims, videos privados, etc.
- 🚫 **Filtrado automático** de contenido no disponible
- 📈 **Estadísticas completas** de descarga

### 💾 **Gestión de Almacenamiento**
- 🔍 **Detección automática de USB** (Windows/macOS/Linux)
- 💽 **Verificación de espacio en disco** antes de descargar
- 🗂️ **Gestión inteligente de duplicados** con interfaz visual
- 📂 **Nombres seguros** compatibles con FAT32/Windows

### ⚙️ **Configuración y Personalización**
- 🔧 **Configuración interactiva** paso a paso
- 🎚️ **Múltiples calidades de audio** (128, 192, 256, 320 kbps)
- 🎼 **Formatos de audio** (MP3, M4A, Opus)
- 💾 **Configuración persistente** entre sesiones

## 🚀 Instalación Rápida

### Prerrequisitos
- **Python 3.8+**
- **ffmpeg** (requerido para conversión de audio)

### 1. Instalar ffmpeg

**Windows:**
```bash
# Con winget
winget install Gyan.FFmpeg

# Con chocolatey
choco install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Linux:**
```bash
# Ubuntu/Debian
sudo apt install ffmpeg

# Fedora
sudo dnf install ffmpeg

# Arch Linux
sudo pacman -S ffmpeg
```

### 2. Instalar dependencias de Python

```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/yt-music-downloader.git
cd yt-music-downloader

# Instalar dependencias
pip install -r requirements.txt
```

## 📖 Uso

### 🎯 Modo Interactivo (Recomendado)

```bash
python download_playlist.py
```

Esto abrirá el menú interactivo con todas las opciones disponibles.

### ⚡ Modo Línea de Comandos

**Descarga básica:**
```bash
python download_playlist.py download "https://music.youtube.com/playlist?list=PLxxxxxxx"
```

**Descarga con configuración:**
```bash
python download_playlist.py download \
  --output "/path/to/usb" \
  --config \
  "https://music.youtube.com/playlist?list=PLxxxxxxx"
```

**Múltiples playlists:**
```bash
python download_playlist.py download \
  "https://music.youtube.com/playlist?list=PLxxxxxxx" \
  "https://music.youtube.com/playlist?list=PLyyyyyyy"
```

### 🔧 Configuración

**Configuración interactiva:**
```bash
python download_playlist.py config --interactive
```

**Configuración rápida:**
```bash
# Establecer carpeta de salida
python download_playlist.py config --set-output "/path/to/folder"

# Cambiar calidad de audio
python download_playlist.py config --set-quality 320

# Cambiar formato de audio
python download_playlist.py config --set-format mp3
```

### 🔍 Utilidades

**Buscar duplicados:**
```bash
python download_playlist.py dedup
```

**Ver estadísticas:**
```bash
python download_playlist.py stats
```

**Información del sistema:**
```bash
python download_playlist.py about
```

## 📊 Ejemplos de Salida

### 🎵 Dashboard de Descarga
```
╭─ 📊 Información del Sistema ─╮     🎵 Playlists a Descargar
│ 🖥️  Sistema: Windows          │ ╭─────┬──────────────────────────────╮
│ 📁 Carpeta: E:\Music         │ │ #   │ URL                          │
│ 🎵 Playlists: 3              │ │ 1   │ https://music.youtube.com... │
│ ⚙️  ffmpeg: ✅ Disponible     │ │ 2   │ https://music.youtube.com... │
│ 🎶 Formato: MP3 @ 192 kbps   │ │ 3   │ https://music.youtube.com... │
╰──────────────────────────────╯ ╰─────┴──────────────────────────────╯
```

### 🎯 Progreso Detallado por Canción
```
🎵 [01/25] Iniciando: Artista - Canción Ejemplo
   🔄 Conectando y verificando disponibilidad...
   ✅ DESCARGADO: Artista - Canción Ejemplo
   📊 Progreso de playlist: 1/25 (24 restantes)

🎵 [02/25] Iniciando: Artista - Canción Con Copyright
   🔄 Conectando y verificando disponibilidad...
   ⏭️ OMITIDO: Artista - Canción Con Copyright
   📝 Razón: Copyright claim
   📊 Progreso de playlist: 2/25 (23 restantes)
```

### 📈 Resumen Final
```
╭──────────── 📊 Resumen de Descarga Completo ─────────────╮
│ ✅ Descargados exitosamente    │ 23                      │
│ ⏭️ Omitidos durante descarga   │ 2                       │
│ ❌ Errores durante descarga    │ 0                       │
│ 🚫 No disponibles detectados  │ 3                       │
│ 📁 Total archivos MP3         │ 23                      │
│ 💾 Tamaño total              │ 127.3 MB               │
│ ⏱️ Tiempo total              │ 5m 23s                 │
│ 📈 Tasa de éxito             │ 82.1%                  │
╰─────────────────────────────────────────────────────────╯
```

## 🎚️ Opciones de Configuración

### 🎵 Calidades de Audio Disponibles
- **128 kbps** - Calidad estándar, archivos pequeños (~3MB/canción)
- **192 kbps** - Calidad alta, recomendado para autos (~4.5MB/canción) **[Predeterminado]**
- **256 kbps** - Calidad muy alta (~6MB/canción)
- **320 kbps** - Calidad máxima (~7.5MB/canción)

### 🎼 Formatos de Audio Soportados
- **MP3** - Compatible universal **[Predeterminado]**
- **M4A/AAC** - Mejor calidad, compatible con Apple
- **Opus** - Mejor compresión, dispositivos modernos

### 📂 Estructura de Archivos Generada
```
📁 Carpeta de Salida/
├── 📁 Nombre de Playlist 1/
│   ├── 🎵 Canción 1.mp3
│   ├── 🎵 Canción 2.mp3
│   └── 📝 Nombre de Playlist 1.m3u
├── 📁 Nombre de Playlist 2/
│   ├── 🎵 Canción A.mp3
│   ├── 🎵 Canción B.mp3
│   └── 📝 Nombre de Playlist 2.m3u
└── 📁 _duplicates/
    └── 🎵 archivo_duplicado.mp3
```

## 🛠️ Características Técnicas

### 🎯 Optimizaciones para Audio Automotriz
- **CBR (Constant Bit Rate)** para mejor compatibilidad
- **44.1 kHz** frecuencia de muestreo estándar
- **ID3v2.3** para máxima compatibilidad con sistemas de audio
- **Nombres de archivo seguros** compatibles con FAT32/Windows
- **Sin caracteres especiales** que puedan causar problemas

### 🔄 Manejo Robusto de Errores
- **Videos no disponibles** se omiten automáticamente sin interrumpir la playlist
- **Copyright claims** se detectan y categorizan específicamente
- **Reintentos inteligentes** con backoff exponencial para errores temporales
- **Validación de URLs** con feedback específico
- **Recuperación automática** ante errores de red

### 💾 Gestión de Recursos
- **Verificación de espacio en disco** antes de comenzar
- **Detección automática de USB** en Windows, macOS y Linux
- **Deduplicación por hash de audio** (no solo por nombre)
- **Limpieza automática** de archivos temporales

## ❓ Preguntas Frecuentes

### 🤔 ¿Por qué algunas canciones se omiten?

Las canciones pueden omitirse por varias razones legítimas:
- **Copyright claims** (reclamaciones de derechos de autor)
- **Videos privados** o eliminados por el usuario
- **Restricciones geográficas** 
- **Contenido premium** que requiere suscripción
- **Videos bloqueados** por el propietario

Esto es completamente normal y la aplicación continúa automáticamente con las siguientes canciones.

### 💿 ¿Es compatible con sistemas de audio automotrices?

¡Absolutamente! La aplicación está específicamente optimizada para autos:
- ✅ Formato MP3 CBR 192 kbps (máxima compatibilidad)
- ✅ ID3v2.3 (compatible con sistemas antiguos)
- ✅ Nombres de archivo seguros (sin caracteres problemáticos)
- ✅ Estructura de carpetas clara por playlist
- ✅ Listas M3U para navegación fácil

### 🔧 ¿Cómo actualizo la configuración?

```bash
# Configuración interactiva completa
python download_playlist.py config --interactive

# Ver configuración actual
python download_playlist.py config --show

# Cambios específicos
python download_playlist.py config --set-quality 320
python download_playlist.py config --set-output "/nueva/ruta"
```

### 🚀 ¿Cómo mejoro la velocidad de descarga?

1. **Usar conexión por cable** en lugar de WiFi
2. **Seleccionar calidad apropiada** (192 kbps es ideal para la mayoría)
3. **Verificar que ffmpeg esté instalado** correctamente
4. **Usar SSD** en lugar de disco duro tradicional para almacenamiento

## 🤝 Contribuciones

¡Las contribuciones son bienvenidas! Por favor:

1. **Fork** el repositorio
2. **Crea una rama** para tu feature (`git checkout -b feature/nueva-funcionalidad`)
3. **Commit** tus cambios (`git commit -am 'Agregar nueva funcionalidad'`)
4. **Push** a la rama (`git push origin feature/nueva-funcionalidad`)
5. **Abre un Pull Request**

### 🐛 Reportar Problemas

Usa las [GitHub Issues](https://github.com/tu-usuario/yt-music-downloader/issues) para reportar bugs o sugerir funcionalidades. Incluye:
- **Sistema operativo** y versión
- **Versión de Python**
- **Mensaje de error completo** (si aplica)
- **URLs de prueba** (si es posible)

## 📜 Licencia

Este proyecto está licenciado bajo la [Licencia MIT](LICENSE) - ver el archivo LICENSE para detalles.

## ⚖️ Descargo de Responsabilidad

Esta herramienta está destinada para **uso personal y educativo únicamente**. Los usuarios son responsables de cumplir con:
- Las condiciones de servicio de YouTube
- Las leyes locales de derechos de autor
- Las regulaciones de uso justo

**No distribuyas contenido protegido por derechos de autor sin autorización.**

## 🙏 Reconocimientos

- [yt-dlp](https://github.com/yt-dlp/yt-dlp) - Motor de descarga robusto
- [Rich](https://github.com/Textualize/rich) - Interfaz de terminal hermosa
- [Typer](https://github.com/tiangolo/typer) - CLI framework moderno
- [psutil](https://github.com/giampaolo/psutil) - Información del sistema
- [FFmpeg](https://ffmpeg.org/) - Procesamiento de audio

---

<div align="center">

**⭐ ¡Si te gusta este proyecto, dale una estrella! ⭐**

[🐛 Reportar Bug](https://github.com/tu-usuario/yt-music-downloader/issues) • [💡 Sugerir Feature](https://github.com/tu-usuario/yt-music-downloader/issues) • [📖 Documentación](https://github.com/tu-usuario/yt-music-downloader/wiki)

</div>