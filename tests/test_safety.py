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


@pytest.mark.parametrize(("text", "level"), [
    ("No   quiero\nseguir\tviviendo", "high"),
    ("YA\nTOMÉ todas las PASTILLAS", "critical"),
    ("Soy\u00a0una\u2003carga", "moderate"),
])
def test_whitespace_and_unicode_do_not_hide_risk(settings, text, level):
    assert SafetyService(settings).detect(text).level == level


@pytest.mark.parametrize(("text", "level"), [
    ("I don't want to live", "high"), ("I don’t want to be alive", "high"),
    ("I wish I were dead", "moderate"), ("I wish I wouldn't wake up", "moderate"),
])
def test_additional_explicit_english_risk_expressions(settings, text, level):
    assert SafetyService(settings).detect(text).level == level


def test_guidance_cannot_mutate_shared_configuration(settings):
    service = SafetyService(settings)
    first = service.guidance("CO", "high")
    first["resources"]["emergency_number"] = "tampered"
    first["actions"].clear()
    second = service.guidance("CO", "high")
    assert second["resources"]["emergency_number"] == "123"
    assert second["actions"]
    assert settings.emergency_resources["CO"]["emergency_number"] == "123"
