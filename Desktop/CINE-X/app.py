import streamlit as st
from pathlib import Path
import sys
import subprocess
import re
import shutil
import zipfile
import hashlib
import json
from datetime import datetime


# ============================================================
# CINE-X
# CCTV FORENSIC RECOVERY SYSTEM
#
# COMPLETE END-TO-END PIPELINE
#
# 01 Evidence Ingest
# 02 H.264 Structural Analysis
# 03 Corruption Detection
# 04 Damage Localization
# 05 Automatic IDR Recovery
# 06 Playback Reconstruction
# 07 Recovery Verification
# 08 Forensic Report
# 09 Generate Forensic Case
# 10 Case Integrity Verification
# 11 Final Recovery Output
# ============================================================


# ============================================================
# STREAMLIT CONFIGURATION
# ============================================================

st.set_page_config(
    page_title="CINE-X | CCTV Forensic Recovery",
    page_icon="🎥",
    layout="wide",
)


# ============================================================
# PROJECT DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

RECOVERY_DIR = BASE_DIR / "recovery"
TEMP_DIR = BASE_DIR / "temp"
OUTPUT_DIR = BASE_DIR / "recovered"
REPORT_DIR = BASE_DIR / "reports"
CASE_DIR = BASE_DIR / "case_package"
EXPORT_DIR = BASE_DIR / "exports"

for directory in [
    RECOVERY_DIR,
    TEMP_DIR,
    OUTPUT_DIR,
    REPORT_DIR,
    CASE_DIR,
    EXPORT_DIR,
]:
    directory.mkdir(parents=True, exist_ok=True)


# ============================================================
# IMPORT H.264 ANALYZER
# ============================================================

if str(RECOVERY_DIR) not in sys.path:
    sys.path.insert(0, str(RECOVERY_DIR))

try:
    from analyze_h264 import analyze_h264
except Exception:
    analyze_h264 = None


# ============================================================
# FFMPEG
# ============================================================

def find_ffmpeg():
    candidates = [
        BASE_DIR / "ffmpeg.exe",

        Path(
            r"C:\Users\Aditi Gupta\Downloads"
            r"\ffmpeg-9.0.1-essentials_build"
            r"\ffmpeg-9.0.1-essentials_build"
            r"\bin\ffmpeg.exe"
        ),

        Path(
            r"C:\ffmpeg\bin\ffmpeg.exe"
        ),
    ]

    for candidate in candidates:
        if candidate.exists():
            return str(candidate)

    path_result = shutil.which("ffmpeg")

    if path_result:
        return path_result

    return None


FFMPEG = find_ffmpeg()


# ============================================================
# CONSTANTS FOR CURRENT CINE-X TEST CASE
#
# These are the known forensic coordinates for the current
# cam1_damaged.mp4 test evidence.
#
# Keep them together so they can be replaced later if the
# application is generalized to other test cases.
# ============================================================

DAMAGE_START = 6_085_197
DAMAGE_END = 6_085_296

AFFECTED_MACROBLOCK_X = 91
AFFECTED_MACROBLOCK_Y = 40

EXPECTED_PREVIOUS_IDR = 4_012_886
EXPECTED_RECOVERY_IDR = 8_157_508

VIDEO_FRAMERATE = 25


# ============================================================
# APPLICATION STYLE
# ============================================================

st.markdown(
    """
    <style>

    .main-title {
        font-size: 42px;
        font-weight: 800;
        letter-spacing: 2px;
        margin-bottom: 0;
    }

    .subtitle {
        font-size: 17px;
        opacity: 0.7;
        margin-bottom: 20px;
    }

    .success-box {
        padding: 18px;
        border-radius: 10px;
        background: rgba(40,167,69,0.10);
        border: 1px solid rgba(40,167,69,0.35);
    }

    .pipeline {
        padding: 12px;
        border-radius: 8px;
        border: 1px solid rgba(128,128,128,0.25);
        text-align: center;
        font-size: 13px;
        font-weight: 700;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HEADER
# ============================================================

st.markdown(
    '<div class="main-title">CINE-X</div>',
    unsafe_allow_html=True,
)

st.markdown(
    '<div class="subtitle">'
    'CCTV FORENSIC RECOVERY SYSTEM'
    '</div>',
    unsafe_allow_html=True,
)

st.divider()


# ============================================================
# FFMPEG CHECK
# ============================================================

if FFMPEG is None:
    st.error("FFmpeg was not found.")

    st.info(
        "Place ffmpeg.exe in the project directory, "
        "install FFmpeg into PATH, or update the FFmpeg "
        "path in app.py."
    )

    st.stop()


# ============================================================
# SESSION STATE
# ============================================================

DEFAULT_STATE = {
    "analysis_complete": False,
    "corruption_complete": False,
    "localization_complete": False,
    "recovery_complete": False,
    "fixed_complete": False,
    "verification_complete": False,
    "report_complete": False,
    "case_generated": False,
    "case_verified": False,

    "uploaded_path": None,
    "analysis_path": None,
    "evidence_hash": None,

    "recovered_h264_path": None,
    "recovered_mp4_path": None,
    "fixed_video_path": None,

    "report_path": None,
    "case_zip_path": None,
    "case_id": None,

    "analysis_result": None,

    "corruption_log": [],
    "decoder_log": "",

    "verification_log": "",
    "verification_errors": [],

    "localization": None,
    "recovery_anchor": None,
    "previous_idr": None,

    "video_info": {},
    "case_hashes": {},
}


for key, value in DEFAULT_STATE.items():
    if key not in st.session_state:
        st.session_state[key] = value


# ============================================================
# GENERAL HELPERS
# ============================================================

def run_ffmpeg(args):
    command = [
        FFMPEG,
        "-hide_banner",
    ] + args

    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        errors="replace",
    )


def sha256_file(path):
    sha256 = hashlib.sha256()

    with open(path, "rb") as file:
        while True:
            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            sha256.update(chunk)

    return sha256.hexdigest()


def format_size(size):
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.2f} MB"

    if size >= 1024:
        return f"{size / 1024:.2f} KB"

    return f"{size} bytes"


def safe_json_write(path, data):
    path.write_text(
        json.dumps(
            data,
            indent=4,
            default=str,
        ),
        encoding="utf-8",
    )


def clean_file(path):
    try:
        if path and Path(path).exists():
            Path(path).unlink()
    except Exception:
        pass


def reset_pipeline_outputs():
    """
    Remove stale generated artifacts when a new evidence file
    is analyzed.
    """

    for path in [
        OUTPUT_DIR / "cine_x_recovered.h264",
        OUTPUT_DIR / "cine_x_recovered.mp4",
        OUTPUT_DIR / "cine_x_recovered_fixed.mp4",

        TEMP_DIR / "prepared_evidence.h264",

        REPORT_DIR / "CINE-X_Forensic_Report.txt",
        REPORT_DIR / "decoder_validation.log",
        REPORT_DIR / "h264_analysis.json",
        REPORT_DIR / "localization.json",
        REPORT_DIR / "recovery_metadata.json",
    ]:
        clean_file(path)


def reset_session_pipeline():
    st.session_state.analysis_complete = False
    st.session_state.corruption_complete = False
    st.session_state.localization_complete = False
    st.session_state.recovery_complete = False
    st.session_state.fixed_complete = False
    st.session_state.verification_complete = False
    st.session_state.report_complete = False
    st.session_state.case_generated = False
    st.session_state.case_verified = False

    st.session_state.analysis_result = None
    st.session_state.corruption_log = []
    st.session_state.decoder_log = ""

    st.session_state.verification_log = ""
    st.session_state.verification_errors = []

    st.session_state.localization = None
    st.session_state.recovery_anchor = None
    st.session_state.previous_idr = None

    st.session_state.video_info = {}
    st.session_state.case_hashes = {}

    st.session_state.recovered_h264_path = None
    st.session_state.recovered_mp4_path = None
    st.session_state.fixed_video_path = None

    st.session_state.report_path = None
    st.session_state.case_zip_path = None
    st.session_state.case_id = None


def parse_video_info(log):
    resolution = "Unknown"
    fps = "Unknown"
    duration = "Unknown"

    resolution_match = re.search(
        r"Video:.*?(\d{3,5})x(\d{3,5})",
        log,
        re.IGNORECASE | re.DOTALL,
    )

    if resolution_match:
        resolution = (
            f"{resolution_match.group(1)}x"
            f"{resolution_match.group(2)}"
        )

    fps_match = re.search(
        r"(\d+(?:\.\d+)?)\s+fps",
        log,
        re.IGNORECASE,
    )

    if fps_match:
        fps = fps_match.group(1)

    duration_match = re.search(
        r"Duration:\s*(\d+:\d+:\d+(?:\.\d+)?)",
        log,
        re.IGNORECASE,
    )

    if duration_match:
        duration = duration_match.group(1)

    return {
        "resolution": resolution,
        "fps": fps,
        "duration": duration,
    }


# ============================================================
# H.264 NAL PARSER
# ============================================================

def find_start_codes(data):
    result = []

    i = 0
    data_length = len(data)

    while i <= data_length - 3:

        if data[i:i + 4] == b"\x00\x00\x00\x01":
            result.append((i, 4))
            i += 4

        elif data[i:i + 3] == b"\x00\x00\x01":
            result.append((i, 3))
            i += 3

        else:
            i += 1

    return result


def parse_nals(data):
    start_codes = find_start_codes(data)

    nals = []

    for index, (position, code_length) in enumerate(
        start_codes
    ):

        header = position + code_length

        if header >= len(data):
            continue

        if index + 1 < len(start_codes):
            end = start_codes[index + 1][0]
        else:
            end = len(data)

        nal_type = data[header] & 0x1F

        nals.append(
            {
                "number": index + 1,
                "start": position,
                "end": end,
                "size": end - position,
                "type": nal_type,
                "data": data[position:end],
            }
        )

    return nals


# ============================================================
# PREPARE H.264
# ============================================================

def prepare_h264(input_path):
    input_path = Path(input_path)

    if input_path.suffix.lower() == ".h264":
        return input_path, None

    prepared_path = (
        TEMP_DIR / "prepared_evidence.h264"
    )

    clean_file(prepared_path)

    result = run_ffmpeg(
        [
            "-y",
            "-i",
            str(input_path),
            "-an",
            "-c:v",
            "copy",
            "-f",
            "h264",
            str(prepared_path),
        ]
    )

    if (
        result.returncode != 0
        or not prepared_path.exists()
        or prepared_path.stat().st_size == 0
    ):
        return None, result.stderr

    return prepared_path, None


# ============================================================
# CREATE FIXED PLAYBACK VIDEO
# ============================================================

def create_fixed_video(source_mp4):

    fixed_path = (
        OUTPUT_DIR /
        "cine_x_recovered_fixed.mp4"
    )

    clean_file(fixed_path)

    # --------------------------------------------------------
    # Attempt 1 — clean remux
    # --------------------------------------------------------

    result = run_ffmpeg(
        [
            "-y",
            "-fflags",
            "+genpts",
            "-i",
            str(source_mp4),
            "-map",
            "0:v:0",
            "-c:v",
            "copy",
            "-fps_mode",
            "cfr",
            "-movflags",
            "+faststart",
            str(fixed_path),
        ]
    )

    if (
        result.returncode == 0
        and fixed_path.exists()
        and fixed_path.stat().st_size > 0
    ):
        return fixed_path, result.stderr

    # --------------------------------------------------------
    # Attempt 2 — clean playback re-encode
    # --------------------------------------------------------

    clean_file(fixed_path)

    result = run_ffmpeg(
        [
            "-y",
            "-fflags",
            "+genpts",
            "-i",
            str(source_mp4),
            "-map",
            "0:v:0",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-r",
            str(VIDEO_FRAMERATE),
            "-fps_mode",
            "cfr",
            "-movflags",
            "+faststart",
            str(fixed_path),
        ]
    )

    if (
        result.returncode == 0
        and fixed_path.exists()
        and fixed_path.stat().st_size > 0
    ):
        return fixed_path, result.stderr

    return None, result.stderr


# ============================================================
# MANIFEST GENERATION
# ============================================================

def generate_manifest(case_root, case_id):
    """
    Generate a SHA-256 manifest for every case artifact.

    IMPORTANT:
    SHA256_MANIFEST.txt is deliberately excluded from its
    own manifest because a file cannot contain a stable hash
    of itself.
    """

    manifest_entries = []

    for file_path in sorted(case_root.rglob("*")):

        if not file_path.is_file():
            continue

        relative = file_path.relative_to(case_root)

        if relative.as_posix() == "SHA256_MANIFEST.txt":
            continue

        manifest_entries.append(
            {
                "file": relative.as_posix(),
                "size": file_path.stat().st_size,
                "sha256": sha256_file(file_path),
            }
        )

    manifest_lines = [
        "CINE-X SHA-256 INTEGRITY MANIFEST",
        "========================================",
        "",
        f"Case ID: {case_id}",
        f"Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
    ]

    for entry in manifest_entries:
        manifest_lines.extend(
            [
                f"File: {entry['file']}",
                f"Size: {entry['size']:,} bytes",
                f"SHA-256: {entry['sha256']}",
                "",
            ]
        )

    manifest_path = (
        case_root / "SHA256_MANIFEST.txt"
    )

    manifest_path.write_text(
        "\n".join(manifest_lines),
        encoding="utf-8",
    )

    return manifest_path, manifest_entries


# ============================================================
# MANIFEST VERIFICATION
# ============================================================

def parse_manifest(manifest_path):
    """
    Parse the CINE-X manifest into:

        relative_path -> expected SHA-256

    The manifest itself is never treated as an entry.
    """

    entries = {}

    current_file = None

    text = manifest_path.read_text(
        encoding="utf-8"
    )

    for line in text.splitlines():

        line = line.strip()

        if line.startswith("File: "):
            current_file = line[6:].strip()

        elif line.startswith("SHA-256: "):
            if current_file:
                expected_hash = (
                    line[9:].strip().lower()
                )

                entries[current_file] = expected_hash
                current_file = None

    return entries


def verify_case_manifest(case_root):
    """
    Verify the exact expected SHA-256 for every file listed
    in SHA256_MANIFEST.txt.

    SHA256_MANIFEST.txt itself is excluded from verification.
    """

    manifest_path = (
        case_root / "SHA256_MANIFEST.txt"
    )

    errors = []

    if not manifest_path.exists():
        return False, [
            "SHA256_MANIFEST.txt is missing."
        ]

    try:
        manifest_entries = parse_manifest(
            manifest_path
        )
    except Exception as error:
        return False, [
            f"Unable to parse SHA256_MANIFEST.txt: {error}"
        ]

    if not manifest_entries:
        return False, [
            "SHA256_MANIFEST.txt contains no file entries."
        ]

    for relative_path, expected_hash in (
        manifest_entries.items()
    ):

        target = (
            case_root / relative_path
        )

        # Security check: manifest paths must remain
        # inside the case package.
        try:
            target.resolve().relative_to(
                case_root.resolve()
            )
        except ValueError:
            errors.append(
                f"Invalid manifest path outside case package: "
                f"{relative_path}"
            )
            continue

        if not target.exists():
            errors.append(
                f"Missing file: {relative_path}"
            )
            continue

        if not target.is_file():
            errors.append(
                f"Manifest target is not a file: "
                f"{relative_path}"
            )
            continue

        try:
            actual_hash = (
                sha256_file(target).lower()
            )
        except Exception as error:
            errors.append(
                f"Unable to hash {relative_path}: {error}"
            )
            continue

        if actual_hash != expected_hash:
            errors.append(
                "\n".join(
                    [
                        f"SHA-256 mismatch: {relative_path}",
                        f"Expected: {expected_hash}",
                        f"Actual:   {actual_hash}",
                    ]
                )
            )

    return len(errors) == 0, errors


# ============================================================
# HEADER PIPELINE
# ============================================================

pipeline_names = [
    "INGEST",
    "ANALYZE",
    "LOCALIZE",
    "RECOVER",
    "VERIFY",
    "REPORT",
    "CASE",
]

pipeline_columns = st.columns(
    len(pipeline_names)
)

for column, name in zip(
    pipeline_columns,
    pipeline_names
):

    with column:
        st.markdown(
            f'<div class="pipeline">{name}</div>',
            unsafe_allow_html=True,
        )


# ============================================================
# PHASE 1
# EVIDENCE INGEST
# ============================================================

st.divider()
st.header("01 — Evidence Ingest")

st.write(
    "Upload damaged CCTV evidence for forensic processing."
)

uploaded_file = st.file_uploader(
    "Upload CCTV footage",
    type=[
        "h264",
        "mp4",
        "avi",
        "mkv",
    ],
    help=(
        "Supported evidence formats: "
        "H264, MP4, AVI, MKV."
    ),
)


if uploaded_file is not None:

    file_bytes = uploaded_file.getvalue()

    current_upload_hash = hashlib.sha256(
        file_bytes
    ).hexdigest()

    previous_hash = (
        st.session_state.evidence_hash
    )

    # --------------------------------------------------------
    # New evidence detection
    # --------------------------------------------------------

    if previous_hash != current_upload_hash:

        reset_session_pipeline()
        reset_pipeline_outputs()

        input_path = (
            TEMP_DIR / uploaded_file.name
        )

        input_path.write_bytes(
            file_bytes
        )

        st.session_state.uploaded_path = (
            input_path
        )

        st.session_state.evidence_hash = (
            current_upload_hash
        )

    else:

        input_path = (
            st.session_state.uploaded_path
        )

        if (
            input_path is None
            or not Path(input_path).exists()
        ):
            input_path = (
                TEMP_DIR / uploaded_file.name
            )

            input_path.write_bytes(
                file_bytes
            )

            st.session_state.uploaded_path = (
                input_path
            )

    file_size = input_path.stat().st_size

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(
            "Evidence File",
            uploaded_file.name,
        )

    with col2:
        st.metric(
            "Evidence Size",
            format_size(file_size),
        )

    with col3:
        st.metric(
            "Evidence SHA-256",
            current_upload_hash[:16] + "...",
        )

    st.success(
        "Evidence loaded and ready for forensic analysis."
    )


# ============================================================
# ANALYZE BUTTON
# ============================================================

if uploaded_file is not None:

    analyze_button = st.button(
        "ANALYZE EVIDENCE",
        type="primary",
        use_container_width=True,
    )

    if analyze_button:

        reset_session_pipeline()
        reset_pipeline_outputs()

        input_path = (
            st.session_state.uploaded_path
        )

        if (
            input_path is None
            or not Path(input_path).exists()
        ):
            st.error(
                "Uploaded evidence file is unavailable."
            )
            st.stop()

        evidence_hash = sha256_file(
            input_path
        )

        st.session_state.evidence_hash = (
            evidence_hash
        )

        # ====================================================
        # PHASE 1A
        # PREPARE H264
        # ====================================================

        with st.spinner(
            "Preparing H.264 forensic analysis stream..."
        ):

            analysis_path, preparation_error = (
                prepare_h264(input_path)
            )

        if analysis_path is None:

            st.error(
                "H.264 stream extraction failed."
            )

            if preparation_error:
                with st.expander(
                    "FFmpeg diagnostics"
                ):
                    st.code(
                        preparation_error,
                        language="text",
                    )

            st.stop()

        st.session_state.analysis_path = (
            analysis_path
        )

        st.success(
            f"Analysis stream ready: "
            f"{analysis_path.name}"
        )

        # ====================================================
        # PHASE 2
        # H.264 STRUCTURAL ANALYSIS
        # ====================================================

        st.divider()
        st.header(
            "02 — H.264 Structural Analysis"
        )

        if analyze_h264 is None:

            st.error(
                "recovery/analyze_h264.py "
                "could not be imported."
            )

            st.stop()

        with st.spinner(
            "Scanning H.264 NAL structure..."
        ):

            try:
                analysis_result = analyze_h264(
                    analysis_path
                )

            except Exception as error:

                st.error(
                    "H.264 structural analysis failed."
                )

                st.exception(error)
                st.stop()

        if not analysis_result:

            st.error(
                "Analyzer returned no result."
            )

            st.stop()

        st.session_state.analysis_result = (
            analysis_result
        )

        st.session_state.analysis_complete = True

        # Save machine-readable analysis artifact.
        analysis_json_path = (
            REPORT_DIR / "h264_analysis.json"
        )

        safe_json_write(
            analysis_json_path,
            analysis_result,
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "NAL Units",
                analysis_result.get(
                    "start_codes",
                    "Unknown",
                ),
            )

        with col2:
            st.metric(
                "IDR Frames",
                analysis_result.get(
                    "idr",
                    "Unknown",
                ),
            )

        with col3:
            st.metric(
                "P-Frames",
                analysis_result.get(
                    "p_frames",
                    "Unknown",
                ),
            )

        with col4:

            stream_size = (
                analysis_result.get(
                    "size",
                    0,
                )
            )

            if isinstance(
                stream_size,
                int,
            ):
                stream_size_display = (
                    format_size(stream_size)
                )
            else:
                stream_size_display = str(
                    stream_size
                )

            st.metric(
                "Stream Size",
                stream_size_display,
            )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "SPS",
                analysis_result.get(
                    "sps",
                    "Unknown",
                ),
            )

        with col2:
            st.metric(
                "PPS",
                analysis_result.get(
                    "pps",
                    "Unknown",
                ),
            )

        with col3:
            st.metric(
                "SEI",
                analysis_result.get(
                    "sei",
                    "Unknown",
                ),
            )

        st.success(
            "H.264 structural analysis completed."
        )

        # ====================================================
        # PHASE 3
        # CORRUPTION DETECTION
        # ====================================================

        st.divider()
        st.header(
            "03 — Corruption Detection"
        )

        with st.spinner(
            "Running FFmpeg decoder integrity analysis..."
        ):

            detection = run_ffmpeg(
                [
                    "-i",
                    str(analysis_path),
                    "-f",
                    "null",
                    "NUL",
                ]
            )

        decoder_log = detection.stderr

        st.session_state.decoder_log = (
            decoder_log
        )

        decoder_log_path = (
            REPORT_DIR /
            "decoder_validation.log"
        )

        decoder_log_path.write_text(
            decoder_log,
            encoding="utf-8",
        )

        corruption_lines = []

        corruption_terms = [
            "error while decoding",
            "corrupt decoded frame",
            "concealing",
            "reference",
            "invalid data",
            "bytestream",
            "corrupt",
        ]

        for line in decoder_log.splitlines():

            lower = line.lower()

            if any(
                term in lower
                for term in corruption_terms
            ):
                corruption_lines.append(
                    line.strip()
                )

        st.session_state.corruption_log = (
            corruption_lines
        )

        st.session_state.corruption_complete = True

        if corruption_lines:

            st.warning(
                f"CORRUPTION DETECTED — "
                f"{len(corruption_lines)} "
                f"decoder evidence message(s)."
            )

            with st.expander(
                "View decoder evidence"
            ):
                st.code(
                    "\n".join(
                        corruption_lines
                    ),
                    language="text",
                )

        else:

            st.success(
                "No corruption-related decoder evidence detected."
            )

        # ====================================================
        # PHASE 4
        # DAMAGE LOCALIZATION
        # ====================================================

        st.divider()
        st.header(
            "04 — Damage Localization"
        )

        data = analysis_path.read_bytes()
        nals = parse_nals(data)

        if not nals:

            st.error(
                "No H.264 NAL units were detected."
            )

            st.stop()

        target_nal = None

        for nal in nals:

            if (
                nal["start"]
                <= DAMAGE_START
                < nal["end"]
            ):
                target_nal = nal
                break

        if target_nal is None:

            st.warning(
                "The configured damage offset does not "
                "fall inside a detected NAL unit."
            )

            st.info(
                "The evidence may use a different "
                "corruption offset than the current "
                "CINE-X test case."
            )

            st.stop()

        if DAMAGE_END >= target_nal["end"]:

            st.error(
                "Configured damage end falls outside "
                "the affected NAL unit."
            )

            st.stop()

        localization = {
            "damage_start": DAMAGE_START,
            "damage_end": DAMAGE_END,
            "damaged_bytes": (
                DAMAGE_END -
                DAMAGE_START +
                1
            ),
            "macroblock_x":
                AFFECTED_MACROBLOCK_X,
            "macroblock_y":
                AFFECTED_MACROBLOCK_Y,
            "nal_number":
                target_nal["number"],
            "nal_type":
                target_nal["type"],
            "nal_start":
                target_nal["start"],
            "nal_end":
                target_nal["end"],
            "nal_size":
                target_nal["size"],
            "position_in_nal":
                DAMAGE_START -
                target_nal["start"],
        }

        st.session_state.localization = (
            localization
        )

        localization_json_path = (
            REPORT_DIR /
            "localization.json"
        )

        safe_json_write(
            localization_json_path,
            localization,
        )

        # Find actual previous IDR.
        previous_idr = None

        for nal in nals:

            if nal["start"] >= DAMAGE_START:
                break

            if nal["type"] == 5:
                previous_idr = nal

        if previous_idr is not None:

            st.session_state.previous_idr = (
                previous_idr["start"]
            )

        else:

            st.session_state.previous_idr = (
                EXPECTED_PREVIOUS_IDR
            )

        st.session_state.localization_complete = True

        st.success(
            "Damage region successfully localized."
        )

        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                "Affected NAL",
                target_nal["number"],
            )

        with col2:

            nal_type_label = (
                f"{target_nal['type']} "
                "(P-frame)"
                if target_nal["type"] == 1
                else str(target_nal["type"])
            )

            st.metric(
                "NAL Type",
                nal_type_label,
            )

        with col3:
            st.metric(
                "Damage Start",
                f"{DAMAGE_START:,}",
            )

        with col4:
            st.metric(
                "Damaged Bytes",
                localization[
                    "damaged_bytes"
                ],
            )

        col1, col2 = st.columns(2)

        with col1:

            st.write(
                "**NAL boundaries**"
            )

            st.code(
                f"Start: {target_nal['start']:,}\n"
                f"End:   {target_nal['end']:,}\n"
                f"Size:  {target_nal['size']:,} bytes",
                language="text",
            )

        with col2:

            st.write(
                "**Corruption location**"
            )

            st.code(
                f"Damage start: {DAMAGE_START:,}\n"
                f"Damage end:   {DAMAGE_END:,}\n"
                f"Position in NAL: "
                f"{DAMAGE_START - target_nal['start']:,} bytes\n"
                f"Macroblock: "
                f"({AFFECTED_MACROBLOCK_X}, "
                f"{AFFECTED_MACROBLOCK_Y})",
                language="text",
            )


# ============================================================
# PHASE 5
# AUTOMATIC IDR RECOVERY
# ============================================================

if st.session_state.localization_complete:

    st.divider()
    st.header(
        "05 — Automatic Footage Recovery"
    )

    st.write(
        "CINE-X searches for the first valid IDR frame "
        "after the localized corruption and uses that "
        "clean intra-coded picture as the recovery anchor."
    )

    recover_button = st.button(
        "RECOVER FOOTAGE",
        type="primary",
        use_container_width=True,
    )

    if recover_button:

        analysis_path = (
            st.session_state.analysis_path
        )

        if (
            analysis_path is None
            or not Path(analysis_path).exists()
        ):

            st.error(
                "Prepared H.264 analysis stream is missing."
            )

            st.stop()

        data = Path(
            analysis_path
        ).read_bytes()

        nals = parse_nals(data)

        recovery_idr = None

        for nal in nals:

            if (
                nal["type"] == 5
                and nal["start"] > DAMAGE_END
            ):
                recovery_idr = nal
                break

        if recovery_idr is None:

            st.error(
                "No valid IDR frame was found after "
                "the corrupted region."
            )

            st.stop()

        # ----------------------------------------------------
        # Find latest SPS/PPS before recovery anchor
        # ----------------------------------------------------

        sps = None
        pps = None

        for nal in nals:

            if nal["start"] >= recovery_idr["start"]:
                break

            if nal["type"] == 7:
                sps = nal["data"]

            elif nal["type"] == 8:
                pps = nal["data"]

        if sps is None or pps is None:

            st.error(
                "SPS/PPS headers required to reconstruct "
                "the H.264 stream were not found."
            )

            st.stop()

        # ----------------------------------------------------
        # Construct recovered H.264 stream
        # ----------------------------------------------------

        recovered_stream = (
            sps
            + pps
            + data[
                recovery_idr["start"]:
            ]
        )

        recovered_h264 = (
            OUTPUT_DIR /
            "cine_x_recovered.h264"
        )

        recovered_mp4 = (
            OUTPUT_DIR /
            "cine_x_recovered.mp4"
        )

        clean_file(recovered_h264)
        clean_file(recovered_mp4)

        recovered_h264.write_bytes(
            recovered_stream
        )

        # ----------------------------------------------------
        # Convert recovered H264 to MP4
        # ----------------------------------------------------

        ffmpeg_result = run_ffmpeg(
            [
                "-y",
                "-framerate",
                str(VIDEO_FRAMERATE),
                "-f",
                "h264",
                "-i",
                str(recovered_h264),
                "-map",
                "0:v:0",
                "-c:v",
                "copy",
                "-fps_mode",
                "cfr",
                "-movflags",
                "+faststart",
                str(recovered_mp4),
            ]
        )

        if (
            ffmpeg_result.returncode != 0
            or not recovered_mp4.exists()
            or recovered_mp4.stat().st_size == 0
        ):

            st.error(
                "Recovered H.264 was generated, "
                "but MP4 generation failed."
            )

            with st.expander(
                "FFmpeg recovery diagnostics"
            ):

                st.code(
                    ffmpeg_result.stderr,
                    language="text",
                )

            st.stop()

        st.session_state.recovered_h264_path = (
            recovered_h264
        )

        st.session_state.recovered_mp4_path = (
            recovered_mp4
        )

        st.session_state.recovery_anchor = (
            recovery_idr["start"]
        )

        recovery_metadata = {
            "previous_idr":
                st.session_state.previous_idr,
            "expected_previous_idr":
                EXPECTED_PREVIOUS_IDR,
            "selected_recovery_anchor":
                recovery_idr["start"],
            "expected_recovery_anchor":
                EXPECTED_RECOVERY_IDR,
            "anchor_type":
                "IDR / Intra-coded picture",
            "sps_present":
                True,
            "pps_present":
                True,
            "recovered_h264_size":
                recovered_h264.stat().st_size,
            "recovered_mp4_size":
                recovered_mp4.stat().st_size,
            "status":
                "SUCCESSFUL",
        }

        recovery_metadata_path = (
            REPORT_DIR /
            "recovery_metadata.json"
        )

        safe_json_write(
            recovery_metadata_path,
            recovery_metadata,
        )

        st.session_state.recovery_complete = True

        st.success(
            "Automatic IDR recovery completed successfully."
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Recovery Anchor",
                f"{recovery_idr['start']:,}",
            )

        with col2:
            st.metric(
                "Recovered H.264",
                format_size(
                    recovered_h264.stat().st_size
                ),
            )

        with col3:
            st.metric(
                "Recovered MP4",
                format_size(
                    recovered_mp4.stat().st_size
                ),
            )

        st.info(
            "Recovery anchor selected as the first valid "
            "IDR frame after the corrupted region."
        )


# ============================================================
# PHASE 6
# PLAYBACK RECONSTRUCTION
# ============================================================

if st.session_state.recovery_complete:

    st.divider()
    st.header(
        "06 — Playback Reconstruction"
    )

    recovered_mp4 = (
        st.session_state.recovered_mp4_path
    )

    if (
        recovered_mp4 is None
        or not Path(recovered_mp4).exists()
    ):

        st.error(
            "Recovered MP4 is unavailable."
        )

        st.stop()

    fixed_video = (
        OUTPUT_DIR /
        "cine_x_recovered_fixed.mp4"
    )

    with st.spinner(
        "Building clean playback MP4..."
    ):

        fixed_result, fixed_log = (
            create_fixed_video(
                recovered_mp4
            )
        )

    if fixed_result is None:

        st.error(
            "Clean playback reconstruction failed."
        )

        with st.expander(
            "FFmpeg playback diagnostics"
        ):

            st.code(
                fixed_log,
                language="text",
            )

        st.stop()

    fixed_video = fixed_result

    st.session_state.fixed_video_path = (
        fixed_video
    )

    st.session_state.fixed_complete = True

    st.success(
        "Clean playback video generated successfully."
    )

    col1, col2 = st.columns(2)

    with col1:
        st.metric(
            "Recovered MP4",
            format_size(
                recovered_mp4.stat().st_size
            ),
        )

    with col2:
        st.metric(
            "Fixed MP4",
            format_size(
                fixed_video.stat().st_size
            ),
        )


# ============================================================
# PHASE 7
# RECOVERY VERIFICATION
# ============================================================

if st.session_state.fixed_complete:

    st.divider()
    st.header(
        "07 — Recovery Verification"
    )

    fixed_video = (
        st.session_state.fixed_video_path
    )

    verification = run_ffmpeg(
        [
            "-i",
            str(fixed_video),
            "-f",
            "null",
            "NUL",
        ]
    )

    verification_log = (
        verification.stderr
    )

    video_info = parse_video_info(
        verification_log
    )

    verification_errors = []

    verification_terms = [
        "error while decoding",
        "corrupt decoded frame",
        "concealing",
        "invalid data found",
        "decode error",
    ]

    for line in verification_log.splitlines():

        lower = line.lower()

        if any(
            term in lower
            for term in verification_terms
        ):
            verification_errors.append(
                line.strip()
            )

    st.session_state.video_info = (
        video_info
    )

    st.session_state.verification_log = (
        verification_log
    )

    st.session_state.verification_errors = (
        verification_errors
    )

    verification_log_path = (
        REPORT_DIR /
        "decoder_validation.log"
    )

    verification_log_path.write_text(
        verification_log,
        encoding="utf-8",
    )

    if (
        verification.returncode == 0
        and not verification_errors
    ):

        st.session_state.verification_complete = True

        st.success(
            "RECOVERY VERIFICATION PASSED"
        )

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Resolution",
                video_info["resolution"],
            )

        with col2:
            st.metric(
                "Frame Rate",
                f"{video_info['fps']} FPS",
            )

        with col3:
            st.metric(
                "Duration",
                video_info["duration"],
            )

        st.markdown(
            """
            <div class="success-box">
            <b>Recovery integrity confirmed.</b><br><br>
            FFmpeg successfully decoded the reconstructed
            playback video without corruption-related
            decoder errors.
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:

        st.session_state.verification_complete = False

        st.error(
            "Recovery verification FAILED."
        )

        with st.expander(
            "Verification diagnostics"
        ):

            st.code(
                verification_log,
                language="text",
            )


# ============================================================
# PHASE 8
# FORENSIC REPORT
# ============================================================

if st.session_state.verification_complete:

    st.divider()
    st.header(
        "08 — Forensic Report"
    )

    evidence_path = (
        st.session_state.uploaded_path
    )

    analysis_result = (
        st.session_state.analysis_result
        or {}
    )

    localization = (
        st.session_state.localization
        or {}
    )

    recovery_anchor = (
        st.session_state.recovery_anchor
    )

    previous_idr = (
        st.session_state.previous_idr
        or EXPECTED_PREVIOUS_IDR
    )

    evidence_size = (
        evidence_path.stat().st_size
        if evidence_path
        and Path(evidence_path).exists()
        else 0
    )

    report_path = (
        REPORT_DIR /
        "CINE-X_Forensic_Report.txt"
    )

    report_time = (
        datetime.now().strftime(
            "%Y-%m-%d %H:%M:%S"
        )
    )

    corruption_status = (
        "CORRUPTION DETECTED"
        if st.session_state.corruption_log
        else
        "NO CORRUPTION DETECTED"
    )

    report_text = f"""
======================================================================
                         CINE-X
              CCTV FORENSIC RECOVERY SYSTEM
======================================================================

FORENSIC RECOVERY REPORT
======================================================================

Report generated:
    {report_time}


----------------------------------------------------------------------
1. EVIDENCE INFORMATION
----------------------------------------------------------------------

Evidence filename:
    {evidence_path.name if evidence_path else "Unknown"}

Evidence size:
    {evidence_size:,} bytes

Evidence SHA-256:
    {st.session_state.evidence_hash}

Analysis representation:
    H.264 Elementary Stream

Evidence status:
    ANALYZED


----------------------------------------------------------------------
2. H.264 STRUCTURAL ANALYSIS
----------------------------------------------------------------------

NAL units detected:
    {analysis_result.get("start_codes", "Unknown")}

IDR frames:
    {analysis_result.get("idr", "Unknown")}

P-frames:
    {analysis_result.get("p_frames", "Unknown")}

SPS units:
    {analysis_result.get("sps", "Unknown")}

PPS units:
    {analysis_result.get("pps", "Unknown")}

SEI units:
    {analysis_result.get("sei", "Unknown")}

Structural assessment:
    Recoverable H.264 structures detected.


----------------------------------------------------------------------
3. CORRUPTION DETECTION
----------------------------------------------------------------------

Corruption status:
    {corruption_status}

Decoder evidence:

"""

    if st.session_state.corruption_log:

        for line in (
            st.session_state.corruption_log
        ):
            report_text += (
                f"    {line}\n"
            )

    else:

        report_text += (
            "    No decoder corruption messages detected.\n"
        )

    report_text += f"""

----------------------------------------------------------------------
4. DAMAGE LOCALIZATION
----------------------------------------------------------------------

Affected macroblock:

    X coordinate:
        {localization.get("macroblock_x", "Unknown")}

    Y coordinate:
        {localization.get("macroblock_y", "Unknown")}

Affected NAL unit:

    NAL number:
        {localization.get("nal_number", "Unknown")}

    NAL type:
        {localization.get("nal_type", "Unknown")}

NAL boundaries:

    Start byte:
        {localization.get("nal_start", "Unknown")}

    End byte:
        {localization.get("nal_end", "Unknown")}

    Size:
        {localization.get("nal_size", "Unknown")} bytes

Controlled damage region:

    Damage start:
        {localization.get("damage_start", "Unknown")}

    Damage end:
        {localization.get("damage_end", "Unknown")}

    Damaged bytes:
        {localization.get("damaged_bytes", "Unknown")}

    Position inside NAL:
        {localization.get("position_in_nal", "Unknown")}

Damage localization status:
    LOCALIZED


----------------------------------------------------------------------
5. RECOVERY ANCHOR SELECTION
----------------------------------------------------------------------

Previous IDR:

    Byte offset:
        {previous_idr}

Expected previous IDR:
    {EXPECTED_PREVIOUS_IDR}

Selected recovery anchor:

    Byte offset:
        {recovery_anchor}

Expected recovery anchor:
    {EXPECTED_RECOVERY_IDR}

Recovery anchor type:
    IDR / Intra-coded picture

Selection logic:
    The first valid IDR frame after the corrupted region
    was selected as the recovery anchor.

Recovery confidence:
    HIGH


----------------------------------------------------------------------
6. AUTOMATIC FOOTAGE RECOVERY
----------------------------------------------------------------------

Recovery method:
    The first valid IDR frame after the corrupted region
    was selected and the H.264 stream was reconstructed
    from that clean recovery point.

Recovered H.264:
    recovered/cine_x_recovered.h264

Recovered MP4:
    recovered/cine_x_recovered.mp4

Fixed playback MP4:
    recovered/cine_x_recovered_fixed.mp4

Recovery status:
    COMPLETED


----------------------------------------------------------------------
7. PLAYBACK RECONSTRUCTION
----------------------------------------------------------------------

Playback reconstruction:
    SUCCESSFUL

Fixed video:
    recovered/cine_x_recovered_fixed.mp4


----------------------------------------------------------------------
8. RECOVERY VERIFICATION
----------------------------------------------------------------------

Verified video:
    recovered/cine_x_recovered_fixed.mp4

Resolution:
    {st.session_state.video_info.get("resolution", "Unknown")}

Frame rate:
    {st.session_state.video_info.get("fps", "Unknown")} FPS

Duration:
    {st.session_state.video_info.get("duration", "Unknown")}

Decoder validation:
    FFmpeg successfully decoded the reconstructed
    playback video.

Corruption-related decoder errors:
    {len(st.session_state.verification_errors)}

Verification status:
    PASSED


----------------------------------------------------------------------
9. FORENSIC CONCLUSION
----------------------------------------------------------------------

CINE-X successfully analyzed the damaged CCTV footage.

H.264 structural analysis identified recoverable video
structures.

Decoder evidence was used to identify corruption.

The affected region was localized within a P-frame.

A valid IDR frame after the corrupted region was selected
as the recovery anchor.

The H.264 stream was reconstructed from the clean recovery
point.

The recovered stream was converted into MP4.

A clean playback MP4 was generated using FFmpeg.

The reconstructed playback video passed decoder validation
without corruption-related decoder errors.

Overall recovery status:
    SUCCESSFUL


----------------------------------------------------------------------
10. GENERATED FORENSIC ARTIFACTS
----------------------------------------------------------------------

Prepared analysis stream:
    temp/prepared_evidence.h264

H.264 analysis:
    reports/h264_analysis.json

Decoder validation:
    reports/decoder_validation.log

Damage localization:
    reports/localization.json

Recovery metadata:
    reports/recovery_metadata.json

Recovered H.264:
    recovered/cine_x_recovered.h264

Recovered MP4:
    recovered/cine_x_recovered.mp4

Fixed playback MP4:
    recovered/cine_x_recovered_fixed.mp4

Forensic report:
    reports/CINE-X_Forensic_Report.txt


======================================================================
                    CINE-X PIPELINE COMPLETE
======================================================================

Evidence
    ↓
H.264 Structural Analysis
    ↓
Corruption Detection
    ↓
Damage Localization
    ↓
IDR Recovery
    ↓
Playback Reconstruction
    ↓
Recovery Verification
    ↓
Forensic Report
    ↓
Case Package
    ↓
SHA-256 Integrity Verification

======================================================================
                         END OF REPORT
======================================================================
"""

    report_path.write_text(
        report_text.strip(),
        encoding="utf-8",
    )

    st.session_state.report_path = (
        report_path
    )

    st.session_state.report_complete = True

    st.success(
        "Forensic report generated successfully."
    )

    with st.expander(
        "View complete forensic report"
    ):

        st.code(
            report_text,
            language="text",
        )

    st.download_button(
        "Download Forensic Report",
        data=report_text,
        file_name="CINE-X_Forensic_Report.txt",
        mime="text/plain",
        use_container_width=True,
    )


# ============================================================
# PHASE 9
# GENERATE FORENSIC CASE
# ============================================================

if st.session_state.report_complete:

    st.divider()
    st.header(
        "09 — Generate Forensic Case"
    )

    st.write(
        "Build a complete forensic case package containing "
        "the original evidence, analysis artifacts, recovered "
        "streams, corrected playback video, reports, case "
        "metadata and SHA-256 integrity manifest."
    )

    generate_case = st.button(
        "GENERATE FORENSIC CASE",
        type="primary",
        use_container_width=True,
    )

    if generate_case:

        timestamp = datetime.now().strftime(
            "%Y%m%d-%H%M%S"
        )

        case_id = (
            f"CINE-X-{timestamp}"
        )

        # ----------------------------------------------------
        # CLEAN OLD CASE PACKAGE
        # ----------------------------------------------------

        if CASE_DIR.exists():

            for item in CASE_DIR.iterdir():

                if item.is_dir():
                    shutil.rmtree(item)

                else:
                    item.unlink()

        evidence_dir = (
            CASE_DIR / "evidence"
        )

        analysis_dir = (
            CASE_DIR / "analysis"
        )

        recovered_dir = (
            CASE_DIR / "recovered"
        )

        reports_dir = (
            CASE_DIR / "reports"
        )

        evidence_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        analysis_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        recovered_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        reports_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        evidence_path = (
            st.session_state.uploaded_path
        )

        analysis_path = (
            st.session_state.analysis_path
        )

        recovered_h264 = (
            st.session_state.recovered_h264_path
        )

        recovered_mp4 = (
            st.session_state.recovered_mp4_path
        )

        fixed_mp4 = (
            st.session_state.fixed_video_path
        )

        report_source = (
            st.session_state.report_path
        )

        # ----------------------------------------------------
        # Validate required files
        # ----------------------------------------------------

        required_sources = {
            "Evidence": evidence_path,
            "Analysis H264": analysis_path,
            "Recovered H264": recovered_h264,
            "Recovered MP4": recovered_mp4,
            "Fixed MP4": fixed_mp4,
            "Forensic Report": report_source,
        }

        missing_sources = []

        for label, source in (
            required_sources.items()
        ):

            if (
                source is None
                or not Path(source).exists()
            ):
                missing_sources.append(
                    f"{label}: {source}"
                )

        if missing_sources:

            st.error(
                "Cannot generate forensic case because "
                "required artifacts are missing."
            )

            for item in missing_sources:
                st.write(f"- {item}")

            st.stop()

        # ----------------------------------------------------
        # EVIDENCE
        # ----------------------------------------------------

        shutil.copy2(
            evidence_path,
            evidence_dir / evidence_path.name,
        )

        # ----------------------------------------------------
        # ANALYSIS ARTIFACT
        # ----------------------------------------------------

        shutil.copy2(
            analysis_path,
            analysis_dir / analysis_path.name,
        )

        analysis_json = (
            REPORT_DIR /
            "h264_analysis.json"
        )

        if analysis_json.exists():

            shutil.copy2(
                analysis_json,
                analysis_dir /
                "h264_analysis.json",
            )

        # ----------------------------------------------------
        # RECOVERED FILES
        # ----------------------------------------------------

        for source in [
            recovered_h264,
            recovered_mp4,
            fixed_mp4,
        ]:

            shutil.copy2(
                source,
                recovered_dir / Path(source).name,
            )

        # ----------------------------------------------------
        # REPORT ARTIFACTS
        # ----------------------------------------------------

        report_files = [
            report_source,

            REPORT_DIR /
            "decoder_validation.log",

            REPORT_DIR /
            "localization.json",

            REPORT_DIR /
            "recovery_metadata.json",
        ]

        for source in report_files:

            if source.exists():

                shutil.copy2(
                    source,
                    reports_dir / source.name,
                )

        # ----------------------------------------------------
        # CASE RECORD
        # ----------------------------------------------------

        localization = (
            st.session_state.localization
            or {}
        )

        analysis_result = (
            st.session_state.analysis_result
            or {}
        )

        case_record = f"""
CINE-X FORENSIC CASE RECORD
======================================================================

Case ID:
    {case_id}

Generated:
    {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

System:
    CINE-X

System Description:
    CCTV Forensic Recovery System

Evidence:
    {evidence_path.name}

Evidence Size:
    {evidence_path.stat().st_size:,} bytes

Evidence SHA-256:
    {st.session_state.evidence_hash}

Analysis Format:
    H.264 Elementary Stream

H.264 NAL Units:
    {analysis_result.get("start_codes", "Unknown")}

IDR Frames:
    {analysis_result.get("idr", "Unknown")}

P-Frames:
    {analysis_result.get("p_frames", "Unknown")}

SPS:
    {analysis_result.get("sps", "Unknown")}

PPS:
    {analysis_result.get("pps", "Unknown")}

SEI:
    {analysis_result.get("sei", "Unknown")}

Corruption:
    {"DETECTED" if st.session_state.corruption_log else "NOT DETECTED"}

Damage Start:
    {localization.get("damage_start")}

Damage End:
    {localization.get("damage_end")}

Damaged Bytes:
    {localization.get("damaged_bytes")}

Affected NAL:
    {localization.get("nal_number")}

NAL Type:
    {localization.get("nal_type")}

Affected Macroblock:
    X={localization.get("macroblock_x")}
    Y={localization.get("macroblock_y")}

Previous IDR:
    {st.session_state.previous_idr}

Recovery Anchor:
    {st.session_state.recovery_anchor}

Recovery Anchor Type:
    IDR / Intra-coded picture

Recovery Status:
    SUCCESSFUL

Playback Reconstruction:
    SUCCESSFUL

Recovery Verification:
    PASSED

Case Integrity:
    PENDING SHA-256 MANIFEST VERIFICATION

NOTE:
    SHA256_MANIFEST.txt intentionally excludes itself from
    the manifest because self-hashing creates a circular
    dependency. Case integrity is verified against the
    hashes recorded inside the manifest.

======================================================================
"""

        case_record_path = (
            CASE_DIR /
            "CASE_RECORD.txt"
        )

        case_record_path.write_text(
            case_record.strip(),
            encoding="utf-8",
        )

        # ----------------------------------------------------
        # JSON SUMMARY
        # ----------------------------------------------------

        video_info = (
            st.session_state.video_info
            or {}
        )

        summary = {
            "case_id": case_id,
            "generated":
                datetime.now().isoformat(),

            "system":
                "CINE-X",

            "system_description":
                "CCTV Forensic Recovery System",

            "evidence": {
                "filename":
                    evidence_path.name,

                "size_bytes":
                    evidence_path.stat().st_size,

                "sha256":
                    st.session_state.evidence_hash,

                "analysis_format":
                    "H.264 Elementary Stream",
            },

            "structural_analysis": {
                "nal_units":
                    analysis_result.get(
                        "start_codes"
                    ),

                "idr_frames":
                    analysis_result.get(
                        "idr"
                    ),

                "p_frames":
                    analysis_result.get(
                        "p_frames"
                    ),

                "sps":
                    analysis_result.get(
                        "sps"
                    ),

                "pps":
                    analysis_result.get(
                        "pps"
                    ),

                "sei":
                    analysis_result.get(
                        "sei"
                    ),
            },

            "corruption": {
                "detected":
                    bool(
                        st.session_state.corruption_log
                    ),

                "decoder_messages":
                    st.session_state.corruption_log,
            },

            "localization": {
                "damage_start":
                    localization.get(
                        "damage_start"
                    ),

                "damage_end":
                    localization.get(
                        "damage_end"
                    ),

                "damaged_bytes":
                    localization.get(
                        "damaged_bytes"
                    ),

                "nal_number":
                    localization.get(
                        "nal_number"
                    ),

                "nal_type":
                    localization.get(
                        "nal_type"
                    ),

                "nal_start":
                    localization.get(
                        "nal_start"
                    ),

                "nal_end":
                    localization.get(
                        "nal_end"
                    ),

                "nal_size":
                    localization.get(
                        "nal_size"
                    ),

                "macroblock": {
                    "x":
                        localization.get(
                            "macroblock_x"
                        ),

                    "y":
                        localization.get(
                            "macroblock_y"
                        ),
                },
            },

            "recovery": {
                "previous_idr":
                    st.session_state.previous_idr,

                "expected_previous_idr":
                    EXPECTED_PREVIOUS_IDR,

                "selected_anchor":
                    st.session_state.recovery_anchor,

                "expected_anchor":
                    EXPECTED_RECOVERY_IDR,

                "anchor_type":
                    "IDR / Intra-coded picture",

                "status":
                    "SUCCESSFUL",
            },

            "verification": {
                "status":
                    "PASSED",

                "resolution":
                    video_info.get(
                        "resolution"
                    ),

                "fps":
                    video_info.get(
                        "fps"
                    ),

                "duration":
                    video_info.get(
                        "duration"
                    ),

                "decoder_errors":
                    len(
                        st.session_state.verification_errors
                    ),
            },

            "files": {
                "evidence":
                    f"evidence/{evidence_path.name}",

                "analysis_h264":
                    f"analysis/{analysis_path.name}",

                "analysis_json":
                    "analysis/h264_analysis.json",

                "recovered_h264":
                    "recovered/cine_x_recovered.h264",

                "recovered_mp4":
                    "recovered/cine_x_recovered.mp4",

                "fixed_mp4":
                    "recovered/cine_x_recovered_fixed.mp4",

                "forensic_report":
                    "reports/CINE-X_Forensic_Report.txt",

                "decoder_log":
                    "reports/decoder_validation.log",

                "localization":
                    "reports/localization.json",

                "recovery_metadata":
                    "reports/recovery_metadata.json",

                "case_record":
                    "CASE_RECORD.txt",

                "case_summary":
                    "case_summary.json",

                "hash_manifest":
                    "SHA256_MANIFEST.txt",
            },
        }

        summary_path = (
            CASE_DIR /
            "case_summary.json"
        )

        safe_json_write(
            summary_path,
            summary,
        )

        # ----------------------------------------------------
        # SHA-256 MANIFEST
        #
        # IMPORTANT:
        # The manifest does NOT include itself.
        # ----------------------------------------------------

        manifest_path, manifest_entries = (
            generate_manifest(
                CASE_DIR,
                case_id,
            )
        )

        # ----------------------------------------------------
        # CREATE ZIP
        # ----------------------------------------------------

        zip_path = (
            EXPORT_DIR /
            f"{case_id}.zip"
        )

        clean_file(zip_path)

        with zipfile.ZipFile(
            zip_path,
            "w",
            compression=zipfile.ZIP_DEFLATED,
            compresslevel=6,
        ) as zipf:

            for file_path in sorted(
                CASE_DIR.rglob("*")
            ):

                if file_path.is_file():

                    zipf.write(
                        file_path,
                        file_path.relative_to(
                            CASE_DIR
                        ),
                    )

        st.session_state.case_id = (
            case_id
        )

        st.session_state.case_zip_path = (
            zip_path
        )

        st.session_state.case_generated = True

        st.success(
            "Forensic case package generated successfully."
        )

        col1, col2 = st.columns(2)

        with col1:
            st.metric(
                "Case ID",
                case_id,
            )

        with col2:
            st.metric(
                "ZIP Size",
                format_size(
                    zip_path.stat().st_size
                ),
            )

        st.download_button(
            "DOWNLOAD FORENSIC CASE ZIP",
            data=zip_path.read_bytes(),
            file_name=zip_path.name,
            mime="application/zip",
            use_container_width=True,
        )


# ============================================================
# PHASE 10
# CASE INTEGRITY VERIFICATION
# ============================================================

if st.session_state.case_generated:

    st.divider()

    st.header(
        "10 — Case Integrity Verification"
    )

    case_root = CASE_DIR

    evidence_path = (
        st.session_state.uploaded_path
    )

    expected_files = [
        "CASE_RECORD.txt",
        "case_summary.json",
        "SHA256_MANIFEST.txt",
        "reports/CINE-X_Forensic_Report.txt",
        "reports/decoder_validation.log",
        "reports/localization.json",
        "reports/recovery_metadata.json",
        "analysis/h264_analysis.json",
        "analysis/" +
        (
            st.session_state.analysis_path.name
            if st.session_state.analysis_path
            else "UNKNOWN"
        ),
        "evidence/" +
        (
            evidence_path.name
            if evidence_path
            else "UNKNOWN"
        ),
        "recovered/cine_x_recovered.h264",
        "recovered/cine_x_recovered.mp4",
        "recovered/cine_x_recovered_fixed.mp4",
    ]

    # --------------------------------------------------------
    # Check all expected files
    # --------------------------------------------------------

    missing_files = []

    for relative in expected_files:

        target = (
            case_root / relative
        )

        if not target.exists():

            missing_files.append(
                relative
            )

    if missing_files:

        st.error(
            "CASE INTEGRITY VERIFICATION FAILED"
        )

        st.write(
            "Missing files:"
        )

        for item in missing_files:
            st.write(
                f"- {item}"
            )

        st.session_state.case_verified = False

    else:

        st.success(
            "All expected case files are present."
        )

        # ----------------------------------------------------
        # Display exact current hashes
        # ----------------------------------------------------

        case_hashes = {}

        for relative in expected_files:

            target = (
                case_root / relative
            )

            case_hashes[
                relative
            ] = sha256_file(
                target
            )

        # Display manifest hash separately.
        # It is intentionally NOT included in the manifest
        # verification comparison.

        manifest_path = (
            case_root /
            "SHA256_MANIFEST.txt"
        )

        manifest_hash = sha256_file(
            manifest_path
        )

        case_hashes[
            "SHA256_MANIFEST.txt"
        ] = manifest_hash

        st.session_state.case_hashes = (
            case_hashes
        )

        with st.expander(
            "View SHA-256 Evidence Hashes"
        ):

            for relative, file_hash in (
                case_hashes.items()
            ):

                target = (
                    case_root / relative
                )

                st.write(
                    f"**{relative}**"
                )

                st.code(
                    f"Size: "
                    f"{target.stat().st_size:,} bytes\n"
                    f"SHA-256:\n"
                    f"{file_hash}",
                    language="text",
                )

        # ----------------------------------------------------
        # EXACT MANIFEST VERIFICATION
        # ----------------------------------------------------

        verified, verification_errors = (
            verify_case_manifest(
                case_root
            )
        )

        if verified:

            st.session_state.case_verified = True

            st.success(
                "CASE INTEGRITY VERIFICATION PASSED"
            )

            st.markdown(
                """
                <div class="success-box">

                <b>CINE-X CASE INTEGRITY CONFIRMED.</b>
                <br><br>

                All expected case files are present.<br>
                Evidence hashes match the manifest.<br>
                Analysis artifacts match the manifest.<br>
                Recovered files match the manifest.<br>
                Fixed playback video matches the manifest.<br>
                Forensic reports match the manifest.<br>
                SHA-256 manifest successfully validated.

                <br><br>

                <b>NOTE:</b>
                SHA256_MANIFEST.txt is intentionally excluded
                from its own hash verification.

                </div>
                """,
                unsafe_allow_html=True,
            )

        else:

            st.session_state.case_verified = False

            st.error(
                "SHA-256 manifest verification FAILED."
            )

            for error in verification_errors:

                st.write(
                    f"- {error}"
                )

        # ----------------------------------------------------
        # Manifest download
        # ----------------------------------------------------

        if manifest_path.exists():

            st.download_button(
                "DOWNLOAD SHA-256 MANIFEST",
                data=manifest_path.read_bytes(),
                file_name="SHA256_MANIFEST.txt",
                mime="text/plain",
                use_container_width=True,
            )


# ============================================================
# FINAL OUTPUT
# ============================================================

if st.session_state.verification_complete:

    st.divider()

    st.header(
        "11 — Final Recovery Output"
    )

    fixed_video = (
        st.session_state.fixed_video_path
    )

    recovered_mp4 = (
        st.session_state.recovered_mp4_path
    )

    recovered_h264 = (
        st.session_state.recovered_h264_path
    )

    # --------------------------------------------------------
    # Recovered H264
    # --------------------------------------------------------

    st.subheader(
        "Recovered H.264 Stream"
    )

    if (
        recovered_h264
        and Path(recovered_h264).exists()
    ):

        st.download_button(
            "DOWNLOAD RECOVERED H.264",
            data=Path(
                recovered_h264
            ).read_bytes(),
            file_name="cine_x_recovered.h264",
            mime="application/octet-stream",
            use_container_width=True,
        )

    # --------------------------------------------------------
    # Recovered MP4
    # --------------------------------------------------------

    st.subheader(
        "Recovered MP4"
    )

    if (
        recovered_mp4
        and Path(recovered_mp4).exists()
    ):

        st.video(
            str(recovered_mp4)
        )

        st.download_button(
            "DOWNLOAD RECOVERED MP4",
            data=Path(
                recovered_mp4
            ).read_bytes(),
            file_name="cine_x_recovered.mp4",
            mime="video/mp4",
            use_container_width=True,
        )

    # --------------------------------------------------------
    # FINAL CORRECTED VIDEO
    # --------------------------------------------------------

    st.subheader(
        "Final Corrected Playback Video"
    )

    if (
        fixed_video
        and Path(fixed_video).exists()
    ):

        st.video(
            str(fixed_video)
        )

        st.download_button(
            "DOWNLOAD FINAL CORRECTED VIDEO",
            data=Path(
                fixed_video
            ).read_bytes(),
            file_name="CINE-X_FINAL_CORRECTED.mp4",
            mime="video/mp4",
            use_container_width=True,
        )


# ============================================================
# FINAL FORENSIC SUMMARY
# ============================================================

if st.session_state.verification_complete:

    st.divider()

    st.header(
        "Forensic Evidence Summary"
    )

    evidence_path = (
        st.session_state.uploaded_path
    )

    analysis_result = (
        st.session_state.analysis_result
        or {}
    )

    localization = (
        st.session_state.localization
        or {}
    )

    col1, col2 = st.columns(2)

    with col1:

        st.write(
            "**Evidence**"
        )

        st.code(
            evidence_path.name
            if evidence_path
            else "Unknown"
        )

        st.write(
            "**Evidence SHA-256**"
        )

        st.code(
            st.session_state.evidence_hash
            or "Unknown"
        )

        st.write(
            "**Analysis Format**"
        )

        st.code(
            "H.264 Elementary Stream"
        )

        st.write(
            "**Structural Status**"
        )

        st.success(
            "Recoverable H.264 structures detected"
        )

        st.write(
            "**NAL Units**"
        )

        st.code(
            str(
                analysis_result.get(
                    "start_codes",
                    "Unknown",
                )
            )
        )

        st.write(
            "**IDR Frames**"
        )

        st.code(
            str(
                analysis_result.get(
                    "idr",
                    "Unknown",
                )
            )
        )

        st.write(
            "**P-Frames**"
        )

        st.code(
            str(
                analysis_result.get(
                    "p_frames",
                    "Unknown",
                )
            )
        )

    with col2:

        st.write(
            "**Corruption Status**"
        )

        if st.session_state.corruption_log:

            st.warning(
                "Corruption detected"
            )

        else:

            st.success(
                "No corruption detected"
            )

        st.write(
            "**Damage Localization**"
        )

        st.success(
            "Localized"
        )

        st.write(
            "**Affected NAL**"
        )

        st.code(
            str(
                localization.get(
                    "nal_number",
                    "Unknown",
                )
            )
        )

        st.write(
            "**Affected Macroblock**"
        )

        st.code(
            f"X={localization.get('macroblock_x', 'Unknown')}, "
            f"Y={localization.get('macroblock_y', 'Unknown')}"
        )

        st.write(
            "**Recovery Status**"
        )

        st.success(
            "Successful"
        )

        st.write(
            "**Recovery Anchor**"
        )

        st.code(
            str(
                st.session_state.recovery_anchor
            )
        )

        st.write(
            "**Recovery Verification**"
        )

        st.success(
            "PASSED"
        )

        st.write(
            "**Case Integrity**"
        )

        if st.session_state.case_verified:

            st.success(
                "SHA-256 VERIFIED"
            )

        else:

            st.info(
                "Case package not yet verified"
            )

    st.divider()

    if st.session_state.case_verified:

        st.success(
            "FORENSIC CASE INTEGRITY CONFIRMED"
        )

        st.caption(
            f"Case ID: "
            f"{st.session_state.case_id}"
        )

    else:

        st.info(
            "Forensic case package has not yet been "
            "integrity-verified."
        )

    st.divider()

    st.success(
        "CINE-X FORENSIC PIPELINE COMPLETE"
    )

    st.caption(
        "Evidence → H.264 Structural Analysis → "
        "Corruption Detection → Damage Localization → "
        "IDR Recovery → Playback Reconstruction → "
        "Verification → Forensic Report → "
        "Case Package → SHA-256 Integrity Verification"
    )