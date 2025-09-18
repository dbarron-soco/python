"""
Cisco Syslog Parser (Improved)

- Robust prefix parsing for: seq, month, day, time, timezone, facility, severity, mnemonic, message
- Extensible event extractors for common Cisco events (ACL permits/denies, login, logout, link/line protocol, config, commands)
- CLI with filtering and multiple output formats
- Summary analytics (counts by event type/mnemonic/severity, top failed-login sources, interface flaps, ACL deny summary)

Usage examples:
  python log_parser_improved.py -i cisco_sample_100.txt --summary
  python log_parser_improved.py -i cisco_sample_100.txt -o parsed.csv --format csv
  python log_parser_improved.py -i cisco_sample_100.txt --filter-mnemonic IPACCESSLOGP --filter-severity 4 5

Note: Cisco logs in samples don't include a year. You may supply --year to construct full datetimes.
"""
from __future__ import annotations
import argparse
import re
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd

# -----------------
# Regex foundations
# -----------------

# Core prefix pattern for Cisco-style syslog lines seen in sample:
# "1: Sep 18 08:00:01.001 CDT: %LINEPROTO-5-UPDOWN: <message>"
PREFIX_RE = re.compile(
    r"^\s*(?P<seq>\d+):\s+"
    r"(?P<month>Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+"
    r"(?P<day>\d{1,2})\s+"
    r"(?P<time>\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?)\s+"
    r"(?P<tz>[A-Z]{2,5})\s*:\s*"
    r"%(?P<facility>[A-Z0-9_]+)-(?P<severity>\d+)-(?P<mnemonic>[A-Z0-9_]+):\s*"
    r"(?P<message>.*)$"
)

# Severity names per Cisco/syslog
SEVERITY_MAP = {
    0: "EMERGENCY",
    1: "ALERT",
    2: "CRITICAL",
    3: "ERROR",
    4: "WARNING",
    5: "NOTICE",
    6: "INFO",
    7: "DEBUG",
}

# Event-specific extractors. Each returns (event_type, fields_dict) or (None, {}).

def extract_acl_permit(message: str) -> Tuple[Optional[str], Dict[str, str]]:
    # e.g. "list acl-vty-in permitted tcp 32.245.68.191(47424) -> 230.0.0.185(22), 8 packet"
    m = re.search(
        r"list\s+(?P<acl>\S+)\s+(?P<action>permitted|denied)\s+"
        r"(?P<proto>\S+)\s+"
        r"(?P<src_ip>\d+\.\d+\.\d+\.\d+)\((?P<src_port>\d+)\)\s*->\s*"
        r"(?P<dst_ip>\d+\.\d+\.\d+\.\d+)\((?P<dst_port>\d+)\),\s+"
        r"(?P<packets>\d+)\s+packet[s]?",
        message,
    )
    if m:
        d = m.groupdict()
        return (f"acl_{d['action']}", d)
    return (None, {})


def extract_acl_deny_hw(message: str) -> Tuple[Optional[str], Dict[str, str]]:
    # FMANFP hardware path deny with MAC and ingress interface
    # e.g. "list acl-core denied 27 6c:b7:cd:85:0c:e0 186.235.35.107 GigabitEthernet3/1-> 237.0.0.189, 2 packets"
    m = re.search(
        r"list\s+(?P<acl>\S+)\s+denied\s+(?P<proto_code>\d+)\s+"
        r"(?P<src_mac>[0-9a-f]{2}(?::[0-9a-f]{2}){5})\s+"
        r"(?P<src_ip>\d+\.\d+\.\d+\.\d+)\s+"
        r"(?P<ingress_if>\S+)->\s+"
        r"(?P<dst_ip>\d+\.\d+\.\d+\.\d+),\s+"
        r"(?P<packets>\d+)\s+packets",
        message,
        flags=re.IGNORECASE,
    )
    if m:
        d = m.groupdict()
        return ("acl_denied_hw", d)
    return (None, {})


def extract_link_state(message: str) -> Tuple[Optional[str], Dict[str, str]]:
    # LINK-*-UPDOWN and LINEPROTO-*-UPDOWN formats
    m = re.search(r"Interface\s+(?P<interface>\S+),\s+changed state to\s+(?P<state>\w+)", message)
    if m:
        return ("link_state", m.groupdict())
    m2 = re.search(
        r"Line protocol on Interface\s+(?P<interface>\S+),\s+changed state to\s+(?P<state>\w+)",
        message,
    )
    if m2:
        return ("lineproto_state", m2.groupdict())
    return (None, {})


def extract_login_success(message: str) -> Tuple[Optional[str], Dict[str, str]]:
    m = re.search(r"Login Success \[user:\s*(?P<user>.+?)\]\s*\[Source:\s*(?P<src_ip>\d+\.\d+\.\d+\.\d+)\]", message)
    if m:
        return ("login_success", m.groupdict())
    return (None, {})


def extract_login_failed(message: str) -> Tuple[Optional[str], Dict[str, str]]:
    m = re.search(
        r"Login failed \[user:\s*(?P<user>.+?)\]\s*\[Source:\s*(?P<src_ip>\d+\.\d+\.\d+\.\d+)\]\s*\[Reason:\s*(?P<reason>.+?)\]",
        message,
    )
    if m:
        return ("login_failed", m.groupdict())
    return (None, {})


def extract_logout(message: str) -> Tuple[Optional[str], Dict[str, str]]:
    m = re.search(r"User\s+(?P<user>\S+)\s+has exited tty session\s+\d+\((?P<src_ip>\d+\.\d+\.\d+\.\d+)\)", message)
    if m:
        return ("logout", m.groupdict())
    return (None, {})


def extract_config(message: str) -> Tuple[Optional[str], Dict[str, str]]:
    m = re.search(
        r"Configured from console by\s+(?P<user>\S+)\s+on\s+(?P<line>\S+)\s+\((?P<src_ip>\d+\.\d+\.\d+\.\d+)\)",
        message,
    )
    if m:
        return ("config_from_console", m.groupdict())
    return (None, {})


def extract_logged_cmd(message: str) -> Tuple[Optional[str], Dict[str, str]]:
    m = re.search(r"User:(?P<user>\S+)\s+logged command:(?P<command>.+)$", message)
    if m:
        d = m.groupdict()
        # normalize command (strip leading markers like !exec: )
        d["command"] = d["command"].strip()
        return ("logged_command", d)
    return (None, {})


EXTRACTORS = [
    extract_acl_permit,
    extract_acl_deny_hw,
    extract_link_state,
    extract_login_success,
    extract_login_failed,
    extract_logout,
    extract_config,
    extract_logged_cmd,
]


@dataclass
class ParsedLine:
    seq: Optional[int] = None
    month: Optional[str] = None
    day: Optional[int] = None
    time: Optional[str] = None
    tz: Optional[str] = None
    facility: Optional[str] = None
    severity: Optional[int] = None
    severity_name: Optional[str] = None
    mnemonic: Optional[str] = None
    message: Optional[str] = None
    event_type: Optional[str] = None
    # Dict for dynamic fields
    fields: Dict[str, str] = None
    # Optional full datetime if --year provided
    dt: Optional[datetime] = None


MONTH_MAP = {
    "Jan": 1,
    "Feb": 2,
    "Mar": 3,
    "Apr": 4,
    "May": 5,
    "Jun": 6,
    "Jul": 7,
    "Aug": 8,
    "Sep": 9,
    "Oct": 10,
    "Nov": 11,
    "Dec": 12,
}


def parse_line(line: str, *, year: Optional[int] = None) -> Optional[ParsedLine]:
    m = PREFIX_RE.search(line)
    if not m:
        return None
    gd = m.groupdict()
    try:
        seq = int(gd["seq"]) if gd.get("seq") else None
        severity = int(gd["severity"]) if gd.get("severity") else None
    except ValueError:
        seq = None
        severity = None
    severity_name = SEVERITY_MAP.get(severity)

    dt = None
    if year is not None:
        # Build datetime with provided year (timezone kept as string, not applied)
        month_num = MONTH_MAP.get(gd["month"], 1)
        # time may include fractional seconds
        time_str = gd["time"]
        fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in time_str else "%Y-%m-%d %H:%M:%S"
        dt_str = f"{year}-{month_num:02d}-{int(gd['day']):02d} {time_str}"
        try:
            dt = datetime.strptime(dt_str, fmt)
        except Exception:
            dt = None

    parsed = ParsedLine(
        seq=seq,
        month=gd.get("month"),
        day=int(gd["day"]) if gd.get("day") else None,
        time=gd.get("time"),
        tz=gd.get("tz"),
        facility=gd.get("facility"),
        severity=severity,
        severity_name=severity_name,
        mnemonic=gd.get("mnemonic"),
        message=gd.get("message"),
        fields={},
        dt=dt,
    )

    # Run extractors to enrich
    for extractor in EXTRACTORS:
        etype, fields = extractor(parsed.message or "")
        if etype:
            parsed.event_type = etype
            parsed.fields = fields
            break

    return parsed


def parse_file(path: str, *, year: Optional[int] = None) -> List[ParsedLine]:
    results: List[ParsedLine] = []
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            pl = parse_line(line, year=year)
            if pl:
                results.append(pl)
    return results


def to_dataframe(rows: List[ParsedLine]) -> pd.DataFrame:
    base_records: List[Dict] = []
    for r in rows:
        base = {
            "seq": r.seq,
            "month": r.month,
            "day": r.day,
            "time": r.time,
            "tz": r.tz,
            "facility": r.facility,
            "severity": r.severity,
            "severity_name": r.severity_name,
            "mnemonic": r.mnemonic,
            "event_type": r.event_type,
            "message": r.message,
            "dt": r.dt,
        }
        # merge dynamic fields with prefix 'f_'
        if r.fields:
            for k, v in r.fields.items():
                base[f"f_{k}"] = v
        base_records.append(base)

    df = pd.DataFrame.from_records(base_records)
    return df


# -----------------
# Summaries
# -----------------

def summarize(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    summaries: Dict[str, pd.DataFrame] = {}
    if df.empty:
        return summaries

    # Counts by event_type / mnemonic / severity
    for col in ["event_type", "mnemonic", "severity_name"]:
        if col in df.columns:
            summaries[f"by_{col}"] = df[col].value_counts(dropna=False).rename_axis(col).reset_index(name="count")

    # Top failed login sources
    if "event_type" in df.columns:
        failed = df[df["event_type"] == "login_failed"]
        if not failed.empty and "f_src_ip" in failed.columns:
            top_failed = (
                failed["f_src_ip"].value_counts().rename_axis("src_ip").reset_index(name="failed_logins")
            )
            summaries["top_failed_sources"] = top_failed

    # Interface flaps (link & lineproto)
    flaps = df[df["event_type"].isin(["link_state", "lineproto_state"])].copy()
    if not flaps.empty and "f_interface" in flaps.columns:
        by_iface = flaps.groupby(["event_type", "f_interface", "f_state"]).size().reset_index(name="count")
        summaries["interface_flaps"] = by_iface

    # ACL denies summary (both software and hardware path)
    acl = df[df["event_type"].isin(["acl_denied_hw", "acl_denied", "acl_denied_sw", "acl_denied"])]
    if not acl.empty:
        # Normalize ACL action/name columns
        acl_name_col = "f_acl"
        if acl_name_col in acl.columns:
            acl_summary = acl.groupby(["event_type", acl_name_col]).size().reset_index(name="count")
            summaries["acl_denies"] = acl_summary

    return summaries


# -----------------
# CLI
# -----------------

def apply_filters(df: pd.DataFrame, args: argparse.Namespace) -> pd.DataFrame:
    out = df
    if args.filter_facility:
        out = out[out["facility"].isin(args.filter_facility)]
    if args.filter_mnemonic:
        out = out[out["mnemonic"].isin(args.filter_mnemonic)]
    if args.filter_event_type:
        out = out[out["event_type"].isin(args.filter_event_type)]
    if args.filter_severity:
        out = out[out["severity"].isin(args.filter_severity)]
    if args.filter_interface and "f_interface" in out.columns:
        out = out[out["f_interface"].isin(args.filter_interface)]
    if args.filter_user and "f_user" in out.columns:
        out = out[out["f_user"].isin(args.filter_user)]
    if args.regex and args.regex_field:
        pat = re.compile(args.regex)
        col = args.regex_field
        if col in out.columns:
            out = out[out[col].astype(str).str.contains(pat)]
    return out


def write_output(df: pd.DataFrame, path: Optional[str], fmt: str) -> None:
    if path is None:
        return
    fmt = fmt.lower()
    if fmt == "csv":
        df.to_csv(path, index=False)
    elif fmt == "json":
        df.to_json(path, orient="records", lines=False)
    else:
        raise ValueError("Unsupported format. Choose csv or json.")


def main(argv: Optional[List[str]] = None) -> int:
    p = argparse.ArgumentParser(description="Cisco Syslog Parser (Improved)")
    p.add_argument("-i", "--input", required=True, help="Path to input log file")
    p.add_argument("-y", "--year", type=int, help="Year to apply to parsed timestamps (optional)")
    p.add_argument("-o", "--output", help="Path to write parsed output (optional)")
    p.add_argument("--format", default="csv", choices=["csv", "json"], help="Output format if --output is provided")
    p.add_argument("--summary", action="store_true", help="Print summary tables")

    # Filters
    p.add_argument("--filter-facility", nargs="*", help="Filter by facility (e.g., SEC, SYS)")
    p.add_argument("--filter-mnemonic", nargs="*", help="Filter by mnemonic (e.g., IPACCESSLOGP, UPDOWN)")
    p.add_argument("--filter-event-type", nargs="*", help="Filter by derived event type (e.g., login_failed)")
    p.add_argument("--filter-severity", nargs="*", type=int, help="Filter by numeric severity (0-7)")
    p.add_argument("--filter-interface", nargs="*", help="Filter by interface names")
    p.add_argument("--filter-user", nargs="*", help="Filter by usernames")
    p.add_argument("--regex", help="Regex to match against a specific field (use with --regex-field)")
    p.add_argument("--regex-field", help="Field/column name to run regex against (e.g., message, f_command)")

    args = p.parse_args(argv)

    rows = parse_file(args.input, year=args.year)
    if not rows:
        print("No lines parsed. Check input format/path.")
        return 2
    df = to_dataframe(rows)

    # Apply filters if any
    df_filtered = apply_filters(df, args)

    # Print quick summary
    print(f"Parsed {len(df)} rows. After filters: {len(df_filtered)} rows.")

    # Show sample rows
    with pd.option_context("display.max_columns", None, "display.width", 200):
        print("\nSample parsed rows:")
        print(df_filtered.head(10).to_string(index=False))

    if args.summary:
        sums = summarize(df_filtered)
        for name, sdf in sums.items():
            print(f"\nSummary: {name}")
            print(sdf.to_string(index=False))

    # Write output if requested
    if args.output:
        write_output(df_filtered, args.output, args.format)
        print(f"\nWrote {len(df_filtered)} rows to {args.output} ({args.format}).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
