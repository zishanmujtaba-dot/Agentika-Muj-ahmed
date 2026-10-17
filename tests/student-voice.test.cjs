const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const {VoiceInput}=require('../web/voice-input.js');
const {LiveCall}=require('../web/live-call.js');
const tick=()=>new Promise(r=>setImmediate(r));
test('student page initializes, speaks first call reply, and cancels audio on interruption',async()=>{
 const nodes=new Map();
 class Element {
  constructor(){this.events={};this.value='';this.checked=false;this.dataset={};this.classList={toggle(){}};this.children=[]}
  addEventListener(k,fn){this.events[k]=fn}
  append(...children){this.children.push(...children)}
  replaceChildren(...children){this.children=children}
  setAttribute(k,v){this[k]=v} focus(){} remove(){}
  click(){this.events.click?.({preventDefault(){}})}
 }
 const document={hidden:false,getElementById:id=>{if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id)},
  querySelectorAll:()=>[],createElement:()=>new Element(),addEventListener(){}};
 const recognizers=[];class Recognition {
  constructor(){this.events={};recognizers.push(this)}addEventListener(k,fn){this.events[k]=fn}start(){}stop(){}abort(){}
  emit(k,event={}){this.events[k]?.(event)}
  result(text){this.emit('result',{results:[Object.assign([{transcript:text}],{isFinal:true})]})}
 }
 const messages=[],spoken=[],requests=[];let cancellations=0,id=0;
 const speechSynthesis={cancel(){cancellations++},speak:u=>spoken.push(u.text)};
 class Utterance {constructor(text){this.text=text}addEventListener(){}}
 const storage=new Map();const window={SpeechRecognition:Recognition,speechSynthesis,SpeechSynthesisUtterance:Utterance,addEventListener(){}};
 const fetch=async(url,options={})=>{
  let data;
  if(url==='/sessions')data={session_id:'demo-session',session_token:'demo-token'};
  else if(url==='/ask'){
   const body=JSON.parse(options.body);requests.push(body);
   const created_at=new Date().toISOString();
   messages.push({id:++id,from:'student',text:body.query,created_at,request_id:body.request_id},
    {id:++id,from:'agent',text:'Supported policy answer',created_at,request_id:body.request_id});
   data={status:'answered'};
  }else if(url.startsWith('/poll/')){const since=Number(url.split('since=')[1]);data={messages:messages.filter(m=>m.id>since),cursor:id,has_more:false}}
  else throw Error(url);
  return {ok:true,json:async()=>data,headers:{get:()=>null}};
 };
 // Only controller timers execute here. Native event completion is controlled below.
 class TestCall extends LiveCall { constructor(options){super({...options,silenceMs:60000,restartMs:60000})} }
 const context=vm.createContext({window,document,sessionStorage:{getItem:k=>storage.get(k)||null,setItem:(k,v)=>storage.set(k,v),removeItem:k=>storage.delete(k)},
  crypto:require('node:crypto').webcrypto,fetch,AbortController,Date,Set,Uint8Array,Promise,
  EchoVoiceInput:VoiceInput,EchoLiveCall:TestCall,SpeechSynthesisUtterance:Utterance,speechSynthesis,
  setTimeout:()=>1,clearTimeout(){}});
 vm.runInContext(fs.readFileSync(path.join(__dirname,'../web/student.js'),'utf8'),context);
 await tick();await tick();
 assert.equal(nodes.get('callBtn').disabled,false);
 nodes.get('callBtn').click();assert.equal(nodes.get('callBtn')['aria-pressed'],'true');
 const r=recognizers.at(-1);r.emit('speechstart');r.result('How much attendance do I need?');
 nodes.get('sendBtn').click();r.emit('end');await tick();await tick();
 assert.equal(requests.length,1);assert.equal(requests[0].query,'How much attendance do I need?');
 assert.deepEqual(spoken,['Supported policy answer']);
 // The call stays listening during playback, without a second user click.
 vm.runInContext('liveCall.listen()',context);
 const next=recognizers.at(-1);const before=cancellations;next.emit('speechstart');
 assert.ok(cancellations>before);next.result('What if I miss it?');
 assert.equal(nodes.get('question').value,'What if I miss it?');
 nodes.get('callBtn').click();assert.equal(nodes.get('callBtn')['aria-pressed'],'false');
 assert.equal(nodes.get('question').value,'What if I miss it?');
});
