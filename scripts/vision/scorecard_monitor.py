#!/usr/bin/python3
"""Scorecard Change Detection for Suksham Vachak Vision PoC.

Monitors a cricket broadcast scorecard region for changes using SSIM,
then applies OCR to extract score text when a change is detected.

Two-stage ROI:
  1. TV region — crop just the TV screen from the camera frame
  2. Scorecard region — crop the scorecard overlay from within the TV image

Usage:
    # Interactive ROI selector (run once to find coordinates)
    python scorecard_monitor.py select-roi --frame path/to/frame.jpg

    # Monitor a live RTSP stream
    python scorecard_monitor.py monitor \
        --url "rtsps://192.168.50.1:7441/..." \
        --config config/scorecard_roi.json

    # Process a directory of captured frames
    python scorecard_monitor.py replay \
        --session data/raw_frames/session_XXXXXXXX \
        --config config/scorecard_roi.json
"""

import argparse
import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2
import numpy as np

os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")


def compute_ssim(img_a: np.ndarray, img_b: np.ndarray) -> float:
    """Compute SSIM between two grayscale images.

    Uses OpenCV-native implementation to avoid scikit-image dependency
    on Pi. Falls back to scikit-image if available for better accuracy.
    """
    # Convert to grayscale if needed
    if len(img_a.shape) == 3:
        img_a = cv2.cvtColor(img_a, cv2.COLOR_BGR2GRAY)
    if len(img_b.shape) == 3:
        img_b = cv2.cvtColor(img_b, cv2.COLOR_BGR2GRAY)

    # Ensure same size
    if img_a.shape != img_b.shape:
        img_b = cv2.resize(img_b, (img_a.shape[1], img_a.shape[0]))

    try:
        from skimage.metrics import structural_similarity

        score, _ = structural_similarity(img_a, img_b, full=True)
        return float(score)
    except ImportError:
        pass

    # OpenCV-native SSIM (Wang et al. 2004)
    c1 = (0.01 * 255) ** 2
    c2 = (0.03 * 255) ** 2

    img_a = img_a.astype(np.float64)
    img_b = img_b.astype(np.float64)

    mu_a = cv2.GaussianBlur(img_a, (11, 11), 1.5)
    mu_b = cv2.GaussianBlur(img_b, (11, 11), 1.5)

    mu_a_sq = mu_a**2
    mu_b_sq = mu_b**2
    mu_ab = mu_a * mu_b

    sigma_a_sq = cv2.GaussianBlur(img_a**2, (11, 11), 1.5) - mu_a_sq
    sigma_b_sq = cv2.GaussianBlur(img_b**2, (11, 11), 1.5) - mu_b_sq
    sigma_ab = cv2.GaussianBlur(img_a * img_b, (11, 11), 1.5) - mu_ab

    numerator = (2 * mu_ab + c1) * (2 * sigma_ab + c2)
    denominator = (mu_a_sq + mu_b_sq + c1) * (sigma_a_sq + sigma_b_sq + c2)

    ssim_map = numerator / denominator
    return float(ssim_map.mean())


class ROISelector:
    """Interactive tool to select TV and scorecard regions from a frame."""

    def __init__(self):
        self.rois = {}

    def select(self, frame: np.ndarray, output_path: Path):
        """Interactively select TV and scorecard ROIs."""
        print("\n  ROI Selection")
        print("  =============")
        print("  1. Draw a rectangle around the TV SCREEN (not the bezel)")
        print("     Press ENTER to confirm, 'c' to redo")
        print("  2. Then draw a rectangle around the SCORECARD region")
        print("     within the TV area")
        print()

        # Select TV region
        print("  [Step 1/2] Select the TV screen region...")
        tv_roi = cv2.selectROI("Select TV Region", frame, fromCenter=False, showCrosshair=True)
        cv2.destroyAllWindows()

        if tv_roi == (0, 0, 0, 0):
            print("  Cancelled.")
            return

        x, y, w, h = tv_roi
        tv_crop = frame[y : y + h, x : x + w]

        # Select scorecard region within TV
        print("  [Step 2/2] Select the SCORECARD region within the TV...")
        sc_roi = cv2.selectROI("Select Scorecard Region", tv_crop, fromCenter=False, showCrosshair=True)
        cv2.destroyAllWindows()

        if sc_roi == (0, 0, 0, 0):
            print("  Cancelled.")
            return

        config = {
            "tv_region": {"x": int(tv_roi[0]), "y": int(tv_roi[1]), "w": int(tv_roi[2]), "h": int(tv_roi[3])},
            "scorecard_region": {
                "x": int(sc_roi[0]),
                "y": int(sc_roi[1]),
                "w": int(sc_roi[2]),
                "h": int(sc_roi[3]),
            },
            "source_resolution": f"{frame.shape[1]}x{frame.shape[0]}",
            "created": datetime.now(tz=timezone.utc).isoformat(),
        }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(config, indent=2))

        # Show preview
        preview = frame.copy()
        # TV region in green
        cv2.rectangle(preview, (x, y), (x + w, y + h), (0, 255, 0), 3)
        # Scorecard region in yellow (translated to full frame coords)
        sx, sy, sw, sh = sc_roi
        cv2.rectangle(preview, (x + sx, y + sy), (x + sx + sw, y + sy + sh), (0, 255, 255), 3)
        cv2.imshow("ROI Preview (press any key)", preview)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

        print(f"\n  ROI config saved: {output_path}")
        print(f"    TV region:        {tv_roi}")
        print(f"    Scorecard region: {sc_roi} (relative to TV)")
        return config


class ScorecardMonitor:
    """Monitors scorecard region for changes and extracts score via OCR."""

    def __init__(self, config_path: Path, ssim_threshold: float = 0.92):
        with open(config_path) as f:
            config = json.load(f)

        tv = config["tv_region"]
        self.tv_roi = (tv["x"], tv["y"], tv["w"], tv["h"])

        sc = config["scorecard_region"]
        self.sc_roi = (sc["x"], sc["y"], sc["w"], sc["h"])

        self.ssim_threshold = ssim_threshold
        self.prev_scorecard = None
        self.ocr_reader = None
        self.events = []

    def _init_ocr(self):
        """Lazy-init EasyOCR (slow to load, only do it once)."""
        if self.ocr_reader is None:
            import easyocr

            self.ocr_reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    def crop_scorecard(self, frame: np.ndarray) -> np.ndarray:
        """Extract the scorecard region from a full camera frame."""
        # Crop TV region
        tx, ty, tw, th = self.tv_roi
        tv_crop = frame[ty : ty + th, tx : tx + tw]

        # Crop scorecard within TV
        sx, sy, sw, sh = self.sc_roi
        scorecard = tv_crop[sy : sy + sh, sx : sx + sw]

        return scorecard

    def preprocess_scorecard(self, scorecard: np.ndarray) -> np.ndarray:
        """Preprocess scorecard crop for better OCR.

        Cricket scorecards are typically white/yellow text on dark background.
        """
        # Upscale for better OCR (scorecard crops are often small)
        h, w = scorecard.shape[:2]
        if w < 400:
            scale = 400 / w
            scorecard = cv2.resize(scorecard, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)

        # Convert to grayscale
        gray = cv2.cvtColor(scorecard, cv2.COLOR_BGR2GRAY)

        # Increase contrast (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)

        # Sharpen
        blurred = cv2.GaussianBlur(enhanced, (0, 0), 3)
        sharpened = cv2.addWeighted(enhanced, 1.5, blurred, -0.5, 0)

        return sharpened

    def read_scorecard(self, scorecard: np.ndarray) -> str:
        """OCR the scorecard region and return extracted text."""
        self._init_ocr()
        processed = self.preprocess_scorecard(scorecard)
        results = self.ocr_reader.readtext(processed, detail=0, paragraph=True)
        return " | ".join(results) if results else ""

    def check_change(self, frame: np.ndarray, timestamp: str = "") -> dict | None:
        """Check if scorecard has changed. Returns event dict if changed."""
        scorecard = self.crop_scorecard(frame)
        gray = cv2.cvtColor(scorecard, cv2.COLOR_BGR2GRAY)

        if self.prev_scorecard is None:
            self.prev_scorecard = gray
            # OCR the first frame to establish baseline
            text = self.read_scorecard(scorecard)
            event = {
                "type": "baseline",
                "timestamp": timestamp or datetime.now(tz=timezone.utc).isoformat(),
                "ssim": 1.0,
                "score_text": text,
            }
            self.events.append(event)
            return event

        ssim = compute_ssim(self.prev_scorecard, gray)

        if ssim < self.ssim_threshold:
            # Scorecard changed — OCR it
            text = self.read_scorecard(scorecard)
            event = {
                "type": "change",
                "timestamp": timestamp or datetime.now(tz=timezone.utc).isoformat(),
                "ssim": round(ssim, 4),
                "score_text": text,
            }
            self.events.append(event)
            self.prev_scorecard = gray
            return event

        # No change — still update reference to handle gradual drift
        self.prev_scorecard = gray
        return None

    def save_log(self, output_path: Path):
        """Save the event log to JSON."""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(self.events, indent=2))
        print(f"  Event log saved: {output_path} ({len(self.events)} events)")


def cmd_select_roi(args):
    """Handle the select-roi subcommand."""
    frame = cv2.imread(args.frame)
    if frame is None:
        print(f"  Cannot read frame: {args.frame}")
        return

    output = Path(args.output)
    selector = ROISelector()
    selector.select(frame, output)


def cmd_replay(args):
    """Process captured frames offline."""
    session_dir = Path(args.session)
    frames = sorted(session_dir.glob("frame_*.jpg"))

    if not frames:
        print(f"  No frames found in {session_dir}")
        return

    monitor = ScorecardMonitor(Path(args.config), ssim_threshold=args.threshold)
    log_path = session_dir / "scorecard_events.json"

    print(f"\n  Replaying {len(frames)} frames from {session_dir.name}")
    print(f"  SSIM threshold: {args.threshold}")
    print()

    for i, frame_path in enumerate(frames):
        frame = cv2.imread(str(frame_path))
        if frame is None:
            continue

        # Extract timestamp from filename
        ts = frame_path.stem.split("_", 2)[-1]

        event = monitor.check_change(frame, timestamp=ts)
        if event:
            etype = event["type"].upper()
            ssim = event["ssim"]
            text = event["score_text"]
            print(f"  [{i + 1:4d}/{len(frames)}] {etype} (SSIM={ssim:.4f}): {text}")

    monitor.save_log(log_path)
    print(f"\n  Done. {len(monitor.events)} events detected.")


def cmd_monitor(args):
    """Monitor a live RTSP stream."""
    monitor = ScorecardMonitor(Path(args.config), ssim_threshold=args.threshold)
    log_path = Path(args.output) / f"scorecard_events_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    check_interval = args.interval

    print("\n  Live scorecard monitoring")
    print(f"  SSIM threshold: {args.threshold}")
    print(f"  Check interval: {check_interval}s")
    print("  Press Ctrl+C to stop\n")

    cap = cv2.VideoCapture(args.url, cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    if not cap.isOpened():
        print(f"  Cannot open stream: {args.url}")
        return

    try:
        while True:
            # Drain buffer to get latest frame
            for _ in range(5):
                cap.grab()
            ret, frame = cap.read()

            if not ret:
                print("  Frame read failed, retrying...")
                time.sleep(2)
                continue

            event = monitor.check_change(frame)
            if event:
                etype = event["type"].upper()
                ssim = event["ssim"]
                text = event["score_text"]
                print(f"  [{datetime.now().strftime('%H:%M:%S')}] {etype} (SSIM={ssim:.4f}): {text}")

            time.sleep(check_interval)

    except KeyboardInterrupt:
        print("\n  Stopping...")
    finally:
        cap.release()
        monitor.save_log(log_path)


def main():
    parser = argparse.ArgumentParser(description="Cricket scorecard change detection")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # select-roi
    roi_parser = subparsers.add_parser("select-roi", help="Interactively select TV and scorecard regions")
    roi_parser.add_argument("--frame", required=True, help="Path to a sample frame")
    roi_parser.add_argument("--output", default="config/scorecard_roi.json", help="Output config path")

    # replay
    replay_parser = subparsers.add_parser("replay", help="Process captured frames offline")
    replay_parser.add_argument("--session", required=True, help="Path to capture session directory")
    replay_parser.add_argument("--config", required=True, help="Path to ROI config JSON")
    replay_parser.add_argument("--threshold", type=float, default=0.92, help="SSIM threshold (default: 0.92)")

    # monitor
    monitor_parser = subparsers.add_parser("monitor", help="Monitor live RTSP stream")
    monitor_parser.add_argument("--url", required=True, help="RTSP stream URL")
    monitor_parser.add_argument("--config", required=True, help="Path to ROI config JSON")
    monitor_parser.add_argument("--threshold", type=float, default=0.92, help="SSIM threshold (default: 0.92)")
    monitor_parser.add_argument("--interval", type=float, default=3.0, help="Check interval in seconds (default: 3.0)")
    monitor_parser.add_argument("--output", default="data/events", help="Output directory for event logs")

    args = parser.parse_args()

    print("\n" + "=" * 55)
    print("  Suksham Vachak — Scorecard Monitor")
    print("=" * 55)

    if args.command == "select-roi":
        cmd_select_roi(args)
    elif args.command == "replay":
        cmd_replay(args)
    elif args.command == "monitor":
        cmd_monitor(args)


if __name__ == "__main__":
    main()
