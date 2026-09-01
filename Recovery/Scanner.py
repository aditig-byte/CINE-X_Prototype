START_CODES = [
    b"\x00\x00\x00\x01",
    b"\x00\x00\x01"
]

NAL_TYPES = {
    1: "P-frame",
    5: "IDR frame",
    7: "SPS",
    8: "PPS"
}


def find_nals(data):
    positions = []

    i = 0

    while i < len(data) - 4:

        if data[i:i+4] == START_CODES[0]:
            positions.append((i, 4))
            i += 4

        elif data[i:i+3] == START_CODES[1]:
            positions.append((i, 3))
            i += 3

        else:
            i += 1

    return positions


def main():

    file_path = r"..\Data\Original\cam01.h264"

    with open(file_path, "rb") as f:
        data = f.read()

    print("File size:", len(data), "bytes")

    nals = find_nals(data)

    print("NAL units found:", len(nals))
    print()

    for number, (position, start_length) in enumerate(nals[:50], start=1):

        header_position = position + start_length

        if header_position >= len(data):
            continue

        header = data[header_position]

        nal_type = header & 0x1F

        name = NAL_TYPES.get(
            nal_type,
            f"Other ({nal_type})"
        )

        print(
            f"NAL {number:3} | "
            f"offset {position:10} | "
            f"type {nal_type:2} | "
            f"{name}"
        )


if __name__ == "__main__":
    main()