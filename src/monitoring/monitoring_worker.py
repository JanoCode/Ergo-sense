from dataclasses import dataclass
import logging
import threading
import time
from typing import Any, Optional

import numpy as np
from PySide6.QtCore import QThread, Signal

from fatigue.blink_detector import BlinkDetector
from fatigue.eye_metrics import get_eye_state
from fatigue.head_pose import HeadPoseEstimator
from fatigue.models import EyeState
from fatigue.mouth_metrics import get_mouth_state
from fatigue.perclos import PerclosCalculator, ProlongedClosureDetector
from fatigue.yawn_detector import YawnDetector


logger = logging.getLogger(__name__)


@dataclass
class MonitoringSample:
    frame_rgb: np.ndarray
    analyzed: bool = False
    face_detected: bool = False
    current_time: Optional[float] = None
    eye_metrics: Any = None
    blink_duration: Optional[float] = None
    blink_metrics: Any = None
    perclos: Any = None
    closure_result: Any = None
    mar: Optional[float] = None
    mouth_state: Any = None
    yawn_metrics: Any = None
    head_result: Any = None


class MonitoringWorker(QThread):
    """Captures frames and computes facial metrics outside the UI thread."""

    sample_ready = Signal(object)
    camera_ready = Signal(int, int, int, float)
    error = Signal(str)

    def __init__(
        self,
        camera_service,
        face_analyzer_factory,
        blink_detector: BlinkDetector,
        perclos_calculator: PerclosCalculator,
        prolonged_detector: ProlongedClosureDetector,
        yawn_detector: YawnDetector,
        head_pose_estimator: HeadPoseEstimator,
        analysis_fps: float = 10.0,
        display_fps: float = 30.0,
        parent=None,
    ):
        super().__init__(parent)
        self.camera_service = camera_service
        self.face_analyzer_factory = face_analyzer_factory
        self.blink_detector = blink_detector
        self.perclos_calculator = perclos_calculator
        self.prolonged_detector = prolonged_detector
        self.yawn_detector = yawn_detector
        self.head_pose_estimator = head_pose_estimator
        self.analysis_interval = 1.0 / max(analysis_fps, 1.0)
        self.display_interval = 1.0 / max(display_fps, 1.0)
        self._stop_event = threading.Event()
        self._last_analysis = 0.0
        self._last_metric_time = 0.0
        self._face_analyzer = None

    def request_stop(self):
        self._stop_event.set()

    def run(self):
        logger.info("Iniciando worker de monitoreo")
        try:
            if not self.camera_service.start():
                self.error.emit(
                    "No se encontró una webcam disponible en los índices 0, 1 o 2. "
                    "La sesión continuará sin video."
                )
                return

            index, width, height, fps = self.camera_service.properties()
            self.camera_ready.emit(index if index is not None else -1, width, height, fps)

            try:
                factory = self.face_analyzer_factory
                self._face_analyzer = factory() if callable(factory) else factory
                logger.info("MediaPipe FaceLandmarker inicializado correctamente")
            except Exception as exc:
                logger.exception("No se pudo iniciar FaceLandmarker")
                self.error.emit(f"La cámara inició, pero FaceLandmarker falló: {exc}")

            while not self._stop_event.is_set():
                loop_started = time.perf_counter()
                frame_rgb = self.camera_service.get_frame()
                if frame_rgb is None:
                    self.msleep(25)
                    continue

                now = time.time()
                should_analyze = (
                    self._face_analyzer is not None
                    and now - self._last_analysis >= self.analysis_interval
                )
                if should_analyze:
                    self._last_analysis = now
                    sample = self._analyze(frame_rgb, now)
                else:
                    sample = MonitoringSample(frame_rgb=frame_rgb)
                self.sample_ready.emit(sample)

                remaining = self.display_interval - (time.perf_counter() - loop_started)
                if remaining > 0:
                    self.msleep(max(1, int(remaining * 1000)))
        except Exception as exc:
            logger.exception("Error inesperado en el worker de monitoreo")
            self.error.emit(f"Error durante el monitoreo: {exc}")
        finally:
            analyzer = self._face_analyzer
            self._face_analyzer = None
            if analyzer is not None:
                analyzer.close()
            self.camera_service.stop()
            logger.info("Worker de monitoreo detenido")

    def _analyze(self, frame_rgb, current_time):
        result = self._face_analyzer.analyze_frame(frame_rgb)
        face_detected = result is not None
        eye_metrics = get_eye_state(result)
        blink_duration = self.blink_detector.process_state(
            eye_metrics.state, current_time
        )
        blink_metrics = self.blink_detector.get_metrics(current_time)

        if self._last_metric_time > 0 and eye_metrics.state != EyeState.UNKNOWN:
            self.perclos_calculator.add_event(
                current_time,
                eye_metrics.state,
                current_time - self._last_metric_time,
            )
        self._last_metric_time = current_time
        self.prolonged_detector.process_state(eye_metrics.state, current_time)
        perclos = self.perclos_calculator.get_perclos(current_time)
        closure_result = self.prolonged_detector.get_result(current_time)

        mar, mouth_state = get_mouth_state(result)
        self.yawn_detector.process_state(mouth_state, current_time)
        yawn_metrics = self.yawn_detector.get_metrics(current_time)

        height, width = frame_rgb.shape[:2]
        head_result = self.head_pose_estimator.process(
            result, width, height, current_time
        )
        rendered_frame = (
            self._face_analyzer.draw_landmarks(frame_rgb, result)
            if result is not None else frame_rgb
        )
        return MonitoringSample(
            frame_rgb=rendered_frame,
            analyzed=True,
            face_detected=face_detected,
            current_time=current_time,
            eye_metrics=eye_metrics,
            blink_duration=blink_duration,
            blink_metrics=blink_metrics,
            perclos=perclos,
            closure_result=closure_result,
            mar=mar,
            mouth_state=mouth_state,
            yawn_metrics=yawn_metrics,
            head_result=head_result,
        )
