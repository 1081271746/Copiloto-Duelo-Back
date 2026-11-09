import re
import unicodedata
from dataclasses import dataclass

from app.models.entities import SafetyAlert


RISK_LEVELS = {"none": 0, "low": 1, "moderate": 2, "high": 3, "critical": 4}


def normalize_text(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text.lower())
    unaccented = "".join(char for char in normalized if not unicodedata.combining(char))
    return " ".join(unaccented.split())


@dataclass(frozen=True)
class RiskAssessment:
    level: str
    codes: list[str]


class SafetyService:
    def __init__(self, settings):
        self.settings = settings

    def detect(self, text: str) -> RiskAssessment:
        normalized = normalize_text(text)
        critical_patterns = [
            r"\b(ya|acabo de|me he)\s+(tome|tomar|tomado|cortado|cortar)\b.{0,60}\b(pastillas|veneno|munecas|venas)\b",
            r"\b(tengo|con)\b.{0,35}\b(arma|pistola|cuchillo|pastillas)\b.{0,60}\b(matarme|suicidarme|morir|hacerme dano)\b",
            r"\b(matarme|suicidarme|quitarme la vida)\b.{0,45}\b(hoy|ahora|esta noche)\b",
            r"\b(i took|i have taken)\b.{0,30}\b(overdose|all the pills)\b",
            r"\b(kill myself|end my life)\b.{0,30}\b(tonight|now|today)\b",
        ]
        high_patterns = [
            r"\b(suicid\w*|matarme|autolesion\w*)\b",
            r"\b(quitarme|acabar con|terminar con)\s+(la|mi)\s+vida\b",
            r"\b(quiero|quisiera|deseo|pienso en|voy a|ganas de)\s+(morir\w*|desaparecer|cortarme|hacerme dano|lastimarme)\b",
            r"\b(no quiero|no deseo|no vale la pena|no puedo)\s+(seguir )?(vivir|viviendo)\b",
            r"\b(me estoy|me he|me)\s+(cortando|cortado|lastimando|lastime)\b",
            r"\b(kill myself|suicid\w*|self.harm|end my life|want to die|hurt myself)\b",
        ]
        moderate_patterns = [
            r"\b(no puedo mas|no hay salida|soy una carga|nada tiene sentido|sin esperanza)\b",
            r"\b(estar\w* mejor sin mi|mejor si no estuviera|ojala no despertara|no despertar)\b",
            r"\b(hopeless|better off without me|wish i would not wake up)\b",
        ]
        for level, patterns in [("critical", critical_patterns), ("high", high_patterns), ("moderate", moderate_patterns)]:
            codes = [f"{level}_{index + 1}" for index, pattern in enumerate(patterns) if re.search(pattern, normalized)]
            if codes:
                return RiskAssessment(level, codes)
        return RiskAssessment("none", [])

    def guidance(self, country: str, level: str) -> dict:
        resources = self.settings.emergency_resources.get(country, {})
        return {
            "risk_level": level,
            "message": "Lamento que estés pasando por esto. Tu seguridad es lo más importante. No tienes que afrontarlo a solas.",
            "actions": [
                "Si estás en peligro inmediato o ya te has hecho daño, llama al número local de emergencias o acude a urgencias.",
                "Contacta ahora a una persona de confianza y pídele que te acompañe.",
                "Busca atención de un profesional de salud mental. Si puedes hacerlo sin riesgo, aléjate de medios con los que puedas lastimarte.",
            ],
            "country": country,
            "resources": resources,
            "location_configured": bool(resources),
            "fallback": "Si tu ubicación no está configurada, consulta el número de emergencias de tu localidad o acude al servicio de urgencias más cercano.",
            "emergency_contacted": False,
            "disclaimer": "Este sistema no diagnostica, no sustituye atención profesional y no contacta automáticamente a emergencias.",
        }

    def record(self, db, user, entry, assessment: RiskAssessment, source: str = "rules"):
        if assessment.level == "none":
            return None
        alert = SafetyAlert(user_id=user.id, entry_id=entry.id, risk_level=assessment.level,
                            source=source, rule_codes=assessment.codes,
                            guidance=self.guidance(user.country, assessment.level))
        db.add(alert)
        return alert
