"""Portable reviewed text packs; never distribute game files or local evidence paths."""
import argparse
import collections
import hashlib
import json
import math
import re
import sqlite3
from pathlib import Path

import asset_catalog as catalog
from asset_catalog_sources import img_entries

VERSION = 'gta-scout-annotations-v1'
METHOD = 'shared-visual'
SHA = re.compile(r'^[0-9a-f]{64}$')
PRIVATE = re.compile(r'(?i)(/Users/|/home/|[a-z]:[\\/]|https?://|file://|ssh://|@[a-z0-9.-]+\.[a-z]{2,})')


def clean_text(value):
    if not isinstance(value, str) or len(value) > 16000 or PRIVATE.search(value):
        raise ValueError('Public text contains a path/URL or is invalid; review before publishing')
    return value


def basename(value):
    return str(value).replace('\\', '/').rsplit('/', 1)[-1]


def source_ok(source, cache):
    identity = (source['path'], source['offset'], source['bytes'], source['sha256'])
    if identity not in cache:
        with open(source['path'], 'rb') as stream:
            stream.seek(source['offset'])
            data = stream.read(source['bytes'])
        cache[identity] = len(data) == source['bytes'] and hashlib.sha256(data).hexdigest() == source['sha256']
    return cache[identity]


def is_fresh(annotation, cache):
    try:
        evidence = json.loads(annotation['evidence'])
        sources = evidence['local_sources']
        return (annotation['confidence'] is not None and math.isfinite(annotation['confidence'])
                and .6 <= annotation['confidence'] <= 1
                and bool(sources) and all(source_ok(s, cache) for s in sources))
    except (ValueError, KeyError, TypeError, OSError):
        return False


def public_source(source):
    path = source.get('path') or source.get('archive') or source.get('file')
    entry = source.get('entry') or basename(path)
    if not path or not SHA.fullmatch(source.get('sha256', '')):
        raise ValueError('Source fingerprint missing')
    return {'archive': basename(path) if str(path).lower().endswith('.img') else None,
            'entry': basename(entry), 'bytes': source['bytes'], 'sha256': source['sha256']}


def bindings(row, evidence, audit):
    """Recover bindings only from manifests connected to actually reviewed views."""
    if row['kind'] == 'texture':
        from asset_catalog_transfer_pixels import pixel_hash
        observed = evidence.get('parent_evidence', evidence)
        views = observed.get('views', [])
        if not isinstance(views,list) or len(views) != 1:
            return []
        record = audit.get(row['key'])
        if not record or record['status'] != 'resolved' or len(record['sources']) != 1:
            return []
        native = json.loads(row['payload'])['record']
        if any(native.get(k) != record.get(k) for k in ('name', 'txd')) or native.get('source') != record['archive']:
            return []
        pixel = pixel_hash(views[0]['path'])
        if pixel != record['pixelSha256']:
            return []
        return [public_source(record['sources'][0]['source'])]
    views = evidence.get('views', [])
    if not isinstance(views,list) or not views:
        return []
    path = Path(views[0]['path']).parent / 'manifest.json'
    if not path.exists():
        return []
    manifest = json.loads(path.read_text())
    if manifest.get('id') != row['key'] or manifest.get('status') != 'ready':
        return []
    reviewed = {(v['path'], v['sha256']) for v in views}
    rendered = {(v['path'], v['sha256']) for v in manifest.get('views', [])}
    if not reviewed or not reviewed.issubset(rendered):
        return []
    sources = manifest.get('sourceExtraction', [])
    hashes = set(manifest.get('sourceSha256', {}).values())
    if not sources or any(s['sha256'] not in hashes for s in sources):
        return []
    result = [public_source(s) for s in sources]
    if not any(s['entry'].lower().endswith('.dff') for s in result):
        return []
    return result


def export_pack(db, version, audit=None):
    audit = {r['key']: r for r in (audit or [])}
    entries = []; skipped = collections.Counter(); cache = {}
    sql = 'SELECT a.*,n.description,n.tags,n.method,n.model,n.confidence,n.evidence FROM assets a JOIN annotations n ON a.key=n.key AND a.hash=n.asset_hash ORDER BY a.key'
    for row in db.execute(sql):
        if row['method'] not in ('model-visual', 'human-visual', 'exact-pixel-visual-transfer') or not catalog.annotation_is_usable(db, row, cache):
            skipped['unusable'] += 1
            continue
        evidence = json.loads(row['evidence']); record = json.loads(row['payload'])['record']
        observed = evidence.get('parent_evidence', evidence)
        selector = {k: clean_text(record[k]) for k in ('name', 'dff', 'txd') if k in record}
        if row['kind'] == 'texture':
            selector['archive'] = basename(record.get('source', ''))
        entry = {'game': row['game'], 'kind': row['kind'], 'selector': selector,
                 'description': clean_text(row['description']),
                 'tags': [clean_text(t) for t in json.loads(row['tags'])],
                 'confidence': row['confidence'], 'review_method': row['method'],
                 'limitations': clean_text(observed.get('limitations', 'Only reviewed views are described.')),
                 'image_sha256': sorted({v['sha256'] for v in catalog.evidence_views(observed)}),
                 'sources': bindings(row, evidence, audit)}
        entry['id'] = catalog.digest(entry)
        entries.append(entry)
    pack = {'format': VERSION, 'version': version, 'license': 'MIT',
            'scope': 'Reviewed text only. Shared publisher observations, not a local visual inspection. Entries without source bindings are reference-only; inspect your own asset before use.',
            'entries': entries}
    pack['sha256'] = catalog.digest(pack)
    return pack, dict(skipped)


def validate(pack):
    if set(pack) - {'format','version','license','scope','entries','sha256'}:
        raise ValueError('Unexpected public pack fields')
    clean_text(pack['version'])
    if pack.get('license') != 'MIT': raise ValueError('Unsupported pack license')
    if pack.get('format') != VERSION or pack.get('sha256') != catalog.digest({k:v for k,v in pack.items() if k != 'sha256'}):
        raise ValueError('Invalid pack format or digest')
    ids = set()
    for e in pack['entries']:
        if set(e) != {'id','game','kind','selector','description','tags','confidence','review_method','limitations','image_sha256','sources'}:
            raise ValueError('Unexpected public entry fields')
        if e['review_method'] not in ('model-visual','human-visual','exact-pixel-visual-transfer'):
            raise ValueError('Unsupported review provenance')
        if set(e['selector']) - {'name','dff','txd','archive'} or 'name' not in e['selector']:
            raise ValueError('Invalid selector')
        if e['kind']=='texture' and not {'txd','archive'}.issubset(e['selector']):
            raise ValueError('Texture occurrence selector missing')
        if e['id'] in ids or e['id'] != catalog.digest({k:v for k,v in e.items() if k != 'id'}):
            raise ValueError('Duplicate or invalid entry digest')
        ids.add(e['id'])
        if e['game'] not in ('sa','vc','gta3') or e['kind'] not in ('model','texture'):
            raise ValueError('Unsupported identity')
        clean_text(e['description']); clean_text(e['limitations'])
        for t in e['tags']: clean_text(t)
        if not isinstance(e['confidence'], (int,float)) or not math.isfinite(e['confidence']) or not .6 <= e['confidence'] <= 1:
            raise ValueError('Invalid confidence')
        for value in e['selector'].values():
            if not value or basename(value) != value: raise ValueError('Nonportable selector')
            clean_text(value)
        if not e['image_sha256'] or not all(SHA.fullmatch(h) for h in e['image_sha256']):
            raise ValueError('Missing review fingerprints')
        for source in e['sources']:
            if set(source) != {'archive','entry','bytes','sha256'}:
                raise ValueError('Unexpected public source fields')
            for field in ('entry','archive'):
                value=source[field]
                if value is not None and (not value or basename(value) != value or value in ('.','..')): raise ValueError('Unsafe source name')
            if not SHA.fullmatch(source['sha256']) or not isinstance(source['bytes'],int) or not 0 < source['bytes'] <= 64*1024*1024:
                raise ValueError('Invalid source binding')
    return pack


def local_sources(game_root, archives=()):
    """Build a local locator; pack paths are never opened or executed."""
    root = Path(game_root).resolve()
    folders=[p for p in root.iterdir() if p.is_dir() and p.name.lower()=='models']
    if len(folders)!=1: raise ValueError('Expected one models directory in game root')
    index=collections.defaultdict(list)
    paths = sorted(p for p in folders[0].rglob('*') if p.is_file())
    paths += [Path(p).resolve() for p in archives]
    for path in dict.fromkeys(paths):
        if path.suffix.lower()=='.img':
            for name, offset, length in img_entries(path):
                if name.lower().endswith(('.dff','.txd')):
                    index[(path.name.lower(),name.lower())].append({'path':str(path.resolve()),'offset':offset,'bytes':length})
        elif path.suffix.lower() in ('.dff','.txd'):
            index[(None,path.name.lower())].append({'path':str(path.resolve()),'offset':0,'bytes':path.stat().st_size})
    return index


def import_pack(db, pack, index, apply=False):
    validate(pack)
    counts=collections.Counter(); staged=[]; cache={}; selected=set()
    assets=list(db.execute('SELECT * FROM assets'))
    by_selector=collections.defaultdict(list)
    for a in assets:
        r=json.loads(a['payload'])['record']
        by_selector[(a['game'],a['kind'],r['name'].lower(),r.get('txd','').lower())].append(a)
    for e in pack['entries']:
        if not e['sources']:
            counts['reference_only']+=1; continue
        locators=[]
        for s in e['sources']:
            found=index.get((s['archive'].lower() if s['archive'] else None,s['entry'].lower()),[])
            if len(found)!=1 or found[0]['bytes'] != s['bytes']: break
            source=dict(found[0],sha256=s['sha256'])
            if not source_ok(source,cache): break
            locators.append(source)
        if len(locators)!=len(e['sources']):
            counts['source_mismatch_or_missing']+=1;continue
        selector=e['selector']
        targets=by_selector.get((e['game'],e['kind'],selector['name'].lower(),selector.get('txd','').lower()),[])
        for a in targets:
            r=json.loads(a['payload'])['record']
            if e['kind']=='model' and r.get('dff',r['name']).lower()!=selector.get('dff',selector['name']).lower():continue
            if e['kind']=='texture' and basename(r.get('source','')).lower()!=selector['archive'].lower():continue
            if a['key'] in selected:
                raise ValueError('Conflicting pack entries for local asset '+a['key'])
            selected.add(a['key'])
            old=db.execute('SELECT * FROM annotations WHERE key=?',(a['key'],)).fetchone()
            if old and old['method']!=METHOD:
                counts['preserved_local_review']+=1;continue
            evidence={'pack_sha256':pack['sha256'],'pack_version':pack['version'],'entry_id':e['id'],
                      'image_sha256':e['image_sha256'],'local_sources':locators,'limitations':e['limitations'],
                      'verification':'Publisher visual review; local source bytes matched. No local image review performed.'}
            staged.append((a,e,evidence))
        if not targets: counts['no_catalog_match']+=1
    if apply:
        with db:
            verified={}
            for a,e,evidence in staged:
                current=db.execute('SELECT hash FROM assets WHERE key=?',(a['key'],)).fetchone()
                if not current or current['hash']!=a['hash'] or not all(source_ok(s,verified) for s in evidence['local_sources']):
                    raise ValueError('Local asset changed before import')
            for a,e,evidence in staged:
                db.execute('INSERT OR REPLACE INTO annotations VALUES (?,?,?,?,?,?,?,?)',
                           (a['key'],a['hash'],e['description'],catalog.canonical(e['tags']),METHOD,
                            'shared-pack:'+pack['version'],e['confidence'],catalog.canonical(evidence)))
                catalog.searchable(db,a['key'],a['name'],json.loads(a['payload']),a['hash'])
    return {'applied':apply,'eligible':len(staged),**dict(counts)}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--db')
    sub=parser.add_subparsers(dest='command',required=True)
    p=sub.add_parser('export');p.add_argument('--out',required=True);p.add_argument('--version',required=True);p.add_argument('--audit')
    p=sub.add_parser('import');p.add_argument('--pack',required=True);p.add_argument('--game-root',required=True);p.add_argument('--archive',action='append',default=[]);p.add_argument('--apply',action='store_true')
    p=sub.add_parser('inspect');p.add_argument('--pack',required=True)
    args=parser.parse_args()
    if args.command=='inspect':
        pack=validate(catalog.load(args.pack));print(json.dumps({'version':pack['version'],'entries':len(pack['entries']),'source_bound':sum(bool(e['sources']) for e in pack['entries']),'sha256':pack['sha256']},indent=2));return
    if not args.db:parser.error('--db required')
    if args.command=='export':
        db=sqlite3.connect(Path(args.db).resolve().as_uri()+'?mode=ro',uri=True);db.row_factory=sqlite3.Row
        pack,skipped=export_pack(db,args.version,catalog.load(args.audit) if args.audit else None)
        validate(pack)
        with open(args.out,'x') as stream:stream.write(json.dumps(pack,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'entries':len(pack['entries']),'source_bound':sum(bool(e['sources']) for e in pack['entries']),'skipped':skipped}))
    else:
        pack=validate(catalog.load(args.pack));index=local_sources(args.game_root,args.archive)
        db=sqlite3.connect(Path(args.db).resolve().as_uri()+('?mode=rw' if args.apply else '?mode=ro'),uri=True);db.row_factory=sqlite3.Row
        print(json.dumps(import_pack(db,pack,index,args.apply),indent=2))

if __name__=='__main__': main()
