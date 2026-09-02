import subprocess
from pathlib import Path

FFMPEG = Path(
    r"C:\Users\Aditi Gupta\Downloads\ffmpeg-9.0.1-essentials_build"
    r"\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
)


def detect_corruption(input_file):

    input_file = Path(input_file)

    result = subprocess.run(
        [
            str(FFMPEG),
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

    errors = []

    for line in log.splitlines():

        if any(word in line.lower() for word in [
            "error while decoding",
            "corrupt decoded frame",
            "reference",
            "concealing"
        ]):

            errors.append(line.strip())

    return errors