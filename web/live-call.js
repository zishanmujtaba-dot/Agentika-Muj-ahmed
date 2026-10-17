"use strict";
// Browser speech only: no audio is stored by ECHO. Each utterance uses a fresh
// recognizer; hypotheses replace one another rather than being appended.
class LiveCall {
  constructor({ Recognition, onText, onSpeech, onSubmit, onState, onError,
                silenceMs = 2000, restartMs = 150, drainMs = 2000, onSettled = () => {} }) {
    Object.assign(this, { Recognition, onText, onSpeech, onSubmit, onState, onError,
                          silenceMs, restartMs, drainMs, onSettled });
    this.active = false; this.current = null; this.text = "";
    this.silence = null; this.restart = null; this.drain = null;
    this.processing = false; this.flushing = false; this.waiting = false;
    this.speaking = false; this.epoch = 0;
  }
  start() {
    if (this.active || this.processing) return false;
    this.active = true; this.epoch++; this.onState(true); this.listen();
    return this.active;
  }
  draft() { return [this.text, this.current?.text || ""].filter(Boolean).join(" ").slice(0, 2000); }
  listen() {
    if (!this.active || this.current) return;
    let recognition;
    try { recognition = new this.Recognition(); }
    catch { this.fail("start-failed"); return; }
    const run = { recognition, text: "" }; this.current = run;
    recognition.lang = "en-US"; recognition.continuous = false;
    recognition.interimResults = true; recognition.maxAlternatives = 1;
    const valid = () => this.active && this.current === run;
    recognition.addEventListener("speechstart", () => {
      if (!valid()) return;
      this.speaking = true; this.waiting = false;
      clearTimeout(this.silence); this.silence = null;
      this.onSpeech();
    });
    recognition.addEventListener("result", event => {
      if (!valid() || !event.results?.length) return;
      const results = event.results;
      let latest = results[results.length - 1];
      for (let i = results.length - 1; i >= 0; i--) {
        if (results[i].isFinal) { latest = results[i]; break; }
      }
      if (typeof latest?.[0]?.transcript !== "string") return;
      run.text = latest[0].transcript.trim();
      this.onSpeech(); this.onText(this.draft());
      this.waiting = false; this.armSilence(true);
    });
    recognition.addEventListener("speechend", () => {
      if (valid()) { this.speaking = false; this.armSilence(); }
    });
    recognition.addEventListener("end", () => {
      if (!valid()) return;
      this.text = this.draft(); this.current = null; this.speaking = false;
      clearTimeout(this.drain);
      if (this.flushing) this.finishTurn(); else this.armSilence();
      this.scheduleListen();
    });
    recognition.addEventListener("error", event => {
      if (!valid()) return;
      if (event.error === "no-speech") return; // Native end restarts a quiet microphone.
      this.fail(event.error || "recognition-failed");
    });
    try { recognition.start(); } catch { this.fail("start-failed"); }
  }
  scheduleListen() {
    clearTimeout(this.restart);
    if (this.active) this.restart = setTimeout(() => this.listen(), this.restartMs);
  }
  armSilence(reset = false) {
    if (!this.active || !this.draft().trim() || this.flushing) return;
    if (this.silence && !reset) return;
    clearTimeout(this.silence);
    this.silence = setTimeout(() => { this.silence = null; this.flush(); }, this.silenceMs);
  }
  flush() {
    if (!this.active || this.flushing || !this.draft().trim()) return;
    clearTimeout(this.silence); this.silence = null;
    this.flushing = true;
    if (!this.current) { this.finishTurn(); return; }
    // Drain the final native result before sending; a late end cannot resubmit it.
    this.drain = setTimeout(() => this.fail("stop-timeout"), this.drainMs);
    try { this.current.recognition.stop(); } catch { this.fail("stop-failed"); }
  }
  finishTurn() {
    this.flushing = false;
    if (this.processing) { this.waiting = true; return; }
    const text = this.text.trim(); if (!text || !this.active) return;
    this.text = ""; this.onText(""); this.waiting = false;
    this.processing = true; const epoch = this.epoch;
    Promise.resolve().then(() => {
      if (!this.active || epoch !== this.epoch) return;
      return this.onSubmit(text);
    }).catch(() => {
      if (this.active && epoch === this.epoch) this.fail("send-failed");
    }).finally(() => {
      this.processing = false; this.onSettled();
      if (this.active && epoch === this.epoch && this.waiting && !this.speaking) this.flush();
    });
  }
  stop() {
    const draft = this.draft(); this.active = false; this.epoch++;
    clearTimeout(this.silence); clearTimeout(this.restart); clearTimeout(this.drain);
    this.silence = this.restart = this.drain = null;
    const run = this.current; this.current = null; this.text = "";
    this.flushing = false; this.waiting = false; this.speaking = false;
    try { run?.recognition.abort(); } catch { /* Native recording already closed. */ }
    this.onState(false); if (draft) this.onText(draft);
  }
  fail(error) { this.stop(); this.onError(error); }
}
if (typeof module !== "undefined" && module.exports) module.exports = { LiveCall };
else globalThis.EchoLiveCall = LiveCall;
