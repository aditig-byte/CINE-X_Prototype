from pathlib import Path
import subprocess
import tempfile
import cv2
import numpy as np


ORIGINAL_FILE = Path(
    "Data/Original/cam01.h264"
)

RECOVERED_FILE = Path(
    "Data/Recovered/cam01_recovered_v1.h264"
)


def extract_all_frames(video_file, output_dir):

    output_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    output_pattern = str(
        output_dir / "frame_%06d.png"
    )

    command = [
        "ffmpeg",
        "-y",
        "-loglevel", "error",
        "-i", str(video_file),
        output_pattern
    ]

    result = subprocess.run(
        command,
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"FFmpeg failed for {video_file}:\n"
            f"{result.stderr}"
        )


def compare_images(original, recovered):

    a = cv2.imread(str(original))
    b = cv2.imread(str(recovered))

    if a is None or b is None:
        return None

    if a.shape != b.shape:
        return None

    difference = cv2.absdiff(a, b)

    mean_difference = float(
        difference.mean()
    )

    changed_pixels = np.count_nonzero(
        np.any(difference > 2, axis=2)
    )

    total_pixels = (
        a.shape[0] * a.shape[1]
    )

    changed_percentage = (
        changed_pixels /
        total_pixels
    ) * 100

    return (
        mean_difference,
        changed_percentage
    )


def main():

    print("CINE-X Recovery Boundary Mapper")
    print("=" * 60)

    if not ORIGINAL_FILE.exists():
        raise FileNotFoundError(
            f"Original file not found:\n{ORIGINAL_FILE}"
        )

    if not RECOVERED_FILE.exists():
        raise FileNotFoundError(
            f"Recovered file not found:\n{RECOVERED_FILE}"
        )

    with tempfile.TemporaryDirectory() as temp:

        temp = Path(temp)

        original_dir = temp / "original"
        recovered_dir = temp / "recovered"

        # ----------------------------------------------------
        # Extract ORIGINAL frames once
        # ----------------------------------------------------

        print()
        print("Extracting original frames...")
        print("-" * 60)

        extract_all_frames(
            ORIGINAL_FILE,
            original_dir
        )

        original_frames = sorted(
            original_dir.glob("*.png")
        )

        print(
            "Original frames extracted:",
            len(original_frames)
        )

        # ----------------------------------------------------
        # Extract RECOVERED frames once
        # ----------------------------------------------------

        print()
        print("Extracting recovered frames...")
        print("-" * 60)

        extract_all_frames(
            RECOVERED_FILE,
            recovered_dir
        )

        recovered_frames = sorted(
            recovered_dir.glob("*.png")
        )

        print(
            "Recovered frames extracted:",
            len(recovered_frames)
        )

        # ----------------------------------------------------
        # Known skipped frame count
        # ----------------------------------------------------

        skipped = (
            len(original_frames)
            - len(recovered_frames)
        )

        print()
        print("Frame difference")
        print("-" * 60)
        print("Skipped frames:", skipped)

        # ----------------------------------------------------
        # Search for matching boundary
        #
        # The recovered stream should correspond to a later
        # section of the original after the skipped region.
        #
        # We test recovered frames 500, 550, 600, 650.
        # ----------------------------------------------------

        test_frames = [
            500,
            550,
            600,
            650
        ]

        search_radius = 30

        print()
        print("Searching for matching frames...")
        print("-" * 60)

        for recovered_number in test_frames:

            if recovered_number >= len(
                recovered_frames
            ):
                continue

            recovered_image = recovered_frames[
                recovered_number
            ]

            expected_original = (
                recovered_number + skipped
            )

            search_start = max(
                0,
                expected_original - search_radius
            )

            search_end = min(
                len(original_frames) - 1,
                expected_original + search_radius
            )

            best = None

            for original_number in range(
                search_start,
                search_end + 1
            ):

                original_image = original_frames[
                    original_number
                ]

                result = compare_images(
                    original_image,
                    recovered_image
                )

                if result is None:
                    continue

                mean_difference, changed_percentage = result

                if (
                    best is None
                    or mean_difference
                    < best["mean_difference"]
                ):

                    best = {
                        "original": original_number,
                        "mean_difference": mean_difference,
                        "changed_percentage": changed_percentage
                    }

            if best:

                print(
                    f"Recovered frame "
                    f"{recovered_number:3d}"
                    f" -> Original frame "
                    f"{best['original']:3d}"
                    f" | Mean difference: "
                    f"{best['mean_difference']:.4f}"
                    f" | Changed pixels: "
                    f"{best['changed_percentage']:.4f}%"
                )

            else:

                print(
                    f"No match found for "
                    f"recovered frame "
                    f"{recovered_number}"
                )

    print()
    print("=" * 60)
    print("BOUNDARY MAPPING COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()