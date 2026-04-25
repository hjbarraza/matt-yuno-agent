#!/usr/bin/env python3
"""
Voxtral TTS standalone (lives in ~/.claude/scripts/).

Requires the `~/voice-venv` Python venv with `mlx-audio[tts]` installed and
the Voxtral weights pulled into the HuggingFace cache. See SETUP-PROMPT.md.

Run with the venv's python explicitly, OR shebang this script at
`/Users/<me>/voice-venv/bin/python` and mark it executable.

Usage:
    ~/voice-venv/bin/python ~/.claude/scripts/voxtral-tts.py "Hello world" --output /tmp/out.ogg
    ... --voice casual_female
    ... --wav-only --output /tmp/out.wav

Outputs JSON on stdout: {"success": bool, "file_path": str, "duration": float}
"""

import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import wave

import numpy as np

logger = logging.getLogger("voxtral-voice")

# CONFIGURE: pick your default voice preset. Language-prefixed voices
# (fr_*, it_*, es_*, de_*, hi_*, pt_*, nl_*, ar_*) expect text in that
# language — feeding English to fr_female sounds wrong. For English use
# neutral_*, casual_*, or cheerful_*.
DEFAULT_VOICE = "neutral_female"

# HuggingFace repo id. `mlx_audio.tts.utils.load()` resolves this against
# the local HF cache (default `~/.cache/huggingface/hub/`). Override with
# the VOXTRAL_MODEL environment variable if you host a custom fine-tune.
DEFAULT_MODEL = os.environ.get(
    "VOXTRAL_MODEL", "mlx-community/Voxtral-4B-TTS-2603-mlx-4bit"
)


def _find_ffmpeg():
    for path in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.exists(path):
            return path
    return shutil.which("ffmpeg")


def _generate_wav(text, voice, wav_path, model_id):
    # Real Voxtral TTS API lives inside mlx-audio, not a separate voxtral_mlx
    # package (that one doesn't exist on PyPI). model.generate() may return a
    # single GenerationResult or yield chunks when streaming — handle both.
    from mlx_audio.tts.utils import load

    logger.info("Generating TTS: voice=%s, len=%d chars", voice, len(text))
    model = load(model_id)
    result = model.generate(text=text, voice=voice)
    chunks = list(result) if hasattr(result, "__iter__") else [result]
    sr = chunks[0].sample_rate
    audio = np.concatenate([np.array(c.audio).reshape(-1) for c in chunks])

    pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(pcm.tobytes())

    duration = len(audio) / sr
    logger.info("WAV generated: %s (%.2fs)", wav_path, duration)
    return {"path": wav_path, "duration": round(duration, 3)}


def _convert_wav_to_ogg(wav_path, ogg_path):
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        logger.error("ffmpeg not found")
        return False

    # EBU loudnorm instead of brute-force gain — preserves dynamics, no pumping
    cmd = [
        ffmpeg, "-y",
        "-i", wav_path,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-acodec", "libopus", "-ac", "1", "-b:a", "64k", "-vbr", "off",
        ogg_path,
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if result.returncode != 0:
            logger.error("ffmpeg failed: %s", result.stderr)
            return False
        if not os.path.exists(ogg_path) or os.path.getsize(ogg_path) == 0:
            logger.error("ffmpeg produced empty output")
            return False
        if os.path.exists(wav_path):
            os.remove(wav_path)
        logger.info("Converted to OGG: %s", ogg_path)
        return True
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg conversion timed out")
        return False


def main():
    parser = argparse.ArgumentParser(description="Voxtral TTS (standalone)")
    parser.add_argument("text", nargs="?", help="Text to convert to speech")
    parser.add_argument("--output", "-o", default=None, help="Output OGG path")
    parser.add_argument("--voice", default=DEFAULT_VOICE, help="Voice preset")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="HF model id")
    parser.add_argument("--wav-only", action="store_true", help="Output WAV only")
    args = parser.parse_args()

    if not args.text:
        print(json.dumps({"success": False, "error": "No text provided"}))
        sys.exit(1)

    if args.output:
        output_path = args.output
    else:
        with tempfile.NamedTemporaryFile(
            suffix=".ogg" if not args.wav_only else ".wav", delete=False
        ) as tf:
            output_path = tf.name
    is_ogg = output_path.endswith(".ogg") and not args.wav_only

    wav_path = output_path if not is_ogg else output_path.replace(".ogg", ".wav")
    os.makedirs(os.path.dirname(os.path.abspath(wav_path)), exist_ok=True)

    try:
        info = _generate_wav(args.text, args.voice, wav_path, args.model)

        if is_ogg:
            success = _convert_wav_to_ogg(wav_path, output_path)
            if success:
                print(json.dumps({"success": True, "file_path": output_path,
                                  "duration": info["duration"], "provider": "voxtral"}))
            else:
                # Fallback: WAV with .ogg extension (Telegram accepts as file)
                if os.path.exists(wav_path):
                    shutil.move(wav_path, output_path)
                print(json.dumps({"success": True, "file_path": output_path,
                                  "duration": info["duration"], "provider": "voxtral",
                                  "warning": "ffmpeg conversion failed, sending WAV"}))
        else:
            print(json.dumps({"success": True, "file_path": wav_path,
                              "duration": info["duration"], "provider": "voxtral"}))
    except Exception as e:
        logger.error("TTS generation failed: %s", e, exc_info=True)
        print(json.dumps({"success": False, "error": str(e), "provider": "voxtral"}))
        sys.exit(1)


if __name__ == "__main__":
    main()
