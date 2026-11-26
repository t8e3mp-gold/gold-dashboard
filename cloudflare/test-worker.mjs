import w from './gold-d1-sync.js';
const run=async(name,files)=>{
 const log=[];
 globalThis.fetch=async(u)=>{const f=u.split('/').pop().replace('.json','');const x=files[f];
  if(x===undefined)return{ok:false,status:404};
  if(x==='500')return{ok:false,status:500};
  return{ok:true,status:200,json:async()=>{if(x==='BAD')throw new Error('Unexpected token');return x}}};
 const env={DB:{prepare:(q)=>({bind:(...a)=>({q,a}),run:async()=>{log.push(['run',q.slice(0,30),...[]]);return{}},all:async()=>({results:[]}),q})
   ,batch:async(s)=>{log.push(['batch',s.length])}}};
 // capture last_error bind
 let lastErr=null; const p=env.DB.prepare;
 env.DB.prepare=(q)=>{const o=p(q); if(q.includes("sync_status (k"))o.bind=(v,at)=>({run:async()=>{lastErr=v}}); return o};
 let sched; await w.scheduled({},env,{waitUntil:(pr)=>sched=pr}); await sched;
 console.log(name,'| batch',JSON.stringify(log.filter(l=>l[0]==='batch')),'| last_error:',lastErr);
};
const good={records:[{id:'a',fetched_at:'t'},{id:'b'}]};
await run('good',{'forward-log':good});
await run('one bad record (null, no id, numeric id)',{'forward-log':{records:[{id:'a'},null,{x:1},{id:5},{id:'b'}]}});
await run('malformed JSON in one file, others fine',{'forward-log':good,'forward-score':'BAD','forward-summary':good});
await run('HTTP 500 one file',{'forward-log':good,'forward-summary':'500'});
await run('404 archive only',{'forward-log':good});
