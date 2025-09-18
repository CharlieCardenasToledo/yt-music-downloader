# 🤝 Guía de Contribución

¡Gracias por tu interés en contribuir a YT Music Downloader! Esta guía te ayudará a empezar.

## 🎯 Formas de Contribuir

### 🐛 Reportar Bugs
- Usa las [GitHub Issues](https://github.com/tu-usuario/yt-music-downloader/issues)
- Incluye información detallada:
  - Sistema operativo y versión
  - Versión de Python
  - Mensaje de error completo
  - URLs de prueba (si es posible)
  - Pasos para reproducir el error

### 💡 Sugerir Funcionalidades
- Abre un issue con la etiqueta "enhancement"
- Describe claramente la funcionalidad deseada
- Explica por qué sería útil para otros usuarios
- Proporciona ejemplos de uso si es posible

### 🔧 Contribuir Código
1. **Fork** el repositorio
2. **Clona** tu fork localmente
3. **Crea una rama** para tu feature
4. **Implementa** tu cambio
5. **Agrega tests** si es apropiado
6. **Actualiza documentación** si es necesario
7. **Envía un Pull Request**

## 🛠️ Configuración de Desarrollo

### Prerrequisitos
```bash
# Python 3.8+
python --version

# ffmpeg instalado
ffmpeg -version
```

### Instalación
```bash
# Clonar el repositorio
git clone https://github.com/tu-usuario/yt-music-downloader.git
cd yt-music-downloader

# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows:
venv\\Scripts\\activate
# macOS/Linux:
source venv/bin/activate

# Instalar dependencias de desarrollo
pip install -r requirements.txt
pip install -r requirements-dev.txt  # cuando esté disponible
```

### Ejecutar Tests
```bash
# Ejecutar tests básicos
python -m pytest tests/

# Con coverage
python -m pytest --cov=download_playlist tests/
```

## 📝 Estándares de Código

### Estilo de Código
- Seguir **PEP 8** para el estilo de Python
- Usar **type hints** cuando sea posible
- **Docstrings** para funciones públicas
- **Comentarios** para lógica compleja

### Convenciones de Nombres
- **snake_case** para variables y funciones
- **PascalCase** para clases
- **UPPER_CASE** para constantes
- Nombres descriptivos y claros

### Ejemplo de Función Bien Documentada
```python
def download_playlist_safely(url: str, output_dir: Path, max_retries: int = 3) -> Tuple[int, int, int]:
    """
    Descarga una playlist de forma segura con manejo de errores.
    
    Args:
        url: URL de la playlist de YouTube/YouTube Music
        output_dir: Directorio donde guardar los archivos
        max_retries: Número máximo de reintentos por video
        
    Returns:
        Tupla con (descargados, omitidos, errores)
        
    Raises:
        ValueError: Si la URL no es válida
        OSError: Si el directorio de salida no es accesible
    """
    # Implementación aquí
    pass
```

## 🧪 Tests

### Escribir Tests
- **Tests unitarios** para funciones individuales
- **Tests de integración** para flujos completos
- **Tests de regresión** para bugs corregidos
- **Mocks** para servicios externos (YouTube)

### Estructura de Tests
```
tests/
├── unit/
│   ├── test_url_validation.py
│   ├── test_audio_processing.py
│   └── test_file_management.py
├── integration/
│   ├── test_download_flow.py
│   └── test_playlist_processing.py
└── fixtures/
    ├── sample_playlists.json
    └── test_audio_files/
```

## 📚 Documentación

### Actualizar README
- Mantener ejemplos actualizados
- Documentar nuevas funcionalidades
- Actualizar capturas de pantalla si es necesario

### Comentarios en Código
```python
# ✅ Bueno: Explica el "por qué"
# Usar CBR para mejor compatibilidad con sistemas de audio automotrices
audio_format = "mp3_cbr"

# ❌ Malo: Explica el "qué" (obvio)
# Establecer formato de audio a MP3 CBR
audio_format = "mp3_cbr"
```

## 🔄 Proceso de Pull Request

### Antes de Enviar
1. **Ejecutar tests** localmente
2. **Verificar que el código funciona** con ejemplos reales
3. **Actualizar documentación** relevante
4. **Verificar que no hay conflictos** con la rama main

### Estructura del Pull Request
```markdown
## 📝 Descripción
Breve descripción de los cambios realizados.

## 🎯 Tipo de Cambio
- [ ] Bug fix (cambio que corrige un issue)
- [ ] Nueva funcionalidad (cambio que agrega funcionalidad)
- [ ] Breaking change (cambio que rompe compatibilidad)
- [ ] Documentación

## 🧪 Tests
- [ ] Tests existentes pasan
- [ ] Agregué tests para mi cambio
- [ ] Probé manualmente la funcionalidad

## 📋 Checklist
- [ ] Mi código sigue el estilo del proyecto
- [ ] Revisé mi propio código
- [ ] Comenté código complejo
- [ ] Actualicé documentación relevante
```

## 🐛 Debugging

### Información Útil para Debug
```python
# Habilitar logs detallados
import logging
logging.basicConfig(level=logging.DEBUG)

# Información de entorno
print(f"Python: {sys.version}")
print(f"Platform: {platform.platform()}")
print(f"yt-dlp version: {yt_dlp.version.__version__}")
```

### Casos de Test Comunes
- **Playlists públicas** con videos disponibles
- **Playlists con videos privados/eliminados**
- **Playlists con copyright claims**
- **URLs malformadas**
- **Directorios sin permisos de escritura**

## 🏷️ Versionado y Releases

### Semantic Versioning
- **MAJOR**: Cambios incompatibles en API
- **MINOR**: Nueva funcionalidad compatible
- **PATCH**: Bug fixes compatibles

### Proceso de Release
1. Actualizar `CHANGELOG.md`
2. Bump version en código
3. Crear tag de git
4. Generar release notes
5. Publicar en GitHub

## 🤔 ¿Preguntas?

### Canales de Comunicación
- **GitHub Issues**: Para bugs y features
- **GitHub Discussions**: Para preguntas generales
- **Pull Request Comments**: Para revisión de código

### Maintainers
- [@tu-usuario](https://github.com/tu-usuario) - Maintainer principal

## 🎉 Reconocimiento

Los contribuidores serán reconocidos en:
- **README.md** - Lista de contribuidores
- **Releases notes** - Cambios específicos
- **CHANGELOG.md** - Historial de cambios

¡Gracias por hacer que YT Music Downloader sea mejor para todos! 🎵