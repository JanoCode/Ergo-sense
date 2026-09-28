# ErgoSense

Aplicación de escritorio para organizar sesiones de trabajo y hábitos de descanso.
ErgoSense registra el tiempo de uso continuo, recuerda cuándo realizar una pausa,
permite posponerla y conserva un historial simple por usuario.

## Funcionalidades

- Usuarios y sesiones independientes.
- Recordatorios de pausa basados exclusivamente en tiempo.
- Posposición configurable sin reiniciar el uso continuo.
- Temporizador y finalización manual o automática de pausas.
- Recomendaciones breves de autocuidado durante los descansos.
- Historial de sesiones, pausas y estadísticas de 7 y 30 días.
- Gráficos de tiempo de uso y pausas por día.

## Arquitectura

El proyecto utiliza una arquitectura de monolito modular y una base SQLite compartida:

- `src/users/`: perfiles y selección de usuario.
- `src/sessions/`: inicio, finalización y persistencia de sesiones.
- `src/wellbeing/`: ciclo de trabajo, pausas, recomendaciones y estadísticas.
- `src/database/`: conexión y esquema SQLite.
- `src/ui/`: interfaz de escritorio y gráficos.
- `src/app/`: configuración y composición de dependencias.
- `tests/`: pruebas organizadas por módulo funcional.

Las tablas históricas de versiones anteriores se conservan por compatibilidad, pero
no forman parte del flujo activo ni se eliminan durante la inicialización.

## Tecnologías

- Python 3.10 o superior.
- PySide6 y Qt Charts.
- SQLite.
- Pytest.

## Instalación

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Ejecución

```bash
python -m src.app.main
```

## Tests

```bash
python -m pytest
```
