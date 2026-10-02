/* Home page: the current menu entry and the mythic foil.
   Navigation lives in site.js. */
(() => {
  'use strict';
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];

  /* ---------- active menu entry: the section at the reading line ----------
     One line below the header decides it: the section it stands in is the current one,
     and its menu door is marked with it. A single line can only ever be inside one
     section, so nothing stays lit after jumping from anchor to anchor. Above the first
     section, and inside a section that has no menu entry of its own, nothing is marked. */
  const sectionLinks = $$('#site-nav a[href^="#"]')
    .map((link) => ({ link, section: document.getElementById(link.getAttribute('href').slice(1)) }))
    .filter((entry) => entry.section);

  if (sectionLinks.length) {
    const header = $('.site-header');
    const doors = [...new Set(sectionLinks.map(({ link }) => link.closest('.nav-group')))].filter(Boolean);
    let scheduled = false;

    function markSection() {
      scheduled = false;
      const line = (header ? header.offsetHeight : 0) + window.innerHeight * 0.3;
      const here = sectionLinks.find(({ section }) => {
        const box = section.getBoundingClientRect();
        return box.top <= line && box.bottom > line;
      });
      sectionLinks.forEach(({ link }) => {
        const active = here && link === here.link;
        link.classList.toggle('active', Boolean(active));
        if (active) link.setAttribute('aria-current', 'location');
        else link.removeAttribute('aria-current');
      });
      doors.forEach((door) => {
        door.querySelector('.nav-top').classList.toggle('active', Boolean(here) && door.contains(here.link));
      });
    }

    function scheduleMark() {
      if (scheduled) return;
      scheduled = true;
      requestAnimationFrame(markSection);
    }
    window.addEventListener('scroll', scheduleMark, { passive: true });
    window.addEventListener('resize', scheduleMark);
    markSection();
  }

  /* ---------- mythic foil: an easter egg ----------
     The mythic lies face down and turns over only when someone clicks it.
     Without JavaScript it lies face up. */
  const relic = $('#relic');
  const relicButton = $('.relic-rotation', relic);
  function setRelicFront(front) {
    relic.classList.toggle('is-front', front);
    relicButton.setAttribute('aria-pressed', String(front));
  }
  relicButton.addEventListener('click', () => setRelicFront(!relic.classList.contains('is-front')));
  setRelicFront(false);
})();
