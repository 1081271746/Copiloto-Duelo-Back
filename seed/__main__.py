import argparse
import os

from app.core.config import get_settings
from app.database.session import Base, create_database
from seed.demo import seed_demo
from seed.library import seed_library


def main():
    parser = argparse.ArgumentParser(description="Inicializar la base de datos y cargar datos ficticios")
    parser.add_argument("--demo", action="store_true", help="Agregar dos usuarios y registros ficticios")
    args = parser.parse_args()
    settings = get_settings()
    engine, session_factory = create_database(settings.database_url)
    Base.metadata.create_all(engine)
    try:
        with session_factory() as db:
            seed_library(db)
            if args.demo:
                seed_demo(db, settings, os.getenv("DEMO_PASSWORD", ""))
    finally:
        engine.dispose()
    print("Datos iniciales cargados. No se muestran credenciales ni contenido sensible.")


if __name__ == "__main__":
    main()
