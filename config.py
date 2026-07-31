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
RESOLVED = INPUTS / 'resolved.parquet'
ARTISTS = INPUTS / 'artists.parquet'
ALBUMS = INPUTS / 'albums.parquet'
LOG_L = RAW / 'logL.csv'
LOG_R = RAW / 'logR.csv'
LOG_A = RAW / 'logA.json'

# Sampling/ingestion constants
MAX_RETRIES = 3
GENRE_COUNT = 19
LISTENER_FLOOR = 100