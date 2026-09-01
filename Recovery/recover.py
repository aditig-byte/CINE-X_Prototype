from pathlib import Path


INPUT_FILE = Path("../Data/Damaged/cam01_severely_damaged.h264")
OUTPUT_FILE = Path("../Data/Recovered/cam01_recovered.h264")


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

    data = INPUT_FILE.read_bytes()

    nals = find_nals(data)

    print("Total NALs:", len(nals))

    # --------------------------------------------
    # Find SPS, PPS and IDR positions
    # --------------------------------------------

    sps_position = None
    pps_position = None
    idr_positions = []

    for index, (start, start_length) in enumerate(nals):

        header_position = start + start_length

        if header_position >= len(data):
            continue

        nal_type = data[header_position] & 0x1F

        if nal_type == 7 and sps_position is None:
            sps_position = start

        elif nal_type == 8 and pps_position is None:
            pps_position = start

        elif nal_type == 5:
            idr_positions.append(start)

    print("SPS:", sps_position)
    print("PPS:", pps_position)
    print("IDR count:", len(idr_positions))

    if sps_position is None:
        print("ERROR: SPS not found.")
        return

    if pps_position is None:
        print("ERROR: PPS not found.")
        return

    if len(idr_positions) < 1:
        print("ERROR: No IDR found.")
        return

    # --------------------------------------------
    # Start recovery from SPS
    # --------------------------------------------

    recovery_start = sps_position

    # Start at the first IDR
    recovery_idr = idr_positions[0]

    # Find the next IDR after the first one
    recovery_end = None

    for position in idr_positions:

        if position > recovery_idr:
            recovery_end = position
            break

    if recovery_end is None:
        recovery_end = len(data)

    # --------------------------------------------
    # Extract:
    #
    # SPS
    # PPS
    # IDR
    # following frames
    # --------------------------------------------

    recovered = data[recovery_start:recovery_end]

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    OUTPUT_FILE.write_bytes(recovered)

    print()
    print("================================")
    print("RECOVERY COMPLETE")
    print("================================")

    print("Recovery start:", recovery_start)
    print("First IDR:", recovery_idr)
    print("Recovery end:", recovery_end)
    print("Recovered bytes:", len(recovered))

    print()
    print("Output:")
    print(OUTPUT_FILE)


if __name__ == "__main__":
    main()