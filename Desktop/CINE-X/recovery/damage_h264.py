from pathlib import Path

INPUT = Path("damaged/cam1_damaged.h264")

TARGET = 6_085_197
DAMAGE_SIZE = 100

data = bytearray(INPUT.read_bytes())

print("CINE-X Controlled Damage")
print("=" * 50)
print(f"Input size: {len(data):,} bytes")
print(f"Damage start: {TARGET:,}")
print(f"Damage size: {DAMAGE_SIZE} bytes")
print(f"Damage end: {TARGET + DAMAGE_SIZE:,}")

# Save original bytes so we can prove exactly what was changed
original_bytes = data[TARGET:TARGET + DAMAGE_SIZE]

# Replace with zeros
data[TARGET:TARGET + DAMAGE_SIZE] = b"\x00" * DAMAGE_SIZE

INPUT.write_bytes(data)

print()
print("✓ Controlled corruption applied.")
print("✓ Original cam1.h264 was NOT modified.")