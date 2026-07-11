# An expansion (and sophistication) of Spotify's 126 "seed" genres
MAINS = {
    'african': ['afrobeats', 'afropop', 'alte', 'amapiano', 'azonto', 'highlife'], 

    'ambient': ['abstract', 'ambient', 'deep ambient', 'drift', 'drone', 'fourth world', 'nu age', 'sound art'], 

    'blues': ['acoustic blues', 'blues', 'blues rock', 'chicago blues', 'country blues', 'delta blues', 
              'electric blues', 'harmonica blues', 'louisiana blues', 'memphis blues', 'modern blues', 
              'new orleans blues', 'piedmont blues', 'rhythm and blues', 'texas blues', 'traditional blues'], 

    'caribbean': ['calypso', 'dancehall', 'dub', 'kompa', 'reggae', 'ska', 'soca'], 

    'country': ['classic country pop', 'contemporary country', 'country', 'country dawn', 
                'country road', 'country rock', 'nashville sound', 'outlaw country', 'traditional country'], 

    'electronic': ['big beat', 'big room', 'breakbeat', 'drum and bass', 'dubstep', 
                   'dutch house', 'edm', 'electro house', 'electronica', 'house', 
                   'hyperpop', 'jungle', 'progressive house', 'synthwave', 'techno', 'trance'], 

    'folk': ['alternative country', 'bluegrass', 'bluegrass gospel', 'contemporary folk', 'folk', 
             'folk rock', 'honky tonk', 'lilith', 'mellow gold', 'new americana', 'soft rock', 
             'old-time', 'progressive bluegrass', 'singer-songwriter', 'sunshine pop'], 

    'funk': ['afrobeat', 'deep funk', 'disco', 'funk', 'jazz funk', 'p funk', 'post-disco', 'traditional funk'], 

    'gospel': ['contemporary gospel', 'gospel', 'gospel r&b'], 

    'hip-hop': ['alternative hip hop', 'conscious hip hop', 'crunk', 'detroit hip hop', 'drill', 'east coast hip hop', 'experimental hip hop', 
                'gangster rap', 'g funk', 'hardcore hip hop', 'hip hop', 'hyphy', 'plugg', 'psychedelic hip hop', 'rage rap', 'rap', 
                'southern hip hop', 'trap', 'trip hop', 'uk hip hop', 'underground hip hop', 'west coast rap'], 

    'indie': ['baroque pop', 'bedroom pop', 'chamber pop', 'indie jazz', 'indie pop', 'indie soul', 'pov: indie'], 

    'jazz': ['acid jazz', 'avant-garde jazz', 'bebop', 'contemporary jazz', 'cool jazz', 'free jazz', 
             'hard bop', 'jazz', 'jazz fusion', 'smooth jazz', 'spiritual jazz', 'swing', 'vocal jazz'], 

    'latin': ['bachata', 'bolero', 'bossa nova', 'forro', 'latin hip hop', 'latin jazz', 'latin pop', 
              'pagode', 'reggaeton', 'salsa', 'samba', 'sertanejo', 'tango', 'trap latino', 'urbano latino'], 

    'metal': ['alternative metal', 'black metal', 'death metal', 'hardcore', 'metal', 'nu metal', 'power metal', 'speed metal', 'thrash metal'], 

    'pop': ['alt z', 'bubblegum pop', 'dance pop', 'k-pop', 'new romantic', 'new wave', 
            'new wave pop', 'pop', 'post-teen pop', 'social media pop', 'teen pop', 'uk pop'], 

    'punk': ['glam punk', 'hardcore punk', 'oi', 'post-hardcore', 'post-punk', 'punk', 'skate punk'], 

    'r-n-b': ['alternative r&b', 'contemporary r&b', 'neo soul', 'new jack smooth', 'r&b', 'urban contemporary'], 

    'rock': ['album rock', 'alternative rock', 'classic rock', 'glam metal', 'glam rock', 'hard rock', 
             'heartland rock', 'industrial', 'minneapolis sound', 'modern rock', 'post-grunge', 
             'psychedelic rock', 'rock', 'rock-and-roll', 'roots rock', 'southern rock'], 

    'soul': ['chicago soul', 'classic soul', 'memphis soul', 'motown', 'philly soul', 
             'psychedelic soul','quiet storm', 'soul', 'soul blues', 'southern soul']
}

SUBS = {sub: main for main, subs in MAINS.items() for sub in subs}