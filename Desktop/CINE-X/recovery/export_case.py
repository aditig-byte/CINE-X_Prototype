from pathlib import Path
from datetime import datetime
import shutil
import zipfile


# ============================================================
# CINE-X — FORENSIC CASE EXPORT
# ============================================================

BASE_DIR = Path(__file__).parent.parent

ORIGINAL_DIR = BASE_DIR / "original"
DAMAGED_DIR = BASE_DIR / "damaged"
RECOVERED_DIR = BASE_DIR / "recovered"
REPORT_DIR = BASE_DIR / "reports"

EXPORT_DIR = BASE_DIR / "case_export"
CASE_DIR = EXPORT_DIR / "CINE-X_CASE"

REPORT_FILE = REPORT_DIR / "CINE-X_Forensic_Report.txt"

RECOVERED_VIDEO = RECOVERED_DIR / "cine_x_recovered.mp4"
RECOVERED_H264 = RECOVERED_DIR / "cine_x_recovered.h264"


print()
print("=" * 70)
print("                    CINE-X")
print("             FORENSIC CASE EXPORT")
print("=" * 70)
print()


# ============================================================
# CREATE CASE DIRECTORY
# ============================================================

CASE_DIR.mkdir(parents=True, exist_ok=True)

EVIDENCE_DIR = CASE_DIR / "evidence"
RECOVERY_DIR = CASE_DIR / "recovered"
REPORTS_DIR = CASE_DIR / "reports"

EVIDENCE_DIR.mkdir(exist_ok=True)
RECOVERY_DIR.mkdir(exist_ok=True)
REPORTS_DIR.mkdir(exist_ok=True)


# ============================================================
# COPY ORIGINAL / DAMAGED EVIDENCE
# ============================================================

print("Preparing evidence package...")
print()

copied_files = []


for directory in [ORIGINAL_DIR, DAMAGED_DIR]:

    if not directory.exists():
        continue

    for file in directory.iterdir():

        if file.is_file():

            destination = EVIDENCE_DIR / file.name

            try:

                shutil.copy2(
                    file,
                    destination
                )

                copied_files.append(
                    destination
                )

                print(
                    f"Evidence copied: {file.name}"
                )

            except Exception as error:

                print(
                    f"Warning: could not copy {file.name}"
                )

                print(error)


# ============================================================
# COPY RECOVERED FILES
# ============================================================

print()
print("Preparing recovered evidence...")
print()


if RECOVERED_VIDEO.exists():

    shutil.copy2(
        RECOVERED_VIDEO,
        RECOVERY_DIR / RECOVERED_VIDEO.name
    )

    copied_files.append(
        RECOVERY_DIR / RECOVERED_VIDEO.name
    )

    print(
        f"Recovered video copied: {RECOVERED_VIDEO.name}"
    )


if RECOVERED_H264.exists():

    shutil.copy2(
        RECOVERED_H264,
        RECOVERY_DIR / RECOVERED_H264.name
    )

    copied_files.append(
        RECOVERY_DIR / RECOVERED_H264.name
    )

    print(
        f"Recovered H.264 copied: {RECOVERED_H264.name}"
    )


# ============================================================
# COPY FORENSIC REPORT
# ============================================================

print()
print("Preparing forensic report...")
print()


if REPORT_FILE.exists():

    shutil.copy2(
        REPORT_FILE,
        REPORTS_DIR / REPORT_FILE.name
    )

    copied_files.append(
        REPORTS_DIR / REPORT_FILE.name
    )

    print(
        "Forensic report copied."
    )

else:

    print(
        "Warning: forensic report was not found."
    )


# ============================================================
# CREATE CASE MANIFEST
# ============================================================

manifest = CASE_DIR / "CASE_MANIFEST.txt"

with manifest.open(
    "w",
    encoding="utf-8"
) as f:

    f.write(
        "=" * 70 + "\n"
    )

    f.write(
        "                         CINE-X\n"
    )

    f.write(
        "                 FORENSIC CASE MANIFEST\n"
    )

    f.write(
        "=" * 70 + "\n\n"
    )

    f.write(
        f"Export time:\n"
        f"    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    )

    f.write(
        "Case contents:\n\n"
    )

    for file in sorted(
        CASE_DIR.rglob("*")
    ):

        if file.is_file():

            relative = file.relative_to(
                CASE_DIR
            )

            size = file.stat().st_size

            f.write(
                f"{relative}\n"
            )

            f.write(
                f"    Size: {size:,} bytes\n\n"
            )

    f.write(
        "=" * 70 + "\n"
    )

    f.write(
        "CINE-X CASE PACKAGE COMPLETE\n"
    )

    f.write(
        "=" * 70 + "\n"
    )


print()
print("Case manifest created.")


# ============================================================
# CREATE ZIP PACKAGE
# ============================================================

EXPORT_DIR.mkdir(exist_ok=True)

timestamp = datetime.now().strftime(
    "%Y%m%d_%H%M%S"
)

zip_path = (
    EXPORT_DIR /
    f"CINE-X_Forensic_Case_{timestamp}.zip"
)


print()
print("Creating forensic case archive...")
print()


with zipfile.ZipFile(
    zip_path,
    "w",
    compression=zipfile.ZIP_DEFLATED
) as archive:

    for file in CASE_DIR.rglob("*"):

        if file.is_file():

            archive.write(
                file,
                file.relative_to(
                    EXPORT_DIR
                )
            )


# ============================================================
# FINAL OUTPUT
# ============================================================

print()
print("=" * 70)
print("                 FORENSIC EXPORT COMPLETE")
print("=" * 70)
print()

print(
    f"Case directory:"
)

print(
    f"    {CASE_DIR}"
)

print()

print(
    f"Case archive:"
)

print(
    f"    {zip_path}"
)

print()

print(
    f"Archive size:"
)

print(
    f"    {zip_path.stat().st_size:,} bytes"
)

print()

print(
    "Package contains:"
)

print(
    "    • Original/damaged evidence"
)

print(
    "    • Recovered H.264 stream"
)

print(
    "    • Recovered MP4 video"
)

print(
    "    • Forensic report"
)

print(
    "    • Case manifest"
)

print()

print(
    "STATUS: FORENSIC CASE PACKAGE READY"
)

print("=" * 70)