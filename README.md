# Text To Speech Highlighted

Terminal-driven text-to-speech reader that opens a live highlight pane while speech playback advances through the text.

## Overview

This project reads text through Piper, splits the content into short spoken chunks, and updates a second terminal window so the currently spoken words stay visually highlighted.

The public repo centers on the current Piper-based workflow:

- `tts_highlight.py` is the main entrypoint
- `highlight_pane.py` renders the live highlight window
- `tts_settings.json` stores basic runtime settings
- `install.sh` installs the app into a standard per-user location
- `legacy/` keeps the older Coqui-TTS based version for reference

## Requirements

- `python3`
- `piper` available in `PATH` or supplied by the user
- a Piper voices directory supplied by the user or via `PIPER_VOICES_DIR`
- `pydub`
- one of:
  - `pw-play`
  - `aplay`
- a terminal emulator for the highlight pane, such as:
  - `xterm`
  - `kitty`
  - `foot`
  - `alacritty`
  - `wezterm`
  - `gnome-terminal`
  - `xfce4-terminal`
  - `konsole`

## Quick Start

```bash
chmod +x tts_highlight.py highlight_pane.py install.sh
./install.sh
python3 "$HOME/.local/share/texttospeechhighlighted/tts_highlight.py" "This text will be spoken and highlighted."
```

Or add a shell alias:

```bash
alias s2t="python3 $HOME/.local/share/texttospeechhighlighted/tts_highlight.py"
```

## How It Works

`tts_highlight.py`:

1. normalizes text into a TTS-safe ASCII form
2. generates speech audio through Piper
3. slices playback into short word chunks
4. writes active word ranges into a temporary index file
5. launches `highlight_pane.py` in a second terminal window

`highlight_pane.py`:

1. reads the full text file
2. watches the index file for the current active word span
3. continuously redraws the terminal so the active words stay highlighted

## Configuration

Supported environment variables:

```bash
PIPER_BIN=/path/to/piper
PIPER_VOICES_DIR=/path/to/piper/voices
```

If those are not set and `piper` is not in `PATH`, the script asks the user for:

- the Piper binary path
- the Piper voices directory

That keeps the public version free of machine-specific path assumptions.

The settings file stores:

```json
{
  "speed": 200,
  "chunk_size": 4,
  "highlight": false,
  "voice": ""
}
```

If `voice` is empty, the first `.onnx` file found in the selected Piper voices directory is used automatically.

## Repository Scope

This repo is focused on the current local-reader workflow:

- text in
- speech out
- live terminal highlight

It is not a browser extension or a full desktop document reader.
