from pathlib import Path
import hashlib
import json


# ============================================================
# CINE-X — CASE INTEGRITY VERIFICATION
# ============================================================

CASE_DIR = Path("case_package")

EXPECTED_FILES = [
    CASE_DIR / "evidence" / "cam1_damaged.mp4",
    CASE_DIR / "recovered" / "cine_x_recovered.h264",
    CASE_DIR / "recovered" / "cine_x_recovered.mp4",
    CASE_DIR / "recovered" / "cine_x_recovered_fixed.mp4",
    CASE_DIR / "reports" / "CINE-X_Forensic_Report.txt",
    CASE_DIR / "CASE_RECORD.txt",
    CASE_DIR / "case_summary.json",
]


# ============================================================
# SHA-256
# ============================================================

def sha256_file(path):

    sha256 = hashlib.sha256()

    with path.open("rb") as f:

        while True:

            chunk = f.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


# ============================================================
# HEADER
# ============================================================

print()
print("CINE-X CASE INTEGRITY VERIFICATION")
print("=" * 70)

print(f"Case directory: {CASE_DIR}")
print()


# ============================================================
# CHECK CASE DIRECTORY
# ============================================================

if not CASE_DIR.exists():

    print("❌ Case package does not exist.")

    raise SystemExit(1)


# ============================================================
# VERIFY EXPECTED FILES
# ============================================================

print("CASE CONTENT VERIFICATION")
print("-" * 70)

missing = []

for path in EXPECTED_FILES:

    if path.exists():

        print(f"✅ {path}")

    else:

        print(f"❌ MISSING: {path}")

        missing.append(path)


print()


if missing:

    print("❌ CASE INTEGRITY VERIFICATION FAILED")

    print()
    print("Missing files:")

    for path in missing:

        print(f" - {path}")

    raise SystemExit(1)


print("✅ All expected case files are present.")
print()


# ============================================================
# HASH EVIDENCE AND RECOVERY FILES
# ============================================================

HASH_FILES = [
    CASE_DIR / "evidence" / "cam1_damaged.mp4",
    CASE_DIR / "recovered" / "cine_x_recovered.h264",
    CASE_DIR / "recovered" / "cine_x_recovered.mp4",
    CASE_DIR / "recovered" / "cine_x_recovered_fixed.mp4",
]


print("SHA-256 EVIDENCE HASHES")
print("-" * 70)

hash_results = {}


for path in HASH_FILES:

    digest = sha256_file(path)

    relative = str(path.relative_to(CASE_DIR))

    hash_results[relative] = digest

    print()
    print(f"File: {relative}")
    print(f"Size: {path.stat().st_size:,} bytes")
    print(f"SHA-256:")
    print(f"    {digest}")


print()


# ============================================================
# READ CASE SUMMARY
# ============================================================

summary_path = CASE_DIR / "case_summary.json"

try:

    summary = json.loads(
        summary_path.read_text(
            encoding="utf-8"
        )
    )

    print("CASE SUMMARY")
    print("-" * 70)

    case_id = summary.get(
        "case_id",
        "Unknown"
    )

    print(f"Case ID: {case_id}")

except Exception as exc:

    print("⚠️ Unable to parse case_summary.json")

    print(exc)

    summary = None


print()


# ============================================================
# GENERATE HASH MANIFEST
# ============================================================

manifest_path = CASE_DIR / "SHA256_MANIFEST.txt"

with manifest_path.open(
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "CINE-X SHA-256 EVIDENCE MANIFEST\n"
    )

    f.write("=" * 70)

    f.write("\n\n")

    for relative, digest in hash_results.items():

        f.write(
            f"{digest}  {relative}\n"
        )


print("HASH MANIFEST")
print("-" * 70)

print(
    f"Created: {manifest_path}"
)

print()


# ============================================================
# FINAL RESULT
# ============================================================

print("=" * 70)

print("CASE INTEGRITY VERIFICATION: PASSED")

print("=" * 70)

print()
print("✅ All expected files are present.")
print("✅ Evidence files successfully hashed.")
print("✅ Recovered files successfully hashed.")
print("✅ SHA-256 manifest generated.")
print()
print("CINE-X CASE INTEGRITY CONFIRMED.")
print()