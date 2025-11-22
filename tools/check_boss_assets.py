#!/usr/bin/env python3
"""Utility: compare BOSS_METADATA keys to files in assets/bosses/ and report mismatches.

Run this from the repo root (it uses resource_path in game.py if available, otherwise assumes relative paths).
"""
import os
import sys

# try to import BOSS_METADATA from globals if possible
try:
    from globals import BOSS_METADATA
except Exception:
    BOSS_METADATA = None

# fallback: attempt to parse minimal subset of globals if file not importable
if BOSS_METADATA is None:
    # try to load the globals.py as a plain file and exec a small dict extraction
    gp = os.path.join(os.path.dirname(__file__), '..', 'globals.py')
    gp = os.path.abspath(gp)
    if os.path.exists(gp):
        try:
            g = {}
            with open(gp, 'r', encoding='utf-8') as fh:
                txt = fh.read()
            # naive exec in isolated dict (only safe-ish for local trusted repo)
            exec(compile(txt, gp, 'exec'), {}, g)
            BOSS_METADATA = g.get('BOSS_METADATA')
        except Exception:
            BOSS_METADATA = None

if BOSS_METADATA is None:
    print('ERROR: Could not load BOSS_METADATA from globals.py')
    sys.exit(2)

# list files under assets/bosses (if exists)
assets_dir = os.path.join(os.path.dirname(__file__), '..', 'assets', 'bosses')
assets_dir = os.path.abspath(assets_dir)
files = []
if os.path.exists(assets_dir) and os.path.isdir(assets_dir):
    for f in os.listdir(assets_dir):
        files.append(f)
else:
    print(f"Assets directory not found: {assets_dir}")

# normalize function for filenames
def norm(name):
    return name.lower()

# build maps
file_set = set([norm(f) for f in files])
meta_keys = list(BOSS_METADATA.keys())

missing_images = []
found_images = []

for k in meta_keys:
    candidates = []
    base = str(k)
    candidates.append(f"{base}.png")
    candidates.append(f"{base.replace('-', '_')}.png")
    candidates.append(f"{base.replace('-', '')}.png")
    candidates.append(f"{base.lower()}.png")
    candidates.append(f"{base}.jpg")
    candidates.append(f"{base.replace('-', '_')}.jpg")
    ok = False
    for c in candidates:
        if norm(c) in file_set:
            ok = True
            found_images.append((k, c))
            break
    if not ok:
        missing_images.append((k, candidates))

# report missing ability metadata
missing_ability = []
for k, v in BOSS_METADATA.items():
    ak = v.get('ability_key') if isinstance(v, dict) else None
    img = v.get('image') if isinstance(v, dict) else None
    if not ak:
        missing_ability.append(k)

# Print report
print('Boss asset scan report')
print('----------------------')
print(f'Total boss metadata entries: {len(meta_keys)}')
print(f'Files found in assets/bosses: {len(files)}')
print('')
if found_images:
    print('Found image matches:')
    for k, c in found_images:
        print(f'  - {k} -> {c}')
    print('')
if missing_images:
    print('Missing images for these boss keys (candidates tried):')
    for k, cands in missing_images:
        print(f'  - {k}:')
        for c in cands:
            print(f'      {c}')
    print('')
else:
    print('All metadata keys have at least one image candidate present.')

if missing_ability:
    print('\nBoss entries missing ability_key:')
    for k in missing_ability:
        print(f'  - {k}')
else:
    print('\nAll boss entries have ability_key present.')

# Exit code indicates whether any problems found
if missing_images or missing_ability:
    sys.exit(1)
else:
    sys.exit(0)
