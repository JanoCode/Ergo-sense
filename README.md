# ErgoSense2

Sistema de monitoreo de fatiga basado en métricas deterministas e historial longitudinal.

## Descripción

Esta aplicación de escritorio utiliza cálculos, reglas deterministas y datos históricos del usuario para evaluar los niveles de fatiga. En el futuro, se empleará MediaPipe para la extracción de landmarks (marcas de referencia) faciales y corporales que alimentarán el motor de evaluación determinista.

**NOTA:** Este proyecto no utiliza Machine Learning para inferir la fatiga directamente, garantizando la explicabilidad de los resultados.

## Arquitectura

El proyecto utiliza **Modular Monolith Architecture**: una sola aplicación de escritorio,
un único proceso y una base de datos SQLite compartida. El código se agrupa por
funcionalidad en lugar de dividirse en capas globales.

- `src/users/`: usuarios, selección, persistencia y diálogo de creación.
- `src/sessions/`: inicio, finalización e historial de sesiones.
- `src/monitoring/`: webcam, frames y extracción de landmarks con MediaPipe.
- `src/fatigue/`: EAR, parpadeos, PERCLOS, MAR, bostezos, pose y baseline personal.
- `src/database/`: conexión y creación del esquema SQLite compartido.
- `src/ui/`: ventana principal y dashboard de escritorio.
- `src/app/`: composición de módulos y punto de entrada.
- `tests/`: pruebas organizadas según los mismos módulos funcionales.

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
python src/app/main.py
```

## Tests

```bash
python -m unittest discover -s tests -t .
```
