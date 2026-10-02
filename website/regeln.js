/* Rules page: the table of contents stays open as a sticky column on wide
   screens and folds away on narrow ones; the chapter being read is marked.
   The PDF menu in the intro closes like the site's menus. */
(() => {
  'use strict';
  const pane = document.querySelector('.rules-toc');
  const toc = pane.querySelector('details');
  const links = new Map([...pane.querySelectorAll('a')].map((a) => [a.hash.slice(1), a]));
  const chapters = [...document.querySelectorAll('.rules-body section[id]')];
  const wide = window.matchMedia('(min-width: 901px)');

  const fitToc = () => { toc.open = wide.matches; };
  fitToc();
  wide.addEventListener('change', fitToc);
  toc.querySelector('summary').addEventListener('click', (event) => { if (wide.matches) event.preventDefault(); });
  links.forEach((link) => link.addEventListener('click', () => { if (!wide.matches) toc.open = false; }));

  let current = null;
  function markChapter() {
    const header = document.querySelector('.site-header').offsetHeight;
    const atEnd = window.innerHeight + window.scrollY >= document.documentElement.scrollHeight - 2;
    let active = atEnd ? chapters[chapters.length - 1] : null;
    if (!active) {
      for (const chapter of chapters) {
        if (chapter.getBoundingClientRect().top > header + 48) break;
        active = chapter;
      }
    }
    const link = active && links.get(active.id);
    if (link === current) return;
    current?.removeAttribute('aria-current');
    current = link;
    if (!link) return;
    link.setAttribute('aria-current', 'true');
    if (wide.matches && pane.scrollHeight > pane.clientHeight) {
      const top = link.offsetTop;
      if (top < pane.scrollTop || top + link.offsetHeight > pane.scrollTop + pane.clientHeight) {
        pane.scrollTop = top - pane.clientHeight / 2;
      }
    }
  }

  /* The PDF menu next to the Markdown button: a <details>, closed again by a
     click outside, Escape or picking a file. */
  const pdfMenu = document.getElementById('pdf-menu');
  if (pdfMenu) {
    const close = () => { pdfMenu.open = false; };
    document.addEventListener('click', (event) => { if (pdfMenu.open && !pdfMenu.contains(event.target)) close(); });
    document.addEventListener('keydown', (event) => {
      if (event.key !== 'Escape' || !pdfMenu.open) return;
      close();
      pdfMenu.querySelector('summary').focus();
    });
    pdfMenu.querySelectorAll('a').forEach((link) => link.addEventListener('click', close));
  }

  let queued = false;
  window.addEventListener('scroll', () => {
    if (queued) return;
    queued = true;
    requestAnimationFrame(() => { queued = false; markChapter(); });
  }, { passive: true });
  markChapter();
})();
