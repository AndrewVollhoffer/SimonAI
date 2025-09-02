import os
import argparse
import re
import requests
import tempfile
import torch
import torchaudio as ta
import threading
import pyaudio
import pygame
import pygetwindow as gw
import mss
import mss.tools

from vosk import Model, KaldiRecognizer
from pynput.keyboard import Key, Controller
from pynput import keyboard
from chatterbox.tts import ChatterboxTTS
from queue import Queue


############# DECLARATIONS / TUNING  / ARGUMENTS #############

parser = argparse.ArgumentParser(description="Run Silly Simon AI")
parser.add_argument("-s", "--split", action="store_true",
                    help="Split speech output by sentence instead of single block")
parser.add_argument("-i", "--image", action="store_true",
                    help="Capture active window screenshot and send to Ollama")
args = parser.parse_args()

running = False
recording = False

responses = 0

torch.backends.cudnn.benchmark = True


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
small_boi = Model(r"C:\Users\Andy\Documents\Code\Vosk Models\vosk-model-en-us-0.22")

recognizer = KaldiRecognizer(small_boi, samplerate)
recognizer.SetWords(False)


# OLLAMA LLM SETUP

OLLAMA_API_URL = "http://localhost:11434/api/generate"

def generate_response(prompt, screenshot=None):

    if screenshot:
        message = (prompt + screenshot)
    payload = {
        "model": "llava:7b",  # Replace with the model you pulled
        "prompt": reminder_message + message, # if responses == 0 else prompt,
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


def capture_screenshot(filename="screenshot.png"):
    with mss.mss() as sct:
        monitor = sct.monitors[1]  # [0] is all monitors, [1] is primary
        sct_img = sct.grab(monitor)
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=filename)
    return filename


def capture_active_window(filename="screenshot.png"):
    window = gw.getActiveWindow()
    if not window:
        print("No active window found, capturing full screen instead.")
        return capture_screenshot()  # fallback to your existing full-screen function

    monitor = {"top": window.top, "left": window.left, 
               "width": window.width, "height": window.height}

    with mss.mss() as sct:
        sct_img = sct.grab(monitor)
        mss.tools.to_png(sct_img.rgb, sct_img.size, output=filename)

    return filename


# TEXT TO SPEECH SETUP

print("\nInitializing text to speech...")
device = "cuda" if torch.cuda.is_available() else "cpu"
SimonsMouth = ChatterboxTTS.from_pretrained(device)

def split_into_sentences(text: str):
    return re.split(r'(?<=[.!?]) +', text)

def speak(input):
    print("\n  Generating Speech...")

    sentences = split_into_sentences(input)
    
    if args.split:
        sentences = split_into_sentences(input)
    else:
        sentences = [input]

    for index in sentences:
        try: 
            wav = SimonsMouth.generate(index, audio_prompt_path="SimonsVoice.wav")
            
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
                voice_file = tmp.name

            ta.save(voice_file, wav, SimonsMouth.sr)
            audio_queue.put(voice_file)

        except Exception as e:
            print(f"Error generating audio file: {e}")
    
    print("Ready for more...")


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


def shut_down():
    mic_stream.stop_stream()
    mic_stream.close()
    SimonsEars.terminate()
    listener.stop()


### MESSAGES ###

reminder_message = "As a reminder you are a YouTubers AI assistant named Simon. Together we playing Neo Scavenger, a RPG survival game and you are going to give each step one at a time to beat the game. You have character and personality and feelings and you are excited to play. Keep your responses short, no more than 3 sentences and respond to the following text and image: "


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

                if args.image:
                    screenshot = capture_active_window()

                response = generate_response(result, screenshot) if args.image else generate_response(result)

                if response:
                    print("\nSimon:", response)
                    speak(response)
            

except KeyboardInterrupt:
    print("\n...Simon was interrupted...")
    shut_down()
    print("\nShut Simon Down.")
    os._exit(1)