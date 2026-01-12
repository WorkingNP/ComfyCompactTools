const $ = (sel) => document.querySelector(sel);

const state = {
  config: null,
  jobs: new Map(), // job_id -> job
  assets: new Map(), // asset_id -> asset
  ws: null,
  renderScheduled: false,
  selectedAssetId: null,
  grokMessages: [], // {role: 'user'|'assistant'|'system', content: string, ts: iso}
  grokErrors: [], // {message: string, ts: iso}
  comfyErrors: [], // {message: string, ts: iso}
  jobErrorSeen: new Set(),
  modalZoom: 1,
  modalFitZoom: 1,
};

const GROK_HISTORY_TOGGLE_KEY = 'grokSendFullHistory';
const GROK_MODEL_KEY = 'grokModel';

function setPill(el, text, kind) {
  el.textContent = text;
  el.classList.remove('pill--warn', 'pill--good', 'pill--bad');
  el.classList.add(kind);
}

function sortByCreatedDesc(a, b) {
  // ISO timestamps sort lexicographically for UTC-ish strings
  return (b.created_at || '').localeCompare(a.created_at || '');
}

function scheduleRender() {
  if (state.renderScheduled) return;
  state.renderScheduled = true;
  requestAnimationFrame(() => {
    state.renderScheduled = false;
    renderQueue();
    renderGallery();
    updateStatusCounts();
  });
}

async function apiGet(path) {
  const r = await fetch(path);
  if (!r.ok) throw new Error(`${path} -> ${r.status}`);
  return await r.json();
}

async function apiPost(path, body) {
  const r = await fetch(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!r.ok) {
    let msg = `${path} -> ${r.status}`;
    try {
      const j = await r.json();
      if (j?.detail) msg += `: ${JSON.stringify(j.detail)}`;
    } catch {}
    throw new Error(msg);
  }
  return await r.json();
}

function readParamsFromUI() {
  return {
    prompt: $('#quickPrompt').value,
    negative_prompt: $('#neg').value,
    checkpoint: $('#checkpoint').value || null,
    sampler_name: $('#sampler').value,
    scheduler: $('#scheduler').value,
    steps: Number($('#steps').value || 20),
    cfg: Number($('#cfg').value || 7),
    seed: Number($('#seed').value || -1),
    width: Number($('#width').value || 512),
    height: Number($('#height').value || 512),
    batch_size: Number($('#batch').value || 1),
    clip_skip: Number($('#clipSkip').value || 1),
    vae: $('#vae').value === '(auto)' ? null : $('#vae').value,
  };
}

async function queuePrompt({ keepText }) {
  const payload = readParamsFromUI();
  const p = (payload.prompt || '').trim();
  if (!p) return;

  try {
    await apiPost('/api/jobs', payload);
    if (!keepText) $('#quickPrompt').value = '';
    $('#quickPrompt').focus();
  } catch (e) {
    console.error(e);
    alert(String(e));
  }
}

function renderQueue() {
  const el = $('#queueList');
  const jobs = Array.from(state.jobs.values()).sort(sortByCreatedDesc);

  const frag = document.createDocumentFragment();

  if (jobs.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'hint';
    empty.textContent = 'まだジョブがありません。左で Prompt を入れて Queue。';
    frag.appendChild(empty);
    el.replaceChildren(frag);
    return;
  }

  for (const j of jobs) {
    const card = document.createElement('div');
    card.className = 'job';

    const promptEl = document.createElement('textarea');
    promptEl.className = 'job__promptEdit';
    promptEl.rows = 3;
    promptEl.value = j.prompt;

    const top = document.createElement('div');
    top.className = 'job__top';

    const left = document.createElement('div');
    left.style.minWidth = '0';

    const title = document.createElement('div');
    title.style.fontWeight = '700';
    title.style.fontSize = '12px';
    title.textContent = j.prompt_id ? `comfy:${j.prompt_id}` : `job:${j.id.slice(0,8)}`;

    const status = document.createElement('div');
    status.className = 'job__status';
    const pv = Number(j.progress_value || 0);
    const pm = Number(j.progress_max || 0);
    const pct = pm > 0 ? Math.round((pv / pm) * 100) : 0;
    status.textContent = `${j.status}${pm > 0 ? ` (${pv}/${pm} ${pct}%)` : ''}`;

    left.appendChild(title);
    left.appendChild(status);

    const right = document.createElement('div');
    right.style.display = 'flex';
    right.style.gap = '6px';

    const requeueBtn = document.createElement('button');
    requeueBtn.className = 'btn';
    requeueBtn.style.padding = '6px 10px';
    requeueBtn.textContent = 'Requeue';
    requeueBtn.onclick = async () => {
      const promptText = (promptEl.value || '').trim();
      if (!promptText) return;
      const recipe = {
        prompt: promptText,
        negative_prompt: j.negative_prompt,
        ...(j.params || {}),
      };
      // Map recipe keys to api keys
      const payload = {
        prompt: recipe.prompt,
        negative_prompt: recipe.negative_prompt,
        checkpoint: recipe.checkpoint ?? null,
        sampler_name: recipe.sampler_name ?? 'euler',
        scheduler: recipe.scheduler ?? 'normal',
        steps: recipe.steps ?? 20,
        cfg: recipe.cfg ?? 7,
        seed: recipe.seed ?? -1,
        width: recipe.width ?? 512,
        height: recipe.height ?? 512,
        batch_size: recipe.batch_size ?? 1,
        clip_skip: recipe.clip_skip ?? 1,
        vae: recipe.vae ?? null,
      };
      try {
        await apiPost('/api/jobs', payload);
      } catch (e) {
        alert(String(e));
      }
    };

    right.appendChild(requeueBtn);

    top.appendChild(left);
    top.appendChild(right);

    let errEl = null;
    if (j.error) {
      errEl = document.createElement('div');
      errEl.className = 'job__error';
      errEl.textContent = `ERROR: ${j.error}`;
    }

    const progress = document.createElement('div');
    progress.className = 'progress';
    const bar = document.createElement('div');
    bar.className = 'progress__bar';
    bar.style.width = `${pm > 0 ? Math.min(100, (pv / pm) * 100) : (j.status === 'completed' ? 100 : 0)}%`;
    progress.appendChild(bar);

    card.appendChild(top);
    card.appendChild(promptEl);
    if (errEl) card.appendChild(errEl);
    card.appendChild(progress);

    frag.appendChild(card);
  }

  el.replaceChildren(frag);
}

function renderGallery() {
  const el = $('#gallery');
  const assets = Array.from(state.assets.values()).sort(sortByCreatedDesc);
  const frag = document.createDocumentFragment();

  if (assets.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'hint';
    empty.textContent = 'まだ画像がありません。生成されるとここに勝手に増えます。';
    frag.appendChild(empty);
    el.replaceChildren(frag);
    return;
  }

  for (const a of assets) {
    const card = document.createElement('div');
    card.className = 'card';
    card.onclick = () => openModal(a.id);

    const img = document.createElement('img');
    img.loading = 'lazy';
    img.src = a.url;

    if (a.favorite) {
      const star = document.createElement('div');
      star.className = 'star';
      star.textContent = '★';
      card.appendChild(star);
    }

    card.appendChild(img);
    frag.appendChild(card);
  }

  el.replaceChildren(frag);
}

function isoNow() {
  return new Date().toISOString();
}

function getGrokSendFullHistory() {
  const el = $('#grokSendFullHistory');
  return Boolean(el && el.checked);
}

function getGrokSelectedModel() {
  const el = $('#grokModelSelect');
  return el ? el.value : null;
}

function isImageModel(model) {
  return Boolean(model) && model.includes('image');
}

function initGrokModelSelect(models, selected) {
  const el = $('#grokModelSelect');
  if (!el) return;

  const saved = localStorage.getItem(GROK_MODEL_KEY);
  const list = Array.isArray(models) && models.length ? models : (selected ? [selected] : []);

  populateSelect(el, list.length ? list : ['(unknown)'], selected);

  if (saved && list.includes(saved)) {
    el.value = saved;
  } else if (selected && list.includes(selected)) {
    el.value = selected;
  } else if (list.length) {
    el.value = list[0];
  }

  localStorage.setItem(GROK_MODEL_KEY, el.value);
  el.addEventListener('change', () => {
    localStorage.setItem(GROK_MODEL_KEY, el.value);
  });
}

function initGrokHistoryToggle() {
  const el = $('#grokSendFullHistory');
  if (!el) return;
  const saved = localStorage.getItem(GROK_HISTORY_TOGGLE_KEY);
  if (saved !== null) el.checked = saved === '1';
  el.addEventListener('change', () => {
    localStorage.setItem(GROK_HISTORY_TOGGLE_KEY, el.checked ? '1' : '0');
  });
}

async function initGrokHistory() {
  try {
    const history = await apiGet('/api/grok/history');
    state.grokMessages = (history || []).map((m) => ({
      role: m.role,
      content: m.content,
      ts: m.created_at || isoNow(),
    }));
    renderGrokMessages();
  } catch (e) {
    console.warn('grok history unavailable', e);
  }
}

function renderGrokLog() {
  const box = $('#grokLog');
  if (!box) return;

  if (state.grokErrors.length === 0) {
    box.textContent = 'No errors.';
    return;
  }

  const frag = document.createDocumentFragment();
  const items = state.grokErrors.slice(-5);
  for (const item of items) {
    const div = document.createElement('div');
    div.className = 'grokLog__item';
    div.textContent = `${item.ts} ${item.message}`;
    frag.appendChild(div);
  }
  box.replaceChildren(frag);
}

function addGrokError(message) {
  state.grokErrors.push({ message, ts: isoNow() });
  if (state.grokErrors.length > 50) state.grokErrors.shift();
  renderGrokLog();
}

function renderQueueLog() {
  const box = $('#queueLog');
  if (!box) return;

  if (state.comfyErrors.length === 0) {
    box.textContent = 'No errors.';
    return;
  }

  const frag = document.createDocumentFragment();
  const items = state.comfyErrors.slice(-5);
  for (const item of items) {
    const div = document.createElement('div');
    div.className = 'queueLog__item';
    div.textContent = `${item.ts} ${item.message}`;
    frag.appendChild(div);
  }
  box.replaceChildren(frag);
}

function addComfyError(message) {
  state.comfyErrors.push({ message, ts: isoNow() });
  if (state.comfyErrors.length > 50) state.comfyErrors.shift();
  renderQueueLog();
}

function trackJobError(job) {
  if (!job || !job.id || !job.error) return;
  if (job.status !== 'failed') return;
  if (state.jobErrorSeen.has(job.id)) return;
  state.jobErrorSeen.add(job.id);
  addComfyError(`job ${job.id.slice(0, 8)}: ${job.error}`);
}

function addGrokMessage(role, content) {
  state.grokMessages.push({ role, content, ts: isoNow() });
  renderGrokMessages();
}

function renderGrokMessages() {
  const box = $('#grokMessages');
  if (!box) return;

  if (state.grokMessages.length === 0) {
    box.replaceChildren(Object.assign(document.createElement('div'), {
      className: 'hint',
      style: 'margin:0',
      textContent: 'No messages yet.',
    }));
    return;
  }

  const frag = document.createDocumentFragment();
  for (const m of state.grokMessages) {
    const p = document.createElement('p');
    p.className = 'grokMsg';

    const role = document.createElement('span');
    role.className = 'grokMsg__role';
    role.textContent = m.role;

    const content = document.createElement('span');
    content.textContent = m.content;

    p.appendChild(role);
    p.appendChild(content);
    frag.appendChild(p);
  }
  box.replaceChildren(frag);

  // 常に最新へ
  box.scrollTop = box.scrollHeight;
}

async function initGrok() {
  const statusEl = $('#grokStatus');
  if (!statusEl) return;

  try {
    const cfg = await apiGet('/api/grok/config');
    const ok = Boolean(cfg?.ok);
    setPill(statusEl, ok ? 'Grok: ready' : 'Grok: not configured', ok ? 'pill--good' : 'pill--warn');
    initGrokModelSelect(cfg?.models || [], cfg?.model || '');
  } catch (e) {
    // サーバにエンドポイントがない／まだ実装してない場合でも落ちないように。
    setPill(statusEl, 'Grok: unavailable', 'pill--bad');
  }
}

async function sendGrok() {
  const input = $('#grokInput');
  const btn = $('#grokSendBtn');
  if (!input || !btn) return;

  const text = (input.value || '').trim();
  if (!text) return;

  input.value = '';
  input.focus();

  addGrokMessage('user', text);
  btn.disabled = true;

  try {
    const model = getGrokSelectedModel();
    if (isImageModel(model)) {
      const assets = await apiPost('/api/grok/image', {
        prompt: text,
        model,
        n: 1,
      });
      if (Array.isArray(assets)) {
        for (const a of assets) state.assets.set(a.id, a);
        scheduleRender();
      }
      const count = Array.isArray(assets) ? assets.length : 0;
      addGrokMessage('assistant', `Image generated: ${count}`);
    } else {
      const res = await apiPost('/api/grok/chat', {
        message: text,
        send_full_history: getGrokSendFullHistory(),
        model,
      });
      const reply = res?.reply ?? '(no reply)';
      addGrokMessage('assistant', reply);
    }
  } catch (e) {
    console.error(e);
    addGrokError(String(e));
    addGrokMessage('system', `ERROR: ${String(e)}`);
  } finally {
    btn.disabled = false;
  }
}

function updateStatusCounts() {
  // future: show counts; for now noop
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function computeFitZoom() {
  const img = $('#modalImg');
  const wrap = document.querySelector('.modal__imageWrap');
  if (!img || !wrap || !img.naturalWidth || !img.naturalHeight) return 1;
  return Math.min(
    wrap.clientWidth / img.naturalWidth,
    wrap.clientHeight / img.naturalHeight,
    1,
  );
}

function applyModalZoom(scale) {
  const img = $('#modalImg');
  if (!img) return;
  img.style.transform = `scale(${scale})`;
}

function setModalZoom(scale) {
  const zoom = clamp(scale, 0.1, 2.0);
  state.modalZoom = zoom;
  applyModalZoom(zoom);
  const range = $('#zoomRange');
  if (range) range.value = String(Math.round(zoom * 100));
}

function openModal(assetId) {
  const a = state.assets.get(assetId);
  if (!a) return;
  state.selectedAssetId = assetId;

  $('#modalTitle').textContent = a.id;
  const img = $('#modalImg');
  img.onload = () => {
    state.modalFitZoom = computeFitZoom();
    setModalZoom(state.modalFitZoom);
  };
  img.src = a.url;
  if (img.complete) {
    state.modalFitZoom = computeFitZoom();
    setModalZoom(state.modalFitZoom);
  }
  $('#modalMeta').textContent = JSON.stringify(a, null, 2);

  $('#favBtn').textContent = a.favorite ? 'Favorited' : 'Favorite';

  $('#modal').classList.remove('hidden');
}

function closeModal() {
  state.selectedAssetId = null;
  $('#modal').classList.add('hidden');
}

async function toggleFavorite() {
  const id = state.selectedAssetId;
  if (!id) return;
  try {
    const updated = await apiPost(`/api/assets/${id}/favorite`);
    state.assets.set(updated.id, updated);
    scheduleRender();
    openModal(updated.id);
  } catch (e) {
    alert(String(e));
  }
}

function setupUI() {
  $('#queueBtn').onclick = () => queuePrompt({ keepText: false });
  $('#queueKeepBtn').onclick = () => queuePrompt({ keepText: true });
  $('#clearPromptBtn').onclick = () => { $('#quickPrompt').value = ''; $('#quickPrompt').focus(); };
  $('#selectPromptBtn').onclick = () => {
    const el = $('#quickPrompt');
    if (!el) return;
    el.focus();
    el.select();
  };

  $('#quickPrompt').addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      queuePrompt({ keepText: false });
    }
  });

  $('#closeModalBtn').onclick = closeModal;
  $('#modalBackdrop').onclick = closeModal;
  $('#favBtn').onclick = toggleFavorite;
  const zoomRange = $('#zoomRange');
  const zoomInBtn = $('#zoomInBtn');
  const zoomOutBtn = $('#zoomOutBtn');
  const zoomFitBtn = $('#zoomFitBtn');
  if (zoomRange) {
    zoomRange.addEventListener('input', () => {
      setModalZoom(Number(zoomRange.value || 100) / 100);
    });
  }
  if (zoomInBtn) {
    zoomInBtn.onclick = () => setModalZoom((state.modalZoom || 1) + 0.1);
  }
  if (zoomOutBtn) {
    zoomOutBtn.onclick = () => setModalZoom((state.modalZoom || 1) - 0.1);
  }
  if (zoomFitBtn) {
    zoomFitBtn.onclick = () => setModalZoom(state.modalFitZoom || 1);
  }

  // Grok chat
  const grokSendBtn = $('#grokSendBtn');
  const grokInput = $('#grokInput');
  if (grokSendBtn && grokInput) {
    grokSendBtn.onclick = sendGrok;
    grokInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendGrok();
      }
    });
  }

  initGrokHistoryToggle();

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeModal();
  });
  window.addEventListener('resize', () => {
    const modal = $('#modal');
    if (modal && !modal.classList.contains('hidden')) {
      state.modalFitZoom = computeFitZoom();
      setModalZoom(state.modalFitZoom);
    }
  });
}

function populateSelect(selectEl, items, selected) {
  selectEl.replaceChildren();
  for (const v of items) {
    const opt = document.createElement('option');
    opt.value = v;
    opt.textContent = v;
    if (selected && v === selected) opt.selected = true;
    selectEl.appendChild(opt);
  }
}

async function initConfig() {
  const cfg = await apiGet('/api/config');
  state.config = cfg;

  const defaults = cfg.defaults || {};
  $('#steps').value = defaults.steps ?? 20;
  $('#cfg').value = defaults.cfg ?? 7;
  $('#seed').value = defaults.seed ?? -1;
  $('#width').value = defaults.width ?? 512;
  $('#height').value = defaults.height ?? 512;
  $('#batch').value = defaults.batch_size ?? 1;
  $('#clipSkip').value = defaults.clip_skip ?? 1;
  $('#neg').value = defaults.negative_prompt ?? '';

  const cps = cfg.choices?.checkpoints || [];
  const samplers = cfg.choices?.samplers || [];
  const schedulers = cfg.choices?.schedulers || [];
  const vaes = cfg.choices?.vaes || [];

  populateSelect($('#checkpoint'), cps.length ? cps : ['(no checkpoints found)'], defaults.checkpoint);
  populateSelect($('#sampler'), samplers, defaults.sampler_name);
  populateSelect($('#scheduler'), schedulers, defaults.scheduler);
  const vaeList = ['(auto)', ...vaes];
  populateSelect($('#vae'), vaeList, defaults.vae || '(auto)');

  setPill($('#comfyStatus'), `Comfy: ${cfg.comfy_url}`, 'pill--warn');
}

function connectWS() {
  const wsProto = location.protocol === 'https:' ? 'wss' : 'ws';
  const wsUrl = `${wsProto}://${location.host}/api/ws`;

  const ws = new WebSocket(wsUrl);
  state.ws = ws;

  setPill($('#wsStatus'), 'WS: connecting', 'pill--warn');

  ws.onopen = () => {
    setPill($('#wsStatus'), 'WS: connected', 'pill--good');
    // Ping loop so the server-side receive loop doesn't idle forever.
    const ping = () => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping');
      setTimeout(ping, 20000);
    };
    ping();
  };

  ws.onclose = () => {
    setPill($('#wsStatus'), 'WS: disconnected', 'pill--bad');
    setTimeout(connectWS, 1000);
  };

  ws.onerror = () => {
    setPill($('#wsStatus'), 'WS: error', 'pill--bad');
  };

  ws.onmessage = (ev) => {
    let msg;
    try { msg = JSON.parse(ev.data); } catch { return; }
    const { type, payload } = msg;

    if (type === 'hello') return;

    if (type === 'comfy_connected') {
      setPill($('#comfyStatus'), `Comfy: connected`, 'pill--good');
      return;
    }
    if (type === 'comfy_disconnected') {
      setPill($('#comfyStatus'), `Comfy: disconnected`, 'pill--bad');
      return;
    }

    if (type === 'jobs_snapshot') {
      state.jobs.clear();
      for (const j of payload || []) {
        state.jobs.set(j.id, j);
        trackJobError(j);
      }
      scheduleRender();
      return;
    }

    if (type === 'assets_snapshot') {
      state.assets.clear();
      for (const a of payload || []) state.assets.set(a.id, a);
      scheduleRender();
      return;
    }

    if (type === 'job_created' || type === 'job_update') {
      state.jobs.set(payload.id, payload);
      trackJobError(payload);
      scheduleRender();
      return;
    }

    if (type === 'job_progress') {
      const j = state.jobs.get(payload.job_id);
      if (j) {
        j.progress_value = payload.value;
        j.progress_max = payload.max;
        state.jobs.set(j.id, j);
        scheduleRender();
      }
      return;
    }

    if (type === 'asset_created' || type === 'asset_updated') {
      state.assets.set(payload.id, payload);
      scheduleRender();
      return;
    }
  };
}

async function boot() {
  setupUI();
  await initConfig();
  await initGrok();
  await initGrokHistory();
  connectWS();
  scheduleRender();
}

boot().catch((e) => {
  console.error(e);
  alert(String(e));
});
