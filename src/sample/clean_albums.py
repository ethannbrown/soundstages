import sys, re, unicodedata
import pandas as pd

sys.path.append('.')  # Run from project root
from config import ALBUMS, ALBUMS_CLEAN

PATTERNS = [
    # Remasters
    r"(digitally\s+|hd\s+)?remaster(ed|s|izado)?(\s+\d{4})?",
    r"\d{4}\s+remaster(ed|izado)?",
    r"original\s+recording\s+remastered", r"the\s+remaster", r"re-?issue",

    # Versions
    r"(super\s+)?deluxe(\s+(edition|version))?",
    r"expanded(\s+(edition|version))?",
    r"\d+(st|nd|rd|th)?\s*anniversary(\s+(edition|version))?",
    r"anniversary(\s+(edition|version))?",
    r"(special|limited|collector'?s?|tour|platinum|gold|standard|bonus)\s+(edition|version)",
    r"bonus\s+track(s)?(\s+(edition|version))?",

    # Radio
    r"explicit(\s+(version|content))?", r"clean(\s+version)?",
    r"(radio|single|album)\s+(edit|mix|version)", r"edited(\s+version)?", r"edit",

    # Pressing
    r"mono(\s+(version|mix))?", r"stereo(\s+(version|mix))?",
    r"\d+\s*(inch|\"|\u201d)(\s+(single|mix|version))?",
    r"(lp|ep|45|7\"|12\")\s+version", r"vinyl(\s+(edition|version))?",
    r"digital\s+45", r"\b(single|ep)\b",

    # Regional
    r"international(\s+version)?", r"int'?l(\s+version)?", r"intl",
    r"(japan|japanese|uk|us|u\.s\.|european|eu|spanish|french|german)\s+(edition|version|release)",

    # Format
    r"instrumental(s)?(\s+version)?", r"a\s*cappella", r"karaoke",
    r"(sped[\s-]?up|slowed(\s*(\+|and)\s*reverb)?)(\s+version)?",

]

CREDITS = r"feat\.?\s", r"ft\.?\s", r"featuring\s", r"with\s"

ALT = "|".join(PATTERNS)
BRACKET = re.compile(rf"[\(\[][^\)\]]*(?:{ALT})[^\)\]]*[\)\]]", re.I)
DASH = re.compile(rf"\s+[-\u2013\u2014]\s*[^-\u2013\u2014]*(?:{ALT}).*$", re.I)

def normalize_title(title):
    if pd.isna(title):
        return title
    
    s = unicodedata.normalize("NFKC", str(title))
    for a, b in [("\u2019", "'"), ("\u2018", "'"),
                 ("\u201c", '"'), ("\u201d", '"'), ("&", " and ")]:
        s = s.replace(a, b)

    s = s.lower()
    s = BRACKET.sub(" ", s)
    s = DASH.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()

df = pd.read_parquet(ALBUMS)
df = df.dropna(subset=["albumID"])

df["year"] = pd.to_numeric(df["released"].str[:4], errors="coerce").astype("Int64")

df = df[df["type"] != "compilation"]

df = df.sort_values(["albumID", "uuid"]).drop_duplicates(subset="albumID")

df["norm"] = df["title"].map(normalize_title)
df = (df.sort_values(["popularity", "albumID"], ascending=[False, True])
        .drop_duplicates(subset=["uuid", "norm", "tracks"]))

df = df.sort_index()
df.to_parquet(ALBUMS_CLEAN)