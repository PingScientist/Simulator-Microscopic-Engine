'use strict';
// Read the actual deliverable; no second copy of the numerical implementation.
const fs=require('fs'),path=require('path'),vm=require('vm'),assert=require('assert'),crypto=require('crypto');
const htmlPath=process.argv[2]||path.resolve(__dirname,'../index.html');
const output=process.env.ENGINE_TEST_OUTPUT||path.resolve(__dirname,'../test-results');
fs.mkdirSync(output,{recursive:true});
const html=fs.readFileSync(htmlPath,'utf8'),extract=id=>html.match(new RegExp('<script id="'+id+'">([\\s\\S]*?)<\\/script>'))[1];
const coreModule={exports:{}};new Function('module',extract('engine-core'))(coreModule);const E=coreModule.exports;const jobsModule={exports:{}};new Function('module','Engine',extract('engine-jobs'))(jobsModule,E);const Job=jobsModule.exports;
const report={date:new Date().toISOString(),node:process.version,sha256:crypto.createHash('sha256').update(html).digest('hex'),coreSha256:crypto.createHash('sha256').update(extract('engine-core')).digest('hex'),checks:[]};
function check(name,fn){const start=Date.now();const evidence=fn();report.checks.push({name,pass:true,ms:Date.now()-start,evidence});console.log('PASS',name,JSON.stringify(evidence??{}));}
function near(a,b,t,msg){assert(Math.abs(a-b)<=t,(msg||'')+' '+a+' vs '+b+' tolerance '+t);}
function run(p,cycles){const s=new E.Sim(p);while(s.cycles<cycles)s.step();return s;}
function repeat(p,R=20,K=3){const reps=[];for(let r=0;r<R;r++){const s=run({...p,seed:E.seedFor(p.seed,r)},p.burn+K);const rows=s.records.filter(x=>!x.burn);reps.push({w:E.summary(rows.map(x=>x.w)).mean,qh:E.summary(rows.map(x=>x.qh)).mean,residual:E.summary(rows.map(x=>x.residual)).mean});}return {work:E.summary(reps.map(x=>x.w)),qh:E.summary(reps.map(x=>x.qh)),residual:E.summary(reps.map(x=>x.residual)),reps};}
// Independent continuous-time moment ODE, advanced by RK4.
function momentReference(p,K=3){
 let z=[p.L/2-p.D/2,0,p.Tc/p.kmax,0,p.Tc,p.Tc,0,0,0],work=[];
 const derivative=(state,phase,f)=>{
   const length=phase%2?p.ramp:p.hold,left=p.L/2-p.D/2,right=p.L/2+p.D/2;
   let k,c,T,kdot=0,cdot=0;
   if(phase===0){k=p.kmax;c=left+p.D*f*f*(3-2*f);T=p.Th;cdot=6*p.D*f*(1-f)/length;}
   if(phase===1){k=p.kmax+(p.kmin-p.kmax)*f;c=right;T=p.Th;kdot=(p.kmin-p.kmax)/length;}
   if(phase===2){k=p.kmin;c=right-p.D*f*f*(3-2*f);T=p.Tc;cdot=-6*p.D*f*(1-f)/length;}
   if(phase===3){k=p.kmin+(p.kmax-p.kmin)*f;c=left;T=p.Tc;kdot=(p.kmax-p.kmin)/length;}
   const [x,v,xx,xv,vv,vy]=state,g=p.gamma;
   return [v,-k*(x-c)-g*v,2*xv,vv-k*xx-g*xv,-2*k*xv-2*g*vv+2*g*T,-2*g*vy+2*g*T,.5*(xx+(x-c)**2)*kdot,-k*(x-c)*cdot,phase<2?g*(2*T-vv-v*v-vy):0];
 };
 for(let cycle=0;cycle<p.burn+K;cycle++){
   z[6]=z[7]=z[8]=0;
   for(let phase=0;phase<4;phase++){const length=phase%2?p.ramp:p.hold,n=Math.ceil(length/.01),h=length/n;
     for(let i=0;i<n;i++){const a=derivative(z,phase,i/n),b=derivative(z.map((x,j)=>x+h*a[j]/2),phase,(i+.5)/n),c=derivative(z.map((x,j)=>x+h*b[j]/2),phase,(i+.5)/n),d=derivative(z.map((x,j)=>x+h*c[j]),phase,(i+1)/n);z=z.map((x,j)=>x+h*(a[j]+2*b[j]+2*c[j]+d[j])/6);}
   }
   if(cycle>=p.burn)work.push({w:-z[6]-z[7],qh:z[8]});
 }
 return {w:work.reduce((a,b)=>a+b.w,0)/K,qh:work.reduce((a,b)=>a+b.qh,0)/K};
}
check('Offline packaging and exposed core',()=>{assert(!/<(?:script|link)[^>]*(?:src|href)=["']https?:/i.test(html));assert(!/fetch\s*\(/.test(extract('engine-app')));assert(E.selfcheck().every(x=>x.pass));return {embeddedOnly:true,quickChecks:E.selfcheck().length};});
check('Force and both parameter derivatives / two models',()=>{
 let worst=0;for(const mode of ['wall','periodic'])for(const x of [.01,4.2,11.3,23.99]){const p={...E.defaults,mode},k=2.3,c=10.4,e=1e-5;
  worst=Math.max(worst,Math.abs(-(E.potential(x+e,k,c,p)-E.potential(x-e,k,c,p))/(2*e)-E.force(x,k,c,p)));
  near((E.potential(x,k+e,c,p)-E.potential(x,k-e,c,p))/(2*e),E.conjugate(x,c,p),1e-7);
  near((E.potential(x,k,c+e,p)-E.potential(x,k,c-e,p))/(2*e),E.force(x,k,c,p),1e-7);
 }assert(worst<1e-7);return {worst};});
check('Periodic seam and translation invariance',()=>{const p={...E.defaults,mode:'periodic'};for(const x of [-500,-24,0,.0001,24,240]){near(E.potential(x,3,4,p),E.potential(x+24,3,4,p),1e-10);near(E.force(x,3,4,p),E.force(x+24,3,4,p),1e-10);}near(E.logZ(p,2,4,1),E.logZ(p,2,4,23),1e-10);return {continuous:true};});
check('Repeated elastic wall reflections preserve kinetic energy',()=>{for(const distance of [-300,-73,-25,-1,1,25,73,300]){const [x,v]=E.reflect(12+distance,distance,24);assert(x>=0&&x<=24);near(v*v,distance*distance,1e-12);}return {cases:8};});
check('Seed reproducibility and exact JSON continuation',()=>{for(const mode of ['wall','periodic']){const a=new E.Sim({...E.defaults,N:32,mode,D:4});a.advance(777);const b=E.Sim.restore(JSON.parse(JSON.stringify(a.snapshot())));a.advance(1234);b.advance(1234);assert.equal(JSON.stringify(a.snapshot()),JSON.stringify(b.snapshot()));}return {modes:2};});
check('Invalid coupled configuration and malformed import rejected',()=>{assert.throws(()=>E.validate({...E.defaults,Th:.5}));assert.throws(()=>E.validate({...E.defaults,dt:.05,kmax:16}));const a=new E.Sim(E.defaults).snapshot();a.x[0]=Infinity;assert.throws(()=>E.Sim.restore(a));const b=new E.Sim(E.defaults).snapshot();b.steps=12;assert.throws(()=>E.Sim.restore(b));return {rejections:4};});
check('Duration endpoints and scan ranges remain valid after normalization',()=>{const s=new E.Sim({...E.defaults,N:4,dt:.007,ramp:120,hold:40});s.advance(333);const restored=E.Sim.restore(s.snapshot());assert.equal(JSON.stringify(restored.snapshot()),JSON.stringify(s.snapshot()));assert(s.p.ramp<=120&&s.p.hold<=40);assert(E.makeScan('scale',{...E.defaults,kmin:5,kmax:6}).every(c=>c.p.kmin<=8));const bad=s.snapshot();bad.total.win+=10;assert.throws(()=>E.Sim.restore(bad));return {ramp:s.p.ramp,hold:s.p.hold,ledgerTamperRejected:true};});
check('Equilibrium Maxwell, Gaussian and equipartition statistics',()=>{
 const s=new E.Sim({...E.defaults,N:512,Tc:2,Th:2,kmin:2,kmax:2,dt:.01});let count=0,x=0,xx=0,vx=0,vxx=0,vyy=0,K=0,U=0;
 for(let j=0;j<25000;j++){s.step();if(j>2000&&j%200===0){const a=s.measure();count++;x+=a.meanX;xx+=a.varianceX;vx+=a.vx;K+=a.K/s.p.N;U+=a.U/s.p.N;for(let i=0;i<s.p.N;i++){vxx+=s.vx[i]**2/s.p.N;vyy+=s.vy[i]**2/s.p.N;}}}
 const data={meanX:x/count,varX:xx/count,meanV:vx/count,vx2:vxx/count,vy2:vyy/count,K:K/count,U:U/count};
 near(data.meanX,12,.04);near(data.varX,1,.04);near(data.meanV,0,.04);near(data.vx2,2,.06);near(data.vy2,2,.06);near(data.K,2,.04);near(data.U,1,.04);return data;
});
check('Independent OU velocity relaxation',()=>{const s=new E.Sim({...E.defaults,N:512,Tc:1,Th:3,kmin:1,kmax:1});s.vy.fill(0);s.energy=s.measure().energy;s.initialEnergy=s.energy;s.cycleStart=s.energy;
 const yy=[];for(let j=0;j<60;j++){s.step();if([9,29,59].includes(j)){const measured=Array.from(s.vy).reduce((a,v)=>a+v*v,0)/512,expected=3*(1-Math.exp(-2*(j+1)*.02));near(measured,expected,expected*.22);yy.push({t:(j+1)*.02,measured,expected});}}return yy;});
const base={...E.defaults,N:64};
check('Positive work from 20 independent dynamical repeats',()=>{const a=repeat(base,20,3);assert(a.work.mean-a.work.ci>0);report.positiveWork=a;return {mean:a.work.mean,ci95:a.work.ci,meanQH:a.qh.mean,eta:a.work.mean/a.qh.mean};});
check('Finite-time work and heat vs independent moment ODE',()=>{const a=report.positiveWork,b=momentReference(base);near(a.work.mean,b.w,4*a.work.sem+.006);near(a.qh.mean,b.qh,4*a.qh.sem+.02);return {measuredWork:a.work.mean,momentWork:b.w,measuredQH:a.qh.mean,momentQH:b.qh};});
check('Translation work vs independent moment ODE',()=>{const p={...base,D:4},a=repeat(p,12,3),b=momentReference(p);near(a.work.mean,b.w,4*a.work.sem+.01);return {mean:a.work.mean,ci95:a.work.ci,momentWork:b.w};});
check('First law is independent of bath heat; residual shrinks with dt',()=>{const values=[];for(const dt of [.04,.02,.01]){const a=repeat({...base,dt,N:32},6,3);values.push({dt,work:a.work.mean,sem:a.work.sem,residual:a.residual.mean});}assert(Math.abs(values[1].residual)<Math.abs(values[0].residual)*.4);assert(Math.abs(values[2].residual)<Math.abs(values[1].residual)*.4);near(values[1].work,values[2].work,4*Math.hypot(values[1].sem,values[2].sem)+.01);return values;});
check('Mechanical error and bath ledger closure',()=>{for(const mode of ['wall','periodic']){const s=run({...base,mode,D:4,L:12},4);near(s.energy-s.initialEnergy-s.total.win-s.total.qh-s.total.qc,s.total.num,1e-8);for(const r of s.records)near(r.residual,r.num,1e-9);}return {modes:2};});
check('Finite wall partition integral agrees with independent Gaussian CDF',()=>{function erf(x){let total=0,n=20000,h=x/n;for(let j=0;j<=n;j++)total+=(j===0||j===n?1:j%2?4:2)*Math.exp(-((j*h)**2));return 2/Math.sqrt(Math.PI)*total*h/3;}
 const p={...base,L:8},T=3,k=.25,c=1,sigma=Math.sqrt(T/k),direct=Math.sqrt(2*Math.PI)*sigma*.5*(erf((8-c)/(Math.sqrt(2)*sigma))-erf(-c/(Math.sqrt(2)*sigma)));
 const computed=Math.exp(E.logZ(p,T,k,c));near(computed,direct,1e-9);return {computed,direct};});
check('Weak periodic trap matches Bessel-series partition function',()=>{const p={...base,mode:'periodic',L:8},T=3,k=.25,a=k*64/(4*Math.PI*Math.PI*T);let I=1,term=1;for(let j=1;j<30;j++){term*=a*a/(4*j*j);I+=term;}const expected=8*Math.exp(-a)*I,computed=Math.exp(E.logZ(p,T,k,3));near(computed,expected,1e-10);return {computed,expected};});
check('Zero temperature difference does not produce systematic positive work',()=>{const a=repeat({...base,Th:1},12,3);assert(a.work.mean<3*a.work.sem);return {mean:a.work.mean,ci95:a.work.ci};});
check('No curvature change and no translation means zero control work',()=>{const s=run({...base,kmin:2,kmax:2},4);s.records.forEach(r=>near(r.w,0,1e-12));return {cycles:4};});
check('Large container periodic model approaches harmonic theory',()=>{const a=E.theory({...base,mode:'periodic',L:24}),b=E.theory({...base,mode:'periodic',L:64});assert(Math.abs(b.work-b.ideal)<Math.abs(a.work-a.ideal));return {L24:a.work,L64:b.work,ideal:a.ideal};});
check('Maximum particle count and parameter corner complete a cycle',()=>{const p={...base,N:512,Th:10,Tc:.2,kmin:.25,kmax:16,gamma:4,L:8,D:4,dt:.02,hold:2,ramp:2};const s=run(p,1);assert(s.x.every(x=>x>=0&&x<=8));assert(Number.isFinite(s.energy));near(s.records[0].residual,s.records[0].num,1e-8);return {N:512,steps:s.steps,work:s.records[0].w};});
check('Bounded scan runner completes all experiment definitions',()=>{const results={};for(const type of ['temperature','ratio','rate','scale','translation','boundary']){const job=new Job({type,p:{...base,N:4,ramp:2,hold:2,burn:0},R:2,K:1},()=>{});while(!job.done)job.tick(20);assert(job.points.length>=3);assert(job.points.every(p=>p.reps.length===2));if(type==='translation')assert(job.points.every(p=>Number.isFinite(p.control)&&p.reps.every(r=>r.controlCycles.length===3)));results[type]=job.points.length;}return results;});
check('Formal linearity scans: 20 independent repeats per point',()=>{
 const results={};
 for(const type of ['temperature','ratio']){
  console.log('RUNNING formal',type);
  const job=new Job({type,p:{...base,N:32,ramp:100,hold:20},R:20,K:3},()=>{});
  let last=-1;while(!job.done){job.tick(25);if(job.ci!==last){last=job.ci;console.log('POINT',type,last,'/',job.cases.length);}}
  const fit=E.regression(job.points.map(p=>({x:p.x,y:p.mean}))),expected=type==='temperature'?.5*Math.log(4):1;
  assert(fit.r2>.99);assert(Math.abs(fit.slope-expected)<.07);
  results[type]={slope:fit.slope,intercept:fit.intercept,r2:fit.r2,idealSlope:expected};
  fs.writeFileSync(path.join(output,'formal-'+type+'.json'),JSON.stringify({coreSha256:report.coreSha256,experiment:type,points:job.points,fit},null,2));
 }
 return results;
});
fs.writeFileSync(path.join(output,'numerical-report.json'),JSON.stringify(report,null,2));
console.log('COMPLETE',report.checks.length,'checks');
