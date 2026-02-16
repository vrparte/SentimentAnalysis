"""Seed script for directors."""

import sys
import yaml
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.director import Director


def seed_directors(yaml_file: str):
    """Seed directors from YAML file."""
    db: Session = SessionLocal()
    try:
        with open(yaml_file, "r") as f:
            data = yaml.safe_load(f)

        directors_data = data.get("directors", [])
        if not directors_data:
            print("No directors found in YAML file")
            return

        for dir_data in directors_data:
            existing = db.query(Director).filter(Director.full_name == dir_data["full_name"]).first()
            if existing:
                print(f"Director {dir_data['full_name']} already exists, skipping")
                continue

            director = Director(
                full_name=dir_data["full_name"],
                aliases=dir_data.get("aliases", []),
                context_terms=dir_data.get("context_terms", []),
                negative_terms=dir_data.get("negative_terms", []),
                known_entities=dir_data.get("known_entities", []),
                provider_gdelt_enabled=dir_data.get("provider_gdelt_enabled", True),
                provider_bing_enabled=dir_data.get("provider_bing_enabled", True),
                provider_serpapi_enabled=dir_data.get("provider_serpapi_enabled", False),
                provider_rss_enabled=dir_data.get("provider_rss_enabled", False),
                is_active=dir_data.get("is_active", True),
            )
            db.add(director)
            print(f"Added director: {dir_data['full_name']}")

        db.commit()
        print(f"Successfully seeded {len(directors_data)} directors")
    except Exception as e:
        print(f"Error seeding directors: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m app.seed directors.yaml")
        sys.exit(1)
    seed_directors(sys.argv[1])

