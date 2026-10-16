from pathlib import Path
import argparse,base64,gzip,hashlib,io,json,tarfile

ROOT=Path('/home/admin2/flowchartcp/site')
DEST=ROOT/'research/in-progress/2026-10-15-pause'
DEST.mkdir(parents=True,exist_ok=True)
def sha(raw):return hashlib.sha256(raw).hexdigest()
def archive(name,files):
    target=DEST/(name+'.tar.gz')
    assert not target.exists(),target
    entries=[]
    with target.open('wb')as out:
        with gzip.GzipFile(filename='',mode='wb',fileobj=out,mtime=0)as zipped:
            with tarfile.open(fileobj=zipped,mode='w',format=tarfile.PAX_FORMAT)as bundle:
                for relative,path in sorted(files,key=lambda pair:pair[0]):
                    parts=Path(relative).parts
                    assert not Path(relative).is_absolute()and'..'not in parts
                    assert not any(part.startswith('.env')for part in parts)
                    assert path.is_file()and not path.is_symlink()
                    raw=path.read_bytes();info=tarfile.TarInfo(relative)
                    info.size=len(raw);info.mode=0o644;info.mtime=0
                    bundle.addfile(info,io.BytesIO(raw))
                    entries.append({'path':relative,'bytes':len(raw),'sha256':sha(raw)})
    # Reopen the finished archive and verify every byte before accepting it.
    with tarfile.open(target,'r:gz')as bundle:
        members=bundle.getmembers();assert len(members)==len(entries)
        for member,entry in zip(members,entries):
            assert member.isfile()and member.name==entry['path']
            assert sha(bundle.extractfile(member).read())==entry['sha256']
    record={'archive':target.name,'sha256':sha(target.read_bytes()),'files':len(entries),'entries':entries,'roundTripAllBytesVerified':True}
    (DEST/(name+'.json')).write_text(json.dumps(record,ensure_ascii=False,indent=2)+'\n')
    return {'archive':target.name,'manifest':name+'.json','sha256':record['sha256'],'files':len(entries),'roundTripAllBytesVerified':True}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('kind',choices=['ioi-2014','ioi-2015','wf2018-triangles']);args=ap.parse_args()
    prefix={'ioi-2014':'flowchartcp-ioi2014-','ioi-2015':'flowchartcp-ioi2015-','wf2018-triangles':'flowchartcp-wf2018-triangles-'}[args.kind]
    files=[]
    for p in Path('/tmp').glob(prefix+'*'):
        if p.is_file()and not p.is_symlink():files.append(('artifacts/'+p.name,p))
    if args.kind!='wf2018-triangles':
        baseline=Path('/tmp')/(prefix+'baseline');assert baseline.is_dir()
        for p in baseline.rglob('*'):
            if p.is_file()and not p.is_symlink():
                rel=p.relative_to(baseline)
                assert not any(part.startswith('.env')for part in rel.parts)
                files.append(('baseline/'+str(rel),p))
    print(json.dumps(archive(args.kind,files),ensure_ascii=False))
