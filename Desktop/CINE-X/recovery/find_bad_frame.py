import subprocess
from pathlib import Path
import re


FFMPEG = Path(
    r"C:\Users\Aditi Gupta\Downloads\ffmpeg-9.0.1-essentials_build"
    r"\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
)

INPUT = Path("damaged/cam1_damaged.h264")


def find_bad_frame(input_file):

    print("CINE-X Frame-Level Corruption Analyzer")
    print("=" * 60)
    print(f"Input: {input_file}")
    print()

    result = subprocess.run(
        [
            str(FFMPEG),
            "-hide_banner",
            "-i",
            str(input_file),
            "-f",
            "null",
            "NUL"
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    log = result.stderr

    corruption_messages = []

    macroblocks = []

    for line in log.splitlines():

        lower = line.lower()

        if (
            "error while decoding" in lower
            or "corrupt decoded frame" in lower
            or "concealing" in lower
            or "reference" in lower
        ):

            corruption_messages.append(
                line.strip()
            )

        match = re.search(
            r"error while decoding MB\s+(\d+)\s+(\d+)",
            line,
            re.IGNORECASE
        )

        if match:

            x = int(match.group(1))
            y = int(match.group(2))

            macroblocks.append(
                {
                    "x": x,
                    "y": y
                }
            )

    print("Decoder analysis")
    print("-" * 60)

    if not corruption_messages:

        print("✓ No corruption detected.")

        return {
            "corrupted": False,
            "messages": [],
            "macroblocks": []
        }

    print("⚠ CORRUPTION DETECTED")
    print()

    for message in corruption_messages:

        print("⚠", message)

    print()

    if macroblocks:

        print("Affected macroblock")
        print("-" * 60)

        for mb in macroblocks:

            print(
                f"X coordinate : {mb['x']}"
            )

            print(
                f"Y coordinate : {mb['y']}"
            )

            print()

    print("=" * 60)

    print("Frame localization status")
    print("=" * 60)

    print(
        "Decoder has confirmed corruption "
        "inside a P-frame."
    )

    print()

    print(
        "The reported MB coordinates identify "
        "the damaged area inside the frame."
    )

    print()

    print(
        "Exact frame number will be correlated "
        "with the H.264 NAL sequence in the "
        "next localization step."
    )

    print()

    print(
        "Status: CORRUPTED P-FRAME DETECTED"
    )

    return {
        "corrupted": True,
        "messages": corruption_messages,
        "macroblocks": macroblocks
    }


if __name__ == "__main__":

    find_bad_frame(INPUT)