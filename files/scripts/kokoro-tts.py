#!/usr/bin/env python3
"""
TTS helper — Kokoro-82M backed, with automatic language-aware voice switching.

This is the FAST default (~3s wall time per reply on Apple Silicon).
If you want heavier, more characterful voice with personality, see
`voxtral-tts.py` in the same folder — same CLI, slower (~30s), more style.

Kokoro is:
  - 82M parameters
  - Local, MLX-accelerated on Apple Silicon
  - 54 voices across 9 languages (English US/UK, Spanish, French, Italian,
    Portuguese BR, Japanese, Mandarin, Hindi)
  - Apache 2.0 license
  - Requires: `pip install mlx-audio` (system python or project venv)

Usage:
    kokoro-tts.py "Hello world" --output /tmp/out.ogg
    kokoro-tts.py "Hola, cómo estás" --output /tmp/hola.ogg      # auto-switches to Spanish voice
    kokoro-tts.py "Override" --voice bm_lewis --output /tmp/out.ogg

Outputs JSON on stdout: {"success": bool, "file_path": str, "duration": float,
                         "provider": "kokoro", "voice": <voice used>}

Voice selection rules (when no --voice passed):
    Text in English → bf_emma      (British female — warm, authoritative)
    Text in Spanish → ef_dora      (the one decent Spanish voice)
    Text in French  → ff_siwis
    Text in Italian → if_sara
    Text in PT-BR   → pf_dora
    Unknown         → bf_emma

Change defaults in the AUTO_VOICE_BY_LANG dict below.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile


DEFAULT_VOICE = "bf_emma"
KOKORO_REPO = "prince-canuma/Kokoro-82M"

AUTO_VOICE_BY_LANG = {
    "en": "bf_emma",
    "es": "ef_dora",
    "fr": "ff_siwis",
    "it": "if_sara",
    "pt": "pf_dora",
}

# Back-compat: if a caller still passes Voxtral-era voice names, map them.
LEGACY_VOICE_MAP = {
    "fr_female": "bf_emma",
    "neutral_female": "bf_emma",
    "casual_female": "af_heart",
    "cheerful_female": "af_heart",
    "it_female": "if_sara",
    "es_female": "ef_dora",
    "pt_female": "pf_dora",
}

MLX_AUDIO_CLI = shutil.which("mlx_audio.tts.generate") or "/opt/homebrew/bin/mlx_audio.tts.generate"


def _find_ffmpeg():
    for p in ["/opt/homebrew/bin/ffmpeg", "/usr/local/bin/ffmpeg"]:
        if os.path.exists(p):
            return p
    return shutil.which("ffmpeg")


def _find_ffprobe():
    for p in ["/opt/homebrew/bin/ffprobe", "/usr/local/bin/ffprobe"]:
        if os.path.exists(p):
            return p
    return shutil.which("ffprobe")


def _resolve_voice(v):
    return LEGACY_VOICE_MAP.get(v, v)


_ES_MARKERS = set("ñÑ¿¡áéíóúÁÉÍÓÚ")
_FR_MARKERS = set("àâçéèêëîïôœùûüÀÂÇÉÈÊËÎÏÔŒÙÛÜ")
_IT_MARKERS = set("àèéìíîòóùúÀÈÉÌÍÎÒÓÙÚ")
_PT_MARKERS = set("ãõâêôáéíóúçÃÕÂÊÔÁÉÍÓÚÇ")


def _detect_language(text):
    """Heuristic language sniff. Returns ISO-ish code in {en, es, fr, it, pt}."""
    chars = set(text)
    hits = {
        "es": len(chars & _ES_MARKERS),
        "fr": len(chars & _FR_MARKERS),
        "it": len(chars & _IT_MARKERS),
        "pt": len(chars & _PT_MARKERS),
    }
    best = max(hits.items(), key=lambda kv: kv[1])
    if best[1] > 0:
        if hits["es"] > 0 and ("ñ" in text.lower() or "¿" in text or "¡" in text):
            return "es"
        return best[0]
    # Fallback: Spanish stopword probe
    lowered = f" {text.lower()} "
    es_words = {" y ", " de ", " la ", " el ", " que ", " es ", " un ", " para ",
                " con ", " por ", " más ", " como ", " pero ", " está ", " los ",
                " las ", " este ", " esta ", " sus ", " mi ", " te ", " se "}
    if sum(1 for w in es_words if w in lowered) >= 3:
        return "es"
    return "en"


def _lang_from_voice(voice):
    first = (voice[:1] or "a").lower()
    if first in "abehijpz":
        return first
    if first == "f":
        return "f"
    return "a"


def _duration_sec(path):
    ffprobe = _find_ffprobe()
    if not ffprobe:
        return 0.0
    try:
        r = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path],
            capture_output=True, text=True, timeout=10,
        )
        return float(r.stdout.strip() or 0)
    except Exception:
        return 0.0


def _generate_wav(text, voice, lang, workdir, prefix="kokoro"):
    cmd = [MLX_AUDIO_CLI, "--model", KOKORO_REPO, "--text", text,
           "--voice", voice, "--lang_code", lang, "--speed", "1.0",
           "--file_prefix", prefix, "--audio_format", "wav"]
    r = subprocess.run(cmd, cwd=workdir, capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        raise RuntimeError(f"mlx-audio failed: {r.stderr[:500]}")
    segments = sorted(glob.glob(os.path.join(workdir, f"{prefix}_*.wav")))
    if not segments:
        raise RuntimeError("mlx-audio produced no output")
    if len(segments) == 1:
        return segments[0]
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("ffmpeg not found")
    concat_list = os.path.join(workdir, "concat.txt")
    with open(concat_list, "w") as f:
        for s in segments:
            f.write(f"file '{s}'\n")
    full_wav = os.path.join(workdir, "full.wav")
    subprocess.run([ffmpeg, "-y", "-f", "concat", "-safe", "0",
                    "-i", concat_list, "-c", "copy", full_wav],
                   check=True, capture_output=True, timeout=30)
    return full_wav


def _encode_ogg(wav_path, ogg_path):
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return False
    r = subprocess.run(
        [ffmpeg, "-y", "-i", wav_path,
         "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
         "-acodec", "libopus", "-ac", "1", "-b:a", "64k", "-vbr", "off",
         ogg_path],
        capture_output=True, text=True, timeout=60,
    )
    return r.returncode == 0 and os.path.exists(ogg_path) and os.path.getsize(ogg_path) > 0


def main():
    ap = argparse.ArgumentParser(description="Kokoro TTS (auto-language)")
    ap.add_argument("text", nargs="?")
    ap.add_argument("--output", "-o", default=None)
    ap.add_argument("--voice", default=None,
                    help="Kokoro voice preset. Omit to auto-detect language.")
    ap.add_argument("--wav-only", action="store_true")
    args = ap.parse_args()

    if not args.text:
        print(json.dumps({"success": False, "error": "No text provided"}))
        return 1

    if args.voice:
        voice = _resolve_voice(args.voice)
    else:
        detected = _detect_language(args.text)
        voice = AUTO_VOICE_BY_LANG.get(detected, DEFAULT_VOICE)

    lang = _lang_from_voice(voice)
    out_path = args.output or tempfile.mktemp(
        suffix=".wav" if args.wav_only else ".ogg"
    )
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)

    try:
        with tempfile.TemporaryDirectory() as workdir:
            wav = _generate_wav(args.text, voice, lang, workdir)
            if args.wav_only:
                shutil.copy(wav, out_path)
            else:
                ok = _encode_ogg(wav, out_path)
                if not ok:
                    shutil.copy(wav, out_path)
    except Exception as e:
        print(json.dumps({"success": False, "error": str(e), "provider": "kokoro"}))
        return 1

    print(json.dumps({
        "success": True,
        "file_path": out_path,
        "duration": _duration_sec(out_path),
        "provider": "kokoro",
        "voice": voice,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
