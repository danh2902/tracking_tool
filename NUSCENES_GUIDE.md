# nuScenes Tracking 3D — QA

## Input

1. `results.json`: official nuScenes tracking submission-style JSON (`results` mapping `sample_token` to a list of boxes). Each box includes `tracking_id`, `tracking_name`, `translation` (global x,y,z in meters), `size` (w,l,h in meters), `rotation` ([w,x,y,z] quaternion). This tool checks existing predictions/annotations; it does not infer tracking.
2. `manifest.json`: a JSON list, or `{ "samples": [...] }`, containing one entry for every sample in results:

```json
[
  {"sample_token": "sample-0", "scene_token": "scene-1", "frame_index": 0, "timestamp": 0.0},
  {"sample_token": "sample-1", "scene_token": "scene-1", "frame_index": 1, "timestamp": 0.5}
]
```

`timestamp` is **seconds**; alternatively use `timestamp_us` for microseconds. `frame_index` starts at zero within each scene, increases by one per annotated sample, and timestamps must increase. Use nuScenes `sample` and `scene` metadata to create this manifest; **sample tokens cannot be sorted lexicographically to determine time**. Only scene-specific IDs are compared. nuScenes global coordinates are expected (not sensor-local).

## Run

```powershell
python -m pip install -r requirements.txt
python track_qa.py --format nuscenes --input results.json --manifest manifest.json --output results_nuscenes
python -m streamlit run app.py
```

For UI, select `nuscenes`, upload tracking JSON and manifest, and click Run.

## Checks and limitations

- `BOX_JUMP`: 3D center deviation from constant-velocity extrapolation, instantaneous speed, yaw rate, or size change; requires history and adjacent samples. `mahalanobis_sq_approx` is a **heuristic standardized residual**, not a fully fitted Kalman covariance or calibrated probability.
- `TRACK_FRAGMENT`: end of one ID near predicted start of a different same-class ID in the same scene.
- `ID_SWITCH`: Hungarian matching between simultaneous IDs in adjacent samples using 3D predicted center distance. Only detects pairwise swaps where both IDs persist.
- These are **review candidates**, not proof of labeling mistakes. Thresholds require dataset calibration. 3D oriented IoU and full 3D Kalman filtering are not implemented.
- nuScenes raw database tables, `sample_annotation.json` alone, and 2D camera bounding boxes are not directly supported by this adapter; convert them to tracking result JSON + manifest first.
