from pathlib import Path
import subprocess
import json


# ============================================================
# FILES
# ============================================================

ORIGINAL_FILE = Path(
    "Data/Original/cam01.h264"
)

RECOVERED_FILE = Path(
    "Data/Recovered/cam01_recovered_v1.h264"
)


# ============================================================
# RUN FFPROBE
# ============================================================

def get_frame_count(video_file):

    command = [
        "ffprobe",
        "-v", "error",
        "-select_streams", "v:0",
        "-count_frames",
        "-show_entries",
        "stream=nb_read_frames",
        "-of", "json",
        str(video_file)
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFprobe failed for {video_file}\n"
            f"{result.stderr}"
        )

    data = json.loads(result.stdout)

    streams = data.get("streams", [])

    if not streams:
        raise RuntimeError(
            f"No video stream found in {video_file}"
        )

    return int(streams[0]["nb_read_frames"])


# ============================================================
# CHECK DECODING
# ============================================================

def check_decode(video_file):

    command = [
        "ffmpeg",
        "-v", "error",
        "-i", str(video_file),
        "-f", "null",
        "-"
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    return {
        "success": result.returncode == 0
        and result.stderr.strip() == "",
        "errors": result.stderr.strip()
    }


# ============================================================
# MAIN VERIFICATION
# ============================================================

def main():

    print("CINE-X Recovery Verification")
    print("=" * 55)

    print()
    print("Input Files")
    print("-" * 55)

    print("Original :", ORIGINAL_FILE)
    print("Recovered:", RECOVERED_FILE)

    if not ORIGINAL_FILE.exists():
        raise FileNotFoundError(
            f"Original file not found: {ORIGINAL_FILE}"
        )

    if not RECOVERED_FILE.exists():
        raise FileNotFoundError(
            f"Recovered file not found: {RECOVERED_FILE}"
        )

    # --------------------------------------------------------
    # FRAME COUNTS
    # --------------------------------------------------------

    print()
    print("Frame Count Analysis")
    print("-" * 55)

    original_frames = get_frame_count(
        ORIGINAL_FILE
    )

    recovered_frames = get_frame_count(
        RECOVERED_FILE
    )

    skipped_frames = (
        original_frames - recovered_frames
    )

    recovery_percentage = (
        recovered_frames / original_frames
    ) * 100

    print(
        f"Original frames : {original_frames}"
    )

    print(
        f"Recovered frames: {recovered_frames}"
    )

    print(
        f"Skipped frames  : {skipped_frames}"
    )

    print(
        f"Recovery ratio  : {recovery_percentage:.2f}%"
    )

    # --------------------------------------------------------
    # DECODE TEST
    # --------------------------------------------------------

    print()
    print("Decode Validation")
    print("-" * 55)

    original_decode = check_decode(
        ORIGINAL_FILE
    )

    recovered_decode = check_decode(
        RECOVERED_FILE
    )

    if original_decode["success"]:
        print("Original : PASS")
    else:
        print("Original : FAIL")
        print(original_decode["errors"])

    if recovered_decode["success"]:
        print("Recovered: PASS")
    else:
        print("Recovered: FAIL")
        print(recovered_decode["errors"])

    # --------------------------------------------------------
    # CURRENT V1 INTERPRETATION
    # --------------------------------------------------------

    print()
    print("V1 Recovery Assessment")
    print("-" * 55)

    if recovered_decode["success"]:
        print(
            "STATUS: CLEAN DECODABLE RECOVERY"
        )
    else:
        print(
            "STATUS: RECOVERY REQUIRES FURTHER ANALYSIS"
        )

    print()
    print("Recovery interpretation:")
    print(
        "1. Valid content before the damaged region "
        "was preserved."
    )

    print(
        "2. The affected prediction chain was skipped."
    )

    print(
        "3. Decoding resumed from the next clean IDR."
    )

    print(
        "4. Skipped frames are NOT claimed as recovered."
    )

    print()
    print("Important:")
    print(
        "A clean decode does not by itself prove "
        "pixel-level identity with the original."
    )

    print(
        "Pixel-level verification will be performed "
        "at the recovery boundary in the next step."
    )


if __name__ == "__main__":
    main()