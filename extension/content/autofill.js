/**
 * Career OS content script — Greenhouse / Lever / Workday.
 * Review mode: fill only. Auto mode: fill + Submit when gates pass.
 */

function norm(s) {
  return String(s || "")
    .toLowerCase()
    .replace(/\s+/g, " ")
    .trim();
}

function setNativeValue(el, value) {
  if (value == null || value === "") return false;
  const proto =
    el.tagName === "TEXTAREA"
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
  const setter = Object.getOwnPropertyDescriptor(proto, "value")?.set;
  if (setter) setter.call(el, value);
  else el.value = value;
  el.dispatchEvent(new Event("input", { bubbles: true }));
  el.dispatchEvent(new Event("change", { bubbles: true }));
  return true;
}

function labelFor(el) {
  const id = el.getAttribute("id");
  if (id) {
    const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
    if (lab) return lab.textContent || "";
  }
  const wrapped = el.closest("label");
  if (wrapped) return wrapped.textContent || "";
  const aria = el.getAttribute("aria-label");
  if (aria) return aria;
  return el.getAttribute("name") || el.getAttribute("placeholder") || "";
}

function matchQA(label, profile) {
  const L = norm(label);
  const list = profile?.screening_qa || [];
  let best = null;
  let bestScore = 0;
  for (const item of list) {
    const q = norm(item.question);
    if (!q) continue;
    let score = 0;
    if (L === q) score = 100;
    else if (L.includes(q) || q.includes(L)) score = 70;
    else {
      const a = new Set(L.split(" "));
      const b = new Set(q.split(" "));
      let overlap = 0;
      for (const t of a) if (b.has(t)) overlap += 1;
      const ratio = overlap / Math.max(a.size, 1);
      if (ratio >= 0.5) score = Math.floor(40 + ratio * 40);
    }
    if (score > bestScore) {
      bestScore = score;
      best = item.answer;
    }
  }
  return bestScore >= 40 ? { answer: best, score: bestScore } : null;
}

function matchProfileField(label, profile) {
  const L = norm(label);
  const p = profile?.profile || {};
  if (!L) return null;
  if (/(first.?name|given.?name)/.test(L)) return { value: p.first_name, conf: 0.95 };
  if (/(last.?name|family.?name|surname)/.test(L)) return { value: p.last_name, conf: 0.95 };
  if (/(full.?name|^name$|legal.?name)/.test(L) && !/company|user|file/.test(L)) {
    return { value: p.full_name, conf: 0.9 };
  }
  if (/e-?mail/.test(L)) return { value: p.email, conf: 0.95 };
  if (/phone|mobile|tel/.test(L)) return { value: p.phone, conf: p.phone ? 0.85 : 0.2 };
  if (/linkedin/.test(L)) return { value: p.linkedin, conf: p.linkedin ? 0.8 : 0.2 };
  if (/location|city|where.*based/.test(L)) {
    return { value: p.location, conf: p.location ? 0.75 : 0.25 };
  }
  if (/authoriz|work.?permit|legally.*work|visa/.test(L)) {
    const qa = matchQA(L, profile);
    if (qa) return { value: qa.answer, conf: qa.score / 100 };
    return { value: p.work_authorization, conf: p.work_authorization ? 0.7 : 0.15 };
  }
  const qa = matchQA(L, profile);
  if (qa) return { value: qa.answer, conf: qa.score / 100 };
  return null;
}

function detectBlocker() {
  const body = norm(document.body?.innerText || "");
  if (/captcha|recaptcha|hcaptcha|verify you are human|cf-turnstile/.test(body)) {
    return { reason: "captcha", detail: "Captcha / human verification detected" };
  }
  if (
    /sign in|log in|create an account|sso|authenticate to continue/.test(body) &&
    document.querySelector("input[type=password]")
  ) {
    return { reason: "login", detail: "Login / signup required" };
  }
  return null;
}

function findSubmitButton() {
  const buttons = [...document.querySelectorAll("button, input[type=submit], a[role=button]")];
  const scored = [];
  for (const el of buttons) {
    const t = norm(el.innerText || el.value || el.getAttribute("aria-label") || "");
    if (!t) continue;
    if (/submit application|submit|apply now|send application/.test(t) && !/cancel|back|save draft/.test(t)) {
      scored.push({ el, score: /submit application|apply now/.test(t) ? 2 : 1 });
    }
  }
  scored.sort((a, b) => b.score - a.score);
  return scored[0]?.el || null;
}

function showToast(text) {
  let el = document.getElementById("career-os-autofill-toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "career-os-autofill-toast";
    document.documentElement.appendChild(el);
  }
  el.textContent = text;
  el.classList.add("career-os-show");
  setTimeout(() => el.classList.remove("career-os-show"), 4000);
}

function fillPage(profile) {
  const fields = [
    ...document.querySelectorAll(
      "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=file]):not([type=checkbox]):not([type=radio]), textarea"
    ),
  ];
  let filled = 0;
  let attempted = 0;
  let confSum = 0;
  let missingRequired = 0;

  for (const el of fields) {
    if (el.disabled || el.readOnly) continue;
    const label = labelFor(el);
    const required = el.required || el.getAttribute("aria-required") === "true";
    attempted += 1;
    const hit = matchProfileField(label, profile);
    if (hit?.value != null && String(hit.value).trim() !== "") {
      if (setNativeValue(el, String(hit.value))) {
        filled += 1;
        confSum += hit.conf || 0.5;
      }
    } else if (required) {
      missingRequired += 1;
    }
  }

  const confidence =
    attempted === 0 ? 0 : Math.min(0.99, (confSum / Math.max(filled, 1)) * (filled / attempted));
  return { filled, attempted, confidence, missingRequired };
}

async function reportEvent(payload) {
  return await new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "REPORT_EVENT", payload }, (res) => {
      resolve(res || { ok: false });
    });
  });
}

async function runFill({ autoSubmit }) {
  const profileRes = await new Promise((resolve) => {
    chrome.runtime.sendMessage({ type: "FETCH_PROFILE" }, resolve);
  });
  if (!profileRes?.ok) {
    return { ok: false, error: profileRes?.error || "Profile fetch failed" };
  }
  const profile = profileRes.profile;
  const host = location.hostname;
  const url = location.href;

  const blocker = detectBlocker();
  if (blocker) {
    await reportEvent({
      event_type: "skip",
      host,
      url,
      reason: blocker.reason,
      detail: blocker.detail,
      confidence: 0,
    });
    showToast(`Paused: ${blocker.detail}. Marked Needs input / Failed.`);
    return { ok: false, error: blocker.detail, skipped: true };
  }

  const stats = fillPage(profile);
  await reportEvent({
    event_type: "filled",
    host,
    url,
    confidence: stats.confidence,
  });

  const mode = profile.mode || "autofill_only";
  const wantAuto = autoSubmit || mode === "auto_submit";

  if (stats.missingRequired > 0) {
    await reportEvent({
      event_type: "skip",
      host,
      url,
      reason: "missing_answer",
      detail: `${stats.missingRequired} required field(s) unmatched`,
      confidence: stats.confidence,
    });
    showToast(
      `Filled ${stats.filled}. Missing answers — add to Screening Q&A, then Reapply.`
    );
    return { ok: true, filled: stats.filled, confidence: stats.confidence, submitted: false };
  }

  if (!wantAuto) {
    showToast(`Career OS filled ${stats.filled} field(s). You click Submit.`);
    return { ok: true, filled: stats.filled, confidence: stats.confidence, submitted: false };
  }

  const gate = await reportEvent({
    event_type: "submit_attempt",
    host,
    url,
    confidence: stats.confidence,
  });
  if (!gate?.allowed && !gate?.ok) {
    showToast(gate?.reason || "Auto Submit blocked — Review mode fill only.");
    return {
      ok: true,
      filled: stats.filled,
      confidence: stats.confidence,
      submitted: false,
      reason: gate?.reason,
    };
  }
  // API returns { ok, allowed, reason }
  if (gate && gate.allowed === false) {
    showToast(gate.reason || "Auto Submit not allowed");
    return {
      ok: true,
      filled: stats.filled,
      confidence: stats.confidence,
      submitted: false,
      reason: gate.reason,
    };
  }

  const btn = findSubmitButton();
  if (!btn) {
    await reportEvent({
      event_type: "skip",
      host,
      url,
      reason: "other",
      detail: "Submit button not found",
      confidence: stats.confidence,
    });
    showToast("Filled form but no Submit button found — click Submit yourself.");
    return { ok: true, filled: stats.filled, submitted: false };
  }

  btn.click();
  await reportEvent({
    event_type: "submitted",
    host,
    url,
    confidence: Math.max(stats.confidence, 0.85),
  });
  showToast("Auto Apply: Submit clicked (allowlisted). Confirm on Tracker.");
  return { ok: true, filled: stats.filled, confidence: stats.confidence, submitted: true };
}

chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
  if (msg?.type !== "CAREER_OS_FILL") return false;
  runFill({ autoSubmit: !!msg.autoSubmit })
    .then(sendResponse)
    .catch((err) => sendResponse({ ok: false, error: String(err?.message || err) }));
  return true;
});
