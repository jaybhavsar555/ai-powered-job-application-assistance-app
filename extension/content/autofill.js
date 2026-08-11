if (!window.__CAREER_OS_AUTOFILL_LOADED) {
  window.__CAREER_OS_AUTOFILL_LOADED = true;

  function norm(s) {
    return String(s || "")
      .toLowerCase()
      .replace(/\s+/g, " ")
      .trim();
  }

  function setNativeValue(el, value) {
    if (value == null || value === "") return false;
    
    // Handle selects
    if (el.tagName === "SELECT") {
      const vNorm = norm(value);
      for (let i = 0; i < el.options.length; i++) {
        const opt = el.options[i];
        const t = norm(opt.text);
        const v = norm(opt.value);
        if (t === vNorm || v === vNorm || t.includes(vNorm) || vNorm.includes(t)) {
          el.selectedIndex = i;
          el.dispatchEvent(new Event("change", { bubbles: true }));
          return true;
        }
      }
      return false; // No matching option found
    }

    // Handle checkboxes/radios
    if (el.tagName === "INPUT" && (el.type === "radio" || el.type === "checkbox")) {
      const vNorm = norm(value);
      const isAffirmative = /yes|true|1|yep|agree/.test(vNorm);
      const isNegative = /no|false|0|nope|disagree/.test(vNorm);
      const elLabel = norm(labelFor(el) || el.value);
      const elAffirmative = /yes|true|1|yep|agree/.test(elLabel);
      const elNegative = /no|false|0|nope|disagree/.test(elLabel);

      if ((isAffirmative && elAffirmative) || (isNegative && elNegative) || vNorm === elLabel) {
        if (!el.checked) {
          el.click();
          // el.checked = true;
          el.dispatchEvent(new Event("change", { bubbles: true }));
        }
        return true;
      }
      return false;
    }

    // Standard text/number inputs and textareas
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
    let text = "";
    
    // Check aria-labelledby
    const ariaLabelledBy = el.getAttribute("aria-labelledby");
    if (ariaLabelledBy) {
      const labelEl = document.getElementById(ariaLabelledBy);
      if (labelEl) text = labelEl.textContent;
    }

    // Check explicit label for
    const id = el.getAttribute("id");
    if (!text && id) {
      const lab = document.querySelector(`label[for="${CSS.escape(id)}"]`);
      if (lab) text = lab.textContent;
    }
    
    // Check wrapping label
    if (!text) {
      const wrapped = el.closest("label");
      if (wrapped) {
        // Exclude the input's own text if it's a checkbox/radio
        const clone = wrapped.cloneNode(true);
        const inputs = clone.querySelectorAll('input');
        inputs.forEach(i => i.remove());
        text = clone.textContent;
      }
    }
    
    // Check previous/sibling text nodes (common in React/custom forms)
    if (!text) {
      const prev = el.previousElementSibling;
      if (prev && prev.tagName !== "INPUT" && prev.tagName !== "TEXTAREA" && prev.textContent.trim().length > 0 && prev.textContent.trim().length < 100) {
        text = prev.textContent;
      }
    }

    if (!text) text = el.getAttribute("aria-label");
    if (!text) text = el.getAttribute("name");
    if (!text) text = el.getAttribute("placeholder");
    return (text || "").trim();
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
    if (/authoriz|work.?permit|legally.*work|visa|sponsorship/.test(L)) {
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

  function isResumeFileInput(el) {
    if (!el || el.type !== "file") return false;
    const blob =
      norm(labelFor(el)) +
      " " +
      norm(el.getAttribute("name")) +
      " " +
      norm(el.getAttribute("id")) +
      " " +
      norm(el.getAttribute("accept")) +
      " " +
      norm(el.closest("label, .form-group, [data-testid], fieldset")?.textContent || "");
    if (
      /cover.?letter|transcript|portfolio|headshot|photo|avatar/.test(blob) &&
      !/resume|cv|curriculum/.test(blob)
    ) {
      return false;
    }
    if (/resume|cv|curriculum|upload.?resume|attach.?resume/.test(blob)) {
      return true;
    }
    if (el.accept && /pdf|msword|officedocument/.test(norm(el.accept))) return true;
    return false;
  }

  function findResumeFileInputs() {
    const all = [...document.querySelectorAll("input[type=file]")];
    const preferred = all.filter(isResumeFileInput);
    if (preferred.length) return preferred;
    // Single unlabeled file input (common on simple ATS) — try it
    return all.length === 1 ? all : [];
  }

  function attachFileToInput(input, file) {
    try {
      const dt = new DataTransfer();
      dt.items.add(file);
      input.files = dt.files;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      return input.files && input.files.length > 0;
    } catch {
      return false;
    }
  }

  async function fetchResumeBlob(applicationId) {
    const res = await new Promise((resolve) => {
      chrome.runtime.sendMessage(
        { type: "FETCH_RESUME_FILE", applicationId: applicationId || null },
        resolve
      );
    });
    if (!res?.ok || !res.bytes?.length) {
      return { ok: false, error: res?.error || "No resume file from API" };
    }
    const u8 = new Uint8Array(res.bytes);
    const file = new File([u8], res.filename || "resume.pdf", {
      type: res.contentType || "application/pdf",
    });
    return { ok: true, file };
  }

  async function fillResumeUploads(profile) {
    const inputs = findResumeFileInputs();
    if (!inputs.length) {
      return { attached: 0, attempted: 0, error: null };
    }
    const appId = profile?.resume?.application_id || null;
    const fetched = await fetchResumeBlob(appId);
    if (!fetched.ok) {
      return { attached: 0, attempted: inputs.length, error: fetched.error };
    }
    let attached = 0;
    for (const input of inputs) {
      if (input.disabled) continue;
      if (attachFileToInput(input, fetched.file)) attached += 1;
    }
    return { attached, attempted: inputs.length, error: null };
  }

  function fillPage(profile, llmMappings = null) {
    const fields = [
      ...document.querySelectorAll(
        "input:not([type=hidden]):not([type=submit]):not([type=button]):not([type=file]), textarea, select"
      ),
    ];
    let filled = 0;
    let attempted = 0;
    let confSum = 0;
    let missingRequired = 0;
    const unmatchedLabels = new Set();

    for (const el of fields) {
      if (el.disabled || el.readOnly) continue;
      const label = labelFor(el);
      if (!label && el.type === "radio") continue; // Usually radio buttons are grouped, rely on wrapper labels if possible

      const required = el.required || el.getAttribute("aria-required") === "true";
      
      // Prevent double counting radio button groups
      if (el.type !== "radio" && el.type !== "checkbox") {
        attempted += 1;
      }

      // Group radio buttons by name to handle them once
      let queryLabel = label;
      if (el.type === "radio" || el.type === "checkbox") {
        // The question label is often on a fieldset or wrapper above the radio buttons
        const fieldset = el.closest("fieldset");
        if (fieldset) {
          const legend = fieldset.querySelector("legend");
          if (legend) queryLabel = legend.textContent;
        } else {
          // If no fieldset, try to find a preceding paragraph or div that acts as the question
          const wrapper = el.closest(".form-group, .question, div");
          if (wrapper && wrapper.textContent.length < 200) {
            queryLabel = wrapper.textContent;
          }
        }
      }

      const query = queryLabel || label;
      const hit = matchProfileField(query, profile);
      
      let answerToSet = null;
      let confToSet = 0;

      if (hit?.value != null && String(hit.value).trim() !== "") {
        answerToSet = hit.value;
        confToSet = hit.conf || 0.5;
      } else if (llmMappings && llmMappings[query]) {
        answerToSet = llmMappings[query];
        confToSet = 0.9;
      } else if (query) {
        unmatchedLabels.add(query);
      }
      
      if (answerToSet != null && String(answerToSet).trim() !== "") {
        if (setNativeValue(el, String(answerToSet))) {
          if (el.type !== "radio" && el.type !== "checkbox") {
             filled += 1;
             confSum += confToSet;
          } else if (el.checked) {
             filled += 1;
             confSum += confToSet;
          }
        }
      } else if (required && el.type !== "radio" && el.type !== "checkbox") {
        missingRequired += 1;
      }
    }

    const confidence =
      attempted === 0 ? 0 : Math.min(0.99, (confSum / Math.max(filled, 1)) * (filled / attempted));
    return { filled, attempted, confidence, missingRequired, unmatchedLabels: Array.from(unmatchedLabels) };
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

    let stats = fillPage(profile);

    if (stats.unmatchedLabels.length > 0) {
      showToast("Asking Career OS AI to map remaining fields...");
      const mapRes = await new Promise((resolve) => {
        chrome.runtime.sendMessage({ type: "MAP_FIELDS", labels: stats.unmatchedLabels }, resolve);
      });
      if (mapRes?.ok && mapRes.mappings) {
        const llmMappings = {};
        for (const m of mapRes.mappings) {
          if (m.answer && m.answer.trim() !== "") {
            llmMappings[m.label] = m.answer;
          }
        }
        if (Object.keys(llmMappings).length > 0) {
          stats = fillPage(profile, llmMappings);
        }
      }
    }

    showToast("Attaching resume file…");
    const resumeUp = await fillResumeUploads(profile);
    if (resumeUp.attached > 0) {
      stats.filled += resumeUp.attached;
      stats.confidence = Math.min(0.99, stats.confidence + 0.05);
    }

    await reportEvent({
      event_type: "filled",
      host,
      url,
      confidence: stats.confidence,
      detail:
        resumeUp.attached > 0
          ? `resume_attached:${resumeUp.attached}`
          : resumeUp.error
            ? `resume_skip:${resumeUp.error}`
            : resumeUp.attempted
              ? "resume_attach_failed"
              : "no_file_input",
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
      const resumeNote =
        resumeUp.attached > 0
          ? ` Resume attached (${resumeUp.attached}).`
          : resumeUp.error
            ? ` Resume not attached: ${resumeUp.error}`
            : resumeUp.attempted
              ? " Resume file input found but attach failed — upload manually."
              : "";
      showToast(`Career OS filled ${stats.filled} field(s).${resumeNote} You click Submit.`);
      return {
        ok: true,
        filled: stats.filled,
        confidence: stats.confidence,
        submitted: false,
        resumeAttached: resumeUp.attached,
      };
    }

    const gate = await reportEvent({
      event_type: "submit_attempt",
      host,
      url,
      confidence: stats.confidence,
    });
    
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
    showToast("Auto Apply: Submit clicked. Confirm on Tracker.");
    return { ok: true, filled: stats.filled, confidence: stats.confidence, submitted: true };
  }

  chrome.runtime.onMessage.addListener((msg, _sender, sendResponse) => {
    if (msg?.type !== "CAREER_OS_FILL") return false;
    runFill({ autoSubmit: !!msg.autoSubmit })
      .then(sendResponse)
      .catch((err) => sendResponse({ ok: false, error: String(err?.message || err) }));
    return true;
  });
}
