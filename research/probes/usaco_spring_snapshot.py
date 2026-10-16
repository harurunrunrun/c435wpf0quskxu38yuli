"""Open the complete immutable 488-article baseline without using the live site."""
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
import hashlib
import json
import tarfile
import tempfile

SITE = Path(__file__).resolve().parents[2]
ARCHIVE = SITE / 'research/snapshots/usaco-2021-february-us-open-platinum-baseline.tar.gz'
ARCHIVE_SHA256 = 'be645b2f3192848bd482d5034e8fe79eca2e637e730d8ac893a6d5e5501c3913'


@contextmanager
def open_snapshot():
    assert hashlib.sha256(ARCHIVE.read_bytes()).hexdigest() == ARCHIVE_SHA256
    with tempfile.TemporaryDirectory(prefix='flowchartcp-usaco-spring-baseline-') as temporary:
        root = Path(temporary)
        with tarfile.open(ARCHIVE, 'r:gz') as archive:
            members = archive.getmembers()
            assert len(members) == 624
            assert len({member.name for member in members}) == len(members)
            for member in members:
                name = PurePosixPath(member.name)
                assert member.isfile() and not name.is_absolute() and '..' not in name.parts
                assert name.parts[0] in {'data', 'src', 'manifest.json', 'hashes-before.json',
                                         'hashes-after.json', 'SHA256SUMS'}
                target = root.joinpath(*name.parts)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(archive.extractfile(member).read())
        before = json.loads((root / 'hashes-before.json').read_text())
        assert before == json.loads((root / 'hashes-after.json').read_text())
        assert len(before) == 620
        for name, expected in before.items():
            assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name
        yield root
