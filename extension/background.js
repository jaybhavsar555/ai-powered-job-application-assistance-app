const DEFAULT_API = "http://localhost:8001/api/v1";

async function getConfig() {
  const data = await chrome.storage.local.get(["apiBase", "token"]);
  return {
    apiBase: (data.apiBase || DEFAULT_API).replace(/\/$/, ""),
    token: (data.token || "").trim(),
  };
}

async function fetchProfile() {
  const { apiBase, token } = await getConfig();
  if (!token) {
    return { ok: false, error: "No token — log in from the extension popup." };
  }
  try {
    const res = await fetch(`${apiBase}/extension/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 401) {
      await chrome.storage.local.remove(["token"]);
      return {
        ok: false,
        error: "Session expired — log in again in the extension popup.",
      };
    }
    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: `HTTP ${res.status}: ${text.slice(0, 120)}` };
    }
    const profile = await res.json();
    return { ok: true, profile };
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
}

async function reportEvent(payload) {
  const { apiBase, token } = await getConfig();
  if (!token) return { ok: false, error: "No token" };
  try {
    const res = await fetch(`${apiBase}/extension/events`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload || {}),
    });
    if (res.status === 401) {
      await chrome.storage.local.remove(["token"]);
      return { ok: false, error: "Session expired — log in again." };
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return { ok: false, ...data, error: data.detail || res.statusText };
    return data;
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
}

async function mapFields(labels) {
  const { apiBase, token } = await getConfig();
  if (!token) return { ok: false, error: "No token" };
  try {
    const res = await fetch(`${apiBase}/extension/map-fields`, {
      method: "POST",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ labels: labels || [] }),
    });
    if (res.status === 401) {
      await chrome.storage.local.remove(["token"]);
      return { ok: false, error: "Session expired" };
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) return { ok: false, error: data.detail || res.statusText };
    return { ok: true, mappings: data.mappings || [] };
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
}

async function fetchResumeFile(applicationId) {
  const { apiBase, token } = await getConfig();
  if (!token) {
    return { ok: false, error: "No token — log in from the extension popup." };
  }
  try {
    let url = `${apiBase}/extension/resume-file`;
    if (applicationId) {
      url += `?application_id=${encodeURIComponent(applicationId)}`;
    }
    const res = await fetch(url, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (res.status === 401) {
      await chrome.storage.local.remove(["token"]);
      return {
        ok: false,
        error: "Session expired — log in again in the extension popup.",
      };
    }
    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: `Resume HTTP ${res.status}: ${text.slice(0, 160)}` };
    }
    const buf = await res.arrayBuffer();
    const bytes = Array.from(new Uint8Array(buf));
    const cd = res.headers.get("content-disposition") || "";
    const match = /filename\*?=(?:UTF-8''|")?([^";]+)/i.exec(cd);
    const filename = match
      ? decodeURIComponent(match[1].replace(/"/g, "").trim())
      : "resume.pdf";
    const contentType =
      res.headers.get("content-type") ||
      (filename.toLowerCase().endsWith(".docx")
        ? "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        : "application/pdf");
    return { ok: true, bytes, filename, contentType };
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
}

async function fetchApplyQueue() {
  const { apiBase, token } = await getConfig();
  if (!token) return { ok: false, error: "No token" };
  try {
    const res = await fetch(`${apiBase}/extension/apply-queue`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      const text = await res.text();
      return { ok: false, error: text.slice(0, 120) };
    }
    const data = await res.json();
    const queue = data.queue || [];
    const count = queue.length;
    if (chrome.action && chrome.action.setBadgeText) {
      chrome.action.setBadgeText({ text: count > 0 ? String(count) : "" });
      chrome.action.setBadgeBackgroundColor({ color: "#2563eb" });
    }
    return { ok: true, queue };
  } catch (err) {
    return { ok: false, error: String(err?.message || err) };
  }
}

async function markQueueDone(applicationId) {
  const { apiBase, token } = await getConfig();
  if (!token || !applicationId) return { ok: false };
  try {
    const res = await fetch(
      `${apiBase}/extension/apply-queue/${encodeURIComponent(applicationId)}/done`,
      { method: "POST", headers: { Authorization: `Bearer ${token}` } }
    );
    return { ok: res.ok };
  } catch {
    return { ok: false };
  }
}

// Poll Loop Engineer apply queue every 5 minutes when extension is active
chrome.alarms.create("loopApplyQueue", { periodInMinutes: 5 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === "loopApplyQueue") {
    fetchApplyQueue().then((r) => {
      if (r.ok && r.queue && r.queue.length > 0) {
        const top = r.queue[0];
        chrome.notifications?.create?.(`loop-queue-${top.application_id}`, {
          type: "basic",
          iconUrl: "icons/icon48.png",
          title: "Career OS — ready to apply",
          message: `${top.title} @ ${top.company}`,
        });
      }
    });
  }
});

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "FETCH_PROFILE") {
    fetchProfile().then(sendResponse);
    return true;
  }
  if (msg?.type === "FETCH_APPLY_QUEUE") {
    fetchApplyQueue().then(sendResponse);
    return true;
  }
  if (msg?.type === "MARK_QUEUE_DONE") {
    markQueueDone(msg.applicationId).then(sendResponse);
    return true;
  }
  if (msg?.type === "REPORT_EVENT") {
    reportEvent(msg.payload).then(sendResponse);
    return true;
  }
  if (msg?.type === "MAP_FIELDS") {
    mapFields(msg.labels).then(sendResponse);
    return true;
  }
  if (msg?.type === "FETCH_RESUME_FILE") {
    fetchResumeFile(msg.applicationId).then(sendResponse);
    return true;
  }
  return false;
});
