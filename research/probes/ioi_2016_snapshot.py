"""Restore the complete immutable IOI2016 baseline, without network access."""
from pathlib import Path
import base64,gzip,hashlib,json,tempfile

def snapshot_baseline():
    root=Path(__file__).resolve().parents[2]
    manifest=json.loads((root/'research/snapshots/ioi-2016-manifest.json').read_text())
    original=base64.b64decode(manifest['originalManifestRawBase64'],validate=True)
    assert hashlib.sha256(original).hexdigest()==manifest['originalManifestSha256']=='cc27a3e4b8fc71957827f96c970bd67c62ca859c300930e54fa7636574dffdf7'
    holder=tempfile.TemporaryDirectory(prefix='flowchartcp-ioi2016-frozen-')
    baseline=Path(holder.name)
    for key,count in [('initialBundle',1431),('vendorBundle',105)]:
        entry=manifest[key];raw=(root/entry['path']).read_bytes()
        assert hashlib.sha256(raw).hexdigest()==entry['sha256']
        bundle=json.loads(gzip.decompress(raw));assert bundle['corpusId']=='ioi-2016' and len(bundle['files'])==count
        for item in bundle['files']:
            relative=Path(item['path'])
            assert not relative.is_absolute() and '..' not in relative.parts and not any(part.startswith('.env')for part in relative.parts)
            content=base64.b64decode(item['rawBase64'],validate=True)
            assert hashlib.sha256(content).hexdigest()==item['sha256']
            target=baseline/relative;target.parent.mkdir(parents=True,exist_ok=True);assert not target.exists();target.write_bytes(content)
    (baseline/'manifest.json').write_bytes(original)
    for name in ['SHA256SUMS','CORE_SHA256SUMS','hashes-before.json','hashes-after.json','vendor-hashes-before.json','vendor-hashes-after.json']:
        item=manifest[name];content=base64.b64decode(item['rawBase64'],validate=True)
        assert hashlib.sha256(content).hexdigest()==item['sha256'];(baseline/name).write_bytes(content)
    original_dir=baseline/'.research-originals';original_dir.mkdir()
    for item in manifest['originalArtifacts']:
        content=gzip.decompress((root/item['path']).read_bytes())
        assert hashlib.sha256(content).hexdigest()==item['uncompressedSha256']
        (original_dir/('flowchartcp-ioi2016-'+item['artifact'])).write_bytes(content)
    return holder,baseline
