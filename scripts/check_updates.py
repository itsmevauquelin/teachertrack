#!/usr/bin/env python3
"""Daily official-source change detector for TeacherTrack.

This deliberately detects SOURCE changes, not changes to admissions facts. New
content is flagged for human verification; catalog unknowns are never filled in
from guesses or page hashes.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from io import BytesIO
from difflib import SequenceMatcher
import hashlib
import json
import re
import sys
import time

import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / 'data/catalog.json'
MONITOR = ROOT / 'data/monitor.json'
SNAPSHOTS = ROOT / 'data/source_snapshots.json'
USER_AGENT = 'TeacherTrackOfficialSourceMonitor/1.0 (personal admissions tracker; daily; no scraping API)'


def load(path, fallback):
    if not path.exists():
        return fallback
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return fallback


def normalize(text: str) -> str:
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:300000]


def download(source):
    url = source['url']
    domain = (urlparse(url).hostname or '').lower()
    if not domain.endswith(('.ujep.cz', '.tul.cz', '.upol.cz', '.muni.cz')):
        raise ValueError('Source is not an allowed official university host')
    response = requests.get(url, headers={'User-Agent':USER_AGENT, 'Accept-Language':'cs,en;q=0.8'}, timeout=(12,35))
    response.raise_for_status()
    if source['type']=='pdf':
        reader = PdfReader(BytesIO(response.content))
        return normalize(' '.join(page.extract_text() or '' for page in reader.pages))
    soup = BeautifulSoup(response.text, 'html.parser')
    for el in soup.select('script,style,nav,header,footer,aside,noscript,form,svg'):
        el.decompose()
    main = soup.find('main') or soup.find('article') or soup.body or soup
    text = main.get_text(' ', strip=True)
    if len(text)<100:
        raise ValueError('Source returned unusually little readable text')
    return normalize(text)


def excerpt(before, after):
    matcher = SequenceMatcher(None, before, after, autojunk=True)
    bits=[]
    for tag,i,j,x,y in matcher.get_opcodes():
        if tag=='equal': continue
        if tag in ('insert','replace') and after[x:y].strip():
            bits.append('Added/edited: '+after[x:y][:160])
        elif tag=='delete' and before[i:j].strip():
            bits.append('Removed: '+before[i:j][:160])
        if len(bits)>=2: break
    return ' | '.join(bits)[:370] or 'The source text fingerprint changed; review the official page.'


def main():
    catalog=load(CATALOG,{})
    monitor=load(MONITOR,{'lastChecked':None,'dailyChecks':[],'events':[],'sourceStatuses':{}})
    snapshots=load(SNAPSHOTS,{})
    now=datetime.now(timezone.utc)
    day=now.date().isoformat()
    changed=failed=ok=baselined=0
    ids=set()
    for src in catalog.get('sources',[]):
        key=src['id']; ids.add(key)
        try:
            content=download(src)
            digest=hashlib.sha256(content.encode('utf-8')).hexdigest()
            old=snapshots.get(key)
            if old and old.get('sha256') != digest:
                event_id=f'change-{key}-{digest[:12]}'
                if not any(ev.get('id')==event_id for ev in monitor.get('events',[])):
                    monitor.setdefault('events',[]).insert(0,{
                        'id':event_id,'date':day,'type':'changed','severity':'high',
                        'programs':src['programs'],'title':f'Official source changed · {src["label"]}',
                        'detail':excerpt(old.get('text',''),content),
                        'sourceId':key,
                        'requiresReview':True
                    })
                changed+=1
                status='changed'
            elif not old:
                baselined+=1
                status='baseline'
            else:
                ok+=1
                status='unchanged'
            snapshots[key]={'sha256':digest,'text':content,'capturedAt':now.isoformat()}
            monitor.setdefault('sourceStatuses',{})[key]={
                'state':status,'checkedAt':now.isoformat(),'http':'ok',
                'sha256':digest
            }
        except Exception as exc:
            failed+=1
            detail=f'{type(exc).__name__}: {str(exc)[:200]}'
            monitor.setdefault('sourceStatuses',{})[key]={
                'state':'unavailable','checkedAt':now.isoformat(),'http':'error', 'error':detail
            }
            event_id=f'error-{key}-{day}'
            if not any(ev.get('id')==event_id for ev in monitor.get('events',[])):
                monitor.setdefault('events',[]).insert(0,{
                    'id':event_id,'date':day,'type':'attention','severity':'medium',
                    'programs':src['programs'],'title':f'Source could not be checked · {src["label"]}',
                    'detail':'Monitoring failed for this source. This is not evidence that admission rules changed. '+detail,
                    'sourceId':key, 'requiresReview':True
                })
        # A courtesy delay between external requests, avoiding server overload.
        time.sleep(0.5)
    monitor['lastChecked']=now.isoformat()
    monitor.setdefault('dailyChecks',[]).insert(0,{
        'date':day,'checkedAt':now.isoformat(),'sources':len(ids),'unchanged':ok,
        'changed':changed,'baselined':baselined,'failed':failed
    })
    monitor['dailyChecks']=monitor['dailyChecks'][:120]
    monitor['events']=monitor.get('events',[])[:200]
    for path,obj in [(MONITOR,monitor),(SNAPSHOTS,snapshots)]:
        path.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(f'{day}: checked {len(ids)} official sources; {changed} changed; {failed} inaccessible; {baselined} initial baselines; {ok} unchanged')
    # Source errors are visible in the site; keep workflow running for later days.
    return 0


if __name__=='__main__':
    sys.exit(main())
