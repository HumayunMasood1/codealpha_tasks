// Cart badge update
async function updateBadge() {
  const res = await fetch('/cart/count/');
  const data = await res.json();
  const badge = document.getElementById('cart-badge');
  if (badge) {
    badge.textContent = data.count;
    badge.style.display = data.count > 0 ? 'flex' : 'none';
  }
}

// Toast notification
function showToast(msg) {
  const container = document.getElementById('toast-container') ||
    (() => { const d = document.createElement('div'); d.id = 'toast-container'; d.className = 'toast-container'; document.body.appendChild(d); return d; })();
  const t = document.createElement('div');
  t.className = 'toast';
  t.textContent = msg;
  container.appendChild(t);
  setTimeout(() => t.remove(), 3000);
}

// Add to cart
async function addToCart(productId, btn) {
  if (btn) { btn.disabled = true; btn.textContent = 'Adding...'; }
  const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
  const res = await fetch(`/cart/add/${productId}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken }
  });
  const data = await res.json();
  if (data.success) {
    showToast('✓ Added to cart!');
    updateBadge();
  }
  if (btn) { btn.disabled = false; btn.textContent = 'Add to Cart'; }
}

// Cart page: update quantity
async function updateQty(productId, qty) {
  const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
  await fetch(`/cart/update/${productId}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
    body: JSON.stringify({ quantity: qty })
  });
  location.reload();
}

// Cart page: remove item
async function removeItem(productId) {
  const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
  await fetch(`/cart/remove/${productId}/`, {
    method: 'POST',
    headers: { 'X-CSRFToken': csrfToken }
  });
  location.reload();
}

// Product detail qty
let qty = 1;
function changeQty(delta) {
  qty = Math.max(1, qty + delta);
  const el = document.getElementById('qty-display');
  if (el) el.textContent = qty;
}

async function addToCartWithQty(productId) {
  const csrfToken = document.cookie.match(/csrftoken=([^;]+)/)?.[1] || '';
  for (let i = 0; i < qty; i++) {
    await fetch(`/cart/add/${productId}/`, {
      method: 'POST',
      headers: { 'X-CSRFToken': csrfToken }
    });
  }
  showToast(`✓ Added ${qty} item${qty > 1 ? 's' : ''} to cart!`);
  updateBadge();
}

document.addEventListener('DOMContentLoaded', () => {
  updateBadge();
});
