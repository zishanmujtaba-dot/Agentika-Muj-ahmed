const {test}=require('node:test');
const assert=require('node:assert/strict');
const {LiveCall}=require('../web/live-call.js');
const wait=ms=>new Promise(r=>setTimeout(r,ms));
function setup(onSubmit=async()=>{}) {
  const recordings=[],texts=[],submitted=[],errors=[];let interrupts=0;
  class Recognition {
    constructor(){this.events={};this.stops=0;recordings.push(this)}
    addEventListener(k,fn){this.events[k]=fn}
    start(){} stop(){this.stops++} abort(){}
    emit(k,e={}){this.events[k]?.(e)}
    result(text,final=false){this.emit('result',{results:[Object.assign([{transcript:text}],{isFinal:final})]})}
  }
  const call=new LiveCall({Recognition,onText:t=>texts.push(t),onSpeech:()=>interrupts++,
    onSubmit:async t=>{submitted.push(t);await onSubmit(t)},onState:()=>{},onError:e=>errors.push(e),
    silenceMs:15,restartMs:2,drainMs:50});
  return {call,recordings,texts,submitted,errors,interrupts:()=>interrupts};
}
test('extended silence drains final result and submits once',async()=>{
 const s=setup();try {
 s.call.start();const r=s.recordings[0];r.result('How many');r.result('How many books');
 await wait(25);assert.equal(r.stops,1);assert.deepEqual(s.submitted,[]);
 r.result('How many books can I borrow?',true);r.emit('end');r.emit('end');await wait(5);
 assert.deepEqual(s.submitted,['How many books can I borrow?']);
 }finally{s.call.stop()}
});
test('speech immediately signals interruption without waiting for a result',()=>{
 const s=setup();try{s.call.start();s.recordings[0].emit('speechstart');assert.equal(s.interrupts(),1);assert.equal(s.call.speaking,true)}finally{s.call.stop()}
});
test('short pauses retain the same turn across fresh recognizers',async()=>{
 const s=setup();try{
 s.call.start();s.recordings[0].result('What about',true);s.recordings[0].emit('end');await wait(5);
 const r=s.recordings[1];r.emit('speechstart');r.result('library books',true);r.emit('end');
 await wait(25);s.call.current?.recognition.emit('end');await wait(5);
 assert.deepEqual(s.submitted,['What about library books']);
 }finally{s.call.stop()}
});
test('listening continues during requests and follow-ups are serialized',async()=>{
 let release;const pending=new Promise(r=>release=r);let count=0;
 const s=setup(()=>++count===1?pending:Promise.resolve());try{
 s.call.start();let r=s.recordings[0];r.result('First question',true);s.call.flush();r.emit('end');await wait(5);
 r=s.call.current.recognition;r.emit('speechstart');r.result('Second question',true);s.call.flush();r.emit('end');await wait(5);
 assert.deepEqual(s.submitted,['First question']);assert.ok(s.call.active);
 release();await wait(5);s.call.current?.recognition.emit('end');await wait(5);
 assert.deepEqual(s.submitted,['First question','Second question']);
 }finally{release();s.call.stop()}
});
test('ending a call preserves draft and ignores late callbacks',async()=>{
 const s=setup();s.call.start();const r=s.recordings[0];r.result('Unsent draft');s.call.stop();
 r.result('late text',true);r.emit('end');await wait(20);
 assert.deepEqual(s.submitted,[]);assert.equal(s.texts.at(-1),'Unsent draft');assert.equal(s.call.current,null);
});
test('permission errors end the call without restart loops',async()=>{
 const s=setup();s.call.start();s.recordings[0].emit('error',{error:'not-allowed'});s.recordings[0].emit('end');await wait(10);
 assert.equal(s.call.active,false);assert.equal(s.recordings.length,1);assert.deepEqual(s.errors,['not-allowed']);
});
test('empty silence does not send a request',async()=>{
 const s=setup();s.call.start();s.recordings[0].emit('end');await wait(25);s.call.stop();assert.deepEqual(s.submitted,[]);
});
test('drain timeout keeps draft and ends the call instead of guessing final text',async()=>{
 const s=setup();s.call.start();s.recordings[0].result('Keep this');s.call.flush();await wait(60);
 assert.deepEqual(s.errors,['stop-timeout']);assert.deepEqual(s.submitted,[]);assert.equal(s.texts.at(-1),'Keep this');
});
test('ending before queued submission prevents that request',async()=>{
 const s=setup();s.call.start();s.recordings[0].result('Do not send',true);s.call.flush();s.recordings[0].emit('end');s.call.stop();await wait(5);
 assert.deepEqual(s.submitted,[]);
});
