import math
from typing import Optional
from monitoring.models import FaceLandmarksResult, Point3D
from fatigue.models import MouthState

class MARConfig:
    MAR_THRESHOLD = 0.5  # Umbral para considerar boca abierta
    BASELINE_MIN_SAMPLES = 30
    BASELINE_STD_MULTIPLIER = 3.0
    BASELINE_MIN_MARGIN = 0.20

def euclidean_distance_2d(p1: Point3D, p2: Point3D) -> float:
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def calculate_mar_from_points(
    p_left: Point3D, p_right: Point3D,
    p_top1: Point3D, p_bottom1: Point3D,
    p_top2: Point3D, p_bottom2: Point3D
) -> Optional[float]:
    """
    MAR = (|top1-bottom1| + |top2-bottom2|) / (2 * |left-right|)
    """
    horiz = euclidean_distance_2d(p_left, p_right)
    if not all(math.isfinite(v) for p in (p_left, p_right, p_top1, p_bottom1, p_top2, p_bottom2) for v in (p.x, p.y)) or horiz == 0:
        return None
    vert1 = euclidean_distance_2d(p_top1, p_bottom1)
    vert2 = euclidean_distance_2d(p_top2, p_bottom2)
    return (vert1 + vert2) / (2.0 * horiz)

def get_mouth_state(
    landmarks: Optional[FaceLandmarksResult],
    config: MARConfig = MARConfig(),
    frame_width: float = 1.0, frame_height: float = 1.0,
    baseline=None,
) -> tuple[Optional[float], MouthState]:
    """
    Devuelve (mar_value, MouthState).
    Nunca convierte ausencia de datos en CLOSED.
    """
    if not landmarks or not landmarks.all_points or len(landmarks.all_points) < 468:
        return None, MouthState.UNKNOWN

    if not all(math.isfinite(v) and v > 0 for v in (frame_width, frame_height)):
        return None, MouthState.UNKNOWN
    # MediaPipe normalizes x and y independently. Restore isotropic image units.
    pts = [Point3D(p.x * frame_width, p.y * frame_height, p.z)
           for p in landmarks.all_points]
    # Esquinas de la boca: 61 (izq), 291 (der)
    # Par superior: 82 (arriba-izq), 13 (arriba-centro)
    # Par inferior: 87 (abajo-izq), 14 (abajo-centro)
    mar = calculate_mar_from_points(
        pts[61], pts[291],
        pts[82], pts[87],
        pts[13], pts[14]
    )

    if mar is None:
        return None, MouthState.UNKNOWN

    threshold = config.MAR_THRESHOLD
    # Personalization only raises the general floor: ordinary speech must not
    # become a yawn merely because the resting mouth aperture is small.
    if (baseline and baseline.n_samples >= config.BASELINE_MIN_SAMPLES and baseline.mean is not None
            and math.isfinite(baseline.mean) and baseline.mean >= 0):
        std = baseline.std if baseline.std is not None and math.isfinite(baseline.std) else 0
        threshold = max(threshold, baseline.mean + max(
            config.BASELINE_STD_MULTIPLIER * std, config.BASELINE_MIN_MARGIN
        ))
    state = MouthState.OPEN if mar >= threshold else MouthState.CLOSED
    return mar, state
