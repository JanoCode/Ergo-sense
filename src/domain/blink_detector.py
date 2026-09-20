from typing import Optional
import time
from domain.metrics import EyeState, BlinkMetrics

class BlinkConfig:
    MIN_CLOSED_SECONDS = 0.05  # Requiere al menos 50ms para considerarse parpadeo válido

class BlinkDetector:
    def __init__(self, config: BlinkConfig = BlinkConfig()):
        self.config = config
        self.total_blinks = 0
        self.last_blink_duration = 0.0
        self.total_blink_duration = 0.0
        self.session_start_time = time.time()
        
        self._is_closed = False
        self._closed_start_time = None
        
    def reset(self):
        self.total_blinks = 0
        self.last_blink_duration = 0.0
        self.total_blink_duration = 0.0
        self.session_start_time = time.time()
        self._is_closed = False
        self._closed_start_time = None

    def process_state(self, state: EyeState, current_time: float) -> Optional[float]:
        if state == EyeState.UNKNOWN:
            return None
            
        if state == EyeState.CLOSED:
            if not self._is_closed:
                self._is_closed = True
                self._closed_start_time = current_time
            return None
            
        if state == EyeState.OPEN:
            if self._is_closed:
                self._is_closed = False
                if self._closed_start_time is not None:
                    duration = current_time - self._closed_start_time
                    if duration >= self.config.MIN_CLOSED_SECONDS:
                        self.total_blinks += 1
                        self.last_blink_duration = duration
                        self.total_blink_duration += duration
                        return duration
        return None

    def get_metrics(self, current_time: float) -> BlinkMetrics:
        elapsed = current_time - self.session_start_time
        bpm = (self.total_blinks / elapsed * 60) if elapsed > 0 else 0.0
        avg_duration = (self.total_blink_duration / self.total_blinks) if self.total_blinks > 0 else 0.0
        
        return BlinkMetrics(
            total_blinks=self.total_blinks,
            last_blink_duration=self.last_blink_duration,
            avg_blink_duration=avg_duration,
            blinks_per_minute=bpm
        )
