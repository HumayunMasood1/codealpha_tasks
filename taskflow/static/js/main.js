const csrf = () => document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

// ── Toast ──
function showToast(msg, type = 'success') {
  const c = document.getElementById('toast-container') ||
    (() => { const d = document.createElement('div'); d.id = 'toast-container'; d.className = 'toast-container'; document.body.appendChild(d); return d; })();
  const t = document.createElement('div');
  t.className = `toast${type === 'error' ? ' error' : ''}`;
  t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3500);
}

// ── Dropdown ──
function toggleDropdown(id) {
  const d = document.getElementById(id);
  if (d) d.classList.toggle('open');
}

document.addEventListener('click', e => {
  if (!e.target.closest('.dropdown')) {
    document.querySelectorAll('.dropdown-menu.open').forEach(d => d.classList.remove('open'));
  }
});

// ── Modal ──
function openModal(id) { document.getElementById(id)?.classList.add('open'); }
function closeModal(id) { document.getElementById(id)?.classList.remove('open'); }

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') document.querySelectorAll('.modal-overlay.open').forEach(m => m.classList.remove('open'));
});

// ── WebSocket Notifications ──
let ws;
function connectNotifications() {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  ws = new WebSocket(`${proto}//${location.host}/ws/notifications/`);

  ws.onmessage = e => {
    const data = JSON.parse(e.data);
    if (data.type === 'unread_count') updateBadge(data.count);
    if (data.type === 'notification') {
      showToast('🔔 ' + data.message);
      fetchUnreadCount();
    }
  };

  ws.onclose = () => setTimeout(connectNotifications, 3000);
}

function fetchUnreadCount() {
  fetch('/notifications/count/')
    .then(r => r.json())
    .then(d => updateBadge(d.count));
}

function updateBadge(count) {
  const badge = document.getElementById('notif-badge');
  if (!badge) return;
  badge.textContent = count;
  badge.style.display = count > 0 ? 'flex' : 'none';
}

// ── Board WebSocket ──
let boardWs;
function connectBoard(projectId) {
  const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
  boardWs = new WebSocket(`${proto}//${location.host}/ws/project/${projectId}/`);

  boardWs.onmessage = e => {
    const data = JSON.parse(e.data);
    if (data.type === 'board_update') {
      showToast('🔄 Board updated by a teammate');
    }
  };

  boardWs.onclose = () => setTimeout(() => connectBoard(projectId), 3000);
}

// ── Drag & Drop ──
let draggedTask = null;

function initDragDrop() {
  document.querySelectorAll('.task-card').forEach(card => {
    card.setAttribute('draggable', true);
    card.addEventListener('dragstart', e => {
      draggedTask = card;
      card.classList.add('dragging');
      e.dataTransfer.effectAllowed = 'move';
    });
    card.addEventListener('dragend', () => {
      card.classList.remove('dragging');
      draggedTask = null;
      document.querySelectorAll('.column-body').forEach(c => c.classList.remove('drag-over'));
    });
  });

  document.querySelectorAll('.column-body').forEach(col => {
    col.addEventListener('dragover', e => {
      e.preventDefault();
      col.classList.add('drag-over');
      const afterEl = getDragAfterElement(col, e.clientY);
      if (afterEl) col.insertBefore(draggedTask, afterEl);
      else col.appendChild(draggedTask);
    });

    col.addEventListener('dragleave', () => col.classList.remove('drag-over'));

    col.addEventListener('drop', async e => {
      e.preventDefault();
      col.classList.remove('drag-over');
      if (!draggedTask) return;
      const taskId = draggedTask.dataset.taskId;
      const columnId = col.dataset.columnId;
      const order = Array.from(col.querySelectorAll('.task-card')).indexOf(draggedTask);

      const res = await fetch(`/task/${taskId}/move/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        body: JSON.stringify({ column_id: columnId, order })
      });

      if (res.ok) {
        // Update column counts
        updateColumnCounts();
        showToast('Task moved!');
        // Broadcast via WebSocket
        if (boardWs && boardWs.readyState === WebSocket.OPEN) {
          boardWs.send(JSON.stringify({ action: 'task_moved', data: { taskId, columnId } }));
        }
      }
    });
  });
}

function getDragAfterElement(container, y) {
  const cards = [...container.querySelectorAll('.task-card:not(.dragging)')];
  return cards.reduce((closest, child) => {
    const box = child.getBoundingClientRect();
    const offset = y - box.top - box.height / 2;
    if (offset < 0 && offset > closest.offset) return { offset, element: child };
    return closest;
  }, { offset: Number.NEGATIVE_INFINITY }).element;
}

function updateColumnCounts() {
  document.querySelectorAll('.column').forEach(col => {
    const count = col.querySelectorAll('.task-card').length;
    const badge = col.querySelector('.column-count');
    if (badge) badge.textContent = count;
  });
}

// ── Quick Add Task ──
async function quickAddTask(columnId, btn) {
  const input = btn.previousElementSibling;
  const title = input?.value?.trim();
  if (!title) { input?.focus(); return; }
  const res = await fetch(`/column/${columnId}/task/create/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrf(), 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `title=${encodeURIComponent(title)}&priority=medium`
  });
  const data = await res.json();
  if (data.success) {
    input.value = '';
    addTaskToBoard(data);
    showToast('Task created!');
    updateColumnCounts();
  }
}

function addTaskToBoard(task) {
  const col = document.querySelector(`[data-column-id="${task.column_id}"] .column-body`);
  if (!col) return;
  const card = document.createElement('div');
  card.className = 'task-card';
  card.dataset.taskId = task.id;
  card.innerHTML = `
    <div class="task-card-priority priority-tag-${task.priority}">${task.priority}</div>
    <div class="task-card-title">${task.title}</div>
    <div class="task-card-footer">
      <div class="task-card-meta"><span>💬 0</span></div>
      <a href="/task/${task.id}/" style="font-size:.75rem;color:var(--accent2)">Open →</a>
    </div>`;
  col.appendChild(card);
  initDragDrop();
}

// ── Delete Task ──
async function deleteTask(taskId) {
  if (!confirm('Delete this task?')) return;
  const res = await fetch(`/task/${taskId}/delete/`, { method: 'POST', headers: { 'X-CSRFToken': csrf() } });
  if (res.ok) {
    document.querySelector(`[data-task-id="${taskId}"]`)?.remove();
    showToast('Task deleted');
    updateColumnCounts();
  }
}

// ── Add Column ──
async function addColumn(projectId) {
  const name = prompt('Column name:');
  if (!name?.trim()) return;
  const res = await fetch(`/project/${projectId}/column/add/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrf(), 'Content-Type': 'application/x-www-form-urlencoded' },
    body: `name=${encodeURIComponent(name)}`
  });
  if (res.ok) { showToast('Column added!'); location.reload(); }
}

// ── Delete Column ──
async function deleteColumn(columnId) {
  if (!confirm('Delete this column and all its tasks?')) return;
  const res = await fetch(`/column/${columnId}/delete/`, { method: 'POST', headers: { 'X-CSRFToken': csrf() } });
  if (res.ok) { showToast('Column deleted'); location.reload(); }
}

// ── Task Detail: Update ──
async function saveTaskField(taskId, field, value) {
  await fetch(`/task/${taskId}/update/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
    body: JSON.stringify({ [field]: value })
  });
  showToast('Saved ✓');
}

// ── Comment ──
async function submitComment(taskId) {
  const input = document.getElementById('comment-input');
  const content = input?.value?.trim();
  if (!content) return;
  const fd = new FormData();
  fd.append('content', content);
  fd.append('csrfmiddlewaretoken', csrf());
  const res = await fetch(`/task/${taskId}/comment/`, { method: 'POST', body: fd });
  const data = await res.json();
  if (data.success) {
    input.value = '';
    const list = document.getElementById('comment-list');
    const el = document.createElement('div');
    el.className = 'notif-item';
    el.innerHTML = `
      <div class="avatar">${data.author[0].toUpperCase()}</div>
      <div class="notif-content">
        <div style="font-weight:700;font-size:.85rem;margin-bottom:.25rem">@${data.author}</div>
        <div class="notif-message">${data.content}</div>
        <div class="notif-time">just now</div>
      </div>`;
    list?.appendChild(el);
  }
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  const isAuth = document.body.dataset.authenticated === 'true';
  if (isAuth) {
    connectNotifications();
    fetchUnreadCount();
  }
  initDragDrop();
});
