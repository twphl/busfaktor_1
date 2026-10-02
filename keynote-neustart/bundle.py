"""Package only this independent keynote and verify local dependencies."""
from html.parser import HTMLParser
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

HERE = Path(__file__).resolve().parent


class CheckLinks(HTMLParser):
    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in ('src', 'href') and value and not value.startswith(('#', 'https:', 'data:')):
                path = (HERE / value).resolve()
                assert path.is_relative_to(HERE), f'Externe Abhängigkeit: {value}'
                assert path.is_file(), f'Fehlende Datei: {value}'


def main():
    CheckLinks().feed((HERE / 'index.html').read_text())
    assert len(list((HERE / 'assets/cards').glob('*.webp'))) == 82
    assert len(list((HERE / 'assets/art').glob('*.webp'))) == 82
    names = ['index.html', 'deck.css', 'deck.js', 'cards.js', 'README.md', 'SPIELREGELN.md', 'prepare.py', 'bundle.py']
    files = [HERE / name for name in names]
    files += sorted(p for p in (HERE / 'assets').rglob('*') if p.is_file())
    destination = HERE / 'busfaktor-keynote.zip'
    with ZipFile(destination, 'w', ZIP_DEFLATED, compresslevel=6) as archive:
        for path in files:
            archive.write(path, 'busfaktor-keynote/' + path.relative_to(HERE).as_posix())
    with ZipFile(destination) as archive:
        assert archive.testzip() is None
        assert sum(name.endswith('.html') for name in archive.namelist()) == 1
    print(f'OK: {destination.name}, {len(files)} Dateien, {destination.stat().st_size / 1048576:.1f} MiB, genau eine index.html.')


if __name__ == '__main__':
    main()
