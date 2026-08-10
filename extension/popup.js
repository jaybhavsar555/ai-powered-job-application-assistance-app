const DEFAULT_API = "http://localhost:8001/api/v1";

const apiBaseEl = document.getElementById("apiBase");
const tokenEl = document.getElementById("token");
const emailEl = document.getElementById("email");
const passwordEl = document.getElementById("password");
const consentEl = document.getElementById("consent");
const statusEl = document.getElementById("status");

function setStatus(msg, ok) {
  statusEl.textContent = msg;
  statusEl.className = ok ? "ok" : "err";
}

chrome.storage.local.get(["apiBase", "token", "autoConsent", "email"], (data) => {
  apiBaseEl.value = data.apiBase || DEFAULT_API;
  tokenEl.value = data.token || "";
  emailEl.value = data.email || "";
  consentEl.checked = !!data.autoConsent;
});

async function syncConsentToServer(apiBase, token, consent) {
  if (!token) return;
  try {
    await fetch(`${apiBase}/apply-prefs/`, {
      method: "PUT",
      headers: {
        Authorization: `Bearer ${token}`,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        apply_mode: consent ? "auto_apply" : "review_and_apply",
        auto_consent: !!consent,
      }),
    });
  } catch (_) {
    /* local save still works */
  }
}

async function savePrefs({ apiBase, token, autoConsent, email }) {
  const payload = { apiBase, token, autoConsent };
  if (email) payload.email = email;
  await chrome.storage.local.set(payload);
  await syncConsentToServer(apiBase, token, autoConsent);
}

document.getElementById("login").addEventListener("click", async () => {
  const apiBase = (apiBaseEl.value || DEFAULT_API).replace(/\/$/, "");
  const email = (emailEl.value || "").trim();
  const password = passwordEl.value || "";
  const autoConsent = !!consentEl.checked;
  if (!email || !password) {
    setStatus("Enter email and password", false);
    return;
  }
  try {
    const res = await fetch(`${apiBase}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      setStatus(data.detail || `Login failed (${res.status})`, false);
      return;
    }
    const token = data.access_token || data.token;
    if (!token) {
      setStatus("Login OK but no token returned", false);
      return;
    }
    tokenEl.value = token;
    passwordEl.value = "";
    await savePrefs({ apiBase, token, autoConsent, email });
    setStatus(
      autoConsent
        ? "Logged in. Auto Apply consent ON."
        : "Logged in. Review mode — you click Submit.",
      true
    );
  } catch (err) {
    setStatus(String(err?.message || err), false);
  }
});

document.getElementById("save").addEventListener("click", async () => {
  const apiBase = (apiBaseEl.value || DEFAULT_API).replace(/\/$/, "");
  const token = (tokenEl.value || "").trim();
  const autoConsent = !!consentEl.checked;
  const email = (emailEl.value || "").trim();
  await savePrefs({ apiBase, token, autoConsent, email });
  setStatus(
    autoConsent
      ? "Saved. Auto Apply consent ON (allowlisted ATS only)."
      : "Saved. Review mode — you always click Submit.",
    true
  );
});

document.getElementById("test").addEventListener("click", () => {
  chrome.runtime.sendMessage({ type: "FETCH_PROFILE" }, (res) => {
    if (chrome.runtime.lastError) {
      setStatus(chrome.runtime.lastError.message, false);
      return;
    }
    if (!res?.ok) {
      setStatus(res?.error || "Profile fetch failed", false);
      return;
    }
    const name = res.profile?.profile?.full_name || "?";
    const mode = res.profile?.mode || "?";
    const qa = res.profile?.screening_qa?.length || 0;
    setStatus(`OK · ${name} · ${mode} · ${qa} Q&A`, true);
  });
});

async function fillActiveTab(autoSubmit) {
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (!tab?.id) {
    setStatus("No active tab", false);
    return;
  }
  chrome.tabs.sendMessage(
    tab.id,
    { type: "CAREER_OS_FILL", autoSubmit: !!autoSubmit },
    (res) => {
      if (chrome.runtime.lastError) {
        setStatus("Open Greenhouse / Lever / Workday apply page first.", false);
        return;
      }
      if (!res?.ok) {
        setStatus(res?.error || "Fill failed", false);
        return;
      }
      if (res.submitted) {
        setStatus(
          `Auto submitted · filled ${res.filled} · conf ${(res.confidence || 0).toFixed(2)}`,
          true
        );
      } else {
        setStatus(
          `Filled ${res.filled || 0}. ${res.reason || "You click Submit."}`,
          true
        );
      }
    }
  );
}

document.getElementById("fill").addEventListener("click", () => fillActiveTab(false));
document.getElementById("auto").addEventListener("click", () => fillActiveTab(true));
