from pathlib import Path
import re
import subprocess


# ============================================================
# CINE-X — DAMAGE LOCALIZATION
# ============================================================

FFMPEG = Path(
    r"C:\Users\Aditi Gupta\Downloads\ffmpeg-9.0.1-essentials_build"
    r"\ffmpeg-9.0.1-essentials_build\bin\ffmpeg.exe"
)

INPUT = Path("damaged/cam1_damaged.h264")

# Controlled corruption ground truth used for this prototype.
# These values come from damage_h264.py.
DAMAGE_START = 6_085_197
DAMAGE_SIZE = 100
DAMAGE_END = DAMAGE_START + DAMAGE_SIZE


# ============================================================
# NAL UNIT DETECTION
# ============================================================

def find_nal_units(data):

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

        header_position = start + code_length

        if header_position >= len(data):
            continue

        if index + 1 < len(start_codes):

            end = start_codes[index + 1][0]

        else:

            end = len(data)

        nal_header = data[header_position]

        nal_type = nal_header & 0x1F

        nals.append(
            {
                "start": start,
                "end": end,
                "size": end - start,
                "type": nal_type
            }
        )

    return nals


# ============================================================
# NAL NAME
# ============================================================

def get_nal_name(nal_type):

    names = {
        1: "P-frame / Non-IDR picture",
        5: "IDR frame",
        6: "SEI",
        7: "SPS",
        8: "PPS"
    }

    return names.get(
        nal_type,
        f"Other ({nal_type})"
    )


# ============================================================
# FIND NAL CONTAINING CORRUPTION
# ============================================================

def find_containing_nal(nals):

    for index, nal in enumerate(nals):

        # Damage range overlaps this NAL.
        if (
            DAMAGE_START < nal["end"]
            and DAMAGE_END > nal["start"]
        ):

            return index, nal

    return None, None


# ============================================================
# FIND PREVIOUS IDR
# ============================================================

def find_previous_idr(nals, affected_index):

    previous_idr = None

    for index in range(affected_index):

        if nals[index]["type"] == 5:

            previous_idr = nals[index]

    return previous_idr


# ============================================================
# FIND NEXT IDR
# ============================================================

def find_next_idr(nals, affected_index):

    for index in range(
        affected_index + 1,
        len(nals)
    ):

        if nals[index]["type"] == 5:

            return nals[index]

    return None


# ============================================================
# FFmpeg CORRUPTION CHECK
# ============================================================

def check_decoder_corruption():

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

    messages = []

    for line in log.splitlines():

        lower = line.lower()

        if any(
            term in lower
            for term in [
                "error while decoding",
                "corrupt decoded frame",
                "concealing",
                "reference"
            ]
        ):

            messages.append(
                line.strip()
            )

    macroblocks = []

    for line in log.splitlines():

        match = re.search(
            r"error while decoding MB\s+(\d+)\s+(\d+)",
            line,
            re.IGNORECASE
        )

        if match:

            macroblocks.append(
                {
                    "x": int(match.group(1)),
                    "y": int(match.group(2))
                }
            )

    return messages, macroblocks


# ============================================================
# MAIN LOCALIZATION FUNCTION
# ============================================================

def localize_corruption(input_file=INPUT):

    input_file = Path(input_file)

    data = input_file.read_bytes()

    nals = find_nal_units(data)

    affected_index, affected_nal = find_containing_nal(
        nals
    )

    previous_idr = None
    next_idr = None

    if affected_nal is not None:

        previous_idr = find_previous_idr(
            nals,
            affected_index
        )

        next_idr = find_next_idr(
            nals,
            affected_index
        )

    decoder_messages, macroblocks = (
        check_decoder_corruption()
    )

    return {
        "file_size": len(data),
        "total_nals": len(nals),
        "affected_index": affected_index,
        "affected_nal": affected_nal,
        "previous_idr": previous_idr,
        "next_idr": next_idr,
        "decoder_messages": decoder_messages,
        "macroblocks": macroblocks,
        "corruption_start": DAMAGE_START,
        "corruption_end": DAMAGE_END - 1,
        "corruption_size": DAMAGE_SIZE
    }


# ============================================================
# TERMINAL DISPLAY
# ============================================================

if __name__ == "__main__":

    print()
    print("CINE-X DAMAGE LOCALIZATION")
    print("=" * 70)

    print(
        f"Input: {INPUT}"
    )

    print()

    result = localize_corruption()

    print("BITSTREAM INFORMATION")
    print("-" * 70)

    print(
        f"File size:       "
        f"{result['file_size']:,} bytes"
    )

    print(
        f"NAL units:       "
        f"{result['total_nals']:,}"
    )

    print()

    print("CORRUPTION GROUND TRUTH")
    print("-" * 70)

    print(
        f"Damage start:    "
        f"{result['corruption_start']:,}"
    )

    print(
        f"Damage end:      "
        f"{result['corruption_end']:,}"
    )

    print(
        f"Damaged bytes:   "
        f"{result['corruption_size']}"
    )

    print()

    if result["decoder_messages"]:

        print("DECODER EVIDENCE")
        print("-" * 70)

        for message in result[
            "decoder_messages"
        ]:

            print(
                "⚠",
                message
            )

        print()

    if result["macroblocks"]:

        print("DAMAGED MACROBLOCK")
        print("-" * 70)

        for mb in result["macroblocks"]:

            print(
                f"X coordinate: {mb['x']}"
            )

            print(
                f"Y coordinate: {mb['y']}"
            )

        print()

    if result["affected_nal"]:

        nal = result["affected_nal"]

        print("AFFECTED NAL UNIT")
        print("-" * 70)

        print(
            f"NAL number:     "
            f"{result['affected_index'] + 1}"
        )

        print(
            f"NAL type:       "
            f"{nal['type']}"
        )

        print(
            f"Meaning:        "
            f"{get_nal_name(nal['type'])}"
        )

        print(
            f"NAL start:      "
            f"{nal['start']:,}"
        )

        print(
            f"NAL end:        "
            f"{nal['end']:,}"
        )

        print(
            f"NAL size:       "
            f"{nal['size']:,} bytes"
        )

        print()

        print(
            f"Damage begins "
            f"{max(0, result['corruption_start'] - nal['start']):,} "
            f"bytes into this NAL."
        )

    else:

        print(
            "❌ Could not map the corruption "
            "range to an H.264 NAL unit."
        )

    print()

    if result["previous_idr"]:

        idr = result["previous_idr"]

        print("PREVIOUS VALID IDR")
        print("-" * 70)

        print(
            f"Start byte:      "
            f"{idr['start']:,}"
        )

        print(
            f"End byte:        "
            f"{idr['end']:,}"
        )

        print(
            "This IDR is a candidate "
            "recovery anchor."
        )

    else:

        print(
            "⚠ No previous IDR found."
        )

    print()

    if result["next_idr"]:

        idr = result["next_idr"]

        print("NEXT IDR")
        print("-" * 70)

        print(
            f"Start byte:      "
            f"{idr['start']:,}"
        )

        print(
            f"End byte:        "
            f"{idr['end']:,}"
        )

    print()

    print("=" * 70)
    print("LOCALIZATION STATUS")
    print("=" * 70)

    if (
        result["affected_nal"]
        and result["previous_idr"]
    ):

        print(
            "✅ DAMAGE LOCALIZED"
        )

        print(
            "Recovery anchor identified."
        )

    else:

        print(
            "⚠ LOCALIZATION INCOMPLETE"
        )

    print()