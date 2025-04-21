# HLS2FTP - HLS Stream Restreamer

A Python-based tool that restreams HLS (HTTP Live Streaming) content to an FTP server, creating a mirrored stream with automatic segment management and playlist generation.

## Features

- 🎥 Restream HLS content to FTP server
- 🔄 Automatic segment management
- 📝 Dynamic m3u8 playlist generation
- 🧹 Automatic cleanup of old segments
- 🌐 Web interface for easy stream management
- 📱 Mobile-responsive interface
- 🔒 Secure FTP transfer
- ⚡ Real-time stream processing

## Installation

1. Clone the repository:
```bash
git clone https://github.com/okoyausman/hls2ftp.git
cd hls2ftp
```

2. Create a virtual environment (recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Start the Flask server:
```bash
python app.py
```

2. Open your web browser and navigate to `http://localhost:5000`

3. Enter the following information in the web interface:
   - HLS Stream URL (m3u8)
   - FTP Server Host
   - FTP Username
   - FTP Password
   - FTP Path (target directory)

4. Click "Start Stream" to begin the restreaming process

## How It Works

1. **Stream Processing**:
   - Downloads HLS segments from the source stream
   - Uploads segments to the specified FTP server
   - Generates and updates an m3u8 playlist file
   - Automatically cleans up old segments

2. **Playlist Management**:
   - Creates a `playlist.m3u8` file on the FTP server
   - Updates the playlist in real-time as new segments arrive
   - Maintains proper segment order and timing
   - Removes references to deleted segments

3. **Cleanup Process**:
   - Automatically removes segments older than 1 hour
   - Updates playlist after cleanup
   - Runs cleanup checks every 5 minutes

## API Endpoints

- `GET /`: Web interface
- `POST /start_stream`: Start a new stream
  ```json
  {
    "m3u8_url": "https://example.com/stream.m3u8",
    "ftp_host": "ftp.example.com",
    "ftp_user": "username",
    "ftp_pass": "password",
    "ftp_path": "/path/to/stream"
  }
  ```
- `POST /stop_stream`: Stop an active stream
  ```json
  {
    "stream_id": "1234567890"
  }
  ```

## Security Considerations

- Use HTTPS for the web interface in production
- Store FTP credentials securely
- Consider using environment variables for sensitive data
- Implement proper authentication for the web interface

## Dependencies

- Flask 3.0.2
- requests 2.31.0
- ftplib3 0.1.0
- python-dotenv 1.0.1
- m3u8 3.5.0

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

If you encounter any issues or have questions, please open an issue on GitHub.

## Acknowledgments

- Flask for the web framework
- m3u8 for HLS playlist parsing
- Bootstrap for the web interface 