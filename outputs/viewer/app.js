const runSelectEl = document.getElementById("run-select");
const runPickerEl = document.querySelector(".run-picker");
const statusEl = document.getElementById("status");
const pageViewEl = document.getElementById("page-view");
const pageCardEl = document.getElementById("page-card");

const bookTitleEl = document.getElementById("book-title");
const bookSubtitleEl = document.getElementById("book-subtitle");

const modePrimaryEl = document.getElementById("mode-primary");
const modeSecondaryEl = document.getElementById("mode-secondary");
const modeBothEl = document.getElementById("mode-both");
const modePrimaryLabelEl = document.getElementById("mode-primary-label");
const modeSecondaryLabelEl = document.getElementById("mode-secondary-label");

const soundToggleEl = document.getElementById("sound-toggle");
const playBtnEl = document.getElementById("play-btn");
const playPrimaryBtnEl = document.getElementById("play-primary-btn");
const playSecondaryBtnEl = document.getElementById("play-secondary-btn");
const speechAudioEl = document.getElementById("speech-audio");

const pageBadgeEl = document.getElementById("page-badge");
const illustrationWrapEl = document.getElementById("illustration-wrap");
const activeLanguagePillEl = document.getElementById("active-language-pill");
const storyTextEl = document.getElementById("story-text");

const prevBtnEl = document.getElementById("prev-btn");
const nextBtnEl = document.getElementById("next-btn");
const pageDotsEl = document.getElementById("page-dots");
const pageIndicatorEl = document.getElementById("page-indicator");

const PAGE_TURN_MS = 360;
const MAX_VISIBLE_DOTS = 9;

const state = {
  runs: [],
  book: null,
  pageIndex: 0,
  isTurning: false,
  textMode: "secondary",
  soundEnabled: true,
};

function normalizeAspectRatio(value, fallback = "1 / 1") {
  const normalized = String(value || "").trim();
  const match = normalized.match(/^(\d+(?:\.\d+)?)\s*:\s*(\d+(?:\.\d+)?)$/);
  if (!match) {
    return fallback;
  }
  return `${match[1]} / ${match[2]}`;
}

function setStatus(message) {
  statusEl.textContent = message || "";
}

function hideBook() {
  pageViewEl.classList.add("hidden");
}

function showBook() {
  pageViewEl.classList.remove("hidden");
}

function getBookLanguages() {
  const primary = state.book?.meta?.primary_language || "한국어";
  const secondary = state.book?.meta?.secondary_language || "English";
  return { primary, secondary };
}

function getCurrentPage() {
  if (!state.book?.pages?.length) {
    return null;
  }
  return state.book.pages[state.pageIndex] || null;
}

function pauseAudio() {
  speechAudioEl.pause();
  speechAudioEl.currentTime = 0;
}

function updateSoundToggle() {
  soundToggleEl.textContent = state.soundEnabled ? "소리 켬" : "소리 끔";
  soundToggleEl.classList.toggle("is-muted", !state.soundEnabled);
}

function updateModeButtons() {
  const isPrimary = state.textMode === "primary";
  const isSecondary = state.textMode === "secondary";
  const isBoth = state.textMode === "both";

  modePrimaryEl.classList.toggle("active", isPrimary);
  modeSecondaryEl.classList.toggle("active", isSecondary);
  modeBothEl.classList.toggle("active", isBoth);

  modePrimaryEl.setAttribute("aria-selected", String(isPrimary));
  modeSecondaryEl.setAttribute("aria-selected", String(isSecondary));
  modeBothEl.setAttribute("aria-selected", String(isBoth));
}

function getActiveAudioUrl(page) {
  if (!page) {
    return null;
  }

  if (state.textMode === "primary") {
    return page.audio_primary_url || null;
  }

  if (state.textMode === "secondary") {
    return page.audio_secondary_url || null;
  }

  return page.audio_secondary_url || page.audio_primary_url || null;
}

function getAudioUrls(page) {
  return {
    primary: page?.audio_primary_url || null,
    secondary: page?.audio_secondary_url || null,
  };
}

function updatePlayControls(page) {
  if (!playPrimaryBtnEl || !playSecondaryBtnEl || !playBtnEl) {
    return;
  }

  const isBothMode = state.textMode === "both";
  const { primary, secondary } = getBookLanguages();
  const audioUrls = getAudioUrls(page);

  playBtnEl.classList.toggle("hidden", isBothMode);
  playPrimaryBtnEl.classList.toggle("hidden", !isBothMode);
  playSecondaryBtnEl.classList.toggle("hidden", !isBothMode);

  if (!isBothMode) {
    return;
  }

  playPrimaryBtnEl.textContent = `${primary} ▶`;
  playSecondaryBtnEl.textContent = `${secondary} ▶`;

  playPrimaryBtnEl.disabled = !state.soundEnabled || !audioUrls.primary;
  playSecondaryBtnEl.disabled = !state.soundEnabled || !audioUrls.secondary;
}

function setNavState() {
  const hasBook = Boolean(state.book?.pages?.length);
  const total = hasBook ? state.book.pages.length : 0;

  prevBtnEl.disabled = !hasBook || state.isTurning || state.pageIndex <= 0;
  nextBtnEl.disabled = !hasBook || state.isTurning || state.pageIndex >= total - 1;

  const page = getCurrentPage();
  const hasAudio = Boolean(getActiveAudioUrl(page));
  playBtnEl.disabled = !hasBook || !hasAudio || !state.soundEnabled;
  updatePlayControls(page);
}

function renderIllustration(url) {
  illustrationWrapEl.innerHTML = "";

  if (!url) {
    const noIllustration = document.createElement("p");
    noIllustration.className = "missing-illustration";
    noIllustration.textContent = "일러스트 없음";
    illustrationWrapEl.appendChild(noIllustration);
    return;
  }

  const link = document.createElement("a");
  link.className = "illustration-link";
  link.href = url;
  link.target = "_blank";
  link.rel = "noopener noreferrer";

  const image = document.createElement("img");
  image.className = "illustration-image";
  image.src = url;
  image.alt = "동화 페이지 일러스트";
  image.loading = "lazy";

  link.appendChild(image);
  illustrationWrapEl.appendChild(link);
}

function applyIllustrationAspectRatio() {
  const aspectRatio = state.book?.assets?.illustrations?.aspect_ratio || "1:1";
  illustrationWrapEl.style.aspectRatio = normalizeAspectRatio(aspectRatio);
}

function renderStoryText(page) {
  storyTextEl.innerHTML = "";
  const { primary, secondary } = getBookLanguages();

  if (state.textMode === "both") {
    activeLanguagePillEl.textContent = `${primary} / ${secondary}`;

    const blocks = [
      { label: primary, text: page?.text_primary || "" },
      { label: secondary, text: page?.text_secondary || "" },
    ];

    let anyText = false;
    blocks.forEach((entry) => {
      if (!entry.text) {
        return;
      }
      anyText = true;

      const block = document.createElement("section");
      block.className = "bilingual-block";

      const label = document.createElement("p");
      label.className = "bilingual-label";
      label.textContent = entry.label;

      const paragraph = document.createElement("p");
      paragraph.className = "story-paragraph";
      paragraph.textContent = entry.text;

      block.appendChild(label);
      block.appendChild(paragraph);
      storyTextEl.appendChild(block);
    });

    if (!anyText) {
      const fallback = document.createElement("p");
      fallback.className = "story-paragraph";
      fallback.textContent = "본문이 없습니다.";
      storyTextEl.appendChild(fallback);
    }

    return;
  }

  if (state.textMode === "primary") {
    activeLanguagePillEl.textContent = primary;
  } else {
    activeLanguagePillEl.textContent = secondary;
  }

  const paragraph = document.createElement("p");
  paragraph.className = "story-paragraph";
  paragraph.textContent =
    state.textMode === "primary"
      ? page?.text_primary || "본문이 없습니다."
      : page?.text_secondary || "본문이 없습니다.";

  storyTextEl.appendChild(paragraph);
}

function buildVisibleDotIndices(total, currentIndex) {
  if (total <= MAX_VISIBLE_DOTS) {
    return Array.from({ length: total }, (_, idx) => idx);
  }

  let start = Math.max(0, currentIndex - Math.floor(MAX_VISIBLE_DOTS / 2));
  let end = Math.min(total, start + MAX_VISIBLE_DOTS);
  start = Math.max(0, end - MAX_VISIBLE_DOTS);

  const indices = [];
  for (let index = start; index < end; index += 1) {
    indices.push(index);
  }
  return indices;
}

function renderPageDots() {
  pageDotsEl.innerHTML = "";

  const total = state.book?.pages?.length || 0;
  if (total <= 0) {
    return;
  }

  const dotIndices = buildVisibleDotIndices(total, state.pageIndex);

  dotIndices.forEach((index) => {
    const dot = document.createElement("button");
    dot.type = "button";
    dot.className = "page-dot";
    dot.textContent = String(index + 1);
    dot.classList.toggle("active", index === state.pageIndex);
    dot.setAttribute("aria-label", `${index + 1} 페이지로 이동`);
    dot.disabled = index === state.pageIndex;
    dot.addEventListener("click", () => moveToPage(index));
    pageDotsEl.appendChild(dot);
  });
}

function animatePageTurn(direction) {
  if (!direction) {
    return;
  }

  const className = direction === "next" ? "turn-next" : "turn-prev";
  pageCardEl.classList.remove("turn-next", "turn-prev");
  void pageCardEl.offsetWidth;
  pageCardEl.classList.add(className);

  state.isTurning = true;
  setNavState();

  window.setTimeout(() => {
    state.isTurning = false;
    pageCardEl.classList.remove(className);
    setNavState();
  }, PAGE_TURN_MS);
}

function renderHeader() {
  const title = state.book?.meta?.title_primary || "(제목 없음)";
  const subtitle = state.book?.meta?.title_secondary || "";

  const titleTextEl = bookTitleEl.querySelector("span");
  if (titleTextEl) {
    titleTextEl.textContent = title;
  }
  bookSubtitleEl.textContent = subtitle;

  const { primary, secondary } = getBookLanguages();
  modePrimaryLabelEl.textContent = primary;
  modeSecondaryLabelEl.textContent = secondary;
}

function renderPage(direction = null) {
  if (!state.book?.pages?.length) {
    hideBook();
    return;
  }

  const page = getCurrentPage();
  if (!page) {
    hideBook();
    return;
  }

  renderHeader();

  pageBadgeEl.textContent = String(page.page_number || state.pageIndex + 1);
  applyIllustrationAspectRatio();
  renderIllustration(page.illustration_url);
  renderStoryText(page);
  renderPageDots();

  const total = state.book.pages.length;
  pageIndicatorEl.textContent = `${state.pageIndex + 1} / ${total}`;

  updateModeButtons();
  updateSoundToggle();
  setNavState();
  showBook();
  animatePageTurn(direction);
}

function moveToPage(nextIndex) {
  if (!state.book?.pages?.length || state.isTurning) {
    return;
  }

  if (nextIndex < 0 || nextIndex >= state.book.pages.length) {
    return;
  }

  if (nextIndex === state.pageIndex) {
    return;
  }

  pauseAudio();

  const direction = nextIndex > state.pageIndex ? "next" : "prev";
  state.pageIndex = nextIndex;
  renderPage(direction);
}

async function playCurrentAudio(preferredMode = null) {
  if (!state.soundEnabled) {
    return;
  }

  const page = getCurrentPage();
  let audioUrl = getActiveAudioUrl(page);

  if (preferredMode === "primary") {
    audioUrl = page?.audio_primary_url || null;
  } else if (preferredMode === "secondary") {
    audioUrl = page?.audio_secondary_url || null;
  }

  if (!audioUrl) {
    setStatus("현재 언어에 재생할 오디오가 없습니다.");
    return;
  }

  try {
    speechAudioEl.src = audioUrl;
    speechAudioEl.currentTime = 0;
    await speechAudioEl.play();
    setStatus("");
  } catch (error) {
    console.error("Audio playback failed", error);
    setStatus(`오디오 재생 실패: ${error.message}`);
  }
}

function pickInitialTextMode() {
  const firstPage = state.book?.pages?.[0];
  if (!firstPage) {
    return "secondary";
  }

  if (firstPage.text_secondary) {
    return "secondary";
  }

  if (firstPage.text_primary) {
    return "primary";
  }

  return "both";
}

async function loadBook(runId) {
  setStatus("불러오는 중...");
  hideBook();
  pauseAudio();

  try {
    const response = await fetch(`/api/book?run=${encodeURIComponent(runId)}`);
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.error || `HTTP ${response.status}`);
    }

    state.book = await response.json();
    state.pageIndex = 0;
    state.isTurning = false;
    state.textMode = pickInitialTextMode();

    if (!state.book.pages?.length) {
      setStatus("페이지 데이터가 없습니다.");
      hideBook();
      return;
    }

    setStatus("");
    renderPage();
  } catch (error) {
    console.error("Failed to load book", error);
    setStatus(`불러오기 실패: ${error.message}`);
    hideBook();
  }
}

function fillRunOptions(runs) {
  runSelectEl.innerHTML = "";

  runs.forEach((run) => {
    const option = document.createElement("option");
    option.value = run.id;

    const title = run.title_primary || run.id;
    option.textContent = `${title} (${run.page_count}p)`;
    runSelectEl.appendChild(option);
  });

  if (runPickerEl) {
    runPickerEl.classList.toggle("is-visible", runs.length > 1);
  }
}

async function loadRuns() {
  setStatus("실행 결과 목록 불러오는 중...");
  hideBook();

  try {
    const response = await fetch("/api/runs");
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }

    const payload = await response.json();
    state.runs = payload.runs || [];

    if (state.runs.length === 0) {
      runSelectEl.innerHTML = "";
      setStatus("표시할 스토리 결과가 없습니다.");
      return;
    }

    fillRunOptions(state.runs);
    runSelectEl.value = state.runs[0].id;
    setStatus("");

    await loadBook(state.runs[0].id);
  } catch (error) {
    console.error("Failed to load runs", error);
    setStatus(`목록 로딩 실패: ${error.message}`);
    hideBook();
  }
}

runSelectEl.addEventListener("change", (event) => {
  const runId = event.target.value;
  if (!runId) {
    return;
  }
  loadBook(runId);
});

modePrimaryEl.addEventListener("click", () => {
  if (state.textMode === "primary") {
    return;
  }
  state.textMode = "primary";
  pauseAudio();
  renderPage();
});

modeSecondaryEl.addEventListener("click", () => {
  if (state.textMode === "secondary") {
    return;
  }
  state.textMode = "secondary";
  pauseAudio();
  renderPage();
});

modeBothEl.addEventListener("click", () => {
  if (state.textMode === "both") {
    return;
  }
  state.textMode = "both";
  pauseAudio();
  renderPage();
});

soundToggleEl.addEventListener("click", () => {
  state.soundEnabled = !state.soundEnabled;
  if (!state.soundEnabled) {
    pauseAudio();
  }
  updateSoundToggle();
  setNavState();
});

if (playBtnEl) {
  playBtnEl.addEventListener("click", () => {
    playCurrentAudio();
  });
}

if (playPrimaryBtnEl) {
  playPrimaryBtnEl.addEventListener("click", () => {
    playCurrentAudio("primary");
  });
}

if (playSecondaryBtnEl) {
  playSecondaryBtnEl.addEventListener("click", () => {
    playCurrentAudio("secondary");
  });
}

prevBtnEl.addEventListener("click", () => {
  moveToPage(state.pageIndex - 1);
});

nextBtnEl.addEventListener("click", () => {
  moveToPage(state.pageIndex + 1);
});

document.addEventListener("keydown", (event) => {
  if (!state.book || pageViewEl.classList.contains("hidden")) {
    return;
  }

  if (event.altKey || event.ctrlKey || event.metaKey || event.shiftKey) {
    return;
  }

  const activeTag = document.activeElement?.tagName?.toLowerCase();
  if (activeTag === "input" || activeTag === "textarea" || activeTag === "select") {
    return;
  }

  if (event.key === "ArrowLeft") {
    event.preventDefault();
    moveToPage(state.pageIndex - 1);
  }

  if (event.key === "ArrowRight") {
    event.preventDefault();
    moveToPage(state.pageIndex + 1);
  }

  if (event.key === " ") {
    event.preventDefault();
    playCurrentAudio();
  }
});

updateSoundToggle();
updateModeButtons();
loadRuns();
