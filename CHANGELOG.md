# Changelog

Todas las mejoras notables de este proyecto serán documentadas en este archivo.

El formato está basado en [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
y este proyecto adhiere a [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-01-XX

### ✨ Agregado
- **Interfaz CLI rica** con menús interactivos usando Rich y Typer
- **Descarga robusta de playlists** de YouTube y YouTube Music
- **Organización automática** por carpetas de playlist
- **Formato optimizado para autos** (MP3 CBR 192 kbps @ 44.1 kHz, ID3v2.3)
- **Generación automática de listas M3U** por carpeta
- **Deduplicación inteligente** por hash de contenido de audio
- **Detección automática de USB** para Windows, macOS y Linux
- **Configuración interactiva** paso a paso
- **Manejo robusto de errores** - videos no disponibles no interrumpen playlists
- **Reintentos automáticos** con backoff exponencial
- **Validación de URLs** con feedback específico
- **Verificación de espacio en disco** antes de descargar
- **Estadísticas completas** de descarga con tasas de éxito
- **Múltiples calidades de audio** (128, 192, 256, 320 kbps)
- **Múltiples formatos** (MP3, M4A, Opus)
- **Nombres de archivo seguros** compatibles con FAT32/Windows

### 🛡️ Seguridad
- **Validación de rutas** para prevenir path traversal
- **Sanitización de nombres** de archivos y carpetas
- **Manejo seguro de URLs** con validación exhaustiva

### 🔧 Características Técnicas
- **Progreso visual detallado** por canción individual
- **Categorización específica de errores** (copyright, privado, geobloqueado, etc.)
- **Filtrado automático** de videos no disponibles durante extracción
- **Método alternativo de extracción** si falla el principal
- **Configuración persistente** entre sesiones
- **Dashboard pre-descarga** con verificación del sistema
- **Resumen post-descarga** con estadísticas completas

### 📱 Interfaz de Usuario
- **Menú interactivo mejorado** con iconos y descripciones
- **Feedback visual en tiempo real** durante descargas
- **Progreso por playlist y por canción**
- **Mensajes informativos** sobre omisiones y errores
- **Dashboard de información del sistema**
- **Separadores visuales** entre playlists
- **Códigos de color** para diferentes tipos de mensajes

### 🎯 Optimizaciones Específicas
- **Ignorar errores individuales** sin afectar la playlist completa
- **Construcción robusta de URLs** desde IDs de video
- **Reducción de reintentos** para videos definitivamente no disponibles
- **Extracción plana como fallback** para playlists problemáticas
- **Verificación de metadata** antes de procesar

## Tipos de Cambios

- `✨ Agregado` para nuevas funcionalidades
- `🔧 Cambiado` para cambios en funcionalidad existente  
- `❌ Obsoleto` para funcionalidades que serán removidas
- `🗑️ Removido` para funcionalidades removidas
- `🔒 Seguridad` en caso de vulnerabilidades
- `🐛 Arreglado` para correcciones de bugs

---

## [Unreleased]

### 🔄 En Desarrollo
- Soporte para YouTube Shorts
- Descarga de metadatos extendidos (lyrics, album art)
- Interfaz web opcional
- Soporte para más formatos de audio
- Sincronización con servicios de música

### 💡 Ideas Futuras
- Plugin system para extensiones
- Tema personalizable para la interfaz
- Descarga programada/automatizada
- Integración con APIs de música
- Soporte para subtítulos/lyrics

---

## Notas de Versión

### Compatibilidad
- **Python**: 3.8+
- **Sistemas Operativos**: Windows, macOS, Linux
- **Dependencias**: yt-dlp, rich, typer, psutil
- **Requerimientos Externos**: ffmpeg

### Migraciones
No se requieren migraciones para la versión inicial.

### Problemas Conocidos
- Algunos sistemas de audio muy antiguos pueden no soportar ID3v2.3
- La detección de USB puede fallar en algunos sistemas Linux con configuraciones especiales
- Algunos copyright claims muy nuevos pueden no ser detectados inmediatamente

### Agradecimientos
- Gracias a la comunidad de yt-dlp por el motor de descarga robusto
- Gracias a los desarrolladores de Rich por la hermosa interfaz de terminal
- Gracias a los beta testers por encontrar edge cases en el manejo de errores