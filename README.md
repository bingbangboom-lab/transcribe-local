# transcriber

Offline speech-to-text using [transcribe.cpp](https://github.com/handy-computer/transcribe.cpp). Runs locally on your machine with no cloud APIs and no internet required after setup.

Supported audio formats: **wav, mp3, flac, ogg, m4a, aac, wma, opus, webm, mp4**.

| Model | Languages | WER (English) | Q8_0 Size | Use Case |
|---|---|---|---|---|
| `parakeet` (default) | English | 1.69% | 730 MB | Fast, accurate English transcription |
| `nemotron-3.5` | 32 languages | 3.06% (BS) / 7.88% (FLEURS) | 716 MB | Multilingual (en-US, fr-FR, de-DE, zh-CN, ja-JP, ...) |

## Prerequisites

- **Python 3.10+** (with pip) — https://www.python.org/downloads/
- **FFmpeg** on your `PATH` — https://www.gyan.dev/ffmpeg/builds/ (download "ffmpeg-release-essentials" and add `bin/` to PATH)
- **GPU recommended but not required.** The default wheel picks Vulkan automatically on Windows/Linux and Metal on macOS Apple Silicon. CPU fallback is also available.

Verify both are installed:

```bash
python --version   # must be 3.10 or newer
ffmpeg -version    # must print a version
```

## Installation

### 1. Clone / copy this repository

```bash
git clone https://github.com/<your-name>/transcriber.git
cd transcriber
```

Or download the ZIP from GitHub and extract it.

### 2. Install transcribe.cpp Python bindings

```bash
pip install transcribe-cpp
```

This installs `transcribe_cpp` plus the native `transcribe-cpp-native` wheel (CPU + Vulkan on Windows/Linux, CPU + Metal on macOS ARM). The native wheel is small (~26 MB) and already contains everything needed for GPU inference.

### 3. Download a model

Pick one or both. The `-m` flag in the CLI also accepts direct paths to any GGUF from https://huggingface.co/handy-computer.

#### Parakeet TDT 0.6B v2 (English - default)

```bash
mkdir -p models/parakeet-tdt-0.6b-v2
curl -L "https://huggingface.co/handy-computer/parakeet-tdt-0.6b-v2-gguf/resolve/main/parakeet-tdt-0.6b-v2-Q8_0.gguf" \
  -o models/parakeet-tdt-0.6b-v2/parakeet-tdt-0.6b-v2-Q8_0.gguf
```

On Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force models\parakeet-tdt-0.6b-v2
Invoke-WebRequest -Uri "https://huggingface.co/handy-computer/parakeet-tdt-0.6b-v2-gguf/resolve/main/parakeet-tdt-0.6b-v2-Q8_0.gguf" `
  -OutFile "models\parakeet-tdt-0.6b-v2\parakeet-tdt-0.6b-v2-Q8_0.gguf"
```

#### Nemotron 3.5 ASR Streaming 0.6B (Multilingual)

```bash
mkdir -p models/nemotron-3.5-asr-streaming-0.6b
curl -L "https://huggingface.co/handy-computer/nemotron-3.5-asr-streaming-0.6b-gguf/resolve/main/nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf" \
  -o models/nemotron-3.5-asr-streaming-0.6b/nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf
```

On Windows (PowerShell):

```powershell
New-Item -ItemType Directory -Force models\nemotron-3.5-asr-streaming-0.6b
Invoke-WebRequest -Uri "https://huggingface.co/handy-computer/nemotron-3.5-asr-streaming-0.6b-gguf/resolve/main/nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf" `
  -OutFile "models\nemotron-3.5-asr-streaming-0.6b\nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf"
```

### 4. Verify setup

```bash
python transcribe.py --list-models
```

Both models should report `[downloaded]`.

## Usage

### Command-line

```bash
# Transcribe one file (default Parakeet model, English)
python transcribe.py audio.mp3

# Multiple files at once
python transcribe.py speech1.wav speech2.mp3 speech3.flac

# Use the multilingual model, specify the language
python transcribe.py -m nemotron-3.5 --language en-US audio.mp3
python transcribe.py -m nemotron-3.5 --language fr-FR french.mp3

# Let Nemotron auto-detect the language
python transcribe.py -m nemotron-3.5 --language auto audio.mp3

# Plain text without timestamps
python transcribe.py audio.mp3 --no-timestamps

# Choose the compute backend explicitly
python transcribe.py audio.mp3 --backend cpu
python transcribe.py audio.mp3 --backend vulkan

# Change output folder
python transcribe.py audio.mp3 -o transcripts/

# Watch a folder and transcribe new audio files automatically
python transcribe.py --watch input/

# Use any GGUF model path directly (not just the shortcuts)
python transcribe.py -m models/parakeet-tdt-0.6b-v2/parakeet-tdt-0.6b-v2-Q8_0.gguf audio.mp3

# List known model shortcuts and which are downloaded
python transcribe.py --list-models
```

### Output

Every input audio file produces a `.txt` file in the `output/` folder (default). Filename matches the input (e.g. `jfk.wav` → `output/jfk.txt`).

Example with timestamps (default):

```
Transcription: jfk.wav
Duration: 00:11.00
Processing time: 0.0s
Language: n/a

[00:00.24 -> 00:10.72]  And so, my fellow Americans, ask not what your country can do for you, ask what you can do for your country.
```

Example with `--no-timestamps`:

```
Transcription: jfk.wav
Duration: 00:11.00
Processing time: 0.0s
Language: n/a

And so, my fellow Americans, ask not what your country can do for you, ask what you can do for your country.
```

## Adding More Models

The project supports the full set of model families from [handy-computer/transcribe.cpp](https://github.com/handy-computer/transcribe.cpp) — 16+ families and 60+ variants. The [handy-computer](https://huggingface.co/handy-computer) HuggingFace org hosts pre-built GGUFs for all of them.

To add another model:

1. Download any GGUF into `models/<family>/` from the corresponding HF repo.
2. Pass it with `-m path/to/model.gguf`, OR add an entry to `KNOWN_MODELS` in `transcribe.py`.

Useful model families:

| Family | Highlights | HF link |
|---|---|---|
| Parakeet | Best WER in family at 1.1B (1.38%) | `handy-computer/parakeet-*` |
| Canary | 1B, fast multilingual + translate | `handy-computer/canary-*` |
| Whisper | Classic whisper (`tiny` → `large-v3-turbo`) | `handy-computer/whisper-*` |
| Moonshine | Tiny model, streaming-friendly | `handy-computer/moonshine-*` |
| SenseVoice | Chinese-optimized | `handy-computer/sensevoice-small-gguf` |
| Granite Speech | IBM model, speech translation | `handy-computer/granite-*` |
| Voxtral | Mistral audio-LLM (transcription + translation) | `handy-computer/voxtral-*` |

## Performance

Numbers from a typical setup:

| Sample | Parakeet Q8_0 | Nemotron 3.5 Q8_0 |
|---|---|---|
| 11 s audio (JFK) | ~22 ms inference (24.4 s total w/ model load) | ~123 ms inference (0.2 s total) |
| 35 s audio | ~189 ms | — |

First run of a session includes ~24 s model load cost. Subsequent runs amortize model load.

The `--backend auto` default picks the fastest available device: Metal on macOS, Vulkan on Linux/Windows with GPU, CPU as fallback. Force a specific backend with `--backend {cpu,vulkan,cuda}`.

## Directory Layout

```
transcriber/
├── transcribe.py          # Main Python script
├── models/
│   ├── parakeet-tdt-0.6b-v2/
│   │   └── parakeet-tdt-0.6b-v2-Q8_0.gguf       # ~730 MB
│   └── nemotron-3.5-asr-streaming-0.6b/
│       └── nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf   # ~716 MB
├── input/                 # (suggested place to drop source audio)
└── output/                # Transcription .txt files
```

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `ffmpeg: command not found` / `not recognized` | FFmpeg not in PATH | Install FFmpeg and add its `bin/` to PATH |
| `could not locate the native transcribe library` | Missing Python package | `pip install transcribe-cpp` |
| `no usable compute backend` | Vulkan/GPU not working | Force CPU: `--backend cpu` |
| `model not found` | Model file missing/typo | Run `python transcribe.py --list-models` to verify |
| `unsupported language` (Nemotron) | Missing or invalid `--language` | Always pass `--language` with Nemotron (e.g. `en-US`, `auto`) |
| `could not open file for reading` | FFmpeg couldn't read the input | Check the file exists and isn't corrupt |
| Transcription is empty | Silent or unsupported audio | Check audio level; try converting to WAV first |

## Credits

Built on [transcribe.cpp](https://github.com/handy-computer/transcribe.cpp) and the [ggml](https://github.com/ggml-org/ggml) runtime. Models are ported from NVIDIA's NeMo checkpoints to GGUF, numerically validated and WER-tested by the transcribe.cpp project, and hosted by [handy-computer on HuggingFace](https://huggingface.co/handy-computer).

## License

MIT.
