from pathlib import Path

INPUT = Path("damaged/cam1_damaged.h264")
OUTPUT = Path("recovered/recovered_from_idr3.h264")

IDR3_OFFSET = 8_157_508

data = INPUT.read_bytes()

# Find NAL start codes
start_codes = []

i = 0
while i < len(data) - 3:
    if data[i:i+4] == b'\x00\x00\x00\x01':
        start_codes.append(i)
        i += 4
    elif data[i:i+3] == b'\x00\x00\x01':
        start_codes.append(i)
        i += 3
    else:
        i += 1

# Collect the last SPS and PPS before IDR #3
sps = None
pps = None

for pos in start_codes:
    if pos >= IDR3_OFFSET:
        break

    if data[pos:pos+4] == b'\x00\x00\x00\x01':
        header = pos + 4
    else:
        header = pos + 3

    nal_type = data[header] & 0x1F

    next_positions = [p for p in start_codes if p > pos]

    end = next_positions[0] if next_positions else len(data)

    nal = data[pos:end]

    if nal_type == 7:
        sps = nal

    elif nal_type == 8:
        pps = nal

if sps is None or pps is None:
    raise RuntimeError("Could not find SPS/PPS before IDR #3")

# Start exactly from IDR #3
recovery_data = data[IDR3_OFFSET:]

OUTPUT.parent.mkdir(exist_ok=True)

with OUTPUT.open("wb") as f:
    f.write(sps)
    f.write(pps)
    f.write(recovery_data)

print("CINE-X Recovery Engine")
print("=" * 60)
print("Recovery point: IDR #3")
print(f"IDR offset:     {IDR3_OFFSET:,}")
print("SPS:            included")
print("PPS:            included")
print(f"Output:         {OUTPUT}")
print(f"Output size:    {OUTPUT.stat().st_size:,} bytes")
print()
print("✓ Recovery stream created with codec headers")