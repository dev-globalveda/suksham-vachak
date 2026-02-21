#!/usr/bin/python3
"""Quick frame labeler for cricket scene classification.

Opens captured frames one by one. Press a key to classify:
    p = pitch_view
    b = boundary_view
    r = replay
    c = crowd
    s = scorecard_close
    x = skip (discard frame)
    q = quit

Labeled frames are copied into YOLO classification directory structure:
    data/labeled/
        train/
            pitch_view/
            boundary_view/
            replay/
            crowd/
            scorecard_close/
        val/
            ...

Usage:
    python label_frames.py --session data/raw_frames/session_20260221_093015
    python label_frames.py --session data/raw_frames/session_20260221_093015 --val-split 0.2
"""

import argparse
import random
import shutil
from pathlib import Path

import cv2

CLASSES = {
    ord("p"): "pitch_view",
    ord("b"): "boundary_view",
    ord("r"): "replay",
    ord("c"): "crowd",
    ord("s"): "scorecard_close",
}

SKIP_KEY = ord("x")
QUIT_KEY = ord("q")

# Non-crypto RNG is fine for train/val splitting
_rng = random.Random()  # noqa: S311


def _label_frame(key: int, frame_path: Path, output_dir: Path, val_split: float, counts: dict) -> bool:
    """Process a single keypress. Returns True if frame was labeled."""
    if key not in CLASSES:
        return False

    cls_name = CLASSES[key]
    split = "val" if _rng.random() < val_split else "train"
    dest = output_dir / split / cls_name / frame_path.name
    shutil.copy2(frame_path, dest)
    counts[cls_name] += 1
    return True


def _write_data_yaml(output_dir: Path):
    """Write data.yaml for YOLO training."""
    yaml_path = output_dir / "data.yaml"
    class_names = sorted(CLASSES.values())
    yaml_content = f"path: {output_dir.resolve()}\ntrain: train\nval: val\n\nnc: {len(class_names)}\nnames:\n"
    for name in class_names:
        yaml_content += f"  - {name}\n"
    yaml_path.write_text(yaml_content)
    print(f"\n  YOLO config written: {yaml_path}")


def label_session(session_dir: Path, output_dir: Path, val_split: float = 0.2):
    """Interactively label frames from a capture session."""
    frames = sorted(session_dir.glob("frame_*.jpg"))
    total = len(frames)

    if total == 0:
        print(f"  No frames found in {session_dir}")
        return

    for split in ("train", "val"):
        for cls in CLASSES.values():
            (output_dir / split / cls).mkdir(parents=True, exist_ok=True)

    print(f"\n  Labeling {total} frames from {session_dir.name}")
    print(f"  Output: {output_dir}")
    print(f"  Val split: {val_split:.0%}")
    print()
    print("  Keys:  [p]itch  [b]oundary  [r]eplay  [c]rowd  [s]corecard")
    print("         [x] skip  [q] quit")
    print()

    counts = {cls: 0 for cls in CLASSES.values()}
    labeled = 0
    skipped = 0

    cv2.namedWindow("Label Frame", cv2.WINDOW_NORMAL)
    cv2.resizeWindow("Label Frame", 960, 540)

    for i, frame_path in enumerate(frames):
        img = cv2.imread(str(frame_path))
        if img is None:
            continue

        display = img.copy()
        hud = f"[{i + 1}/{total}] labeled={labeled} skipped={skipped}"
        cv2.putText(display, hud, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 0), 2)
        cv2.putText(
            display,
            "[p]itch [b]oundary [r]eplay [c]rowd [s]corecard [x]skip [q]uit",
            (10, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (0, 255, 0),
            1,
        )

        cv2.imshow("Label Frame", display)
        key = cv2.waitKey(0) & 0xFF

        if key == QUIT_KEY:
            print(f"\n  Quit at frame {i + 1}/{total}")
            break
        elif key == SKIP_KEY:
            skipped += 1
        elif _label_frame(key, frame_path, output_dir, val_split, counts):
            labeled += 1

    cv2.destroyAllWindows()

    print("\n  Labeling complete:")
    print(f"    Labeled: {labeled}")
    print(f"    Skipped: {skipped}")
    print("    Breakdown:")
    for cls, count in sorted(counts.items()):
        print(f"      {cls:20s} {count}")

    _write_data_yaml(output_dir)


def main():
    parser = argparse.ArgumentParser(description="Label captured frames for scene classification")
    parser.add_argument("--session", required=True, help="Path to capture session directory")
    parser.add_argument("--output", default="data/labeled", help="Output directory for labeled data")
    parser.add_argument("--val-split", type=float, default=0.2, help="Fraction for validation (default: 0.2)")
    args = parser.parse_args()

    label_session(
        session_dir=Path(args.session),
        output_dir=Path(args.output),
        val_split=args.val_split,
    )


if __name__ == "__main__":
    main()
