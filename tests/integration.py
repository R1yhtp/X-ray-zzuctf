#!/usr/bin/env python3
"""Behavioral integration tests: real RTL + public HTTP + independent solver."""
import concurrent.futures
import contextlib
import io
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'organizer'))
from solve import solve,request,parse_vcd

def call(base,path,data=None,ctype='application/json'):
    req=urllib.request.Request(base+path,data=data,headers={'Content-Type':ctype})
    try:
        with urllib.request.urlopen(req,timeout=30) as r: return r.status,r.read()
    except urllib.error.HTTPError as e: return e.code,e.read()

@contextlib.contextmanager
def server(flag):
    with socket.socket() as s:
        s.bind(('127.0.0.1',0));port=s.getsockname()[1]
    env=dict(os.environ,GZCTF_FLAG=flag,PORT=str(port),PYTHONDONTWRITEBYTECODE='1')
    process=subprocess.Popen([sys.executable,'app/server.py'],cwd=ROOT,env=env,
        stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    base=f'http://127.0.0.1:{port}'
    try:
        for _ in range(200):
            if process.poll() is not None: raise RuntimeError(process.stderr.read().decode())
            try:
                if call(base,'/healthz')[0]==200: break
            except OSError: pass
            time.sleep(.025)
        else: raise RuntimeError('startup timeout')
        yield base
    finally:
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired: process.kill();process.wait()
        if process.stderr: process.stderr.close()

def main():
    if not (ROOT/'build/sim.vvp').is_file():
        subprocess.run(['sh','tools/build_local.sh'],cwd=ROOT,check=True)
    begin=time.monotonic();checks=0
    flags=['zzuctf{'+secrets.token_hex(18)+'}',
           'zzuctf{AaZz09_wave-BANK_mask_'+secrets.token_hex(5)+'}',
           'zzuctf{'+('Aa0_-z9B'*10)+'}']
    instances=[]
    with tempfile.TemporaryDirectory(prefix='x-ray-tests-') as folder:
        for index,flag in enumerate(flags):
            with server(flag) as base:
                info=json.loads(request(base,'/api/info'));instances.append(info['instance'])
                for path in ['/','/app.js','/app.css','/api/info','/attachments/x-ray-player.zip']:
                    code,data=call(base,path);assert code==200
                    assert flag.encode() not in data;checks+=1
                    if path.endswith('.zip'):
                        with zipfile.ZipFile(io.BytesIO(data)) as z:
                            assert all(flag.encode() not in z.read(n) for n in z.namelist());checks+=1
                decoded=solve(base,Path(folder)/str(index),quiet=True)
                assert decoded==flag;checks+=1
                if index==0:
                    target=ROOT.parent/'qa-x-ray/recovered'
                    target.mkdir(parents=True,exist_ok=True)
                    # Retain only generated example images and report, not random flag captures.
                    for name in ['recovered.png','final-buffer.png']:
                        (target/name).write_bytes((Path(folder)/str(index)/name).read_bytes())
                    for path in ['/flag','/app/server.py','/rtl/display_core.sv','/../app/server.py','/api/capture?file=/proc/self/environ']:
                        assert call(base,path)[0]==404;checks+=1
                    good={'probes':['tx_valid','tx_ready'],'trigger':'activity','start':0,'count':32}
                    bads=[dict(good,probes=['rom_data']),dict(good,probes=['tx_valid']*2),
                        dict(good,probes=[n['name'] for n in info['signals'][:5]]),
                        dict(good,start=-1),dict(good,start=True),dict(good,count=1025),
                        dict(good,count=0),dict(good,trigger='activity;cat /flag'),
                        dict(good,out='/tmp/x'),dict(good,probes=[{}]),[],None]
                    for data in bads:
                        assert call(base,'/api/capture',json.dumps(data).encode())[0]==400;checks+=1
                    assert call(base,'/api/capture',b'{}','text/plain')[0]==415;checks+=1
                    assert call(base,'/api/capture',b' '*2049)[0]==413;checks+=1
                    assert call(base,'/api/capture',b'{')[0]==400;checks+=1
                    captures=[]
                    for _ in range(2):
                        blob=request(base,'/api/capture',good)
                        with zipfile.ZipFile(io.BytesIO(blob)) as z: captures.append(z.read('capture.vcd'))
                    assert captures[0]==captures[1];assert len(parse_vcd(captures[0]))==32;checks+=2
                    for trigger in ['clock','vblank']:
                        config=dict(good,trigger=trigger,probes=['pixel','hsync','vsync'])
                        with zipfile.ZipFile(io.BytesIO(request(base,'/api/capture',config))) as z:
                            meta=json.loads(z.read('acquisition.json'))
                            assert meta['captured']==32 and len(parse_vcd(z.read('capture.vcd')))==32;checks+=1
                    late=dict(good,start=32768)
                    with zipfile.ZipFile(io.BytesIO(request(base,'/api/capture',late))) as z:
                        assert json.loads(z.read('acquisition.json'))['captured']==0;checks+=1
                    body=json.dumps(good).encode()
                    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
                        codes=list(pool.map(lambda _:call(base,'/api/capture',body)[0],range(3)))
                    assert 200 in codes and set(codes)<={200,429};checks+=1
            print(f'PASS: instance {index+1}, dynamic flag length={len(flag)}, full black-box recovery')
        assert len(set(instances))==len(flags);checks+=1
        env=dict(os.environ);env.pop('GZCTF_FLAG',None)
        missing=subprocess.run([sys.executable,'app/server.py'],cwd=ROOT,env=env,
            capture_output=True,timeout=5)
        assert missing.returncode!=0 and b'GZCTF_FLAG' in missing.stderr;checks+=1
    report={'passed':True,'assertion_groups':checks,'dynamic_instances':len(flags),
        'wall_seconds':round(time.monotonic()-begin,2),
        'simulator':'Icarus Verilog 12.0 / vvp',
        'coverage':['actual RTL compilation','three dynamic flags including maximum length',
        'HTTP-only official solve','four-probe cap and input validation','static/file route isolation',
        'deterministic recapture','all three triggers','empty acquisition','concurrency bound',
        'startup rejects missing flag'],
        'not_run':['Docker image build/run (Docker unavailable in authoring environment)',
        'GZCTF platform integration (no platform instance supplied)','human difficulty playtest']}
    (ROOT/'organizer/VALIDATION.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
