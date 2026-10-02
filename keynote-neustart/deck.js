(() => {
  'use strict';
  const $ = (selector) => document.querySelector(selector);
  const slides = [...document.querySelectorAll('.slide')];
  let index = 0;
  let touch = null;
  let swiped = false;

  function fit() {
    const stage = $('#stage');
    const factor = Math.min(stage.clientWidth / 1600, stage.clientHeight / 900);
    $('#canvas').style.transform = `translate(-50%, -50%) scale(${factor})`;
  }

  function paintStep(slide, step) {
    slide.dataset.step = String(step);
    if (slide.classList.contains('opening')) {
      slide.querySelectorAll('.opening-copy, .opening-product, .opening-subtitle').forEach((part) => {
        part.inert = step === 0;
        part.setAttribute('aria-hidden', String(step === 0));
      });
    }
    if (slide.classList.contains('genesis')) {
      // Schritt 1 enthüllt das andere Bingo samt Stempel; Schritt 2 zeigt die Karten.
      const pivot = step > 1 ? 1 : 0;
      slide.querySelectorAll('[data-genesis-state]').forEach((part) => {
        const visible = Number(part.dataset.genesisState) === pivot;
        part.inert = !visible;
        part.setAttribute('aria-hidden', String(!visible));
      });
      slide.querySelectorAll('[data-genesis-reveal]').forEach((part) => {
        part.hidden = step === 0;
      });
      slide.querySelectorAll('[data-genesis-step]').forEach((part) => {
        part.hidden = Number(part.dataset.genesisStep) > step;
      });
      slide.querySelector('.idea-stamp').setAttribute('aria-hidden', String(step === 0));
      slide.querySelector('.bingo-proposal').setAttribute('aria-hidden', String(pivot > 0));
    }
    if (slide.classList.contains('project')) {
      // Schritt 0 zeigt nur die Regeln; das Beispiel folgt ab Schritt 1.
      const example = slide.querySelector('.project-example');
      example.inert = step === 0;
      example.setAttribute('aria-hidden', String(step === 0));
      slide.querySelectorAll('[data-turn-step]').forEach((part) => {
        part.hidden = Number(part.dataset.turnStep) > step;
      });
    }
    if (slide.classList.contains('synergy')) {
      slide.querySelectorAll('.shared-factor, .shared-caption').forEach((part) => part.setAttribute('aria-hidden', String(step === 0)));
      slide.querySelectorAll('[data-shared-status]').forEach((status) => {
        status.textContent = step === 0 ? 'offen' : '✓';
        status.setAttribute('aria-label', step === 0 ? 'offen' : 'erfüllt');
      });
    }
    if (slide.classList.contains('miracle')) {
      slide.querySelector('.relic-front').setAttribute('aria-hidden', String(step === 0));
      slide.querySelector('.relic-back').setAttribute('aria-hidden', String(step > 0));
    }
  }

  function refresh() {
    slides.forEach((slide, i) => {
      const active = i === index;
      slide.classList.toggle('active', active);
      slide.inert = !active;
      slide.setAttribute('aria-hidden', String(!active));
    });
    const slide = slides[index];
    const step = Number(slide.dataset.step);
    $('#overview-list').querySelectorAll('button').forEach((button, i) => {
      if (i === index) button.setAttribute('aria-current', 'step');
      else button.removeAttribute('aria-current');
    });
    $('#announcement').textContent = `Folie ${index + 1} von ${slides.length}: ${slide.dataset.title}${step ? ', Pointe enthüllt' : ''}`;
    fit();
  }

  function navigate(target, step = 0, updateHash = true) {
    const old = slides[index];
    const moveFocus = old.contains(document.activeElement);
    index = Math.max(0, Math.min(slides.length - 1, target));
    paintStep(slides[index], Math.min(step, Number(slides[index].dataset.steps || 0)));
    refresh();
    if (updateHash && location.hash !== `#${index + 1}`) location.hash = String(index + 1);
    if (moveFocus) {
      slides[index].tabIndex = -1;
      slides[index].focus({preventScroll:true});
    }
  }

  function forward() {
    const slide = slides[index];
    const step = Number(slide.dataset.step);
    if (step < Number(slide.dataset.steps || 0)) {
      paintStep(slide, step + 1);
      refresh();
    } else if (index < slides.length - 1) navigate(index + 1);
  }

  function backward() {
    const step = Number(slides[index].dataset.step);
    if (step) { paintStep(slides[index], step - 1); refresh(); }
    else if (index > 0) navigate(index - 1, Number(slides[index - 1].dataset.steps || 0));
  }

  function hashNavigation() {
    const match = location.hash.match(/^#(\d+)$/);
    const target = Math.max(0, Math.min(slides.length - 1, match ? Number(match[1]) - 1 : 0));
    // Ignore hash events caused by our own navigation so an immediate reveal is preserved.
    if (target !== index) navigate(target, 0, false);
  }

  function open(dialog) {
    if (dialog.open) return;
    dialog.showModal();
  }
  function close(dialog) { if (dialog.open) dialog.close(); }
  function toggle(dialog) { dialog.open ? close(dialog) : open(dialog); }


  slides.forEach((slide, i) => {
    const button = document.createElement('button');
    const number = document.createElement('span'); number.textContent = String(i + 1).padStart(2, '0');
    button.append(number, document.createTextNode(slide.dataset.title));
    button.addEventListener('click', () => { close($('#overview')); navigate(i); });
    $('#overview-list').append(button);
    paintStep(slide,0);
  });
  document.querySelectorAll('[data-close]').forEach((button) => button.addEventListener('click', () => close(button.closest('dialog'))));
  document.querySelectorAll('dialog').forEach((dialog) => dialog.addEventListener('click', (event) => {
    if (event.target !== dialog) return;
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) close(dialog);
  }));
  document.addEventListener('keydown', (event) => {
    if (event.ctrlKey || event.metaKey || event.altKey || event.isComposing) return;
    const key = event.key.toLowerCase();
    const dialogs = [...document.querySelectorAll('dialog[open]')];
    if (key === 'escape') {
      if (dialogs.length) { event.preventDefault(); close(dialogs.at(-1)); }
      return;
    }
    if (dialogs.length || event.target.closest('input,select,textarea,[contenteditable="true"]')) return;
    if (key === ' ' && event.target.closest('button,a')) return;
    const actions = {arrowright:forward,pagedown:forward,' ':forward,arrowleft:backward,pageup:backward,home:()=>navigate(0),end:()=>navigate(slides.length-1),o:()=>toggle($('#overview'))};
    if (actions[key]) { event.preventDefault(); actions[key](); }
  });
  $('#canvas').addEventListener('touchstart', (event) => {
    touch = event.touches.length === 1 && !event.target.closest('button,a') ? {x:event.touches[0].clientX,y:event.touches[0].clientY} : null;
  }, {passive:true});
  $('#canvas').addEventListener('touchend', (event) => {
    if (!touch || !event.changedTouches.length) return;
    const dx = event.changedTouches[0].clientX - touch.x;
    const dy = event.changedTouches[0].clientY - touch.y;
    touch = null;
    if (Math.abs(dx) > 55 && Math.abs(dx) > Math.abs(dy) * 1.5) {
      // Nach einem Wisch folgt auf manchen Geraeten noch ein Klick; der darf nicht doppelt blaettern.
      swiped = true;
      setTimeout(() => { swiped = false; }, 400);
      dx < 0 ? forward() : backward();
    }
  }, {passive:true});
  $('#canvas').addEventListener('touchcancel', () => { touch = null; }, {passive:true});
  // Klick auf die Buehne blaettert weiter; Schaltflaechen und Links behalten ihre eigene Funktion.
  $('#stage').addEventListener('click', (event) => {
    if (swiped) { swiped = false; return; }
    if (event.target.closest('button,a')) return;
    forward();
  });
  addEventListener('hashchange', hashNavigation);
  addEventListener('resize', fit);
  document.addEventListener('fullscreenchange', fit);
  new ResizeObserver(fit).observe($('#stage'));
  hashNavigation(); refresh();
})();
