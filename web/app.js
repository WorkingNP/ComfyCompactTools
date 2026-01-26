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
  templates: [],
  thumbSize: 200,
  workflows: [], // Available workflows
  selectedWorkflow: null, // Currently selected workflow detail (with params)
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
  const payload = {};

  // If using dynamic workflow form
  if (state.selectedWorkflow) {
    payload.workflow_id = state.selectedWorkflow.id;

    // Read all dynamic params
    const dynamicInputs = document.querySelectorAll('#dynamicParams [data-param-name]');
    for (const input of dynamicInputs) {
      const paramName = input.getAttribute('data-param-name');
      const paramType = input.getAttribute('data-param-type');

      let value;
      if (input.type === 'checkbox') {
        value = input.checked;
      } else if (paramType === 'integer') {
        value = parseInt(input.value, 10);
        if (isNaN(value)) value = 0;
      } else if (paramType === 'float') {
        value = parseFloat(input.value);
        if (isNaN(value)) value = 0.0;
      } else {
        value = input.value;
      }

      payload[paramName] = value;
    }

    // Ensure prompt from quickPrompt takes priority if present
    const quickPrompt = $('#quickPrompt');
    if (quickPrompt && quickPrompt.value.trim()) {
      payload.prompt = quickPrompt.value.trim();
    }
  } else {
    // Legacy mode: use old fixed form
    payload.prompt = $('#quickPrompt').value;
    payload.negative_prompt = $('#neg').value;
    payload.checkpoint = $('#checkpoint').value || null;
    payload.sampler_name = $('#sampler').value;
    payload.scheduler = $('#scheduler').value;
    payload.steps = Number($('#steps').value || 20);
    payload.cfg = Number($('#cfg').value || 7);
    payload.seed = Number($('#seed').value || -1);
    payload.width = Number($('#width').value || 512);
    payload.height = Number($('#height').value || 512);
    payload.batch_size = Number($('#batch').value || 1);
    payload.clip_skip = Number($('#clipSkip').value || 1);
    payload.vae = $('#vae').value === '(auto)' ? null : $('#vae').value;
  }

  return payload;
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

      const params = j.params || {};
      const workflow_id = params.workflow_id;

      // Build payload preserving workflow_id if present
      const payload = {
        prompt: promptText,
        ...params
      };

      // Override prompt with edited value
      payload.prompt = promptText;

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

async function initTemplates() {
  const tryFetch = async (url) => {
    const r = await fetch(url);
    if (!r.ok) throw new Error(`${url} -> ${r.status}`);
    return await r.json();
  };

  try {
    const res = await tryFetch('/api/templates');
    state.templates = Array.isArray(res) ? res : [];
  } catch (e) {
    try {
      const res = await tryFetch('/templates.json');
      const items = res?.templates;
      state.templates = Array.isArray(items) ? items : [];
    } catch (err) {
      console.warn('templates unavailable', err);
      state.templates = [];
    }
  }

  const select = $('#templateSelect');
  if (!select) return;
  const names = state.templates.map((t) => t.name);
  populateSelect(select, ['(none)', ...names], '(none)');
  updateTemplateNotes();
}

async function initWorkflows() {
  try {
    const workflows = await apiGet('/api/workflows');
    state.workflows = Array.isArray(workflows) ? workflows : [];

    const select = $('#workflowSelect');
    if (!select) return;

    if (state.workflows.length === 0) {
      select.innerHTML = '<option value="">No workflows available</option>';
      return;
    }

    // Populate workflow select
    select.innerHTML = state.workflows.map(wf =>
      `<option value="${wf.id}">${wf.name}</option>`
    ).join('');

    // Select first workflow by default
    if (state.workflows.length > 0) {
      select.value = state.workflows[0].id;
      await loadWorkflowDetail(state.workflows[0].id);
    }

    // Setup change handler
    select.addEventListener('change', async (e) => {
      const workflowId = e.target.value;
      if (workflowId) {
        await loadWorkflowDetail(workflowId);
      }
    });
  } catch (e) {
    console.error('Failed to load workflows:', e);
    state.workflows = [];
  }
}

async function loadWorkflowDetail(workflowId) {
  try {
    const detail = await apiGet(`/api/workflows/${workflowId}`);
    state.selectedWorkflow = detail;

    // Update description
    const descEl = $('#workflowDescription');
    if (descEl) {
      descEl.textContent = detail.description || 'No description available.';
    }

    // Generate dynamic form
    generateDynamicForm(detail.params || {});
  } catch (e) {
    console.error('Failed to load workflow detail:', e);
    state.selectedWorkflow = null;
  }
}

function generateDynamicForm(params) {
  const container = $('#dynamicParams');
  if (!container) return;

  container.innerHTML = ''; // Clear existing

  // Sort params: required first, then optional
  const entries = Object.entries(params).sort((a, b) => {
    const aReq = a[1].required || false;
    const bReq = b[1].required || false;
    if (aReq && !bReq) return -1;
    if (!aReq && bReq) return 1;
    return a[0].localeCompare(b[0]);
  });

  for (const [paramName, paramDef] of entries) {
    const div = document.createElement('div');

    const label = document.createElement('label');
    label.className = 'label';
    label.textContent = paramDef.description || paramName;
    if (paramDef.required) {
      label.textContent += ' *';
    }
    div.appendChild(label);

    let input;
    const type = paramDef.type || 'string';

    if (paramDef.choices && Array.isArray(paramDef.choices)) {
      // Enum/choices -> select
      input = document.createElement('select');
      input.className = 'select';
      input.innerHTML = paramDef.choices.map(choice =>
        `<option value="${choice}">${choice}</option>`
      ).join('');
      if (paramDef.default !== undefined) {
        input.value = paramDef.default;
      }
    } else if (type === 'boolean') {
      // Boolean -> checkbox
      input = document.createElement('input');
      input.type = 'checkbox';
      if (paramDef.default !== undefined) {
        input.checked = !!paramDef.default;
      }
    } else if (type === 'integer') {
      // Integer -> number input
      input = document.createElement('input');
      input.className = 'input';
      input.type = 'number';
      input.step = '1';
      if (paramDef.min !== undefined) input.min = paramDef.min;
      if (paramDef.max !== undefined) input.max = paramDef.max;
      if (paramDef.default !== undefined) input.value = paramDef.default;
    } else if (type === 'float') {
      // Float -> number input
      input = document.createElement('input');
      input.className = 'input';
      input.type = 'number';
      input.step = '0.1';
      if (paramDef.min !== undefined) input.min = paramDef.min;
      if (paramDef.max !== undefined) input.max = paramDef.max;
      if (paramDef.default !== undefined) input.value = paramDef.default;
    } else {
      // String (default) or prompt -> text input or textarea
      if (paramName === 'prompt' || paramName === 'negative_prompt') {
        input = document.createElement('textarea');
        input.className = 'textarea';
        input.rows = paramName === 'prompt' ? 4 : 2;
        if (paramDef.default !== undefined) input.value = paramDef.default;
      } else {
        input = document.createElement('input');
        input.className = 'input';
        input.type = 'text';
        if (paramDef.default !== undefined) input.value = paramDef.default;
      }
    }

    input.id = `dynamic_${paramName}`;
    input.setAttribute('data-param-name', paramName);
    input.setAttribute('data-param-type', type);

    div.appendChild(input);
    container.appendChild(div);
  }
}

function getSelectedTemplate() {
  const select = $('#templateSelect');
  if (!select) return null;
  const name = select.value;
  return state.templates.find((t) => t.name === name) || null;
}

function updateTemplateNotes() {
  const notesEl = $('#templateNotes');
  if (!notesEl) return;
  const t = getSelectedTemplate();
  if (!t) {
    notesEl.textContent = 'No template selected.';
    return;
  }
  const triggers = Array.isArray(t.trigger_words) ? t.trigger_words.join(', ') : '';
  const lines = [];
  if (t.notes) lines.push(t.notes);
  if (triggers) lines.push(`Triggers: ${triggers}`);
  notesEl.textContent = lines.length ? lines.join('\n') : 'No notes.';
}

function applyTemplate() {
  const t = getSelectedTemplate();
  if (!t) return;

  if (t.checkpoint) $('#checkpoint').value = t.checkpoint;
  if (t.sampler_name) $('#sampler').value = t.sampler_name;
  if (t.scheduler) $('#scheduler').value = t.scheduler;
  if (t.steps != null) $('#steps').value = t.steps;
  if (t.cfg != null) $('#cfg').value = t.cfg;
  if (t.seed != null) $('#seed').value = t.seed;
  if (t.width != null) $('#width').value = t.width;
  if (t.height != null) $('#height').value = t.height;
  if (t.batch_size != null) $('#batch').value = t.batch_size;
  if (t.clip_skip != null) $('#clipSkip').value = t.clip_skip;
  if (t.vae != null) $('#vae').value = t.vae;
  if (t.negative_prompt != null) $('#neg').value = t.negative_prompt;

  updateTemplateNotes();
}

function insertTemplateTriggers() {
  const t = getSelectedTemplate();
  if (!t || !Array.isArray(t.trigger_words) || t.trigger_words.length === 0) return;
  const prompt = $('#quickPrompt');
  if (!prompt) return;
  const current = prompt.value || '';
  const insert = t.trigger_words.join(', ');
  prompt.value = current ? `${current}, ${insert}` : insert;
  prompt.focus();
}

function initGalleryControls() {
  const range = $('#thumbSize');
  const value = $('#thumbSizeValue');
  const gallery = $('#gallery');
  if (!range || !value || !gallery) return;
  const apply = (val) => {
    state.thumbSize = val;
    gallery.style.setProperty('--thumb-size', `${val}px`);
    value.textContent = String(val);
  };
  apply(state.thumbSize);
  range.addEventListener('input', () => apply(Number(range.value || 200)));
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

async function rerunFromModal() {
  const assetId = state.selectedAssetId;
  if (!assetId) return;

  const asset = state.assets.get(assetId);
  if (!asset || !asset.recipe) return;

  const recipe = asset.recipe;
  const params = recipe.params || {};

  // Restore prompt to quickPrompt textarea
  if (recipe.prompt) {
    const quickPrompt = $('#quickPrompt');
    if (quickPrompt) {
      quickPrompt.value = recipe.prompt;
    }
  }

  // If workflow_id is present, switch to that workflow
  if (params.workflow_id) {
    const workflowSelect = $('#workflowSelect');
    if (workflowSelect && workflowSelect.value !== params.workflow_id) {
      workflowSelect.value = params.workflow_id;
      // Trigger workflow load
      await loadWorkflowDetail(params.workflow_id);
    }

    // Wait a tick for dynamic form to be generated
    await new Promise(resolve => setTimeout(resolve, 100));

    // Restore dynamic form values
    for (const [paramName, paramValue] of Object.entries(params)) {
      if (paramName === 'workflow_id') continue;

      const input = document.querySelector(`#dynamicParams [data-param-name="${paramName}"]`);
      if (input) {
        if (input.type === 'checkbox') {
          input.checked = !!paramValue;
        } else {
          input.value = paramValue;
        }
      }
    }
  } else {
    // Legacy mode: restore to old fixed form
    if (recipe.negative_prompt !== undefined) $('#neg').value = recipe.negative_prompt;
    if (recipe.checkpoint) $('#checkpoint').value = recipe.checkpoint;
    if (recipe.sampler_name) $('#sampler').value = recipe.sampler_name;
    if (recipe.scheduler) $('#scheduler').value = recipe.scheduler;
    if (params.steps !== undefined) $('#steps').value = params.steps;
    if (params.cfg !== undefined) $('#cfg').value = params.cfg;
    if (params.seed !== undefined) $('#seed').value = params.seed;
    if (params.width !== undefined) $('#width').value = params.width;
    if (params.height !== undefined) $('#height').value = params.height;
    if (params.batch_size !== undefined) $('#batch').value = params.batch_size;
    if (params.clip_skip !== undefined) $('#clipSkip').value = params.clip_skip;
    if (params.vae) $('#vae').value = params.vae;
  }

  // Close modal and focus prompt
  closeModal();
  const quickPrompt = $('#quickPrompt');
  if (quickPrompt) quickPrompt.focus();
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
  $('#rerunBtn').onclick = rerunFromModal;
  const templateSelect = $('#templateSelect');
  const applyTemplateBtn = $('#applyTemplateBtn');
  const insertTriggersBtn = $('#insertTriggersBtn');
  if (templateSelect) {
    templateSelect.onchange = updateTemplateNotes;
  }
  if (applyTemplateBtn) applyTemplateBtn.onclick = applyTemplate;
  if (insertTriggersBtn) insertTriggersBtn.onclick = insertTemplateTriggers;
  const prevBtn = $('#prevAssetBtn');
  const nextBtn = $('#nextAssetBtn');
  if (prevBtn) prevBtn.onclick = () => openAssetByOffset(1);
  if (nextBtn) nextBtn.onclick = () => openAssetByOffset(-1);
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
    if (e.key === 'ArrowRight') openAssetByOffset(1);
    if (e.key === 'ArrowLeft') openAssetByOffset(-1);
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

  const uiDefaults = {
    width: 832,
    height: 1024,
    steps: 20,
    cfg: 4.0,
    sampler_name: 'euler_ancestral',
    scheduler: 'normal',
    seed: -1,
    batch_size: 1,
    clip_skip: 2,
    vae: null,
    negative_prompt: '(worst quality, low quality:1.4), (deformed, distorted, disfigured:1.3), poorly drawn, bad anatomy, wrong anatomy, extra limb, missing limb, floating limbs, (mutated hands and fingers:1.4), cloned face, malformed hands, long neck, extra breasts, mutated pussy, bad pussy, blurry, watermark, text, error, cropped',
  };
  const defaults = { ...(cfg.defaults || {}), ...uiDefaults };
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
  const samplerDefault = samplers.includes(defaults.sampler_name) ? defaults.sampler_name : (samplers[0] || '');
  const schedulerDefault = schedulers.includes(defaults.scheduler) ? defaults.scheduler : (schedulers[0] || '');
  populateSelect($('#sampler'), samplers, samplerDefault);
  populateSelect($('#scheduler'), schedulers, schedulerDefault);
  const vaeList = ['(auto)', ...vaes];
  populateSelect($('#vae'), vaeList, defaults.vae || '(auto)');

  // Check ComfyUI health status
  try {
    const health = await apiGet('/api/health');
    const comfyStatusEl = $('#comfyStatus');
    if (health.ok) {
      setPill(comfyStatusEl, `Comfy: connected`, 'pill--good');
    } else if (health.error_code === 'COMFY_UNREACHABLE') {
      setPill(comfyStatusEl, `Comfy: unreachable`, 'pill--bad');
    } else {
      setPill(comfyStatusEl, `Comfy: error (${health.error_code || 'unknown'})`, 'pill--bad');
    }
  } catch (e) {
    setPill($('#comfyStatus'), `Comfy: check failed`, 'pill--bad');
  }
}

function getSortedAssets() {
  return Array.from(state.assets.values()).sort(sortByCreatedDesc);
}

function openAssetByOffset(offset) {
  const modal = $('#modal');
  if (!modal || modal.classList.contains('hidden')) return;
  if (!state.selectedAssetId) return;
  const assets = getSortedAssets();
  if (!assets.length) return;
  const idx = assets.findIndex((a) => a.id === state.selectedAssetId);
  const nextIdx = idx === -1 ? 0 : (idx + offset + assets.length) % assets.length;
  openModal(assets[nextIdx].id);
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
  await initWorkflows(); // Load workflows and generate dynamic form
  await initTemplates();
  initGalleryControls();
  await initGrok();
  await initGrokHistory();
  connectWS();
  scheduleRender();
}

boot().catch((e) => {
  console.error(e);
  alert(String(e));
});
