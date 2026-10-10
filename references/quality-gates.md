# Quality gates

Apply these checks before calling a conversion complete.

## Structural

- Every full measure equals the printed meter; pickup and shortened final measures are explicitly identified.
- Measure count and system breaks agree with the source.
- Part and voice counts are preserved.
- Repeats, first/second endings, D.C./D.S., coda, and fine are represented or reported missing.

## Pitch and rhythm

- Key and every key change are correct.
- Clefs or Jianpu octave dots give the intended register.
- Accidentals persist only for their intended scope.
- Dots, beams/underlines, tuplets, grace notes, rests, ties, and slurs are distinguished.
- Sustained Jianpu dashes are encoded as duration, not as separate rests.

## Text and expression

- Title and credits are transcribed from the source.
- Lyric verses align to note attacks; melismas do not consume extra syllables.
- Chord symbols, dynamics, articulations, tempo text, rehearsal marks, and playing instructions are either preserved or listed as unresolved.

## Round-trip

- Parse the generated MusicXML again without errors.
- Import or render it in an available notation application.
- Compare the rendered result with the source system by system.
- Listen to MIDI when it can expose octave, duration, or missing-note errors.

Report exact uncertainty locations. Prefer “measure 12, beat 3, pitch unclear” over a general warning.
