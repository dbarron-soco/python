# Cisco Syslog Parser

A fast, extensible Python parser for Cisco-style syslog messages. It converts raw log lines into a tidy table you can filter, summarize, and export for further analysis.

> Works great with Catalyst/Nexus sample logs that look like:
>
> `1: Sep 18 08:00:01.001 CDT: %LINEPROTO-5-UPDOWN: Line protocol on Interface GigabitEthernet1/0, changed state to up`

---

## Features

- **Robust envelope parsing**: extracts sequence, month/day/time, timezone, facility, severity, mnemonic, and message.
- **Event enrichment via extractors**: ACL permits/denies (software & hardware path), LOGIN success/failed, LOGOUT, LINK/LINEPROTO UPDOWN, CONFIG_I, and logged commands.
- **CLI filters** for facility, mnemonic, event type, severity, interface, user, and arbitrary regex matches.
- **Summaries**: counts by event/mnemonic/severity, top failed-login sources, interface flaps, ACL deny overview.
- **Export**: CSV or JSON. Optional `--year` to build full datetimes.

---

## Repo Layout

```
.
├── log_parser.py                 # The parser CLI
├── cisco_sample_logfile.txt      # Sample log lines (included)
└── README.md                     # This file
```

> If you prefer the name `log_parser.py`, just rename the script; commands below stay the same except for the filename.

---

## Requirements

- Python **3.9+**
- `pandas`

Install dependencies:

```bash
pip install pandas
# (Optional) For dev tooling: pip install black ruff pytest
```

---

## Quick Start

Run against the included sample file and print summaries:

```bash
python log_parser.py -i cisco_sample_logfile.txt --summary
```

Export parsed rows to CSV:

```bash
python log_parser.py -i cisco_sample_logfile.txt -o parsed.csv --format csv
```

Build full datetimes by supplying a year (since many Cisco logs omit it):

```bash
python log_parser.py -i cisco_sample_logfile.txt --year 2025 -o parsed.json --format json
```

---

## Command-Line Options

```text
-i, --input           Path to input log file (required)
-y, --year            Year to apply to parsed timestamps (optional)
-o, --output          Path to write parsed output (optional)
    --format          Output format if --output is provided: csv | json (default: csv)
    --summary         Print summary tables to stdout

# Filters (chainable)
    --filter-facility   Filter by facility, e.g., SEC SYS LINK LINEPROTO FMANFP
    --filter-mnemonic   Filter by Cisco mnemonic, e.g., IPACCESSLOGP UPDOWN CFGLOG_LOGGEDCMD LOGIN_FAILED
    --filter-event-type Filter by derived event type, e.g., login_failed logged_command link_state lineproto_state acl_denied_hw
    --filter-severity   Filter by numeric severity (0–7)
    --filter-interface  Filter by interface name(s), e.g., GigabitEthernet1/0
    --filter-user       Filter by username(s)
    --regex             Regex pattern to match
    --regex-field       Field/column to run the regex against (e.g., message, f_command)
```

### Examples

Only ACL software-path logs (IPACCESSLOGP) with severities 4–6:
```bash
python log_parser.py -i cisco_sample_logfile.txt \
  --filter-mnemonic IPACCESSLOGP --filter-severity 4 5 6 --summary
```

Only failed logins for a specific user:
```bash
python log_parser.py -i device.log \
  --filter-event-type login_failed --filter-user admin -o failed_admin.csv
```

Search for a specific command in logged commands:
```bash
python log_parser.py -i device.log \
  --filter-event-type logged_command --regex "\\breload\\b" --regex-field f_command
```

---

## Output Schema

Each parsed row contains the standard **envelope** fields:

- `seq` – sequence number (if present)
- `month`, `day`, `time`, `tz` – timestamp parts from the log line
- `facility` – e.g., `SEC`, `SYS`, `LINK`, `LINEPROTO`, `FMANFP`
- `severity` – numeric 0–7 and `severity_name` (EMERGENCY…DEBUG)
- `mnemonic` – e.g., `IPACCESSLOGP`, `UPDOWN`, `CFGLOG_LOGGEDCMD`, `LOGIN_FAILED`, `CONFIG_I`, `LOGOUT`
- `message` – remainder of the line after the `%FAC-<sev>-MNEM:` prefix
- `event_type` – normalized category (e.g., `acl_permitted`, `acl_denied_hw`, `login_failed`, `link_state`, `lineproto_state`, `logged_command`, `config_from_console`, `logout`)
- `dt` – full datetime if `--year` was provided; otherwise `None`

Event‑specific **dynamic fields** (only present when matched) are prefixed with `f_`:

- **ACL (software path)**: `f_acl`, `f_action` (permitted/denied), `f_proto`, `f_src_ip`, `f_src_port`, `f_dst_ip`, `f_dst_port`, `f_packets`
- **ACL (hardware path)**: `f_acl`, `f_proto_code`, `f_src_mac`, `f_src_ip`, `f_ingress_if`, `f_dst_ip`, `f_packets`
- **LINK/LINEPROTO**: `f_interface`, `f_state` (`up`/`down`)
- **Login success/failed**: `f_user`, `f_src_ip`, and `f_reason` (failed only)
- **Logout**: `f_user`, `f_src_ip`
- **Config from console**: `f_user`, `f_line`, `f_src_ip`
- **Logged command**: `f_user`, `f_command`

---

## How it Works

1. **Prefix parsing**: a single regex extracts the common Cisco envelope.
2. **Extractor pass**: a list of small extractor functions inspects the `message` tail. The first one that matches sets `event_type` and adds normalized `f_*` fields.
3. **DataFrame**: rows are assembled into a pandas DataFrame for printing, filtering, summarizing, or exporting.

---

## Extending the Parser (Adding New Events)

Add a new extractor in `log_parser.py` and register it in the `EXTRACTORS` list. Example for OSPF adjacency changes:

```python
def extract_ospf_adj(message: str):
    m = re.search(r"neighbor\\s+(?P<neighbor>\\S+)\\s+from\\s+(?P<from>\\S+)\\s+to\\s+(?P<to>\\S+)", message, re.IGNORECASE)
    if m:
        return ("ospf_adj_change", m.groupdict())
    return (None, {})

# register (order matters: put specific extractors before generic ones)
EXTRACTORS.insert(0, extract_ospf_adj)
```

Guidelines:
- Keep extractors **small and specific**; return `(event_type, fields_dict)` or `(None, {})`.
- Reuse existing field names where possible. New fields should use the `f_` prefix.
- Place more specific extractors **earlier** in the `EXTRACTORS` list so they win over generic ones.

---

## Troubleshooting

- **`error: the following arguments are required: -i/--input`**  
  You ran the script without specifying the input file. Add `-i <path>`.

- **No rows parsed**  
  Your logs might use a different header format (e.g., include hostname or year before the `%FAC-...` prefix). Share a couple of real lines and add a new prefix pattern or a pre‑strip step.

- **Encoding issues**  
  The parser opens files with `encoding='utf-8', errors='ignore'`. If your logs are different, adjust as needed.

- **Timezone handling**  
  The `tz` string is parsed but not applied. If you need tz‑aware datetimes, convert `dt` after export or enhance the script to map TZ abbreviations to IANA zones.

---

## Performance Tips

- For very large files, consider piping through `grep` first or adding a start/end time filter after you adopt a `--year`.
- Export to **CSV** and load into your analytics platform (Splunk/Elastic/Kusto/Power BI). For huge datasets, consider adding a Parquet writer.

---

## Contributing

1. Fork & clone the repo
2. Create a branch: `git checkout -b feat/new-extractor`
3. Add tests/samples where possible
4. Open a PR describing the log patterns you added

---

## License

MIT (or company standard). Update this section as appropriate.

---

## Acknowledgements

Thanks to the sample log (`cisco_sample_logfile.txt`) and the initial pattern ideas for shaping the first set of extractors.
