"use strict";
const form = document.getElementById("chatForm");
const question = document.getElementById("question");
const messages = document.getElementById("messages");
const statusEl = document.getElementById("status");
const sendBtn = document.getElementById("sendBtn");
const talkBtn = document.getElementById("talkBtn");
const newBtn = document.getElementById("newChat");
const speechEnabled = document.getElementById("speakAnswers");
const SESSION_KEY = "echo.conversation.v1";
const PENDING_KEY = "echo.pending.v1";
let session = null, pending = null, busy = false, ready = false;
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
  sendBtn.disabled = busy || !ready || listening;
  talkBtn.disabled = busy || !ready || !recognition;
  newBtn.disabled = busy || listening;
  question.readOnly = busy || listening;
  sendBtn.textContent = busy ? "Sending…" : (pending ? "Retry question ↗" : "Send question ↗");
  document.querySelectorAll("[data-question]").forEach(button => { button.disabled = busy || listening; });
}
function speak(text) {
  if (!speechEnabled.checked || !window.speechSynthesis || !window.SpeechSynthesisUtterance) return;
  speechSynthesis.cancel(); speechSynthesis.speak(new SpeechSynthesisUtterance(text));
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
  const body = document.createElement("p"); body.textContent = message.text;
  bubble.append(label, body);
  const meta = document.createElement("div"); meta.className = "message-meta";
  const detail = message.metadata || {};
  const time = new Date(message.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  meta.textContent = detail.ticket_id ? `${time} · Ticket #${detail.ticket_id}` : time;
  if (detail.status === "unavailable") meta.textContent += " · Follow-up was not saved";
  bubble.append(meta); messages.append(bubble); messages.scrollTop = messages.scrollHeight;
  if (announce && kind !== "student") speak(message.text);
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
    for (const message of data.messages) renderMessage(message, hadHistory);
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
  empty.textContent = "Your questions and staff replies will appear here."; messages.append(empty);
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
    statusEl.textContent = pending ? "Your last question can be retried safely." : "Ready. Type a question or use voice.";
    pollLoop(generation);
  } catch { if (epoch !== generation) return; ready = false; updateControls(); statusEl.textContent = "Could not connect. Check the server, then choose New conversation to retry."; }
}
newBtn.addEventListener("click", () => initialize(true));
document.querySelectorAll("[data-question]").forEach(button => button.addEventListener("click", () => {
  question.value = button.dataset.question; question.focus();
}));

async function sendQuestion(event) {
  event?.preventDefault();
  const query = question.value.trim();
  if (!query || busy || !ready || listening) return;
  if (!pending || pending.query !== query) pending = { query, request_id: requestId() };
  store(PENDING_KEY, pending); busy = true; updateControls();
  statusEl.textContent = "Checking the policy rulebook…";
  try {
    const result = await api("/ask", {
      method: "POST", headers: { "Content-Type": "application/json", ...tokenHeaders() },
      body: JSON.stringify({ ...pending, session_id: session.session_id }),
    });
    pending = null; forget(PENDING_KEY); question.value = "";
    statusEl.textContent = result.status === "escalated" ? `Sent to ${result.department}. You can return to this tab for a staff reply.`
      : result.status === "unavailable" ? "The follow-up could not be saved. Try a new question or contact the helpdesk."
      : "Answered from the policy rulebook.";
    await syncMessages().catch(() => { /* Scheduled polling will recover the saved response. */ });
  } catch (error) {
    if (error.status === 401) { ready = false; statusEl.textContent = "Conversation access denied. Start a new conversation."; }
    else if (error.status === 409 && error.retry) statusEl.textContent = "This question is still processing. Wait a few seconds, then Retry question.";
    else statusEl.textContent = "The request did not finish here. Retry the same question to recover its saved result.";
  } finally { busy = false; updateControls(); question.focus(); }
}
form.addEventListener("submit", sendQuestion);
question.addEventListener("keydown", event => {
  if (event.key === "Enter" && !event.shiftKey && !event.isComposing) { event.preventDefault(); form.requestSubmit(); }
});

const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
const recognition = SpeechRecognition ? new SpeechRecognition() : null;
let listening = false, sendOnEnd = false, voiceError = false, voicePrefix = "";
if (recognition) {
  recognition.lang = "en-US"; recognition.interimResults = true; recognition.continuous = true;
  recognition.addEventListener("result", event => {
    const transcript = [...event.results].map(result => result[0].transcript).join(" ");
    question.value = `${voicePrefix} ${transcript}`.trim().slice(0, 2000);
  });
  recognition.addEventListener("end", () => {
    const shouldSend = sendOnEnd; listening = false; sendOnEnd = false;
    talkBtn.classList.remove("listening"); talkBtn.textContent = "Start voice"; updateControls();
    if (shouldSend && question.value.trim()) sendQuestion();
    else if (!voiceError && question.value.trim()) statusEl.textContent = "Transcript ready. Review it and Send question.";
  });
  recognition.addEventListener("error", event => {
    voiceError = true; sendOnEnd = false; listening = false;
    talkBtn.classList.remove("listening"); talkBtn.textContent = "Start voice"; updateControls();
    statusEl.textContent = event.error === "not-allowed" ? "Microphone access was denied. You can type your question."
      : "Voice input stopped. You can review the transcript or type instead.";
  });
} else document.getElementById("voiceNote").textContent = "Speech recognition is unavailable in this browser. Text chat is fully available.";
talkBtn.addEventListener("click", () => {
  if (!recognition || busy || !ready) return;
  if (listening) { sendOnEnd = true; recognition.stop(); return; }
  window.speechSynthesis?.cancel(); voicePrefix = question.value.trim(); sendOnEnd = false; voiceError = false;
  try {
    recognition.start(); listening = true; talkBtn.classList.add("listening");
    talkBtn.textContent = "Stop and send"; statusEl.textContent = "Listening… click Stop and send when finished.";
  } catch { listening = false; statusEl.textContent = "Microphone could not start. You can type instead."; }
  updateControls();
});
window.addEventListener("pagehide", () => { sendOnEnd = false; recognition?.abort(); window.speechSynthesis?.cancel(); clearTimeout(pollTimer); });
window.addEventListener("pageshow", event => {
  if (event.persisted && session && ready) { clearTimeout(pollTimer); pollLoop(generation); }
});
initialize();
