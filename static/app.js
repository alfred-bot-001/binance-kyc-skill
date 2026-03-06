// ── Chat Demo JS ──

let sessionId = null;
let currentState = 'awaiting_consent';

// Quick action buttons per state
const quickActions = {
  'awaiting_consent': [
    { label: 'Yes, I agree ✅', value: 'yes' },
    { label: 'No ❌', value: 'no' },
  ],
  'collecting_name': [
    { label: 'John Doe', value: 'John Doe' },
    { label: '张三', value: '张三' },
  ],
  'collecting_dob': [
    { label: '1990-01-15', value: '1990-01-15' },
    { label: '1985-06-20', value: '1985-06-20' },
  ],
  'collecting_nationality': [
    { label: '🇺🇸 United States', value: 'United States' },
    { label: '🇨🇳 China', value: 'China' },
    { label: '🇯🇵 Japan', value: 'Japan' },
    { label: '🇬🇧 UK', value: 'United Kingdom' },
  ],
  'collecting_address': [
    { label: '123 Main St, NYC', value: '123 Main St, New York, NY 10001, USA' },
    { label: '北京市朝阳区建国路 88号', value: '北京市朝阳区建国路88号, 100022, 中国' },
  ],
  'selecting_document': [
    { label: '1️⃣ Passport', value: '1' },
    { label: '2️⃣ National ID', value: '2' },
    { label: '3️⃣ License', value: '3' },
  ],
  'reviewing': [
    { label: '✅ Confirm', value: 'confirm' },
    { label: '✏️ Edit', value: 'edit' },
  ],
};

async function api(url, data = {}) {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  return res.json();
}

function addMessage(text, type = 'bot') {
  const container = document.getElementById('chat-messages');
  const div = document.createElement('div');
  div.className = `msg ${type}`;
  // Convert **bold** to <b>bold</b>
  let html = text
    .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
    .replace(/\n/g, '<br>');
  div.innerHTML = html;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function updateProgress(progress, state) {
  const fill = document.getElementById('progress-fill');
  const label = document.getElementById('progress-label');
  fill.style.width = `${progress * 100}%`;

  const labels = {
    'awaiting_consent': 'Getting started',
    'collecting_name': 'Personal information',
    'collecting_dob': 'Date of birth',
    'collecting_nationality': 'Nationality',
    'collecting_address': 'Address',
    'selecting_document': 'Document selection',
    'uploading_doc_front': 'Document upload',
    'uploading_doc_back': 'Document upload (back)',
    'uploading_selfie': 'Selfie',
    'reviewing': 'Review & confirm',
    'submitted': 'Processing...',
    'approved': 'Verified ✅',
  };
  label.textContent = `${Math.round(progress * 100)}% — ${labels[state] || state}`;
}

function updateFlowDiagram(state) {
  const steps = document.querySelectorAll('.flow-step');
  let foundCurrent = false;
  steps.forEach(step => {
    const stepState = step.dataset.step;
    if (stepState === state) {
      step.classList.add('active');
      step.classList.remove('done');
      foundCurrent = true;
    } else if (!foundCurrent) {
      step.classList.remove('active');
      step.classList.add('done');
    } else {
      step.classList.remove('active', 'done');
    }
  });
}

function updateCollectedData(data, docType) {
  if (!data) return;
  document.getElementById('data-name').textContent = data.full_name || '—';
  document.getElementById('data-dob').textContent = data.date_of_birth || '—';
  document.getElementById('data-nationality').textContent = data.nationality || '—';
  document.getElementById('data-address').textContent = data.address || '—';
  document.getElementById('data-doc').textContent = docType || '—';

  // Highlight filled fields
  ['name', 'dob', 'nationality', 'address', 'doc'].forEach(field => {
    const el = document.getElementById(`data-${field}`);
    if (el.textContent !== '—') {
      el.classList.add('highlight');
    }
  });
}

function showQuickActions(state) {
  const container = document.getElementById('quick-actions');
  container.innerHTML = '';
  const actions = quickActions[state];
  if (!actions) return;

  actions.forEach(action => {
    const btn = document.createElement('button');
    btn.className = 'quick-btn';
    btn.textContent = action.label;
    btn.onclick = () => {
      document.getElementById('chat-input').value = action.value;
      sendMessage();
    };
    container.appendChild(btn);
  });
}

function showPhotoQuickAction() {
  const container = document.getElementById('quick-actions');
  container.innerHTML = '';
  const btn = document.createElement('button');
  btn.className = 'quick-btn';
  btn.textContent = '📷 Send Photo (simulated)';
  btn.onclick = () => sendPhoto();
  container.appendChild(btn);
}

async function handleResponse(resp) {
  sessionId = resp.session_id;
  currentState = resp.state;

  resp.bot_messages.forEach(msg => {
    addMessage(msg, 'bot');
  });

  updateProgress(resp.progress, resp.state);
  updateFlowDiagram(resp.state);
  updateCollectedData(resp.personal_info, resp.document_type);

  // Show appropriate quick actions
  if (['uploading_doc_front', 'uploading_doc_back', 'uploading_selfie'].includes(resp.state)) {
    showPhotoQuickAction();
  } else {
    showQuickActions(resp.state);
  }
}

async function sendMessage() {
  const input = document.getElementById('chat-input');
  const text = input.value.trim();
  if (!text) return;

  addMessage(text, 'user');
  input.value = '';

  const resp = await api('/api/chat', {
    session_id: sessionId,
    message: text,
    language: currentLang,
  });
  await handleResponse(resp);
}

async function sendPhoto() {
  addMessage('📷 [Photo sent]', 'user');

  const resp = await api('/api/chat', {
    session_id: sessionId,
    message: '',
    image: true,
    language: currentLang,
  });
  await handleResponse(resp);
}

async function resetChat() {
  if (sessionId) {
    await api('/api/reset', { session_id: sessionId });
  }
  sessionId = null;
  currentState = 'awaiting_consent';
  document.getElementById('chat-messages').innerHTML = '';
  document.getElementById('progress-fill').style.width = '0%';
  document.getElementById('progress-label').textContent = '0% — Getting started';
  document.getElementById('quick-actions').innerHTML = '';
  ['name', 'dob', 'nationality', 'address', 'doc'].forEach(f => {
    const el = document.getElementById(`data-${f}`);
    el.textContent = '—';
    el.classList.remove('highlight');
  });
  document.querySelectorAll('.flow-step').forEach((s, i) => {
    s.classList.remove('done', 'active');
    if (i === 0) s.classList.add('active');
  });
  startChat();
}

async function startChat() {
  const resp = await api('/api/start', { language: currentLang });
  await handleResponse(resp);
}

function onLangChange(lang) {
  // Update flow diagram labels based on language
  const flowLabels = {
    en: ['Consent', 'Name', 'DOB', 'Country', 'Address', 'Doc', '📄', '📸', 'Review', '✅'],
    zh: ['同意', '姓名', '生日', '国籍', '地址', '证件', '📄', '📸', '确认', '✅'],
  };
  const steps = document.querySelectorAll('.flow-step');
  const labels = flowLabels[lang] || flowLabels['en'];
  steps.forEach((step, i) => {
    if (labels[i]) step.textContent = labels[i];
  });
}

// Auto-start
window.addEventListener('DOMContentLoaded', startChat);
