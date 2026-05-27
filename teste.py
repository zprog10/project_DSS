import os

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL


load_dotenv()


def build_engine():
    return create_engine(
        URL.create(
            "postgresql+psycopg2",
            username=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            host=os.getenv("SUPABASE_URL"),
            port=int(os.getenv("SUPABASE_PORT", "5432")),
            database=os.getenv("SUPABASE_DB", "postgres"),
            query={"sslmode": "require"},
        )
    )


engine = build_engine()

with engine.connect() as conn:
    result = conn.execute(text("SELECT 1"))
    print("Connection OK:", result.scalar_one())