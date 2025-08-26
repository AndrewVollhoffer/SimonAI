import pyaudio
import pygame
import textwrap
import os
import tempfile
import requests
import re
import torch
import threading

from vosk import Model, KaldiRecognizer
from pynput.keyboard import Key, Controller
from pynput import keyboard
from TTS.api import TTS
from queue import Queue

############# DECLARATIONS #############

running = False
recording = False

############# INITIALIZATION #############

# KEYBOARD
def on_press(key):
    global recording
    if key == keyboard.Key.end and running:
        if recording:
            print("Stopped recording...")
            recording = False
        elif not recording:
            print("Recording...")
            recording = True
    elif key == keyboard.Key.esc:
        shut_down()

def on_release(key):
    pass

print("\nInitializing keyboard...")
SimonsHands = Controller()

listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()


# MIC SETUP WITH PYAUDIO
print("\nInitializing microphone...")
SimonsEars = pyaudio.PyAudio()

device_info = SimonsEars.get_default_input_device_info()
samplerate = int(device_info['defaultSampleRate'])

mic_stream = SimonsEars.open(format=pyaudio.paInt16, channels=1, rate=samplerate, input=True, frames_per_buffer=4096)
mic_stream.start_stream()


# VOICE RECOGNITION SETUP WITH VOSK
# Grab the model you want here: https://alphacephei.com/vosk/models and reference the absolute path
print("\nInitializing voice recognition...")
small_boi = Model(r"C:\Users\Andy\Documents\Code\Vosk Models\vosk-model-small-en-us-0.15")

recognizer = KaldiRecognizer(small_boi, samplerate)
recognizer.SetWords(False)


# TEXT TO SPEECH SETUP
print("\nInitializing text to speech...")
device = "cuda" if torch.cuda.is_available() else "cpu"
SimonsMouth = TTS("tts_models/multilingual/multi-dataset/xtts_v2").to(device)

def speak(input):
    print("\n  Generating Speech...")
    
    # Split text into chunks
    try:  
        print("\n  Splitting text...")
        chunks = textwrap.wrap(
            re.sub(r"[^\x00-\x7F]+", "", input),
            100,
            break_long_words=False,
            replace_whitespace=False
        )

    except Exception as e:
        print(f"Error splitting text: {e}")

    # Iterate through chunks then convert to audio file then play
    try:
        print("\n  Chunking audio...")
        index = 0
        for chunk in chunks:

            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmpfile:
                generated_voice_file = tmpfile.name
                tmpfile.close()

            SimonsMouth.tts_to_file(
                text=chunk,
                file_path=generated_voice_file,
                speaker_wav="SimonsVoice.wav",
                language="en"
                )
            index += 1
            print(f"   - Done {index} of {len(chunks)} chunks.")
            
            audio_queue.put(generated_voice_file)

    except Exception as e:
        print(f"Error generating audio files: {e}")


# AUDIO QUEUE AND THREADING OUTPUT WITH PYGAME
print("\nInitializing audio output...")
pygame.mixer.init()
audio_queue = Queue()

def playback_thread():
    while True:
        temp_file = audio_queue.get()
        if temp_file is None:
            break
        try:
            sound = pygame.mixer.Sound(temp_file)
            channel = sound.play()
            while channel.get_busy():
                pygame.time.wait(50)
        except Exception as e:
            print(f"Cannot play audio file: {e}")
        os.remove(temp_file)
        audio_queue.task_done()

player_thread = threading.Thread(target=playback_thread, daemon=True)
player_thread.start()

# OLLAMA SETUP
OLLAMA_API_URL = "http://localhost:11434/api/generate"

def generate_response(prompt):
    payload = {
        "model": "Tohur/natsumura-storytelling-rp-llama-3.1:8b",  # Replace with the model you pulled
        "prompt": prompt,
        "stream": False  # Set to True if you want streaming responses (not supported)
    }
    try:
        print("\n  Generating response...")
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        return None

def shut_down():
    mic_stream.stop_stream()
    mic_stream.close()
    SimonsEars.terminate()
    listener.stop()


######## START PROGRAM ########

running = True
print("/nProgram started. Press End to record or Crtl+C to stop.")
try:
    while running:
        result = ""
        while recording:
            data = mic_stream.read(4096)
            if recognizer.AcceptWaveform(data):
                text = recognizer.Result()
                result = text[14:len(text)-3]

                if result:
                    print("\nYou:", result)
                    recording = False

                response = generate_response(result)

                if response:
                    print("\nSimon:", response)
                    speak(response)
            

except KeyboardInterrupt:
    print("\n...Simon was interrupted...")
    shut_down()
    print("\nShut Simon Down.")
    os._exit(1)