/* Card collection: search, filters and the detail dialog. karten.html#KAT-C03
   opens that card directly; the rules page links card names this way. */
(() => {
  'use strict';
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const cards = window.CARDS || [];
  const normalize = (value) => String(value || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase();
  const rarityName = (value) => ({ common: 'Common', uncommon: 'Uncommon', rare: 'Rare', mythic: 'Mythic' }[value] || value);
  const domainName = (value) => ({ team: 'Team', data: 'Daten', operations: 'Betrieb', methods: 'Methode', neutral: 'Neutral' }[value] || value);

  const grid = $('#card-grid');
  const searchInput = $('#card-search');
  const rarityFilter = $('#rarity-filter');
  const domainFilter = $('#domain-filter');
  const results = $('#gallery-results');
  const detail = $('#card-detail');
  let currentCard = null;
  let showArt = false;

  function renderGallery() {
    const term = normalize(searchInput.value.trim());
    const rarity = rarityFilter.value;
    const domain = domainFilter.value;
    const matches = cards.filter((card) =>
      (rarity === 'all' || card.rarity === rarity) &&
      (domain === 'all' || card.domain_primary === domain) &&
      normalize([card.name, card.card_id, card.card_type, card.rules_text, card.flavor_text, card.domain_primary, card.editorial_tags].join(' ')).includes(term)
    );
    const fragment = document.createDocumentFragment();
    for (const card of matches) {
      const tile = document.createElement('button');
      tile.type = 'button';
      tile.className = 'card-tile';
      tile.id = card.card_id;
      tile.setAttribute('aria-label', `${card.name}, ${rarityName(card.rarity)}, Karte ansehen`);
      const image = document.createElement('img');
      image.src = `assets/cards/${card.card_id}.webp`;
      image.alt = '';
      image.loading = 'lazy';
      image.decoding = 'async';
      const title = document.createElement('strong');
      title.textContent = card.name;
      const meta = document.createElement('span');
      meta.textContent = `${card.card_id} · ${rarityName(card.rarity)}`;
      tile.append(image, title, meta);
      tile.addEventListener('click', () => openDetail(card));
      fragment.append(tile);
    }
    if (!matches.length) {
      const message = document.createElement('p');
      message.className = 'gallery-empty';
      message.textContent = 'Keine Karte passt zu dieser Suche.';
      fragment.append(message);
    }
    grid.replaceChildren(fragment);
    results.textContent = `${matches.length} / ${cards.length} Karten`;
  }

  function setDetailImage() {
    $('#detail-image').src = `assets/${showArt ? 'art' : 'cards'}/${currentCard.card_id}.webp`;
    $('#detail-image').alt = `${showArt ? 'Illustration: ' : ''}${currentCard.name}`;
    $('#art-toggle').textContent = showArt ? 'Zur Karte zurück ↙' : 'Illustration ansehen ↗';
    $('#art-toggle').setAttribute('aria-pressed', String(showArt));
  }

  function openDetail(card) {
    currentCard = card;
    showArt = false;
    $('#detail-title').textContent = card.name;
    $('#detail-meta').textContent = `${card.card_id} · ${rarityName(card.rarity)} · ${card.card_type} · ${domainName(card.domain_primary)}`;
    $('#detail-rule').textContent = card.rules_text || '';
    $('#detail-flavor').textContent = card.flavor_text || '';
    $('#detail-flavor').hidden = !card.flavor_text;
    $('#detail-generator').href = `generator.html?vorlage=${encodeURIComponent(card.card_id)}`;
    setDetailImage();
    if (location.hash !== `#${card.card_id}`) history.replaceState(null, '', `#${card.card_id}`);
    if (!detail.open) detail.showModal();
  }

  function cardFromHash() {
    const id = decodeURIComponent(location.hash.slice(1));
    return cards.find((card) => card.card_id === id);
  }

  $('#art-toggle').addEventListener('click', () => { showArt = !showArt; setDetailImage(); });
  detail.querySelectorAll('[data-close]').forEach((btn) => btn.addEventListener('click', () => detail.close()));
  detail.addEventListener('click', (event) => { if (event.target === detail) detail.close(); });
  detail.addEventListener('close', () => {
    if (location.hash) history.replaceState(null, '', location.pathname + location.search);
  });
  window.addEventListener('hashchange', () => {
    const card = cardFromHash();
    if (card) openDetail(card);
  });

  searchInput.addEventListener('input', renderGallery);
  rarityFilter.addEventListener('change', renderGallery);
  domainFilter.addEventListener('change', renderGallery);
  renderGallery();

  const requested = cardFromHash();
  if (requested) openDetail(requested);
})();
