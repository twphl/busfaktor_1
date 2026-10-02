/* Busfaktor: 1 — card generator.
 *
 * Collects a card from the form, renders it with renderer.js and exports
 * PNG, print PNG, SVG and a CSV row with the columns of data/cards.csv.
 * Rules text is assembled from the building blocks of the community form
 * (docs/11-community-expansion.md) unless the person switches to free text.
 */
(() => {
  'use strict';

  const R = window.BusfaktorRenderer;
  const LAYOUT = R.data.layout;
  const CARDS = window.CARDS || [];
  const $ = (selector, scope = document) => scope.querySelector(selector);
  const $$ = (selector, scope = document) => [...scope.querySelectorAll(selector)];

  const STORAGE_KEY = 'busfaktor-kartengenerator-v1';
  const FAMILIES = ['team', 'data', 'operations', 'methods'];
  const WORDS = {
    team: { label: 'Team', stem: 'Team-', requirement: 'Team-Anforderung', factor: 'Teamfaktor', factors: 'Teamfaktoren' },
    data: { label: 'Daten', stem: 'Daten-', requirement: 'Daten-Anforderung', factor: 'Datenfaktor', factors: 'Datenfaktoren' },
    operations: { label: 'Betrieb', stem: 'Betriebs-', requirement: 'Betriebs-Anforderung', factor: 'Betriebsfaktor', factors: 'Betriebsfaktoren' },
    methods: { label: 'Methode', stem: 'Methoden-', requirement: 'Methoden-Anforderung', factor: 'Methodenfaktor', factors: 'Methodenfaktoren' },
  };
  const COUNT_WORDS = ['', 'einen', 'zwei', 'drei', 'vier'];

  // Short meanings as on the table sign (docs/community/tischaushang.html).
  const TEMPLATES = {
    E1: { hint: 'oberste Karten ansehen, eine davon nehmen', targets: 'none', polarity: 'positive' },
    E2: { hint: 'gezielt Projektfaktoren nachziehen', targets: 'none', polarity: 'positive' },
    E3: { hint: 'einen Faktor aus der offenen Ablage holen', targets: 'none', polarity: 'positive' },
    E4: { hint: 'angelegte Faktoren zwischen Projekten verschieben', targets: 'none', polarity: 'ambivalent' },
    E5: { hint: 'das Ereignis selbst als beliebiger Faktor anlegen', targets: 'pair-or-any', polarity: 'positive' },
    E6: { hint: 'fremdes Projekt bekommt eine Anforderung dazu', targets: 'one-or-any', polarity: 'negative' },
    E7: { hint: 'einen angelegten Faktor auf die Hand zurückgeben', targets: 'pair', polarity: 'negative' },
    E8: { hint: 'ein störendes Ereignis verhindern', targets: 'none', polarity: 'positive' },
  };

  const DEFAULTS = {
    template: '',
    card_type: 'Projektfaktor',
    name: 'Passwort im Wiki',
    flavor_text: 'Damit es niemand vergisst. Auch sonst niemand.',
    factor_family: 'operations',
    joker_pair: ['team', 'methods'],
    effect_template: 'E6',
    targets: ['team'],
    domain_primary: 'operations',
    requirements: { team: 1, data: 0, operations: 1, methods: 0 },
    project_goal: 'Zwei Personen können den Dienst ohne Rückfrage neu starten, und die Zugangsdaten liegen im Passwortmanager.',
    free_rules: false,
    rules_text: '',
    visual_motif: '',
    card_id: 'KAT-X01',
    rarity: 'community',
    artwork: null,
    proof: false,
  };

  let state = structuredClone(DEFAULTS);
  let lastGood = null;
  let renderTimer = null;
  let paperArtwork = null;

  // Without an upload the window shows the flat paper of the blank cards
  // (scripts/render_blank_cards.py) instead of the print renderer's
  // internal "ILLUSTRATION FEHLT" placeholder.
  function paperField() {
    if (!paperArtwork) {
      const canvas = document.createElement('canvas');
      canvas.width = 300;
      canvas.height = 200;
      const context = canvas.getContext('2d');
      context.fillStyle = LAYOUT.colors['background/paper'].hex;
      context.fillRect(0, 0, canvas.width, canvas.height);
      paperArtwork = canvas.toDataURL('image/png');
    }
    return paperArtwork;
  }

  /* ---------- rules text from building blocks ---------- */

  const orPhrase = ([first, second], noun) => `${WORDS[first].stem} oder ${WORDS[second][noun]}`;

  function factorRules(current) {
    if (current.factor_family === 'wildcard') {
      return `Erfüllt wahlweise eine ${orPhrase(current.joker_pair, 'requirement')}.`;
    }
    return `Erfüllt eine ${WORDS[current.factor_family].requirement}.`;
  }

  function requirementList(current) {
    return FAMILIES.flatMap((family) => Array(current.requirements[family] || 0).fill(family));
  }

  function projectRules(current) {
    const parts = FAMILIES
      .filter((family) => current.requirements[family])
      .map((family) => {
        const count = current.requirements[family];
        return count === 1 ? `einen ${WORDS[family].factor}` : `${COUNT_WORDS[count]} ${WORDS[family].factors}`;
      });
    if (!parts.length) return 'Abschluss: Lege Projektfaktoren an.';
    const joined = parts.length === 1 ? parts[0] : `${parts.slice(0, -1).join(', ')} und ${parts[parts.length - 1]}`;
    return `Abschluss: Lege ${joined} an.`;
  }

  function eventRules(current) {
    const targets = current.targets.filter((target) => target !== 'any');
    const any = current.targets.includes('any') || !targets.length;
    switch (current.effect_template) {
      case 'E1':
        return 'Sieh dir die obersten drei Karten des Aktionsstapels an. Nimm eine davon auf die Hand. Lege die anderen in beliebiger Reihenfolge unter den Aktionsstapel.';
      case 'E2':
        return 'Decke nacheinander Karten vom Aktionsstapel auf, bis du zwei Projektfaktoren aufgedeckt hast. Nimm die beiden Projektfaktoren auf die Hand. Lege alle dabei aufgedeckten Ereignisse verdeckt auf den Verbrauchsstapel.';
      case 'E3':
        return 'Nimm einen Projektfaktor aus der offenen Ablage auf die Hand.';
      case 'E4':
        return 'Verschiebe einen angelegten Projektfaktor zwischen zwei deiner aktiven Projekte. Er muss am neuen Projekt eine offene Anforderung erfüllen.';
      case 'E5':
        if (any) return 'Lege dieses Ereignis an eines deiner aktiven Projekte. Es erfüllt eine offene Anforderung eines Faktortyps deiner Wahl.';
        return `Lege dieses Ereignis an eines deiner aktiven Projekte. Es erfüllt eine offene ${targets.length === 2 ? orPhrase(targets, 'requirement') : WORDS[targets[0]].requirement}.`;
      case 'E6':
        if (any) return 'Lege dieses Ereignis an ein aktives Projekt einer anderen Person. Diese Person wählt einen Faktortyp. Das Projekt erhält eine zusätzliche Anforderung dieses Typs. Dieses Ereignis wird beim Projektabschluss verbraucht.';
        return `Lege dieses Ereignis an ein aktives Projekt einer anderen Person. Das Projekt erhält eine zusätzliche ${WORDS[targets[0]].requirement}. Dieses Ereignis wird beim Projektabschluss verbraucht.`;
      case 'E7':
        if (!targets.length) return 'Wähle einen angelegten Projektfaktor. Gib ihn der kontrollierenden Person auf die Hand zurück.';
        return `Wähle einen angelegten ${targets.length === 2 ? orPhrase(targets, 'factor') : WORDS[targets[0]].factor}. Gib ihn der kontrollierenden Person auf die Hand zurück.`;
      case 'E8':
      default:
        return 'Spiele dieses Ereignis als Reaktion auf ein Ereignis mit Rückschlag. Dessen Effekt wird verhindert. Beide Ereignisse werden verbraucht.';
    }
  }

  function generatedRules(current) {
    if (current.card_type === 'Projekt') return projectRules(current);
    if (current.card_type === 'Ereignis') return eventRules(current);
    return factorRules(current);
  }

  function targetFamily(current) {
    const mode = TEMPLATES[current.effect_template].targets;
    if (mode === 'none') return '';
    if (current.targets.includes('any')) return mode === 'pair' ? '' : 'any';
    return FAMILIES.filter((family) => current.targets.includes(family)).join('+');
  }

  /* ---------- state → renderer row ---------- */

  function toCard(current) {
    const rules = current.free_rules ? current.rules_text : generatedRules(current);
    const card = {
      card_id: current.card_id.trim() || 'KAT-X01',
      name: current.name.trim(),
      domain_primary: '',
      rarity: current.rarity === 'community' ? '' : current.rarity,
      card_type: current.card_type,
      factor_family: '',
      target_family: '',
      polarity: '',
      effect_template: '',
      requirements: '',
      points: '',
      project_goal: '',
      rules_text: rules.trim(),
      flavor_text: current.flavor_text.trim(),
      visual_motif: current.visual_motif.trim(),
    };
    if (current.card_type === 'Projektfaktor') {
      card.factor_family = current.factor_family;
      card.domain_primary = current.factor_family === 'wildcard' ? 'neutral' : current.factor_family;
    } else if (current.card_type === 'Ereignis') {
      card.effect_template = current.effect_template;
      card.polarity = TEMPLATES[current.effect_template].polarity;
      card.target_family = targetFamily(current);
      card.domain_primary = card.target_family && card.target_family !== 'any' ? card.target_family.split('+')[0] : 'neutral';
    } else {
      const requirements = requirementList(current);
      card.domain_primary = current.domain_primary;
      card.requirements = requirements.join('+');
      card.points = String(requirements.length);
      card.project_goal = current.project_goal.trim();
    }
    return card;
  }

  /* ---------- rendering ---------- */

  const FIELD_MESSAGES = {
    name: 'Der Titel passt nicht in die Titelzeile. Bitte kürzer fassen.',
    flavor_text: 'Der Flavor Text ist zu lang. Er darf höchstens zwei Zeilen füllen.',
    rules_text: 'Der Regeltext ist zu lang für die Karte.',
    project_goal: 'Das Projektziel ist zu lang. Es darf höchstens vier Zeilen füllen.',
    requirements: 'Die Anforderungen passen nicht in die Typzeile.',
    target_family: 'Die Zielangabe ist zu lang für die Typzeile.',
    card_id: 'Die Kartennummer ist zu lang.',
  };

  function validate(card) {
    const problems = {};
    if (!card.name) problems.name = 'Die Karte braucht einen Titel.';
    if (!card.rules_text) problems.rules_text = 'Der Regeltext fehlt.';
    if (card.card_type === 'Projekt') {
      const count = card.requirements ? card.requirements.split('+').length : 0;
      if (count < 2 || count > 4) problems.requirements = 'Ein Projekt braucht zwei bis vier Anforderungen.';
      if (!card.project_goal) problems.project_goal = 'Das Projekt braucht ein Ziel.';
    }
    if (card.card_type === 'Projektfaktor' && card.factor_family === 'wildcard' && new Set(state.joker_pair).size !== 2) {
      problems.factor_family = 'Ein Joker nennt zwei verschiedene Faktortypen.';
    }
    return problems;
  }

  function showProblems(problems) {
    $$('.field-error').forEach((node) => { node.textContent = ''; });
    $$('[aria-invalid]').forEach((node) => node.removeAttribute('aria-invalid'));
    for (const [field, message] of Object.entries(problems)) {
      const slot = $(`#error-${field}`) || $('#error-rules_text');
      slot.textContent = message;
      const input = $(`#${field}`);
      if (input) input.setAttribute('aria-invalid', 'true');
    }
  }

  function render() {
    const card = toCard(state);
    const problems = validate(card);
    const status = $('#render-status');
    const frame = $('#preview');
    if (Object.keys(problems).length) {
      showProblems(problems);
      frame.classList.add('is-stale');
      status.textContent = 'Die Vorschau zeigt den letzten vollständigen Stand.';
      setExportsEnabled(false);
      return;
    }
    try {
      const svg = R.buildCardSvg(card, {
        artwork: { href: state.artwork || paperField() },
        rarityOverride: state.rarity === 'community' ? { label: 'COMMUNITY', marks: 0 } : null,
        proof: state.proof,
      });
      svg.setAttribute('role', 'img');
      svg.setAttribute('aria-label', `Vorschau: ${card.name}`);
      svg.removeAttribute('width');
      svg.removeAttribute('height');
      if (!state.proof) {
        const trim = R.data.profile.master_svg.rectangles.trim;
        svg.setAttribute('viewBox', `${trim.x} ${trim.y} ${trim.width} ${trim.height}`);
      }
      frame.classList.toggle('is-proof', state.proof);
      frame.replaceChildren(svg);
      frame.classList.remove('is-stale');
      showProblems({});
      status.textContent = '';
      lastGood = { card, svg };
      setExportsEnabled(true);
    } catch (error) {
      if (!(error instanceof R.RenderError)) throw error;
      const field = error.field || 'rules_text';
      showProblems({ [field]: FIELD_MESSAGES[field] || error.message });
      frame.classList.add('is-stale');
      status.textContent = lastGood ? 'Die Vorschau zeigt den letzten Stand, der auf die Karte passt.' : error.message;
      setExportsEnabled(false);
    }
  }

  function scheduleRender() {
    clearTimeout(renderTimer);
    renderTimer = setTimeout(render, 90);
    saveDraft();
  }

  function setExportsEnabled(enabled) {
    $$('[data-export]').forEach((button) => { button.disabled = !enabled; });
  }

  /* ---------- form ↔ state ---------- */

  function familyRadio(name, value, labelText, iconKey) {
    const label = document.createElement('label');
    label.className = 'choice family';
    const input = document.createElement('input');
    input.type = 'radio';
    input.name = name;
    input.value = value;
    const body = document.createElement('span');
    body.className = 'choice-body';
    const icon = document.createElement('img');
    icon.src = `assets/icons/${iconKey}.svg`;
    icon.alt = '';
    const text = document.createElement('b');
    text.textContent = labelText;
    body.append(icon, text);
    label.append(input, body);
    return label;
  }

  function chip(value, labelText, iconKey) {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'chip-toggle';
    button.dataset.value = value;
    button.setAttribute('aria-pressed', 'false');
    if (iconKey) {
      const icon = document.createElement('img');
      icon.src = `assets/icons/${iconKey}.svg`;
      icon.alt = '';
      button.append(icon);
    }
    button.append(labelText);
    return button;
  }

  function buildControls() {
    const templateSelect = $('#template');
    for (const [type, label] of [['Projektfaktor', 'Projektfaktoren'], ['Ereignis', 'Ereignisse'], ['Projekt', 'Projekte']]) {
      const group = document.createElement('optgroup');
      group.label = `Vorlage: ${label}`;
      CARDS.filter((card) => card.card_type === type).forEach((card) => {
        group.append(new Option(`${card.card_id} · ${card.name}`, card.card_id));
      });
      templateSelect.append(group);
    }

    const factorGroup = $('[data-family-radios="factor_family"]');
    FAMILIES.forEach((family) => factorGroup.append(familyRadio('factor_family', family, WORDS[family].label, family)));
    factorGroup.append(familyRadio('factor_family', 'wildcard', 'Joker', 'joker'));
    const jokerRow = document.createElement('div');
    jokerRow.className = 'chip-row joker-pair';
    jokerRow.setAttribute('role', 'group');
    jokerRow.setAttribute('aria-label', 'Zwei Faktortypen für den Joker');
    FAMILIES.forEach((family) => jokerRow.append(chip(family, WORDS[family].label, family)));
    factorGroup.after(jokerRow);
    const jokerError = document.createElement('span');
    jokerError.className = 'field-error';
    jokerError.id = 'error-factor_family';
    jokerRow.after(jokerError);

    const effectSelect = $('#effect_template');
    Object.entries(TEMPLATES).forEach(([key, template]) => {
      effectSelect.append(new Option(`${key} ${capitalize(LAYOUT.effect_templates[key].toLowerCase())} – ${template.hint}`, key));
    });

    const targetChips = $('#target-chips');
    FAMILIES.forEach((family) => targetChips.append(chip(family, WORDS[family].label, family)));
    targetChips.append(chip('any', 'Freie Wahl', 'joker'));

    const domainSelect = $('#domain_primary');
    FAMILIES.forEach((family) => domainSelect.append(new Option(WORDS[family].label, family)));

    const steppers = $('#requirement-steppers');
    FAMILIES.forEach((family) => {
      const row = document.createElement('div');
      row.className = 'stepper';
      row.dataset.family = family;
      row.innerHTML = `<span class="stepper-label"><img src="assets/icons/${family}.svg" alt="">${WORDS[family].label}</span>`
        + `<button type="button" data-step="-1" aria-label="${WORDS[family].label}: eine Anforderung weniger">−</button>`
        + '<output aria-live="polite">0</output>'
        + `<button type="button" data-step="1" aria-label="${WORDS[family].label}: eine Anforderung mehr">+</button>`;
      steppers.append(row);
    });
  }

  function capitalize(text) {
    return text.charAt(0).toUpperCase() + text.slice(1);
  }

  function syncForm() {
    $('#template').value = state.template;
    $$('input[name="card_type"]').forEach((input) => { input.checked = input.value === state.card_type; });
    $$('[data-for]').forEach((group) => { group.hidden = group.dataset.for !== state.card_type; });
    for (const field of ['name', 'flavor_text', 'project_goal', 'visual_motif', 'card_id']) $(`#${field}`).value = state[field];
    $('#rarity').value = state.rarity;
    $('#effect_template').value = state.effect_template;
    $('#domain_primary').value = state.domain_primary;
    $$('input[name="factor_family"]').forEach((input) => { input.checked = input.value === state.factor_family; });

    const jokerRow = $('.joker-pair');
    jokerRow.hidden = state.factor_family !== 'wildcard';
    $$('.chip-toggle', jokerRow).forEach((button) => button.setAttribute('aria-pressed', String(state.joker_pair.includes(button.dataset.value))));

    const mode = TEMPLATES[state.effect_template].targets;
    $('#target-field').hidden = mode === 'none';
    $$('#target-chips .chip-toggle').forEach((button) => {
      button.hidden = button.dataset.value === 'any' && mode === 'pair';
      button.setAttribute('aria-pressed', String(state.targets.includes(button.dataset.value)));
    });
    $('#target-hint').textContent = {
      none: 'Dieser Baustein nennt kein Ziel.',
      'pair-or-any': 'Ein oder zwei Faktortypen, oder freie Wahl beim Anlegen.',
      'one-or-any': 'Ein Faktortyp, oder die betroffene Person wählt.',
      pair: 'Ein oder zwei Faktortypen. Ohne Auswahl trifft es einen beliebigen Faktor.',
    }[mode];

    const total = requirementList(state).length;
    $$('#requirement-steppers .stepper').forEach((row) => {
      const count = state.requirements[row.dataset.family] || 0;
      $('output', row).textContent = String(count);
      $('[data-step="-1"]', row).disabled = count === 0;
      $('[data-step="1"]', row).disabled = total >= 4;
    });
    $('#requirements-total').textContent = `${total} · ${total} Punkte`;

    const rules = $('#rules_text');
    rules.readOnly = !state.free_rules;
    rules.value = state.free_rules ? state.rules_text : generatedRules(state);
    $('#free_rules').checked = state.free_rules;
    $('[data-field="rules_text"] .field-label').textContent = state.free_rules ? 'Frei formuliert' : 'Aus den Bausteinen';

    $('#artwork-clear').hidden = !state.artwork;
    $('#proof').checked = state.proof;
    updateCounters();
  }

  function updateCounters() {
    $$('[data-counter]').forEach((node) => {
      const length = Array.from($(`#${node.dataset.counter}`).value.trim()).length;
      const soft = Number(node.dataset.soft);
      node.textContent = `${length}/${soft}`;
      node.classList.toggle('is-over', length > soft);
    });
  }

  function bindForm() {
    const form = $('#card-form');
    form.addEventListener('submit', (event) => event.preventDefault());

    for (const field of ['name', 'flavor_text', 'project_goal', 'visual_motif', 'card_id']) {
      $(`#${field}`).addEventListener('input', (event) => {
        state[field] = event.target.value;
        updateCounters();
        scheduleRender();
      });
    }
    $('#rules_text').addEventListener('input', (event) => {
      if (!state.free_rules) return;
      state.rules_text = event.target.value;
      scheduleRender();
    });
    $('#free_rules').addEventListener('change', (event) => {
      state.free_rules = event.target.checked;
      if (state.free_rules && !state.rules_text.trim()) state.rules_text = generatedRules(state);
      syncForm();
      scheduleRender();
      if (state.free_rules) $('#rules_text').focus();
    });
    $$('input[name="card_type"]').forEach((input) => input.addEventListener('change', () => {
      state.card_type = input.value;
      state.free_rules = false;
      syncForm();
      scheduleRender();
    }));
    form.addEventListener('change', (event) => {
      if (event.target.name === 'factor_family') state.factor_family = event.target.value;
      else if (event.target.id === 'effect_template') {
        state.effect_template = event.target.value;
        const mode = TEMPLATES[state.effect_template].targets;
        if (mode === 'none') state.targets = [];
        else if (mode === 'pair' && state.targets.includes('any')) state.targets = [];
        else if (!state.targets.length) state.targets = mode === 'pair' ? ['team'] : ['any'];
      } else if (event.target.id === 'domain_primary') state.domain_primary = event.target.value;
      else if (event.target.id === 'rarity') state.rarity = event.target.value;
      else if (event.target.id === 'proof') state.proof = event.target.checked;
      else return;
      syncForm();
      scheduleRender();
    });
    $('#target-chips').addEventListener('click', (event) => {
      const button = event.target.closest('.chip-toggle');
      if (!button) return;
      const value = button.dataset.value;
      const mode = TEMPLATES[state.effect_template].targets;
      if (value === 'any') state.targets = state.targets.includes('any') ? [] : ['any'];
      else if (mode === 'one-or-any') state.targets = [value];
      else {
        const selected = state.targets.filter((target) => target !== 'any');
        if (selected.includes(value)) state.targets = selected.filter((target) => target !== value);
        else state.targets = [...selected, value].slice(-2);
      }
      if (!state.targets.length && mode !== 'pair') state.targets = ['any'];
      syncForm();
      scheduleRender();
    });
    $('.joker-pair').addEventListener('click', (event) => {
      const button = event.target.closest('.chip-toggle');
      if (!button) return;
      const value = button.dataset.value;
      state.joker_pair = state.joker_pair.includes(value)
        ? state.joker_pair.filter((family) => family !== value)
        : [...state.joker_pair, value].slice(-2);
      if (state.joker_pair.length === 2) state.joker_pair = FAMILIES.filter((family) => state.joker_pair.includes(family));
      syncForm();
      scheduleRender();
    });
    $('#requirement-steppers').addEventListener('click', (event) => {
      const button = event.target.closest('button[data-step]');
      if (!button) return;
      const family = button.closest('.stepper').dataset.family;
      const next = (state.requirements[family] || 0) + Number(button.dataset.step);
      const total = requirementList(state).length + Number(button.dataset.step);
      if (next < 0 || total > 4) return;
      state.requirements = { ...state.requirements, [family]: next };
      syncForm();
      scheduleRender();
    });
    $('#template').addEventListener('change', (event) => loadTemplate(event.target.value));
    $('#artwork').addEventListener('change', async (event) => {
      const file = event.target.files[0];
      event.target.value = '';
      if (!file) return;
      try {
        state.artwork = await prepareArtwork(file);
        $('#error-artwork').textContent = '';
      } catch (error) {
        $('#error-artwork').textContent = 'Dieses Bild lässt sich nicht lesen. PNG, JPG oder WebP verwenden.';
        return;
      }
      syncForm();
      scheduleRender();
    });
    $('#artwork-clear').addEventListener('click', () => {
      state.artwork = null;
      syncForm();
      scheduleRender();
    });
    $('#reset').addEventListener('click', () => {
      state = structuredClone(DEFAULTS);
      syncForm();
      scheduleRender();
    });
    $$('[data-export]').forEach((button) => button.addEventListener('click', () => exportCard(button.dataset.export, button)));
  }

  /* ---------- templates and artwork ---------- */

  const WORD_TO_FAMILY = { Team: 'team', Daten: 'data', Betriebs: 'operations', Methoden: 'methods' };

  async function loadTemplate(cardId) {
    if (!cardId) {
      state = { ...structuredClone(DEFAULTS), artwork: null };
      syncForm();
      scheduleRender();
      return;
    }
    const card = CARDS.find((entry) => entry.card_id === cardId);
    if (!card) return;
    const next = structuredClone(DEFAULTS);
    Object.assign(next, {
      template: cardId,
      card_type: card.card_type,
      name: card.name,
      flavor_text: card.flavor_text,
      project_goal: card.project_goal,
      visual_motif: card.visual_motif,
      card_id: card.card_id,
      rarity: card.rarity,
      artwork: null,
    });
    if (card.card_type === 'Projektfaktor') {
      next.factor_family = card.factor_family || 'team';
      const pair = /eine (\w+)- oder (\w+)-Anforderung/.exec(card.rules_text);
      if (pair) next.joker_pair = [WORD_TO_FAMILY[pair[1]], WORD_TO_FAMILY[pair[2]]].filter(Boolean);
    } else if (card.card_type === 'Ereignis') {
      next.effect_template = card.effect_template;
      next.targets = card.target_family ? card.target_family.split('+') : [];
    } else {
      next.domain_primary = card.domain_primary;
      next.requirements = { team: 0, data: 0, operations: 0, methods: 0 };
      card.requirements.split('+').forEach((family) => { next.requirements[family] += 1; });
    }
    next.free_rules = generatedRules(next) !== card.rules_text;
    next.rules_text = next.free_rules ? card.rules_text : '';
    state = next;
    syncForm();
    render();
    try {
      const response = await fetch(`assets/art/${cardId}.webp`);
      if (!response.ok) throw new Error(String(response.status));
      const artwork = await blobToDataUrl(await response.blob());
      if (state.template === cardId) {
        state.artwork = artwork;
        syncForm();
        scheduleRender();
      }
    } catch (error) {
      // The card still renders with the placeholder illustration.
    }
  }

  function blobToDataUrl(blob) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = () => resolve(reader.result);
      reader.onerror = () => reject(reader.error);
      reader.readAsDataURL(blob);
    });
  }

  function loadImage(src) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = () => resolve(image);
      image.onerror = reject;
      image.src = src;
    });
  }

  // Crop to the 3:2 art window and keep enough pixels for the print PNG.
  async function prepareArtwork(file) {
    const url = URL.createObjectURL(file);
    try {
      const image = await loadImage(url);
      const targetRatio = 3 / 2;
      let sw = image.naturalWidth;
      let sh = image.naturalHeight;
      if (sw / sh > targetRatio) sw = Math.round(sh * targetRatio);
      else sh = Math.round(sw / targetRatio);
      const sx = Math.round((image.naturalWidth - sw) / 2);
      const sy = Math.round((image.naturalHeight - sh) / 2);
      const width = Math.min(1320, sw);
      const height = Math.round(width / targetRatio);
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      canvas.getContext('2d').drawImage(image, sx, sy, sw, sh, 0, 0, width, height);
      return canvas.toDataURL('image/jpeg', 0.9);
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  /* ---------- export ---------- */

  const fontData = {};
  async function embeddedFontCss(svg) {
    const roles = new Set([...svg.querySelectorAll('text[data-font-role]')].map((node) => node.getAttribute('data-font-role')));
    const faces = {
      regular: ['Noto Serif', 400, 'normal'],
      bold: ['Noto Serif', 700, 'normal'],
      italic: ['Noto Serif', 400, 'italic'],
      sans_bold: ['Noto Sans', 700, 'normal'],
      sans_regular: ['Noto Sans', 400, 'normal'],
    };
    const rules = [];
    for (const role of roles) {
      if (!fontData[role]) {
        const response = await fetch(R.data.fonts[role].file);
        fontData[role] = await blobToDataUrl(new Blob([await response.arrayBuffer()], { type: 'font/ttf' }));
      }
      const [family, weight, style] = faces[role];
      rules.push(`@font-face{font-family:'${family}';src:url(${fontData[role]}) format('truetype');font-weight:${weight};font-style:${style}}`);
    }
    rules.push("text[font-feature-settings]{font-feature-settings:'tnum' 1,'lnum' 1}");
    return rules.join('\n');
  }

  async function exportSvgString() {
    const svg = lastGood.svg.cloneNode(true);
    svg.removeAttribute('role');
    svg.removeAttribute('aria-label');
    svg.setAttribute('width', '69.6mm');
    svg.setAttribute('height', '95mm');
    svg.setAttribute('viewBox', R.data.profile.master_svg.view_box.join(' '));
    const style = document.createElementNS('http://www.w3.org/2000/svg', 'style');
    style.textContent = await embeddedFontCss(svg);
    svg.querySelector('defs').prepend(style);
    return new XMLSerializer().serializeToString(svg);
  }

  async function rasterize(svgString) {
    const [width, height] = [1644, 2244];
    const url = URL.createObjectURL(new Blob([svgString], { type: 'image/svg+xml' }));
    try {
      const image = await loadImage(url);
      if (image.decode) await image.decode().catch(() => {});
      const canvas = document.createElement('canvas');
      canvas.width = width;
      canvas.height = height;
      const context = canvas.getContext('2d');
      context.fillStyle = '#171A1E';
      context.fillRect(0, 0, width, height);
      context.drawImage(image, 0, 0, width, height);
      return canvas;
    } finally {
      URL.revokeObjectURL(url);
    }
  }

  function canvasToBlob(canvas) {
    return new Promise((resolve) => canvas.toBlob(resolve, 'image/png'));
  }

  const CRC_TABLE = Array.from({ length: 256 }, (_, n) => {
    let c = n;
    for (let k = 0; k < 8; k += 1) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    return c >>> 0;
  });
  function crc32(bytes) {
    let crc = 0xffffffff;
    for (const byte of bytes) crc = CRC_TABLE[(crc ^ byte) & 0xff] ^ (crc >>> 8);
    return (crc ^ 0xffffffff) >>> 0;
  }
  function pngChunk(type, data) {
    const chunk = new Uint8Array(12 + data.length);
    const view = new DataView(chunk.buffer);
    view.setUint32(0, data.length);
    chunk.set([...type].map((ch) => ch.charCodeAt(0)), 4);
    chunk.set(data, 8);
    view.setUint32(8 + data.length, crc32(chunk.subarray(4, 8 + data.length)));
    return chunk;
  }

  // Declare sRGB and 600 dpi like the print pipeline's PNGs.
  async function withPrintMetadata(blob) {
    const bytes = new Uint8Array(await blob.arrayBuffer());
    const ihdrEnd = 8 + 25;
    const perMetre = Math.round(600 / 0.0254);
    const phys = new Uint8Array(9);
    new DataView(phys.buffer).setUint32(0, perMetre);
    new DataView(phys.buffer).setUint32(4, perMetre);
    phys[8] = 1;
    const parts = [bytes.subarray(0, ihdrEnd), pngChunk('sRGB', new Uint8Array([0])), pngChunk('pHYs', phys), bytes.subarray(ihdrEnd)];
    return new Blob(parts, { type: 'image/png' });
  }

  function download(blob, filename) {
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 2000);
  }

  function slug(text) {
    return text.normalize('NFD').replace(/[̀-ͯ]/g, '').replace(/ß/g, 'ss')
      .replace(/[^A-Za-z0-9]+/g, '-').replace(/^-|-$/g, '').toLowerCase() || 'karte';
  }

  const CSV_COLUMNS = ['card_id', 'name', 'domain_primary', 'domain_secondary', 'editorial_tags', 'rarity', 'card_type', 'factor_family',
    'target_family', 'polarity', 'effect_template', 'requirements', 'points', 'project_goal', 'foil_only', 'stage_candidate', 'stage_copies',
    'motif_origin', 'visual_motif', 'mechanical_role', 'rules_text', 'flavor_text', 'test_notes', 'notes'];

  function csvText(card) {
    const row = { ...card, foil_only: 'false', motif_origin: state.rarity === 'community' ? 'community' : '' };
    const quote = (value) => {
      const text = String(value ?? '');
      return /[",\n\r]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
    };
    return `${CSV_COLUMNS.join(',')}\n${CSV_COLUMNS.map((column) => quote(row[column])).join(',')}\n`;
  }

  async function exportCard(kind, button) {
    if (!lastGood) return;
    const status = $('#render-status');
    const filename = `${lastGood.card.card_id}-${slug(lastGood.card.name)}`;
    const label = button.textContent;
    button.disabled = true;
    button.textContent = 'Wird erstellt …';
    try {
      if (kind === 'csv') {
        const text = csvText(lastGood.card);
        try {
          await navigator.clipboard.writeText(text);
          status.textContent = 'Kartendaten als CSV-Zeile mit Kopfzeile kopiert, passend zu data/cards.csv.';
        } catch (error) {
          download(new Blob([text], { type: 'text/csv' }), `${filename}.csv`);
          status.textContent = 'Kartendaten als CSV-Datei heruntergeladen.';
        }
        return;
      }
      const svgString = await exportSvgString();
      if (kind === 'svg') {
        download(new Blob([svgString], { type: 'image/svg+xml' }), `${filename}.svg`);
        status.textContent = 'SVG mit eingebetteten Schriften heruntergeladen.';
        return;
      }
      const canvas = await rasterize(svgString);
      if (kind === 'print') {
        download(await withPrintMetadata(await canvasToBlob(canvas)), `${filename}-druck-1644x2244.png`);
        status.textContent = 'Druck-PNG mit Beschnitt heruntergeladen: 1644 × 2244 px, 600 dpi.';
        return;
      }
      const trim = R.data.profile.master_svg.rectangles.trim;
      const scale = 2;
      const cropped = document.createElement('canvas');
      cropped.width = trim.width * scale;
      cropped.height = trim.height * scale;
      cropped.getContext('2d').drawImage(canvas, trim.x * scale, trim.y * scale, cropped.width, cropped.height, 0, 0, cropped.width, cropped.height);
      download(await canvasToBlob(cropped), `${filename}.png`);
      status.textContent = 'PNG im Kartenformat heruntergeladen: 1500 × 2100 px.';
    } catch (error) {
      status.textContent = 'Der Export ist fehlgeschlagen. Bitte erneut versuchen.';
    } finally {
      button.disabled = false;
      button.textContent = label;
    }
  }

  /* ---------- draft ---------- */

  function saveDraft() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (error) {
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ ...state, artwork: null }));
      } catch (ignored) {
        // Private windows or full storage: the generator works without a draft.
      }
    }
  }

  function loadDraft() {
    try {
      const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || 'null');
      if (saved && typeof saved === 'object') {
        state = { ...structuredClone(DEFAULTS), ...saved, requirements: { ...DEFAULTS.requirements, ...(saved.requirements || {}) } };
        if (!TEMPLATES[state.effect_template]) state.effect_template = DEFAULTS.effect_template;
      }
    } catch (error) {
      state = structuredClone(DEFAULTS);
    }
  }

  /* ---------- start ---------- */

  async function start() {
    buildControls();
    const requested = new URLSearchParams(location.search).get('vorlage');
    loadDraft();
    syncForm();
    bindForm();
    setExportsEnabled(false);
    await R.loadFonts();
    if (requested && CARDS.some((card) => card.card_id === requested)) await loadTemplate(requested);
    else render();
  }

  start();
})();
