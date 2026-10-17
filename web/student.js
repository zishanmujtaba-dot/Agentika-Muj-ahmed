"use strict";
const form = document.getElementById("chatForm");
const question = document.getElementById("question");
const messages = document.getElementById("messages");
const statusEl = document.getElementById("status");
const sendBtn = document.getElementById("sendBtn");
const callBtn = document.getElementById("callBtn");
const callStatus = document.getElementById("callStatus");
const mutedRequests = new Set();
const talkBtn = document.getElementById("talkBtn");
const newBtn = document.getElementById("newChat");
const speechEnabled = document.getElementById("speakAnswers");
const SESSION_KEY = "echo.conversation.v1";
const PENDING_KEY = "echo.pending.v1";
let session = null, pending = null, busy = false, ready = false, inFlightRequestId = null;
let cursor = 0, generation = 0, pollTimer, pollPromise = null, retryDelay = 3000;
const shown = new Set();

function saved(key) { try { return JSON.parse(sessionStorage.getItem(key)); } catch { return null; } }
function store(key, value) { try { sessionStorage.setItem(key, JSON.stringify(value)); } catch { /* Current page remains usable without storage. */ } }
function forget(key) { try { sessionStorage.removeItem(key); } catch { /* Storage may be unavailable. */ } }
function requestId() {
  if (crypto.randomUUID) return crypto.randomUUID();
  const bytes = crypto.getRandomValues(new Uint8Array(16));
  bytes[6] = (bytes[6] & 15) | 64; bytes[8] = (bytes[8] & 63) | 128;
  const hex = [...bytes].map(x => x.toString(16).padStart(2, "0")).join("");
  return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
}
async function api(url, options = {}, timeout = 45000) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeout);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal, cache: "no-store" });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(typeof data.detail === "string" ? data.detail : `Request failed (${response.status}).`);
      error.status = response.status; error.retry = response.headers.get("Retry-After"); throw error;
    }
    return data;
  } finally { clearTimeout(timer); }
}
function tokenHeaders() { return { "X-Conversation-Token": session.session_token }; }
function updateControls() {
  sendBtn.disabled = busy || !ready || Boolean(voice?.stopping);
  talkBtn.disabled = busy || !ready || !voice || voice.stopping || Boolean(liveCall?.active);
  callBtn.disabled = !liveCall || (!liveCall.active && (busy || !ready || listening || liveCall.processing));
  callBtn.textContent = liveCall?.active ? "End voice call" : "Start voice call";
  callBtn.setAttribute("aria-pressed", String(Boolean(liveCall?.active)));
  newBtn.disabled = busy || listening || Boolean(liveCall?.active);
  question.readOnly = busy || listening || Boolean(liveCall?.active);
  sendBtn.textContent = busy ? "Sending…" : voice?.stopping ? "Finishing voice…" : listening ? "Finish and send" : pending ? "Retry question" : "Send question";
  document.querySelectorAll("[data-question]").forEach(button => { button.disabled = busy || listening || Boolean(liveCall?.active); });
}
function speak(text, requestId) {
  if (mutedRequests.has(String(requestId)) || (liveCall?.active && (liveCall.speaking || liveCall.draft().trim()))) return;
  if (listening || (!speechEnabled.checked && !liveCall?.active) || !window.speechSynthesis || !window.SpeechSynthesisUtterance) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  if (liveCall?.active) {
    callStatus.textContent = "ECHO is speaking. Speak to interrupt.";
    utterance.addEventListener("end", () => {
      if (liveCall.active && !liveCall.draft()) callStatus.textContent = "Listening. Pause for two seconds to send.";
    });
  }
  speechSynthesis.speak(utterance);
}
document.getElementById("stopSpeech").addEventListener("click", () => window.speechSynthesis?.cancel());
speechEnabled.addEventListener("change", () => { if (!speechEnabled.checked) window.speechSynthesis?.cancel(); });

function renderMessage(message, announce = false) {
  if (shown.has(message.id)) return;
  shown.add(message.id); document.getElementById("emptyChat")?.remove();
  const bubble = document.createElement("article");
  const kind = ["student", "staff", "agent"].includes(message.from) ? message.from : "agent";
  bubble.className = `message ${kind}`;
  const label = document.createElement("span"); label.className = "message-label";
  label.textContent = kind === "student" ? "You" : kind === "staff" ? "Staff reply" : "ECHO";
  bubble.append(label);
  const detail = message.metadata || {};
  const originalQuestion = message.reply_to?.question || detail.question;
  if (kind === "staff" && originalQuestion) {
    const context = document.createElement("div"); context.className = "reply-context";
    const caption = document.createElement("span"); caption.textContent = "In reply to your question";
    const quote = document.createElement("blockquote"); quote.textContent = originalQuestion;
    context.append(caption, quote); bubble.append(context);
  }
  const body = document.createElement("p"); body.textContent = message.text;
  bubble.append(body);
  const meta = document.createElement("div"); meta.className = "message-meta";
  const time = new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  meta.textContent = time;
  if (detail.status === "unavailable") meta.textContent += " · Follow-up was not saved";
  bubble.append(meta); messages.append(bubble); messages.scrollTop = messages.scrollHeight;
  if (announce && kind !== "student") speak(message.text, message.request_id);
  if (announce && kind === "staff" && !busy) statusEl.textContent = "A staff reply has arrived.";
}

function syncMessages() {
  if (pollPromise) return pollPromise;
  if (!session) return Promise.resolve(false);
  const active = session, epoch = generation, hadHistory = shown.size > 0;
  const promise = (async () => {
    const data = await api(`/poll/${active.session_id}?since=${cursor}`, {
      headers: { "X-Conversation-Token": active.session_token },
    }, 12000);
    if (epoch !== generation) return false;
    for (const message of data.messages) renderMessage(message, hadHistory || Boolean(liveCall?.active));
    cursor = data.cursor; retryDelay = 3000;
    return data.has_more;
  })();
  pollPromise = promise;
  return promise.finally(() => { if (pollPromise === promise) pollPromise = null; });
}
async function pollLoop(epoch) {
  if (epoch !== generation || !session) return;
  let delay = document.hidden ? 15000 : 3000;
  const recovering = retryDelay > 3000;
  try {
    if (await syncMessages()) delay = 0;
    if (recovering && !busy && !pending) statusEl.textContent = "Connected. Waiting for new replies.";
  } catch (error) {
    if (epoch !== generation) return;
    if (error.status === 401) {
      ready = false; updateControls(); statusEl.textContent = "Conversation access expired. Start a new conversation.";
      return;
    }
    retryDelay = Math.min(retryDelay * 2, 30000); delay = retryDelay;
    if (!busy) statusEl.textContent = "Connection interrupted. Checking for replies again shortly…";
  }
  if (epoch === generation) { clearTimeout(pollTimer); pollTimer = setTimeout(() => pollLoop(epoch), delay); }
}
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && session && ready) { clearTimeout(pollTimer); pollLoop(generation); }
});

async function initialize(fresh = false) {
  generation++; const epoch = generation; clearTimeout(pollTimer); session = null; ready = false; pollPromise = null;
  shown.clear(); cursor = 0; messages.replaceChildren();
  const empty = document.createElement("p"); empty.id = "emptyChat"; empty.className = "empty";
  empty.textContent = "Ask a question to get started."; messages.append(empty);
  if (fresh) { forget(SESSION_KEY); forget(PENDING_KEY); pending = null; question.value = ""; window.speechSynthesis?.cancel(); }
  updateControls(); statusEl.textContent = "Connecting to your conversation…";
  try {
    const previous = fresh ? null : saved(SESSION_KEY);
    const candidate = previous?.session_id && previous?.session_token ? previous : await api("/sessions", { method: "POST" });
    if (epoch !== generation) return;
    session = candidate;
    store(SESSION_KEY, session);
    pending = fresh ? null : saved(PENDING_KEY);
    if (pending?.query && pending?.request_id) question.value = pending.query;
    else pending = null;
    ready = true; updateControls();
    statusEl.textContent = pending ? "Your last question can be retried safely." : "Ready for your question.";
    pollLoop(generation);
  } catch { if (epoch !== generation) return; ready = false; updateControls(); statusEl.textContent = "Could not connect. Check the server, then choose New conversation to retry."; }
}
newBtn.addEventListener("click", () => initialize(true));
document.querySelectorAll("[data-question]").forEach(button => button.addEventListener("click", () => {
  question.value = button.dataset.question; question.focus();
}));

async function sendQuestion(event, voiceQuery = null) {
  event?.preventDefault();
  if (listening) { voice?.stop(true); return; }
  if (liveCall?.active && voiceQuery === null) { liveCall.flush(); return; }
  const query = (voiceQuery ?? question.value).trim();
  if (!query || busy || !ready) return;
  if (!pending || pending.query !== query) pending = { query, request_id: requestId() };
  store(PENDING_KEY, pending); inFlightRequestId = String(pending.request_id); busy = true; updateControls();
  statusEl.textContent = "Checking the policy rulebook…";
  try {
    const result = await api("/ask", {
      method: "POST", headers: { "Content-Type": "application/json", ...tokenHeaders() },
      body: JSON.stringify({ ...pending, session_id: session.session_id }),
    });
    pending = null; forget(PENDING_KEY); if (question.value.trim() === query) question.value = "";
    statusEl.textContent = result.status === "escalated" ? `Sent to ${result.department}. You can return to this tab for a staff reply.`
      : result.status === "unavailable" ? "The follow-up could not be saved. Try a new question or contact the helpdesk."
      : "Answered from the policy rulebook.";
    await syncMessages().catch(() => { /* Scheduled polling will recover the saved response. */ });
    return true;
  } catch (error) {
    if (error.status === 401) { ready = false; statusEl.textContent = "Conversation access denied. Start a new conversation."; }
    else if (error.status === 409 && error.retry) statusEl.textContent = "This question is still processing. Wait a few seconds, then Retry question.";
    else statusEl.textContent = "The request did not finish here. Retry the same question to recover its saved result.";
    return false;
  } finally { busy = false; inFlightRequestId = null; updateControls(); question.focus(); }
}
form.addEventListener("submit", sendQuestion);
// Stop recognition even if the required textarea is still empty/interim; wait
// for the native final result before submitting the question.
sendBtn.addEventListener("click", event => {
  if (liveCall?.active) { event.preventDefault(); liveCall.flush(); }
  else if (listening) { event.preventDefault(); voice?.stop(true); }
});
question.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) {
    event.preventDefault();
    if (listening) voice?.stop(true); else form.requestSubmit();
  }
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
let listening = false;
const voice = SpeechRecognition ? new EchoVoiceInput({
  Recognition: SpeechRecognition,
  onText: text => { question.value = text; },
  onState: active => {
    listening = active;
    talkBtn.classList.toggle("listening", active);
    talkBtn.textContent = active ? "Finish and send" : "Use voice";
    updateControls();
  },
  onEnd: ({ text, send, error }) => {
    if (error) return; // The error callback preserves the draft and explains recovery.
    question.value = text;
    if (send && text.trim()) sendQuestion();
    else statusEl.textContent = text.trim() ? "Transcript ready. Review it and send your question." : "No speech captured. Try again or type your question.";
  },
  onError: error => {
    statusEl.textContent = error === "not-allowed" || error === "service-not-allowed"
      ? "Microphone access was denied. You can type your question."
      : error === "stop-timeout" ? "Voice input did not finish. Review the text, then send it yourself."
      : "Voice input stopped. Review the text or type your question.";
  },
}) : null;
const liveCall = SpeechRecognition && window.speechSynthesis && window.SpeechSynthesisUtterance ? new EchoLiveCall({
  Recognition: SpeechRecognition,
  onText: text => { question.value = text; },
  onSpeech: () => {
    window.speechSynthesis.cancel();
    if (busy && inFlightRequestId) {
      mutedRequests.add(inFlightRequestId);
      if (mutedRequests.size > 100) mutedRequests.delete(mutedRequests.values().next().value);
    }
    callStatus.textContent = "Listening to you. Pause for two seconds to send.";
  },
  onSettled: () => updateControls(),
  onSubmit: async text => {
    callStatus.textContent = "Waiting for ECHO. You can keep speaking to ask the next question.";
    const sent = await sendQuestion(null, text);
    if (!sent && liveCall.active) {
      liveCall.fail("send-failed");
      if (!question.value.trim()) question.value = text;
    }
  },
  onState: active => {
    if (!active) window.speechSynthesis.cancel();
    callStatus.hidden = !active;
    callStatus.textContent = active ? "Listening. Pause for two seconds to send. Use headphones to avoid speaker echo." : "";
    updateControls();
  },
  onError: error => {
    callStatus.hidden = false;
    callStatus.textContent = error === "not-allowed" || error === "service-not-allowed"
      ? "Call ended: microphone access was denied. You can still type."
      : error === "send-failed" ? "Call paused because sending failed. Review your draft or retry the last question."
      : "Call ended because voice input stopped. Your draft is kept; try starting the call again.";
  },
}) : null;
callBtn.addEventListener("click", () => {
  if (!liveCall) return;
  if (liveCall.active) { liveCall.stop(); return; }
  if (busy || !ready || listening) return;
  if (question.value.trim() || pending) {
    statusEl.textContent = "Send or clear your existing draft before starting a live call.";
    return;
  }
  window.speechSynthesis.cancel(); liveCall.start();
});
if (!voice) document.getElementById("voiceNote").textContent = "Speech recognition is unavailable in this browser. Text chat is fully available.";
else document.getElementById("voiceNote").textContent = "Use voice records one question for review. Voice call sends after two seconds of silence and lets you interrupt ECHO. Use headphones; recognition depends on your browser’s speech service.";
talkBtn.addEventListener("click", () => {
  if (!voice || busy || !ready || voice.stopping) return;
  if (listening) { voice.stop(true); return; }
  window.speechSynthesis?.cancel();
  if (voice.start(question.value)) statusEl.textContent = "Listening… pause to review, or choose Finish and send.";
});
window.addEventListener("pagehide", () => { voice?.cancel(); liveCall?.stop(); window.speechSynthesis?.cancel(); clearTimeout(pollTimer); });
window.addEventListener("pageshow", event => {
  if (event.persisted && session && ready) { clearTimeout(pollTimer); pollLoop(generation); }
});
initialize();
