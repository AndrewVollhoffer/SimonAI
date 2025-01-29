# Currently written for Diddy Kong Racing 64.

from vosk import Model, KaldiRecognizer
from pynput.keyboard import Key, Controller
from pynput import keyboard

import sys
import time
import random
import pyaudio
import os


############# DECLARATIONS #############


LEFT = 'a'
RIGHT = 'd'
UP = 'w'
DOWN = 's'

C_RIGHT = Key.right
C_UP = Key.up

BRAKE = 'j'
DRIVE = 'k'
ACTION = 'l'
L1 = 'q'
R1 = 'e'

running = True
recording = True
driving = False


############# SYSTEM METHODS #############


def shut_down():
    stream.stop_stream()
    stream.close()
    mic.terminate()
    listener.stop()


############# INPUT METHODS #############


def auto_press(key, length = 0.25):
    Simon.press(key)
    time.sleep(length)
    Simon.release(key)

def turn_left():
    print("Turning left")
    with Simon.pressed(DRIVE):
        auto_press(LEFT, .85)

def slight_left():
    print("Turning left")
    with Simon.pressed(DRIVE):
        auto_press(LEFT, .35)

def turn_right():
    print("Turning right")
    with Simon.pressed(DRIVE):
        auto_press(RIGHT, .85)

def slight_right():
    print("Turning right")
    with Simon.pressed(DRIVE):
        auto_press(RIGHT, .35)

def up():
    print("Going up")
    auto_press(UP, 1)

def down():
    print("Going down or backward")
    auto_press(DOWN, 1)

def drive():
   Simon.press(DRIVE)

def brake():
    global driving
    driving = False
    Simon.release(DRIVE)
    print("Braking")
    auto_press(BRAKE, 3)

def reverse():
    global driving
    driving = False
    Simon.release(DRIVE)
    print("Reversing")
    with Simon.pressed(BRAKE):
        auto_press(DOWN, 5)

def reverse_left():
    global driving
    driving = False
    Simon.release(DRIVE)
    print("Reversing left")
    with Simon.pressed(BRAKE):
        with Simon.pressed(DOWN):
            auto_press(LEFT, .5)

def reverse_right():
    global driving
    driving = False
    Simon.release(DRIVE)
    print("Reversing right")
    with Simon.pressed(BRAKE):
        with Simon.pressed(DOWN):
            auto_press(RIGHT, .5)

def use_item():
    print("Using item")
    auto_press(ACTION)

def change_view():
    print("Changing view")
    auto_press(C_UP)

def change_map():
    print("Changing map")
    auto_press(C_RIGHT)


############# KEYBOARD LISTENING METHODS #############


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


############# INITIALIZATION #############

# KEYBOARD
Simon = Controller()

listener = keyboard.Listener(
    on_press=on_press,
    on_release=on_release)
listener.start()

# MIC SETUP WITH PYAUDIO
mic = pyaudio.PyAudio()

device_info = mic.get_default_input_device_info()
samplerate = int(device_info['defaultSampleRate'])

stream = mic.open(format=pyaudio.paInt16, channels=1, rate=samplerate, input=True, frames_per_buffer=4096)
stream.start_stream()

# VOICE RECOGNITION SETUP WITH VOSK
# Grab the model you want here: https://alphacephei.com/vosk/models and reference the absolute path
small_boi = Model(r"C:\Users\Andy\Documents\Code\Vosk Models\vosk-model-small-en-us-0.15")

recognizer = KaldiRecognizer(small_boi, samplerate)
recognizer.SetWords(False)


######## START PROGRAM ########k


print("/nStarted recording. Press Crtl+C or End to stop.")
try:
    while running:
        while recording:
            choice = random.randint(1, 100)
            data = stream.read(4096)
            if recognizer.AcceptWaveform(data):
                text = recognizer.Result()
                result = text[14:len(text)-3]

                print(result)

                if "help" in result or "left" in result:
                    turn_left()
                elif "steak" in result or "stake" in result:
                    slight_left()
                elif "right" in result:
                    turn_right()
                elif "cookies" in result:
                    slight_right()
                elif "up" in result or "forward" in result:
                    up()
                elif "down" in result or "back" in result:
                    down()
                elif "drive" in result or "go" in result:
                    driving = True
                elif "brake" in result or "break" in result or "stop" in result:
                    brake()
                elif "reverse" in result:
                    reverse()
                elif "fuck" in result:
                    reverse_left()
                elif "shit" in result:
                    reverse_right()
                elif "item" in result:
                    use_item()

            else:
                if driving:
                    drive()

            if choice == 1:
                change_view()
            elif choice == 2:
                change_map()
            elif choice >= 3 and choice <= 5:
                use_item()
            

except KeyboardInterrupt:
    print("\n...Simon was interrupted...")

finally:
    shut_down()
    print("\nShut Simon Down.")
    os._exit(1)