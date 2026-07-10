import argparse
import array
import subprocess
import sys
import tempfile
import time
import wave
from pathlib import Path

import transcribe_cpp

APP_DIR = Path(__file__).resolve().parent
DEFAULT_MODEL = APP_DIR / "models" / "parakeet-tdt-0.6b-v2" / "parakeet-tdt-0.6b-v2-Q8_0.gguf"
DEFAULT_OUTPUT_DIR = APP_DIR / "output"
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".ogg", ".m4a", ".aac", ".wma", ".opus", ".webm", ".mp4"}


KNOWN_MODELS = {
    "parakeet": DEFAULT_MODEL,
    "nemotron-3.5": APP_DIR / "models" / "nemotron-3.5-asr-streaming-0.6b" / "nemotron-3.5-asr-streaming-0.6b-Q8_0.gguf",
}


def resolve_model(model_arg: str) -> Path:
    if model_arg in KNOWN_MODELS:
        return KNOWN_MODELS[model_arg]
    return Path(model_arg)


def convert_to_wav16k(input_path: Path) -> Path:
    suffix = input_path.suffix.lower()
    if suffix == ".wav":
        try:
            with wave.open(str(input_path), "rb") as w:
                if w.getnchannels() == 1 and w.getframerate() == 16000:
                    return input_path
        except Exception:
            pass

    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp.close()
    tmp_path = Path(tmp.name)
    try:
        cmd = [
            "ffmpeg", "-y", "-i", str(input_path),
            "-ar", "16000", "-ac", "1", "-f", "wav",
            str(tmp_path),
        ]
        print(f"  Converting {input_path.name} to 16kHz mono WAV...")
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"ffmpeg failed for {input_path}:\n{result.stderr}")
        return tmp_path
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def load_wav_mono16k(path: Path) -> array.array:
    with wave.open(str(path), "rb") as w:
        n_channels = w.getnchannels()
        sample_width = w.getsampwidth()
        framerate = w.getframerate()
        frames = w.readframes(w.getnframes())

    if sample_width != 2:
        raise ValueError(f"{path}: expected 16-bit PCM, got {sample_width * 8}-bit")
    if framerate != 16000:
        raise ValueError(f"{path}: expected 16 kHz, got {framerate} Hz")

    pcm16 = array.array("h")
    pcm16.frombytes(frames)
    if sys.byteorder == "big":
        pcm16.byteswap()

    if n_channels > 1:
        mono = array.array("h", [0]) * (len(pcm16) // n_channels)
        for i in range(len(mono)):
            acc = sum(pcm16[i * n_channels + c] for c in range(n_channels))
            mono[i] = int(acc / n_channels)
        pcm16 = mono

    return array.array("f", (s / 32768.0 for s in pcm16))


def format_time(ms: int) -> str:
    s = ms / 1000.0
    h = int(s // 3600)
    m = int((s % 3600) // 60)
    sec = s % 60
    if h > 0:
        return f"{h:02d}:{m:02d}:{sec:05.2f}"
    return f"{m:02d}:{sec:05.2f}"


def transcribe_file(
    audio_path: Path,
    model: transcribe_cpp.Model,
    output_dir: Path,
    timestamps: str = "segment",
    with_timestamps: bool = True,
    language: str | None = None,
) -> Path:
    wav_path = None
    try:
        wav_path = convert_to_wav16k(audio_path)
        pcm = load_wav_mono16k(wav_path)
        duration_s = len(pcm) / 16000.0
        print(f"  Audio duration: {format_time(int(duration_s * 1000))}")

        with model.session() as session:
            start = time.time()
            result = session.run(pcm, timestamps=timestamps if with_timestamps else "none", language=language)
            elapsed = time.time() - start

        output_path = output_dir / (audio_path.stem + ".txt")
        lines = []
        lines.append(f"Transcription: {audio_path.name}")
        lines.append(f"Duration: {format_time(int(duration_s * 1000))}")
        lines.append(f"Processing time: {elapsed:.1f}s")
        lines.append(f"Language: {result.language or 'n/a'}")
        lines.append("")

        if with_timestamps and result.segments:
            for seg in result.segments:
                lines.append(f"[{format_time(seg.t0_ms)} -> {format_time(seg.t1_ms)}]  {seg.text.strip()}")
        else:
            lines.append(result.text.strip())

        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

    finally:
        if wav_path and wav_path != audio_path:
            wav_path.unlink(missing_ok=True)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Local audio transcription using transcribe.cpp",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
model shortcuts (use with -m):
  parakeet        Parakeet TDT 0.6B v2  (English, fast, default)
  nemotron-3.5    Nemotron 3.5 ASR 0.6B (32 languages, requires --language)

examples:
  python transcribe.py audio.mp3
  python transcribe.py -m nemotron-3.5 --language en-US audio.mp3
  python transcribe.py audio.mp3 --language auto
  python transcribe.py audio.mp3 --no-timestamps
  python transcribe.py --list-models
  python transcribe.py --watch input/
""",
    )
    ap.add_argument("files", nargs="*", help="Audio files to transcribe")
    ap.add_argument("-m", "--model", default="parakeet", help="Path to GGUF model file or shorthand: " + ", ".join(KNOWN_MODELS))
    ap.add_argument("-o", "--output", default=str(DEFAULT_OUTPUT_DIR), help="Output directory for .txt files")
    ap.add_argument("--no-timestamps", action="store_true", help="Output plain text without timestamps")
    ap.add_argument("--language", default=None, help="Language/locale (e.g. en-US, fr-FR); required by some models")
    ap.add_argument("--backend", default="auto", choices=["auto", "cpu", "vulkan", "cuda"], help="Compute backend")
    ap.add_argument("--list-models", action="store_true", help="List known model shortcuts and exit")
    ap.add_argument("--watch", type=str, help="Watch a directory for new audio files")
    args = ap.parse_args()

    if args.list_models:
        print("Known model shortcuts:")
        for name, path in KNOWN_MODELS.items():
            status = "downloaded" if path.is_file() else "not downloaded"
            print(f"  {name:20s}  {path}  [{status}]")
        return 0

    if not args.files and not args.watch:
        ap.error("provide audio files or use --watch")

    model_path = resolve_model(args.model)
    if not model_path.is_file():
        print(f"Error: model not found: {model_path}", file=sys.stderr)
        return 1

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"transcribe_cpp {transcribe_cpp.__version__} | native {transcribe_cpp.native_version()}")
    devs = transcribe_cpp.backends()
    for d in devs:
        vram = f" ({d.memory_free // (1024**2)} MB free)" if d.memory_free else ""
        print(f"  {d.kind}: {d.description}{vram}")
    print(f"Loading model: {model_path}")

    with transcribe_cpp.Model(str(model_path), backend=args.backend) as model:
        print(f"  {model.arch}/{model.variant} on {model.backend}")
        dev = model.device
        free = f"{dev.memory_free // (1024**2)} MB free" if dev.memory_free else "n/a"
        print(f"  Device: {dev.description} ({free})")

        if args.watch:
            watch_dir = Path(args.watch)
            watch_dir.mkdir(parents=True, exist_ok=True)
            print(f"\nWatching {watch_dir} for audio files (Ctrl+C to stop)...")
            processed = set()
            try:
                while True:
                    for f in sorted(watch_dir.iterdir()):
                        if f.is_file() and f.suffix.lower() in AUDIO_EXTENSIONS and f.name not in processed:
                            processed.add(f.name)
                            print(f"\n--- Transcribing: {f.name} ---")
                            try:
                                out = transcribe_file(f, model, output_dir, with_timestamps=not args.no_timestamps, language=args.language)
                                print(f"  Output: {out}")
                            except Exception as e:
                                print(f"  Error: {e}", file=sys.stderr)
                    time.sleep(2)
            except KeyboardInterrupt:
                print("\nStopped.")
        else:
            failed = 0
            for f in args.files:
                audio_path = Path(f)
                if not audio_path.is_file():
                    print(f"Error: file not found: {audio_path}", file=sys.stderr)
                    failed += 1
                    continue
                print(f"\n--- Transcribing: {audio_path.name} ---")
                try:
                    out = transcribe_file(audio_path, model, output_dir, with_timestamps=not args.no_timestamps, language=args.language)
                    print(f"  Output: {out}")
                except Exception as e:
                    print(f"  Error: {e}", file=sys.stderr)
                    failed += 1

            if failed:
                return 1

    print("\nDone.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
