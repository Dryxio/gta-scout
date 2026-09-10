#!/usr/bin/env python3
"""Incremental, evidence-preserving GTA asset discovery pilot. Python stdlib only."""
import argparse, hashlib, json, math, re, sqlite3, time, unicodedata
from pathlib import Path

VERSION = '2'
# Deliberately narrow lexical hints. These are NOT visual classifications.
RULES = {
 'chair': (r'chair|\bseat', ['chaise', 'siege', 'chair', 'mobilier']),
 'desk': (r'desk', ['bureau', 'desk', 'mobilier']),
 'computer': (r'\b(?:computer|pc\s*\d|monitor|keyboard)', ['ordinateur', 'computer', 'informatique']),
 'toilet': (r'toilet|urinal|lavatory', ['toilettes', 'toilet', 'sanitaire']),
 'police': (r'police|sheriff|copdesk|cop\d', ['police', 'sheriff', 'commissariat']),
 'cabinet': (r'filing|cabinet', ['armoire', 'rangement', 'cabinet', 'mobilier']),
 'lamp': (r'lamp|light', ['lampe', 'eclairage']),
 'farm': (r'farm|barn|haybale', ['ferme', 'grange']),
}
SYNONYMS = {'chaises':'chaise','bureaux':'bureau','ordinateurs':'ordinateur','sherif':'sheriff','wc':'toilettes','sieges':'siege'}
STOP = {'de','du','des','la','le','les','un','une','pour','avec','dans','et','a','en','the','of','for','and'}

def canonical(value): return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))
def digest(value): return hashlib.sha256(canonical(value).encode()).hexdigest()
def tokens(value, expand=False):
    value = ''.join(c for c in unicodedata.normalize('NFKD', str(value).lower()) if not unicodedata.combining(c))
    return [SYNONYMS.get(t,t) if expand else t for t in re.findall(r'[a-z0-9]+',value) if t not in STOP]

def connect(path):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path); db.row_factory = sqlite3.Row
    db.executescript('''
    CREATE TABLE IF NOT EXISTS assets(key TEXT PRIMARY KEY,game TEXT,kind TEXT,name TEXT,hash TEXT,payload TEXT);
    CREATE TABLE IF NOT EXISTS annotations(key TEXT PRIMARY KEY,asset_hash TEXT,description TEXT,tags TEXT,method TEXT,model TEXT,confidence REAL,evidence TEXT);
    CREATE TABLE IF NOT EXISTS files(path TEXT PRIMARY KEY,size INTEGER,mtime_ns INTEGER,sha256 TEXT,kind TEXT);
    CREATE TABLE IF NOT EXISTS state(key TEXT PRIMARY KEY,value TEXT);
    CREATE VIRTUAL TABLE IF NOT EXISTS search USING fts5(key UNINDEXED,name,body,tokenize='unicode61 remove_diacritics 2');
    ''')
    return db

def load(path, default=None):
    if not Path(path).exists():
        if default is not None: return default
        raise ValueError(f'Missing input: {path}')
    try: return json.loads(Path(path).read_text())
    except (ValueError, UnicodeError) as e: raise ValueError(f'Invalid JSON: {path}: {e}') from e

def records(root,game):
    root=Path(root); models=load(root/'models/data/models.json')['models']; textures=load(root/'textures/data/textures.json')['textures']
    sizes=load(root/'models/data/model-sizes.json',{}); locations=load(root/'models/data/locations.json',{}).get('locations',{})
    seen={}
    for kind, rows in [('model',models),('texture',textures)]:
        if not isinstance(rows,list): raise ValueError(f'{kind} records must be an array')
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get('name'),str) or not row['name']: raise ValueError(f'Invalid {kind} record: {row}')
            if kind=='model':
                if 'id' not in row: raise ValueError('Model lacks id')
                key=f'{game}:model:{row["id"]}'
            else:
                if not row.get('txd'): raise ValueError('Texture lacks txd')
                key=f'{game}:texture:'+canonical([row.get('source',''),row['txd'],row['name']])
            # Identity dedup only: conflicting repeated identities invalidate the batch.
            if key in seen:
                if seen[key] != row: raise ValueError(f'Conflicting duplicate identity: {key}')
                continue
            seen[key] = row
            payload={'record':row,'catalogSource':str(root.resolve()),'identity':key,'hints':[], 'pipelineVersion':VERSION}
            if kind=='model':
                payload['dimensions']=sizes.get(str(row['id']))
                loc=locations.get(str(row['id']),{})
                payload['placements']={'count':len(loc.get('locs',[])), 'ipls':loc.get('ipls',[]),'examples':loc.get('locs',[])[:5]}
            name=tokens(row['name']); name_text=' '.join(name)
            for label,(pattern, tags) in RULES.items():
                if re.search(pattern,name_text):payload['hints'].append({'label':label,'tags':tags,'method':'filename-rule','confidence':'unverified'})
            yield key,game,kind,row['name'],payload

def evidence_views(evidence):
    views=evidence.get('views')
    if isinstance(views,list) and views:
        if not all(isinstance(v,dict) and isinstance(v.get('path'),str) and isinstance(v.get('sha256'),str) for v in views):raise ValueError('Malformed evidence views')
        return views
    if views is not None and not isinstance(views,(int,list)):raise ValueError('Malformed evidence view count')
    if evidence.get('image_path') and evidence.get('image_sha256'):
        return [{'path':evidence['image_path'],'sha256':evidence['image_sha256']}]
    if evidence.get('preview') and evidence.get('sha256'):
        return [{'path':evidence['preview'],'sha256':evidence['sha256']}]
    raise ValueError('No supported image evidence')

def annotation_is_fresh(db,annotation,cache=None):
    """Recheck image bytes per operation; transfers also depend on their live parent."""
    if not annotation:return False
    cache={} if cache is None else cache
    if annotation['method']=='shared-visual':
        from asset_catalog_pack import is_fresh
        return is_fresh(annotation,cache)
    if annotation['method'] in ('model-visual','human-visual'):
        try:
            evidence=json.loads(annotation['evidence'])
            files=evidence if isinstance(evidence,list) else evidence_views(evidence)
            if isinstance(evidence,dict) and evidence.get('image_path'):
                files=files+[{'path':evidence['image_path'],'sha256':evidence['image_sha256']}]
            if not files:return False
            for view in files:
                path=Path(view['path']);expected=view['sha256']
                # Scope this cache to one caller operation, never persist validity.
                identity=('image-bytes',str(path),expected)
                if identity not in cache:cache[identity]=hashlib.sha256(path.read_bytes()).hexdigest()==expected
                if not cache[identity]:return False
            return True
        except (KeyError,TypeError,ValueError,OSError):return False
    if annotation['method']!='exact-pixel-visual-transfer':return True
    try:
        evidence=json.loads(annotation['evidence']);identity=(evidence['parent_key'],evidence['parent_annotation_sha256'])
        if identity not in cache:
            parent=db.execute('SELECT a.hash,n.* FROM annotations n JOIN assets a ON a.key=n.key AND a.hash=n.asset_hash WHERE n.key=?',(evidence['parent_key'],)).fetchone()
            valid=parent is not None and parent['method']=='model-visual' and parent['confidence'] is not None and parent['confidence']>=.6
            if valid:
                fingerprint=digest({k:parent[k] for k in ('key','hash','description','tags','method','model','confidence','evidence')})
                valid=fingerprint==evidence['parent_annotation_sha256']
            if valid:
                original=json.loads(parent['evidence'])
                if original.get('needs_another_view') or original.get('visual_status') in ('ambiguous','failed') or original.get('status') in ('ambiguous','failed'):valid=False
                files=evidence_views(original)
                if original.get('image_path'):files=files+[{'path':original['image_path'],'sha256':original['image_sha256']}]
                valid=valid and all(hashlib.sha256(Path(v['path']).read_bytes()).hexdigest()==v['sha256'] for v in files)
            cache[identity]=valid
        return cache[identity]
    except (KeyError,TypeError,ValueError,OSError):return False

def annotation_is_usable(db,annotation,cache=None):
    if not annotation_is_fresh(db,annotation,cache):return False
    if annotation['method'] in ('model-visual','human-visual'):
        try:
            confidence=annotation['confidence'];evidence=json.loads(annotation['evidence'])
            if not isinstance(confidence,(int,float)) or not math.isfinite(confidence) or confidence<.6:return False
            if isinstance(evidence,dict) and (evidence.get('needs_another_view') or evidence.get('visual_status') in ('ambiguous','failed') or evidence.get('status') in ('ambiguous','failed')):return False
            if not isinstance(evidence,(dict,list)):return False
        except (KeyError,ValueError,TypeError):return False
    return True

def searchable(db,key,name,payload,asset_hash):
    row=payload['record']; values=[name,row.get('dff',''),row.get('txd',''),row.get('category',''), ' '.join(row.get('tags',[]))]
    values += [t for h in payload['hints'] for t in h['tags']]
    values += payload.get('placements',{}).get('ipls',[])
    a=db.execute('SELECT * FROM annotations WHERE key=? AND asset_hash=?',(key,asset_hash)).fetchone()
    if a and annotation_is_usable(db,a):values += [a['description'],a['tags']]
    rowid=db.execute('SELECT rowid FROM assets WHERE key=?',(key,)).fetchone()[0]
    db.execute('DELETE FROM search WHERE rowid=?',(rowid,))
    db.execute('INSERT INTO search(rowid,key,name,body) VALUES (?,?,?,?)',(rowid,key,' '.join(tokens(name)),' '.join(tokens(' '.join(values)))))

def build(db,root,game='sa'):
    start=time.monotonic(); stats={'inserted':0,'updated':0,'unchanged':0,'deleted':0}
    # Build inside one transaction: malformed input never partially replaces an existing catalog.
    with db:
        db.execute('CREATE TEMP TABLE IF NOT EXISTS seen(key TEXT PRIMARY KEY)');db.execute('DELETE FROM seen')
        for key,game,kind,name,payload in records(root,game):
            h=digest(payload); old=db.execute('SELECT hash FROM assets WHERE key=?',(key,)).fetchone()
            db.execute('INSERT INTO seen VALUES (?)',(key,))
            if old and old[0]==h:stats['unchanged']+=1;continue
            stats['updated' if old else 'inserted']+=1
            db.execute('INSERT INTO assets VALUES (?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET game=excluded.game,kind=excluded.kind,name=excluded.name,hash=excluded.hash,payload=excluded.payload',(key,game,kind,name,h,canonical(payload)))
            searchable(db,key,name,payload,h)
        stale=db.execute('SELECT key FROM assets WHERE game=? AND key NOT IN (SELECT key FROM seen)',(game,)).fetchall()
        for (key,) in stale:
            db.execute('DELETE FROM search WHERE rowid=(SELECT rowid FROM assets WHERE key=?)',(key,));db.execute('DELETE FROM assets WHERE key=?',(key,))
        stats['deleted']=len(stale)
    stats['seconds']=round(time.monotonic()-start,3)
    return stats

def search(db,query,limit=20,kind=None,game=None,max_width=None):
    if limit < 1 or limit > 1000: raise ValueError('limit must be between 1 and 1000')
    words=list(dict.fromkeys(tokens(query,True)))
    if not words:return []
    # OR retrieves partial candidates; coverage is exposed so partial matches are not guarantees.
    expression=' OR '.join('"'+w+'"' for w in words)
    sql='SELECT a.*,bm25(search,0,4,1) rank FROM search JOIN assets a ON a.key=search.key WHERE search MATCH ?'
    params=[expression]
    if kind:sql+=' AND a.kind=?';params.append(kind)
    if game:sql+=' AND a.game=?';params.append(game)
    if max_width is not None:
        sql+=" AND json_type(a.payload,'$.dimensions.width') IN ('integer','real') AND json_extract(a.payload,'$.dimensions.width')<=?";params.append(max_width)
    sql+=' ORDER BY rank,a.key LIMIT 1000'
    results=[];freshness_cache={}
    for r in db.execute(sql,params):
        p=json.loads(r['payload']); dims=p.get('dimensions') or {}
        if max_width is not None and (not isinstance(dims.get('width'),(int,float)) or dims['width']>max_width):continue
        a=db.execute('SELECT * FROM annotations WHERE key=? AND asset_hash=?',(r['key'],r['hash'])).fetchone()
        if a and not annotation_is_usable(db,a,freshness_cache):continue
        indexed=db.execute('SELECT name,body FROM search WHERE rowid=(SELECT rowid FROM assets WHERE key=?)',(r['key'],)).fetchone()
        matched=[w for w in words if w in set((indexed['name']+' '+indexed['body']).split())]
        results.append({'matchedTerms':matched,'queryCoverage':round(len(matched)/len(words),3),'key':r['key'],'name':r['name'],'kind':r['kind'],'score':round(-r['rank'],4),'record':p['record'],'dimensions':p.get('dimensions'),'placements':p.get('placements'),'hints':p['hints'],'annotation':dict(a) if a else None,'catalogSource':p['catalogSource']})
        if len(results)>=limit:break
    return results

def annotate(db,path):
    entries=load(path); entries=entries if isinstance(entries,list) else [entries]
    with db:
        for a in entries:
            row=db.execute('SELECT * FROM assets WHERE key=?',(a.get('key'),)).fetchone()
            if not row:raise ValueError('Annotation asset does not exist')
            if a.get('asset_hash')!=row['hash']:raise ValueError('Stale annotation asset_hash')
            if a.get('method') not in ('human-visual','model-visual','curated-context'):raise ValueError('Explicit annotation method required')
            if not a.get('evidence') or not a.get('model'):raise ValueError('Evidence and annotator/model required')
            confidence=a.get('confidence')
            if not isinstance(confidence,(int,float)) or not math.isfinite(confidence) or not 0<=confidence<=1:raise ValueError('Confidence must be finite in [0,1]')
            if not isinstance(a.get('description'),str) or not isinstance(a.get('tags'),list) or not all(isinstance(t,str) for t in a['tags']):raise ValueError('Description and string tags required')
            db.execute('INSERT OR REPLACE INTO annotations VALUES (?,?,?,?,?,?,?,?)',(a['key'],a['asset_hash'],a['description'],canonical(a['tags']),a['method'],a['model'],confidence,canonical(a['evidence'])))
            searchable(db,row['key'],row['name'],json.loads(row['payload']),row['hash'])
    return {'imported':len(entries)}

def scan(db,root,verify=False):
    """Exact binary SHA-256 groups. Stat cache optional; verify catches preserved-mtime edits."""
    root=Path(root).resolve()
    if not root.is_dir(): raise ValueError(f'Asset root is not a directory: {root}')
    stats={'hashed':0,'cached':0,'deleted':0,'bytesHashed':0}; seen=set()
    for p in sorted(root.rglob('*')):
        if not p.is_file() or p.suffix.lower() not in {'.dff','.txd','.png','.jpg','.webp','.col'}:continue
        name=str(p.resolve()); seen.add(name); s=p.stat(); old=db.execute('SELECT * FROM files WHERE path=?',(name,)).fetchone()
        if old and not verify and old['size']==s.st_size and old['mtime_ns']==s.st_mtime_ns:stats['cached']+=1;continue
        h=hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(1024*1024),b''):h.update(chunk)
        after=p.stat()
        if (s.st_size,s.st_mtime_ns)!=(after.st_size,after.st_mtime_ns):raise ValueError(f'File changed during hash: {p}')
        with db:db.execute('INSERT OR REPLACE INTO files VALUES (?,?,?,?,?)',(name,s.st_size,s.st_mtime_ns,h.hexdigest(),p.suffix.lower()[1:]))
        stats['hashed']+=1;stats['bytesHashed']+=s.st_size
    # Scope cleanup to this exact directory; sibling prefixes must survive.
    with db:
        for row in db.execute('SELECT path FROM files').fetchall():
            if Path(row['path']).is_relative_to(root) and row['path'] not in seen:
                db.execute('DELETE FROM files WHERE path=?',(row['path'],));stats['deleted']+=1
    stats['duplicateGroups']=db.execute('SELECT count(*) FROM (SELECT sha256 FROM files GROUP BY sha256 HAVING count(*)>1)').fetchone()[0]
    return stats

def jobs(db,limit,max_confidence=0.5):
    if not 1 <= limit <= 10000: raise ValueError('jobs limit must be between 1 and 10000')
    if not math.isfinite(max_confidence) or not 0 <= max_confidence <= 1: raise ValueError('max-confidence must be in [0,1]')
    return [dict(r) for r in db.execute("SELECT a.key,a.name,a.kind,a.hash asset_hash,a.payload,CASE WHEN n.key IS NULL THEN 'missing-or-stale' ELSE 'low-confidence' END reason FROM assets a LEFT JOIN annotations n ON n.key=a.key AND n.asset_hash=a.hash WHERE n.key IS NULL OR n.confidence<=? ORDER BY CASE WHEN n.key IS NULL THEN 1 ELSE 0 END,a.key LIMIT ?",(max_confidence,limit))]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',default='output/asset-catalog/catalog.sqlite')
    sub=p.add_subparsers(dest='command',required=True)
    b=sub.add_parser('build');b.add_argument('--root',default='.');b.add_argument('--game',default='sa')
    s=sub.add_parser('search');s.add_argument('query');s.add_argument('--limit',type=int,default=20);s.add_argument('--kind',choices=['model','texture']);s.add_argument('--game');s.add_argument('--max-width',type=float)
    a=sub.add_parser('annotate');a.add_argument('file')
    f=sub.add_parser('scan');f.add_argument('root');f.add_argument('--verify',action='store_true')
    j=sub.add_parser('jobs');j.add_argument('--limit',type=int,default=100);j.add_argument('--max-confidence',type=float,default=0.5)
    sub.add_parser('stats')
    sub.add_parser('duplicates')
    args=p.parse_args();db=connect(args.db)
    if args.command=='build':result=build(db,args.root,args.game)
    elif args.command=='search':result=search(db,args.query,args.limit,args.kind,args.game,args.max_width)
    elif args.command=='annotate':result=annotate(db,args.file)
    elif args.command=='scan':result=scan(db,args.root,args.verify)
    elif args.command=='jobs':result=jobs(db,args.limit,args.max_confidence)
    elif args.command=='duplicates':result=[{'sha256':r[0],'sources':[dict(f) for f in db.execute('SELECT path,size,kind FROM files WHERE sha256=? ORDER BY path',(r[0],))]} for r in db.execute('SELECT sha256 FROM files GROUP BY sha256 HAVING count(*)>1 ORDER BY sha256')]
    else:result={'assets':[dict(r) for r in db.execute('SELECT game,kind,count(*) count FROM assets GROUP BY game,kind')], 'files':db.execute('SELECT count(*) FROM files').fetchone()[0], 'annotations':db.execute('SELECT count(*) FROM annotations').fetchone()[0]}
    print(json.dumps(result,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
