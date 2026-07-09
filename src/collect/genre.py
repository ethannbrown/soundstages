# Spotify's 126 'seed' genres. Initial list, unused. All microgenres ("nodes") cover useful items here.
# SEEDS = ['acoustic', 'afrobeat', 'alt-rock', 'alternative', 'ambient', 'anime', 'black-metal', 'bluegrass', 'blues', 'bossanova', 'brazil', 'breakbeat', 'british', 'cantopop', 'chicago-house', 'children', 'chill', 'classical', 'club', 'comedy', 'country', 'dance', 'dancehall', 'death-metal', 'deep-house', 'detroit-techno', 'disco', 'disney', 'drum-and-bass', 'dub', 'dubstep', 'edm', 'electro', 'electronic', 'emo', 'folk', 'forro', 'french', 'funk', 'garage', 'german', 'gospel', 'goth', 'grindcore', 'groove', 'grunge', 'guitar', 'happy', 'hard-rock', 'hardcore', 'hardstyle', 'heavy-metal', 'hip-hop', 'holidays', 'honky-tonk', 'house', 'idm', 'indian', 'indie', 'indie-pop', 'industrial', 'iranian', 'j-dance', 'j-idol', 'j-pop', 'j-rock', 'jazz', 'k-pop', 'kids', 'latin', 'latino', 'malay', 'mandopop', 'metal', 'metal-misc', 'metalcore', 'minimal-techno', 'movies', 'mpb', 'new-age', 'new-release', 'opera', 'pagode', 'party', 'philippines-opm', 'piano', 'pop', 'pop-film', 'post-dubstep', 'power-pop', 'progressive-house', 'psych-rock', 'punk', 'punk-rock', 'r-n-b', 'rainy-day', 'reggae', 'reggaeton', 'road-trip', 'rock', 'rock-n-roll', 'rockabilly', 'romance', 'sad', 'salsa', 'samba', 'sertanejo', 'show-tunes', 'singer-songwriter', 'ska', 'sleep', 'songwriter', 'soul', 'soundtracks', 'spanish', 'study', 'summer', 'swedish', 'synth-pop', 'tango', 'techno', 'trance', 'trip-hop', 'turkish', 'work-out', 'world-music']

GENRES = {
    'rock': ['rock-and-roll', 'rock', 'album rock', 'classic rock', 'heartland rock', 'hard rock', 'alternative rock', 
             'modern rock', 'glam rock', 'glam metal', 'post-grunge', 'psychedelic rock', 'industrial'],

    'metal': ['metal', 'speed metal', 'thrash metal', 'death metal', 'power metal', 
              'black metal', 'alternative metal', 'nu metal', 'hardcore'],

    'punk': ['punk', 'hardcore punk', 'post-punk'],

    'pop': ['pop', 'dance pop', 'post-teen pop', 'afrobeats', 'uk pop', 
            'alt z', 'k-pop', 'social media pop', 'teen pop'],

    'indie': ['pov: indie', 'indie pop', 'bedroom pop'],
              
    'hip-hop': ['hip hop', 'gangster rap', 'rap', 'hardcore hip hop', 'conscious hip hop', 
                'southern hip hop', 'east coast hip hop', 'west coast rap', 'trap', 'alternative hip hop', 
                'detroit hip hop', 'underground hip hop', 'hyphy', 'uk hip hop', 'plugg', 'rage rap'],

    'r-n-b': ['r&b', 'contemporary r&b', 'neo soul'],
    
    'soul': ['soul', 'quiet storm', 'classic soul', 'motown', 'southern soul', 
             'philly soul', 'soul blues', 'memphis soul', 'chicago soul'],

    'funk': ['funk', 'disco', 'p funk', 'post-disco', 'jazz funk', 'minneapolis sound'],

    'gospel': ['gospel', 'gospel r&b', 'contemporary gospel'],

    'caribbean': ['reggae', 'dub', 'dancehall', 'ska', 'calypso', 'soca', 'konpa'],

    'electronic': ['edm', 'electro house', 'dutch house', 'big room', 'progressive house', 'house', 'drum and bass', 
                   'techno', 'new wave', 'dubstep', 'big beat', 'trance', 'breakbeat', 'hyperpop', 'jungle', 'synthwave'],

    'latin': ['urbano latino', 'trap latino', 'reggaeton', 'latin hip hop', 'latin pop', 'salsa', 
              'samba', 'tango', 'bossa nova','pagode', 'forro', 'sertanejo', 'bachata', 'bolero'],

    'country': ['country', 'country road', 'contemporary country', 'country rock', 
                'classic country pop', 'country dawn', 'outlaw country', 'nashville sound'],

    'folk': ['folk', 'singer-songwriter', 'folk rock', 'mellow gold', 'alternative country', 
             'soft rock', 'contemporary folk', 'bluegrass', 'honky tonk', 'afrobeat'],
    
    'blues': ['blues', 'blues rock', 'country blues', 'modern blues', 'delta blues', 'electric blues', 'acoustic blues', 
              'chicago blues', 'texas blues', 'memphis blues', 'louisiana blues', 'new orleans blues'],

    'jazz': ['jazz', 'bebop', 'hard bop', 'cool jazz', 'vocal jazz', 'contemporary jazz', 
             'swing', 'free jazz', 'avant-garde jazz','jazz fusion', 'smooth jazz', 'acid jazz'],
            
    'ambient': ['ambient', 'drone', 'nu age', 'sound art', 'fourth world', 'drift', 'deep ambient', 'abstract']
}

SUBS = {sub: main for main, subs in GENRES.items() for sub in subs}