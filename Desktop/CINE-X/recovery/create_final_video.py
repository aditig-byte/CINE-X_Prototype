from pathlib import Path
import subprocess
import sys


# ============================================================
# CINE-X — FINAL VIDEO ASSEMBLER
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

FFMPEG = Path(
    r"C:\Users\Aditi Gupta\Downloads\ffmpeg-9.0.1-essentials_build"
    r"\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
)

SOURCE_H264 = BASE_DIR / "original" / "cam1.h264"

RECOVERED_MP4 = (
    BASE_DIR
    / "recovered"
    / "cine_x_recovered_fixed.mp4"
)

OUTPUT = (
    BASE_DIR
    / "recovered"
    / "cine_x_final.mp4"
)

TEMP_GOOD = BASE_DIR / "temp" / "good_before_damage.mp4"


# ============================================================
# SETTINGS
# ============================================================

# Damage begins at byte 6,085,197.
# The corrupted NAL ends at byte 6,092,388.
#
# We use the previous clean IDR as the beginning of the
# preserved section and the next IDR as the recovery point.

PREVIOUS_IDR = 4_012_886
RECOVERY_IDR = 8_157_508

FPS = 25


# ============================================================
# HEADER
# ============================================================

print()
print("CINE-X FINAL VIDEO ASSEMBLER")
print("=" * 70)

print(f"Original H.264:  {SOURCE_H264}")
print(f"Recovered MP4:   {RECOVERED_MP4}")
print(f"Final output:    {OUTPUT}")
print()


# ============================================================
# CHECK FILES
# ============================================================

if not FFMPEG.exists():

    print("❌ FFmpeg not found.")
    print(FFMPEG)
    sys.exit(1)


if not SOURCE_H264.exists():

    print("❌ Original H.264 does not exist.")
    print(SOURCE_H264)
    sys.exit(1)


if not RECOVERED_MP4.exists():

    print("❌ Recovered fixed video does not exist.")
    print(RECOVERED_MP4)
    sys.exit(1)


# ============================================================
# READ ORIGINAL BITSTREAM
# ============================================================

data = SOURCE_H264.read_bytes()

print(f"Original size: {len(data):,} bytes")
print()


# ============================================================
# CREATE CLEAN SECTION BEFORE CORRUPTION
# ============================================================

print("Creating preserved footage before corruption...")

good_segment = data[:PREVIOUS_IDR]

TEMP_GOOD.parent.mkdir(exist_ok=True)

TEMP_H264 = BASE_DIR / "temp" / "good_before_damage.h264"

TEMP_H264.write_bytes(good_segment)


# ============================================================
# CONVERT GOOD SECTION TO MP4
# ============================================================

print("Converting preserved footage...")

result = subprocess.run(
    [
        str(FFMPEG),
        "-y",
        "-f",
        "h264",
        "-framerate",
        str(FPS),
        "-i",
        str(TEMP_H264),
        "-c:v",
        "libx264",
        "-crf",
        "18",
        "-preset",
        "medium",
        "-pix_fmt",
        "yuv420p",
        "-profile:v",
        "high",
        "-movflags",
        "+faststart",
        str(TEMP_GOOD),
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)


if result.returncode != 0 or not TEMP_GOOD.exists():

    print("❌ Could not create preserved video section.")
    print(result.stderr)
    sys.exit(1)


# ============================================================
# CREATE CONCAT LIST
# ============================================================

CONCAT_FILE = BASE_DIR / "temp" / "final_concat.txt"

def ffconcat_path(path):
    return str(path.resolve()).replace("\\", "/").replace("'", "'\\''")


CONCAT_FILE.write_text(
    "ffconcat version 1.0\n"
    f"file '{ffconcat_path(TEMP_GOOD)}'\n"
    f"file '{ffconcat_path(RECOVERED_MP4)}'\n",
    encoding="utf-8",
)


# ============================================================
# JOIN
# ============================================================

print()
print("Joining preserved footage + recovered footage...")
print()

OUTPUT.parent.mkdir(exist_ok=True)

result = subprocess.run(
    [
        str(FFMPEG),
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(CONCAT_FILE),
        "-c",
        "copy",
        "-movflags",
        "+faststart",
        str(OUTPUT),
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
)


# ============================================================
# RESULT
# ============================================================

if result.returncode != 0 or not OUTPUT.exists():

    print("❌ Final video creation failed.")
    print()
    print(result.stderr)
    sys.exit(1)


print("=" * 70)
print("✅ FINAL VIDEO CREATED")
print("=" * 70)

print()
print(f"Output: {OUTPUT}")
print(f"Size:   {OUTPUT.stat().st_size:,} bytes")

print()
print("Final video structure:")
print()
print("GOOD FOOTAGE")
print("     ↓")
print("CORRUPTED SECTION SKIPPED")
print("     ↓")
print("RECOVERED FOOTAGE")
print("     ↓")
print("FINAL CINE-X VIDEO")

print()
print("=" * 70)
print("CINE-X FINAL VIDEO ASSEMBLY COMPLETE")
print("=" * 70)