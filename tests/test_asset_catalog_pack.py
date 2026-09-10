import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import asset_catalog as cat
import asset_catalog_pack as pack
import asset_catalog_semantic as semantic
from PIL import Image
import numpy as np


class Encoder:
    identity='pack-test'
    def encode(self,texts,query=False):return np.array([[1.,0.] for _ in texts])


class PackTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name);self.db=cat.connect(':memory:');self.addCleanup(self.db.close)
        self.source=self.root/'fixture.txd';self.source.write_bytes(b'original pixels')
        self.locator={'path':str(self.source),'offset':0,'bytes':15}
        self.index={('gta3.img','fixture.txd'):[self.locator]}
        self.payload={'catalogSource':'local-fixture','record':{'name':'surface','txd':'fixture','source':'/another/user/models/gta3.img'},'hints':[]}
        self.db.execute('INSERT INTO assets VALUES (?,?,?,?,?,?)',('sa:texture:local','sa','texture','surface','local-metadata-hash',cat.canonical(self.payload)))
        self.entry={'game':'sa','kind':'texture','selector':{'name':'surface','txd':'fixture','archive':'gta3.img'},'description':'Red brick wall','tags':['brick','red'],'confidence':.9,'review_method':'model-visual','limitations':'Appearance only','image_sha256':['a'*64],'sources':[{'archive':'gta3.img','entry':'fixture.txd','bytes':15,'sha256':hashlib.sha256(self.source.read_bytes()).hexdigest()}]}
        self.refresh()
        self.db.commit()
    def refresh(self):
        self.entry['id']=cat.digest({k:v for k,v in self.entry.items() if k!='id'})
        self.pack={'format':pack.VERSION,'version':'test-v1','license':'MIT','entries':[self.entry]}
        self.pack['sha256']=cat.digest(self.pack)
    def test_portable_import_and_semantic_retrieval(self):
        self.assertEqual(pack.import_pack(self.db,self.pack,self.index)['eligible'],1)
        self.assertEqual(self.db.execute('select count(*) from annotations').fetchone()[0],0)
        self.assertEqual(pack.import_pack(self.db,self.pack,self.index,True)['eligible'],1)
        annotation=self.db.execute('select * from annotations').fetchone()
        self.assertEqual(annotation['asset_hash'],'local-metadata-hash')
        self.assertEqual(annotation['method'],'shared-visual')
        self.assertTrue(cat.annotation_is_usable(self.db,annotation))
        self.assertEqual(cat.search(self.db,'brick')[0]['key'],'sa:texture:local')
        semantic.build(self.db,Encoder())
        self.assertEqual(len(semantic.search(self.db,Encoder(),'wall')['results']),1)
    def test_source_change_excludes_lexical_and_semantic(self):
        pack.import_pack(self.db,self.pack,self.index,True);semantic.build(self.db,Encoder())
        self.source.write_bytes(b'modified pixels')
        self.assertEqual(cat.search(self.db,'brick'),[])
        self.assertEqual(semantic.search(self.db,Encoder(),'wall')['results'],[])
    def test_source_missing_is_not_fresh(self):
        pack.import_pack(self.db,self.pack,self.index,True);self.source.unlink()
        self.assertFalse(cat.annotation_is_usable(self.db,self.db.execute('select * from annotations').fetchone()))
    def test_wrong_bytes_and_duplicate_archive_rejected(self):
        self.source.write_bytes(b'different bytes')
        self.assertEqual(pack.import_pack(self.db,self.pack,self.index)['eligible'],0)
        self.index[('gta3.img','fixture.txd')].append(self.locator)
        self.assertEqual(pack.import_pack(self.db,self.pack,self.index)['eligible'],0)
    def test_reference_only_not_auto_imported(self):
        self.entry['sources']=[];self.refresh()
        r=pack.import_pack(self.db,self.pack,self.index,True)
        self.assertEqual(r['reference_only'],1);self.assertEqual(r['eligible'],0)
    def test_local_review_preserved(self):
        self.db.execute('insert into annotations values (?,?,?,?,?,?,?,?)',('sa:texture:local','local-metadata-hash','local','[]','human-visual','tester',1,'{}'));self.db.commit()
        r=pack.import_pack(self.db,self.pack,self.index,True)
        self.assertEqual(r['preserved_local_review'],1)
        self.assertEqual(self.db.execute('select description from annotations').fetchone()[0],'local')
    def test_digest_and_paths_rejected(self):
        self.entry['description']='changed'
        with self.assertRaises(ValueError):pack.import_pack(self.db,self.pack,self.index,True)
        self.entry['description']='safe';self.entry['sources'][0]['entry']='../fixture.txd';self.refresh()
        with self.assertRaises(ValueError):pack.validate(self.pack)
        self.assertEqual(self.db.execute('select count(*) from annotations').fetchone()[0],0)
    def test_conflicting_entries_fail_before_writes(self):
        e=dict(self.entry,description='another description');e['id']=cat.digest({k:v for k,v in e.items() if k!='id'})
        self.pack['entries'].append(e);self.pack['sha256']=cat.digest({k:v for k,v in self.pack.items() if k!='sha256'})
        with self.assertRaises(ValueError):pack.import_pack(self.db,self.pack,self.index,True)
        self.assertEqual(self.db.execute('select count(*) from annotations').fetchone()[0],0)
    def test_export_strips_private_identity_and_evidence_paths(self):
        image=self.root/'private.png';Image.new('RGB',(8,8),'red').save(image)
        evidence={'views':[{'path':str(image),'sha256':hashlib.sha256(image.read_bytes()).hexdigest()}],'limitations':'One view'}
        self.db.execute('insert into annotations values (?,?,?,?,?,?,?,?)',('sa:texture:local','local-metadata-hash','red surface','["red"]','model-visual','tester',.9,cat.canonical(evidence)))
        result,_=pack.export_pack(self.db,'fixture')
        pack.validate(result)
        serialized=json.dumps(result)
        self.assertNotIn(str(self.root),serialized);self.assertNotIn('/another/user',serialized)
        self.assertNotIn('local-metadata-hash',serialized)
        self.assertEqual(result['entries'][0]['sources'],[])
    def test_public_pack_has_only_portable_text_and_hashes(self):
        public=Path(__file__).resolve().parents[1]/'data/annotations/sa-2026-09-11.json'
        data=public.read_text()
        loaded=pack.validate(json.loads(data))
        self.assertGreater(len(loaded['entries']),0)
        self.assertIsNone(pack.PRIVATE.search(data))
    def test_local_archive_offsets_are_discovered_not_taken_from_pack(self):
        import struct
        models=self.root/'game'/'models';models.mkdir(parents=True)
        archive=models/'gta3.img'
        content=b'pixels'+b'\0'*(2048-6)
        archive.write_bytes(b'VER2'+struct.pack('<I',1)+struct.pack('<IHH24s',2,1,0,b'fixture.txd')+b'\0'*(4096-40)+content)
        self.entry['sources'][0].update(bytes=2048,sha256=hashlib.sha256(content).hexdigest());self.refresh()
        index=pack.local_sources(models.parent)
        self.assertEqual(index[('gta3.img','fixture.txd')][0]['offset'],4096)
        self.assertEqual(pack.import_pack(self.db,self.pack,index,True)['eligible'],1)

    def test_private_text_fails_export(self):
        for value in ('local /Users/alice/secret', 'https://example.org/private','C:\\Users\\alice'):
            with self.assertRaises(ValueError):pack.clean_text(value)

if __name__=='__main__':unittest.main()
