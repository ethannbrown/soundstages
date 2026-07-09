# Keys denote non-artist categories, values denote strings that are not allowed in the artist name.
VIOLATIONS = {
    'aggregate': ['various', 'compilation', 'compilations', 'sample'],
    'seo': ['sleep', 'noise', 'meditation', 'yoga', 'study', 'lofi', 'lo-fi', 
            'concentration', 'relaxation', 'instrumental', 'christmas', 'halloween', 'holiday'],
    'role': ['artist', 'vocal', 'actor', 'composer', 'musician', 'ft', 'feat'],
    'instrument': ['violin', 'viola', 'cello', 'bass', 'guitar', 'ukelele', 'harp', 'banjo', 
                   'flute', 'clarinet', 'oboe', 'bassoon', 'saxophone', 'trumpet', 'trombone', 
                   'tuba', 'drum', 'xylophone', 'marimba', 'piano', 'synthesizer'],
    'derivative': ['remix', 'cover', 'tribute', 'karaoke', 'soundtrack', 'ost', 'theme', 'score'],
    'misc': ['asmr', 'podcast', 'traditional', 'anonymous', 'spotify']
}

LOOKUP = {vio for cat, vios in VIOLATIONS.items() for vio in vios}

def depunctuate(name: str) -> str:
    for p in '&.?,!\'+_':
        name = name.replace(p, '')
    return name

def is_artist(name: str) -> bool:
    elements = depunctuate(name).lower().split()
    for element in elements:
        if element in LOOKUP:
            return False
    return True