const csrf = () => document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';

function showToast(msg) {
  const c = document.getElementById('toast-container') ||
    (() => { const d = document.createElement('div'); d.id = 'toast-container'; d.className = 'toast-container'; document.body.appendChild(d); return d; })();
  const t = document.createElement('div');
  t.className = 'toast'; t.textContent = msg;
  c.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// ── Like toggle ──
async function toggleLike(postId, btn) {
  const res = await fetch(`/post/${postId}/like/`, { method: 'POST', headers: { 'X-CSRFToken': csrf() } });
  const data = await res.json();
  const countEl = btn.querySelector('.like-count');
  if (countEl) countEl.textContent = data.count;
  btn.classList.toggle('liked', data.liked);
  const icon = btn.querySelector('.icon');
  if (icon) icon.textContent = data.liked ? '❤️' : '🤍';
}

// ── Follow toggle ──
async function toggleFollow(username, btn) {
  const res = await fetch(`/profile/${username}/follow/`, { method: 'POST', headers: { 'X-CSRFToken': csrf() } });
  const data = await res.json();
  if (data.following) {
    btn.textContent = 'Following';
    btn.classList.add('following');
  } else {
    btn.textContent = 'Follow';
    btn.classList.remove('following');
  }
  const countEl = document.getElementById('followers-count');
  if (countEl) countEl.textContent = data.followers_count;
  showToast(data.following ? `Following @${username}` : `Unfollowed @${username}`);
}

// ── Comment submit ──
async function submitComment(postId, input, listEl, countEl) {
  const content = input.value.trim();
  if (!content) return;
  const fd = new FormData();
  fd.append('content', content);
  fd.append('csrfmiddlewaretoken', csrf());
  const res = await fetch(`/post/${postId}/comment/`, { method: 'POST', body: fd });
  const data = await res.json();
  if (data.success) {
    input.value = '';
    if (listEl) {
      const div = document.createElement('div');
      div.className = 'comment-item';
      div.innerHTML = `
        <div class="avatar avatar-sm">${data.username[0].toUpperCase()}</div>
        <div class="comment-body">
          <span class="comment-author">@${data.username}</span>
          <p class="comment-text">${data.content}</p>
          <span class="comment-time">just now</span>
        </div>`;
      listEl.appendChild(div);
    }
    if (countEl) countEl.textContent = parseInt(countEl.textContent || 0) + 1;
  }
}

// ── Delete post ──
async function deletePost(postId) {
  if (!confirm('Delete this post?')) return;
  const res = await fetch(`/post/${postId}/delete/`, { method: 'POST', headers: { 'X-CSRFToken': csrf() } });
  const data = await res.json();
  if (data.success) {
    const el = document.getElementById(`post-${postId}`);
    if (el) { el.style.opacity = '0'; el.style.transition = 'opacity 0.3s'; setTimeout(() => el.remove(), 300); }
    showToast('Post deleted');
  }
}

// ── Compose modal ──
function openCompose() {
  document.getElementById('compose-modal')?.classList.add('open');
  document.getElementById('compose-textarea')?.focus();
}

function closeCompose() {
  document.getElementById('compose-modal')?.classList.remove('open');
}

// ── Char counter ──
function updateCharCount(textarea, counterId, max = 500) {
  const el = document.getElementById(counterId);
  if (!el) return;
  const len = textarea.value.length;
  el.textContent = max - len;
  el.className = 'char-count' + (len > max - 50 ? ' warn' : '') + (len > max ? ' over' : '');
}

// ── Dropdown menu ──
function toggleMenu(id) {
  const d = document.getElementById(id);
  if (!d) return;
  d.classList.toggle('open');
}

document.addEventListener('click', e => {
  if (!e.target.closest('.post-menu')) {
    document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
  }
});

// ── Image URL preview toggle ──
function toggleImageInput(btn) {
  const row = document.getElementById('image-url-row');
  if (!row) return;
  row.style.display = row.style.display === 'none' ? 'flex' : 'none';
  btn.style.opacity = row.style.display === 'none' ? '1' : '0.5';
}
