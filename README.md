# ErgoSense

Aplicación de escritorio para monitorear señales asociadas a fatiga durante sesiones
de trabajo y analizar su evolución histórica por usuario. Es una herramienta de apoyo
ergonómico: **no realiza diagnósticos médicos**.

## Descripción

MediaPipe se utiliza exclusivamente para extraer landmarks faciales. A partir de ellos,
ErgoSense calcula EAR, parpadeos, PERCLOS, MAR y pose de cabeza. La clasificación de
fatiga no usa Machine Learning: combina métricas mediante reglas deterministas,
configurables y explicables, adaptadas cuando existe un baseline personal válido.

## Arquitectura

El proyecto utiliza **Modular Monolith Architecture**: una sola aplicación de escritorio,
un único proceso y una base de datos SQLite compartida. El código se agrupa por
funcionalidad en lugar de dividirse en capas globales.

- `src/users/`: usuarios, selección, persistencia y diálogo de creación.
- `src/sessions/`: inicio, finalización e historial de sesiones.
- `src/monitoring/`: webcam, frames y extracción de landmarks con MediaPipe.
- `src/fatigue/`: métricas, baseline, motor de score, persistencia y analytics.
- `src/database/`: conexión y creación del esquema SQLite compartido.
- `src/ui/`: ventana principal, monitoreo, historial, gráficos e insights.
- `src/app/`: composición de módulos y punto de entrada.
- `tests/`: pruebas organizadas según los mismos módulos funcionales.

Toda la solución se ejecuta como un único proceso y comparte una sola base SQLite.

## Tecnologías

- Python 3.10 o superior.
- PySide6 y Qt Charts para la interfaz y visualizaciones.
- OpenCV para captura y tratamiento de frames.
- MediaPipe para landmarks faciales.
- SQLite para usuarios, sesiones, assessments, eventos y resúmenes.
- `unittest` para pruebas automatizadas.

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

La webcam debe estar disponible para el monitoreo en tiempo real. El historial y las
vistas analíticas pueden consultarse sin iniciar la cámara.

## Ejecución

Para iniciar la aplicación, ejecuta:
```bash
python src/app/main.py
```

## Funcionamiento general

1. Crea o selecciona un usuario.
2. Inicia una sesión; si hace falta, el baseline personal comienza a calibrarse.
3. La webcam alimenta landmarks y métricas deterministas, sin clasificar imágenes.
4. Cada 30 segundos el motor genera un Fatigue Score de 0 a 100, nivel, confianza y
   razones explicativas.
5. Las evaluaciones y eventos relevantes se guardan en SQLite.
6. Al finalizar se genera un resumen con métricas, scores y tiempos hasta niveles.
7. El historial, los gráficos y el análisis de 7/30/90 días utilizan únicamente esos
   datos reales persistidos.

Los valores ausentes (`None`, `UNKNOWN`, rostro no detectado o muestras inválidas) se
tratan como información no disponible; nunca se convierten automáticamente en un
estado normal ni en cero.

## Tests

```bash
python -m unittest discover -s tests -t .
```
