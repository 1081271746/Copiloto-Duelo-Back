from uuid import NAMESPACE_URL, uuid5

from app.models.entities import Exercise, Resource


EXERCISES = [
    ("grounding", "Reconocer el momento presente", "denial", "Explora lo que percibes sin forzarte a aceptar nada.",
     ["Siéntate en un lugar seguro.", "Nombra cinco cosas que ves y tres sonidos.", "Escribe una frase sobre cómo te sientes; puedes detenerte cuando quieras."], 5),
    ("anger", "Dar palabras a la ira", "anger", "Expresa la ira sin hacerte daño ni dañar a otros.",
     ["Busca un espacio tranquilo.", "Escribe qué te enfada sin juzgarte.", "Deja la hoja y haz una pausa; si aumenta el malestar, detente."], 10),
    ("bargaining", "Una carta compasiva", "bargaining", "Reflexiona sobre pensamientos de culpa con amabilidad.",
     ["Escribe un pensamiento de 'si hubiera'.", "Distingue lo que estaba bajo tu control de lo que no.", "Responde como responderías a una persona querida; no tienes que terminar la carta."], 10),
    ("sadness", "Un pequeño cuidado", "depression", "Elige un cuidado cotidiano posible, sin exigirte sentirte mejor.",
     ["Identifica una necesidad sencilla, como beber agua o descansar.", "Realiza una acción pequeña si te resulta posible.", "Anota cómo te sentiste; busca apoyo profesional si el malestar persiste."], 5),
    ("acceptance", "Un recuerdo significativo", "acceptance", "Da espacio a un recuerdo sin imponer un cierre al duelo.",
     ["Elige un recuerdo que puedas tolerar hoy.", "Escribe qué significa para ti.", "Decide si quieres compartirlo con alguien de confianza; puedes parar en cualquier momento."], 10),
    ("breathing", "Respirar sin exigencias", "anger", "Observa tu respiración natural en un entorno seguro.",
     ["Adopta una postura cómoda.", "Observa tres respiraciones sin retener el aire.", "Detente si aparece mareo o incomodidad."], 3),
]


def seed_library(db):
    for key, title, category, description, instructions, duration in EXERCISES:
        exercise_id = str(uuid5(NAMESPACE_URL, f"grief-copilot/exercises/{key}"))
        if db.get(Exercise, exercise_id) is None:
            db.add(Exercise(id=exercise_id, title=title, category=category, description=description,
                             instructions=instructions, duration_minutes=duration))
    for key, title, description, url, country, category in [
        ("who", "Salud mental y apoyo profesional", "Información general de la OMS; no es una línea de crisis.",
         "https://www.who.int/es/health-topics/mental-health", None, "professional_support"),
        ("colombia", "Recursos territoriales de salud mental", "Consulta fuentes oficiales para encontrar atención local. En peligro inmediato, usa el número local de emergencias.",
         "https://www.minsalud.gov.co/", "CO", "professional_support"),
        ("grief", "Sobre el duelo y el autocuidado", "El duelo no tiene un orden obligatorio. Compartir lo que sientes con una persona de confianza puede ser un apoyo.",
         "https://www.who.int/es/health-topics/mental-health", None, "grief"),
    ]:
        resource_id = str(uuid5(NAMESPACE_URL, f"grief-copilot/resources/{key}"))
        if db.get(Resource, resource_id) is None:
            db.add(Resource(id=resource_id, title=title, description=description, url=url, country=country, category=category))
    db.commit()
