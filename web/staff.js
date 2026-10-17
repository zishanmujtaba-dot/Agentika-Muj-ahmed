"use strict";
const loginPanel = document.getElementById("loginPanel"), queuePanel = document.getElementById("queuePanel");
const statusEl = document.getElementById("staffStatus"), list = document.getElementById("ticketList");
const loginBtn = document.getElementById("loginBtn");
let authorization = null, timer, loading = false, epoch = 0, backoff = 4000;
const nodes = new Map();

async function api(url, options = {}) {
  const controller = new AbortController(); const timeout = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(url, { ...options, cache: "no-store", signal: controller.signal,
      headers: { ...options.headers, Authorization: authorization || "" } });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) {
      const error = new Error(typeof data.detail === "string" ? data.detail : `Request failed (${response.status}).`);
      error.status = response.status; throw error;
    }
    return data;
  } finally { clearTimeout(timeout); }
}
function signOut(message = "Signed out.") {
  epoch++; authorization = null; clearTimeout(timer); loading = false;
  nodes.clear(); list.replaceChildren(); queuePanel.hidden = true; loginPanel.hidden = false;
  document.getElementById("password").value = ""; statusEl.textContent = message;
}
document.getElementById("logoutBtn").addEventListener("click", () => signOut());
document.getElementById("loginForm").addEventListener("submit", async event => {
  event.preventDefault(); loginBtn.disabled = true; statusEl.textContent = "Signing in…";
  try {
    const username = document.getElementById("username").value.trim();
    const password = document.getElementById("password").value;
    authorization = `Basic ${btoa(`${username}:${password}`)}`;
    const data = await api("/staff/auth");
    document.getElementById("password").value = "";
    loginPanel.hidden = true; queuePanel.hidden = false;
    statusEl.textContent = `Signed in as ${data.username}. Pending questions refresh automatically.`;
    epoch++; poll(epoch);
  } catch (error) {
    authorization = null; statusEl.textContent = error.message || "Sign-in failed. Check the server and try again.";
  } finally { loginBtn.disabled = false; }
});

function ticketNode(ticket) {
  const article = document.createElement("article"); article.className = "ticket";
  const meta = document.createElement("div"); meta.className = "ticket-meta";
  const badge = document.createElement("span"); badge.className = "badge"; badge.textContent = ticket.department || "Helpdesk";
  const detail = document.createElement("span");
  detail.textContent = `#${ticket.id} · ${new Date(ticket.created_at).toLocaleString()} · ${(ticket.reason || "follow-up").replaceAll("_", " ")}`;
  meta.append(badge, detail);
  const title = document.createElement("h3"); title.textContent = ticket.student_query;
  article.append(meta, title);
  if (!ticket.can_reply) {
    const note = document.createElement("p"); note.textContent = "Legacy ticket: this conversation predates secure sessions. Handle through the helpdesk.";
    article.append(note); return article;
  }
  const form = document.createElement("form");
  const label = document.createElement("label"); label.htmlFor = `reply-${ticket.id}`; label.textContent = "Reply to student";
  const textarea = document.createElement("textarea"); textarea.id = label.htmlFor; textarea.required = true;
  textarea.maxLength = 6000; textarea.placeholder = "Explain the next step or answer their question…";
  const errorEl = document.createElement("p"); errorEl.className = "ticket-error"; errorEl.setAttribute("role", "status");
  const button = document.createElement("button"); button.type = "submit"; button.textContent = "Send reply and resolve";
  form.append(label, textarea, errorEl, button); article.append(form);
  form.addEventListener("submit", async event => {
    event.preventDefault(); const text = textarea.value.trim(); if (!text || button.disabled) return;
    const activeEpoch = epoch; button.disabled = true; textarea.readOnly = true; button.textContent = "Saving reply…"; errorEl.textContent = "";
    try {
      await api(`/escalations/${ticket.id}/reply`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ text }) });
      if (activeEpoch !== epoch) return;
      article.remove(); nodes.delete(ticket.id);
      statusEl.textContent = `Reply to ticket #${ticket.id} saved and delivered to the conversation.`;
      refreshCount(); clearTimeout(timer); poll(epoch);
    } catch (error) {
      if (activeEpoch !== epoch) return;
      if (error.status === 401) { signOut("Your credentials were rejected. Sign in again."); return; }
      errorEl.textContent = error.status ? error.message : "Couldn't confirm the save. Retry the same reply safely.";
      button.disabled = false; textarea.readOnly = false; button.textContent = "Retry reply";
    }
  });
  return article;
}
function refreshCount() {
  document.getElementById("ticketCount").textContent = nodes.size;
  document.getElementById("emptyQueue").hidden = nodes.size !== 0;
}
function render(tickets) {
  const ids = new Set(tickets.map(ticket => ticket.id));
  for (const [id, node] of nodes) if (!ids.has(id)) { node.remove(); nodes.delete(id); }
  for (const ticket of tickets) if (!nodes.has(ticket.id)) {
    const node = ticketNode(ticket); nodes.set(ticket.id, node); list.append(node);
  }
  // Existing nodes stay in place so background polling preserves typed drafts and focus.
  refreshCount();
}
async function poll(activeEpoch) {
  if (!authorization || activeEpoch !== epoch || loading) return;
  loading = true; const recovering = backoff > 4000; let delay = document.hidden ? 15000 : 4000;
  try {
    const tickets = await api("/escalations");
    if (activeEpoch !== epoch) return;
    render(tickets); backoff = 4000;
    if (recovering) statusEl.textContent = "Connected. Queue is up to date.";
  } catch (error) {
    if (activeEpoch !== epoch) return;
    if (error.status === 401) { signOut("Sign in again to view the queue."); return; }
    backoff = Math.min(backoff * 2, 30000); delay = backoff;
    statusEl.textContent = error.message || "Connection interrupted. Retrying shortly; your drafts are preserved.";
  } finally {
    if (activeEpoch === epoch) {
      loading = false;
      if (authorization) { clearTimeout(timer); timer = setTimeout(() => poll(activeEpoch), delay); }
    }
  }
}
document.addEventListener("visibilitychange", () => {
  if (!document.hidden && authorization) { clearTimeout(timer); poll(epoch); }
});
window.addEventListener("pagehide", () => signOut("Sign in to view the queue."));
