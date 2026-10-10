#!/usr/bin/env python3
"""Build MusicXML and MIDI from validated monophonic Jianpu JSON."""

from __future__ import annotations

import argparse
import json
import re
import struct
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

DIVISIONS = 8
DURATIONS = {
    "t": 1,
    "s": 2,
    "e": 4,
    "q": 8,
    "h": 16,
    "w": 32,
    "de": 6,
    "dq": 12,
    "dh": 24,
}
TYPES = {"t": "32nd", "s": "16th", "e": "eighth", "q": "quarter", "h": "half", "w": "whole"}
MAJOR_FIFTHS = {
    "Cb": -7, "Gb": -6, "Db": -5, "Ab": -4, "Eb": -3, "Bb": -2, "F": -1,
    "C": 0, "G": 1, "D": 2, "A": 3, "E": 4, "B": 5, "F#": 6, "C#": 7,
}
LETTERS = "CDEFGAB"
NATURAL_PC = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9, "B": 11}


def fail(message: str) -> None:
    raise ValueError(message)


def duration_info(code: str) -> tuple[int, str, bool]:
    if code not in DURATIONS:
        fail(f"Unsupported duration: {code}")
    dotted = code.startswith("d")
    base = code[1:] if dotted else code
    return DURATIONS[code], TYPES[base], dotted


def key_alters(fifths: int) -> dict[str, int]:
    alters = {letter: 0 for letter in LETTERS}
    order = "FCGDAEB" if fifths > 0 else "BEADGCF"
    for letter in order[:abs(fifths)]:
        alters[letter] = 1 if fifths > 0 else -1
    return alters


def pitch_for(note: dict, tonic: str, tonic_octave: int, fifths: int) -> tuple[str, int, int, int]:
    degree = int(note["degree"])
    if degree < 1 or degree > 7:
        fail(f"Degree must be 1..7, got {degree}")
    tonic_letter = tonic[0].upper()
    tonic_index = LETTERS.index(tonic_letter)
    absolute_index = tonic_index + degree - 1
    step = LETTERS[absolute_index % 7]
    octave = tonic_octave + absolute_index // 7 + int(note.get("octave", 0))
    alter = key_alters(fifths)[step] + int(note.get("accidental", 0))
    midi = 12 * (octave + 1) + NATURAL_PC[step] + alter
    return step, alter, octave, midi


def add_text(parent: ET.Element, tag: str, text: object, **attrs: str) -> ET.Element:
    child = ET.SubElement(parent, tag, attrs)
    child.text = str(text)
    return child


def vlq(value: int) -> bytes:
    out = [value & 0x7F]
    value >>= 7
    while value:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    return bytes(reversed(out))


def midi_file(events: list[tuple[int, int]], tempo: int, title: str, time_sig: tuple[int, int]) -> bytes:
    ticks = 480
    track = bytearray()
    name = title.encode("utf-8")
    track += vlq(0) + b"\xFF\x03" + vlq(len(name)) + name
    micros = round(60_000_000 / tempo)
    track += vlq(0) + b"\xFF\x51\x03" + micros.to_bytes(3, "big")
    numerator, denominator = time_sig
    power = 0
    value = denominator
    while value > 1 and value % 2 == 0:
        power += 1
        value //= 2
    track += vlq(0) + b"\xFF\x58\x04" + bytes([numerator, power, 24, 8])
    pending = 0
    for midi, units in events:
        delta_ticks = round(units * ticks / DIVISIONS)
        if midi < 0:
            pending += delta_ticks
            continue
        track += vlq(pending) + bytes([0x90, midi, 72])
        track += vlq(delta_ticks) + bytes([0x80, midi, 0])
        pending = 0
    track += vlq(pending) + b"\xFF\x2F\x00"
    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, ticks)
    return header + b"MTrk" + struct.pack(">I", len(track)) + track


def safe_name(value: str) -> str:
    cleaned = re.sub(r"[<>:\"/\\|?*]+", "_", value).strip(" .")
    return cleaned or "score"


def build(data: dict, output_dir: Path) -> list[Path]:
    if data.get("mode", "major") != "major":
        fail("The helper currently supports major-mode Jianpu only")
    title = str(data.get("title") or "Untitled")
    tonic = str(data.get("tonic") or "C")
    if tonic not in MAJOR_FIFTHS:
        fail(f"Unsupported major key tonic: {tonic}")
    fifths = MAJOR_FIFTHS[tonic]
    tonic_octave = int(data.get("tonic_octave", 4))
    time_sig = tuple(data.get("time", [4, 4]))
    if len(time_sig) != 2 or time_sig[1] not in (1, 2, 4, 8, 16):
        fail(f"Invalid time signature: {time_sig}")
    expected = int(time_sig[0] * DIVISIONS * 4 / time_sig[1])
    measures = data.get("measures")
    if not isinstance(measures, list) or not measures:
        fail("At least one measure is required")

    problems: list[str] = []
    midi_events: list[tuple[int, int]] = []
    lyric_assignments: list[dict[int, str]] = []
    for measure_index, measure in enumerate(measures, 1):
        notes = measure.get("notes", [])
        total = sum(duration_info(note["duration"])[0] for note in notes)
        measure_expected = int(measure.get("expected_units", expected))
        if total != measure_expected:
            problems.append(f"Measure {measure_index}: duration {total}/{DIVISIONS} quarters, expected {measure_expected}/{DIVISIONS}")
        anchors = [index for index, note in enumerate(notes) if not note.get("rest") and note.get("lyric_anchor", True)]
        verse_map: dict[int, str] = {}
        for verse, syllables in measure.get("lyrics", {}).items():
            if len(syllables) != len(anchors):
                problems.append(f"Measure {measure_index}, verse {verse}: {len(syllables)} syllables for {len(anchors)} lyric anchors")
            for note_index, syllable in zip(anchors, syllables):
                verse_map[note_index * 100 + int(verse)] = syllable
        lyric_assignments.append(verse_map)
        for note in notes:
            units, _, _ = duration_info(note["duration"])
            if note.get("rest"):
                midi_events.append((-1, units))
            else:
                midi_events.append((pitch_for(note, tonic, tonic_octave, fifths)[3], units))
    if problems:
        fail("\n".join(problems))

    root = ET.Element("score-partwise", version="4.0")
    work = ET.SubElement(root, "work")
    add_text(work, "work-title", title)
    identification = ET.SubElement(root, "identification")
    if data.get("composer"):
        add_text(identification, "creator", data["composer"], type="composer")
    if data.get("lyricist"):
        add_text(identification, "creator", data["lyricist"], type="lyricist")
    encoding = ET.SubElement(identification, "encoding")
    add_text(encoding, "software", "score-photo-to-editable build_score.py")
    part_list = ET.SubElement(root, "part-list")
    score_part = ET.SubElement(part_list, "score-part", id="P1")
    add_text(score_part, "part-name", data.get("instrument", "Melody"))
    part = ET.SubElement(root, "part", id="P1")

    for measure_index, measure_data in enumerate(measures, 1):
        measure = ET.SubElement(part, "measure", number=str(measure_index))
        if measure_index == 1:
            attributes = ET.SubElement(measure, "attributes")
            add_text(attributes, "divisions", DIVISIONS)
            key = ET.SubElement(attributes, "key")
            add_text(key, "fifths", fifths)
            time = ET.SubElement(attributes, "time")
            add_text(time, "beats", time_sig[0])
            add_text(time, "beat-type", time_sig[1])
            clef = ET.SubElement(attributes, "clef")
            add_text(clef, "sign", "G")
            add_text(clef, "line", 2)
            sound_direction = ET.SubElement(measure, "direction", placement="above")
            ET.SubElement(sound_direction, "sound", tempo=str(int(data.get("preview_tempo", 80))))
        for note_index, note_data in enumerate(measure_data["notes"]):
            note = ET.SubElement(measure, "note")
            if note_data.get("rest"):
                ET.SubElement(note, "rest")
            else:
                step, alter, octave, _ = pitch_for(note_data, tonic, tonic_octave, fifths)
                pitch = ET.SubElement(note, "pitch")
                add_text(pitch, "step", step)
                if alter:
                    add_text(pitch, "alter", alter)
                add_text(pitch, "octave", octave)
            units, note_type, dotted = duration_info(note_data["duration"])
            add_text(note, "duration", units)
            add_text(note, "voice", 1)
            add_text(note, "type", note_type)
            if dotted:
                ET.SubElement(note, "dot")
            if note_data.get("slur_start") or note_data.get("slur_stop"):
                notations = ET.SubElement(note, "notations")
                if note_data.get("slur_start"):
                    ET.SubElement(notations, "slur", type="start", number=str(note_data["slur_start"]))
                if note_data.get("slur_stop"):
                    ET.SubElement(notations, "slur", type="stop", number=str(note_data["slur_stop"]))
            verse_map = lyric_assignments[measure_index - 1]
            for key_code, syllable in sorted(verse_map.items()):
                encoded_note_index, verse = divmod(key_code, 100)
                if encoded_note_index == note_index:
                    lyric = ET.SubElement(note, "lyric", number=str(verse))
                    add_text(lyric, "syllabic", "single")
                    add_text(lyric, "text", syllable)
        if measure_index == len(measures):
            barline = ET.SubElement(measure, "barline", location="right")
            add_text(barline, "bar-style", "light-heavy")

    ET.indent(root, space="  ")
    output_dir.mkdir(parents=True, exist_ok=True)
    basename = safe_name(str(data.get("output_basename") or title))
    xml_path = output_dir / f"{basename}.musicxml"
    ET.ElementTree(root).write(xml_path, encoding="utf-8", xml_declaration=True)
    ET.parse(xml_path)
    midi_path = output_dir / f"{basename}.mid"
    midi_path.write_bytes(midi_file(midi_events, int(data.get("preview_tempo", 80)), title, time_sig))

    transcription_path = output_dir / f"{basename}-transcription.md"
    transcription_lines = [f"# {title}", "", f"1={tonic}  {time_sig[0]}/{time_sig[1]}", ""]
    for index, measure in enumerate(measures, 1):
        tokens = []
        for note in measure["notes"]:
            if note.get("rest"):
                token = "0"
            else:
                token = str(note["degree"])
                token += "′" * max(0, int(note.get("octave", 0)))
                token += "₋" * max(0, -int(note.get("octave", 0)))
            tokens.append(f"{token}/{note['duration']}")
        transcription_lines.append(f"m.{index}: " + " ".join(tokens))
        for verse, syllables in measure.get("lyrics", {}).items():
            transcription_lines.append(f"  verse {verse}: " + " ".join(syllables))
    transcription_path.write_text("\n".join(transcription_lines) + "\n", encoding="utf-8")

    report_path = output_dir / f"{basename}-report.md"
    assumptions = data.get("assumptions", [])
    report_lines = [
        f"# {title} conversion report", "",
        f"- Measures: {len(measures)}", f"- Meter: {time_sig[0]}/{time_sig[1]}",
        f"- Key: 1={tonic} major", "- Measure-duration validation: passed",
        "- MusicXML parse validation: passed", "- MIDI generation: passed", "",
        "## Assumptions", "",
    ]
    report_lines.extend(f"- {item}" for item in assumptions)
    if not assumptions:
        report_lines.append("- None recorded.")
    report_lines += ["", "## Remaining validation", "", "- Import/render the MusicXML and compare it with the source image system by system."]
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    return [xml_path, midi_path, transcription_path, report_path]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_json", type=Path)
    parser.add_argument("output_directory", type=Path)
    args = parser.parse_args()
    try:
        data = json.loads(args.input_json.read_text(encoding="utf-8"))
        outputs = build(data, args.output_directory)
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    for path in outputs:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
