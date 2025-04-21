from flask import Flask, request, jsonify, render_template
import requests
from ftplib import FTP
import m3u8
import os
import time
from datetime import datetime, timedelta
import threading
from urllib.parse import urlparse
import logging
from collections import defaultdict
from io import BytesIO

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Store active streams
active_streams = defaultdict(dict)

class HLSProcessor:
    def __init__(self, m3u8_url, ftp_host, ftp_user, ftp_pass, ftp_path, stream_id):
        self.m3u8_url = m3u8_url
        self.ftp_host = ftp_host
        self.ftp_user = ftp_user
        self.ftp_pass = ftp_pass
        self.ftp_path = ftp_path
        self.stream_id = stream_id
        self.base_url = self._get_base_url(m3u8_url)
        self.processed_segments = set()
        self.cleanup_thread = None
        self.running = True
        self.playlist_filename = "playlist.m3u8"
        self.segment_duration = None

    def _get_base_url(self, url):
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{os.path.dirname(parsed.path)}/"

    def _download_segment(self, segment_url):
        try:
            response = requests.get(segment_url, stream=True)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Error downloading segment {segment_url}: {str(e)}")
            return None

    def _upload_to_ftp(self, content, filename):
        try:
            with FTP(self.ftp_host) as ftp:
                ftp.login(self.ftp_user, self.ftp_pass)
                ftp.cwd(self.ftp_path)
                
                # Create a BytesIO object from the content
                file_obj = BytesIO(content)
                ftp.storbinary(f'STOR {filename}', file_obj)
                file_obj.close()
            return True
        except Exception as e:
            logger.error(f"Error uploading to FTP: {str(e)}")
            return False

    def _update_playlist(self, segment_filename):
        try:
            with FTP(self.ftp_host) as ftp:
                ftp.login(self.ftp_user, self.ftp_pass)
                ftp.cwd(self.ftp_path)
                
                # Get list of current .ts files
                files = []
                ftp.retrlines('LIST', files.append)
                ts_files = [f.split()[-1] for f in files if f.split()[-1].endswith('.ts')]
                ts_files.sort()  # Sort to maintain order
                
                # Create m3u8 playlist content
                playlist_content = "#EXTM3U\n"
                playlist_content += "#EXT-X-VERSION:3\n"
                playlist_content += f"#EXT-X-TARGETDURATION:{self.segment_duration or 10}\n"
                playlist_content += "#EXT-X-MEDIA-SEQUENCE:0\n"
                
                # Add segments to playlist
                for ts_file in ts_files:
                    playlist_content += f"#EXTINF:{self.segment_duration or 10.0},\n"
                    playlist_content += f"{ts_file}\n"
                
                # Upload updated playlist
                playlist_bytes = BytesIO(playlist_content.encode('utf-8'))
                ftp.storbinary(f'STOR {self.playlist_filename}', playlist_bytes)
                playlist_bytes.close()
                
                logger.info(f"Updated playlist with {len(ts_files)} segments")
                return True
        except Exception as e:
            logger.error(f"Error updating playlist: {str(e)}")
            return False

    def _cleanup_old_segments(self):
        while self.running:
            try:
                with FTP(self.ftp_host) as ftp:
                    ftp.login(self.ftp_user, self.ftp_pass)
                    ftp.cwd(self.ftp_path)
                    
                    # List all files
                    files = []
                    ftp.retrlines('LIST', files.append)
                    
                    # Get current time
                    now = datetime.now()
                    
                    # Delete files older than 1 hour
                    for file_info in files:
                        filename = file_info.split()[-1]
                        if filename.endswith('.ts'):
                            # Get file modification time from FTP
                            mtime = ftp.sendcmd(f'MDTM {filename}')[4:]
                            file_time = datetime.strptime(mtime, '%Y%m%d%H%M%S')
                            
                            if now - file_time > timedelta(hours=1):
                                ftp.delete(filename)
                                logger.info(f"Deleted old segment: {filename}")
                    
                    # Update playlist after cleanup
                    self._update_playlist(None)
            except Exception as e:
                logger.error(f"Error during cleanup: {str(e)}")
            
            time.sleep(300)  # Check every 5 minutes

    def process_stream(self):
        try:
            # Start cleanup thread
            self.cleanup_thread = threading.Thread(target=self._cleanup_old_segments)
            self.cleanup_thread.daemon = True
            self.cleanup_thread.start()

            while self.running:
                try:
                    # Fetch and parse m3u8 playlist
                    playlist = m3u8.load(self.m3u8_url)
                    self.segment_duration = playlist.target_duration
                    
                    for segment in playlist.segments:
                        segment_url = segment.uri
                        if not segment_url.startswith('http'):
                            segment_url = self.base_url + segment_url
                        
                        if segment_url not in self.processed_segments:
                            # Download segment
                            content = self._download_segment(segment_url)
                            if content:
                                # Upload to FTP
                                filename = os.path.basename(segment_url)
                                if self._upload_to_ftp(content, filename):
                                    self.processed_segments.add(segment_url)
                                    logger.info(f"Processed segment: {filename}")
                                    # Update playlist after each new segment
                                    self._update_playlist(filename)
                
                except Exception as e:
                    logger.error(f"Error processing stream: {str(e)}")
                
                time.sleep(playlist.target_duration or 2)  # Wait for next segment

        except Exception as e:
            logger.error(f"Fatal error in stream processing: {str(e)}")
        finally:
            self.running = False
            if self.stream_id in active_streams:
                del active_streams[self.stream_id]

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start_stream', methods=['POST'])
def start_stream():
    data = request.json
    
    required_fields = ['m3u8_url', 'ftp_host', 'ftp_user', 'ftp_pass', 'ftp_path']
    if not all(field in data for field in required_fields):
        return jsonify({'error': 'Missing required fields'}), 400
    
    # Generate a unique stream ID
    stream_id = str(int(time.time()))
    
    processor = HLSProcessor(
        m3u8_url=data['m3u8_url'],
        ftp_host=data['ftp_host'],
        ftp_user=data['ftp_user'],
        ftp_pass=data['ftp_pass'],
        ftp_path=data['ftp_path'],
        stream_id=stream_id
    )
    
    # Store processor in active streams
    active_streams[stream_id]['processor'] = processor
    
    # Start processing in a separate thread
    thread = threading.Thread(target=processor.process_stream)
    thread.daemon = True
    thread.start()
    
    return jsonify({'status': 'Stream processing started', 'stream_id': stream_id})

@app.route('/stop_stream', methods=['POST'])
def stop_stream():
    data = request.json
    stream_id = data.get('stream_id')
    
    if stream_id in active_streams:
        processor = active_streams[stream_id]['processor']
        processor.running = False
        return jsonify({'status': 'Stream stopped'})
    
    return jsonify({'error': 'Stream not found'}), 404

if __name__ == '__main__':
    app.run(debug=True) 