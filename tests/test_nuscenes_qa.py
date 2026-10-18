import json
import tempfile
import unittest
from pathlib import Path

from nuscenes_qa import parse_nuscenes, yaw_from_quaternion, jump_check, fragmentation_check


class NuScenesTests(unittest.TestCase):
    def make_data(self, root):
        manifest = []
        results = {}
        for i in range(5):
            token = f'sample-{i}'
            manifest.append({'sample_token': token, 'scene_token': 'scene-1', 'frame_index': i, 'timestamp': i * .5})
            results[token] = [{'tracking_id': 'car-1', 'tracking_name': 'car',
                               'translation': [i * .5, 0, 0], 'size': [2, 4, 1.5],
                               'rotation': [1, 0, 0, 0], 'tracking_score': .9}]
        m, r = root / 'manifest.json', root / 'results.json'
        m.write_text(json.dumps(manifest))
        r.write_text(json.dumps({'results': results, 'meta': {}}))
        return m, r

    def test_parse(self):
        with tempfile.TemporaryDirectory() as d:
            m, r = self.make_data(Path(d))
            tracks = parse_nuscenes(r, m)
            self.assertEqual(len(tracks), 1)
            self.assertEqual(len(tracks[('scene-1', 'car-1')]), 5)
            self.assertEqual(jump_check(tracks), [])
            self.assertEqual(fragmentation_check(tracks), [])

    def test_missing_manifest_token(self):
        with tempfile.TemporaryDirectory() as d:
            m, r = self.make_data(Path(d))
            m.write_text('[]')
            with self.assertRaises(ValueError):
                parse_nuscenes(r, m)

    def test_quaternion(self):
        self.assertAlmostEqual(yaw_from_quaternion([1, 0, 0, 0]), 0)
        with self.assertRaises(ValueError):
            yaw_from_quaternion([0, 0, 0, 0])


if __name__ == '__main__':
    unittest.main()
