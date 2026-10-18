# 1. Architecture Diagram — Tracking QA

```mermaid
flowchart TD
    CVAT[CVAT Online: Export XML] --> CLI[track_qa.py CLI]
    BDD[BDD100K MOT JSON] --> CLI
    CLI --> PARSE[parse_cvat / parse_bdd]
    PARSE --> TRACKS[Box objects grouped by Track ID]
    TRACKS --> J[Kalman + Mahalanobis: BOX_JUMP]
    TRACKS --> F[Temporal gap + extrapolation + IoU: TRACK_FRAGMENT]
    TRACKS --> S[Motion prediction + Hungarian: ID_SWITCH]
    J --> R[report function]
    F --> R
    S --> R
    R --> OUT[issues.csv / issues.json / summary.json / report.html]
    OUT --> REVIEW[Reviewer validates in CVAT]
```

**Deployment:** Offline Python 3, NumPy and SciPy on Windows/Linux. No GPU, database, web server or CVAT API required.

**Data flow:** one video annotation → parse valid 2D boxes → group/sort by ID/frame → three independent detectors → flagged issues → CSV/JSON/HTML. The input file is never modified.

**Interfaces:** `python track_qa.py --input demo.xml --format cvat --output results` or `--format bdd` for per-video BDD100K MOT JSON.
