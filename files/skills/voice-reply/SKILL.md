---
name: voice-reply
description: Every Telegram reply includes BOTH a text message AND a Voxtral voice (.ogg) attachment. Apply on every turn where the last user message arrived with <channel source="plugin:telegram:telegram">, whether inbound was voice or text. Enforced by ~/.claude/hooks/telegram-reply-enforcer.py (optional).
---

# voice-reply

Every Telegram turn sends two things:
- A **text message** carrying the readable answer
- A **voice message** (Voxtral-generated `.ogg`) carrying the spoken version

The operator reads the text immediately on the lock screen and listens to the voice when it's convenient. Both are required. The Stop hook blocks if either is missing (if installed).

## Shape: one reply, text + voice attached

Default and only shape: **a single `mcp__plugin_telegram_telegram__reply` call** that passes both `text` (the substantive answer) and `files: ["/tmp/reply.ogg"]`. The text carries the full written answer; the `.ogg` carries the spoken TL;DR. One message, two payloads.

**Never send a second reply whose only text is an emoji caption like `🎙️`.** That shows up on the device as a standalone sticker-style message and is noise. If you have a voice to send, attach it to the substantive text reply.

Telegram rejects empty-text replies, so every reply has some text — but that text is the real answer, not a caption.

## Generate the voice

```bash
~/.claude/scripts/voxtral-tts.py "<spoken version of the answer>" --output /tmp/reply_<ts>.ogg
```

### Voice-script guidelines

- **Under ~500 chars** for reliability (Voxtral max frames ≈ 60s of speech).
- **Sound like speech, not reading.** Contractions, short sentences, no bullet points or markdown.
- **Lead with the point.** Listened to on the go; bury nothing.
- **Say numbers and URLs naturally.** "seventeen twenty six" not "17:26"; avoid reading URLs aloud — reference them in the text only.
- **Default voice**: pick a Voxtral preset that fits your operator's assistant identity. Override with `--voice <preset>` per-message when context calls for it.

## Text formatting on Telegram

Telegram does not render markdown unless the reply is sent with `format: "markdownv2"`. If you send `**bold**` or `- item` in plain mode, the operator sees literal asterisks and hyphens.

**Default: plain text, no markdown symbols.** Write prose that reads cleanly without formatting. No `**bold**`, no `_italics_`, no bullet `-` lists, no `` `code` `` backticks. Use sentence structure and line breaks for rhythm. Short fragments. Em-dashes. Blank lines between thoughts.

**Opt into `format: "markdownv2"` only when formatting earns its keep:**
- Inline `code` for file paths, commands, identifiers.
- Fenced code blocks for snippets, diffs.
- **Bold** for a genuine headline or a single emphasized word.
- Clickable `[link text](url)`.

When you do use `markdownv2`, escape these chars in any non-formatted text: `_ * [ ] ( ) ~ ` > # + - = | { } . !` — prefix each with `\`. Miss one and the API rejects the message. Keep the formatted surface small so escaping stays tractable.

Lists: prefer prose. If a list is genuinely clearer, use numbered `1.` `2.` `3.` (numbers don't need escaping) or unicode bullets `•` in plain mode.

Tables: never on Telegram. Telegram has no table rendering in either mode. Convert to prose or two short lines.

## Scripting the voice vs. the text

The text and voice live in the same message but don't have to say the same thing:

- **Short answer** → text and voice say essentially the same thing.
- **Long answer with structure** (lists, multi-part comparison) → text carries the full structure; voice is a tighter spoken TL;DR. Both ride the single reply.

## Workflow

1. Draft the full text answer.
2. Compress to a ~300-char spoken version (lead, then key points).
3. Run `voxtral-tts.py` → `/tmp/reply_<ts>.ogg`.
4. Send via `mcp__plugin_telegram_telegram__reply` (one call with both `text` and `files`).
5. Apply the voice-filter skill to the text and to the spoken version.

## Hard rules

- **Both channels required.** Text-only reply = hook blocks. Voice-only reply = Telegram rejects empty text.
- **Voice under ~500 chars.** Longer scripts risk Voxtral truncation.
- **No markdown in the voice script.** Asterisks and hyphens get read literally.
- **Plain text by default on the text reply.** Flip to `format: "markdownv2"` only when bold/code/link formatting earns its keep.
- **Never voice-reply** lists, tables, code blocks, diffs, or URLs verbatim. The voice covers the *narrative*; text carries the *structure*.
- **One-word inbound → still both.** A yes/no answer gets a one-sentence voice.

## Edge case: hook-block recovery

If the hook blocks you because you forgot the voice, don't argue. Generate the `.ogg`, send the reply, stop. The hook is a safety net — honor it.

## Checklist

- [ ] Text TL;DR drafted
- [ ] Voice script ≤ 500 chars, speech-shaped
- [ ] `voxtral-tts.py` produced a valid `.ogg`
- [ ] Sent via `mcp__plugin_telegram_telegram__reply` with both `text` and `files`
- [ ] Both message types visible in Telegram
