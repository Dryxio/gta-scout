#!/usr/bin/env python3
"""Evidence-bound image packets for real agent vision; no unattended model API worker."""
import argparse, concurrent.futures, hashlib, io, json, math, os, re, sqlite3, time, urllib.request
from PIL import Image, ImageDraw
from pathlib import Path
import asset_catalog as catalog
VERSION = 'visual-packet-v1'
MAX_BYTES = 16 * 1024 * 1024
DEFAULT_PREVIEW_BASE_URL = 'https://gtastuff.namecdsl.xyz'

def sha(data): return hashlib.sha256(data).hexdigest()
def read_json(path): return json.loads(Path(path).read_text())
def write_json(path, data):
    p=Path(path); p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def image_ok(data):
    try:
        with Image.open(io.BytesIO(data)) as im:
            if im.width * im.height > 40000000: return False
            im.verify()
        return True
    except Exception: return False
def pixel_properties(data):
    with Image.open(io.BytesIO(data)) as image:
        histogram=image.convert('RGBA').getchannel('A').histogram()
        return {'width':image.width,'height':image.height,'fully_transparent_pixels':histogram[0],
                'partially_transparent_pixels':sum(histogram[1:255]),'opaque_pixels':histogram[255],
                'interpretation':'Alpha is transparency of these texture pixels, not white/gray material and not proof of a geometric hole.'}
def preview_source(row):
    p=json.loads(row['payload']); r=p['record']; prefix='' if row['game']=='sa' else row['game']+'/'
    if row['game'] not in ('sa','vc','gta3'): raise ValueError('Unsupported game')
    if row['kind']=='model': name=f"thumbnails/{r['id']}.png"
    else:
        clean=lambda x: re.sub(r'[^a-zA-Z0-9_-]','_',x).lower()
        name=f"textures/{clean(r['txd'])}__{clean(r['name'])}.png"
    configured=os.environ.get('ASSET_PREVIEW_BASE_URL')
    base=(configured if configured is not None else
          (DEFAULT_PREVIEW_BASE_URL if row['game']=='sa' else '')).rstrip('/')
    return (base+'/' if base else 'unconfigured-preview:')+prefix+name

def fetch_image(url):
    if url.startswith('unconfigured-preview:'):
        raise ValueError('No preview source configured. Supply --overrides with local images or set ASSET_PREVIEW_BASE_URL (SA uses the public GTA Stuff preview service by default).')
    if not url.startswith(('https://', 'http://')):
        raise ValueError('Preview base must use HTTP(S); use local overrides for files.')
    req=urllib.request.Request(url,headers={'User-Agent':'gta-asset-search/0.1'})
    with urllib.request.urlopen(req,timeout=25) as response:
        data=response.read(MAX_BYTES+1)
    if len(data)>MAX_BYTES: raise ValueError('Image exceeds size bound')
    if not image_ok(data): raise ValueError('Response is not a supported image')
    return data

def packet_id(entries): return catalog.digest({'version':VERSION,'entries':entries})

def prepare(db,keys,out,workers=4,refresh=False,fetcher=fetch_image,overrides=None):
    if not isinstance(keys,list) or not keys or not all(isinstance(k,str) for k in keys): raise ValueError('Nonempty asset key array required')
    if len(set(keys))!=len(keys): raise ValueError('Duplicate asset keys')
    if not 1<=workers<=16: raise ValueError('workers must be 1..16')
    out=Path(out).resolve(); out.mkdir(parents=True,exist_ok=True); cache=out/'cache'; cache.mkdir(exist_ok=True)
    jobs=[]; overrides=overrides or {}
    texture_sources={}
    for texture in db.execute("SELECT * FROM assets WHERE kind='texture'"):
        url=preview_source(texture);texture_sources.setdefault(url,[]).append(texture['key'])
    unknown=set(overrides)-set(keys)
    if unknown: raise ValueError('Overrides contain keys outside packet')
    for key in sorted(keys):
        row=db.execute('SELECT * FROM assets WHERE key=?',(key,)).fetchone()
        if not row: raise ValueError('Unknown asset: '+key)
        source=preview_source(row)
        job={'key':key,'asset_hash':row['hash'],'source':source,'kind':row['kind']}
        if key in overrides:
            paths=overrides[key]
            if not isinstance(paths,list) or not 1<=len(paths)<=8: raise ValueError('Override requires 1..8 local image paths')
            views=[]
            for path in paths:
                path=Path(path).resolve(); data=path.read_bytes()
                if not image_ok(data): raise ValueError('Invalid override image')
                views.append({'path':str(path),'sha256':sha(data)})
            job.update(source='local-render:'+catalog.digest(views),views=views)
        if row['kind']=='texture' and key not in overrides and len(texture_sources[source])>1:
            job['source_error']='CDN preview identity collides across catalog assets; require local override'
        jobs.append(job)
    def work(job):
        j=dict(job); index=cache/(sha(j['source'].encode())+'.json'); cached=False
        try:
            if j.get('source_error'):raise ValueError(j['source_error'])
            if j.get('views'):
                n=len(j['views']); cols=min(2,n); rows=math.ceil(n/cols)
                canvas=Image.new('RGB',(cols*512,rows*512),(235,235,235))
                for k,v in enumerate(j['views']):
                    im=Image.open(v['path']).convert('RGBA')
                    if n==1 and max(im.size)<512:
                        scale=min(512/im.width,512/im.height)
                        im=im.resize((max(1,round(im.width*scale)),max(1,round(im.height*scale))),Image.Resampling.NEAREST)
                    else:im.thumbnail((512,512))
                    canvas.paste(im,((k%cols)*512+(512-im.width)//2,(k//cols)*512+(512-im.height)//2),im)
                buf=io.BytesIO();canvas.save(buf,format='PNG');data=buf.getvalue();p=cache/(sha(data)+'.png')
                cached=p.exists() and sha(p.read_bytes())==sha(data);p.write_bytes(data)
            elif index.exists() and not refresh:
                previous=read_json(index); p=cache/(previous['image_sha256']+'.png')
                data=p.read_bytes()
                if sha(data)!=previous['image_sha256'] or not image_ok(data): raise ValueError('Corrupt cached image; rerun with --refresh')
                cached=True
            else:
                data=fetcher(j['source'])
                if not image_ok(data): raise ValueError('Invalid image bytes')
                h=sha(data); p=cache/(h+'.png'); p.write_bytes(data)
                write_json(index,{'source':j['source'],'image_sha256':h,'fetched_at':time.time()})
            if j['kind']=='texture':
                source_data=Path(j['views'][0]['path']).read_bytes() if len(j.get('views',[]))==1 else data
                j['pixel_properties']=pixel_properties(source_data)
            j.update(status='ready',image_sha256=sha(data),image_path=str(p),cached=cached)
        except Exception as e:j.update(status='failed',error=f'{type(e).__name__}: {e}')
        return j
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor: results=list(executor.map(work,jobs))
    # Stable identity excludes timings/cache-hit flags. Failed attempts are retried on next prepare.
    entries=[]
    for j in results:
        if j['status']=='ready':
            identity={k:j[k] for k in ('key','asset_hash','source','image_sha256')}
            j['image_id']='img_'+catalog.digest(identity)[:24]
            entries.append({k:v for k,v in j.items() if k!='cached'})
    pid=packet_id(entries); folder=out/pid; folder.mkdir(exist_ok=True)
    manifest={'version':VERSION,'packet_id':pid,'entries':entries}
    path=folder/'manifest.json'
    if path.exists() and read_json(path)!=manifest: raise ValueError('Immutable manifest collision')
    write_json(path,manifest)
    packet={'version':VERSION,'packet_id':pid,'instructions':'Inspect actual images. Describe visible form, materials, colors, condition and plausible reusable functions in French and English. Never infer from filenames or invent hidden details. Mark ambiguous views for additional rendering. No target queries are supplied. Responses must identify your actual model/reviewer and limitations.', 'images':[{k:j[k] for k in ('image_id','image_path','image_sha256')} for j in entries], 'response_schema':{'packet_id':pid,'reviews':[{'image_id':'COPY IMAGE ID','status':'accepted | ambiguous | failed','description':'visible evidence only','tags':['descriptive tags'],'confidence':'number 0..1','model':'actual reviewing model','limitations':'occlusions / uncertainty'}]}}
    for public,entry in zip(packet['images'],entries):
        if 'pixel_properties' in entry:public['pixel_properties']=entry['pixel_properties']
    write_json(folder/'packet.json',packet)
    report={'packet_id':pid,'manifest':str(path),'packet':str(folder/'packet.json'),'ready':len(entries),'failed':[j for j in results if j['status']=='failed'],'cached':sum(j.get('cached',False) for j in results)}
    write_json(out/'latest.json',report);return report

def validate_manifest(manifest):
    if manifest.get('version')!=VERSION or packet_id(manifest['entries'])!=manifest.get('packet_id'): raise ValueError('Manifest content hash mismatch')
    ids=[e['image_id'] for e in manifest['entries']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate image identities')
    for e in manifest['entries']:
        identity={k:e[k] for k in ('key','asset_hash','source','image_sha256')}
        if e['image_id']!='img_'+catalog.digest(identity)[:24]:raise ValueError('Image identity mismatch')
        for v in e.get('views',[]):
            if sha(Path(v['path']).read_bytes())!=v['sha256']:raise ValueError('Original view evidence changed')
        data=Path(e['image_path']).read_bytes()
        if sha(data)!=e['image_sha256'] or not image_ok(data): raise ValueError('Image evidence changed')

def import_reviews(db,manifest,responses):
    validate_manifest(manifest)
    if responses.get('packet_id')!=manifest['packet_id']:raise ValueError('Response packet mismatch')
    reviews=responses.get('reviews'); entries={e['image_id']:e for e in manifest['entries']}
    if not isinstance(reviews,list) or not reviews:raise ValueError('Nonempty reviews required')
    seen=set(); staged=[]
    for r in reviews:
        iid=r.get('image_id')
        if iid not in entries or iid in seen:raise ValueError('Unknown or repeated image ID')
        seen.add(iid);e=entries[iid]
        row=db.execute('SELECT * FROM assets WHERE key=?',(e['key'],)).fetchone()
        if not row or row['hash']!=e['asset_hash']:raise ValueError('Stale asset metadata')
        if e.get('views'):
            if e['source']!='local-render:'+catalog.digest(e['views']):raise ValueError('Local view source mismatch')
        elif preview_source(row)!=e['source']:raise ValueError('Asset source mismatch')
        if r.get('status') not in ('accepted','ambiguous','failed'):raise ValueError('Explicit review status required')
        c=r.get('confidence')
        if isinstance(c,bool) or not isinstance(c,(float,int)) or not math.isfinite(c) or not 0<=c<=1:raise ValueError('Invalid confidence')
        for field in ('description','model','limitations'):
            if not isinstance(r.get(field),str) or not r[field].strip():raise ValueError('Missing '+field)
        if not isinstance(r.get('tags'),list) or not all(isinstance(t,str) and t.strip() for t in r['tags']):raise ValueError('Invalid tags')
        if r['status']=='accepted' and (c<.6 or not r['tags']):raise ValueError('Accepted review needs confidence >= .6 and tags')
        staged.append((r,e,row))
    counts={'accepted':0,'ambiguous':0,'failed':0,'unchanged':0}
    if db.in_transaction:raise ValueError('Visual import requires its own immediate transaction')
    db.execute('BEGIN IMMEDIATE')
    with db:
        # Staging does not lock the catalog or the image files. Revalidate after
        # acquiring the database write lock, before any annotation is written.
        validate_manifest(manifest)
        for r,e,row in staged:
            current=db.execute('SELECT hash FROM assets WHERE key=?',(e['key'],)).fetchone()
            if not current or current['hash']!=e['asset_hash']:raise ValueError('Stale asset metadata changed before import transaction')
        db.execute('CREATE TABLE IF NOT EXISTS visual_reviews(packet_id TEXT,image_id TEXT,key TEXT,status TEXT,response TEXT,evidence TEXT,PRIMARY KEY(packet_id,image_id))')
        for r,e,row in staged:
            old=db.execute('SELECT response FROM visual_reviews WHERE packet_id=? AND image_id=?',(manifest['packet_id'],r['image_id'])).fetchone()
            if old and old[0]==catalog.canonical(r):counts['unchanged']+=1;continue
            if old:raise ValueError('Review already imported; prepare a new packet or use a distinct review workflow')
            evidence=dict(e,packet_id=manifest['packet_id'],limitations=r['limitations'],verification='local image bytes and catalog metadata checked; remote freshness requires prepare --refresh')
            db.execute('INSERT INTO visual_reviews VALUES (?,?,?,?,?,?)',(manifest['packet_id'],r['image_id'],e['key'],r['status'],catalog.canonical(r),catalog.canonical(evidence)))
            if r['status']=='accepted':
                db.execute('INSERT OR REPLACE INTO annotations VALUES (?,?,?,?,?,?,?,?)',(e['key'],e['asset_hash'],r['description'],catalog.canonical(r['tags']),'model-visual',r['model'],r['confidence'],catalog.canonical(evidence)))
                catalog.searchable(db,row['key'],row['name'],json.loads(row['payload']),row['hash'])
            else:
                db.execute('DELETE FROM annotations WHERE key=?',(e['key'],))
                catalog.searchable(db,row['key'],row['name'],json.loads(row['payload']),row['hash'])
            counts[r['status']]+=1
    return counts

def sheets(manifest,out,per_page=16,cell=320):
    validate_manifest(manifest)
    if per_page not in (4,9,16):raise ValueError('per-page must be 4, 9, or 16')
    out=Path(out).resolve();out.mkdir(parents=True,exist_ok=True); files=[]
    cols=int(math.sqrt(per_page))
    for offset in range(0,len(manifest['entries']),per_page):
        entries=manifest['entries'][offset:offset+per_page]
        page=Image.new('RGB',(cols*cell,math.ceil(len(entries)/cols)*(cell+36)),(235,235,235)); draw=ImageDraw.Draw(page)
        for i,e in enumerate(entries):
            im=Image.open(e['image_path']).convert('RGBA');im.thumbnail((cell-8,cell-8))
            x=(i%cols)*cell;y=(i//cols)*(cell+36)
            page.paste(im,(x+(cell-im.width)//2,y+(cell-im.height)//2),im)
            draw.text((x+5,y+cell+5),e['image_id'],fill=(10,10,10))
        path=out/f"sheet-{offset//per_page+1:03d}.png";page.save(path)
        files.append({'path':str(path),'sha256':sha(path.read_bytes()),'image_ids':[e['image_id'] for e in entries]})
    report={'packet_id':manifest['packet_id'],'sheets':files};write_json(out/'sheets.json',report);return report

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--db',default='output/asset-catalog/visual-v2/catalog.sqlite');s=p.add_subparsers(dest='command',required=True)
    q=s.add_parser('prepare');q.add_argument('--keys',required=True);q.add_argument('--out',required=True);q.add_argument('--workers',type=int,default=4);q.add_argument('--refresh',action='store_true');q.add_argument('--overrides')
    q=s.add_parser('sheets');q.add_argument('--manifest',required=True);q.add_argument('--out',required=True);q.add_argument('--per-page',type=int,default=16)
    q=s.add_parser('import');q.add_argument('--manifest',required=True);q.add_argument('--responses',required=True)
    a=p.parse_args()
    if not Path(a.db).is_file():p.error('Existing database required; copy baseline first')
    db=catalog.connect(a.db)
    if a.command=='prepare':result=prepare(db,read_json(a.keys),a.out,a.workers,a.refresh,overrides=read_json(a.overrides) if a.overrides else None)
    elif a.command=='sheets':result=sheets(read_json(a.manifest),a.out,a.per_page)
    else:result=import_reviews(db,read_json(a.manifest),read_json(a.responses))
    print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
