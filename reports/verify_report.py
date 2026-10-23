"""Independently audit saved report data; never changes simulation records."""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import re
import statistics as stats
import subprocess
import numpy as np


def verify(repo, node=None):
    source = repo / 'docs/verification/2026-10-22'
    read = lambda p: json.loads(p.read_text())
    scans = read(repo / 'reports/quasistatic-data.json')
    formal = {k: read(source / f'formal-{k}.json') for k in ('temperature', 'ratio')}
    positive = read(source / 'chromium-all-evidence.json')['evidence']['positive']['points'][0]
    html = (repo / 'index.html').read_bytes()
    core = re.search(rb'<script id="engine-core">([\s\S]*?)</script>', html)[1]
    sha = hashlib.sha256(core).hexdigest()
    assert all(d['coreSha256'] == sha for d in (scans, *formal.values()))
    assert hashlib.sha256(html).hexdigest() == scans['htmlSha256']
    groups = {'positive': [positive], **{k: v['points'] for k, v in formal.items()}, **scans['scans']}
    errors = {'aggregate': 0., 'ledger': 0., 'theory': 0., 'fit': 0., 'ciRelative': 0.}
    count = {'points': 0, 'repeats': 0, 'cyclesIncludingControls': 0, 'pairedControlRepeats': 0}

    def near(a, b, label, atol=1e-10, rtol=0):
        error = abs(a-b)
        assert error <= atol+rtol*abs(b), (label, a, b)
        errors[label] = max(errors[label], error)

    # Numerically invert the independently normalized Student density.
    nodes, weights = np.polynomial.legendre.leggauss(96)
    def tcritical(df):
        factor = math.exp(math.lgamma((df+1)/2)-math.lgamma(df/2))/math.sqrt(df*math.pi)
        lo, hi = 0., 10.
        for _ in range(60):
            x = (lo+hi)/2
            values = factor*(1+(x*(nodes+1)/2)**2/df)**(-(df+1)/2)
            cdf = .5+x/2*float(weights@values)
            if cdf < .975: lo = x
            else: hi = x
        return (lo+hi)/2

    def independent_theory(p):
        def free(T, k, c):
            if p['mode'] == 'wall':
                a = math.sqrt(k/(2*T))
                Z = math.sqrt(math.pi*T/(2*k))*(math.erf((p['L']-c)*a)+math.erf(c*a))
                return -T*math.log(Z)
            a = k*p['L']**2/(4*math.pi**2*T)
            return -T*(math.log(p['L'])-a+math.log(float(np.i0(a))))
        left, right = (p['L']-p['D'])/2, (p['L']+p['D'])/2
        return -(free(p['Th'],p['kmin'],right)-free(p['Th'],p['kmax'],left)
                 +free(p['Tc'],p['kmax'],left)-free(p['Tc'],p['kmin'],right))

    for name, points in groups.items():
        for point in points:
            p = point['p']; R = point['R']; K = point['K']
            assert R == 20 and len(point['reps']) == R
            assert K == (3 if name in formal else 5)
            assert p['burn'] == 2 and p['dt'] == .02
            count['points'] += 1; count['repeats'] += R
            for rep in point['reps']:
                for key in ('cycles', 'controlCycles'):
                    if key not in rep: continue
                    cycles = rep[key]
                    assert len(cycles) == p['burn']+K
                    count['cyclesIncludingControls'] += len(cycles)
                    assert [r['cycle'] for r in cycles] == list(range(1,len(cycles)+1))
                    assert [r['burn'] for r in cycles] == [True]*p['burn']+[False]*K
                    for r in cycles:
                        near(r['w'], r['wk']+r['wx'], 'ledger')
                        near(r['de']+r['w']-r['qh']-r['qc'], r['num'], 'ledger')
                        near(r['residual'], r['num'], 'ledger')
                    kept = [r for r in cycles if not r['burn']]
                    if key == 'controlCycles':
                        count['pairedControlRepeats'] += 1
                        near(rep['control'], stats.mean(r['w'] for r in kept), 'aggregate')
                        near(rep['delta'], rep['w']-rep['control'], 'aggregate')
                    else:
                        for k in ('w','wk','wx','qh','qc','de','num'):
                            near(rep[k], stats.mean(r[k] for r in kept), 'aggregate')
            means = [r['w'] for r in point['reps']]
            mean, sd = stats.mean(means), stats.stdev(means)
            sem = sd/math.sqrt(R)
            for a,b in [(point['mean'],mean),(point['sd'],sd),(point['sem'],sem)]: near(a,b,'aggregate')
            ci = tcritical(R-1)*sem
            rel = abs(point['ci']/ci-1) if ci else 0
            assert rel < 1.2e-5  # Core tabulates t_19 = 2.093 to three decimals.
            errors['ciRelative'] = max(errors['ciRelative'],rel)
            for k in ('wk','wx','qh','qc','de','num'):
                near(point[k], stats.mean(r[k] for r in point['reps']), 'aggregate')
            near(point['power'], mean/(2*(p['ramp']+p['hold'])), 'aggregate')
            if mean > 0 and point['qh'] > 0: near(point['eta'],mean/point['qh'],'aggregate')
            else: assert point['eta'] is None
            near(point['theory'], independent_theory(p), 'theory', atol=1e-8)
            if name == 'translation':
                differences = [r['delta'] for r in point['reps']]
                near(point['control'],stats.mean(r['control'] for r in point['reps']),'aggregate')
                near(point['delta']['mean'],stats.mean(differences),'aggregate')
                expected = tcritical(R-1)*stats.stdev(differences)/math.sqrt(R)
                assert abs(point['delta']['ci']/expected-1) < 1.2e-5
    fits = {}
    for name,d in formal.items():
        x = np.array([p['x'] for p in d['points']]); y = np.array([p['mean'] for p in d['points']])
        A = np.column_stack([x,np.ones(len(x))]); coef = np.linalg.lstsq(A,y,rcond=None)[0]
        residual = y-A@coef; variance = float(residual@residual)/(len(x)-2)
        covariance = variance*np.linalg.inv(A.T@A)
        fit = {'slope':float(coef[0]),'intercept':float(coef[1]),
               'r2':float(1-residual@residual/np.sum((y-y.mean())**2)),
               'slopeSE':float(np.sqrt(covariance[0,0]))}
        for k,v in fit.items(): near(d['fit'][k],v,'fit')
        fits[name] = fit
        rows=list(csv.DictReader((repo/f'reports/latex/data/{name}.csv').open()))
        assert len(rows)==len(d['points'])
        for row,point in zip(rows,d['points']):
            for k in ('x','mean','ci','theory'): assert float(row[k])==point[k]
    # Verify the displayed CI precision at every point actually printed in the PDF.
    printed = [positive, *[p for k in ('rate','scale','translation')
                          for p in (scans['scans'][k][0],scans['scans'][k][-1])],
               *[p for p in scans['scans']['boundary'] if p['x']==24]]
    for i,p in enumerate(printed):
        ci = tcritical(19)*stats.stdev(r['w'] for r in p['reps'])/math.sqrt(20)
        digits = 4 if i==0 else 3
        assert f'{p["ci"]:.{digits}f}' == f'{ci:.{digits}f}'
    report={'coreSha256':sha,'htmlSha256':hashlib.sha256(html).hexdigest(),
            'counts':count,'maxAbsoluteErrors':{k:v for k,v in errors.items() if k!='ciRelative'},
            'confidenceIntervals':{'independentT19':tcritical(19),'engineTabulatedT19':2.093,
                                   'maxRelativeDifference':errors['ciRelative'],'displayRoundingUnaffected':True},
            'fits':fits,'positiveMean':positive['mean'],'positiveCI95':positive['ci']}
    if node:
        # Replay the first saved seed at EVERY point, without choosing favorable cases.
        js = r'''
const fs=require('fs'),path=require('path');const repo=process.argv[1];
const html=fs.readFileSync(path.join(repo,'index.html'),'utf8');
const m={exports:{}};new Function('module',html.match(/<script id="engine-core">([\s\S]*?)<\/script>/)[1])(m);const E=m.exports;
const groups=JSON.parse(fs.readFileSync(0,'utf8'));let runs=0,cycles=0,worst=0,steps=0;
for(const [name,points] of Object.entries(groups))for(const point of points){
 const rep=point.reps[0];
 for(const control of [false,true]){
  if(control&&!rep.controlCycles)continue;
  const saved=control?rep.controlCycles:rep.cycles;
  const sim=new E.Sim({...point.p,seed:rep.seed,...(control?{D:0}:{})});
  while(sim.cycles<saved.length)sim.step();
  for(let i=0;i<saved.length;i++)for(const key of ['w','wk','wx','qh','qc','de','num','residual']){
   const diff=Math.abs(sim.records[i][key]-saved[i][key]);worst=Math.max(worst,diff);
   if(diff>1e-10)throw Error(name+' '+point.x+' '+key+' '+diff);
  }
  runs++;cycles+=saved.length;steps+=sim.steps;
 }
}
console.log(JSON.stringify({runs,cycles,steps,maxAbsoluteDifference:worst,selection:'First saved repeat at every point, plus every paired control'}));
'''
        result=subprocess.run([node,'-e',js,str(repo)],input=json.dumps(groups),text=True,capture_output=True,check=True)
        report['replay']=json.loads(result.stdout)
    return report


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--node',help='Replay one saved repeat at every point using this Node executable')
    args=parser.parse_args()
    print(json.dumps(verify(args.repo,args.node),indent=2))
