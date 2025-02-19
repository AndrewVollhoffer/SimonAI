from vosk import Model, KaldiRecognizer
from pynput.keyboard import Key, Controller
from pynput import keyboard

import sys
import time
import random
import pyaudio
import os
import requests
import pvorca
import struct
import re


############# DECLARATIONS #############

running = True
recording = True

############# INITIALIZATION #############

# KEYBOARD
def on_press(key):
    global running, recording
    if key == keyboard.Key.end:
        if recording:
            print("\nPausing recording.")
            recording = False
        else:
            print("\nResuming recording.")
            recording = True
    elif key == keyboard.Key.esc:
        shut_down()

def on_release(key):
    pass

SimonsHands = Controller()

listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()


# MIC SETUP WITH PYAUDIO
SimonsEars = pyaudio.PyAudio()

device_info = SimonsEars.get_default_input_device_info()
samplerate = int(device_info['defaultSampleRate'])

mic_stream = SimonsEars.open(format=pyaudio.paInt16, channels=1, rate=samplerate, input=True, frames_per_buffer=4096)
mic_stream.start_stream()


# VOICE RECOGNITION SETUP WITH VOSK
# Grab the model you want here: https://alphacephei.com/vosk/models and reference the absolute path
small_boi = Model(r"C:\Users\Andy\Documents\Code\Vosk Models\vosk-model-small-en-us-0.15")

recognizer = KaldiRecognizer(small_boi, samplerate)
recognizer.SetWords(False)


# TEXT TO SPEECH SETUP
access = "tW6PBbt2UIsX2NvdAUnlswex5MsMHgB0ct4CIICZlse/oN4d0bq/yQ=="
voice_model= r"C:\Users\Andy\Documents\Code\Python\SillySimonAI\orca_params_male.pv"
SimonsMouth = pvorca.create(access_key=access, model_path=voice_model)

# OUTPUT STREAM FOR PCM AUDIO
output_stream = SimonsEars.open(format=pyaudio.paInt16, channels=1, rate=23500 , output=True, frames_per_buffer=4096)


# OLLAMA SETUP
OLLAMA_API_URL = "http://localhost:11434/api/generate"


def generate_response(prompt):
    payload = {
        "model": "wizardlm2:7b",  # Replace with the model you pulled
        "prompt": prompt,
        "stream": False  # Set to True if you want streaming responses
    }
    try:
        response = requests.post(OLLAMA_API_URL, json=payload)
        response.raise_for_status()
        return response.json()["response"]
    except requests.exceptions.RequestException as e:
        print(f"Error calling Ollama API: {e}")
        return None

def speak(input):
    voice_input = re.sub(r"[^\x00-\x7F]+", "", input)
    pcm, alignments = SimonsMouth.synthesize(text=voice_input)
    convert = struct.pack(f"{len(pcm)}h", *pcm)
    output_stream.write(convert) 

def shut_down():
    mic_stream.stop_stream()
    mic_stream.close()
    SimonsEars.terminate()
    SimonsMouth.delete()
    listener.stop()


######## START PROGRAM ########k


print("/nStarted recording. Press End to pause or Crtl+C to stop.")
try:
    while running:
        while recording:
            data = mic_stream.read(4096)
            if recognizer.AcceptWaveform(data):
                text = recognizer.Result()
                result = text[14:len(text)-3]

                print("You:", result)

                response = generate_response(result)

                if response:
                    print("\nSimon:", response)
                    speak(response)
            

except KeyboardInterrupt:
    print("\n...Simon was interrupted...")
    shut_down()
    print("\nShut Simon Down.")
    os._exit(1)