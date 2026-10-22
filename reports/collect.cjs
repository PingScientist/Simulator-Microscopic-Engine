'use strict';
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const repo=process.argv[2]||path.resolve(__dirname,'..'),out=process.argv[3]||path.join(__dirname,'quasistatic-data.json');
const html=fs.readFileSync(path.join(repo,'index.html'),'utf8'),extract=id=>html.match(new RegExp('<script id="'+id+'">([\\s\\S]*?)<\\/script>'))[1];
const m={exports:{}};new Function('module',extract('engine-core'))(m);const E=m.exports;const j={exports:{}};new Function('module','Engine',extract('engine-jobs'))(j,E);const Job=j.exports;
const result={date:'2026-10-22',htmlSha256:crypto.createHash('sha256').update(html).digest('hex'),coreSha256:crypto.createHash('sha256').update(extract('engine-core')).digest('hex'),base:{...E.defaults,N:32,ramp:30,hold:10,burn:2},R:20,K:5,scans:{}};
for(const type of ['rate','scale','translation','boundary']){
 const p={...result.base};if(type==='boundary'){p.ramp=100;p.hold=20;}
 const job=new Job({type,p,R:20,K:5},msg=>{if(msg.kind==='point')console.log(type,JSON.stringify({x:msg.point.x,group:msg.point.group,w:msg.point.mean,ci:msg.point.ci,eta:msg.point.eta,qs:msg.point.theory,delta:msg.point.delta}));});
 while(!job.done)job.tick(20);
 result.scans[type]=job.points;fs.writeFileSync(out,JSON.stringify(result,null,2));
}
