#!/usr/bin/env python3
"""Official black-box solve. Python >=3.10, standard library only.

Uses only the public player attachment and /api/capture; never imports server code.
"""
import argparse
import io
import json
from pathlib import Path
import re
import struct
import time
import urllib.error
import urllib.request
import zipfile
import zlib

def request(base,path,payload=None):
    body=None if payload is None else json.dumps(payload).encode()
    headers={} if body is None else {'Content-Type':'application/json'}
    req=urllib.request.Request(base.rstrip('/')+path,data=body,headers=headers)
    for attempt in range(12):
        try:
            with urllib.request.urlopen(req,timeout=30) as response: return response.read()
        except urllib.error.HTTPError as exc:
            if exc.code!=429 or attempt==11: raise
            time.sleep(.25)

def parse_vcd(data):
    names={}; values={}; records=[]; tick=0
    for raw in data.decode('ascii').splitlines():
        line=raw.strip()
        if line.startswith('$var'):
            parts=line.split();names[parts[3]]=parts[4]
        elif line.startswith('#'):
            tick=int(line[1:])
        elif line.startswith('b'):
            bits,code=line[1:].split()
            if any(c in bits.lower() for c in 'xz'): raise ValueError('unknown signal in captured record')
            values[names[code]]=int(bits,2)
        elif line and line[0] in '01' and line[1:] in names:
            name=names[line[1:]];values[name]=int(line[0])
            if name=='sample' and line[0]=='1':
                records.append((tick,{k:v for k,v in values.items() if k!='sample'}))
    return records

def fetch_trace(base,probes,start,count):
    result=request(base,'/api/capture',{
        'probes':probes,'trigger':'activity','start':start,'count':count})
    with zipfile.ZipFile(io.BytesIO(result)) as archive:
        meta=json.loads(archive.read('acquisition.json'))
        vcd=archive.read('capture.vcd')
    rows=parse_vcd(vcd)
    if len(rows)!=meta['captured']: raise ValueError('VCD count mismatch')
    return rows,meta,vcd

def physical(y,col):
    # Inverted from scanout's public 16x8 tile/serpentine wiring.
    tile_y=y//8
    tile_x=11-col if tile_y%2 else col
    return (tile_y*12+tile_x)*8+y%8

def pixels_from_words(words):
    return [[(words[physical(y,x//16)]>>(x%16))&1 for x in range(192)] for y in range(64)]

def png(pixels,scale=4):
    def chunk(kind,data):
        return struct.pack('>I',len(data))+kind+data+struct.pack('>I',zlib.crc32(kind+data)&0xffffffff)
    height=len(pixels);width=len(pixels[0]);rows=[]
    for row in pixels:
        line=b''.join((bytes((205,228,169)) if value else bytes((13,25,18)))*scale for value in row)
        rows.extend([b'\0'+line]*scale)
    return b'\x89PNG\r\n\x1a\n'+chunk(b'IHDR',struct.pack('>IIBBBBB',width*scale,height*scale,8,2,0,0,0))+chunk(b'IDAT',zlib.compress(b''.join(rows)))+chunk(b'IEND',b'')

def read_text(pixels,font):
    lookup={tuple(rows):char for char,rows in font.items()}
    text=[]
    for index in range(90):
        left=6+(index%30)*6;top=14+(index//30)*10
        glyph=tuple(sum(pixels[top+y][left+x]<<(4-x) for x in range(5)) for y in range(7))
        if glyph not in lookup: raise ValueError(f'unknown glyph {index}: {glyph}')
        text.append(lookup[glyph])
    result=''.join(text).rstrip()
    if not re.fullmatch(r'zzuctf\{[A-Za-z0-9_-]{1,80}\}',result):
        raise ValueError('decoded image does not contain a complete flag')
    return result

def solve(base,output,quiet=False):
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    handout=request(base,'/attachments/x-ray-player.zip')
    with zipfile.ZipFile(io.BytesIO(handout)) as z: font=json.loads(z.read('font5x7.json'))
    group_a=['tx_valid','tx_ready','tx_bank','tx_mask']
    group_b=['tx_addr','tx_data']
    all_rows=[];instance=None;total=None;start=0
    while total is None or start<total:
        a,ma,va=fetch_trace(base,group_a,start,1024)
        b,mb,vb=fetch_trace(base,group_b,start,1024)
        instance=instance or ma['instance']
        if ma['instance']!=instance or mb['instance']!=instance:
            raise ValueError('instance changed while capturing; restart the solve')
        if ma['total_events']!=mb['total_events']: raise ValueError('inconsistent event universe')
        if [t for t,_ in a]!=[t for t,_ in b]: raise ValueError('probe timestamps do not align')
        total=ma['total_events']
        for (tick,controls),(_,bus) in zip(a,b): all_rows.append((tick,dict(controls,**bus)))
        (output/f'controls-{start}.vcd').write_bytes(va)
        (output/f'bus-{start}.vcd').write_bytes(vb)
        if not quiet: print(f'[+] aligned {start+len(a)}/{total} candidate events')
        start+=1024
    # Public state machine: 768 clear writes, then 2 byte writes per word.
    snapshot_after=768+2*768
    banks=[[0]*768 for _ in range(2)]
    accepted=0;snapshot=None
    for tick,row in all_rows:
        if not (row['tx_valid'] and row['tx_ready']): continue
        bank=row['tx_bank'];addr=row['tx_addr'];value=row['tx_data'];mask=row['tx_mask']
        if not (0<=addr<768): raise ValueError('invalid captured address')
        old=banks[bank][addr]
        if mask&1: old=(old&0xff00)|(value&0xff)
        if mask&2: old=(old&0x00ff)|(value&0xff00)
        banks[bank][addr]=old
        accepted+=1
        if accepted==snapshot_after: snapshot=banks[1].copy()
    if snapshot is None or accepted!=3072: raise ValueError(f'incomplete write history: {accepted}')
    if any(banks[1]): raise ValueError('final backbuffer should have been scrubbed')
    pixels=pixels_from_words(snapshot)
    flag=read_text(pixels,font)
    (output/'recovered.png').write_bytes(png(pixels))
    (output/'final-buffer.png').write_bytes(png(pixels_from_words(banks[1])))
    (output/'flag.txt').write_text(flag+'\n')
    (output/'solve-report.json').write_text(json.dumps({'instance':instance,'candidate_events':len(all_rows),
        'accepted_writes':accepted,'snapshot_after_write':snapshot_after,'flag':flag},indent=2))
    if not quiet:
        print(f'[+] {accepted} accepted writes; snapshot before scrub; final bank is blank')
        print(flag)
        print(f'[+] image: {output.resolve()/"recovered.png"}')
    return flag

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('url');parser.add_argument('--out',default='recovered')
    args=parser.parse_args()
    solve(args.url,args.out)
