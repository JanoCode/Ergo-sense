from typing import Optional
from fatigue.baseline import UserBaseline, BaselineState
from fatigue.baseline_calibrator import BaselineCalibrator
from fatigue.models import EyeState, MouthState

class BaselineService:
    """
    Orquesta la carga, calibración y persistencia del baseline personal.
    """
    # Cada cuántas muestras persistir en SQLite para no escribir en cada frame
    SAVE_INTERVAL = 100

    def __init__(self, baseline_repository):
        self.repo = baseline_repository
        self._calibrator: Optional[BaselineCalibrator] = None
        self._current_user_id: Optional[int] = None
        self._samples_since_save = 0
        self._baseline_locked = False

    def start_for_user(self, user_id: int):
        """Llamar al iniciar sesión. Carga baseline existente o inicia calibración."""
        self._current_user_id = user_id
        self._calibrator = BaselineCalibrator(user_id)
        self._samples_since_save = 0
        self._baseline_locked = False

        existing = self.repo.get_by_user_id(user_id)
        if existing:
            self._calibrator.restore_from_baseline(existing)
            # Un baseline estable se conserva intacto. Una futura política explícita
            # podrá desbloquear actualizaciones históricas fiables.
            self._baseline_locked = self._calibrator.state == BaselineState.READY

    def add_sample(
        self,
        ear: Optional[float], eye_state: EyeState,
        mar: Optional[float], mouth_state: MouthState,
        pitch: Optional[float], yaw: Optional[float], roll: Optional[float],
        blink_duration: Optional[float] = None,
        blink_bpm: Optional[float] = None,
        perclos: Optional[float] = None,
    ):
        if not self._calibrator or self._baseline_locked:
            return
        self._calibrator.add_ear_sample(ear, eye_state)
        self._calibrator.add_mar_sample(mar, mouth_state)
        self._calibrator.add_head_pose_sample(pitch, yaw, roll)
        if blink_duration is not None:
            self._calibrator.add_blink_duration(blink_duration)
        if blink_bpm is not None:
            self._calibrator.add_blink_rate(blink_bpm)
        if perclos is not None:
            self._calibrator.add_perclos_sample(perclos)

        self._samples_since_save += 1
        if self._samples_since_save >= self.SAVE_INTERVAL:
            self._persist()
            self._samples_since_save = 0

    def get_state(self) -> Optional[BaselineState]:
        return self._calibrator.state if self._calibrator else None

    def get_progress(self) -> float:
        return self._calibrator.progress if self._calibrator else 0.0

    def get_baseline(self) -> Optional[UserBaseline]:
        return self._calibrator.build_baseline() if self._calibrator else None

    def get_deviation(self, metric_name: str, value: float):
        """Compara un valor actual con una métrica disponible del baseline."""
        baseline = self.get_baseline()
        metric = getattr(baseline, metric_name, None) if baseline else None
        return metric.deviation(value) if metric else None

    def finish(self):
        """Llamar al finalizar sesión para persistir datos definitivamente."""
        self._persist()

    def _persist(self):
        if not self._calibrator or self._current_user_id is None or self._baseline_locked:
            return
        baseline = self._calibrator.build_baseline()
        self.repo.save(baseline)
