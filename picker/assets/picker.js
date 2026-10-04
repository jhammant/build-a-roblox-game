// picker: taps become picks. Saves each board as {picks, note, at} to the first backend that works:
// the Claude artifact database, then the local picker server (picks.json), then this browser only (copy and paste).
(function () {
  "use strict";
  var CONFIG = JSON.parse(document.getElementById("picker-config").textContent);
  var SECTIONS = CONFIG.sections;
  var NOTE_MAX = 300;
  var TEXT_MAX = 60;
  var NOTES = [523.25, 587.33, 659.25, 783.99, 880.0, 1046.5, 1174.66, 1318.51];
  var CONFETTI = ["#FF4D5E", "#FF9F1C", "#FFD447", "#3FD46B", "#33B5FF", "#A877FF", "#FF6FB5", "#FFFFFF"];
  var STORE_KEY = "picker:" + CONFIG.collection;
  var BY_KEY = {};
  SECTIONS.forEach(function (s, i) { s.index = i; BY_KEY[s.key] = s; });

  var state = {}; // section -> picks
  var notes = {}; // section -> note text
  var changedAt = {}; // section -> when this page last changed it (ms)
  var saving = {}; // section -> a save is in flight
  var again = {}; // section -> changed again while saving
  var backend = null; // { kind, save(section, doc) -> Promise }
  var audio = null;
  var soundOn = true;
  var celebrated = false;
  var noteTimers = {};

  function $(sel, el) { return (el || document).querySelector(sel); }
  function $$(sel, el) { return Array.prototype.slice.call((el || document).querySelectorAll(sel)); }
  function sec(s) { return state[s] || (state[s] = {}); }

  function groupDone(picks, g) {
    var v = picks[g.key];
    return g.mode === "many" ? Array.isArray(v) && v.length > 0 : typeof v === "string" && v !== "";
  }
  function sectionDone(s) {
    var picks = state[s.key] || {};
    return s.groups.every(function (g) { return groupDone(picks, g); });
  }
  function tweakValue(s, g, t) {
    var v = (state[s.key] || {})[g.key + "." + t.key];
    return t.choices.indexOf(v) !== -1 ? v : t.default;
  }

  function summaryText() {
    return SECTIONS.map(function (s) {
      var picks = state[s.key] || {};
      var parts = s.groups.map(function (g) {
        var v = picks[g.key];
        var shown;
        if (g.mode === "many") {
          shown = Array.isArray(v) && v.length ? v.map(function (x) { return g.names[x] || x; }).join(", ") : "–";
        } else {
          shown = v ? v + " " + (g.names[v] || "") : "?";
        }
        g.tweaks.forEach(function (t) { shown += " (" + t.label + ": " + tweakValue(s, g, t) + ")"; });
        return g.title + ": " + shown;
      });
      var note = (notes[s.key] || "").trim();
      return s.title.toUpperCase() + "\n" + parts.join(" · ") + (note ? "\nNote: " + note : "");
    }).join("\n\n");
  }

  function render() {
    $$("input[data-s][data-g]").forEach(function (inp) {
      var v = sec(inp.dataset.s)[inp.dataset.g];
      var on = inp.type === "radio" ? v === inp.value : Array.isArray(v) && v.indexOf(inp.value) !== -1;
      inp.checked = on;
      var card = inp.closest("label");
      card.classList.toggle("is-picked", on);
      if (inp.type === "radio") card.classList.toggle("is-other", !!v && !on);
    });
    $$("select[data-t]").forEach(function (sel) {
      var want = sec(sel.dataset.s)[sel.dataset.t] || sel.dataset.default;
      if (document.activeElement !== sel && sel.value !== want) sel.value = want;
    });
    $$("input[data-note]").forEach(function (inp) {
      var want = notes[inp.dataset.s] || "";
      if (document.activeElement !== inp && inp.value !== want) inp.value = want;
    });
    var done = 0;
    SECTIONS.forEach(function (s) {
      var d = sectionDone(s);
      if (d) done++;
      var dot = $('.dot[data-board="' + s.key + '"]');
      if (dot) dot.classList.toggle("done", d);
      var chip = $('.toc-chip[data-toc="' + s.key + '"]');
      if (chip) chip.classList.toggle("done", d);
    });
    $("#count").textContent = done + " of " + SECTIONS.length + " done";
    $("#done").hidden = done < SECTIONS.length;
    $("#summary").textContent = summaryText();
    return done;
  }

  var STATUS = {
    connecting: "Getting ready…",
    artifact: "Your picks save as you tap, and Claude can read them.",
    local: "Your picks save as you tap, straight to the computer running the picker.",
    saving: "Saving…",
    copy: "Picks are kept on this screen only. When you're done, tap “Copy picks” at the bottom and paste them to Claude.",
    error: "That one didn't save. Tap it again, or copy your picks at the bottom and paste them to Claude."
  };
  function setStatus(mode) {
    var el = $("#status");
    el.dataset.mode = mode;
    el.textContent = STATUS[mode];
  }
  function savedStatus() { setStatus(backend ? backend.kind : "copy"); }

  function docFor(s) {
    return { picks: sec(s), note: (notes[s] || "").slice(0, NOTE_MAX), at: changedAt[s] || Date.now() };
  }

  function keepLocally() {
    try { localStorage.setItem(STORE_KEY, JSON.stringify({ state: state, notes: notes })); } catch (e) { /* none */ }
  }

  // One write at a time per board: a change made while saving is sent once the first save finishes
  function save(s, retried) {
    if (!backend) { keepLocally(); return; }
    if (saving[s]) { again[s] = true; return; }
    saving[s] = true;
    setStatus("saving");
    backend.save(s, docFor(s)).then(function () {
      saving[s] = false;
      savedStatus();
      if (again[s]) { again[s] = false; save(s); }
    }, function (e) {
      saving[s] = false;
      var transient = e && (e.code === "unavailable" || e.code === "network");
      if (transient && !retried) {
        setTimeout(function () { save(s, true); }, 600 + Math.random() * 600);
      } else {
        setStatus("error");
        keepLocally();
      }
    });
  }

  function sanitize(picks) {
    var out = {};
    if (!picks || typeof picks !== "object") return out;
    Object.keys(picks).slice(0, 80).forEach(function (k) {
      var v = picks[k];
      if (typeof v === "string") out[k] = v.slice(0, TEXT_MAX);
      else if (Array.isArray(v)) {
        out[k] = v.filter(function (x) { return typeof x === "string"; }).slice(0, 60)
          .map(function (x) { return x.slice(0, TEXT_MAX); });
      }
    });
    return out;
  }

  // Apply saved documents from a backend, unless this page has a newer change of its own for that board
  function applyDocs(entries) {
    entries.forEach(function (entry) {
      var id = entry[0];
      var v = entry[1];
      if (!v || !BY_KEY[id] || saving[id] || again[id]) return;
      if (changedAt[id] && typeof v.at === "number" && v.at < changedAt[id]) return;
      state[id] = sanitize(v.picks);
      var typing = document.activeElement && document.activeElement.id === "note-" + id;
      if (!typing && typeof v.note === "string") notes[id] = v.note.slice(0, NOTE_MAX);
    });
    if (render() === SECTIONS.length) celebrated = true;
  }

  function play(freq, delay) {
    if (!soundOn) return;
    try {
      audio = audio || new (window.AudioContext || window.webkitAudioContext)();
      var t = audio.currentTime + (delay || 0);
      [[1, "triangle", 0.22, 0.6], [4, "sine", 0.05, 0.15]].forEach(function (p) {
        var osc = audio.createOscillator();
        var gain = audio.createGain();
        osc.type = p[1];
        osc.frequency.value = freq * p[0];
        gain.gain.setValueAtTime(p[2], t);
        gain.gain.exponentialRampToValueAtTime(0.0001, t + p[3]);
        osc.connect(gain);
        gain.connect(audio.destination);
        osc.start(t);
        osc.stop(t + p[3] + 0.05);
      });
    } catch (e) { /* no sound on this device */ }
  }

  function celebrate() {
    NOTES.forEach(function (f, i) { play(f, i * 0.09); });
    if (window.matchMedia && window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    var box = $("#confetti");
    for (var i = 0; i < 90; i++) {
      var bit = document.createElement("span");
      bit.className = "bit";
      bit.style.left = (Math.random() * 100) + "%";
      bit.style.background = CONFETTI[i % CONFETTI.length];
      bit.style.animationDelay = (Math.random() * 0.6) + "s";
      bit.style.animationDuration = (1.6 + Math.random() * 1.4) + "s";
      box.appendChild(bit);
    }
    setTimeout(function () { box.replaceChildren(); }, 3800);
  }

  document.addEventListener("change", function (e) {
    var t = e.target;
    if (!t.dataset || !t.dataset.s || t.dataset.note) return;
    var s = t.dataset.s;
    var picks = sec(s);
    if (t.tagName === "SELECT" && t.dataset.t) {
      picks[t.dataset.t] = t.value;
    } else if (t.type === "radio") {
      picks[t.dataset.g] = t.value;
    } else if (t.type === "checkbox") {
      var list = (Array.isArray(picks[t.dataset.g]) ? picks[t.dataset.g] : []).filter(function (v) { return v !== t.value; });
      if (t.checked) list.push(t.value);
      picks[t.dataset.g] = list;
    } else {
      return;
    }
    changedAt[s] = Date.now();
    play(NOTES[BY_KEY[s].index % NOTES.length] * (t.type === "checkbox" ? 1.5 : 1));
    var done = render();
    save(s);
    if (done === SECTIONS.length && !celebrated) {
      celebrated = true;
      celebrate();
    }
  });

  document.addEventListener("input", function (e) {
    var t = e.target;
    if (!t.dataset || !t.dataset.note) return;
    var s = t.dataset.s;
    notes[s] = t.value;
    changedAt[s] = Date.now();
    $("#summary").textContent = summaryText();
    clearTimeout(noteTimers[s]);
    noteTimers[s] = setTimeout(function () { save(s); }, 700);
  });

  $("#sound").addEventListener("click", function (e) {
    soundOn = !soundOn;
    e.currentTarget.setAttribute("aria-pressed", String(soundOn));
    e.currentTarget.textContent = soundOn ? "Sound on" : "Sound off";
  });

  function selectSummary() {
    var range = document.createRange();
    range.selectNodeContents($("#summary"));
    var sel = window.getSelection();
    sel.removeAllRanges();
    sel.addRange(range);
  }
  $("#copy").addEventListener("click", function () {
    var btn = $("#copy");
    function copied() {
      btn.textContent = "Copied";
      setTimeout(function () { btn.textContent = "Copy picks"; }, 1600);
    }
    try {
      navigator.clipboard.writeText(summaryText()).then(copied, selectSummary);
    } catch (err) {
      selectSummary();
    }
  });

  // Backends --------------------------------------------------------------------------------------------------

  function startArtifact() {
    var host = window.claude;
    if (!host || typeof host.use !== "function") return Promise.resolve(false);
    return host.use("db").then(function (db) {
      if (!db) return false;
      backend = {
        kind: "artifact",
        save: function (s, doc) { return db.doc(CONFIG.collection + "/" + s).set(doc); }
      };
      db.collection(CONFIG.collection).onSnapshot(function (snap) {
        applyDocs(snap.docs.map(function (d) { return [d.id, d.data()]; }));
      }, function () {
        backend = null;
        setStatus("copy");
      });
      return true;
    }, function () { return false; });
  }

  function fetchDocs() {
    return fetch("api/picks", { cache: "no-store" }).then(function (r) {
      if (!r.ok) throw new Error("status " + r.status);
      return r.json();
    }).then(function (body) {
      if (!body || typeof body.docs !== "object") throw new Error("not a picker server");
      return body.docs;
    });
  }

  function startLocal() {
    if (!/^https?:$/.test(location.protocol)) return Promise.resolve(false);
    return fetchDocs().then(function (docs) {
      backend = {
        kind: "local",
        save: function (s, doc) {
          return fetch("api/picks/" + encodeURIComponent(s), {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(doc)
          }).then(function (r) {
            if (!r.ok) throw { code: r.status >= 500 ? "unavailable" : "rejected" };
          }, function () { throw { code: "network" }; });
        }
      };
      applyDocs(Object.keys(docs).map(function (k) { return [k, docs[k]]; }));
      // Poll so a second screen (the parent's laptop, the kid's tablet) sees the other's taps
      setInterval(function () {
        if (document.hidden) return;
        fetchDocs().then(function (d) {
          applyDocs(Object.keys(d).map(function (k) { return [k, d[k]]; }));
        }, function () { /* the server will be back */ });
      }, 2500);
      return true;
    }, function () { return false; });
  }

  function startCopy() {
    try {
      var kept = JSON.parse(localStorage.getItem(STORE_KEY) || "null");
      if (kept && kept.state) {
        Object.keys(kept.state).forEach(function (k) { if (BY_KEY[k]) state[k] = sanitize(kept.state[k]); });
        Object.keys(kept.notes || {}).forEach(function (k) {
          if (BY_KEY[k] && typeof kept.notes[k] === "string") notes[k] = kept.notes[k].slice(0, NOTE_MAX);
        });
      }
    } catch (e) { /* nothing kept */ }
    setStatus("copy");
    if (render() === SECTIONS.length) celebrated = true;
  }

  render();
  startArtifact().then(function (ok) { return ok || startLocal(); }).then(function (ok) {
    if (!ok) { startCopy(); return; }
    savedStatus();
    // Taps made while the page was still connecting
    Object.keys(changedAt).forEach(function (s) { save(s); });
  });
})();
