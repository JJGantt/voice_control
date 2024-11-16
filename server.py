from quart import Quart, websocket
import asyncio
from voice import VoiceProcessor
import numpy as np
import wave
from dotenv import load_dotenv
import os
import uuid

load_dotenv()
api_key = os.getenv("PICO_API_KEY")
raspberry_path = os.getenv("RASPBERRY_PATH")
oswald_path = os.getenv("OSWALD_PATH")

app = Quart(__name__)

connected_clients = {}

@app.websocket('/ws/audio')
async def audio_stream():
    client_id = str(uuid.uuid4())
    print(f"Client {client_id} connected")

    voice_processor = VoiceProcessor(
        access_key=api_key,
        keyword_paths=[
            raspberry_path,
            oswald_path
        ],
        silence_threshold=60,
        silence_duration=0.5,
        websocket=websocket
    )

    connected_clients[client_id] = {
        "websocket": websocket,
        "processor": voice_processor
    }
    
    try:
        while True:
            audio_data = await websocket.receive()

            if not isinstance(audio_data, bytes):
                print(f"Invalid data type received: {type(audio_data)}")
                continue

            if voice_processor.process_audio(audio_data):
                print(f"Wake word detected for client {client_id}")
                await websocket.send("LED_ON")

            captured_audio = voice_processor.capture_audio(audio_data)
            if captured_audio:
                print(f"Captured spoken command for client {client_id}")
                await websocket.send("LED_OFF")

    except Exception as e:
        print(f"Error with client {client_id}: {e}")
    finally:
        print(f"Client {client_id} disconnected")
        del connected_clients[client_id]
        voice_processor.cleanup()

async def send_to_client(client_id, command):
    if client_id in connected_clients:
        try:
            await connected_clients[client_id].send(command)
            print(f"Sent {command} to {client_id}")
        except Exception as e:
            print(f"Failed to send message to {client_id}: {e}")

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
