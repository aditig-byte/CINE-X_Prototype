from pathlib import Path
import json


INPUT_FILE = Path("../Data/Original/cam01.h264")
OUTPUT_FILE = Path("../Data/Damaged/cam01_severely_damaged.h264")
REPORT_FILE = Path("../Data/Damaged/severe_damage_report.json")

START_NAL = 100
NUMBER_OF_NALS = 20

DAMAGE_RATIO = 0.70


def find_nals(data):

    positions = []

    i = 0

    while i < len(data) - 4:

        if data[i:i + 4] == b"\x00\x00\x00\x01":
            positions.append((i, 4))
            i += 4

        elif data[i:i + 3] == b"\x00\x00\x01":
            positions.append((i, 3))
            i += 3

        else:
            i += 1

    return positions


def main():

    print("Loading original H.264...")

    data = bytearray(INPUT_FILE.read_bytes())

    print("File size:", len(data), "bytes")

    nals = find_nals(data)

    print("NAL units found:", len(nals))

    start_index = START_NAL - 1
    end_index = start_index + NUMBER_OF_NALS

    if end_index >= len(nals):

        print("ERROR: Not enough NAL units.")

        return

    damage_start = None
    damage_end = None

    damaged_nals = []

    damaged = bytearray(data)

    for index in range(start_index, end_index):

        start, start_code_length = nals[index]

        if index + 1 < len(nals):

            end = nals[index + 1][0]

        else:

            end = len(data)

        header_position = start + start_code_length

        nal_type = data[header_position] & 0x1F

        payload_start = header_position + 1

        payload_size = end - payload_start

        if payload_size <= 10:
            continue

        # Keep the beginning and end of each NAL intact.
        corrupt_size = int(payload_size * DAMAGE_RATIO)

        corrupt_start = payload_start + int(payload_size * 0.15)

        corrupt_end = min(
            corrupt_start + corrupt_size,
            end
        )

        for i in range(corrupt_start, corrupt_end):

            damaged[i] = 0xFF

        if damage_start is None:
            damage_start = corrupt_start

        damage_end = corrupt_end

        damaged_nals.append({
            "nal_number": index + 1,
            "nal_type": nal_type,
            "start": start,
            "end": end,
            "corrupt_start": corrupt_start,
            "corrupt_end": corrupt_end,
            "corrupt_bytes": corrupt_end - corrupt_start
        })

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_FILE.write_bytes(damaged)

    report = {
        "original_file": str(INPUT_FILE),
        "damaged_file": str(OUTPUT_FILE),
        "start_nal": START_NAL,
        "number_of_nals": NUMBER_OF_NALS,
        "damage_ratio": DAMAGE_RATIO,
        "damage_start": damage_start,
        "damage_end": damage_end,
        "damaged_nals": damaged_nals
    }

    REPORT_FILE.write_text(
        json.dumps(report, indent=4)
    )

    print()
    print("================================")
    print("SEVERE DAMAGE CREATED")
    print("================================")

    print("NAL range:",
          START_NAL,
          "to",
          START_NAL + NUMBER_OF_NALS - 1)

    print("Damage ratio:",
          DAMAGE_RATIO * 100,
          "%")

    print("Damaged NALs:",
          len(damaged_nals))

    print("Damage range:",
          damage_start,
          "→",
          damage_end)

    print()

    print("Damaged file:")
    print(OUTPUT_FILE)

    print()

    print("Ground truth:")
    print(REPORT_FILE)


if __name__ == "__main__":
    main()