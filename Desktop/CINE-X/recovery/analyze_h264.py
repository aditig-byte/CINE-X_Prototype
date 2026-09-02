from pathlib import Path


NAMES = {
    1: "Non-IDR picture",
    5: "IDR picture",
    6: "SEI",
    7: "SPS",
    8: "PPS",
}


def analyze_h264(input_file):

    input_file = Path(input_file)

    data = input_file.read_bytes()

    start_codes = []
    i = 0

    while i < len(data) - 4:

        if data[i:i+4] == b"\x00\x00\x00\x01":
            start_codes.append((i, 4))
            i += 4

        elif data[i:i+3] == b"\x00\x00\x01":
            start_codes.append((i, 3))
            i += 3

        else:
            i += 1

    counts = {}

    for pos, code_length in start_codes:

        header_pos = pos + code_length

        if header_pos >= len(data):
            continue

        nal_header = data[header_pos]

        nal_type = nal_header & 0x1F

        counts[nal_type] = counts.get(nal_type, 0) + 1

    return {
        "file": input_file.name,
        "size": len(data),
        "start_codes": len(start_codes),
        "nal_counts": counts,
        "sps": counts.get(7, 0),
        "pps": counts.get(8, 0),
        "idr": counts.get(5, 0),
        "p_frames": counts.get(1, 0),
        "sei": counts.get(6, 0),
    }


if __name__ == "__main__":

    result = analyze_h264("original/cam1.h264")

    print("CINE-X H.264 Analyzer")
    print("=" * 60)

    print(f"File: {result['file']}")
    print(f"Size: {result['size']:,} bytes")
    print(f"Start codes: {result['start_codes']:,}")

    print()
    print("NAL Summary")
    print("-" * 60)

    for nal_type, count in sorted(result["nal_counts"].items()):

        name = NAMES.get(nal_type, "Other")

        print(
            f"Type {nal_type:2} | "
            f"{name:20} | "
            f"{count:,}"
        )