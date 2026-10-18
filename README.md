# Tracking QA — CVAT / BDD100K

Offline annotation QA for three suspected error types: `ID_SWITCH`, `TRACK_FRAGMENT`, and `BOX_JUMP`. **Does not edit annotations**.

## Install

```bash
python -m pip install -r requirements.txt
```

## Run

CVAT Online: **Export task dataset → CVAT for video 1.1 → annotations.xml**. Choose *Track* annotations, not independent *Shape* annotations.

```bash
python track_qa.py --input annotations.xml --format cvat --output results
```

BDD100K MOT: supply **one video** as a JSON array of frames with `frameIndex`, `labels`, `id`, `category`, and `box2d:{x1,y1,x2,y2}`.

```bash
python track_qa.py --input video.json --format bdd --output results
```

Outputs: `issues.csv`, `issues.json`, `summary.json`, `report.html`. Open HTML in a browser. Frame indices are **0-based**, matching annotation data; check CVAT's displayed frame numbering.

## Tuning

- `--jump-confidence 0.999`: chi-square 4D Mahalanobis gate for box jumps.
- `--max-gap 12`: max missing frames between two tracks.
- `--fragment-max-dist 0.8`: max normalized predicted center distance.
- `--fragment-min-iou 0.1`: min predicted/observed IoU.
- `--switch-max-dist 0.8`: max normalized cross-match distance.
- `--switch-min-gain 0.3`: minimum advantage of swapped vs original assignment.
- `--min-history 3`: minimum earlier samples before jump/switch checks.

## Important limitations

- This is **heuristic QA**, not ground truth: review every flag visually.
- Kalman constant-velocity prediction can be inaccurate for turning, zooming, moving cameras, fast perspective changes, occlusion, or sparse keyframes.
- ID switch detection specifically targets **pairwise swaps between IDs present in both adjacent frames**. It cannot reliably identify every ID reassignment, and uses no image appearance/ReID.
- Fragmentation detection compares track endpoints and can report multiple candidate merges; it does not resolve them automatically.
- CVAT XML keyframe tracks may omit interpolated frames. Exported keyframes are used as-is; for rigorous QA of frame-by-frame motion, export dense annotations or expand interpolation first.
- BDD parser assumes per-video frames and stable label IDs. Keep one video per input to avoid mixing sequences.
- Scores across error types are not calibrated probabilities.


## nuScenes Tracking 3D + Streamlit

Install all dependencies with `python -m pip install -r requirements.txt` (UI and CLI combined). Run `python -m streamlit run app.py`. Select nuScenes and upload tracking result JSON **plus sample manifest**. See [NUSCENES_GUIDE.md](NUSCENES_GUIDE.md) for manifest schema, CLI example and limitations. The legacy `requirements_ui.txt` has been removed.
