#!/usr/bin/env python3
"""Video frame extraction utility using OpenCV and modern Python best practices."""

from __future__ import annotations

import argparse
import contextlib
import logging
import sys
from collections.abc import Generator
from pathlib import Path
from typing import NamedTuple

import cv2
import numpy as np

logger = logging.getLogger("frame_extractor")


class VideoMetadata(NamedTuple):
    """Metadata container for an opened video stream."""

    fps: float
    total_frames: int
    duration_seconds: float
    width: int
    height: int


@contextlib.contextmanager
def open_video_capture(video_path: Path) -> Generator[cv2.VideoCapture, None, None]:
    """Context manager ensuring safe acquisition and release of cv2.VideoCapture."""
    cap = cv2.VideoCapture(str(video_path))
    try:
        if not cap.isOpened():
            raise FileNotFoundError(f"Failed to open video file: {video_path}")
        yield cap
    finally:
        cap.release()


def get_video_metadata(cap: cv2.VideoCapture) -> VideoMetadata:
    """Extract and validate video stream properties with defensive fallbacks."""
    fps = cap.get(cv2.CAP_PROP_FPS)
    if fps <= 0 or np.isnan(fps):
        logger.warning("Invalid or missing FPS metadata; falling back to 30.0.")
        fps = 30.0

    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_seconds = total_frames / fps if total_frames > 0 else 0.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

    return VideoMetadata(
        fps=fps,
        total_frames=total_frames,
        duration_seconds=duration_seconds,
        width=width,
        height=height,
    )


def generate_sampled_frames(
    cap: cv2.VideoCapture,
    source_fps: float,
    target_fps: float,
) -> Generator[tuple[int, float, np.ndarray], None, None]:
    """Yield target frames without fully decoding skipped intermediate frames.

    Yields:
        tuple[int, float, np.ndarray]: (frame_index, timestamp_seconds, frame_bgr)
    """
    frame_interval_seconds = 1.0 / target_fps
    next_capture_timestamp = 0.0
    frame_idx = 0

    while True:
        # cap.grab() advances the decoder without decompressing the full frame image
        if not cap.grab():
            break

        current_timestamp = frame_idx / source_fps

        if current_timestamp >= next_capture_timestamp:
            ret, frame = cap.retrieve()
            if not ret or frame is None:
                logger.warning("Frame retrieve failed at frame %d", frame_idx)
                break

            yield frame_idx, current_timestamp, frame
            next_capture_timestamp += frame_interval_seconds

        frame_idx += 1


def extract_key_frames(
    video_path: Path,
    output_dir: Path,
    target_fps: float = 1.0,
    jpeg_quality: int = 95,
) -> int:
    """Orchestrate extraction and persist sampled frames to disk.

    Returns:
        int: Number of frames successfully saved.
    """
    if not video_path.is_file():
        raise FileNotFoundError(f"Input file not found: {video_path}")

    if target_fps <= 0:
        raise ValueError(f"Target FPS must be positive, got {target_fps}")

    output_dir.mkdir(parents=True, exist_ok=True)
    encode_params = [int(cv2.IMWRITE_JPEG_QUALITY), jpeg_quality]

    with open_video_capture(video_path) as cap:
        meta = get_video_metadata(cap)
        logger.info(
            "Opened '%s' | Resolution: %dx%d | Source FPS: %.2f | Length: %.1fs",
            video_path.name,
            meta.width,
            meta.height,
            meta.fps,
            meta.duration_seconds,
        )

        saved_count = 0
        for frame_idx, timestamp_sec, frame in generate_sampled_frames(
            cap, meta.fps, target_fps
        ):
            output_file = (
                output_dir / f"frame_{saved_count:05d}_t{timestamp_sec:.2f}s.jpg"
            )
            success = cv2.imwrite(str(output_file), frame, encode_params)

            if not success:
                logger.error("Failed to write image to %s", output_file)
                continue

            saved_count += 1

    logger.info("Extracted %d frames to '%s'", saved_count, output_dir)
    return saved_count


def configure_logging(verbose: bool = False) -> None:
    """Set up structured console logging format."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="[%(asctime)s] [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser with rich documentation."""
    parser = argparse.ArgumentParser(
        prog="extract_frames",
        description="High-performance frame extraction utility for video pipelines.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Extract 1 frame per second (default):
  python extract_frames.py input.mp4 ./frames

  # Extract 0.5 frames per second (1 frame every 2 seconds):
  python extract_frames.py input.mp4 ./frames --fps 0.5

  # Extract high-frequency frames with custom compression quality:
  python extract_frames.py input.mp4 ./frames --fps 5.0 --quality 85 -v
        """,
    )

    parser.add_argument(
        "video_path",
        type=Path,
        help="Path to the input video file (e.g., .mp4, .mkv, .mov).",
    )
    parser.add_argument(
        "output_dir",
        type=Path,
        help="Directory where extracted JPEG frames will be saved.",
    )
    parser.add_argument(
        "--fps",
        type=float,
        default=1.0,
        metavar="FLOAT",
        help="Target sampling rate in frames per second (supports fractional values, default: 1.0).",
    )
    parser.add_argument(
        "--quality",
        type=int,
        default=95,
        choices=range(1, 101),
        metavar="[1-100]",
        help="JPEG output image quality from 1 to 100 (default: 95).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable detailed debug output.",
    )

    return parser


def main() -> int:
    """CLI entry point handling exit codes cleanly."""
    parser = build_parser()
    args = parser.parse_args()

    configure_logging(args.verbose)

    try:
        extract_key_frames(
            video_path=args.video_path,
            output_dir=args.output_dir,
            target_fps=args.fps,
            jpeg_quality=args.quality,
        )
        return 0
    except (FileNotFoundError, ValueError) as err:
        logger.error("%s", err)
        return 1
    except KeyboardInterrupt:
        logger.warning("Frame extraction cancelled by user.")
        return 130
    except Exception:
        logger.exception("An unexpected fatal error occurred.")
        return 2


if __name__ == "__main__":
    sys.exit(main())
