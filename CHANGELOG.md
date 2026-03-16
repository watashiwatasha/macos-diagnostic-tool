# Changelog

All notable changes to this project will be documented here.

---

## [2.0.0] — 2025-02-12

### Added
- **Ranked space offenders**: Scans 10+ directories and ranks them by size. Highlights quick cleanup wins (folders over 5GB).
- **Fan & thermal health check**: Reads CPU temperature and system thermal logs. Alerts if temperature exceeds 80°C or 90°C.
- **Smart disk warnings**: Separate alerts for large Downloads, large Cache, and unemptied Trash.
- **Space consumers table**: HTML report now includes a ranked table of top disk space users.
- **CPU temperature display**: Shown in the system info section of the report (if accessible).

### Improved
- Swap usage parsing now correctly reads the `Used` value instead of `Total`.
- HTML report layout is cleaner and more readable.
- Alert messages are more specific and actionable.
- Code style updated (PEP 8 compliant, type hints, consistent quoting).

---

## [1.0.0] — 2025-02-12

### Initial release

- Memory and swap usage monitoring
- GPU memory check (Lightroom-aware)
- Orphan daemon scanner (Cisco, VPN, AnyConnect)
- System Extensions check
- Leftover preference file scanner
- Basic disk space check
- Process anomaly detection (zombie processes, top CPU/memory hogs)
- Network listener check
- Cache size reporting
- HTML + JSON report output
