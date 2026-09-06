import subprocess
import json
import os
import logging

logger = logging.getLogger(__name__)

class FFmpegService:
    @staticmethod
    def extract_metadata(file_path: str) -> dict:
        """Extract audio metadata using ffprobe."""
        try:
            cmd = [
                "ffprobe", 
                "-v", "quiet", 
                "-print_format", "json", 
                "-show_format", 
                "-show_streams", 
                file_path
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            data = json.loads(result.stdout)
            
            # Extract basic info
            format_info = dict(data.get("format", {}))
            duration = float(format_info.get("duration", 0.0))
            
            # Audio stream info
            audio_streams = [s for s in data.get("streams", []) if s.get("codec_type") == "audio"]
            if not audio_streams:
                raise ValueError("No audio stream found in the file.")
                
            stream = audio_streams[0]
            sample_rate = int(stream.get("sample_rate", 0))
            channels = int(stream.get("channels", 0))
            
            return {
                "duration": duration,
                "sample_rate": sample_rate,
                "channels": channels
            }
        except subprocess.CalledProcessError as e:
            logger.error(f"FFprobe error: {e.stderr}")
            raise Exception("Failed to extract audio metadata")
            
    @staticmethod
    def process_to_asr_format(input_path: str, output_path: str) -> str:
        """
        Normalize audio to WAV, mono, 16kHz for ASR processing.
        Requires ffmpeg installed.
        """
        try:
            cmd = [
                "ffmpeg",
                "-y",              # Overwrite output files
                "-i", input_path,  # Input file
                "-ac", "1",        # Mono channel
                "-ar", "16000",    # 16 kHz sample rate
                "-acodec", "pcm_s16le", # PCM 16-bit little-endian
                output_path
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
            return output_path
        except subprocess.CalledProcessError as e:
            logger.error(f"FFmpeg error: {e.stderr}")
            raise Exception("Failed to process audio file")
