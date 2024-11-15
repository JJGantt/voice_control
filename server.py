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

connected_clients = {}

voice_processor = VoiceProcessor(
    access_key=api_key,
    keyword_path=path,
    silence_threshold=60,
    silence_duration=0.5,
    clients = connected_clients
)

@app.websocket('/ws/audio')
async def audio_stream():
    client_id = websocket.remote_addr[0]  # Use client's IP as an identifier
    connected_clients[client_id] = websocket
    print(f"Client {client_id} connected")
    
    try:
        while True:
            audio_data = await websocket.receive()

            if not isinstance(audio_data, bytes):
                print(f"Invalid data type received: {type(data)}")
                continue

            # Check for wake word detection
            if voice_processor.process_audio(audio_data):
                print("Wake word detected, capturing audio...")
                if client_id in connected_clients:
                    await connected_clients[client_id].send("LED_ON")
                    print(f"Sent LED_ON to {client_id}")

            captured_audio = voice_processor.capture_audio(audio_data)
            if captured_audio:
                print("Captured spoken command")
                await connected_clients[client_id].send("LED_OFF")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        print(f"Client {client_id} disconnected")
        connected_clients.pop(client_id, None)

# Function to send a message to a specific client by ID
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
