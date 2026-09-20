from dataclasses import dataclass
from typing import List

@dataclass
class Point3D:
    x: float
    y: float
    z: float

@dataclass
class FaceLandmarksResult:
    left_eye: List[Point3D]
    right_eye: List[Point3D]
    mouth: List[Point3D]
    head_orientation_points: List[Point3D]
    all_points: List[Point3D]
