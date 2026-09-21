from contextlib import closing
from typing import Optional
from fatigue.baseline import UserBaseline, MetricBaseline, BaselineState

class SQLiteBaselineRepository:
    def __init__(self, database_manager):
        self.db = database_manager

    def get_by_user_id(self, user_id: int) -> Optional[UserBaseline]:
        with closing(self.db.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM baselines WHERE user_id = ?", (user_id,))
            row = cursor.fetchone()
            if not row:
                return None
            return self._row_to_baseline(row)

    def save(self, baseline: UserBaseline):
        def _vals(mb: Optional[MetricBaseline]):
            if mb is None:
                return (None, None, None)
            return (mb.mean, mb.std, mb.n_samples)

        ear = _vals(baseline.ear)
        br  = _vals(baseline.blink_rate)
        bd  = _vals(baseline.blink_duration)
        pc  = _vals(baseline.perclos)
        mar = _vals(baseline.mar)
        pit = _vals(baseline.pitch)
        yaw = _vals(baseline.yaw)
        rol = _vals(baseline.roll)

        with closing(self.db.get_connection()) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO baselines (
                    user_id, state,
                    ear_mean, ear_std, ear_samples,
                    blink_rate_mean, blink_rate_std, blink_rate_samples,
                    blink_duration_mean, blink_duration_std, blink_duration_samples,
                    perclos_mean, perclos_std, perclos_samples,
                    mar_mean, mar_std, mar_samples,
                    pitch_mean, pitch_std, pitch_samples,
                    yaw_mean, yaw_std, yaw_samples,
                    roll_mean, roll_std, roll_samples
                ) VALUES (
                    ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                )
                ON CONFLICT(user_id) DO UPDATE SET
                    state=excluded.state,
                    ear_mean=excluded.ear_mean, ear_std=excluded.ear_std, ear_samples=excluded.ear_samples,
                    blink_rate_mean=excluded.blink_rate_mean, blink_rate_std=excluded.blink_rate_std, blink_rate_samples=excluded.blink_rate_samples,
                    blink_duration_mean=excluded.blink_duration_mean, blink_duration_std=excluded.blink_duration_std, blink_duration_samples=excluded.blink_duration_samples,
                    perclos_mean=excluded.perclos_mean, perclos_std=excluded.perclos_std, perclos_samples=excluded.perclos_samples,
                    mar_mean=excluded.mar_mean, mar_std=excluded.mar_std, mar_samples=excluded.mar_samples,
                    pitch_mean=excluded.pitch_mean, pitch_std=excluded.pitch_std, pitch_samples=excluded.pitch_samples,
                    yaw_mean=excluded.yaw_mean, yaw_std=excluded.yaw_std, yaw_samples=excluded.yaw_samples,
                    roll_mean=excluded.roll_mean, roll_std=excluded.roll_std, roll_samples=excluded.roll_samples,
                    updated_at=CURRENT_TIMESTAMP
            """, (
                baseline.user_id, baseline.state.value,
                *ear, *br, *bd, *pc, *mar, *pit, *yaw, *rol
            ))
            conn.commit()

    def _row_to_baseline(self, row) -> UserBaseline:
        def _metric(mean_col, std_col, n_col) -> Optional[MetricBaseline]:
            if row[mean_col] is None:
                return None
            return MetricBaseline(
                mean=row[mean_col], std=row[std_col], n_samples=row[n_col] or 0
            )
        return UserBaseline(
            user_id=row["user_id"],
            state=BaselineState(row["state"]),
            ear=_metric("ear_mean", "ear_std", "ear_samples"),
            blink_rate=_metric("blink_rate_mean", "blink_rate_std", "blink_rate_samples"),
            blink_duration=_metric("blink_duration_mean", "blink_duration_std", "blink_duration_samples"),
            perclos=_metric("perclos_mean", "perclos_std", "perclos_samples"),
            mar=_metric("mar_mean", "mar_std", "mar_samples"),
            pitch=_metric("pitch_mean", "pitch_std", "pitch_samples"),
            yaw=_metric("yaw_mean", "yaw_std", "yaw_samples"),
            roll=_metric("roll_mean", "roll_std", "roll_samples"),
        )
