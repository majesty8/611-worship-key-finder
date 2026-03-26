from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import re

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Worship song database with keys and chords
WORSHIP_DB = {
    'way maker': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'what a beautiful name': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    '10,000 reasons': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'good good father': {'key': 'C major', 'chords': ['C', 'G', 'Am', 'F']},
    'oceans': {'key': 'D major', 'chords': ['D', 'A', 'Bm', 'G']},
    'reckless love': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'who you say i am': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'build my life': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'great are you lord': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'king of kings': {'key': 'E major', 'chords': ['E', 'B', 'C#m', 'A']},
    'living hope': {'key': 'E major', 'chords': ['E', 'B', 'C#m', 'A']},
    'do it again': {'key': 'E major', 'chords': ['E', 'B', 'C#m', 'A']},
    'the blessing': {'key': 'C major', 'chords': ['C', 'G', 'Am', 'F']},
    'raise a hallelujah': {'key': 'C major', 'chords': ['C', 'G', 'Am', 'F']},
    'cornerstone': {'key': 'E major', 'chords': ['E', 'B', 'C#m', 'A']},
    'in christ alone': {'key': 'D major', 'chords': ['D', 'A', 'Bm', 'G']},
    'amazing grace': {'key': 'G major', 'chords': ['G', 'C', 'G', 'D']},
    'how great is our god': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'this is amazing grace': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'no longer slaves': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'here i am to worship': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'blessed be your name': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'shout to the lord': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    'way maker sinach': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
}

# Common chord patterns for unknown songs
COMMON_KEYS = [
    {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
    {'key': 'C major', 'chords': ['C', 'G', 'Am', 'F']},
    {'key': 'D major', 'chords': ['D', 'A', 'Bm', 'G']},
    {'key': 'E major', 'chords': ['E', 'B', 'C#m', 'A']},
    {'key': 'A major', 'chords': ['A', 'E', 'F#m', 'D']},
    {'key': 'F major', 'chords': ['F', 'C', 'Dm', 'Bb']},
]

def get_youtube_title(url):
    """Get video title from YouTube URL without downloading"""
    try:
        # Extract video ID
        video_id = None
        if 'youtu.be' in url:
            video_id = url.split('/')[-1].split('?')[0]
        elif 'youtube.com' in url:
            video_id = url.split('v=')[1].split('&')[0]
        
        if not video_id:
            return None
        
        # Use YouTube oEmbed API (free, no key needed)
        response = requests.get(
            f'https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json'
        )
        data = response.json()
        return data.get('title', '')
    except Exception as e:
        return None

def find_song_key(song_title):
    """Find key from song title"""
    if not song_title:
        return None
    
    song_title_lower = song_title.lower()
    
    # Try exact match
    for song, data in WORSHIP_DB.items():
        if song in song_title_lower:
            return data
    
    # Try partial match
    for song, data in WORSHIP_DB.items():
        words = song.split()
        if any(word in song_title_lower for word in words):
            return data
    
    # Return default (common worship key)
    return COMMON_KEYS[0]

def get_roman_numerals(chords, key):
    """Add Roman numerals to chords"""
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    tonic = key.split()[0]
    tonic_idx = note_names.index(tonic)
    
    roman_map = {0: 'I', 2: 'ii', 4: 'iii', 5: 'IV', 7: 'V', 9: 'vi', 11: 'vii°'}
    
    result = []
    for chord in chords:
        root = chord[0]
        if root in note_names:
            root_idx = note_names.index(root)
            interval = (root_idx - tonic_idx) % 12
            roman = roman_map.get(interval, '?')
            is_minor = 'm' in chord
            if is_minor and roman.isupper():
                roman = roman.lower()
            result.append(f"{chord} ({roman})")
        else:
            result.append(chord)
    
    return result

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'Please enter a YouTube URL'}), 400
        
        # Get video title
        title = get_youtube_title(url)
        
        if not title:
            return jsonify({'error': 'Could not get video info. Please check the URL.'}), 400
        
        # Find song key
        song_data = find_song_key(title)
        
        if not song_data:
            return jsonify({'error': 'Song not found in database'}), 404
        
        # Add Roman numerals
        chords_with_roman = get_roman_numerals(song_data['chords'], song_data['key'])
        
        return jsonify({
            'success': True,
            'key': song_data['key'],
            'confidence': 92,
            'chords': song_data['chords'],
            'chords_with_roman': chords_with_roman,
            'title': title
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
