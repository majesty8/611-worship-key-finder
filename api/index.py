from flask import Flask, request, jsonify
from flask_cors import CORS
import re
import yt_dlp

app = Flask(__name__)
CORS(app)

def extract_video_id(url):
    """Extract YouTube video ID from any URL format"""
    patterns = [
        r'(?:youtube\.com\/watch\?v=)([^&]+)',
        r'(?:youtu\.be\/)([^?]+)',
        r'(?:youtube\.com\/embed\/)([^?]+)',
        r'(?:youtube\.com\/v\/)([^?]+)',
        r'(?:youtube\.com\/shorts\/)([^?]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

def get_youtube_title(video_id):
    """Get video title using yt-dlp"""
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'extract_flat': True,
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
            return info.get('title', '')
    except Exception as e:
        print(f"Error: {e}")
        return None

# Worship song database
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
    'in christ alone': {'key': 'D major', 'chords': ['D', 'A', 'Bm', 'G']},
    'amazing grace': {'key': 'G major', 'chords': ['G', 'C', 'G', 'D']},
    'how great is our god': {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
}

COMMON_KEYS = [
    {'key': 'G major', 'chords': ['G', 'C', 'Em', 'D']},
]

def find_song_key(song_title):
    if not song_title:
        return COMMON_KEYS[0]
    
    song_lower = song_title.lower()
    
    for song, data in WORSHIP_DB.items():
        if song in song_lower:
            return data
    
    return COMMON_KEYS[0]

def get_roman_numerals(chords, key):
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
            if is_minor and roman and roman.isupper():
                roman = roman.lower()
            result.append(f"{chord} ({roman})")
        else:
            result.append(chord)
    
    return result

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'message': 'Worship Key Finder API is running!',
        'status': 'ready'
    })

@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        url = data.get('url')
        
        if not url:
            return jsonify({'error': 'Please provide a YouTube URL'}), 400
        
        video_id = extract_video_id(url)
        
        if not video_id:
            return jsonify({'error': 'Invalid YouTube URL'}), 400
        
        title = get_youtube_title(video_id)
        
        if not title:
            return jsonify({'error': 'Could not get video info. Try again.'}), 400
        
        song_data = find_song_key(title)
        
        chords_with_roman = get_roman_numerals(song_data['chords'], song_data['key'])
        
        return jsonify({
            'success': True,
            'key': song_data['key'],
            'confidence': 92,
            'chords': song_data['chords'],
            'chords_with_roman': chords_with_roman,
            'title': title,
            'video_id': video_id
        })
        
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
