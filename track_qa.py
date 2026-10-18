#!/usr/bin/env python3
"""Offline QA for annotated 2D multi-object tracks (CVAT video XML / BDD100K MOT JSON)."""
import argparse
import csv
import html
import json
import math
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
import xml.etree.ElementTree as ET

import numpy as np
from scipy.optimize import linear_sum_assignment
from scipy.stats import chi2


@dataclass(frozen=True)
class Box:
    frame: int
    tid: str
    label: str
    xyxy: tuple
    occluded: bool = False

    @property
    def z(self):
        x1, y1, x2, y2 = self.xyxy
        return np.array([(x1+x2)/2, (y1+y2)/2, x2-x1, y2-y1], dtype=float)


def parse_cvat(path):
    root = ET.parse(path).getroot()
    result = []
    if root.tag != 'annotations':
        raise ValueError('Expected CVAT for video XML with <annotations> root')
    tracks = root.findall('track')
    if not tracks:
        raise ValueError('No <track> found. Export CVAT for video, not CVAT for images (shapes have no stable IDs).')
    for track in tracks:
        tid = str(track.get('id'))
        label = track.get('label', 'unknown')
        for b in track.findall('box'):
            if b.get('outside', '0') == '1':
                continue
            xy = tuple(float(b.get(k)) for k in ('xtl','ytl','xbr','ybr'))
            if xy[2] <= xy[0] or xy[3] <= xy[1]:
                continue
            result.append(Box(int(b.get('frame')), tid, label, xy, b.get('occluded','0') == '1'))
    return result


def parse_bdd(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    if isinstance(data, dict):
        data = data.get('frames', data.get('labels', []))
    if not isinstance(data, list):
        raise ValueError('BDD input must be a list of frame objects')
    result = []
    for i, frame in enumerate(data):
        f = frame.get('frameIndex', frame.get('frame_id', i))
        try:
            f = int(f)
        except (ValueError, TypeError):
            f = i
        video = str(frame.get('videoName', frame.get('video', 'video')))
        for b in frame.get('labels', []):
            xy = b.get('box2d')
            tid = b.get('id')
            if not isinstance(xy, dict) or tid is None:
                continue
            coords = tuple(float(xy[k]) for k in ('x1','y1','x2','y2'))
            if coords[2] <= coords[0] or coords[3] <= coords[1]:
                continue
            attrs = b.get('attributes') or {}
            result.append(Box(f, f'{video}:{tid}', b.get('category','unknown'), coords, bool(attrs.get('occluded', False))))
    return result


def iou(a, b):
    x1, y1 = max(a[0],b[0]), max(a[1],b[1])
    x2, y2 = min(a[2],b[2]), min(a[3],b[3])
    inter = max(0,x2-x1)*max(0,y2-y1)
    aa = max(0,a[2]-a[0])*max(0,a[3]-a[1])
    bb = max(0,b[2]-b[0])*max(0,b[3]-b[1])
    return inter/(aa+bb-inter) if aa+bb-inter > 0 else 0.0


def predicted_box(z):
    x,y,w,h = z
    return (x-w/2,y-h/2,x+w/2,y+h/2)


class Kalman:
    """8D constant velocity state: [cx,cy,w,h,vx,vy,vw,vh]."""
    def __init__(self, b, noise=0.03):
        z = b.z
        self.x = np.r_[z, np.zeros(4)]
        scale = max(10.0, math.hypot(z[2], z[3]))
        self.scale = scale
        self.P = np.diag([(.15*scale)**2]*2 + [(.12*scale)**2]*2 + [(.15*scale)**2]*4)
        self.H = np.c_[np.eye(4), np.zeros((4,4))]
        self.R = np.eye(4)*(.035*scale)**2
        self.noise = noise

    def predict(self, dt=1):
        F = np.eye(8)
        F[:4,4:] = np.eye(4)*dt
        q = (self.noise*self.scale)**2
        Q = np.zeros((8,8))
        Q[:4,:4] = np.eye(4)*q*dt**4/4
        Q[:4,4:] = np.eye(4)*q*dt**3/2
        Q[4:,:4] = np.eye(4)*q*dt**3/2
        Q[4:,4:] = np.eye(4)*q*dt**2
        self.x = F@self.x
        self.P = F@self.P@F.T + Q
        return self.x[:4].copy()

    def innovation(self, z):
        d = z-self.H@self.x
        S = self.H@self.P@self.H.T + self.R
        return float(d@np.linalg.solve(S,d))

    def update(self, z):
        S = self.H@self.P@self.H.T+self.R
        K = np.linalg.solve(S, self.H@self.P).T
        self.x += K@(z-self.H@self.x)
        self.P = (np.eye(8)-K@self.H)@self.P


def make_issue(kind, frame, tid, other='', score=0, reason='', details=None):
    return dict(type=kind, frame=int(frame), track_id=str(tid), other_id=str(other),
                score=round(float(score),4), reason=reason, details=details or {})


def jump_check(tracks, threshold, min_history):
    issues = []
    for tid, seq in tracks.items():
        if len(seq) < min_history:
            continue
        kf = Kalman(seq[0]); prev = seq[0]; seen = 1
        for b in seq[1:]:
            dt = b.frame-prev.frame
            if dt <= 0:
                continue
            kf.predict(dt)
            d2 = kf.innovation(b.z)
            if seen >= min_history and dt == 1 and not (prev.occluded or b.occluded) and d2 > threshold:
                issues.append(make_issue('BOX_JUMP', b.frame, tid, score=min(d2/threshold,99),
                    reason='Bounding box differs strongly from Kalman prediction',
                    details={'mahalanobis_sq':round(d2,3),'threshold':round(threshold,3),
                             'previous_frame':prev.frame,'previous_box':prev.xyxy,'current_box':b.xyxy}))
            # Update even if suspicious; avoid a long series of repeated alarms from one outlier.
            kf.update(b.z)
            prev = b; seen += 1
    return issues


def track_velocity(seq, last=True, window=4):
    s = seq[-window:] if last else seq[:window]
    if len(s) < 2:
        return np.zeros(4)
    dt = s[-1].frame-s[0].frame
    return (s[-1].z-s[0].z)/dt if dt else np.zeros(4)


def extrapolate(b, velocity, dt):
    z = b.z + velocity*dt
    z[2:] = np.maximum(z[2:], 1.0)
    return z


def normalized_distance(a, b):
    scale = max(10.0, math.hypot(a[2],a[3]))
    return float(np.linalg.norm(a[:2]-b[:2])/scale)


def fragmentation_check(tracks, max_gap, max_dist, min_iou):
    issues = []
    endings = sorted(tracks.values(), key=lambda s:s[-1].frame)
    beginnings = sorted(tracks.values(), key=lambda s:s[0].frame)
    for a in endings:
        for b in beginnings:
            if a[0].tid == b[0].tid or a[-1].label != b[0].label:
                continue
            gap = b[0].frame-a[-1].frame-1
            if not 0 <= gap <= max_gap:
                continue
            dt = gap+1
            pred = extrapolate(a[-1],track_velocity(a),dt)
            dist = normalized_distance(pred,b[0].z)
            ov = iou(predicted_box(pred),b[0].xyxy)
            if dist > max_dist or ov < min_iou:
                continue
            score = (1/(1+dist))*(0.5+0.5*ov)
            issues.append(make_issue('TRACK_FRAGMENT',b[0].frame,a[0].tid,b[0].tid,score,
                'Track ends near where another same-class track begins',
                {'end_frame':a[-1].frame,'start_frame':b[0].frame,'missing_frames':gap,
                 'predicted_iou':round(ov,3),'normalized_center_distance':round(dist,3)}))
    return issues


def switch_check(tracks, max_dist, min_gain, min_history):
    """Detect pairwise simultaneous identity swaps at adjacent frames, with global Hungarian association."""
    by_frame = defaultdict(dict)
    for tid, seq in tracks.items():
        for b in seq:
            by_frame[b.frame][tid] = b
    issues=[]; frames=sorted(by_frame)
    for t in frames:
        if t-1 not in by_frame:
            continue
        old=by_frame[t-1]; new=by_frame[t]
        ids=sorted(set(old)&set(new))
        # Require histories before transition; swaps of newly created IDs cannot be inferred reliably.
        ids=[tid for tid in ids if len([b for b in tracks[tid] if b.frame < t]) >= min_history]
        if len(ids)<2:
            continue
        for label in sorted(set(old[k].label for k in ids)):
            sub=[k for k in ids if old[k].label == label and new[k].label == label]
            if len(sub)<2: continue
            pred=[]
            for tid in sub:
                past=[b for b in tracks[tid] if b.frame<t]
                pred.append(extrapolate(old[tid],track_velocity(past),1))
            cost=np.array([[normalized_distance(pred[i],new[j].z) for j in sub] for i in range(len(sub))])
            rows,cols=linear_sum_assignment(cost)
            match={r:c for r,c in zip(rows,cols)}
            for i in range(len(sub)):
                j=match[i]
                if j<=i or match.get(j)!=i:
                    continue
                if max(cost[i,j],cost[j,i])>max_dist:
                    continue
                identity_cost=cost[i,i]+cost[j,j]
                swap_cost=cost[i,j]+cost[j,i]
                gain=identity_cost-swap_cost
                if gain>=min_gain:
                    issues.append(make_issue('ID_SWITCH',t,sub[i],sub[j],gain,
                        'Swapped assignment fits predicted motion better than original IDs',
                        {'identity_cost':round(identity_cost,3),'swap_cost':round(swap_cost,3),
                         'cost_improvement':round(gain,3)}))
    return issues


def report(issues, output, n_tracks, n_boxes, settings):
    output.mkdir(parents=True,exist_ok=True)
    issues.sort(key=lambda x:(x['frame'],x['type'],x['track_id']))
    (output/'issues.json').write_text(json.dumps(issues,indent=2,ensure_ascii=False),encoding='utf-8')
    with (output/'issues.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=['type','frame','track_id','other_id','score','reason','details'])
        writer.writeheader()
        for issue in issues:
            writer.writerow({**issue,'details':json.dumps(issue['details'],ensure_ascii=False)})
    counts={k:sum(x['type']==k for x in issues) for k in ('ID_SWITCH','TRACK_FRAGMENT','BOX_JUMP')}
    rows='\n'.join('<tr>'+''.join('<td>'+html.escape(str(x[k]))+'</td>' for k in ('type','frame','track_id','other_id','score','reason'))+'</tr>' for x in issues)
    page='''<!doctype html><html lang="en"><meta charset="utf-8"><title>Tracking QA</title>
    <style>body{font:15px system-ui;margin:32px;color:#202936}table{border-collapse:collapse;width:100%%}th,td{padding:10px;border-bottom:1px solid #ddd;text-align:left}th{background:#eef2f7}tr:hover{background:#f5f8ff}code{background:#eee;padding:3px}</style>
    <h1>Tracking Annotation QA</h1><p>Potential errors only — human review required.</p>
    <p>Tracks: %s | Boxes: %s | ID switches: %s | Fragments: %s | Box jumps: %s</p>
    <table><thead><tr><th>Type</th><th>Frame</th><th>Track</th><th>Other track</th><th>Score</th><th>Reason</th></tr></thead><tbody>%s</tbody></table></html>'''%(n_tracks,n_boxes,counts['ID_SWITCH'],counts['TRACK_FRAGMENT'],counts['BOX_JUMP'],rows)
    (output/'report.html').write_text(page,encoding='utf-8')
    (output/'summary.json').write_text(json.dumps({'tracks':n_tracks,'boxes':n_boxes,'issues':counts,'settings':settings},indent=2),encoding='utf-8')
    return counts


def main():
    p=argparse.ArgumentParser(description='QA existing 2D tracking annotations (never edits input)')
    p.add_argument('--input',required=True,type=Path)
    p.add_argument('--format',choices=['cvat','bdd'],required=True)
    p.add_argument('--output',type=Path,default=Path('results'))
    p.add_argument('--max-gap',type=int,default=12,help='Maximum missing frames between two candidate fragments')
    p.add_argument('--fragment-max-dist',type=float,default=0.8,help='Center distance / box diagonal')
    p.add_argument('--fragment-min-iou',type=float,default=0.1)
    p.add_argument('--switch-max-dist',type=float,default=0.8)
    p.add_argument('--switch-min-gain',type=float,default=0.3)
    p.add_argument('--min-history',type=int,default=3)
    p.add_argument('--jump-confidence',type=float,default=0.999,help='Chi-square threshold for 4D measurement')
    args=p.parse_args()
    if args.max_gap<0 or args.min_history<2 or not 0<args.jump_confidence<1:
        p.error('Invalid thresholds')
    boxes=parse_cvat(args.input) if args.format=='cvat' else parse_bdd(args.input)
    tracks=defaultdict(list)
    for b in boxes:
        tracks[b.tid].append(b)
    for tid in tracks:
        tracks[tid].sort(key=lambda b:b.frame)
    issues=jump_check(tracks,chi2.ppf(args.jump_confidence,4),args.min_history)
    issues+=fragmentation_check(tracks,args.max_gap,args.fragment_max_dist,args.fragment_min_iou)
    issues+=switch_check(tracks,args.switch_max_dist,args.switch_min_gain,args.min_history)
    counts=report(issues,args.output,len(tracks),len(boxes),vars(args).__str__())
    print(f'Tracks: {len(tracks)} | Boxes: {len(boxes)} | Alerts: {len(issues)} | {counts}')
    print(f'Reports: {args.output.resolve()}')

if __name__=='__main__':
    main()
