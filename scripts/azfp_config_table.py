#!/usr/bin/env python3
"""
Note: this script was written entirely by Claude. 
It only extracts settings from the instrument's .XML and .DPL files into tables
for reference.

Build per-month tables of AZFP instrument settings from the .XML and .DPL files.

Expects one folder per month named YYYYMM (e.g. 202503, 202504), each holding that
month's .01A files plus its .XML and .DPL. Point the script at the folder that
contains the month folders:

    python scripts/azfp_config_table.py ~/Desktop/2025-03-01_MalaspinaStrait/2025-03-01_MalaspinaStrait/AZFP/55158/DATA
    python scripts/azfp_config_table.py ~/Desktop/2025-03-01_MalaspinaStrait/2025-03-01_MalaspinaStrait/AZFP/55158/DATA --out some/other/folder

Writes to data/calibration/ by default (created if missing; gitignored, so DFO values never get committed):
  azfp_calibration.csv   month x frequency: the values that turn counts into Sv
  azfp_sampling.csv      month x phase x frequency: ping timing and range/bin geometry
  azfp_deployment.csv    month: instrument, start, depths, sensors, .01A inventory
  azfp_config_report.md  the three tables, plus anything that changes between months
                         and anything where a month's XML and DPL disagree

To add or drop columns, edit the *_COLUMNS lists below. Every key built in
calibration_rows / sampling_rows / deployment_row can go in them.

Standard library only, no installs needed.
"""

import argparse
import csv
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Columns shown in each table, in order. "month" and "file" are always first
CALIBRATION_COLUMNS = [
    "frequency_khz",
    "EL",                 # echo level at detector max (dB)
    "DS",                 # detector slope (dB/count)
    "TVR",                # transmit voltage response (dB)
    "VTX",                # transmit voltage (only the first NumVtx values are used)
    "BP",                 # beam pattern / equivalent beam angle factor
    "pulse_len_us",       # pulse length used in this deployment (part of the Sv equation)
    "min_pulse_len_us",
]

SAMPLING_COLUMNS = [
    "phase",
    "frequency_khz",
    "burst_interval_s",
    "pings_per_burst",
    "ping_period_s",
    "average_burst_pings",
    "seconds_per_record",  # time between pings in the .01A (the CNN/RF time axis)
    "records_per_hour",
    "dig_rate_hz",
    "range_samples",
    "range_averaging_samples",
    "sample_spacing_m",    # c / (2 * dig rate), using the header sound speed
    "bin_size_m",          # sample spacing x averaging samples (the vertical pixel size)
    "n_bins",
    "max_range_m",
    "pulse_res_m",         # c * pulse length / 2, the real vertical resolution
    "lockout_index",
    "lockout_m",           # assumes LockOutIndex counts raw samples, check on an echogram
    "gain",
    "storage_format",
]

DEPLOYMENT_COLUMNS = [
    "serial_number",
    "firmware",
    "frequencies_khz",
    "acquisition_start",   # instrument clock, time zone not stated in the file
    "num_phases",
    "duration_days",
    "sound_speed_header_m_s",
    "instrument_depth_m",  # TxDelay InstrumentDepthHighTide
    "water_depth_m",       # TxDelay WaterDepthHighTide
    "pressure_sensor",
    "dpl_config_line",
    "n_01a_files",
    "first_01a",
    "last_01a",
    "total_01a_gb",
]

MONTH_RE = re.compile(r"^\d{6}$")
NUM_RE = re.compile(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?")


# ---------------------------------------------------------------- helpers

def _num(text):
    """XML/DPL text -> int, float (7 significant digits, as stored) or the stripped string."""
    if text is None:
        return None
    t = text.strip()
    try:
        v = float(t)
    except ValueError:
        return t
    if "." not in t and "e" not in t.lower():
        return int(v)
    v = float(f"{v:.7g}")  # values are float32, so this drops artifacts like 146.1999969
    return int(v) if v.is_integer() and abs(v) < 1e15 else v


def _lead_num(text):
    """First number in a DPL value like '500 us' or '40 kHz (0.0181 m/smpl)'."""
    m = NUM_RE.search(text or "")
    return _num(m.group()) if m else None


def _read_text(path: Path) -> str:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _r(v, nd=4):
    return round(v, nd) if isinstance(v, float) else v


# ---------------------------------------------------------------- XML

def parse_xml(path: Path) -> dict:
    root = ET.fromstring(_read_text(path))

    def get(xpath, el=root):
        node = el.find(xpath)
        return _num(node.text) if node is not None else None

    log = root.find("ULS5_LogConfiguration")
    params = root.find("AZFP_Parameters")

    # calibration, one entry per frequency board
    cal = []
    for f in log.findall("LogAcousticCoefficients/Frequencies/Frequency"):
        n_vtx = get("NumVtx", f) or 1
        vtx = [get(f"VTX{i}", f) for i in range(n_vtx)]
        cal.append({
            "frequency_khz": get("kHz", f),
            "EL": get("EL", f),
            "DS": get("DS", f),
            "TVR": get("TVR", f),
            "VTX": vtx[0] if len(vtx) == 1 else ";".join(str(v) for v in vtx),
            "num_vtx": n_vtx,
            "BP": get("BP", f),
            "min_pulse_len_us": get("MinPulseLen", f),
        })

    # board order, labelled units="hz" in the file but they're kHz
    boards = [_num(b.text) for b in params.findall("Header/Boards/Frequency")]

    phases = []
    for ph in params.findall("Phases/Phase"):
        freqs = []
        for f in ph.findall("Frequencies/Frequency"):
            if get("AcquireFrequency", f) != 1:
                continue
            n = int(f.get("Number"))
            freqs.append({
                "number": n,
                "frequency_khz": boards[n - 1] if n - 1 < len(boards) else None,
                "pulse_len_us": get("PulseLen", f),
                "dig_rate_hz": get("DigRate", f),
                "range_samples": get("RangeSamples", f),
                "range_averaging_samples": get("RangeAveragingSamples", f),
                "lockout_index": get("LockOutIndex", f),
                "gain": get("Gain", f),
                "storage_format": get("StorageFormat", f),
            })
        phases.append({
            "phase": int(ph.get("Number", len(phases) + 1)),
            "start": get("StartDate", ph),
            "duration_s": get("Duration", ph),
            "ping_period_s": get("PingPeriod", ph),
            "burst_interval_s": get("BurstInterval", ph),
            "pings_per_burst": get("PingsPerBurst", ph),
            "average_burst_pings": get("AverageBurstPings", ph),
            "freqs": freqs,
        })

    sensors = log.find("SensorsFlag")
    start = get("Header/StartDate", params)
    return {
        "serial_number": get("SerialNumber", log) or get("AZFP_Version/SerialNumber"),
        "firmware": f"{get('AZFP_Version/Major')}.{get('AZFP_Version/Minor')}",
        "sound_speed": get("Header/SoundSpeed", params),
        "start": datetime.fromtimestamp(start, tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                 if isinstance(start, int) else start,
        "num_phases": get("Header/NumPhases", params),
        "instrument_depth_m": get("TxDelay/InstrumentDepthHighTide", params),
        "water_depth_m": get("TxDelay/WaterDepthHighTide", params),
        "pressure_sensor": sensors.get("PressureSensorInstalled") if sensors is not None else None,
        "cal": cal,
        "phases": phases,
    }


# ---------------------------------------------------------------- DPL

def parse_dpl(path: Path) -> dict:
    """DPL is plain text: 'Key<TAB>value' lines, 'Phase N' blocks, 'Fn Key' per-frequency lines."""
    lines = _read_text(path).splitlines()
    out = {"config_line": lines[0].strip() if lines else "", "fields": {}, "phases": {}}
    phase = None
    for line in lines[1:]:
        s = line.strip()
        if not s or set(s) <= {"-"}:
            continue
        m = re.match(r"^Phase\s+(\d+)$", s)
        if m:
            phase = out["phases"].setdefault(int(m.group(1)), {"fields": {}, "freqs": defaultdict(dict)})
            continue
        if "\t" in s:
            key, val = s.split("\t", 1)
        elif ":" in s:
            key, val = s.split(":", 1)
        else:
            continue
        key, val = key.strip().rstrip(":").strip(), val.strip()
        fm = re.match(r"^F(\d+)\s+(.*)$", key)
        if phase is not None and fm:
            phase["freqs"][int(fm.group(1))][fm.group(2).strip()] = val
        elif phase is not None:
            phase["fields"][key] = val
        else:
            out["fields"][key] = val
    return out


def compare_xml_dpl(x: dict, d: dict) -> list[str]:
    """Return a line for every setting where the XML and DPL disagree."""
    diffs = []

    def check(label, xv, dv):
        if xv is None or dv is None:
            return
        if isinstance(xv, (int, float)) and isinstance(dv, (int, float)):
            if abs(xv - dv) > 1e-6 * max(1, abs(xv)):
                diffs.append(f"{label}: XML {xv} vs DPL {dv}")
        elif str(xv) != str(dv):
            diffs.append(f"{label}: XML {xv} vs DPL {dv}")

    f = d["fields"]
    check("serial number", x["serial_number"], _lead_num(f.get("Unit Serial Number")))
    check("sound speed", x["sound_speed"], _lead_num(f.get("SoundSpeed")))
    check("number of phases", x["num_phases"], _lead_num(f.get("Number of phases")))

    yes_no = {"yes": 1, "no": 0}
    for ph in x["phases"]:
        dp = d["phases"].get(ph["phase"])
        if dp is None:
            diffs.append(f"phase {ph['phase']}: in XML but not in DPL")
            continue
        pf = dp["fields"]
        p = f"phase {ph['phase']}"
        check(f"{p} burst interval", ph["burst_interval_s"], _lead_num(pf.get("Burst Interval")))
        check(f"{p} pings per burst", ph["pings_per_burst"], _lead_num(pf.get("Pings Per Burst")))
        check(f"{p} ping period", ph["ping_period_s"], _lead_num(pf.get("Ping Period")))
        check(f"{p} duration (s)", ph["duration_s"], _lead_num(pf.get("Duration")))
        avg = pf.get("Average Burst Pings", "").strip().lower()
        check(f"{p} average burst pings", ph["average_burst_pings"], yes_no.get(avg, _lead_num(avg)))
        for fr in ph["freqs"]:
            df = dp["freqs"].get(fr["number"], {})
            q = f"{p} F{fr['number']} ({fr['frequency_khz']} kHz)"
            dig = _lead_num(df.get("Dig. Rate"))
            check(f"{q} frequency", fr["frequency_khz"], _lead_num(df.get("Frequency")))
            check(f"{q} pulse length", fr["pulse_len_us"], _lead_num(df.get("Pulse Length")))
            check(f"{q} dig rate (Hz)", fr["dig_rate_hz"], dig * 1000 if dig is not None else None)
            check(f"{q} range samples", fr["range_samples"], _lead_num(df.get("Range Samples")))
            check(f"{q} range averaging", fr["range_averaging_samples"],
                  _lead_num(df.get("Range Averaging Samples")))
            check(f"{q} lockout index", fr["lockout_index"], _lead_num(df.get("LockOutIndex")))
            check(f"{q} storage format", fr["storage_format"], _lead_num(df.get("Storage Format")))
    return diffs


# ---------------------------------------------------------------- rows

def calibration_rows(month, stem, x):
    pulse = {}
    for ph in x["phases"]:
        for fr in ph["freqs"]:
            pulse.setdefault(fr["frequency_khz"], fr["pulse_len_us"])
    return [{"month": month, "file": stem, **c, "pulse_len_us": pulse.get(c["frequency_khz"])}
            for c in x["cal"]]


def sampling_rows(month, stem, x):
    c = x["sound_speed"]
    rows = []
    for ph in x["phases"]:
        ppb, burst = ph["pings_per_burst"] or 1, ph["burst_interval_s"]
        averaged = ph["average_burst_pings"] == 1 or ppb == 1
        recs_per_burst = 1 if averaged else ppb
        for fr in ph["freqs"]:
            spacing = c / (2 * fr["dig_rate_hz"]) if c and fr["dig_rate_hz"] else None
            avg = fr["range_averaging_samples"] or 1
            rows.append({
                "month": month, "file": stem, "phase": ph["phase"],
                "frequency_khz": fr["frequency_khz"],
                "burst_interval_s": burst, "pings_per_burst": ppb,
                "ping_period_s": ph["ping_period_s"],
                "average_burst_pings": ph["average_burst_pings"],
                "seconds_per_record": _r(burst / recs_per_burst, 3) if burst else None,
                "records_per_hour": _r(3600 / burst * recs_per_burst, 1) if burst else None,
                "dig_rate_hz": fr["dig_rate_hz"],
                "range_samples": fr["range_samples"],
                "range_averaging_samples": avg,
                "sample_spacing_m": _r(spacing, 5),
                "bin_size_m": _r(spacing * avg, 4) if spacing else None,
                "n_bins": fr["range_samples"] // avg if fr["range_samples"] else None,
                "max_range_m": _r(spacing * fr["range_samples"], 2) if spacing else None,
                "pulse_res_m": _r(c * fr["pulse_len_us"] * 1e-6 / 2, 3) if c else None,
                "lockout_index": fr["lockout_index"],
                "lockout_m": _r(spacing * fr["lockout_index"], 2) if spacing else None,
                "gain": fr["gain"], "storage_format": fr["storage_format"],
            })
    return rows


def deployment_row(month, stem, x, d, raw_files):
    durations = [p["duration_s"] for p in x["phases"] if isinstance(p["duration_s"], (int, float))]
    names = sorted(p.name for p in raw_files)
    return {
        "month": month, "file": stem,
        "serial_number": x["serial_number"], "firmware": x["firmware"],
        "frequencies_khz": ";".join(str(c["frequency_khz"]) for c in x["cal"]),
        "acquisition_start": x["start"], "num_phases": x["num_phases"],
        "duration_days": _r(sum(durations) / 86400, 2) if durations else None,
        "sound_speed_header_m_s": x["sound_speed"],
        "instrument_depth_m": x["instrument_depth_m"], "water_depth_m": x["water_depth_m"],
        "pressure_sensor": x["pressure_sensor"],
        "dpl_config_line": d["config_line"] if d else "(no DPL)",
        "n_01a_files": len(names),
        "first_01a": names[0] if names else "", "last_01a": names[-1] if names else "",
        "total_01a_gb": _r(sum(p.stat().st_size for p in raw_files) / 1e9, 2),
    }


# ---------------------------------------------------------------- months

def find_months(root: Path) -> list[Path]:
    if MONTH_RE.match(root.name):
        return [root]
    return sorted(p for p in root.iterdir() if p.is_dir() and MONTH_RE.match(p.name))


def files_with(folder: Path, suffix: str) -> list[Path]:
    hits = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() == suffix)
    if not hits:  # fall back to subfolders
        hits = sorted(p for p in folder.rglob("*") if p.is_file() and p.suffix.lower() == suffix)
    return hits


def pair_dpl(xml: Path, dpls: list[Path]) -> Path | None:
    for d in dpls:
        if d.stem.lower() == xml.stem.lower():
            return d
    return dpls[0] if len(dpls) == 1 else None


# ---------------------------------------------------------------- output

def write_csv(path: Path, rows: list[dict], cols: list[str]):
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["month", "file", *cols], extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)


def md_table(rows: list[dict], cols: list[str]) -> str:
    cols = ["month", "file", *cols]
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for r in rows:
        out.append("| " + " | ".join("" if r.get(c) is None else str(r.get(c)) for c in cols) + " |")
    return "\n".join(out)


def month_changes(rows: list[dict], cols: list[str], key_cols: list[str]) -> list[str]:
    """For each frequency/phase, list any column whose value isn't the same in every month."""
    groups = defaultdict(list)
    for r in rows:
        groups[tuple(r.get(k) for k in key_cols)].append(r)
    lines = []
    for key, rs in groups.items():
        label = ", ".join(f"{k}={v}" for k, v in zip(key_cols, key)) or "all"
        for c in cols:
            if c in key_cols or c in ("n_01a_files", "first_01a", "last_01a", "total_01a_gb"):
                continue
            vals = {str(r.get(c)) for r in rs}
            if len(vals) > 1:
                per = ", ".join(f"{r['month']}: {r.get(c)}" for r in rs)
                lines.append(f"- **{c}** ({label}) — {per}")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser(description="Per-month tables of AZFP .XML/.DPL settings.")
    ap.add_argument("root", type=Path, help="folder containing the YYYYMM month folders")
    ap.add_argument("--out", type=Path, default=Path("data/calibration"),
                    help="output folder (default: data/calibration/)")
    args = ap.parse_args()

    root = args.root.expanduser()
    if not root.is_dir():
        print(f"Folder not found: {root}", file=sys.stderr)
        return 1
    months = find_months(root)
    if not months:
        print(f"No YYYYMM month folders in {root}", file=sys.stderr)
        return 1

    cal, samp, dep, problems, mismatches = [], [], [], [], []
    for mdir in months:
        month = mdir.name
        xmls, dpls = files_with(mdir, ".xml"), files_with(mdir, ".dpl")
        raw = files_with(mdir, ".01a")
        if not xmls:
            problems.append(f"- {month}: no .XML file")
            continue
        if not dpls:
            problems.append(f"- {month}: no .DPL file")
        for xml in xmls:
            try:
                x = parse_xml(xml)
            except Exception as e:  # keep going on a bad file
                problems.append(f"- {month}/{xml.name}: could not read XML ({e})")
                continue
            dpl = pair_dpl(xml, dpls)
            d = None
            if dpl:
                try:
                    d = parse_dpl(dpl)
                    for diff in compare_xml_dpl(x, d):
                        mismatches.append(f"- {month} ({xml.name} vs {dpl.name}): {diff}")
                except Exception as e:
                    problems.append(f"- {month}/{dpl.name}: could not read DPL ({e})")
            cal += calibration_rows(month, xml.stem, x)
            samp += sampling_rows(month, xml.stem, x)
            dep.append(deployment_row(month, xml.stem, x, d, raw if len(xmls) == 1 else []))

    args.out.mkdir(parents=True, exist_ok=True)
    write_csv(args.out / "azfp_calibration.csv", cal, CALIBRATION_COLUMNS)
    write_csv(args.out / "azfp_sampling.csv", samp, SAMPLING_COLUMNS)
    write_csv(args.out / "azfp_deployment.csv", dep, DEPLOYMENT_COLUMNS)

    changes = (month_changes(dep, DEPLOYMENT_COLUMNS, [])
               + month_changes(cal, CALIBRATION_COLUMNS, ["frequency_khz"])
               + month_changes(samp, SAMPLING_COLUMNS, ["phase", "frequency_khz"]))
    report = [
        f"# AZFP configuration by month\n\nSource: `{root}`  \n"
        f"Generated {datetime.now():%Y-%m-%d %H:%M} from {len(months)} month folder(s).\n",
        "## Changes between months\n",
        "\n".join(changes) if changes else "None, every month has the same settings.",
        "\n## XML vs DPL disagreements\n",
        "\n".join(mismatches) if mismatches else "None.",
        "\n## Missing or unreadable files\n",
        "\n".join(problems) if problems else "None.",
        "\n## Deployment\n", md_table(dep, DEPLOYMENT_COLUMNS),
        "\n## Calibration\n", md_table(cal, CALIBRATION_COLUMNS),
        "\n## Sampling\n", md_table(samp, SAMPLING_COLUMNS),
        "\n## Notes\n",
        "- Frequencies are labelled Hz in the XML/DPL but are kHz.\n"
        "- `sample_spacing_m`, `bin_size_m`, `max_range_m` and `lockout_m` use the header "
        "sound speed; Echopype recomputes sound speed from temperature, salinity and pressure, "
        "so its depth axis can differ by a few percent.\n"
        "- `lockout_m` assumes LockOutIndex counts raw samples.\n"
        "- `acquisition_start` is the instrument clock; the file doesn't say which time zone.\n",
    ]
    (args.out / "azfp_config_report.md").write_text("\n".join(report) + "\n")

    print(f"{len(months)} month(s): {len(dep)} XML file(s), {len(cal)} calibration row(s)")
    print(f"{len(changes)} change(s) between months, {len(mismatches)} XML/DPL disagreement(s), "
          f"{len(problems)} problem(s)")
    for line in changes + mismatches + problems:
        print(" ", line.lstrip("- ").replace("**", ""))
    print(f"Wrote tables and report to {args.out}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())