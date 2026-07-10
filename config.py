from pathlib import Path

# Constant seed for reproducibility
SEED = 3

# File paths
BASE = Path(__file__).resolve().parent
DATA = BASE / 'data'
RAW = DATA / 'raw'
INPUTS = DATA / 'inputs'
NOMINEES = INPUTS / 'nominees.parquet'
LISTENERS = INPUTS / 'listeners.parquet'
LOG = RAW / 'log.csv'

# Sampling/ingestion constants
MAX_RETRIES = 3
GENRE_COUNT = 18
GENRE_FLOOR = 10
GENRE_CEIL = 250
LISTENER_FLOOR = 100