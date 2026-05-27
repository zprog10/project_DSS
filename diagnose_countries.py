import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from dotenv import load_dotenv
import os

load_dotenv(override=True)

SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_PORT = int(os.getenv('SUPABASE_PORT', 5432))
SUPABASE_DB = os.getenv('SUPABASE_DB')
SUPABASE_USER = os.getenv('SUPABASE_USER')
SUPABASE_PASSWORD = os.getenv('SUPABASE_PASSWORD')

def make_engine(host, port, db, user, password, sslmode=None):
    return create_engine(URL.create('postgresql+psycopg2', username=user, password=password, host=host, port=port, database=db, query={'sslmode': sslmode} if sslmode else None))

engine = make_engine(SUPABASE_URL, SUPABASE_PORT, SUPABASE_DB, SUPABASE_USER, SUPABASE_PASSWORD, sslmode='require')

# Query countries table
with engine.connect() as conn:
    df = pd.read_sql(text("SELECT * FROM bronze.countries WHERE _snapshot_id = (SELECT MAX(_snapshot_id) FROM bronze.countries) AND _change_op != 'DELETE' LIMIT 1"), conn)
    print('Columns in bronze.countries:')
    print(df.columns.tolist())
    print('\nFirst row:')
    print(df.iloc[0])
