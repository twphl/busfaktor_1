/* Shared by every page: the menu (drop-downs, mobile panel). Nothing on the
   site moves on scroll; every section stands in its final state. */
(() => {
  'use strict';
  const toggle = document.getElementById('nav-toggle');
  const nav = document.getElementById('site-nav');

  function setOpen(open) {
    nav.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', String(open));
  }
  toggle.addEventListener('click', () => setOpen(!nav.classList.contains('open')));
  nav.querySelectorAll('a').forEach((link) => link.addEventListener('click', () => setOpen(false)));

  /* Menu groups: drop-downs on wide screens, open lists inside the mobile panel. */
  const groups = [...nav.querySelectorAll('.nav-group')];
  const wide = window.matchMedia('(min-width:1001px)');

  function setGroup(group, open) {
    group.classList.toggle('open', open);
    group.querySelector('.nav-top').setAttribute('aria-expanded', String(open));
  }
  function closeGroups(except) {
    groups.forEach((group) => { if (group !== except) setGroup(group, false); });
  }
  groups.forEach((group) => {
    const button = group.querySelector('.nav-top');
    button.addEventListener('click', () => {
      const open = !group.classList.contains('open');
      closeGroups(group);
      setGroup(group, open);
    });
  });
  document.addEventListener('click', (event) => {
    if (!event.target.closest('.nav-group')) closeGroups();
  });
  document.addEventListener('keydown', (event) => {
    if (event.key !== 'Escape') return;
    const open = groups.find((group) => group.classList.contains('open'));
    if (!open) return;
    closeGroups();
    open.querySelector('.nav-top').focus();
  });
  /* Narrow screens have no room to hover a menu open, so the lists start open there. */
  const layout = () => groups.forEach((group) => setGroup(group, !wide.matches));
  wide.addEventListener('change', layout);
  layout();
})();
