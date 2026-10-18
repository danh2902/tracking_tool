import sys
import unittest
import tempfile
import subprocess
import hashlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from track_qa import Box, iou, parse_cvat, parse_bdd, jump_check, fragmentation_check, switch_check

class TrackingQATests(unittest.TestCase):
    def test_iou(self):
        self.assertAlmostEqual(iou((0,0,10,10),(5,0,15,10)), 1/3)

    def test_cvat_outside(self):
        xml = '<annotations><track id="1" label="car"><box frame="0" xtl="0" ytl="0" xbr="10" ybr="10" outside="0"/><box frame="1" xtl="0" ytl="0" xbr="10" ybr="10" outside="1"/></track></annotations>'
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.xml';f.write_text(xml)
            self.assertEqual(len(parse_cvat(f)),1)

    def test_no_tracks(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.xml';f.write_text('<annotations/>')
            with self.assertRaises(ValueError): parse_cvat(f)

    def test_bdd(self):
        with tempfile.TemporaryDirectory() as d:
            f=Path(d)/'a.json';f.write_text('[{"frameIndex":1,"videoName":"v","labels":[{"id":"2","category":"car","box2d":{"x1":0,"y1":0,"x2":10,"y2":10}}]}]')
            self.assertEqual(parse_bdd(f)[0].tid,'v:2')

    def test_jump(self):
        s=[Box(i,'1','car',(i*2,0,i*2+20,20)) for i in range(5)]
        s.append(Box(5,'1','car',(400,400,420,420)))
        self.assertTrue(any(x['type']=='BOX_JUMP' for x in jump_check({'1':s},18.466,3)))

    def test_fragment(self):
        a=[Box(i,'A','car',(i*2,0,i*2+20,20)) for i in range(4)]
        b=[Box(i,'B','car',(i*2,0,i*2+20,20)) for i in range(6,9)]
        self.assertTrue(fragmentation_check({'A':a,'B':b},12,0.8,0.1))
        b2=[Box(i,'B','truck',(i*2,0,i*2+20,20)) for i in range(6,9)]
        self.assertFalse(fragmentation_check({'A':a,'B':b2},12,0.8,0.1))

    def test_switch(self):
        a=[Box(i,'A','car',(i*10,0,i*10+12,12)) for i in range(4)]
        b=[Box(i,'B','car',(100-i*10,0,112-i*10,12)) for i in range(4)]
        a.append(Box(4,'A','car',(60,0,72,12)))
        b.append(Box(4,'B','car',(40,0,52,12)))
        self.assertTrue(any(x['type']=='ID_SWITCH' for x in switch_check({'A':a,'B':b},2.0,0.3,3)))

    def test_cli_outputs_and_unchanged_input(self):
        source=ROOT/'demo.xml'; before=hashlib.sha256(source.read_bytes()).hexdigest()
        with tempfile.TemporaryDirectory() as d:
            r=subprocess.run([sys.executable,str(ROOT/'track_qa.py'),'--input',str(source),'--format','cvat','--output',d],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stderr)
            for name in ('issues.csv','issues.json','summary.json','report.html'):
                self.assertTrue((Path(d)/name).exists(),name)
        self.assertEqual(before,hashlib.sha256(source.read_bytes()).hexdigest())

if __name__=='__main__': unittest.main()
