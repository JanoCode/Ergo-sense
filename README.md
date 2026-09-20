# ErgoSense2

Sistema de monitoreo de fatiga basado en métricas deterministas e historial longitudinal.

## Descripción

Esta aplicación de escritorio utiliza cálculos, reglas deterministas y datos históricos del usuario para evaluar los niveles de fatiga. En el futuro, se empleará MediaPipe para la extracción de landmarks (marcas de referencia) faciales y corporales que alimentarán el motor de evaluación determinista.

**NOTA:** Este proyecto no utiliza Machine Learning para inferir la fatiga directamente, garantizando la explicabilidad de los resultados.

## Estructura del proyecto

El proyecto sigue una arquitectura limpia (Clean Architecture) orientada a la separación de responsabilidades:

- `src/core/`: Funciones principales, excepciones base y tipos de datos generales.
- `src/domain/`: Entidades del dominio (Usuario, Sesión, Métricas) y lógica de negocio pura.
- `src/application/`: Casos de uso y servicios de aplicación.
- `src/infrastructure/`: Implementaciones concretas (Acceso a SQLite, servicios de cámara con OpenCV, etc).
- `src/presentation/`: Interfaz de usuario (UI) basada en PySide6.
- `tests/`: Pruebas automatizadas.

## Instalación

1. Crea un entorno virtual:
   ```bash
   python -m venv venv
   # En Windows:
   venv\Scripts\activate
   # En Linux/Mac:
   source venv/bin/activate
   ```
2. Instala las dependencias:
   ```bash
   pip install -r requirements.txt
   ```

## Ejecución

Para iniciar la aplicación, ejecuta:
```bash
python src/main.py
```
