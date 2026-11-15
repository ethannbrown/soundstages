import re
import unicodedata

import pandas as pd

# Title rules shared by clean_albums.py and clean_tracks.py.


def clean_text(title):
    s = unicodedata.normalize('NFKC', title).lower()
    for a, b in [('’', "'"), ('‘', "'"), ('“', '"'), ('”', '"'), ('&', ' and ')]:
        s = s.replace(a, b)
    return s


# Tracks

# Only matches track "labels" within brackets or after a dash
def in_label(words):
    bracket = rf'[\(\[][^\)\]]*(?:{words})[^\)\]]*[\)\]]'
    dash = rf'\s+[-–—]\s*[^-–—]*(?:{words})'
    return re.compile(f'{bracket}|{dash}', re.I)

# Songs with near identical audio
NEAR_COPIES = in_label(r'instrumental|\binst\b\.?|off[\s-]?vocal|a\s*cc?app?ella|karaoke|\bclean(?:ed)?\b(?!\s+bandit)|edited'
                      r'|radio\s+edit|sped[\s-]?up|slowed|\bscrewed\b(?!\s+up\s+click)|nightcore|\b8d\b|tv\s*size')

# e.g., J mixes, spoken commentary
NOT_SONGS = in_label(r'\basot\s*\d+|\bmixed\b|mix\s+cut|continuous(?:\s+dj)?\s+mix|commentary|interview')

# Labels that don't change the recording at all
NEUTRAL = (r'remaster\w*|\d{4}\s+(?:digital\s+)?remaster\w*|single\s+version|album\s+version|original\s+version'
           r'|mono|stereo|explicit|bonus\s+track|feat\.?|ft\.?|featuring|with\s'
           # 'Original' or 'Original Mix' only as the whole label
           r'|(?:(?<=[\(\[])|(?<=[-–—]\s))original(?:\s+mix)?(?=\s*(?:[\)\]]|$))')

# Common track title labels; shared by a multitude of records
GENERIC = re.compile(r'^(?:intro|outro|interlude|skit|untitled|prelude|reprise|theme|hidden track'
                     r'|bonus track|track \d+|(?:intro|outro|interlude|untitled) \d+)$')

# Features (obviously)
FEAT = re.compile(r'[\(\[]\s*(?:feat\.?|ft\.?|featuring|with)\s', re.I)

# Strips every label for a normalized dataset
def base(title):
    if pd.isna(title):
        return ''
    s = re.sub(r'\s*[\(\[][^\)\]]*[\)\]]', '', clean_text(title))
    s = re.sub(r'\s+[-–—]\s+.*$', '', s)
    return re.sub(r'\s+', ' ', s).strip()

# Recording key: strip only NEUTRAL labels, so "Song - Remastered" matches "Song" but "Song (Live)" doesn't
def recording_key(title):
    if pd.isna(title):
        return ''
    s = re.sub(rf'\s*[\(\[][^\)\]]*(?:{NEUTRAL})[^\)\]]*[\)\]]', '', clean_text(title))
    s = re.sub(rf'\s+[-–—]\s+[^-–—]*(?:{NEUTRAL}).*$', '', s)
    return re.sub(r'\s+', ' ', s).strip()


# Albums

PATTERNS = [
    # Remasters
    r'(digitally\s+|hd\s+)?remaster(ed|s|izado)?(\s+\d{4})?',
    r'\d{4}\s+remaster(ed|izado)?',
    r'original\s+recording\s+remastered', r'the\s+remaster', r're-?issue',

    # Versions
    r'(super\s+)?deluxe(\s+(edition|version))?',
    r'expanded(\s+(edition|version))?',
    r'\d+(st|nd|rd|th)?\s*anniversary(\s+(edition|version))?',
    r'anniversary(\s+(edition|version))?',
    r"(special|limited|collector'?s?|tour|platinum|gold|standard|bonus)\s+(edition|version)",
    r'bonus\s+track(s)?(\s+(edition|version))?',

    # Radio
    r'explicit(\s+(version|content))?', r'clean(\s+version)?',
    r'(radio|single|album)\s+(edit|mix|version)', r'edited(\s+version)?', r'edit',

    # Pressing
    r'mono(\s+(version|mix))?', r'stereo(\s+(version|mix))?',
    r'\d+\s*(inch|\"|\u201d)(\s+(single|mix|version))?',
    r'(lp|ep|45|7\"|12\")\s+version', r'vinyl(\s+(edition|version))?',
    r'digital\s+45', r'\b(single|ep)\b',

    # Regional
    r'international(\s+version)?', r"int'?l(\s+version)?", r'intl',
    r'(japan|japanese|uk|us|u\.s\.|european|eu|spanish|french|german)\s+(edition|version|release)',

    # Format
    r'instrumental(s)?(\s+version)?', r'a\s*cappella', r'karaoke',
    r'(sped[\s-]?up|slowed(\s*(\+|and)\s*reverb)?)(\s+version)?',

]

CREDITS = r'feat\.?\s', r'ft\.?\s', r'featuring\s', r'with\s'

ALT = '|'.join(PATTERNS + list(CREDITS))
BRACKET = re.compile(rf'[\(\[][^\)\]]*(?:{ALT})[^\)\]]*[\)\]]', re.I)
DASH = re.compile(rf'\s+[-\u2013\u2014]\s*[^-\u2013\u2014]*(?:{ALT}).*$', re.I)

def normalize_title(title):
    if pd.isna(title):
        return title

    s = clean_text(str(title))
    s = BRACKET.sub(' ', s)
    s = DASH.sub(' ', s)
    return re.sub(r'\s+', ' ', s).strip()
