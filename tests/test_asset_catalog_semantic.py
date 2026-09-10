import importlib.util, json, os, sys, tempfile, unittest, hashlib
from PIL import Image
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import asset_catalog as cat
import asset_catalog_semantic as sem

class Fake:
    identity='test@revision:normalized'
    def encode(self,texts,query=False):
        return np.array([[1.,0.] if 'chair' in t or 'seat' in t else [0.,1.] for t in texts])

class RetrievalTests(unittest.TestCase):
    def setUp(self):
        self.db=cat.connect(':memory:');self.e=Fake()
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        image=Path(tmp.name)/'fixture.png';Image.new('RGB',(4,4),'red').save(image)
        evidence=json.dumps({'preview':str(image),'sha256':hashlib.sha256(image.read_bytes()).hexdigest()})
        for key,name,description in [('sa:model:1','chair','wooden chair'),('sa:model:2','barrel','metal barrel'),('vc:model:1','chair_vc','chair antique')]:
            payload={'record':{'name':name},'hints':[],'catalogSource':'fixture'}
            self.db.execute('INSERT INTO assets VALUES (?,?,?,?,?,?)',(key,key[:2],'model',name,'hash',json.dumps(payload)))
            self.db.execute('INSERT INTO annotations VALUES (?,?,?,?,?,?,?,?)',(key,'hash',description,'[]','human-visual','fixture',1,evidence))
            cat.searchable(self.db,key,name,payload,'hash')
        self.db.commit()
    def tearDown(self):self.db.close()
    def test_incremental_and_annotation_change(self):
        self.assertEqual(sem.build(self.db,self.e)['embedded'],3)
        self.assertEqual(sem.build(self.db,self.e)['unchanged'],3)
        self.db.execute("UPDATE annotations SET description='seat worn' WHERE key='sa:model:1'")
        self.assertEqual(sem.build(self.db,self.e)['embedded'],1)
    def test_stale_vectors_excluded_before_rebuild(self):
        sem.build(self.db,self.e)
        self.db.execute("UPDATE assets SET hash='new' WHERE key='sa:model:1'")
        r=sem.search(self.db,self.e,'seat',game='sa')
        self.assertEqual(r['coverage']['freshEmbeddedDocuments'],1)
        self.assertNotIn('sa:model:1',[x['key'] for x in r['results']])
        self.assertEqual(sem.build(self.db,self.e)['deleted'],1)
    def test_game_filter_and_cosine(self):
        sem.build(self.db,self.e)
        r=sem.search(self.db,self.e,'seat',game='sa')
        self.assertEqual(r['results'][0]['key'],'sa:model:1')
        self.assertEqual(r['results'][0]['cosineScore'],1.)
        self.assertEqual(r['coverage']['assetsInScope'],2)
    def test_revision_namespace(self):
        sem.build(self.db,self.e);self.e.identity='new-revision'
        self.assertEqual(sem.search(self.db,self.e,'seat')['coverage']['freshEmbeddedDocuments'],0)
        self.assertEqual(sem.build(self.db,self.e)['embedded'],3)
    def test_hybrid_retains_unembedded_assets(self):
        sem.build(self.db,self.e)
        self.db.execute("DELETE FROM annotations WHERE key='sa:model:2'")
        r=sem.search(self.db,self.e,'barrel',hybrid=True)
        x=next(x for x in r['results'] if x['key']=='sa:model:2')
        self.assertIsNone(x['cosineScore']);self.assertEqual(x['lexicalRank'],1)
    def test_metadata_is_separate_corpus(self):
        self.db.execute('DELETE FROM annotations')
        self.assertEqual(sem.build(self.db,self.e)['eligible'],0)
        self.assertEqual(sem.build(self.db,self.e,'metadata')['embedded'],3)
        self.assertEqual(sem.search(self.db,self.e,'chair')['results'],[])

    def test_metadata_coverage_does_not_claim_visual_annotation(self):
        self.db.execute("DELETE FROM annotations WHERE key='sa:model:2'")
        sem.build(self.db,self.e,'metadata')
        result=sem.search(self.db,self.e,'chair',corpus='metadata',game='sa')
        coverage=result['coverage']
        self.assertEqual(coverage['freshEmbeddedDocuments'],2)
        self.assertEqual(coverage['freshVisuallyAnnotatedDocuments'],1)
        self.assertEqual(coverage['freshMetadataOnlyDocuments'],1)
        # Changing actual evidence invalidates the visual coverage, even when
        # metadata remains eligible and the previous vectors are still stored.
        self.db.execute("UPDATE annotations SET confidence=.1 WHERE key='sa:model:1'")
        result=sem.search(self.db,self.e,'chair',corpus='metadata',game='sa')
        self.assertEqual(result['coverage']['freshVisuallyAnnotatedDocuments'],0)
        self.assertEqual(result['coverage']['freshMetadataOnlyDocuments'],1)
    def test_reject_invalid_vectors(self):
        self.e.encode=lambda texts: np.full((len(texts),2),np.nan)
        with self.assertRaises(ValueError):sem.build(self.db,self.e)
    def test_invalid_query_vectors(self):
        sem.build(self.db,self.e)
        for value in (np.array([[0.,0.]]),np.array([[np.nan,1.]]),np.array([[1.,0.,0.]]),np.array([1.,0.])):
            self.e.encode=lambda texts,query=False,value=value:value
            with self.assertRaises(ValueError):sem.search(self.db,self.e,'seat')
    def test_corrupt_stored_dimensions(self):
        sem.build(self.db,self.e)
        self.db.execute('UPDATE semantic_vectors SET dim=3')
        with self.assertRaises(ValueError):sem.search(self.db,self.e,'seat')
    def test_deleted_assets_cleaned(self):
        sem.build(self.db,self.e);self.db.execute("DELETE FROM assets WHERE key='sa:model:1'")
        self.assertEqual(sem.build(self.db,self.e)['deleted'],1)
    def test_legacy_ambiguous_annotation_not_usable(self):
        self.db.execute("UPDATE annotations SET confidence=.2,evidence=? WHERE key='sa:model:1'",(json.dumps({'preview':'fixture.png','sha256':'fixture','views':1,'needs_another_view':True}),))
        self.assertNotIn('sa:model:1',sem.documents(self.db))
        metadata=sem.documents(self.db,'metadata')['sa:model:1']
        self.assertFalse(metadata['visuallyAnnotated'])
        self.assertEqual(self.db.execute("SELECT COUNT(*) FROM annotations WHERE key='sa:model:1'").fetchone()[0],1)
    def test_explicit_ambiguity_overrides_high_confidence(self):
        self.db.execute("UPDATE annotations SET confidence=.9,evidence=? WHERE key='sa:model:1'",(json.dumps({'needs_another_view':True}),))
        self.assertNotIn('sa:model:1',sem.documents(self.db))

@unittest.skipUnless(os.getenv('ASSET_SEMANTIC_INTEGRATION')=='1','opt-in public model download')
class RealModelTests(unittest.TestCase):
    def test_cross_language_paraphrase_smoke(self):
        # Synthetic infrastructure smoke, not a catalogue recall evaluation.
        e=sem.Encoder();passages=['A wooden seat with a backrest for one person.','A cylindrical steel container for storing fuel.','A ceramic basin and faucet for washing hands.','A tall electric appliance that keeps food cold.']
        queries=['Je cherche de quoi asseoir un visiteur.','Un récipient pour garder de l’essence.','Où se nettoyer les mains ?','Conserver les courses au frais.']
        scores=e.encode(queries,query=True)@e.encode(passages).T
        # Fourth paraphrase is a documented miss (ranked fuel ahead of fridge).
        # This is an inference smoke, not a claim that every query succeeds.
        self.assertEqual(scores[:3].argmax(axis=1).tolist(),[0,1,2])
        self.assertEqual(scores.shape,(4,4))
        self.assertTrue(np.all(np.abs(scores)<=1.0001))
if __name__=='__main__':unittest.main()
