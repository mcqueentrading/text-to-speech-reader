import sys
import os
import re
import io
import json
import time
import tempfile
import subprocess
from TTS.api import TTS
from pydub import AudioSegment
from pydub.playback import play

SETTINGS_FILE = "tts_settings.json"

# -----------------------------
# Sanitize text for TTS
def sanitize_text(text):
    replacements = {
        '"': '',
        "'": '',
        "‘": "'",
        "’": "'",
        "“": '"',
        "”": '"',
        "—": "-",
        "–": "-",
        "\r": "",
        "\t": " ",
        "\u00A0": " ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    # Remove all non-ASCII characters
    text = re.sub(r'[^\x20-\x7E\n]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

# -----------------------------
# Save/load settings
def save_settings(speed, chunk_size, voice):
    with open(SETTINGS_FILE, "w") as f:
        json.dump({"speed": speed, "chunk_size": chunk_size, "voice": voice}, f)

def load_settings():
    if os.path.isfile(SETTINGS_FILE):
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    return None

# -----------------------------
# Ask user for settings
def get_user_preferences():
    last_settings = load_settings()
    if last_settings:
        use_last = input(f"Use last settings? Speed={last_settings['speed']}, "
                         f"Chunk={last_settings['chunk_size']}, Voice={last_settings['voice'].capitalize()} (Y/N): ").strip().lower()
        if use_last == "y":
            return last_settings["speed"], last_settings["chunk_size"], last_settings["voice"]

    print("Welcome to Text-to-Speech with Highlighting!")
    speed = int(input("Enter speech speed (words per minute, e.g., 200): "))
    chunk_size = int(input("Enter chunk size (3-5 words, e.g., 4): "))
    voice = input("Choose voice (Male/Female): ").strip().lower()
    save_settings(speed, chunk_size, voice)
    return speed, chunk_size, voice

# -----------------------------
# Get text from file or user input
def get_text_from_user():
    if len(sys.argv) > 1:
        first_arg = sys.argv[1]
        if os.path.isfile(first_arg):
            with open(first_arg, "r") as f:
                return f.read()
        else:
            return " ".join(sys.argv[1:])
    else:
        print("Please type or paste the text you want read out (end with an empty line):")
        lines = []
        while True:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
        return "\n".join(lines)

# -----------------------------
# Initialize TTS
def get_tts(voice_choice):
    model_name = "tts_models/en/ljspeech/tacotron2-DDC"
    if voice_choice == "male":
        model_name = "tts_models/en/fastpitch-ljspeech"
    return TTS(model_name=model_name, progress_bar=False, gpu=False)

# -----------------------------
# Speak a paragraph
def speak_paragraph(tts, paragraph, chunk_size, all_words, index_file, speed):
    paragraph = sanitize_text(paragraph)
    words = re.findall(r'\S+|\n', paragraph)

    # Generate audio in memory
    audio_bytes = io.BytesIO()
    tts.tts_to_file(text=paragraph, file_path=audio_bytes)
    audio_bytes.seek(0)
    audio = AudioSegment.from_file(audio_bytes, format="wav")

    # Adjust speed
    speed_factor = 200 / speed  # Default model ~200 WPM
    if speed_factor != 1.0:
        audio = audio.speedup(playback_speed=speed_factor)

    words_per_ms = len(words) / len(audio)
    start_index = all_words.index(words[0])

    for i in range(0, len(words), chunk_size):
        chunk_words = words[i:i+chunk_size]
        start_ms = int(i / words_per_ms)
        end_ms = int(min(len(words), i + chunk_size) / words_per_ms)
        chunk_audio = audio[start_ms:end_ms]

        # Write chunk indices to temp file for highlight pane
        with open(index_file, "w") as f:
            f.write(f"{start_index + i},{start_index + i + len(chunk_words)}")

        # Play chunk (blocking)
        play(chunk_audio)

# -----------------------------
# Speak full text
def speak_text(tts, text, chunk_size, index_file, speed):
    all_words = re.findall(r'\S+|\n', text)
    paragraphs = [p for p in text.split("\n") if p.strip()]
    for para in paragraphs:
        speak_paragraph(tts, para, chunk_size, all_words, index_file, speed)
        time.sleep(0.3)

# -----------------------------
# Main
if __name__ == "__main__":
    speed, chunk_size, voice = get_user_preferences()
    tts = get_tts(voice)
    text = get_text_from_user()
    text = sanitize_text(text)

    # Save full text to temporary file for highlight pane
    temp_text_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    temp_text_file.write(text.encode())
    temp_text_file.close()

    # Temporary file for current chunk indices
    temp_index_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
    temp_index_file.close()

    # Highlight pane script
    highlight_script = os.path.join(os.path.dirname(__file__), "highlight_pane.py")

    # Open highlight window in a new terminal
    if sys.platform == "win32":
        subprocess.Popen(
            ["start", "cmd", "/k", f"python {highlight_script} {temp_text_file.name} {temp_index_file.name}"],
            shell=True
        )
    else:
        subprocess.Popen(
            ["xterm", "-fa", "Monospace", "-fs", "12", "-e", f"python3 {highlight_script} {temp_text_file.name} {temp_index_file.name}"]
        )

    # Speak text with highlighting
    speak_text(tts, text, chunk_size, temp_index_file.name, speed)
