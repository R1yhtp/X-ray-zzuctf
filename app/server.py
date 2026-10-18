#!/usr/bin/env python3
"""GZCTF X-ray: bounded acquisition of a real SystemVerilog simulation."""
import hashlib
import http.server
import io
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from urllib.parse import urlsplit
import zipfile

from font import rasterize

ROOT=Path(__file__).resolve().parents[1]
PORT=int(os.environ.get('PORT','8000'))
SIGNALS=[('tx_valid',1),('tx_ready',1),('tx_bank',1),('tx_mask',2),
         ('tx_addr',10),('tx_data',16),('hsync',1),('vsync',1),
         ('pixel',1),('fence',1),('hpos',8),('vpos',7)]
TRIGGERS={'clock':0,'activity':1,'vblank':2}
FLAG=os.environ.get('GZCTF_FLAG','')
if not re.fullmatch(r'zzuctf\{[A-Za-z0-9_-]{1,80}\}',FLAG):
    raise SystemExit('GZCTF_FLAG must be zzuctf{...}, 1-80 ASCII letters/digits/_/- inside braces')
SIM=Path(os.environ.get('SIM_EXECUTABLE',str(ROOT/'build/sim.vvp')))
VVP=os.environ.get('VVP','vvp')
if not SIM.is_file() or not shutil.which(VVP):
    raise SystemExit('Missing compiled simulation or vvp. See README.md.')
STATE=tempfile.TemporaryDirectory(prefix='x-ray-')
ROM=Path(STATE.name)/'panel.mem'
ROM.write_text(''.join(f'{word:04x}\n' for word in rasterize(FLAG)),encoding='ascii')
os.chmod(ROM,0o600)
del FLAG
INSTANCE=secrets.token_hex(8)
GATE=threading.BoundedSemaphore(1)
STATIC={
 '/':('index.html','text/html; charset=utf-8'),
 '/app.css':('app.css','text/css; charset=utf-8'),
 '/app.js':('app.js','text/javascript; charset=utf-8')}

def archive(files):
    output=io.BytesIO()
    with zipfile.ZipFile(output,'w',zipfile.ZIP_DEFLATED) as z:
        for name,data in files.items(): z.writestr(name,data)
    return output.getvalue()

HANDOUT=archive({
 'README.md':(ROOT/'player/README.md').read_bytes(),
 'BOARD.md':(ROOT/'player/BOARD.md').read_bytes(),
 'LICENSE':(ROOT/'LICENSE').read_bytes(),
 'rtl/display_core.sv':(ROOT/'rtl/display_core.sv').read_bytes(),
 'rtl/analyzer_tb.sv':(ROOT/'rtl/analyzer_tb.sv').read_bytes(),
 'font5x7.json':json.dumps(__import__('font').FONT).encode(),
 'preview.mem':''.join(f'{word:04x}\n' for word in rasterize('zzuctf{LOCAL_PREVIEW_ONLY}')).encode()
})

def check_config(data):
    if not isinstance(data,dict) or set(data)-{'probes','trigger','start','count'}:
        raise ValueError('配置字段应为 probes、trigger、start、count。')
    probes=data.get('probes')
    names=[name for name,_ in SIGNALS]
    if not isinstance(probes,list) or not 1<=len(probes)<=4:
        raise ValueError('每次采集请选择 1～4 组探针。')
    if any(not isinstance(p,str) or p not in names for p in probes) or len(set(probes))!=len(probes):
        raise ValueError('探针名称无效或重复。')
    trigger=data.get('trigger','activity')
    start=data.get('start',0); count=data.get('count',512)
    if not isinstance(trigger,str) or trigger not in TRIGGERS:
        raise ValueError('未知触发条件。')
    if type(start) is not int or not 0<=start<=32768:
        raise ValueError('起始事件应为 0～32768 的整数。')
    if type(count) is not int or not 1<=count<=1024:
        raise ValueError('采样深度应为 1～1024 的整数。')
    return probes,trigger,start,count

def acquire(probes,trigger,start,count):
    mask=sum(1<<i for i,(name,_) in enumerate(SIGNALS) if name in probes)
    with tempfile.TemporaryDirectory(prefix='capture-',dir=STATE.name) as folder:
        out=Path(folder)/'capture.vcd'
        before=time.monotonic()
        result=subprocess.run([VVP,str(SIM),f'+rom={ROM}',f'+out={out}',
            f'+probes={mask}',f'+trigger={TRIGGERS[trigger]}',f'+skip={start}',f'+take={count}'],
            stdin=subprocess.DEVNULL,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
            timeout=15,check=True,env={'PATH':os.environ.get('PATH','/usr/bin:/bin')})
        match=re.search(rb'ACQ (\d+) (\d+)',result.stdout)
        if not match or not out.is_file(): raise RuntimeError('incomplete simulator output')
        meta={'instance':INSTANCE,'probes':probes,'trigger':trigger,'start':start,
            'requested':count,'captured':int(match[1]),'total_events':int(match[2]),
            'wall_ms':round((time.monotonic()-before)*1000),
            'sampling':'Signal values precede sample=1; timestamps are absolute simulation nanoseconds.'}
        return archive({'capture.vcd':out.read_bytes(),
            'acquisition.json':json.dumps(meta,ensure_ascii=False,indent=2).encode()})

class Handler(http.server.BaseHTTPRequestHandler):
    server_version='XRay/1'
    protocol_version='HTTP/1.0'
    def setup(self):
        super().setup();self.connection.settimeout(10)
    def log_message(self,fmt,*args):
        # Do not log POST bodies or instance secrets.
        print(f'{self.client_address[0]} {fmt%args}',flush=True)
    def send(self,status,body,mime='application/json; charset=utf-8',filename=None):
        if isinstance(body,dict): body=json.dumps(body,ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header('Content-Type',mime)
        self.send_header('Content-Length',str(len(body)))
        self.send_header('Cache-Control','no-store')
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','DENY')
        self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        if filename: self.send_header('Content-Disposition',f'attachment; filename="{filename}"')
        self.end_headers();self.wfile.write(body)
    def do_GET(self):
        path=urlsplit(self.path).path
        if path in STATIC:
            filename,mime=STATIC[path]
            return self.send(200,(ROOT/'app/static'/filename).read_bytes(),mime)
        if path=='/healthz': return self.send(200,{'ok':True})
        if path=='/api/info':
            return self.send(200,{'instance':INSTANCE,'max_probes':4,'max_samples':1024,
                'max_start':32768,'signals':[{'name':n,'width':w} for n,w in SIGNALS],
                'triggers':list(TRIGGERS)})
        if path=='/attachments/x-ray-player.zip':
            return self.send(200,HANDOUT,'application/zip','x-ray-player.zip')
        return self.send(404,{'error':'未找到资源。'})
    def do_POST(self):
        if urlsplit(self.path).path!='/api/capture': return self.send(404,{'error':'未找到资源。'})
        if self.headers.get('Content-Type','').split(';')[0]!='application/json':
            return self.send(415,{'error':'请使用 application/json。'})
        try:
            length=int(self.headers.get('Content-Length','-1'))
            if not 0<length<=2048: return self.send(413,{'error':'配置大小超限。'})
            config=check_config(json.loads(self.rfile.read(length)))
        except (ValueError,TypeError,UnicodeError):
            return self.send(400,{'error':'采集配置无效，请核对探针、触发条件和采样范围。'})
        if not GATE.acquire(blocking=False): return self.send(429,{'error':'采集器忙，请稍后重试。'})
        try:
            body=acquire(*config)
        except (subprocess.SubprocessError,OSError,RuntimeError):
            return self.send(503,{'error':'仿真未完成，请重试；持续失败请联系赛事管理员。'})
        finally: GATE.release()
        return self.send(200,body,'application/zip',f'capture-{config[2]}.zip')

class Server(http.server.ThreadingHTTPServer):
    daemon_threads=True
    allow_reuse_address=True
    request_queue_size=16
    def __init__(self,*args,**kwargs):
        self.slots=threading.BoundedSemaphore(24)
        super().__init__(*args,**kwargs)
    def process_request(self,request,client_address):
        if not self.slots.acquire(blocking=False):
            request.close();return
        try: super().process_request(request,client_address)
        except BaseException:
            self.slots.release();raise
    def process_request_thread(self,request,client_address):
        try: super().process_request_thread(request,client_address)
        finally: self.slots.release()

if __name__=='__main__':
    print(f'X-ray instance={INSTANCE} port={PORT}',flush=True)
    try: Server(('0.0.0.0',PORT),Handler).serve_forever()
    finally: STATE.cleanup()
