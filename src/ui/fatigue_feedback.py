"""Human-readable presentation of existing assessments and configured rules."""
from fatigue.baseline import BaselineState


def level_feedback(level):
    return {
        "NORMAL": ("Sin señales relevantes de fatiga", "Tu estado se mantiene estable.", "#238a5a"),
        "MILD": ("Fatiga leve", "Se detectan señales iniciales de cansancio. Sigue monitoreando tu estado.", "#b77900"),
        "MODERATE": ("Fatiga moderada", "Tu nivel de fatiga está aumentando. Considera una pausa breve.", "#d96812"),
        "HIGH": ("Fatiga alta", "Se detecta fatiga alta. Se recomienda descansar.", "#c93737"),
        "VERY_HIGH": ("Fatiga muy alta", "Se detectan señales muy altas de fatiga. Considera detener la sesión y descansar.", "#831c2c"),
    }[level.value]


def readable_reasons(reasons):
    replacements = (("PERCLOS", "Cierre ocular"), ("baseline", "tu referencia habitual"),
                    ("Head drop", "Inclinación de cabeza"), ("Pitch", "Inclinación de cabeza"),
                    ("pitch", "la cabeza"))
    texts = []
    for reason in reasons[:3]:
        for source, target in replacements:
            reason = reason.replace(source, target)
        texts.append("• " + reason)
    return "\n".join(texts) or "No se detectan señales relevantes de fatiga."


def metric_context(sample, baseline, config):
    ready = baseline and baseline.state == BaselineState.READY
    perclos = sample.perclos.perclos_60s
    reference = baseline.perclos if ready else None
    if perclos is None:
        ocular = "Datos insuficientes"
    else:
        if reference and reference.mean and reference.mean > 0:
            low, high = config.baseline_ratio_range
            threshold = reference.mean * (low + (high - low) * config.active_signal_threshold)
        else:
            low, high = config.perclos_range
            threshold = low + (high - low) * config.active_signal_threshold
        ocular = "Elevado" if perclos >= threshold else "Sin elevación relevante"
    rate = sample.blink_metrics.blinks_per_minute
    reference = baseline.blink_rate if ready else None
    if reference and reference.mean and reference.mean > 0:
        low, high = config.blink_rate_change_range
        changed = abs(rate - reference.mean) / reference.mean >= low + (high-low) * config.active_signal_threshold
        blink = "Fuera de tu rango habitual" if changed else "Dentro de tu rango habitual"
    else:
        blink = "Referencia general; baseline aún no disponible"
    head = sample.head_result
    posture = ("Fuera de tu postura habitual" if head.sustained_deviation else
               "Sin desviación sostenida" if head.has_reference else "Calibrando")
    return f"Cierre ocular: {ocular} · Parpadeos: {blink} · Postura: {posture}"
