from pathlib import Path


class H264RecoveryEngine:

    def __init__(self, input_file):
        self.input_file = Path(input_file)
        self.data = self.input_file.read_bytes()
        self.nals = self.find_nals(self.data)

    # ---------------------------------------------------------
    # Find H.264 NAL start codes
    # ---------------------------------------------------------
    def find_nals(self, data):
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

        nals = []

        for index, (start, start_code_length) in enumerate(positions):

            if index + 1 < len(positions):
                end = positions[index + 1][0]
            else:
                end = len(data)

            header_position = start + start_code_length

            if header_position >= len(data):
                continue

            nal_type = data[header_position] & 0x1F

            nals.append({
                "number": index + 1,
                "start": start,
                "end": end,
                "type": nal_type,
                "start_code_length": start_code_length
            })

        return nals

    # ---------------------------------------------------------
    # Find NAL containing a byte offset
    # ---------------------------------------------------------
    def find_nal_containing_offset(self, offset):

        for nal in self.nals:

            if nal["start"] <= offset < nal["end"]:
                return nal

        return None

    # ---------------------------------------------------------
    # Find previous IDR
    # ---------------------------------------------------------
    def find_previous_idr(self, nal_number):

        previous = None

        for nal in self.nals:

            if nal["number"] >= nal_number:
                break

            if nal["type"] == 5:
                previous = nal

        return previous

    # ---------------------------------------------------------
    # Find next IDR
    # ---------------------------------------------------------
    def find_next_idr(self, nal_number):

        for nal in self.nals:

            if nal["number"] > nal_number and nal["type"] == 5:
                return nal

        return None

    # ---------------------------------------------------------
    # Create recovery plan
    # ---------------------------------------------------------
    def create_recovery_plan(self, damage_start, damage_end):

        damage_start_nal = self.find_nal_containing_offset(
            damage_start
        )

        damage_end_nal = self.find_nal_containing_offset(
            damage_end
        )

        if damage_start_nal is None or damage_end_nal is None:
            raise ValueError("Could not locate damage inside NAL units.")

        previous_idr = self.find_previous_idr(
            damage_start_nal["number"]
        )

        next_idr = self.find_next_idr(
            damage_end_nal["number"]
        )

        return {
            "damage_start_nal": damage_start_nal,
            "damage_end_nal": damage_end_nal,
            "previous_idr": previous_idr,
            "next_idr": next_idr
        }

    # ---------------------------------------------------------
    # Build recovered H.264 stream
    # ---------------------------------------------------------
    def build_recovered_stream(self, recovery_plan, output_file):

        previous_idr = recovery_plan["previous_idr"]
        next_idr = recovery_plan["next_idr"]

        if previous_idr is None:
            raise ValueError("No previous IDR found.")

        if next_idr is None:
            raise ValueError("No next IDR found.")

        damage_start_nal = recovery_plan["damage_start_nal"]
        damage_end_nal = recovery_plan["damage_end_nal"]

        # -----------------------------------------------------
        # Part 1:
        # Keep everything before the damaged region.
        #
        # IMPORTANT:
        # We stop before the first damaged NAL.
        # -----------------------------------------------------

        prefix_end = damage_start_nal["start"]

        prefix = self.data[:prefix_end]

        # -----------------------------------------------------
        # Part 2:
        # Resume from the next clean IDR.
        # -----------------------------------------------------

        recovery_start = next_idr["start"]

        suffix = self.data[recovery_start:]

        # -----------------------------------------------------
        # Combine:
        #
        # VALID DATA
        #      +
        # CLEAN IDR ONWARD
        # -----------------------------------------------------

        recovered_data = prefix + suffix

        output_file = Path(output_file)
        output_file.parent.mkdir(
            parents=True,
            exist_ok=True
        )

        output_file.write_bytes(recovered_data)

        return {
            "output_file": output_file,
            "original_size": len(self.data),
            "recovered_size": len(recovered_data),
            "removed_bytes": len(self.data) - len(recovered_data),
            "damage_start_nal": damage_start_nal["number"],
            "damage_end_nal": damage_end_nal["number"],
            "recovery_idr": next_idr["number"],
            "recovery_offset": recovery_start
        }


# =============================================================
# TEST
# =============================================================

if __name__ == "__main__":

    INPUT_FILE = Path(
        "Data/Damaged/cam01_severely_damaged.h264"
    )

    OUTPUT_FILE = Path(
        "Data/Recovered/cam01_recovered_v1.h264"
    )

    # Ground-truth damage coordinates from our test damage generator
    DAMAGE_START = 1784148
    DAMAGE_END = 2072723

    print("CINE-X Recovery Engine")
    print("=" * 50)

    engine = H264RecoveryEngine(INPUT_FILE)

    print(f"File: {INPUT_FILE}")
    print(f"File size: {len(engine.data)}")
    print(f"NAL units: {len(engine.nals)}")

    print()
    print("Creating recovery plan")
    print("-" * 50)

    plan = engine.create_recovery_plan(
        DAMAGE_START,
        DAMAGE_END
    )

    print(
        "Damage starts in NAL:",
        plan["damage_start_nal"]["number"]
    )

    print(
        "Damage ends in NAL:",
        plan["damage_end_nal"]["number"]
    )

    print(
        "Previous IDR:",
        plan["previous_idr"]["number"]
    )

    print(
        "Next IDR:",
        plan["next_idr"]["number"]
    )

    print()
    print("Building recovered stream")
    print("-" * 50)

    result = engine.build_recovered_stream(
        plan,
        OUTPUT_FILE
    )

    print("RECOVERY COMPLETE")
    print("-" * 50)

    print("Output:", result["output_file"])
    print("Original size:", result["original_size"])
    print("Recovered size:", result["recovered_size"])
    print("Removed bytes:", result["removed_bytes"])
    print("Recovery IDR:", result["recovery_idr"])
    print("Recovery offset:", result["recovery_offset"])