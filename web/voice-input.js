"use strict";

// A recording owns its recognizer and transcript. Never concatenate successive
// result snapshots: interim hypotheses are replacements, not additional speech.
class VoiceInput {
  constructor({ Recognition, onText, onState, onEnd, onError, stopTimeoutMs = 8000 }) {
    this.Recognition = Recognition;
    this.onText = onText;
    this.onState = onState;
    this.onEnd = onEnd;
    this.onError = onError;
    this.stopTimeoutMs = stopTimeoutMs;
    this.current = null;
  }

  get stopping() { return this.current?.phase === "stopping"; }

  start(prefix = "") {
    if (this.current) return false;
    const recognition = new this.Recognition();
    const run = { recognition, prefix: prefix.trim(), transcript: "", send: false, phase: "listening", timer: null };
    this.current = run;
    recognition.lang = "en-US";
    // One utterance yields one transcript. This avoids browser-specific continuous
    // result duplication without deleting intentionally repeated words.
    recognition.continuous = false;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.addEventListener("result", event => {
      if (this.current !== run || !event.results?.length) return;
      // Single-utterance results are snapshots. If a browser emits several slots
      // at finalization, take one final snapshot instead of joining duplicates.
      let latest = event.results[event.results.length - 1];
      for (let i = event.results.length - 1; i >= 0; i--) {
        if (event.results[i].isFinal) { latest = event.results[i]; break; }
      }
      const transcript = latest?.[0]?.transcript;
      if (typeof transcript !== "string") return;
      run.transcript = transcript.trim();
      this.onText(this.text(run));
    });
    recognition.addEventListener("end", () => this.finish(run));
    recognition.addEventListener("error", event => {
      if (this.current !== run) return;
      this.fail(run, event.error || "recognition-failed");
    });
    this.onState(true);
    try { recognition.start(); }
    catch { this.fail(run, "start-failed"); return false; }
    return true;
  }

  text(run) { return [run.prefix, run.transcript].filter(Boolean).join(" ").slice(0, 2000); }

  stop(send = false) {
    const run = this.current;
    if (!run) return;
    run.send ||= send;
    if (run.phase === "stopping") return;
    run.phase = "stopping";
    this.onState(true);
    run.timer = setTimeout(() => this.fail(run, "stop-timeout"), this.stopTimeoutMs);
    try { run.recognition.stop(); }
    catch { this.fail(run, "stop-failed"); }
  }

  finish(run, error = null) {
    if (this.current !== run) return;
    clearTimeout(run.timer);
    this.current = null; // Close first: duplicate end/late result events cannot send again.
    this.onState(false);
    this.onEnd({ text: this.text(run), send: !error && run.send && Boolean(run.transcript), error });
  }

  fail(run, error) {
    if (this.current !== run) return;
    this.finish(run, error);
    try { run.recognition.abort(); } catch { /* Already closed by the browser. */ }
    this.onError(error);
  }

  cancel() {
    const run = this.current;
    if (!run) return;
    this.current = null;
    clearTimeout(run.timer);
    try { run.recognition.abort(); } catch { /* No active native recording. */ }
    this.onState(false);
  }
}

if (typeof module !== "undefined" && module.exports) module.exports = { VoiceInput };
else globalThis.EchoVoiceInput = VoiceInput;
