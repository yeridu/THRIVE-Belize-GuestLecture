/* ============================================================
   THRIVE-Belize Deck Engine v2
   ============================================================ */
(function () {
  "use strict";

  var slides = [];
  var currentIndex = 0;
  var notesVisible = false;
  var timerInterval = null;
  var timerSeconds = 0;
  var timerRunning = false;
  var timerStepIndex = 0;

  var ACTIVITY_STEPS = [
    { label: "Pick one THRIVE module + one evidence principle. Write a one-sentence workshop goal.", duration: 180 },
    { label: "Plan your hardest moment. A participant says something harmful. Write what you'd say and do.", duration: 180 },
    { label: "Pair up. Pitch your workshop in 60 seconds. Your partner gives you one challenge.", duration: 120 },
    { label: "Whole class: share the toughest challenge you received.", duration: 120 }
  ];

  function init() {
    slides = Array.prototype.slice.call(document.querySelectorAll(".slide"));
    if (!slides.length) return;
    hydrateVideos();
    setupNavigation();
    setupKeyboard();
    setupTimer();
    goToSlide(0);
  }

  function hydrateVideos() {
    var dataEl = document.getElementById("deck-data");
    if (!dataEl) return;
    var data;
    try { data = JSON.parse(dataEl.textContent); } catch (e) { return; }
    if (!data || !data.videos) return;

    ["v1", "v2", "v3"].forEach(function (key) {
      var rec = data.videos[key] || {};
      var fileEl = document.getElementById(key + "-file");
      var durEl = document.getElementById(key + "-dur");
      if (fileEl) fileEl.textContent = rec.filename || "Not detected";
      if (durEl) durEl.textContent = rec.duration || "Play to see";

      var player = document.querySelector('video[data-video="' + key + '"]');
      if (!player) return;

      // Try local file first, fall back to GitHub release
      if (rec.filename) {
        player.src = rec.filename;
        player.onerror = function () {
          if (rec.remote) {
            player.src = rec.remote;
            if (fileEl) fileEl.textContent = "Streaming from GitHub";
          }
        };
      } else if (rec.remote) {
        player.src = rec.remote;
        if (fileEl) fileEl.textContent = "Streaming from GitHub";
      }
    });
  }

  function goToSlide(index) {
    if (index < 0 || index >= slides.length) return;
    slides[currentIndex].classList.remove("active");
    currentIndex = index;
    slides[currentIndex].classList.add("active");
    updateProgress();
    updateCounter();
    updateNotes();
    updateMusic();
  }

  function nextSlide() { goToSlide(Math.min(slides.length - 1, currentIndex + 1)); }
  function prevSlide() { goToSlide(Math.max(0, currentIndex - 1)); }

  function updateProgress() {
    var fill = document.getElementById("progress-fill");
    if (!fill) return;
    fill.style.width = (slides.length > 1 ? (currentIndex / (slides.length - 1)) * 100 : 100) + "%";
  }

  function updateCounter() {
    var el = document.getElementById("slide-counter");
    if (el) el.textContent = (currentIndex + 1) + " / " + slides.length;
    var prev = document.getElementById("prev-btn");
    var next = document.getElementById("next-btn");
    if (prev) prev.disabled = currentIndex === 0;
    if (next) next.disabled = currentIndex === slides.length - 1;
  }

  function setupNavigation() {
    var prev = document.getElementById("prev-btn");
    var next = document.getElementById("next-btn");
    if (prev) prev.addEventListener("click", prevSlide);
    if (next) next.addEventListener("click", nextSlide);
  }

  function setupKeyboard() {
    document.addEventListener("keydown", function (e) {
      var tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea") return;
      switch (e.key) {
        case "ArrowRight": case "PageDown":
          e.preventDefault(); nextSlide(); break;
        case " ":
          if (tag !== "video" && tag !== "button") { e.preventDefault(); nextSlide(); }
          break;
        case "ArrowLeft": case "PageUp":
          e.preventDefault(); prevSlide(); break;
        case "Home": e.preventDefault(); goToSlide(0); break;
        case "End":  e.preventDefault(); goToSlide(slides.length - 1); break;
        case "s": case "S": toggleNotes(); break;
        case "f": case "F": toggleFullscreen(); break;
      }
    });
  }

  function updateNotes() {
    var panel = document.getElementById("notes-content");
    if (!panel) return;
    var slide = slides[currentIndex];
    var note = slide ? slide.querySelector(".speaker-note") : null;
    panel.textContent = note ? note.textContent : "";
  }

  function toggleNotes() {
    var panel = document.getElementById("notes-panel");
    if (!panel) return;
    notesVisible = !notesVisible;
    panel.classList.toggle("visible", notesVisible);
  }

  function toggleFullscreen() {
    if (!document.fullscreenElement) {
      document.documentElement.requestFullscreen().catch(function () {});
    } else {
      document.exitFullscreen().catch(function () {});
    }
  }

  // --- Music (Spotify on last 3 slides) ---
  var musicActive = false;

  function updateMusic() {
    var player = document.getElementById("music-player");
    if (!player) return;
    // Last 3 slides: indices (slides.length - 3) through (slides.length - 1)
    var musicStart = slides.length - 3;
    var shouldShow = currentIndex >= musicStart;

    if (shouldShow && !musicActive) {
      player.classList.add("visible");
      musicActive = true;
    } else if (!shouldShow && musicActive) {
      player.classList.remove("visible");
      musicActive = false;
    }
  }

  // --- Timer ---
  function setupTimer() {
    var btn = document.getElementById("timer-btn");
    var resetBtn = document.getElementById("timer-reset");
    if (!btn) return;
    btn.addEventListener("click", function () {
      timerRunning ? pauseTimer() : startTimer();
    });
    if (resetBtn) resetBtn.addEventListener("click", resetTimer);
    timerStepIndex = 0;
    timerSeconds = ACTIVITY_STEPS[0].duration;
    renderTimer();
  }

  function startTimer() {
    timerRunning = true;
    var btn = document.getElementById("timer-btn");
    if (btn) { btn.textContent = "Pause"; btn.className = "timer-btn timer-btn--pause"; }
    timerInterval = setInterval(function () {
      timerSeconds--;
      if (timerSeconds <= 0) {
        timerStepIndex++;
        if (timerStepIndex < ACTIVITY_STEPS.length) {
          timerSeconds = ACTIVITY_STEPS[timerStepIndex].duration;
        } else {
          clearInterval(timerInterval);
          timerRunning = false;
          timerSeconds = 0;
          if (btn) { btn.textContent = "Done"; btn.disabled = true; }
        }
      }
      renderTimer();
    }, 1000);
  }

  function pauseTimer() {
    timerRunning = false;
    clearInterval(timerInterval);
    var btn = document.getElementById("timer-btn");
    if (btn) { btn.textContent = "Resume"; btn.className = "timer-btn timer-btn--start"; }
  }

  function resetTimer() {
    clearInterval(timerInterval);
    timerRunning = false;
    timerStepIndex = 0;
    timerSeconds = ACTIVITY_STEPS[0].duration;
    var btn = document.getElementById("timer-btn");
    if (btn) { btn.textContent = "Start"; btn.className = "timer-btn timer-btn--start"; btn.disabled = false; }
    renderTimer();
  }

  function renderTimer() {
    var display = document.getElementById("timer-display");
    var stepEl = document.getElementById("timer-step-name");
    if (!display) return;
    var m = Math.floor(timerSeconds / 60);
    var s = timerSeconds % 60;
    display.textContent = (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;
    display.className = "timer-display";
    if (timerSeconds <= 10 && timerSeconds > 0) display.className += " danger";
    else if (timerSeconds <= 30) display.className += " warning";
    if (stepEl && timerStepIndex < ACTIVITY_STEPS.length) {
      stepEl.textContent = "Step " + (timerStepIndex + 1) + ": " + ACTIVITY_STEPS[timerStepIndex].label;
    } else if (stepEl) {
      stepEl.textContent = "Activity complete.";
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
