# Jianpu transcription representation

Use this representation for printed, monophonic numbered notation. Transcribe from the image, not from memory of the song.

## Score fields

```json
{
  "title": "Title",
  "composer": "Composer",
  "lyricist": "Lyricist",
  "instrument": "Harmonica",
  "tonic": "C",
  "tonic_octave": 4,
  "mode": "major",
  "time": [4, 4],
  "preview_tempo": 80,
  "assumptions": ["Tempo is not printed; 80 BPM is used only for MIDI preview."],
  "measures": []
}
```

`tonic_octave` is the sounding octave assigned to degree 1 with no octave dots. Use scientific pitch notation: C4 is middle C. `preview_tempo` does not assert that the source contains a tempo marking.

## Notes

Each measure contains `notes`. A pitched event uses `degree` 1–7. A rest uses `rest: true`.

```json
{"degree": 5, "duration": "q"}
{"degree": 1, "octave": 1, "duration": "dq"}
{"degree": 7, "octave": -1, "duration": "e"}
{"degree": 4, "accidental": 1, "duration": "q"}
{"rest": true, "duration": "h"}
```

Durations are `w` whole, `h` half, `q` quarter, `e` eighth, `s` sixteenth, `t` thirty-second; prefix dotted values with `d`, such as `dq` or `de`.

Use `octave: 1` for one dot above and `octave: -1` for one dot below. Use `accidental: 1` for sharp, `-1` for flat, and `0` or omission for the scale spelling implied by the key.

Encode a printed slur on its boundary notes:

```json
{"degree": 3, "duration": "e", "slur_start": 1}
{"degree": 5, "duration": "e", "slur_stop": 1, "lyric_anchor": false}
```

`lyric_anchor: false` means that a note does not consume a new lyric syllable, commonly the second note of a two-note melisma. It does not by itself create a slur.

## Lyrics

Attach verse syllables at measure level. Each verse must have exactly as many entries as lyric-anchor notes in that measure.

```json
"lyrics": {
  "1": ["长", "亭", "外"],
  "2": ["长", "亭", "外"]
}
```

Omit `lyrics` for instrumental introductions. Do not infer missing lyrics from a known edition unless the user authorizes using another source.

## Reading visual duration marks

- A plain digit is normally a quarter note in common Jianpu.
- One underline is an eighth note; two are sixteenth notes.
- A dot to the right adds half the duration.
- A following dash extends the preceding sound by one quarter-note unit.
- Dots above or below change octave, not duration.

Resolve duration from the complete measure and printed meter. If more than one interpretation closes the measure, record the ambiguity rather than choosing silently.
