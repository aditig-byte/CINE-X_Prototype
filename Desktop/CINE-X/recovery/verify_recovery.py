from pathlib import Path
import subprocess
import re


FFMPEG = Path(
    r"C:\Users\Aditi Gupta\Downloads\ffmpeg-9.0.1-essentials_build"
    r"\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
)
INPUT = Path("recovered/cine_x_recovered_fixed.mp4")


print()
print("CINE-X RECOVERY VERIFICATION")
print("=" * 70)

print(f"Input: {INPUT}")
print()

if not INPUT.exists():

    print("❌ Recovered video does not exist.")

    raise SystemExit(1)


print("Running FFmpeg validation...")
print()

result = subprocess.run(
    [
        str(FFMPEG),
        "-hide_banner",
        "-i",
        str(INPUT),
        "-f",
        "null",
        "NUL"
    ],
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True
)


log = result.stderr


# ============================================================
# EXTRACT VIDEO INFORMATION
# ============================================================

resolution = None
fps = None
duration = None
frames = None


match = re.search(
    r"Video:.*?(\d{3,5})x(\d{3,5})",
    log
)

if match:

    resolution = (
        f"{match.group(1)}x{match.group(2)}"
    )


match = re.search(
    r"Duration:\s*(\d+:\d+:\d+\.\d+)",
    log
)

if match:

    duration = match.group(1)


match = re.search(
    r"(\d+(?:\.\d+)?) fps",
    log
)

if match:

    fps = match.group(1)


# ============================================================
# LOOK FOR DECODER ERRORS
# ============================================================

errors = []

for line in log.splitlines():

    lower = line.lower()

    if any(
        term in lower
        for term in [
            "error while decoding",
            "corrupt decoded frame",
            "concealing",
            "invalid data",
            "error"
        ]
    ):

        errors.append(
            line.strip()
        )


# ============================================================
# DISPLAY RESULTS
# ============================================================

print("RECOVERED VIDEO INFORMATION")
print("-" * 70)

print(
    f"File size:       "
    f"{INPUT.stat().st_size:,} bytes"
)

print(
    f"Resolution:      "
    f"{resolution or 'Detected by FFmpeg'}"
)

print(
    f"Frame rate:      "
    f"{fps or 'Detected by FFmpeg'}"
)

print(
    f"Duration:        "
    f"{duration or 'Detected by FFmpeg'}"
)

print()

print("DECODER VALIDATION")
print("-" * 70)

if result.returncode == 0 and not errors:

    print(
        "✅ FFmpeg decoded the recovered video successfully."
    )

    print(
        "✅ No corruption-related decoder errors detected."
    )

    print()

    print("=" * 70)
    print("RECOVERY VERIFICATION: PASSED")
    print("=" * 70)

else:

    print(
        "⚠ Decoder reported issues."
    )

    print()

    for error in errors:

        print(
            "⚠",
            error
        )

    print()

    print("=" * 70)
    print("RECOVERY VERIFICATION: REVIEW REQUIRED")
    print("=" * 70)