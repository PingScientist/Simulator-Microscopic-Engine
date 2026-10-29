"""Typeset the reference report (at most four pages) with LaTeX, using saved simulation data only."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import tempfile

REPO = Path(__file__).resolve().parents[1]
REPORTS = REPO / 'reports'
LATEX = REPORTS / 'latex'
OUTPUT = REPORTS / '微觀引擎-參考報告.pdf'


def prepare_data():
    source = REPO / 'docs/verification/2026-10-22'
    formal = {k: json.loads((source / f'formal-{k}.json').read_text())
              for k in ('temperature', 'ratio')}
    positive = json.loads((source / 'chromium-all-evidence.json').read_text())['evidence']['positive']['points'][0]
    scans = json.loads((REPORTS / 'quasistatic-data.json').read_text())
    core = re.search(r'<script id="engine-core">([\s\S]*?)</script>',
                     (REPO / 'index.html').read_text())
    if core is None:
        raise ValueError('Cannot find the delivered physics core')
    digest = hashlib.sha256(core[1].encode()).hexdigest()
    if any(x['coreSha256'] != digest for x in (scans, *formal.values())):
        raise ValueError('Saved results do not match the current physics core')

    data_dir = LATEX / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    for key, dataset in formal.items():
        with (data_dir / f'{key}.csv').open('w', newline='') as handle:
            writer = csv.DictWriter(handle, fieldnames=['x', 'mean', 'ci', 'theory'], lineterminator='\n')
            writer.writeheader()
            for point in dataset['points']:
                writer.writerow({field: point[field] for field in writer.fieldnames})

    def value(point):
        return rf'\({point["mean"]:.3f}\pm{point["ci"]:.3f}\)'

    s = scans['scans']
    macros = {
        'PosMean': f'{positive["mean"]:.4f}',
        'PosCI': f'{positive["ci"]:.4f}',
        'PosEta': f'{positive["eta"]:.3f}',
        'RateFrom': value(s['rate'][0]), 'RateTo': value(s['rate'][-1]),
        'RateEtaFrom': f'{s["rate"][0]["eta"]:.3f}',
        'RateEtaTo': f'{s["rate"][-1]["eta"]:.3f}',
        'ScaleFrom': value(s['scale'][0]), 'ScaleTo': value(s['scale'][-1]),
        'MoveFrom': value(s['translation'][0]), 'MoveTo': value(s['translation'][-1]),
    }
    for key, prefix in [('temperature', 'Temp'), ('ratio', 'Ratio')]:
        fit = formal[key]['fit']
        macros.update({
            prefix + 'Slope': repr(fit['slope']),
            prefix + 'Intercept': repr(fit['intercept']),
            prefix + 'SlopeShort': f'{fit["slope"]:.4f}',
            prefix + 'SE': f'{fit["slopeSE"]:.4f}',
            prefix + 'B': f'{fit["intercept"]:.4f}',
            prefix + 'R': f'{fit["r2"]:.5f}',
        })
    for mode, prefix in [('wall', 'Wall'), ('periodic', 'Period')]:
        point = next(p for p in s['boundary'] if p['p']['mode'] == mode and p['x'] == 24)
        macros.update({prefix + 'Mean': f'{point["mean"]:.3f}',
                       prefix + 'CI': f'{point["ci"]:.3f}',
                       prefix + 'QS': f'{point["theory"]:.3f}'})
    (data_dir / 'results.tex').write_text(
        '% Generated from saved JSON by reports/generate_report.py; do not edit.\n'
        + ''.join(rf'\newcommand{{\{name}}}{{{value}}}' + '\n'
                  for name, value in macros.items()))


def build_pdf(compiler=None):
    from pypdf import PdfReader
    compiler = compiler or shutil.which('tectonic')
    bundled = Path('/Applications/ChatGPT.app/Contents/Resources/tectonic/tectonic')
    if not compiler and bundled.is_file():
        compiler = str(bundled)
    if not compiler:
        raise RuntimeError('Tectonic is required. Pass --tectonic /path/to/tectonic.')
    # The previous PDF is preserved unless compilation and page checks both pass.
    # TemporaryDirectory removes all intermediate files and its directory.
    with tempfile.TemporaryDirectory(prefix='microscopic-engine-latex-') as build:
        subprocess.run([compiler, '--untrusted', '--keep-logs', '--outdir', build,
                        str(LATEX / 'main.tex')], cwd=LATEX, check=True)
        pdf = Path(build) / 'main.pdf'
        reader = PdfReader(pdf)
        if not 1 <= len(reader.pages) <= 4:
            raise ValueError(f'Expected 1 to 4 pages, got {len(reader.pages)}')
        if any(abs(float(p.mediabox.width) - 595.276) > 1 or
               abs(float(p.mediabox.height) - 841.89) > 1 for p in reader.pages):
            raise ValueError('Expected A4 pages')
        log = (Path(build) / 'main.log').read_text(errors='replace')
        if re.search(r'Missing character:|Overfull \\[hv]box', log):
            raise ValueError('LaTeX reported missing glyphs or overflowing content')
        shutil.copyfile(pdf, OUTPUT)
    print(f'{OUTPUT}\n{len(reader.pages)} pages; SHA-256 {hashlib.sha256(OUTPUT.read_bytes()).hexdigest()}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true', help='Refresh CSV and LaTeX data macros without compiling')
    parser.add_argument('--tectonic', help='Path to the Tectonic executable')
    args = parser.parse_args()
    prepare_data()
    if not args.prepare_only:
        build_pdf(args.tectonic)


if __name__ == '__main__':
    main()
