import os
import tempfile
import logging
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import yt_dlp
import librosa
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static', static_url_path='')
CORS(app)

# Create necessary directories
os.makedirs('static', exist_ok=True)

NOTE_NAMES = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']

class WorshipKeyDetector:
    def __init__(self):
        self.note_names = NOTE_NAMES
        self.worship_patterns = [
            [4, 5, 1, 6], [6, 4, 1, 5], [1, 5, 6, 4],
            [4, 1, 5, 6], [2, 5, 1, 4], [6, 5, 4, 1]
        ]
    
    def extract_chords(self, audio_path):
        try:
            y, sr = librosa.load(audio_path, sr=22050, duration=180)
            chroma = librosa.feature.chroma_cqt(y=y, sr=sr)
            tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
            beat_frames = beats if len(beats) > 4 else np.arange(0, chroma.shape[1], int(2 * sr / 512))
            
            chords = []
            for i in range(len(beat_frames) - 1):
                start = beat_frames[i]
                end = beat_frames[i+1]
                if start >= chroma.shape[1]:
                    break
                end = min(end, chroma.shape[1])
                segment = chroma[:, start:end].mean(axis=1)
                root = np.argmax(segment)
                third_major = segment[(root + 4) % 12]
                third_minor = segment[(root + 3) % 12]
                quality = 'major' if third_major >= third_minor else 'minor'
                chords.append({
                    'root': root,
                    'quality': quality,
                    'name': f"{self.note_names[root]}{'m' if quality == 'minor' else ''}"
                })
            
            # Remove duplicates
            unique = []
            for c in chords:
                if not unique or unique[-1]['name'] != c['name']:
                    unique.append(c)
            return unique
        except Exception as e:
            logger.error(f"Chord extraction error: {e}")
            return []
    
    def find_key(self, chords):
        if not chords:
            return None, 0
        
        chord_roots = [c['root'] for c in chords]
        unique_roots = list(set(chord_roots))
        
        best_key = None
        best_score = 0
        best_mode = 'major'
        
        for tonic in range(12):
            diatonic = [tonic, (tonic+2)%12, (tonic+4)%12, (tonic+5)%12, (tonic+7)%12, (tonic+9)%12, (tonic+11)%12]
            score = sum(1 for r in unique_roots if r in diatonic)
            if len(chords) >= 4:
                relative = [(chords[i]['root'] - tonic) % 12 for i in range(4)]
                if relative in self.worship_patterns:
                    score += 3
            if score > best_score:
                best_score = score
                best_key = tonic
                best_mode = 'major'
        
        for tonic in range(12):
            diatonic = [tonic, (tonic+2)%12, (tonic+3)%12, (tonic+5)%12, (tonic+7)%12, (tonic+8)%12, (tonic+10)%12]
            score = sum(1 for r in unique_roots if r in diatonic)
            if score > best_score:
                best_score = score
                best_key = tonic
                best_mode = 'minor'
        
        confidence = (best_score / max(len(unique_roots), 1)) * 100
        return f"{NOTE_NAMES[best_key]} {best_mode}", min(confidence, 98)
    
    def add_roman_numerals(self, chords, key):
        tonic = key.split()[0]
        tonic_idx = NOTE_NAMES.index(tonic)
        roman_map = {0: 'I', 2: 'ii', 4: 'iii', 5: 'IV', 7: 'V', 9: 'vi', 11: 'vii°'}
        result = []
        for c in chords:
            interval = (c['root'] - tonic_idx) % 12
            roman = roman_map.get(interval, '?')
            if c['quality'] == 'minor' and roman.isupper():
                roman = roman.lower()
            result.append(f"{c['name']} ({roman})")
        return result

def download_audio(url):
    try:
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_path = temp_file.name
        temp_file.close()
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'outtmpl': temp_path.replace('.wav', ''),
            'quiet': True,
            'no_warnings': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if filename.endswith('.webm'):
                filename = filename.replace('.webm', '.wav')
            elif not filename.endswith('.wav'):
                filename += '.wav'
            return filename
    except Exception as e:
        raise Exception(f"Download failed: {str(e)}")

@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        url = data.get('url')
        if not url:
            return jsonify({'error': 'No URL provided'}), 400
        
        logger.info(f"Analyzing: {url}")
        audio_path = download_audio(url)
        
        try:
            detector = WorshipKeyDetector()
            chords = detector.extract_chords(audio_path)
            if not chords:
                return jsonify({'error': 'Could not detect chords'}), 400
            
            key, confidence = detector.find_key(chords)
            chords_with_roman = detector.add_roman_numerals(chords, key)
            
            return jsonify({
                'success': True,
                'key': key,
                'confidence': confidence,
                'chords': [c['name'] for c in chords][:20],
                'chords_with_roman': chords_with_roman[:20]
            })
        finally:
            if os.path.exists(audio_path):
                os.remove(audio_path)
    except Exception as e:
        logger.error(f"Error: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)