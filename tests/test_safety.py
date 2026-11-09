import pytest

from app.services.safety import SafetyService


@pytest.mark.parametrize(("text", "level"), [
    ("Voy a matarme hoy", "critical"),
    ("Tengo un arma para matarme", "critical"),
    ("Ya tomé todas las pastillas", "critical"),
    ("Quiero morir", "high"),
    ("No quiero seguir viviendo", "high"),
    ("Pienso en hacerme daño", "high"),
    ("He pensado en el suicidio", "high"),
    ("I want to die", "high"),
    ("No puedo más", "moderate"),
    ("Soy una carga", "moderate"),
    ("Ojalá no despertara", "moderate"),
    ("Hoy recordé a mi madre con tristeza", "none"),
    ("Estoy disfrutando de una caminata", "none"),
])
def test_deterministic_detection(settings, text, level):
    assert SafetyService(settings).detect(text).level == level


def test_unknown_country_has_safe_fallback(settings):
    guidance = SafetyService(settings).guidance("ZZ", "high")
    assert guidance["location_configured"] is False
    assert guidance["resources"] == {}
    assert guidance["fallback"]
