#!/usr/bin/env python3
"""
Count regions per species in Echoview region files (.evr).

Region type: https://support.echoview.com/WebHelp/Reference/File_Formats/Export_File_Formats/2D_Region_definition_file_format.htm
"0" = bad (no data);
"1" = analysis;
"2" = marker
"3" = fish tracks
"4" = bad (empty water)

Run: python3 scripts/count_species_evr.py your_path_to_the_region_folder --analysis-only

"""

import argparse
import csv
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, asdict
from datetime import date
from pathlib import Path

REGION_TYPES = {
    "0": "bad (no data)",
    "1": "analysis",
    "2": "marker",
    "3": "fishtracks",
    "4": "bad (empty water)",
}
UNCLASSIFIED = {"", "unclassified regions", "unclassified"}
DATE_RE = re.compile(r"^\d{8}$")


@dataclass
class Region:
    file: str
    folder: str
    week: str
    region_id: str
    name: str
    classification: str
    region_type: str
    n_points: int
    start: str
    end: str
    depth_top: str
    depth_bottom: str


def _read_lines(path: Path) -> list[str]:
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    return [ln.rstrip("\r\n") for ln in text.splitlines()]


def _is_points_line(line: str, n_points: int) -> bool:
    """Points line = n_points x (date time depth) followed by the region type code."""
    tok = line.split()
    if len(tok) != 3 * n_points + 1 or n_points < 1:
        return False
    return DATE_RE.match(tok[0]) is not None and tok[-1] in REGION_TYPES


def _iso_week(yyyymmdd: str) -> str:
    try:
        d = date(int(yyyymmdd[:4]), int(yyyymmdd[4:6]), int(yyyymmdd[6:8]))
    except (ValueError, IndexError):
        return ""
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def parse_evr(path: Path, root: Path | None = None) -> list[Region]:
    rel = path.relative_to(root) if root and root in path.parents else Path(path.name)
    folder = str(rel.parent) if str(rel.parent) != "." else ""
    lines = _read_lines(path)
    if not lines or not lines[0].startswith("EVRG"):
        raise ValueError(f"{path.name}: not an Echoview region file (missing EVRG header)")

    try:
        expected = int(lines[1].strip())
    except (IndexError, ValueError):
        expected = None

    regions: list[Region] = []
    i = 2
    n = len(lines)
    while i < n:
        tok = lines[i].split()
        # region header: <structver> <npoints> <id> <selected> <creation type> <dummy> <bbox valid> <bbox x6>
        if len(tok) >= 7 and tok[0].isdigit() and tok[1].isdigit() and (i == 2 or lines[i - 1].strip() == ""):
            n_points = int(tok[1])
            region_id = tok[2]
            bbox = tok[7:13] if len(tok) >= 13 else [""] * 6
            # find the points line, classfication sits above, label below
            j = i + 1
            while j < n and not _is_points_line(lines[j], n_points):
                j += 1
            if j >= n:
                print(f"  warning: {path.name}: region {region_id} has no point list, skipped", file=sys.stderr)
                i += 1
                continue
            classification = lines[j - 1].strip() if j - 1 > i else ""
            name = lines[j + 1].strip() if j + 1 < n else ""
            rtype = lines[j].split()[-1]
            regions.append(Region(
                file=str(rel),
                folder=folder,
                week=_iso_week(bbox[0]),
                region_id=region_id,
                name=name,
                classification=classification,
                region_type=REGION_TYPES.get(rtype, rtype),
                n_points=n_points,
                start=f"{bbox[0]} {bbox[1]}".strip(),
                end=f"{bbox[3]} {bbox[4]}".strip(),
                depth_top=bbox[2],
                depth_bottom=bbox[5],
            ))
            i = j + 2
        else:
            i += 1

    if expected is not None and expected != len(regions):
        print(f"  warning: {path.name}: header says {expected} regions, parsed {len(regions)}", file=sys.stderr)
    return regions


def label_for(r: Region) -> str:
    """Species comes from the region classification; anything unclassified is grouped as 'Unclassified'"""
    if r.classification.strip().lower() in UNCLASSIFIED:
        return "Unclassified"
    return r.classification.strip()


def main() -> int:
    ap = argparse.ArgumentParser(description="Count regions per species in Echoview .evr files.")
    ap.add_argument("path", type=Path, nargs="?", default=Path("data"),
                    help="the folder with the .evr files (default: data/)")
    
    # optional on/off switch: add --analysis-only when running the script to count
    # only region type 1 (analysis) and skip bad data, markers and fish tracks
    ap.add_argument("--analysis-only", action="store_true", help="count only 'analysis' regions")
    ap.add_argument("--out", type=Path, default=Path("data"))    
    args = ap.parse_args()

    # only pull .evr/ .EVR files 
    if not args.path.is_dir():
        print(f"Folder not found: {args.path}", file=sys.stderr)
        return 1
    files = sorted(p for p in args.path.iterdir() if p.suffix.lower() == ".evr")
    if not files:
        print(f"No .evr files found in {args.path}", file=sys.stderr)
        return 1

    # read every region from every file
    all_regions: list[Region] = []
    for f in files:
        try:
            all_regions.extend(parse_evr(f))
        except Exception as e:  # keep going on a bad file
            print(f"  error: {f}: {e}", file=sys.stderr)

    counted = [r for r in all_regions if not args.analysis_only or r.region_type == "analysis"]

    # count regions per species across all files
    totals: Counter[str] = Counter()
    for r in counted:
        totals[label_for(r)] += 1

    # save the counts
    args.out.mkdir(parents=True, exist_ok=True)
    with open(args.out / "Malaspina2025_species_counts.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["species", "n_regions"])
        for sp, c in totals.most_common():
            w.writerow([sp, c])

    # print the summary 
    print(f"\nParsed {len(files)} .evr file(s), {len(all_regions)} region(s); counted {len(counted)}.")
    for sp, c in totals.most_common():
        print(f"{sp}: {c}")

    # what got skipped by --analysis-only by region type and label
    skipped = Counter((r.region_type, label_for(r)) for r in all_regions if r.region_type != "analysis")
    print("\nSkipped:")
    for (rtype, sp), c in skipped.most_common():
        print(f"  {rtype} / {sp}: {c}")


    # list the skipped regions that still have a species label
    print("\nSkipped regions with a species:")
    for r in all_regions:
        if r.region_type != "analysis" and label_for(r) != "Unclassified":
            print(f"  {r.file}  region {r.region_id}  {r.region_type}  {label_for(r)}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())


