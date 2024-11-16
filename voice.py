import pvporcupine
import pvleopard
import numpy as np
import time
import requests

class VoiceProcessor:
    def __init__(self, keyword_paths=None, access_key=None, sensitivity=1,
                 silence_threshold=60, silence_duration=1.5, grace_period=0.75,
                 max_recording_duration=10.0, clients = None, websocket=None):
        self.websocket = websocket
        self.clients = clients
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keyword_paths=keyword_paths,
            sensitivities=[sensitivity, sensitivity]
        )
        self.leopard = pvleopard.create(access_key=access_key)

        self.sample_rate = self.porcupine.sample_rate
        self.frame_length = self.porcupine.frame_length
        self.audio_buffer = b""
        self.is_recording = False
        self.recording_buffer = b""
        self.recording_start_time = None
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration
        self.grace_period = grace_period
        self.secondary_grace_period = 0.5
        self.max_recording_duration = max_recording_duration
        self.last_non_silent_time = None

    def process_audio(self, audio_chunk):
        self.audio_buffer += audio_chunk

        if len(self.audio_buffer) >= self.frame_length * 2:
            pcm_data = np.frombuffer(self.audio_buffer[:self.frame_length * 2], dtype=np.int16)
            self.audio_buffer = self.audio_buffer[self.frame_length * 2:]

            result = self.porcupine.process(pcm_data)
            if result >= 0:
                print("Wake word detected")
                self.is_recording = True
                self.recording_start_time = time.time()
                self.recording_buffer = b""
                self.last_non_silent_time = time.time()
                return True
        return False

    def capture_audio(self, audio_chunk):
        if self.is_recording:
            self.recording_buffer += audio_chunk

            samples = np.frombuffer(audio_chunk, dtype=np.int16)
            if len(samples) == 0:
                return None

            mean_square = np.mean(np.square(samples))
            volume = np.sqrt(mean_square) if mean_square > 0 else 0

            elapsed_time = time.time() - self.recording_start_time
            if elapsed_time > self.max_recording_duration:
                print("Maximum recording duration reached, stopping recording.")
                return self.transcribe_audio()

            if elapsed_time < self.grace_period:
                self.last_non_silent_time = time.time()
                return None

            #print(f"Volume level: {volume}")

            if volume > self.silence_threshold:
                self.last_non_silent_time = time.time()
            else:
                elapsed_since_speech = time.time() - self.last_non_silent_time
                if elapsed_since_speech > self.silence_duration + self.secondary_grace_period:
                    self.is_recording = False
                    print("Silence detected, stopping recording.")
                    return self.transcribe_audio()
        return None

    def transcribe_audio(self):
        """
        Transcribes the captured audio using Picovoice Leopard and sends the result to the server.
        """
        if self.recording_buffer:
            try:
                print("Transcribing audio...")
                
                samples = np.frombuffer(self.recording_buffer, dtype=np.int16)

                if len(samples) == 0:
                    print("No audio data to transcribe.")
                    self.recording_buffer = b"" 
                    return True

                max_val = np.max(np.abs(samples))
                if max_val > 0:
                    samples = (samples / max_val * 32767).astype(np.int16)

                transcript, words = self.leopard.process(samples)
                
                if not transcript:
                    print("Leopard returned an empty transcript.")
                    self.recording_buffer = b""
                    return True

                print(f"Transcript: {transcript}")
                
                response = self.send_transcript_to_server(transcript)
                if response:
                    print(f"Server Response: {response}")

            except Exception as e:
                print(f"Error during transcription: {e}")
            finally:
                self.recording_buffer = b""
        return True

    def send_transcript_to_server(self, transcript):
        """
        Sends the transcribed text to the server's /api/gpt endpoint.
        """
        url = "http://172.20.6.231:8080/api/gpt"
        headers = {'Content-Type': 'application/json'}
        data = {"prompt": transcript}

        try:
            response = requests.post(url, json=data, headers=headers, timeout=5)
            response.raise_for_status() 
            return response.json()  
        except requests.exceptions.RequestException as e:
            print(f"Error sending transcript to server: {e}")
            return None

    def cleanup(self):
        """Explicitly clean up resources."""
        if self.porcupine is not None:
            self.porcupine.delete()
            self.porcupine = None
        if self.leopard is not None:
            self.leopard.delete()
            self.leopard = None
        print("Resources cleaned up")

    def __del__(self):
        self.cleanup()
