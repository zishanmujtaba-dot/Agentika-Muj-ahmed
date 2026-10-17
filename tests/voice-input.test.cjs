const { test } = require('node:test');
const assert = require('node:assert/strict');
const { VoiceInput } = require('../web/voice-input.js');
function setup(options = {}) {
  const recordings = [], texts = [], ends = [], errors = [];
  class Recognition {
    constructor() { this.handlers = {}; this.stops = 0; recordings.push(this); }
    addEventListener(name, handler) { this.handlers[name] = handler; }
    start() { if (options.startFails) throw Error('start'); }
    stop() { this.stops++; }
    abort() {}
    emit(name, event = {}) { this.handlers[name]?.(event); }
    result(...entries) { this.emit('result', { results: entries.map(([text, final]) => Object.assign([{transcript:text}], {isFinal:final})) }); }
  }
  const voice = new VoiceInput({Recognition, onText:t=>texts.push(t), onState:()=>{}, onEnd:e=>ends.push(e), onError:e=>errors.push(e), stopTimeoutMs:10});
  return {voice, recordings, texts, ends, errors};
}
test('interim and duplicate final snapshots replace the transcript', () => {
  const s=setup(); s.voice.start(); const r=s.recordings[0];
  r.result(['what is',false]); r.result(['what is attendance',false]);
  r.result(['what is attendance',true],['what is attendance',true]);
  s.voice.stop(true); r.emit('end');
  assert.equal(s.ends[0].text,'what is attendance'); assert.equal(s.ends[0].send,true);
});
test('intentional repeated words are preserved', () => {
  const s=setup(); s.voice.start(); s.recordings[0].result(['I am very very late',true]); s.recordings[0].emit('end');
  assert.equal(s.ends[0].text,'I am very very late'); assert.equal(s.ends[0].send,false);
});
test('each recording is isolated and the existing draft is included once', () => {
  const s=setup(); s.voice.start('Existing draft'); const old=s.recordings[0]; old.result(['first part',true]); old.emit('end');
  s.voice.start(s.ends[0].text); const next=s.recordings[1];
  assert.notEqual(old,next); assert.equal(next.continuous,false);
  old.result(['stale data',true]); old.emit('end'); next.result(['second part',true]); next.emit('end');
  assert.equal(s.ends.length,2); assert.equal(s.ends[1].text,'Existing draft first part second part');
});
test('send waits for final recognition and duplicate stop/end events send once', () => {
  const s=setup(); s.voice.start(); const r=s.recordings[0]; r.result(['interim',false]);
  s.voice.stop(true); s.voice.stop(true); assert.equal(s.ends.length,0); assert.equal(r.stops,1);
  r.result(['final question',true]); r.emit('end'); r.emit('end'); r.result(['late',true]);
  assert.equal(s.ends.length,1); assert.equal(s.ends[0].text,'final question'); assert.equal(s.ends[0].send,true);
});
test('errors preserve draft and never send automatically', () => {
  const s=setup(); s.voice.start('Draft'); const r=s.recordings[0]; r.result(['spoken text',false]); s.voice.stop(true); r.emit('error',{error:'network'}); r.emit('end');
  assert.equal(s.ends.length,1); assert.equal(s.ends[0].text,'Draft spoken text'); assert.equal(s.ends[0].send,false); assert.deepEqual(s.errors,['network']);
});
test('timeout permits recovery without sending', async () => {
  const s=setup(); s.voice.start(); s.recordings[0].result(['draft',false]); s.voice.stop(true);
  await new Promise(resolve=>setTimeout(resolve,25));
  assert.equal(s.ends[0].send,false); assert.equal(s.ends[0].text,'draft'); assert.deepEqual(s.errors,['stop-timeout']);
});
test('failed start and cancellation ignore late native events', () => {
  const failed=setup({startFails:true}); assert.equal(failed.voice.start('draft'),false); assert.equal(failed.ends[0].send,false);
  const s=setup(); s.voice.start(); const r=s.recordings[0]; s.voice.cancel(); r.result(['late',true]); r.emit('end');
  assert.deepEqual(s.texts,[]); assert.deepEqual(s.ends,[]);
});
test('empty recording never submits an existing draft automatically', () => {
  const s=setup(); s.voice.start('Existing draft'); s.voice.stop(true); s.recordings[0].emit('end');
  assert.equal(s.ends[0].send,false); assert.equal(s.ends[0].text,'Existing draft');
});
