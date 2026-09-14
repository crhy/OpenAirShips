const page = document.body.dataset.page || '';
const navItems = [
  ['home', '/', 'Home'], ['plan', '/plan', 'Plan'], ['involved', '/get-involved', 'Get Involved'],
  ['faq', '/faq', 'FAQ'], ['team', '/team', 'Team'], ['hindenburg', '/hindenburg', 'Hindenburg'],
  ['open-source', '/open-source', 'Open Source'], ['alberto', '/alberto', 'Alberto'], ['contact', '/contact', 'Contact']
];
const navLink = ([key, href, label]) => `<a href="${href}"${page === key ? ' aria-current="page"' : ''}>${label}</a>`;

const headerMount = document.querySelector('[data-site-header]');
if (headerMount) headerMount.innerHTML = `
  <header class="site-header${page === 'home' ? '' : ' solid'}">
    <div class="shell nav-bar">
      <a class="brand" href="/" aria-label="OpenAirShips.com"><img src="/assets/images/new-logo-2026.png" alt="OpenAirShips.com" width="136" height="68"></a>
      <nav class="desktop-nav">${navItems.map(navLink).join('')}</nav>
      <button class="menu-toggle" type="button" aria-expanded="false" aria-label="OpenAirShips.com"><span></span></button>
    </div>
    <nav class="mobile-panel">${navItems.map(navLink).join('')}</nav>
  </header>`;

const footerMount = document.querySelector('[data-site-footer]');
if (footerMount) footerMount.innerHTML = `<footer class="site-footer"><div class="shell footer-original"><a href="/">OpenAirShips.com</a></div></footer>`;

const header = document.querySelector('.site-header');
const menuButton = document.querySelector('.menu-toggle');
function updateHeader() {
  if (!header || page !== 'home') return;
  header.classList.toggle('scrolled', window.scrollY > 24);
}
updateHeader();
window.addEventListener('scroll', updateHeader, { passive: true });
if (menuButton) {
  menuButton.addEventListener('click', () => {
    const open = document.body.classList.toggle('menu-open');
    menuButton.setAttribute('aria-expanded', String(open));
  });
  document.querySelectorAll('.mobile-panel a').forEach((link) => link.addEventListener('click', () => {
    document.body.classList.remove('menu-open');
    menuButton.setAttribute('aria-expanded', 'false');
  }));
}

document.querySelectorAll('[data-contact-form]').forEach((form) => {
  form.addEventListener('submit', (event) => {
    event.preventDefault();
    const data = new FormData(form);
    const name = `${data.get('first') || ''} ${data.get('last') || ''}`.trim();
    const subject = name ? `OpenAirShips contact from ${name}` : 'OpenAirShips contact';
    const body = `Name: ${name}\nEmail: ${data.get('email') || ''}\n\n${data.get('comment') || ''}`;
    window.location.href = `mailto:rhy@leperkhanz.com?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;
  });
});

const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
const reveals = document.querySelectorAll('.reveal');
if (reduceMotion || !('IntersectionObserver' in window)) reveals.forEach((el) => el.classList.add('visible'));
else {
  const observer = new IntersectionObserver((entries) => entries.forEach((entry) => {
    if (entry.isIntersecting) { entry.target.classList.add('visible'); observer.unobserve(entry.target); }
  }), { threshold: .12 });
  reveals.forEach((el) => observer.observe(el));
}
