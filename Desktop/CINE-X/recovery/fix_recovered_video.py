from pathlib import Path
import subprocess
import sys


# ============================================================
# CINE-X — RECOVERED VIDEO PLAYBACK OPTIMIZER
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FFMPEG = Path(
    r"C:\Users\Aditi Gupta\Downloads\ffmpeg-9.0.1-essentials_build"
    r"\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
)

INPUT = BASE_DIR / "recovered" / "cine_x_recovered.h264"
OUTPUT = BASE_DIR / "recovered" / "cine_x_recovered_fixed.mp4"


# ============================================================
# CHECKS
# ============================================================

print()
print("CINE-X RECOVERED VIDEO OPTIMIZER")
print("=" * 70)

print(f"Input:  {INPUT}")
print(f"Output: {OUTPUT}")
print()

if not FFMPEG.exists():
    print("❌ FFmpeg was not found.")
    print(f"Expected: {FFMPEG}")
    sys.exit(1)

if not INPUT.exists():
    print("❌ Recovered H.264 file does not exist.")
    print(f"Missing: {INPUT}")
    sys.exit(1)


# ============================================================
# OPTIMIZATION
# ============================================================

print("Rebuilding a clean playback stream...")
print()
print("This creates a NEW MP4.")
print("The original recovered H.264 and MP4 are preserved.")
print()


command = [
    str(FFMPEG),

    "-y",

    # Input format
    "-f",
    "h264",

    # Known CCTV frame rate
    "-framerate",
    "25",

    "-i",
    str(INPUT),

    # Generate continuous presentation timestamps.
    "-fflags",
    "+genpts",

    # Clean H.264 re-encode.
    "-c:v",
    "libx264",

    # Reasonable quality for forensic playback copy.
    "-crf",
    "18",

    # Compatibility / stable playback.
    "-preset",
    "medium",

    "-pix_fmt",
    "yuv420p",

    "-profile:v",
    "high",

    "-level",
    "4.2",

    # Force a keyframe regularly for smooth seeking.
    "-g",
    "50",

    "-keyint_min",
    "50",

    "-sc_threshold",
    "0",

    # MP4 container.
    "-movflags",
    "+faststart",

    str(OUTPUT),
]


print("Running FFmpeg...")
print()


result = subprocess.run(
    command,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)


# ============================================================
# RESULT
# ============================================================

if result.returncode != 0 or not OUTPUT.exists():

    print("❌ Video optimization failed.")
    print()
    print(result.stderr)
    sys.exit(1)


print("✅ Playback optimization completed.")
print()
print("=" * 70)

print("OPTIMIZED VIDEO")
print("-" * 70)

print(f"Output:      {OUTPUT}")
print(f"Output size: {OUTPUT.stat().st_size:,} bytes")

print()
print("Original forensic artifacts were NOT modified.")
print()
print("=" * 70)
print("CINE-X PLAYBACK OPTIMIZATION COMPLETE")
print("=" * 70)