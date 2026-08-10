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

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type === "FETCH_PROFILE") {
    fetchProfile().then(sendResponse);
    return true;
  }
  if (msg?.type === "REPORT_EVENT") {
    reportEvent(msg.payload).then(sendResponse);
    return true;
  }
  return false;
});
