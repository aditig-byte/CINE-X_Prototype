# 🎥 CINE-X

**CCTV Forensic Recovery System** — detects, localizes, and recovers corrupted H.264 surveillance footage without inventing a single pixel, then packages the result into a tamper-evident, SHA-256-verified forensic case file.

Built for **SIH26150** — *Development of a Multi-Vendor DVR/NVR Forensic Analysis Tool for Standardized Acquisition, Recovery, and Analysis of Surveillance Evidence* (NTRO, Software Track, Blockchain & Cybersecurity theme).

> **Prototype scope:** this repo implements the corruption-detection, recovery, and chain-of-custody core of the pipeline for H.264 evidence files. Multi-vendor proprietary parsers (Dahua DHFS, Hikvision FS) and the AI cross-camera reasoning layer are architected but not yet in this build — see [Roadmap](#roadmap).

---

## Table of Contents
- [Why This Exists](#why-this-exists)
- [What It Does](#what-it-does)
- [Pipeline Overview](#pipeline-overview)
- [Core Techniques](#core-techniques)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
- [Usage Walkthrough](#usage-walkthrough)
- [Output Artifacts](#output-artifacts)
- [Forensic Integrity Model](#forensic-integrity-model)
- [Known Limitations](#known-limitations)
- [Roadmap](#roadmap)

---

## Why This Exists

CCTV/DVR footage frequently becomes unplayable — power loss mid-write, degraded storage, incomplete transfers, firmware faults — and investigators often write it off as a total loss, even when only a small fraction of the file is actually damaged.

H.264 video isn't one monolithic blob; it's built from independently-parseable units (NAL units). A handful of corrupted bytes usually breaks only *one* structural unit and everything that depends on it — not the entire recording. CINE-X exploits this: find the exact damage boundary, surgically remove only what's unrecoverable, and keep everything else, byte-for-byte.

---

## What It Does

Upload a damaged `.h264` / `.mp4` / `.avi` / `.mkv` file and CINE-X automatically:

1. Normalizes it into a raw H.264 elementary stream
2. Parses every NAL unit and reports the stream's structure
3. Runs a decoder validation pass to capture concrete corruption evidence
4. Statistically localizes the exact corrupted NAL unit (no hardcoded offsets — works on any file)
5. Cuts out only the unrecoverable segment and resumes from the next clean keyframe, producing one continuous recovered video
6. *(Optional)* Generates a separate, clearly-labeled visual "best guess" reconstruction using the decoder's own motion-based error concealment — never treated as evidence
7. Re-verifies the recovered video decodes cleanly
8. Generates a structured forensic report with a quantified recovery breakdown
9. Packages everything into a SHA-256-hashed, tamper-evident case ZIP
10. Re-verifies that package's integrity on demand

---

## Pipeline Overview

```
Evidence Upload
      │
      ▼
01 — Evidence Ingest ──────────── SHA-256 hash on ingest
      │
      ▼
02 — H.264 Structural Analysis ── NAL unit / IDR / P-frame / SPS / PPS / SEI counts
      │
      ▼
03 — Corruption Detection ─────── FFmpeg decoder error log
      │
      ▼
04 — Damage Localization ──────── MAD-based statistical anomaly detection
      │
      ▼
05 — Automatic Footage Recovery ─ Cut-and-resume at next valid IDR
      │
      ▼
06 — Playback Reconstruction ──── Clean, constant-frame-rate MP4
      │
      ├── 06B — Visual Reconstruction Preview (optional, NOT evidence)
      │
      ▼
07 — Recovery Verification ────── Re-decode pass, pass/fail
      │
      ▼
08 — Forensic Report ──────────── Full structured report (.txt + .json)
      │
      ▼
09 — Generate Forensic Case ───── SHA-256 manifest + ZIP package
      │
      ▼
10 — Case Integrity Verification  Re-hash & compare against manifest
      │
      ▼
11 — Final Recovery Output ────── Original / Recovered / Reconstructed comparison
```

---

## Core Techniques

### NAL-level bitstream parsing
Raw byte scanning for H.264 Annex-B start codes (`00 00 01` / `00 00 00 01`); each NAL unit's type is read from the 5 low bits of the header byte (`& 0x1F`) and classified — IDR/keyframe (5), P-frame (1), SPS (7), PPS (8), SEI (6).

### Dual-signal corruption detection
1. **Statistical:** a robust, file-independent anomaly detector — median absolute deviation (MAD) z-score over slice-NAL sizes, with a ratio-test fallback for low-motion/static scenes where MAD collapses to zero.
2. **Decoder-reported:** FFmpeg's own decode-pass error log, cross-referenced for macroblock coordinates when available.

Two independent signals pointing at the same location give much stronger localization confidence than either alone.

### Cut-and-resume recovery
P-frames are differentially encoded against previous frames — if one is corrupted, every frame that depends on it (directly or transitively) is also untrustworthy, until the next IDR resets the chain. CINE-X keeps every clean byte before the damage, discards only the damaged NAL through the next IDR, re-injects fresh SPS/PPS so the resumed segment is independently decodable, and produces **one continuous recovered video** — not a clip truncated at the first sign of trouble.

### Chain of custody
Every artifact is SHA-256 hashed on ingest and again at case packaging. A manifest records every file's expected hash; re-verification re-hashes everything on disk and proves nothing was altered since the case was sealed. (The manifest deliberately excludes its own hash — self-hashing a file whose contents *are* the hashes is a logical impossibility, so this is handled explicitly rather than hand-waved.)

### Honest separation of evidence vs. estimate
The optional visual reconstruction preview uses FFmpeg's built-in decoder error concealment (motion vectors + reference frames already present in the stream — **no AI/ML, nothing invented**). It is clearly labeled "NOT VERIFIED EVIDENCE" everywhere it appears and is excluded from every SHA-256 evidentiary claim.

---

## Tech Stack

| Layer | Technology |
|---|---|
| UI / App framework | [Streamlit](https://streamlit.io/) |
| Video engine | [FFmpeg](https://ffmpeg.org/) (via `subprocess`) |
| Bitstream parsing | Pure Python (`re`, manual byte scanning) — no third-party H.264 parser |
| Statistics | Python's built-in `statistics` module (median, MAD) |
| Integrity | `hashlib` (SHA-256) |
| Packaging | `zipfile` (stdlib) |
| Reporting | Templated plain-text + JSON (`json` stdlib) |

No ML/AI framework, no cloud APIs, no external paid services — every recovery decision is deterministic and explainable, which matters for a tool whose outputs may need to stand up to legal/evidentiary scrutiny.

---

## Project Structure

```
CINE-X/
├── app.py                          # Main Streamlit application
├── ffmpeg.exe                      # (optional) bundled FFmpeg binary
├── recovery/
│   └── analyze_h264.py             # NAL structural analyzer module
├── temp/                           # Scratch space (prepared streams, preview cache)
├── recovered/                      # Pipeline outputs (h264, mp4, fixed mp4, estimate)
├── reports/                        # JSON + text forensic artifacts
├── case_package/                   # Assembled case folder before zipping
└── exports/                        # Final CINE-X-<timestamp>.zip case files
```

All of the above (except `app.py` and `recovery/`) are created automatically on first run.

---

## Getting Started

### Prerequisites
- Python 3.9+
- [FFmpeg](https://ffmpeg.org/download.html) installed and reachable — either on your system `PATH`, at `C:\ffmpeg\bin\ffmpeg.exe`, or bundled as `ffmpeg.exe` alongside `app.py`

### Installation
```bash
git clone https://github.com/<your-username>/cine-x.git
cd cine-x
pip install streamlit
```

### Run
```bash
streamlit run app.py
```
Then open the local URL Streamlit prints (defaults to `http://localhost:8501`).

---

## Usage Walkthrough

1. **Upload** damaged CCTV footage (`.h264`, `.mp4`, `.avi`, or `.mkv`) in **01 — Evidence Ingest**.
2. Click **ANALYZE EVIDENCE** — runs structural analysis, corruption detection, and damage localization in one pass.
3. Click **RECOVER FOOTAGE** — executes the cut-and-resume recovery.
4. *(Optional)* Click **GENERATE RECONSTRUCTION PREVIEW** for the non-evidentiary visual estimate.
5. Review the **Recovery Verification** pass/fail and the generated **Forensic Report**.
6. Click **GENERATE FORENSIC CASE** to produce the SHA-256-manifested case ZIP.
7. Run **Case Integrity Verification** to confirm the package hasn't been tampered with.
8. Compare **Original Evidence / Recovered / Reconstructed** side by side in the final output tabs.

---

## Output Artifacts

| File | Description |
|---|---|
| `cine_x_recovered.h264` | Raw recovered bitstream (clean prefix + SPS/PPS + resumed footage) |
| `cine_x_recovered.mp4` | Recovered stream muxed to MP4 |
| `cine_x_recovered_fixed.mp4` | Constant-frame-rate playback version — the verified deliverable |
| `cine_x_reconstruction_estimate.mp4` | Optional decoder-concealment preview — **not evidence** |
| `CINE-X_Forensic_Report.txt` | Full structured forensic report |
| `SHA256_MANIFEST.txt` | Per-file integrity manifest for the case package |
| `case_summary.json` | Machine-readable case summary |
| `CINE-X-<timestamp>.zip` | Complete exportable case package |

---

## Forensic Integrity Model

```
Ingest ──► SHA-256(original) ──► Recovery (byte-exact subset only) ──► SHA-256(each artifact)
                                                                              │
                                                                              ▼
                                                            SHA256_MANIFEST.txt (excludes itself)
                                                                              │
                                                                              ▼
                                                        Re-hash on demand ──► PASS / FAIL
```

**Guarantee:** every byte in the recovered evidence is a byte from the original file — never generated, interpolated, or inferred. The optional visual estimate is the sole exception, and it is excluded from every hash-verified claim and labeled as non-evidentiary everywhere it's surfaced.

---

## Known Limitations

- Single-region damage detection per analysis pass (the highest-scoring anomaly is localized; multiple unrelated corrupted regions would need iterative re-runs).
- Assumes standard Annex-B H.264 byte-stream structure.
- Raw `.h264` elementary streams carry no timing metadata, so a frame-rate assumption (25fps) is required, matching what any player would need to assume.
- Requires FFmpeg on the host machine.
- This solves *bitstream corruption* recovery, not disk-level file carving from deleted/overwritten sectors — a related but distinct forensic problem.

---

## Roadmap

- [ ] Multi-vendor proprietary file-system parsers (Dahua DHFS, Hikvision FS/HikFS)
- [ ] Raw disk/image ingestion (`.dd`, `.raw`, `.E01` via `pytsk3` / `libewf`)
- [ ] Cross-camera object detection and tracking
- [ ] Temporal alignment across cameras with clock-drift correction
- [ ] Evidence reasoning layer: Observed / Inferred / Conflicted classification with per-claim confidence and frame-level provenance
- [ ] Automated BSA Section 65B legal certificate generation
- [ ] Portable single-executable packaging (PyInstaller) for offline field deployment

---

## Acknowledgments

Built for **Smart India Hackathon 2026**, Problem Statement **SIH26150**, posed by the **National Technical Research Organisation (NTRO)**.
