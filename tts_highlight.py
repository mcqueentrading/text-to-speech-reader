#!/usr/bin/env python3
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import unicodedata
from pathlib import Path

from pydub import AudioSegment

SETTINGS_FILE = Path(__file__).with_name("tts_settings.json")
TERMINAL_CANDIDATES = [
    ["xterm", "-fa", "Monospace", "-fs", "12", "-e"],
    ["kitty", "-e"],
    ["foot", "-e"],
    ["alacritty", "-e"],
    ["wezterm", "start", "--always-new-process", "--"],
    ["gnome-terminal", "--"],
    ["xfce4-terminal", "--command"],
    ["konsole", "-e"],
]


def get_default_voice(voices_dir: Path) -> str:
    voices = sorted(f for f in voices_dir.iterdir() if f.suffix == ".onnx")
    if not voices:
        raise FileNotFoundError(f"No ONNX voices found in {voices_dir}")
    return str(voices[0])


def prompt_yes_no(message: str) -> bool:
    answer = input(message).strip().lower()
    return answer in ("", "y", "yes")


def prompt_path(message: str) -> str:
    while True:
        value = input(message).strip()
        if value:
            return os.path.expanduser(value)
        print("A path is required.")


def normalize_to_ascii(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")

    replacements = {
        "“": '"',
        "”": '"',
        "‘": "'",
        "’": "'",
        "—": "-",
        "–": "-",
        "\t": " ",
        "\r": "",
        "&": " and ",
        "%": " percent ",
        "+": " plus ",
        "#": " number ",
        "@": " at ",
        "$": " dollars ",
        "*": " star ",
        "^": " caret ",
        "/": " slash ",
        "\\": " backslash ",
        "|": " pipe ",
        "~": " tilde ",
        "`": " backtick",
        "<": " less than ",
        ">": " greater than ",
        "=": " equals ",
    }
    for k, v in replacements.items():
        text = text.replace(k, v)

    text = "".join(c for c in text if 32 <= ord(c) <= 126 or c == "\n")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def load_settings_or_defaults() -> dict:
    defaults = {
        "speed": 200,
        "chunk_size": 4,
        "highlight": False,
        "voice": "",
        "piper_bin": "",
        "voices_dir": "",
    }
    if SETTINGS_FILE.is_file():
        with SETTINGS_FILE.open() as f:
            loaded = json.load(f)
        defaults.update(loaded)
    return defaults


def save_settings(settings: dict) -> None:
    with SETTINGS_FILE.open("w") as f:
        json.dump(settings, f, indent=2)


def resolve_piper_bin(settings: dict) -> str:
    candidate = settings.get("piper_bin") or os.environ.get("PIPER_BIN") or shutil.which("piper")
    if candidate and shutil.which(candidate) or (candidate and Path(candidate).exists()):
        return candidate
    return prompt_path("Path to `piper` binary: ")


def resolve_voices_dir(settings: dict) -> Path:
    candidate = settings.get("voices_dir") or os.environ.get("PIPER_VOICES_DIR")
    if candidate and Path(os.path.expanduser(candidate)).is_dir():
        return Path(os.path.expanduser(candidate))
    while True:
        value = Path(prompt_path("Path to Piper voices directory: "))
        if value.is_dir():
            return value
        print("That directory does not exist.")


def split_into_sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?]) +", text) if s.strip()]


def chunk_sentences(sentences: list[str], chunk_size: int) -> list[str]:
    chunks, current, count = [], [], 0
    for sentence in sentences:
        word_count = len(sentence.split())
        if current and count + word_count > chunk_size:
            chunks.append(" ".join(current))
            current, count = [], 0
        current.append(sentence)
        count += word_count
    if current:
        chunks.append(" ".join(current))
    return chunks


def play_wav(path: str) -> None:
    if shutil.which("pw-play"):
        subprocess.run(["pw-play", path], check=False)
    elif shutil.which("aplay"):
        subprocess.run(["aplay", path], check=False)
    else:
        raise FileNotFoundError("Could not find an audio player. Install pw-play or aplay.")


def piper_tts_to_audio(text: str, piper_bin: str, model_path: str, speed: int) -> AudioSegment:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
        subprocess.run(
            [
                piper_bin,
                "-m",
                model_path,
                "--sentence-silence",
                "0.15",
                "--no-normalize",
                "-f",
                f.name,
            ],
            input=text.encode("utf-8"),
            check=True,
        )
        audio = AudioSegment.from_wav(f.name)
        os.unlink(f.name)

    speed_factor = 200 / speed
    if speed_factor != 1.0:
        audio = audio.speedup(playback_speed=speed_factor)
    return audio


def launch_highlight_window(script_path: Path, text_file: str, index_file: str) -> None:
    for candidate in TERMINAL_CANDIDATES:
        if shutil.which(candidate[0]):
            if candidate[0] == "xfce4-terminal":
                subprocess.Popen(candidate + [f"python3 {script_path} {text_file} {index_file}"])
            else:
                subprocess.Popen(candidate + ["python3", str(script_path), text_file, index_file])
            return
    raise FileNotFoundError("No supported terminal found for the highlight pane.")


def speak_paragraph(paragraph: str, chunk_size: int, all_words: list[str], index_file: str | None, speed: int, piper_bin: str, model_path: str) -> None:
    paragraph = normalize_to_ascii(paragraph)
    sentences = split_into_sentences(paragraph)
    chunks = chunk_sentences(sentences, chunk_size)
    audio = piper_tts_to_audio(paragraph, piper_bin, model_path, speed)

    words = re.findall(r"\S+", paragraph)
    start_index = all_words.index(words[0])
    words_seen = 0
    words_per_ms = len(words) / len(audio)

    for chunk in chunks:
        chunk_words = re.findall(r"\S+", chunk)
        start_ms = int(words_seen / words_per_ms)
        end_ms = int((words_seen + len(chunk_words)) / words_per_ms)

        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
            audio[start_ms:end_ms].export(f.name, format="wav")
            if index_file:
                with open(index_file, "w") as idx:
                    idx.write(f"{start_index + words_seen},{start_index + words_seen + len(chunk_words)}")
            play_wav(f.name)
            os.unlink(f.name)
        words_seen += len(chunk_words)


def speak_text(text: str, chunk_size: int, index_file: str | None, speed: int, piper_bin: str, model_path: str) -> None:
    text = normalize_to_ascii(text)
    all_words = re.findall(r"\S+|\n", text)
    for para in (p for p in text.split("\n") if p.strip()):
        speak_paragraph(para, chunk_size, all_words, index_file, speed, piper_bin, model_path)
        time.sleep(0.25)


if __name__ == "__main__":
    use_highlight = prompt_yes_no("Enable highlight pane? [Y/n]: ")
    settings = load_settings_or_defaults()

    speed = settings["speed"]
    chunk_size = settings["chunk_size"]
    piper_bin = resolve_piper_bin(settings)
    voices_dir = resolve_voices_dir(settings)
    model_path = settings.get("voice") if settings.get("voice") and Path(settings["voice"]).exists() else get_default_voice(voices_dir)
    settings.update({
        "piper_bin": piper_bin,
        "voices_dir": str(voices_dir),
        "voice": model_path,
        "speed": speed,
        "chunk_size": chunk_size,
        "highlight": use_highlight,
    })
    save_settings(settings)

    if len(sys.argv) < 2:
        print("ERROR: Provide text in quotes.")
        sys.exit(1)

    text = sys.argv[1]

    if use_highlight:
        text_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        index_file = tempfile.NamedTemporaryFile(delete=False, suffix=".txt")
        text_file.write(text.encode())
        text_file.close()
        index_file.close()

        highlight_script = Path(__file__).with_name("highlight_pane.py")
        launch_highlight_window(highlight_script, text_file.name, index_file.name)
        index_path = index_file.name
    else:
        index_path = None

    speak_text(text, chunk_size, index_path, speed, piper_bin, model_path)
