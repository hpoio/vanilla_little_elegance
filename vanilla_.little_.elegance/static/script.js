// ===== VANILLA ELEGANCE — MAIN SCRIPT =====
const CART_KEY = 'vanilla_elegance_cart';

function getCart() {
  try { return JSON.parse(localStorage.getItem(CART_KEY)) || []; } catch { return []; }
}
function saveCart(cart) { localStorage.setItem(CART_KEY, JSON.stringify(cart)); }

function updateCartUI() {
  const cart = getCart();
  const total = cart.reduce((s, i) => s + i.price * i.quantity, 0);
  const count = cart.reduce((s, i) => s + i.quantity, 0);

  const badge = document.getElementById('cart-badge');
  const header = document.getElementById('cart-count-header');
  const totalEl = document.getElementById('cart-total-price');

  if (badge) { badge.textContent = count; badge.classList.toggle('visible', count > 0); }
  if (header) header.textContent = count + (count === 1 ? ' item' : ' items');
  if (totalEl) totalEl.textContent = total.toLocaleString() + ' DA';

  renderCartItems();
}

function renderCartItems() {
  const cart = getCart();
  const container = document.getElementById('cart-items-container');
  const empty = document.getElementById('cart-empty-state');
  const footer = document.getElementById('cart-footer');
  if (!container) return;

  if (cart.length === 0) {
    container.innerHTML = '';
    if (empty) empty.style.display = 'block';
    if (footer) footer.style.display = 'none';
    return;
  }
  if (empty) empty.style.display = 'none';
  if (footer) footer.style.display = 'block';

  container.innerHTML = cart.map(item => `
    <div class="cart-item">
      <img src="/static/${item.image}" class="cart-item-img" alt="${item.name}" onerror="this.src='/static/placeholder.jpg'">
      <div class="cart-item-info">
        <div class="cart-item-name">${item.name}</div>
        <div class="cart-item-price">${(item.price * item.quantity).toLocaleString()} DA</div>
        <div class="cart-item-qty">
          <button class="qty-btn" onclick="changeQty(${item.id}, -1)">−</button>
          <span>${item.quantity}</span>
          <button class="qty-btn" onclick="changeQty(${item.id}, 1)">+</button>
        </div>
      </div>
      <button class="cart-item-remove" onclick="removeItem(${item.id})" title="Remove"><i class="fas fa-trash-alt"></i></button>
    </div>
  `).join('');
}

function addToCart(id, name, price, image, gender) {
  const cart = getCart();
  const existing = cart.find(i => i.id === id);
  if (existing) { existing.quantity++; }
  else { cart.push({ id, name, price: parseInt(price), image, gender, quantity: 1 }); }
  saveCart(cart);
  updateCartUI();
  openCart();
  showAddedFeedback(id);
}

function changeQty(id, delta) {
  let cart = getCart();
  const item = cart.find(i => i.id === id);
  if (!item) return;
  item.quantity += delta;
  if (item.quantity <= 0) cart = cart.filter(i => i.id !== id);
  saveCart(cart);
  updateCartUI();
}

function removeItem(id) {
  saveCart(getCart().filter(i => i.id !== id));
  updateCartUI();
}

function openCart() {
  document.getElementById('cart-sidebar')?.classList.add('open');
  document.getElementById('cart-overlay')?.classList.add('open');
  document.body.style.overflow = 'hidden';
}

function closeCart() {
  document.getElementById('cart-sidebar')?.classList.remove('open');
  document.getElementById('cart-overlay')?.classList.remove('open');
  document.body.style.overflow = '';
}

function showAddedFeedback(id) {
  const btn = document.querySelector(`[data-id="${id}"]`);
  if (!btn) return;
  const orig = btn.innerHTML;
  btn.innerHTML = '<i class="fas fa-check"></i> Added!';
  btn.style.opacity = '0.7';
  setTimeout(() => { btn.innerHTML = orig; btn.style.opacity = ''; }, 1500);
}

// Particles
function createParticles() {
  const container = document.querySelector('.particles');
  if (!container) return;
  for (let i = 0; i < 25; i++) {
    const p = document.createElement('div');
    p.className = 'particle';
    p.style.left = Math.random() * 100 + '%';
    p.style.animationDuration = (8 + Math.random() * 12) + 's';
    p.style.animationDelay = (Math.random() * 10) + 's';
    p.style.width = p.style.height = (1 + Math.random() * 3) + 'px';
    p.style.opacity = Math.random() * 0.5;
    container.appendChild(p);
  }
}

// Scroll reveal
function initReveal() {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => { if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); } });
  }, { threshold: 0.1 });
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
}

// Navbar scroll effect
function initNavbar() {
  const nav = document.querySelector('.navbar');
  if (!nav) return;
  window.addEventListener('scroll', () => {
    nav.style.background = window.scrollY > 50
      ? 'rgba(10,14,26,0.97)' : 'rgba(10,14,26,0.85)';
  });
}

// Hamburger
function initHamburger() {
  const btn = document.querySelector('.nav-hamburger');
  const links = document.querySelector('.nav-links');
  if (!btn || !links) return;
  btn.addEventListener('click', () => links.classList.toggle('open'));
  document.addEventListener('click', e => {
    if (!btn.contains(e.target) && !links.contains(e.target)) links.classList.remove('open');
  });
}

document.addEventListener('DOMContentLoaded', () => {
  createParticles();
  initReveal();
  initNavbar();
  initHamburger();
  updateCartUI();

  // Close cart on overlay click
  document.getElementById('cart-overlay')?.addEventListener('click', closeCart);

  // Escape key
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeCart(); });
});
