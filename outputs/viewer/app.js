const runSelect = document.getElementById("run-select");
const statusEl = document.getElementById("status");
const bookMetaEl = document.getElementById("book-meta");
const pageViewEl = document.getElementById("page-view");

const bookTitleEl = document.getElementById("book-title");
const bookSubtitleEl = document.getElementById("book-subtitle");
const bookLangEl = document.getElementById("book-lang");

const prevBtn = document.getElementById("prev-btn");
const nextBtn = document.getElementById("next-btn");
const pageIndicatorEl = document.getElementById("page-indicator");
const pageTitleEl = document.getElementById("page-title");
const textPrimaryEl = document.getElementById("text-primary");
const textSecondaryEl = document.getElementById("text-secondary");
const audioPrimaryWrap = document.getElementById("audio-primary-wrap");
const audioSecondaryWrap = document.getElementById("audio-secondary-wrap");

const state = {
  runs: [],
  book: null,
  pageIndex: 0,
};

function setStatus(message) {
  statusEl.textContent = message || "";
}

function hideBook() {
  bookMetaEl.classList.add("hidden");
  pageViewEl.classList.add("hidden");
}

function showBook() {
  bookMetaEl.classList.remove("hidden");
  pageViewEl.classList.remove("hidden");
}

function renderAudio(target, url) {
  target.innerHTML = "";
  if (!url) {
    const noAudio = document.createElement("p");
    noAudio.className = "missing-audio";
    noAudio.textContent = "오디오 없음";
    target.appendChild(noAudio);
    return;
  }

  const audio = document.createElement("audio");
  audio.controls = true;
  audio.preload = "none";
  audio.src = url;
  target.appendChild(audio);
}

function renderPage() {
  if (!state.book || !state.book.pages || state.book.pages.length === 0) {
    hideBook();
    return;
  }

  const pages = state.book.pages;
  const page = pages[state.pageIndex];
  const total = pages.length;

  bookTitleEl.textContent = state.book.meta.title_primary || "(제목 없음)";
  bookSubtitleEl.textContent = state.book.meta.title_secondary || "";
  bookLangEl.textContent = `${state.book.meta.primary_language || "-"} / ${
    state.book.meta.secondary_language || "-"
  }`;

  pageIndicatorEl.textContent = `${state.pageIndex + 1} / ${total}`;
  pageTitleEl.textContent = `Page ${page.page_number}`;
  textPrimaryEl.textContent = page.text_primary || "";
  textSecondaryEl.textContent = page.text_secondary || "";
  renderAudio(audioPrimaryWrap, page.audio_primary_url);
  renderAudio(audioSecondaryWrap, page.audio_secondary_url);

  prevBtn.disabled = state.pageIndex === 0;
  nextBtn.disabled = state.pageIndex >= total - 1;
  showBook();
}

async function loadBook(runId) {
  setStatus("불러오는 중...");
  hideBook();

  try {
    const response = await fetch(`/api/book?run=${encodeURIComponent(runId)}`);
    if (!response.ok) {
      const errorPayload = await response.json().catch(() => ({}));
      throw new Error(errorPayload.error || `HTTP ${response.status}`);
    }

    state.book = await response.json();
    state.pageIndex = 0;
    setStatus("");

    if (!state.book.pages || state.book.pages.length === 0) {
      setStatus("페이지 데이터가 없습니다.");
      hideBook();
      return;
    }

    renderPage();
  } catch (error) {
    console.error("Failed to load book", error);
    setStatus(`불러오기 실패: ${error.message}`);
    hideBook();
  }
}

function fillRunOptions(runs) {
  runSelect.innerHTML = "";

  runs.forEach((run) => {
    const option = document.createElement("option");
    option.value = run.id;
    const title = run.title_primary || run.id;
    option.textContent = `${run.id} | ${title} (${run.page_count}p)`;
    runSelect.appendChild(option);
  });
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
      setStatus("표시할 스토리 결과가 없습니다.");
      runSelect.innerHTML = "";
      return;
    }

    fillRunOptions(state.runs);
    runSelect.value = state.runs[0].id;
    setStatus("");
    await loadBook(state.runs[0].id);
  } catch (error) {
    console.error("Failed to load runs", error);
    setStatus(`목록 로딩 실패: ${error.message}`);
    hideBook();
  }
}

runSelect.addEventListener("change", (event) => {
  const runId = event.target.value;
  if (!runId) {
    return;
  }
  loadBook(runId);
});

prevBtn.addEventListener("click", () => {
  if (!state.book || state.pageIndex <= 0) {
    return;
  }
  state.pageIndex -= 1;
  renderPage();
});

nextBtn.addEventListener("click", () => {
  if (!state.book || state.pageIndex >= state.book.pages.length - 1) {
    return;
  }
  state.pageIndex += 1;
  renderPage();
});

loadRuns();
