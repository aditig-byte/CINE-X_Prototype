from pathlib import Path


INPUT_FILE = Path("Data/Damaged/cam01_severely_damaged.h264")


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

    print("File:", INPUT_FILE)
    print("File size:", len(data), "bytes")
    print("Total NAL units:", len(nals))
    print()

    idr_count = 0

    print("IDR RECOVERY POINTS")
    print("===================")

    for index, (start, start_length) in enumerate(nals):

        header_position = start + start_length

        if header_position >= len(data):
            continue

        nal_type = data[header_position] & 0x1F

        if nal_type == 5:

            idr_count += 1

            print(
                f"IDR #{idr_count:3} | "
                f"NAL #{index + 1:3} | "
                f"offset {start}"
            )

    print()
    print("Total IDR frames:", idr_count)


if __name__ == "__main__":
    main()