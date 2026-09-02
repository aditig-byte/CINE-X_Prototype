from pathlib import Path
import subprocess


# ============================================================
# CINE-X — AUTOMATIC RECOVERY ENGINE
# ============================================================

FFMPEG = Path(
    r"C:\Users\Aditi Gupta\Downloads\ffmpeg-9.0.1-essentials_build"
    r"\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
)

INPUT = Path("damaged/cam1_damaged.h264")
OUTPUT_H264 = Path("recovered/cine_x_recovered.h264")
OUTPUT_MP4 = Path("recovered/cine_x_recovered.mp4")


# ============================================================
# H.264 NAL SCANNER
# ============================================================

def find_nals(data):

    start_codes = []

    i = 0

    while i < len(data) - 3:

        if data[i:i + 4] == b"\x00\x00\x00\x01":

            start_codes.append((i, 4))
            i += 4

        elif data[i:i + 3] == b"\x00\x00\x01":

            start_codes.append((i, 3))
            i += 3

        else:

            i += 1

    nals = []

    for index, (start, code_length) in enumerate(start_codes):

        header = start + code_length

        if header >= len(data):
            continue

        if index + 1 < len(start_codes):

            end = start_codes[index + 1][0]

        else:

            end = len(data)

        nal_type = data[header] & 0x1F

        nals.append(
            {
                "start": start,
                "end": end,
                "type": nal_type,
                "data": data[start:end]
            }
        )

    return nals


# ============================================================
# FIND CLEAN IDR AFTER CORRUPTION
# ============================================================

def find_recovery_idr(nals, damage_start):

    for nal in nals:

        if (
            nal["type"] == 5
            and nal["start"] > damage_start
        ):

            return nal

    return None


# ============================================================
# FIND SPS / PPS
# ============================================================

def find_codec_headers(nals, recovery_start):

    sps = None
    pps = None

    for nal in nals:

        if nal["start"] >= recovery_start:
            break

        if nal["type"] == 7:

            sps = nal["data"]

        elif nal["type"] == 8:

            pps = nal["data"]

    return sps, pps


# ============================================================
# CONVERT H.264 → MP4
# ============================================================

def create_mp4():

    result = subprocess.run(
        [
            str(FFMPEG),
            "-y",
            "-framerate",
            "25",
            "-f",
            "h264",
            "-i",
            str(OUTPUT_H264),
            "-c:v",
            "copy",
            str(OUTPUT_MP4)
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:

        print(result.stderr)

        raise RuntimeError(
            "FFmpeg failed to create recovered MP4."
        )


# ============================================================
# MAIN RECOVERY
# ============================================================

def recover():

    print()
    print("CINE-X AUTOMATIC RECOVERY ENGINE")
    print("=" * 70)

    data = INPUT.read_bytes()

    print(
        f"Input file:       {INPUT}"
    )

    print(
        f"Input size:       {len(data):,} bytes"
    )

    print()

    # Controlled prototype corruption location.
    damage_start = 6_085_197

    print(
        f"Known corruption: {damage_start:,}"
    )

    print()

    nals = find_nals(data)

    print(
        f"NAL units found:  {len(nals):,}"
    )

    print()

    # --------------------------------------------------------
    # Find next clean IDR
    # --------------------------------------------------------

    recovery_idr = find_recovery_idr(
        nals,
        damage_start
    )

    if recovery_idr is None:

        raise RuntimeError(
            "No clean IDR frame found after corruption."
        )

    print("RECOVERY ANCHOR")
    print("-" * 70)

    print(
        f"IDR start:        "
        f"{recovery_idr['start']:,}"
    )

    print(
        f"IDR end:          "
        f"{recovery_idr['end']:,}"
    )

    print(
        "Status:            CLEAN IDR FOUND"
    )

    print()

    # --------------------------------------------------------
    # Find SPS/PPS
    # --------------------------------------------------------

    sps, pps = find_codec_headers(
        nals,
        recovery_idr["start"]
    )

    if sps is None:

        raise RuntimeError(
            "SPS header could not be found."
        )

    if pps is None:

        raise RuntimeError(
            "PPS header could not be found."
        )

    print("CODEC HEADERS")
    print("-" * 70)

    print("SPS:              FOUND")
    print("PPS:              FOUND")

    print()

    # --------------------------------------------------------
    # Build recovered stream
    # --------------------------------------------------------

    recovery_data = data[
        recovery_idr["start"] :
    ]

    OUTPUT_H264.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    with OUTPUT_H264.open("wb") as f:

        f.write(sps)
        f.write(pps)
        f.write(recovery_data)

    print("RECOVERED H.264")
    print("-" * 70)

    print(
        f"Output:           {OUTPUT_H264}"
    )

    print(
        f"Output size:      "
        f"{OUTPUT_H264.stat().st_size:,} bytes"
    )

    print()

    # --------------------------------------------------------
    # Create playable MP4
    # --------------------------------------------------------

    print("CREATING PLAYABLE VIDEO")
    print("-" * 70)

    create_mp4()

    print(
        f"Output:           {OUTPUT_MP4}"
    )

    print(
        f"Output size:      "
        f"{OUTPUT_MP4.stat().st_size:,} bytes"
    )

    print()

    print("=" * 70)

    print(
        "✅ RECOVERY COMPLETE"
    )

    print(
        "CINE-X selected a clean IDR after the "
        "corrupted region and reconstructed a "
        "playable video stream."
    )

    print("=" * 70)


if __name__ == "__main__":

    recover()