import math
from typing import Optional
from domain.facial_landmarks import FaceLandmarksResult, Point3D
from domain.metrics import EyeState, EyeMetricsResult

class EARConfig:
    EAR_THRESHOLD = 0.20

def euclidean_distance(p1: Point3D, p2: Point3D) -> float:
    return math.sqrt((p1.x - p2.x)**2 + (p1.y - p2.y)**2)

def calculate_ear_from_points(p1: Point3D, p2: Point3D, p3: Point3D, p4: Point3D, p5: Point3D, p6: Point3D) -> Optional[float]:
    horiz_dist = euclidean_distance(p1, p4)
    vert_dist1 = euclidean_distance(p2, p6)
    vert_dist2 = euclidean_distance(p3, p5)
    
    if horiz_dist == 0:
        return None
        
    return (vert_dist1 + vert_dist2) / (2.0 * horiz_dist)

def get_eye_state(landmarks: Optional[FaceLandmarksResult], config: EARConfig = EARConfig()) -> EyeMetricsResult:
    if not landmarks or not landmarks.all_points or len(landmarks.all_points) < 468:
        return EyeMetricsResult(None, None, None, EyeState.UNKNOWN)
        
    pts = landmarks.all_points
    # Left eye: 33, 159, 158, 133, 144, 145
    ear_left = calculate_ear_from_points(pts[33], pts[159], pts[158], pts[133], pts[144], pts[145])
    # Right eye: 362, 385, 386, 263, 374, 380
    ear_right = calculate_ear_from_points(pts[362], pts[385], pts[386], pts[263], pts[374], pts[380])
    
    if ear_left is None or ear_right is None:
        return EyeMetricsResult(ear_left, ear_right, None, EyeState.UNKNOWN)
        
    ear_avg = (ear_left + ear_right) / 2.0
    
    state = EyeState.CLOSED if ear_avg < config.EAR_THRESHOLD else EyeState.OPEN
    return EyeMetricsResult(ear_left, ear_right, ear_avg, state)
