#!/usr/bin/env python3
"""Resolve and validate a GHCR reference from workflow inputs, without shell eval."""
import os
from pathlib import Path
import re

def resolve(owner,path,tag):
    owner=owner.lower()
    component=r'[a-z0-9]+(?:[._-][a-z0-9]+)*'
    if not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]*[a-z0-9])?',owner):
        raise ValueError('Invalid GitHub owner')
    if len(path)>150 or not re.fullmatch(component+r'(?:/'+component+r')*',path):
        raise ValueError('image_path must contain lowercase repository-name components separated by /')
    if not re.fullmatch(r'[A-Za-z0-9_][A-Za-z0-9_.-]{0,127}',tag):
        raise ValueError('Invalid image_tag')
    return f'ghcr.io/{owner}/{path}:{tag}'

if __name__=='__main__':
    uri=resolve(os.environ['GITHUB_REPOSITORY_OWNER'],os.environ['INPUT_IMAGE_PATH'],os.environ['INPUT_IMAGE_TAG'])
    with Path(os.environ['GITHUB_OUTPUT']).open('a',encoding='utf-8') as out:
        out.write(f'uri={uri}\n')
    print(f'Image to build and publish: {uri}')
