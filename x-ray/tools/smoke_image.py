#!/usr/bin/env python3
"""Start the built image with GZCTF-like limits and solve it before publishing."""
import argparse
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'organizer'))
from solve import solve

def wait_and_solve(url,expected,output):
    for _ in range(240):
        try:
            with urllib.request.urlopen(url+'/healthz',timeout=2) as response:
                if response.status==200: break
        except (OSError,urllib.error.URLError): pass
        time.sleep(.25)
    else: raise RuntimeError('Image did not become healthy within 60 seconds')
    actual=solve(url,output)
    if actual!=expected: raise RuntimeError('Recovered flag does not match the injected test flag')
    print('PASS: container simulation, HTTP acquisition and full dynamic-flag recovery')

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image',required=True)
    args=parser.parse_args()
    name='x-ray-smoke-'+secrets.token_hex(5)
    expected='zzuctf{ci_test_'+secrets.token_hex(16)+'}'
    command=['docker','run','--detach','--name',name,
        '--publish','127.0.0.1::8000','--cpus','0.5','--memory','256m',
        '--pids-limit','48','--read-only','--tmpfs','/tmp:size=32m,mode=1777',
        '--cap-drop','ALL','--security-opt','no-new-privileges:true',
        '--env','GZCTF_FLAG='+expected,args.image]
    try:
        subprocess.run(command,check=True)
        mapping=subprocess.check_output(['docker','port',name,'8000/tcp'],text=True).strip().splitlines()[0]
        port=int(mapping.rsplit(':',1)[1])
        with tempfile.TemporaryDirectory(prefix='x-ray-smoke-') as output:
            wait_and_solve(f'http://127.0.0.1:{port}',expected,output)
    except BaseException:
        subprocess.run(['docker','logs',name],check=False)
        raise
    finally:
        subprocess.run(['docker','rm','--force',name],check=False,stdout=subprocess.DEVNULL)

if __name__=='__main__': main()
