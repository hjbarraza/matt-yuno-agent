# TTS tuning — what we learned

Empirical settings discovered during a tuning session 2026-04-25 (operator: H, agent: Æris). Apply them to whichever engine you run — Voxtral, Kokoro, or another.

The lessons split cleanly into two layers: **engine-agnostic** (apply everywhere) and **engine-specific** (Voxtral only here, but the same shape applies to other autoregressive TTS).

---

## 1. Engine-agnostic — applies to Voxtral, Kokoro, anything

### 1.1 Write voice text in long flowing sentences with commas, NOT short sentences with periods

Counter-intuitive but verified. We word-timestamped a generated `.ogg` with Whisper and found pauses of 0.5–0.7 seconds at every period. Natural English mid-sentence pauses are ~0.15s. So:

- "Got it. Moving the kicker. Polishing the rhythm. Few minutes." → produces 4 long pauses → choppy delivery
- "Got it, moving the kicker above the headline, polishing the rhythm and tightening the spacing across the page, few minutes." → one flowing sentence → one final pause

The text version on Telegram or terminal can stay terse and dense. **Only the .ogg payload needs the rewrite.**

### 1.2 Auto-chunk long messages

Autoregressive TTS models drift past ~25–30 seconds of generated speech. Symptoms: background noise, hallucinated music, audio quality degradation in the tail. Even raising `max_frames` (or the equivalent length cap) only delays the drift, doesn't prevent it.

The reliable fix: split the input at sentence boundaries into ≤22-second chunks, generate each chunk independently, concatenate with ffmpeg.

**Drop-in helper** (works for any TTS function with the signature `generate(text, voice, output_path, **engine_params) -> result_with_duration_seconds`):

```python
import re
import subprocess
import os

CHUNK_WORDS = 55  # ~22 seconds of speech at 2.5 wps. Conservative on purpose.

def generate_with_chunking(text, voice, wav_path, generate_fn, **engine_params):
    """
    generate_fn must accept (text, voice, output_path, **engine_params)
    and return an object with `.duration_seconds` (or rename inside).
    """
    word_count = len(text.split())

    # Short — single generation
    if word_count <= CHUNK_WORDS:
        result = generate_fn(text=text, voice=voice, output_path=wav_path, **engine_params)
        return {"path": wav_path, "duration": result.duration_seconds}

    # Long — split at sentence boundaries
    sentences = re.split(r'(?<=[.!?])\s+', text.strip())
    chunks, cur, cur_words = [], [], 0
    for s in sentences:
        sw = len(s.split())
        if cur_words + sw > CHUNK_WORDS and cur:
            chunks.append(' '.join(cur))
            cur, cur_words = [s], sw
        else:
            cur.append(s)
            cur_words += sw
    if cur:
        chunks.append(' '.join(cur))

    chunk_paths, total = [], 0.0
    for i, ct in enumerate(chunks):
        cp = wav_path.replace('.wav', f'.chunk{i}.wav')
        r = generate_fn(text=ct, voice=voice, output_path=cp, **engine_params)
        chunk_paths.append(cp)
        total += r.duration_seconds

    # ffmpeg concat-demuxer (no re-encode — fast, lossless)
    list_path = wav_path + '.list'
    with open(list_path, 'w') as f:
        for cp in chunk_paths:
            f.write(f"file '{cp}'\n")
    subprocess.run(
        ['ffmpeg', '-y', '-f', 'concat', '-safe', '0',
         '-i', list_path, '-c', 'copy', wav_path],
        check=True, capture_output=True,
    )
    os.remove(list_path)
    for cp in chunk_paths:
        os.remove(cp)

    return {"path": wav_path, "duration": total}
```

Why 55 words: at 2.5 words/sec (typical Voxtral pace) that's ~22 seconds — well below the ~30s drift threshold. Chunks have room to breathe.

Why concat-demuxer with `-c copy`: zero re-encoding, no quality loss at boundaries, sub-100ms operation. Boundary clicks are negligible because each chunk ends/begins on a natural sentence break with a period of silence already present.

### 1.3 Voice preset matters more than parameters

Different voice presets in the same model can have very different artifact profiles. Some have ambient noise or musical bleed in their training samples and produce dirtier audio at low classifier-free-guidance values. **Try multiple presets before tuning params.** Keep the one that's cleanest for your language and switch the params around it.

In our case: `cheerful_female` produced background-music artifacts in the tail at `cfg_alpha=1.0`. `fr_female` at the same `cfg_alpha=1.0` produced clean audio. We kept fr_female.

---

## 2. Voxtral-specific (mlx-audio package)

### 2.1 Recommended params

```python
generate(
    text=text,
    voice="fr_female",      # or whichever preset is cleanest in your language
    output_path=wav_path,
    seed=0,
    cfg_alpha=1.0,          # was 1.2 default — lower = more naturalistic
    max_frames=4000,        # was 2000 default — ~80s clean audio per chunk
    model_path=model_path,
)
```

Caveat: the public `mlx_audio.tts.utils.load() + model.generate()` API may not expose `cfg_alpha` and `max_frames` in older versions. The lower-level `voxtral_mlx.generate.generate()` does. If you're on the public API, plumb the params through or check your installed version's signature.

### 2.2 Iteration history (so you don't redo the experiments)

| Setting | Result |
|---|---|
| `cfg_alpha=1.2` (default) | Choppy and robotic |
| `cfg_alpha=1.5` | Still choppy |
| `cfg_alpha=1.0` | Naturalistic, clean when chunked |
| `max_frames=2000` (default) | Tail squeezing past ~40s |
| `max_frames=4000` | Clean up to ~80s; still drifts past that without chunking |
| No chunking, message > 30s | Background music/noise artifacts in tail |
| Chunking + cfg_alpha=1.0 + cheerful_female | Background music in tail |
| Chunking + cfg_alpha=1.0 + fr_female | Clean throughout — H verdict: "perfect" |

### 2.3 Pacing analysis (for reference)

Whisper word-timestamp analysis of a generated message:
- Voxtral pace: ~2.54 words/sec (natural English: 3-4)
- Pause cadence: one audible pause (>200ms) every 5 words
- Average pause length: 0.48s
- All longest pauses (0.5-0.7s) cluster immediately after periods

Drives the "long flowing sentences with commas" rule.

---

## 3. Kokoro-specific (also mlx-audio)

Kokoro 82M is much smaller and faster (~3s wall time vs Voxtral's ~30s). Different drift profile. Reports from operators indicate:

- The chunking strategy from §1.2 transfers cleanly — no engine-specific changes needed
- Voxtral's `cfg_alpha` / `max_frames` knobs do NOT exist in Kokoro
- Kokoro's voices are more even in artifact profile across presets — preset choice matters less
- Recommended default for English: `bf_emma` (British female) per the existing setup

If Kokoro starts showing tail artifacts on long messages, apply §1.2 chunking. That's the universal lever.

---

## 4. Verifying your setup

Quick sanity tests to run after applying:

1. **Pacing**: generate a 30-second message and count pauses by ear. Should feel like a human reading aloud, not a robot enumerating.
2. **Tail quality**: generate a 60-second message (will trigger chunking). Listen to the last 10 seconds. Should match the first 10 in clarity.
3. **Boundary**: in a chunked message, listen for clicks/pops at the join points (calculate where they are: chunk 1 ends ~22s, chunk 2 ends ~44s, etc.). If audible, switch concat to re-encode with a small crossfade — see commented variation below.

Crossfade variant (slower, smoother joins) — only use if `-c copy` produces audible clicks:

```python
# Replace the concat block with this if you need crossfaded joins
# (requires re-encoding both chunks; ~2-5x slower than -c copy)
filter_complex = ''.join(
    f'[{i}:a]' for i in range(len(chunk_paths))
) + f'concat=n={len(chunk_paths)}:v=0:a=1[out]'
subprocess.run(
    ['ffmpeg', '-y'] +
    sum([['-i', cp] for cp in chunk_paths], []) +
    ['-filter_complex', filter_complex, '-map', '[out]', wav_path],
    check=True, capture_output=True,
)
```

---

## 5. Provenance

Discovered through iterative debugging by Æris and H over an evening session 2026-04-25. The operator (H) listened to ~6 generated samples, called out specific artifacts (choppy pacing, tail degradation, background music), and we tuned each variable in isolation until the failure mode stopped appearing. Lyra (Eugenio's TalenTaPy AI CoS) received the recipe and successfully adapted the chunking portion to Kokoro within minutes — confirming the §1 lessons are engine-agnostic.

Save this file as evidence so the next operator doesn't redo the experiments from scratch.
