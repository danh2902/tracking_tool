"""Offline heuristic QA for nuScenes 3D tracking result JSON.

Requires an explicit scene/sample manifest: sample tokens are opaque, not sortable.
All coordinates are in nuScenes global frame, dimensions in meters, time in seconds.
"""
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import chi2


@dataclass(frozen=True)
class Detection3D:
    scene: str
    frame: int
    timestamp: float
    token: str
    tid: str
    label: str
    xyz: tuple
    size: tuple
    yaw: float

    @property
    def measurement(self):
        return np.array([*self.xyz, *self.size], dtype=float)


def yaw_from_quaternion(q):
    """nuScenes quaternion convention: [w, x, y, z]."""
    w, x, y, z = (float(v) for v in q)
    norm = math.sqrt(w*w+x*x+y*y+z*z)
    if norm < 1e-9 or not math.isfinite(norm):
        raise ValueError('Invalid rotation quaternion')
    w, x, y, z = (v/norm for v in (w, x, y, z))
    return math.atan2(2*(w*z+x*y), 1-2*(y*y+z*z))


def angle_difference(a, b):
    return abs((a-b+math.pi) % (2*math.pi)-math.pi)


def parse_manifest(path):
    """JSON list of {sample_token, scene_token, frame_index, timestamp}.

    timestamp is in seconds. Alternative timestamp_us in microseconds.
    """
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(raw, dict):
        raw = raw.get('samples')
    if not isinstance(raw, list) or not raw:
        raise ValueError('Manifest must be a non-empty list or {"samples": [...]}')
    lookup = {}
    seen_frames = set()
    for item in raw:
        token = str(item['sample_token'])
        scene = str(item['scene_token'])
        frame = int(item['frame_index'])
        if 'timestamp' in item:
            timestamp = float(item['timestamp'])
        else:
            timestamp = float(item['timestamp_us']) / 1e6
        if not math.isfinite(timestamp) or frame < 0:
            raise ValueError(f'Invalid timestamp/frame for sample {token}')
        if token in lookup or (scene, frame) in seen_frames:
            raise ValueError(f'Duplicate sample or scene/frame: {token}')
        lookup[token] = (scene, frame, timestamp)
        seen_frames.add((scene, frame))
    by_scene = defaultdict(list)
    for scene, frame, ts in lookup.values():
        by_scene[scene].append((frame, ts))
    for scene, seq in by_scene.items():
        seq.sort()
        if any(b[1] <= a[1] for a, b in zip(seq, seq[1:])):
            raise ValueError(f'Non-increasing timestamps in scene {scene}')
    return lookup


def parse_nuscenes(path, manifest_path):
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(raw, dict) or not isinstance(raw.get('results'), dict):
        raise ValueError('Expected nuScenes tracking result {"results": {sample_token: [...]}}')
    manifest = parse_manifest(manifest_path)
    tracks = defaultdict(list)
    seen = set()
    for token, annotations in raw['results'].items():
        if token not in manifest:
            raise ValueError(f'Missing sample_token in manifest: {token}')
        if not isinstance(annotations, list):
            raise ValueError(f'Expected list of boxes for sample {token}')
        scene, frame, ts = manifest[token]
        for box in annotations:
            tid = str(box['tracking_id'])
            label = str(box['tracking_name'])
            xyz = tuple(float(v) for v in box['translation'])
            size = tuple(float(v) for v in box['size'])
            if len(xyz) != 3 or len(size) != 3 or any(not math.isfinite(v) for v in xyz+size) or any(v <= 0 for v in size):
                raise ValueError(f'Invalid 3D translation/size for {token}, track {tid}')
            yaw = yaw_from_quaternion(box['rotation'])
            key = (scene, frame, tid)
            if key in seen:
                raise ValueError(f'Duplicate track ID in scene/frame: {key}')
            seen.add(key)
            tracks[(scene, tid)].append(Detection3D(scene, frame, ts, token, tid, label, xyz, size, yaw))
    for seq in tracks.values():
        seq.sort(key=lambda b: b.timestamp)
    return tracks


def velocity(seq, last=True, window=4):
    part = seq[-window:] if last else seq[:window]
    if len(part) < 2:
        return np.zeros(3)
    dt = part[-1].timestamp-part[0].timestamp
    return (np.array(part[-1].xyz)-np.array(part[0].xyz))/dt if dt > 0 else np.zeros(3)


def issue(kind, b, other='', score=0, reason='', details=None):
    return dict(type=kind, frame=b.frame, track_id=f'{b.scene}:{b.tid}',
                other_id=f'{b.scene}:{other}' if other else '', score=round(float(score), 4),
                reason=reason, details={'scene': b.scene, 'sample_token': b.token, 'timestamp': b.timestamp, **(details or {})})


def jump_check(tracks, confidence=0.999, min_history=3, max_speed=55.0, max_yaw_rate=3.0, max_size_change=0.6):
    """3D position constant-velocity Kalman-like innovation with time-scaled covariance.

    Scores are heuristic, not calibrated probabilities. Only adjacent annotated frames
    trigger jumps; timestamp-based velocity and yaw checks complement innovation.
    """
    issues = []
    threshold = chi2.ppf(confidence, 3)
    for seq in tracks.values():
        if len(seq) < min_history:
            continue
        for i in range(1, len(seq)):
            prev, curr = seq[i-1], seq[i]
            dt = curr.timestamp-prev.timestamp
            if dt <= 0 or curr.frame != prev.frame+1:
                continue
            v = velocity(seq[:i])
            predicted = np.array(prev.xyz)+v*dt
            delta = np.array(curr.xyz)-predicted
            # Position measurement covariance: ~0.5 m base, uncertainty increases with dt.
            sigma = 0.5 + 1.5*dt
            d2 = float(delta@delta/(sigma*sigma))
            speed = float(np.linalg.norm(np.array(curr.xyz)-np.array(prev.xyz))/dt)
            yaw_rate = angle_difference(curr.yaw, prev.yaw)/dt
            size_change = float(np.max(np.abs(np.array(curr.size)-np.array(prev.size))/np.array(prev.size)))
            if i >= min_history and (d2 > threshold or speed > max_speed or yaw_rate > max_yaw_rate or size_change > max_size_change):
                issues.append(issue('BOX_JUMP', curr, score=min(max(d2/threshold, speed/max_speed, yaw_rate/max_yaw_rate, size_change/max_size_change), 99),
                    reason='Suspicious 3D position, speed, yaw or size change',
                    details={'mahalanobis_sq_approx':round(d2, 3), 'speed_mps':round(speed, 3),
                             'yaw_rate_rad_s':round(yaw_rate, 3), 'max_relative_size_change':round(size_change, 3),
                             'previous_frame':prev.frame}))
    return issues


def fragmentation_check(tracks, max_gap=12, max_dist=4.0, max_time_gap=10.0):
    issues = []
    by_scene = defaultdict(list)
    for seq in tracks.values():
        by_scene[seq[0].scene].append(seq)
    for seqs in by_scene.values():
        for a in seqs:
            for b in seqs:
                if a is b or a[-1].label != b[0].label:
                    continue
                gap = b[0].frame-a[-1].frame-1
                dt = b[0].timestamp-a[-1].timestamp
                if not (0 <= gap <= max_gap and 0 < dt <= max_time_gap):
                    continue
                predicted = np.array(a[-1].xyz)+velocity(a)*dt
                distance = float(np.linalg.norm(predicted-np.array(b[0].xyz)))
                if distance <= max_dist:
                    issues.append(issue('TRACK_FRAGMENT', b[0], a[0].tid, 1/(1+distance),
                        'One 3D track ends near the start of another same-class track',
                        {'missing_frames':gap, 'time_gap_s':round(dt, 3), 'predicted_distance_m':round(distance, 3)}))
    return issues


def switch_check(tracks, max_dist=4.0, min_gain=1.0, min_history=3):
    issues = []
    by_frame = defaultdict(dict)
    for (scene, tid), seq in tracks.items():
        for b in seq:
            by_frame[(scene, b.frame)][tid] = b
    for (scene, frame), current in sorted(by_frame.items()):
        previous = by_frame.get((scene, frame-1), {})
        ids = [tid for tid in sorted(set(previous)&set(current))
               if len([b for b in tracks[(scene, tid)] if b.frame < frame]) >= min_history]
        for label in sorted({previous[tid].label for tid in ids}):
            subset = [tid for tid in ids if previous[tid].label == current[tid].label == label]
            if len(subset) < 2:
                continue
            pred = []
            for tid in subset:
                past = [b for b in tracks[(scene, tid)] if b.frame < frame]
                dt = current[tid].timestamp-previous[tid].timestamp
                pred.append(np.array(previous[tid].xyz)+velocity(past)*dt)
            cost = np.array([[np.linalg.norm(pred[i]-np.array(current[other].xyz)) for other in subset]
                             for i in range(len(subset))])
            rows, cols = linear_sum_assignment(cost)
            match = dict(zip(rows, cols))
            for i, j in match.items():
                if j <= i or match.get(j) != i:
                    continue
                gain = cost[i,i]+cost[j,j]-cost[i,j]-cost[j,i]
                if gain >= min_gain and max(cost[i,j], cost[j,i]) <= max_dist:
                    issues.append(issue('ID_SWITCH', current[subset[i]], subset[j], gain,
                        'Swapped 3D assignments fit predicted positions better',
                        {'cost_improvement_m':round(float(gain), 3)}))
    return issues


def run_nuscenes(path, manifest_path, output, settings):
    from track_qa import report
    tracks = parse_nuscenes(path, manifest_path)
    issues = jump_check(tracks, settings['jump_confidence'], settings['min_history'],
                        settings['max_speed'], settings['max_yaw_rate'], settings['max_size_change'])
    issues += fragmentation_check(tracks, settings['max_gap'], settings['fragment_max_dist_3d'], settings['max_time_gap'])
    issues += switch_check(tracks, settings['switch_max_dist_3d'], settings['switch_min_gain_3d'], settings['min_history'])
    count = sum(map(len, tracks.values()))
    counts = report(issues, Path(output), len(tracks), count, {'format':'nuscenes', **settings})
    return len(tracks), count, issues, counts
