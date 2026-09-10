#!/usr/bin/env python3
"""Local multilingual retrieval. Embeddings describe text, not unexamined images."""
import argparse, json, time
from pathlib import Path
import numpy as np
import asset_catalog as catalog
MODEL='intfloat/multilingual-e5-small'
REVISION='614241f622f53c4eeff9890bdc4f31cfecc418b3'
FORMAT='e5-prefix-normalized-f32-v1'

class Encoder:
    def __init__(self, model=MODEL, revision=REVISION, device='cpu'):
        from sentence_transformers import SentenceTransformer
        self.identity=f'{model}@{revision}:{FORMAT}'
        self.model=SentenceTransformer(model,revision=revision,device=device,trust_remote_code=False)
        self.model.max_seq_length=512
    def encode(self, texts, query=False):
        return self.model.encode([('query: ' if query else 'passage: ')+t for t in texts],normalize_embeddings=True,convert_to_numpy=True,show_progress_bar=False,batch_size=32)

def setup(db):
    db.execute('''CREATE TABLE IF NOT EXISTS semantic_vectors (
      key TEXT, model TEXT, corpus TEXT, fingerprint TEXT, dim INTEGER, vector BLOB,
      PRIMARY KEY(key,model,corpus))''')

def documents(db, corpus='annotations', game=None, kind=None):
    if corpus not in ('annotations','metadata'):raise ValueError('Unknown corpus')
    sql='SELECT a.*,n.description,n.tags,n.method,n.model annotator,n.confidence,n.evidence FROM assets a LEFT JOIN annotations n ON a.key=n.key AND a.hash=n.asset_hash WHERE 1=1'
    params=[]
    if game:sql+=' AND a.game=?';params.append(game)
    if kind:sql+=' AND a.kind=?';params.append(kind)
    result={};freshness_cache={}
    for r in db.execute(sql,params):
        usable=bool(r['description']) and catalog.annotation_is_usable(db,r,freshness_cache)
        if r['method']=='exact-pixel-visual-transfer' and not usable:continue
        if corpus=='annotations' and not usable:continue
        parts=[]
        if corpus=='metadata':
            p=json.loads(r['payload']); rec=p['record']
            parts=[r['name'],rec.get('category',''),' '.join(rec.get('tags',[]))]
            parts += [t for h in p.get('hints',[]) for t in h['tags']]
        if usable:parts += [r['description'],r['tags'] or '']
        text=' '.join(parts).strip()
        if not text:continue
        fingerprint=catalog.digest([FORMAT,r['hash'],text,r['method'],r['annotator'],r['evidence']])
        result[r['key']]={'key':r['key'],'name':r['name'],'kind':r['kind'],'game':r['game'],'text':text,'fingerprint':fingerprint,'visuallyAnnotated':usable}
    return result

def build(db,encoder,corpus='annotations',batch_size=32):
    if batch_size<1:raise ValueError('batch_size must be positive')
    setup(db);start=time.monotonic();docs=documents(db,corpus)
    old={r['key']:r['fingerprint'] for r in db.execute('SELECT key,fingerprint FROM semantic_vectors WHERE model=? AND corpus=?',(encoder.identity,corpus))}
    pending=[d for k,d in docs.items() if old.get(k)!=d['fingerprint']]
    removed=set(old)-set(docs)
    with db:
        for k in removed:db.execute('DELETE FROM semantic_vectors WHERE key=? AND model=? AND corpus=?',(k,encoder.identity,corpus))
    for start_i in range(0,len(pending),batch_size):
        batch=pending[start_i:start_i+batch_size];vectors=np.asarray(encoder.encode([d['text'] for d in batch]),dtype='<f4')
        if vectors.ndim!=2 or len(vectors)!=len(batch) or not np.isfinite(vectors).all():raise ValueError('Invalid encoder vectors')
        norms=np.linalg.norm(vectors,axis=1,keepdims=True)
        if (norms==0).any():raise ValueError('Zero vector')
        vectors=vectors/norms
        with db:
            for d,v in zip(batch,vectors):db.execute('INSERT OR REPLACE INTO semantic_vectors VALUES (?,?,?,?,?,?)',(d['key'],encoder.identity,corpus,d['fingerprint'],len(v),v.astype('<f4').tobytes()))
    return {'model':encoder.identity,'corpus':corpus,'embedded':len(pending),'unchanged':len(docs)-len(pending),'deleted':len(removed),'eligible':len(docs),'seconds':round(time.monotonic()-start,3)}

def diversify_texture_pixels(db, ranked):
    """Keep one ranked appearance per proven pixel group, retaining occurrence IDs."""
    groups={};freshness_cache={}
    for row in db.execute("SELECT * FROM annotations WHERE method='exact-pixel-visual-transfer'"):
        if not catalog.annotation_is_fresh(db,row,freshness_cache):continue
        e=json.loads(row['evidence']);groups[row['key']]=e['pixel_sha256'];groups[e['parent_key']]=e['pixel_sha256']
    if db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='visual_pixel_observations'").fetchone():
        for row in db.execute('SELECT * FROM visual_pixel_observations'):
            bound={'parent_key':row['key'],'parent_annotation_sha256':row['parent_annotation_sha256']}
            if catalog.annotation_is_fresh(db,{'method':'exact-pixel-visual-transfer','evidence':catalog.canonical(bound)},freshness_cache):groups[row['key']]=row['pixel_sha256']
    result=[];seen={}
    for item in ranked:
        group=groups.get(item['key']) if item['kind']=='texture' else None
        if not group:
            result.append(item);continue
        if group in seen:
            for key in item.get('equivalent_pixel_occurrences',[item['key']]):
                if key not in seen[group]['equivalent_pixel_occurrences']:seen[group]['equivalent_pixel_occurrences'].append(key)
            continue
        representative=dict(item,pixel_group_sha256=group,equivalent_pixel_occurrences=list(item.get('equivalent_pixel_occurrences',[item['key']])),equivalence_scope='Exact texture pixels only; model use and atlas context are not interchangeable.')
        seen[group]=representative;result.append(representative)
    return result

def search(db,encoder,query,limit=20,corpus='annotations',game=None,kind=None,hybrid=False,diversify_pixels=False):
    if not 1<=limit<=1000:raise ValueError('limit must be 1..1000')
    if not query.strip():raise ValueError('Empty query')
    setup(db);docs=documents(db,corpus,game,kind);rows=[];vectors=[]
    for r in db.execute('SELECT * FROM semantic_vectors WHERE model=? AND corpus=?',(encoder.identity,corpus)):
        d=docs.get(r['key'])
        if not d or d['fingerprint']!=r['fingerprint']:continue
        v=np.frombuffer(r['vector'],dtype='<f4')
        if len(v)!=r['dim'] or not np.isfinite(v).all():raise ValueError('Corrupt stored vector')
        rows.append(d);vectors.append(v)
    result=[]
    if vectors:
        encoded=np.asarray(encoder.encode([query],query=True))
        if encoded.ndim!=2 or encoded.shape[0]!=1 or not np.isfinite(encoded).all():raise ValueError('Invalid query vector')
        q=encoded[0];norm=np.linalg.norm(q)
        if not np.isfinite(norm) or norm==0:raise ValueError('Zero or invalid query vector')
        if not all(v.shape==q.shape for v in vectors):raise ValueError('Embedding dimension mismatch')
        q=q/norm
        scores=np.clip(np.stack(vectors)@q,-1,1)
        order=sorted(range(len(rows)),key=lambda i:(-float(scores[i]),rows[i]['key']))
        if not diversify_pixels:order=order[:max(limit,100) if hybrid else limit]
        result=[{k:v for k,v in rows[i].items() if k not in ('fingerprint','text')}|{'cosineScore':float(scores[i]),'semanticRank':rank+1} for rank,i in enumerate(order)]
        if diversify_pixels:result=diversify_texture_pixels(db,result)[:max(limit,100) if hybrid else limit]
    if hybrid:
        merged={r['key']:dict(r,rrfScore=1/(60+r['semanticRank'])) for r in result}
        for rank,r in enumerate(catalog.search(db,query,limit=max(limit,100),game=game,kind=kind),1):
            target=merged.setdefault(r['key'],{k:r[k] for k in ('key','name','kind')}|{'cosineScore':None,'semanticRank':None,'rrfScore':0})
            target['lexicalRank']=rank;target['rrfScore']+=1/(60+rank)
        result=sorted(merged.values(),key=lambda r:(-r['rrfScore'],r['key']))
        if diversify_pixels:result=diversify_texture_pixels(db,result)
        result=result[:limit]
    sql='SELECT COUNT(*) FROM assets WHERE 1=1';params=[]
    for column,value in [('game',game),('kind',kind)]:
        if value:sql+=f' AND {column}=?';params.append(value)
    total=db.execute(sql,params).fetchone()[0]
    visually_annotated=sum(bool(r['visuallyAnnotated']) for r in rows)
    return {'query':query,'model':encoder.identity,'corpus':corpus,'mode':'hybrid-rrf' if hybrid else 'semantic','diversified_texture_pixels':diversify_pixels,'coverage':{'assetsInScope':total,'eligibleDocuments':len(docs),'freshEmbeddedDocuments':len(rows),'freshVisuallyAnnotatedDocuments':visually_annotated,'freshMetadataOnlyDocuments':len(rows)-visually_annotated,'eligibleMissingVectors':len(docs)-len(rows),'assetsWithoutSemanticCoverage':total-len(rows)},'scoreMeaning':'Cosine similarity, not probability. RRF is rank fusion, not confidence.','results':result}

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',required=True);p.add_argument('--device',default='cpu');p.add_argument('--corpus',choices=['annotations','metadata'],default='annotations')
    sub=p.add_subparsers(dest='command',required=True);b=sub.add_parser('build');b.add_argument('--batch-size',type=int,default=32)
    s=sub.add_parser('search');s.add_argument('query');s.add_argument('--limit',type=int,default=20);s.add_argument('--game');s.add_argument('--kind',choices=['model','texture']);s.add_argument('--hybrid',action='store_true')
    s.add_argument('--diversify-pixels',action='store_true',help='One result per exact texture pixel group; equivalent occurrence keys retained')
    a=p.parse_args();db=catalog.connect(a.db);e=Encoder(device=a.device)
    result=build(db,e,a.corpus,a.batch_size) if a.command=='build' else search(db,e,a.query,a.limit,a.corpus,a.game,a.kind,a.hybrid,a.diversify_pixels)
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
