# Score Photo to Editable

A reusable Codex skill for turning photographed, scanned, or PDF sheet music into checked, editable notation files. It supports a deterministic workflow for monophonic printed Jianpu and guides OMR-assisted work for staff notation.

## Outputs

- MusicXML as the canonical editable score
- MIDI for aural checking
- A readable transcription
- A validation report with assumptions and unresolved checks

The included `送别` example contains 20 measures in C major, 4/4 time, an instrumental introduction, and two lyric verses.

## Install

Copy or clone this repository into the Codex skills directory:

```text
~/.codex/skills/score-photo-to-editable/
```

Then ask Codex to convert a score image into editable MusicXML and apply the `score-photo-to-editable` quality checks.

## Jianpu helper

For printed, monophonic Jianpu, encode the transcription using the JSON format in `references/jianpu-transcription.md`, then run:

```text
python scripts/build_score.py transcription.json output-directory
```

See `examples/songbie/` for a complete input and generated output set.

## Validation performed on the example

- All 20 measures close correctly in 4/4.
- Generated MusicXML parses successfully.
- Generated MIDI has a valid header and track structure.
- Repeated generation is byte-for-byte reproducible.
- An intentionally incomplete measure is rejected with its measure number.

Visual comparison in a notation editor remains a required final gate for each new source image.

