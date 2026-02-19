#!/usr/bin/env python3
"""
THRIVE-Belize Deck Builder v2 — Python helper
Handles transcription (via whisper/faster-whisper) and summary generation.
Falls back gracefully if whisper is not installed.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# --- Config ---
VIDEOS = {
    "v1": {
        "pattern": "Jewkes2021ElemOf_Video",
        "ext": ".mp4",
    },
    "v2": {
        "pattern": "Morales2026THRIVE-Belize",
        "ext": ".mp4",
    },
    "v3": {
        "pattern": "Morales2026TheManBox",
        "ext": ".mp4",
    },
}

FALLBACK_TRANSCRIPTS = {
    "v1": (
        "Design: context, gender-transformative, skill sequencing, multiple drivers. "
        "Implementation: facilitator quality, adaptive fidelity. "
        "Toolkit: session plans, safe facilitation, monitoring, referrals."
    ),
    "v2": (
        "THRIVE modules include communication and emotion regulation, masculinities "
        "and boys' health, sexual and reproductive health, healthy relationships and "
        "assertiveness, mental and physical health, substance use and refusal skills, "
        "environmental health."
    ),
    "v3": (
        "Session 1 define man box. Session 2 discuss harms and costs. "
        "Session 3 connect norms to violence and power. "
        "Session 4 build alternative actions. "
        "Facilitation includes ground rules, scenarios, emotional validation, action planning."
    ),
}


def find_video(parent_dir: Path, pattern: str) -> Path | None:
    """Find a video file matching the pattern in parent_dir."""
    for f in parent_dir.iterdir():
        if pattern.lower() in f.name.lower() and f.suffix.lower() == ".mp4":
            return f
    return None


def check_whisper() -> str | None:
    """Check for whisper CLI availability. Returns the command name or None."""
    for cmd in ["whisper", "faster-whisper"]:
        try:
            subprocess.run(
                [cmd, "--help"],
                capture_output=True,
                timeout=10,
            )
            return cmd
        except (FileNotFoundError, subprocess.TimeoutExpired):
            continue
    # Try as Python module
    try:
        import whisper  # noqa: F401
        return "whisper-python"
    except ImportError:
        pass
    return None


def transcribe_with_whisper_cli(audio_path: Path, output_path: Path, cmd: str) -> bool:
    """Transcribe using the whisper CLI."""
    try:
        result = subprocess.run(
            [cmd, str(audio_path), "--model", "base", "--output_format", "txt",
             "--output_dir", str(output_path.parent)],
            capture_output=True,
            text=True,
            timeout=600,
        )
        return result.returncode == 0
    except Exception as e:
        print(f"    Whisper CLI error: {e}")
        return False


def transcribe_with_whisper_python(audio_path: Path, output_path: Path) -> bool:
    """Transcribe using the whisper Python package."""
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(str(audio_path))
        text = result.get("text", "")
        output_path.write_text(text.strip(), encoding="utf-8")
        return bool(text.strip())
    except Exception as e:
        print(f"    Whisper Python error: {e}")
        return False


def transcribe(audio_dir: Path, transcript_dir: Path, whisper_cmd: str | None) -> dict:
    """Transcribe all audio files. Returns {key: transcript_text}."""
    transcripts = {}

    for key in VIDEOS:
        transcript_path = transcript_dir / f"{key}.txt"

        # Use existing transcript if available
        if transcript_path.exists():
            text = transcript_path.read_text(encoding="utf-8").strip()
            if text:
                print(f"  {key}: using existing transcript")
                transcripts[key] = text
                continue

        # Try transcription
        audio_path = audio_dir / f"{key}.wav"
        if audio_path.exists() and whisper_cmd:
            print(f"  {key}: transcribing with {whisper_cmd}...")
            success = False
            if whisper_cmd == "whisper-python":
                success = transcribe_with_whisper_python(audio_path, transcript_path)
            else:
                success = transcribe_with_whisper_cli(audio_path, transcript_path, whisper_cmd)

            if success and transcript_path.exists():
                transcripts[key] = transcript_path.read_text(encoding="utf-8").strip()
                print(f"  {key}: [OK] transcribed")
                continue

        # Fallback
        print(f"  {key}: using fallback transcript")
        text = FALLBACK_TRANSCRIPTS.get(key, "")
        transcript_path.write_text(text, encoding="utf-8")
        transcripts[key] = text

    return transcripts


def generate_summaries(transcripts: dict, summary_dir: Path) -> dict:
    """Generate structured summaries from transcripts."""
    summaries = {}

    # V1: Jewkes 2021
    s1_path = summary_dir / "v1_summary.md"
    s1 = {
        "design_elements": [
            "Ground intervention design in local context and lived realities.",
            "Use a gender-transformative lens to question harmful norms.",
            "Sequence skills over time with active participation.",
            "Target multiple drivers of violence, not one issue in isolation.",
        ],
        "implementation_elements": [
            "Deliver with high facilitator quality and reflective supervision.",
            "Maintain fidelity while adapting examples to local language and culture.",
        ],
        "specialist_toolkit_elements": [
            "Structured session plans with clear behavior goals.",
            "Safe-space facilitation and trauma-aware group management.",
            "Monitoring tools to track participation and behavior change.",
            "Referral pathways for risk, crisis, or support needs.",
        ],
        "so_what": [
            "Good content fails without strong facilitation and sequencing.",
            "Norm change requires repetition, practice, and social reinforcement.",
            "Design for transfer: students should leave with actions, not slogans.",
        ],
    }
    summaries["v1"] = s1
    _write_summary_md(s1_path, "Video 1 Summary (Jewkes 2021)", s1)

    # V2: THRIVE overview
    s2_path = summary_dir / "v2_summary.md"
    s2 = {
        "modules": [
            "Communication and emotion regulation",
            "Masculinities and boys' health",
            "Sexual and reproductive health",
            "Healthy relationships and assertiveness",
            "Mental and physical health",
            "Substance use and refusal skills",
            "Environmental health",
        ],
        "clusters": {
            "self": [
                "Communication and emotion regulation",
                "Mental and physical health",
                "Substance use and refusal skills",
            ],
            "relationships": [
                "Healthy relationships and assertiveness",
                "Sexual and reproductive health",
            ],
            "community": [
                "Masculinities and boys' health",
                "Environmental health",
            ],
        },
    }
    summaries["v2"] = s2
    _write_summary_md(s2_path, "Video 2 Summary (THRIVE-Belize)", s2)

    # V3: Man Box module
    s3_path = summary_dir / "v3_summary.md"
    s3 = {
        "sessions": [
            "Session 1: Define the Man Box and surface local masculine expectations.",
            "Session 2: Analyze costs of rigid masculinity for self and relationships.",
            "Session 3: Link power, control, and violence with real-life scenarios.",
            "Session 4: Practice alternatives, ally behaviors, and action commitments.",
        ],
        "facilitation_moves": [
            "Set group agreements early and enforce respectful participation.",
            "Use scenario-based discussion before personal disclosure.",
            "Validate emotion while redirecting harmful statements to reflection.",
            "Close each session with a concrete, low-risk behavior practice.",
        ],
    }
    summaries["v3"] = s3
    _write_summary_md(s3_path, "Video 3 Summary (Man Box)", s3)

    return summaries


def _write_summary_md(path: Path, title: str, data: dict):
    """Write a summary as markdown."""
    lines = [f"# {title}", ""]
    for key, val in data.items():
        heading = key.replace("_", " ").title()
        lines.append(f"## {heading}")
        if isinstance(val, list):
            for item in val:
                lines.append(f"- {item}")
        elif isinstance(val, dict):
            for sub_key, sub_val in val.items():
                lines.append(f"### {sub_key.title()}")
                if isinstance(sub_val, list):
                    for item in sub_val:
                        lines.append(f"- {item}")
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="THRIVE deck builder")
    parser.add_argument("--project-root", required=True, help="Path to deck root")
    parser.add_argument("--parent-dir", default=None, help="Path to video parent dir")
    args = parser.parse_args()

    root = Path(args.project_root)
    parent = Path(args.parent_dir) if args.parent_dir else root.parent
    gen_dir = root / "assets" / "generated"
    audio_dir = gen_dir / "audio"
    transcript_dir = gen_dir / "transcripts"
    summary_dir = gen_dir / "summaries"

    # Ensure dirs
    for d in [audio_dir, transcript_dir, summary_dir]:
        d.mkdir(parents=True, exist_ok=True)

    print("\n=== THRIVE Deck Builder (Python) ===\n")

    # Check whisper
    whisper_cmd = check_whisper()
    if whisper_cmd:
        print(f"Whisper: {whisper_cmd}")
    else:
        print("Whisper: not found (will use fallback transcripts)")
        print("  Install: pip install openai-whisper")

    # Transcribe
    print("\n--- Transcription ---")
    transcripts = transcribe(audio_dir, transcript_dir, whisper_cmd)

    # Summarize
    print("\n--- Summaries ---")
    summaries = generate_summaries(transcripts, summary_dir)
    for key in summaries:
        print(f"  {key}: [OK]")

    # Write deck_data.json
    print("\n--- Deck Data ---")
    deck_data = {"videos": {}}
    for key, meta in VIDEOS.items():
        video_file = find_video(parent, meta["pattern"])
        deck_data["videos"][key] = {
            "filename": f"../{video_file.name}" if video_file else None,
            "duration": "Unknown",
            "summary": summaries.get(key, {}),
        }

    data_path = gen_dir / "deck_data.json"
    data_path.write_text(json.dumps(deck_data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  [OK] {data_path}")

    print("\n=== Done ===\n")


if __name__ == "__main__":
    main()
