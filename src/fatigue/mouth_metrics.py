import math
from typing import Optional
from monitoring.models import FaceLandmarksResult, Point3D
from fatigue.models import MouthState

class MARConfig:
    MAR_THRESHOLD = 0.5  # Umbral para considerar boca abierta

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
    if horiz == 0:
        return None
    vert1 = euclidean_distance_2d(p_top1, p_bottom1)
    vert2 = euclidean_distance_2d(p_top2, p_bottom2)
    return (vert1 + vert2) / (2.0 * horiz)

def get_mouth_state(
    landmarks: Optional[FaceLandmarksResult],
    config: MARConfig = MARConfig()
) -> tuple[Optional[float], MouthState]:
    """
    Devuelve (mar_value, MouthState).
    Nunca convierte ausencia de datos en CLOSED.
    """
    if not landmarks or not landmarks.all_points or len(landmarks.all_points) < 468:
        return None, MouthState.UNKNOWN

    pts = landmarks.all_points
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

    state = MouthState.OPEN if mar >= config.MAR_THRESHOLD else MouthState.CLOSED
    return mar, state
