from quart import Quart, websocket
import asyncio
from voice import VoiceProcessor
import numpy as np
import wave
from dotenv import load_dotenv
import os

load_dotenv()
api_key = os.getenv("PICO_API_KEY")
path = os.getenv("KEYWORD_PATH")

app = Quart(__name__)

connected_clients = set()

voice_processor = VoiceProcessor(
    access_key=api_key,
    keyword_path=path,
    silence_threshold=60,
    silence_duration=0.5
)

@app.websocket('/ws/audio')
async def audio_stream():
    print("Client connected")
    try:
        while True:
            audio_data = await websocket.receive()
            
            if voice_processor.process_audio(audio_data):
                print("Wake word detected, capturing audio...")

            captured_audio = voice_processor.capture_audio(audio_data)   #always None 
            if captured_audio:
                print("Captured spoken command")
                save_audio_to_wav("spoken_command.wav", captured_audio)  #not in use
    except Exception as e:
        print(f"Error: {e}")
    finally:
        print("Client disconnected")

#for testing
def save_audio_to_wav(filename, audio_data):     
    """ Save int16 audio samples to a WAV file """
    samples = np.frombuffer(audio_data, dtype=np.int16)
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(16000)
        wav_file.writeframes(samples.tobytes())
    print(f"Saved audio to {filename}")

@app.route('/')
async def index():
    return "Server running"

if __name__ == '__main__':
    import hypercorn.asyncio
    from hypercorn.config import Config

    config = Config()
    config.bind = ["0.0.0.0:8000"]
    asyncio.run(hypercorn.asyncio.serve(app, config))
