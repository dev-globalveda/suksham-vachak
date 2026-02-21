#!/usr/bin/python3
"""Video Capture for Suksham Vachak Vision PoC.

Captures frames from either:
  - RTSP stream (UniFi Protect G6 camera pointed at TV)
  - USB capture device (Elgato Cam Link 4K for direct HDMI feed)

Usage:
    # G6 camera via RTSP
    python capture_rtsp.py --source "rtsps://192.168.50.1:7441/..." --fps 1 --duration 10800

    # Elgato Cam Link via USB (clean HDMI capture)
    python capture_rtsp.py --source camlink --fps 1 --duration 10800 --record-av

    # Specific /dev/video device
    python capture_rtsp.py --source /dev/video0 --fps 1

Output:
    data/raw_frames/
        session_YYYYMMDD_HHMMSS/
            frame_000001_20260221_093015.jpg
            ...
            session_meta.json
    data/raw_video/   (with --record-av)
        session_YYYYMMDD_HHMMSS.mkv
"""

import argparse
import json
import os
import signal
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import cv2

# Allow RTSPS with self-signed certs (UniFi Protect)
os.environ.setdefault("OPENCV_FFMPEG_CAPTURE_OPTIONS", "rtsp_transport;tcp")


def detect_camlink() -> str | None:
    """Auto-detect Elgato Cam Link device path on Linux."""
    import glob

    for dev in sorted(glob.glob("/dev/video*")):
        try:
            cap = cv2.VideoCapture(dev)
            if cap.isOpened():
                w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                cap.release()
                # Cam Link typically shows up as 1920x1080 or 3840x2160
                if w >= 1920:
                    return dev
            cap.release()
        except Exception:  # noqa: S112
            continue
    return None


def resolve_source(source: str) -> tuple[str, str]:
    """Resolve source argument to (open_target, source_type).

    Returns:
        (target, type) where target is what to pass to cv2.VideoCapture
        and type is 'rtsp', 'usb', or 'file'.
    """
    if source == "camlink":
        dev = detect_camlink()
        if dev is None:
            msg = "Cam Link not detected. Check USB connection and run: ls /dev/video*"
            raise RuntimeError(msg)
        print(f"  Auto-detected Cam Link: {dev}")
        return dev, "usb"
    elif source.startswith(("rtsp://", "rtsps://")):
        return source, "rtsp"
    elif source.startswith("/dev/video"):
        return source, "usb"
    elif Path(source).is_file():
        return source, "file"
    else:
        # Try as device index (e.g. "0")
        try:
            idx = int(source)
            return str(idx), "usb"
        except ValueError as err:
            msg = f"Unknown source: {source}"
            raise RuntimeError(msg) from err


class AVRecorder:
    """Records full audio+video stream via ffmpeg as a sidecar process."""

    def __init__(self, source: str, source_type: str, output_path: Path, duration: int | None = None):
        self.output_path = output_path
        self.process: subprocess.Popen | None = None

        output_path.parent.mkdir(parents=True, exist_ok=True)

        if source_type == "rtsp":
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-rtsp_transport",
                "tcp",
                "-i",
                source,
                "-c",
                "copy",
            ]
        elif source_type == "usb":
            # For USB capture devices, ffmpeg reads from v4l2
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-f",
                "v4l2",
                "-video_size",
                "1920x1080",
                "-i",
                source,
                # Also capture audio from the Cam Link's ALSA device
                "-f",
                "alsa",
                "-i",
                "default",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-crf",
                "23",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
            ]
        else:
            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "warning",
                "-i",
                source,
                "-c",
                "copy",
            ]

        if duration:
            cmd.extend(["-t", str(duration)])
        cmd.append(str(output_path))

        self.cmd = cmd

    def start(self):
        """Start ffmpeg recording in background."""
        self.process = subprocess.Popen(  # noqa: S603
            self.cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        print(f"  A/V recording: {self.output_path}")
        print(f"  ffmpeg PID: {self.process.pid}")

    def stop(self):
        """Gracefully stop ffmpeg."""
        if self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

        if self.output_path.exists():
            size_mb = self.output_path.stat().st_size / (1024 * 1024)
            print(f"  A/V file: {self.output_path} ({size_mb:.1f} MB)")
        else:
            print("  A/V recording: no file produced (ffmpeg may have failed)")


class VideoCapture:
    """Captures frames from an RTSP stream or USB device at a target FPS."""

    def __init__(
        self,
        source: str,
        source_type: str,
        output_dir: Path,
        target_fps: float = 1.0,
        quality: int = 90,
        max_reconnects: int = 10,
        reconnect_delay: float = 5.0,
    ):
        self.source = source
        self.source_type = source_type
        self.target_fps = target_fps
        self.quality = quality
        self.max_reconnects = max_reconnects
        self.reconnect_delay = reconnect_delay
        self.running = False
        self.frame_count = 0
        self.drop_count = 0

        # Create session directory
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_id = f"session_{timestamp}"
        self.session_dir = output_dir / self.session_id
        self.session_dir.mkdir(parents=True, exist_ok=True)

        self.meta = {
            "source": source,
            "source_type": source_type,
            "target_fps": target_fps,
            "quality": quality,
            "session_start": datetime.now(tz=timezone.utc).isoformat(),
            "session_end": None,
            "frames_captured": 0,
            "frames_dropped": 0,
            "resolution": None,
            "av_recording": None,
        }

    def _connect(self) -> cv2.VideoCapture:
        """Connect to video source."""
        if self.source_type == "usb":
            # USB device path or index
            try:
                cap = cv2.VideoCapture(int(self.source))
            except ValueError:
                cap = cv2.VideoCapture(self.source)

            # Request 1080p from Cam Link
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        else:
            # RTSP or file
            cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 10000)

        if not cap.isOpened():
            msg = f"Cannot open source: {self.source}"
            raise ConnectionError(msg)

        w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        native_fps = cap.get(cv2.CAP_PROP_FPS)
        self.meta["resolution"] = f"{w}x{h}"

        mode = "USB/HDMI" if self.source_type == "usb" else "RTSP"
        print(f"  Connected [{mode}]: {w}x{h} @ {native_fps:.1f} FPS (capturing at {self.target_fps} FPS)")
        return cap

    def _save_frame(self, frame) -> Path:
        """Save a frame to disk with timestamp filename."""
        self.frame_count += 1
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"frame_{self.frame_count:06d}_{ts}.jpg"
        filepath = self.session_dir / filename
        cv2.imwrite(str(filepath), frame, [cv2.IMWRITE_JPEG_QUALITY, self.quality])
        return filepath

    def _save_meta(self):
        """Write session metadata to JSON."""
        self.meta["session_end"] = datetime.now(tz=timezone.utc).isoformat()
        self.meta["frames_captured"] = self.frame_count
        self.meta["frames_dropped"] = self.drop_count
        meta_path = self.session_dir / "session_meta.json"
        meta_path.write_text(json.dumps(self.meta, indent=2))

    def _read_loop(self, cap: cv2.VideoCapture, start_time: float, duration: int | None, frame_interval: float):
        """Inner frame-read loop. Returns True if should reconnect, False if done."""
        last_capture = 0.0
        while self.running:
            ret, frame = cap.read()

            if not ret:
                self.drop_count += 1
                if self.source_type == "usb":
                    print(f"  Frame drop #{self.drop_count}")
                    time.sleep(0.1)
                    continue
                print(f"  Frame drop #{self.drop_count}, reconnecting...")
                return True

            now = time.monotonic()

            if duration and (now - start_time) >= duration:
                print(f"\n  Duration limit ({duration}s) reached.")
                self.running = False
                return False

            if (now - last_capture) >= frame_interval:
                self._save_frame(frame)
                last_capture = now

                if self.frame_count % 10 == 0:
                    elapsed = now - start_time
                    print(f"  [{elapsed:6.0f}s] Captured {self.frame_count} frames ({self.drop_count} drops)")

        return False

    def capture(self, duration: int | None = None, record_av: bool = False):
        """Main capture loop.

        Args:
            duration: Max capture time in seconds. None = until interrupted.
            record_av: If True, run ffmpeg sidecar to record full A/V stream.
        """
        self.running = True
        reconnects = 0
        start_time = time.monotonic()
        frame_interval = 1.0 / self.target_fps
        av_recorder = None

        def _shutdown(sig, _frame):
            print(f"\n  Signal {sig} received, stopping...")
            self.running = False

        signal.signal(signal.SIGINT, _shutdown)
        signal.signal(signal.SIGTERM, _shutdown)

        if record_av:
            av_path = Path("data/raw_video") / f"{self.session_id}.mkv"
            av_recorder = AVRecorder(self.source, self.source_type, av_path, duration)
            av_recorder.start()
            self.meta["av_recording"] = str(av_path)

        print(f"\n  Session dir: {self.session_dir}")
        print(f"  Target FPS: {self.target_fps}")
        if duration:
            print(f"  Duration: {duration}s")
        print("  Press Ctrl+C to stop\n")

        while self.running:
            try:
                cap = self._connect()
                reconnects = 0
                self._read_loop(cap, start_time, duration, frame_interval)
                cap.release()
            except ConnectionError as e:
                reconnects += 1
                if reconnects > self.max_reconnects:
                    print(f"\n  Max reconnects ({self.max_reconnects}) exceeded. Exiting.")
                    break
                print(f"  Connection error: {e}")
                print(f"  Reconnecting in {self.reconnect_delay}s ({reconnects}/{self.max_reconnects})...")
                time.sleep(self.reconnect_delay)

        if av_recorder:
            print("\n  Stopping A/V recording...")
            av_recorder.stop()

        self._save_meta()
        print("\n  Session complete:")
        print(f"    Frames captured: {self.frame_count}")
        print(f"    Frames dropped:  {self.drop_count}")
        print(f"    Output dir:      {self.session_dir}")
        print(f"    Metadata:        {self.session_dir / 'session_meta.json'}")
        if av_recorder:
            print(f"    A/V recording:   {av_recorder.output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Capture video frames for cricket vision PoC",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Sources:
  "rtsps://..."         UniFi Protect G6 camera (RTSP stream)
  "camlink"             Auto-detect Elgato Cam Link 4K (USB)
  "/dev/video0"         Specific V4L2 device
  "0"                   Device index

Examples:
  # G6 camera via RTSP — 1 FPS for 3 hours
  python capture_rtsp.py --source "rtsps://..." --fps 1 --duration 10800

  # Elgato Cam Link — clean HDMI capture with A/V recording
  python capture_rtsp.py --source camlink --fps 1 --duration 10800 --record-av

  # Quick test — 30 seconds from Cam Link
  python capture_rtsp.py --source camlink --duration 30
        """,
    )
    parser.add_argument(
        "--source", required=True, help="Video source: RTSP URL, 'camlink', /dev/videoN, or device index"
    )
    # Keep --url as hidden alias for backward compatibility
    parser.add_argument("--url", dest="source_alias", help=argparse.SUPPRESS)
    parser.add_argument("--fps", type=float, default=1.0, help="Target capture FPS (default: 1.0)")
    parser.add_argument(
        "--duration", type=int, default=None, help="Max capture duration in seconds (default: unlimited)"
    )
    parser.add_argument(
        "--output", type=str, default="data/raw_frames", help="Output directory for frames (default: data/raw_frames)"
    )
    parser.add_argument("--quality", type=int, default=90, help="JPEG quality 1-100 (default: 90)")
    parser.add_argument("--record-av", action="store_true", help="Also record full A/V stream via ffmpeg")
    args = parser.parse_args()

    # Support --url as alias for --source
    source = args.source_alias or args.source

    print("\n" + "=" * 55)
    print("  Suksham Vachak — Video Capture")
    print("=" * 55)

    target, source_type = resolve_source(source)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    capture = VideoCapture(
        source=target,
        source_type=source_type,
        output_dir=output_dir,
        target_fps=args.fps,
        quality=args.quality,
    )
    capture.capture(duration=args.duration, record_av=args.record_av)


if __name__ == "__main__":
    main()
