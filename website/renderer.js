/* Busfaktor: 1 — card renderer for the browser.
 *
 * A port of scripts/render_cards.py (build_card_svg and everything it draws).
 * Layout, profile, constants, icon geometry and font metrics come unchanged
 * from renderer-data.js, which website/prepare.py exports from the Python
 * renderer. Function names follow the Python originals so a change there can
 * be found and carried over here; website/tests/check_renderer_parity.mjs
 * compares both renderers on all canonical cards.
 *
 * Text widths are measured with canvas measureText on the renderer's own Noto
 * files at four times the layout size, like Pillow's RAQM layout in Python.
 */
(function (global) {
  'use strict';

  const DATA = global.CARD_RENDERER_DATA;
  if (!DATA) throw new Error('renderer-data.js fehlt');
  const C = DATA.constants;
  const LAYOUT = DATA.layout;
  const SVG_NS = C.SVG_NS;
  const WEB_RENDERER_VERSION = `${C.RENDERER_VERSION}-web.1`;

  const GERMAN_PREPOSITIONS = new Set(C.GERMAN_PREPOSITIONS);
  const GERMAN_DETERMINERS = new Set(C.GERMAN_DETERMINERS);
  const GERMAN_NUMBER_WORDS = new Set(C.GERMAN_NUMBER_WORDS);
  const RARITY_TRACKING_LABELS = new Set(C.RARITY_TRACKING_LABELS);

  const ROLE_FONTS = {
    regular: { family: 'Noto Serif', weight: '400', style: 'normal' },
    bold: { family: 'Noto Serif', weight: '700', style: 'normal' },
    italic: { family: 'Noto Serif', weight: '400', style: 'italic' },
    sans_bold: { family: 'Noto Sans', weight: '700', style: 'normal' },
    sans_regular: { family: 'Noto Sans', weight: '400', style: 'normal' },
  };

  class RenderError extends Error {
    constructor(message, field) {
      super(message);
      this.name = 'RenderError';
      this.field = field || null;
    }
  }

  /* ---------- fonts and measuring ---------- */

  let fontsReady = null;
  function loadFonts(base = '') {
    if (!fontsReady) {
      fontsReady = Promise.all(Object.entries(ROLE_FONTS).map(([role, spec]) => {
        const face = new FontFace(spec.family, `url("${base}${DATA.fonts[role].file}")`, {
          weight: spec.weight,
          style: spec.style,
        });
        document.fonts.add(face);
        return face.load();
      }));
    }
    return fontsReady;
  }

  let context = null;
  const widthCache = new Map();

  function pyRound(value) {
    const floor = Math.floor(value);
    const diff = value - floor;
    if (diff > 0.5) return floor + 1;
    if (diff < 0.5) return floor;
    return floor % 2 === 0 ? floor : floor + 1;
  }

  function codePoints(text) {
    return Array.from(text).length;
  }

  function measure(text, role, size) {
    const spec = ROLE_FONTS[role];
    const pixels = pyRound(size * 4);
    const key = `${role}|${pixels}|${text}`;
    let width = widthCache.get(key);
    if (width === undefined) {
      if (!context) {
        context = document.createElement('canvas').getContext('2d');
        if ('fontKerning' in context) context.fontKerning = 'normal';
      }
      context.font = `${spec.style} ${spec.weight} ${pixels}px "${spec.family}"`;
      width = context.measureText(text).width / 4;
      widthCache.set(key, width);
    }
    return width;
  }

  function textWidth(text, role, size, letterSpacing = 0) {
    return measure(text, role, size) + Math.max(codePoints(text) - 1, 0) * letterSpacing;
  }

  function fontMetrics(role, size) {
    const metrics = DATA.fonts[role].metrics[attrNumber(size)];
    if (!metrics) throw new RenderError(`Keine Schriftmetrik für ${role} ${size}`);
    return metrics;
  }

  /* ---------- small Python equivalents ---------- */

  const hasCase = (ch) => ch.toLowerCase() !== ch.toUpperCase();
  const isUpperChar = (ch) => hasCase(ch) && ch === ch.toUpperCase();
  const isLowerChar = (ch) => hasCase(ch) && ch === ch.toLowerCase();

  function isUpper(text) {
    let cased = false;
    for (const ch of text) {
      if (!hasCase(ch)) continue;
      if (ch !== ch.toUpperCase()) return false;
      cased = true;
    }
    return cased;
  }

  const hasDigit = (text) => /\p{Nd}/u.test(text);
  const splitWords = (text) => text.split(/\s+/u).filter(Boolean);
  const casefold = (text) => text.toLowerCase();

  function attrNumber(value) {
    if (Number.isInteger(value)) return String(value);
    return value.toFixed(4).replace(/0+$/, '').replace(/\.$/, '');
  }

  function el(parent, name, attrs = {}) {
    const node = document.createElementNS(SVG_NS, name);
    for (const [key, value] of Object.entries(attrs)) {
      if (value === null || value === undefined) continue;
      node.setAttribute(key, typeof value === 'number' ? attrNumber(value) : String(value));
    }
    if (parent) parent.appendChild(node);
    return node;
  }

  function setAttr(node, key, value) {
    node.setAttribute(key, typeof value === 'number' ? attrNumber(value) : String(value));
  }

  function compareTuples(a, b) {
    for (let i = 0; i < Math.max(a.length, b.length); i += 1) {
      if (i >= a.length) return -1;
      if (i >= b.length) return 1;
      const x = a[i];
      const y = b[i];
      if (Array.isArray(x)) {
        const nested = compareTuples(x, y);
        if (nested) return nested;
        continue;
      }
      if (x < y) return -1;
      if (x > y) return 1;
    }
    return 0;
  }

  /* ---------- icons ---------- */

  function appendIconTree(parent, node) {
    const child = el(parent, node.tag, node.attrs);
    node.children.forEach((grandchild) => appendIconTree(child, grandchild));
  }

  function drawIcon(parent, iconKey, x, y, size, color, { role, opacity = null, attributes = null } = {}) {
    const icon = DATA.icons[iconKey];
    if (!icon) throw new RenderError(`Unbekannte Iconrolle: ${iconKey}`);
    const scale = size / 256;
    const group = el(parent, 'g', {
      transform: `translate(${attrNumber(x)} ${attrNumber(y)}) scale(${attrNumber(scale)})`,
      fill: color,
      opacity,
      'data-role': role,
      'data-icon': icon.icon,
      'data-icon-label': icon.label,
      'data-icon-source': icon.source,
      'data-icon-sha256': icon.sha256,
      'data-icon-library': icon.library,
      'data-icon-version': icon.version,
      'data-icon-weight': icon.weight,
      'data-icon-size': size,
    });
    for (const [key, value] of Object.entries(attributes || {})) setAttr(group, key, value);
    icon.children.forEach((child) => appendIconTree(group, child));
    return group;
  }

  function rect(parent, x, y, width, height, { fill = 'none', stroke = null, strokeWidth = null, radius = 0, opacity = null, role = null } = {}) {
    return el(parent, 'rect', {
      x, y, width, height,
      rx: radius || null,
      fill,
      stroke,
      'stroke-width': strokeWidth,
      opacity,
      'data-role': role,
    });
  }

  function ellipse(parent, x, y, width, height, { fill = 'none', stroke = null, strokeWidth = null, opacity = null } = {}) {
    return el(parent, 'ellipse', {
      cx: x + width / 2,
      cy: y + height / 2,
      rx: width / 2,
      ry: height / 2,
      fill,
      stroke,
      'stroke-width': strokeWidth,
      opacity,
    });
  }

  /* ---------- typography ---------- */

  function typographySteps(mapping, typographyRole) {
    const role = mapping.typography[typographyRole];
    if (!role) throw new RenderError(`Unbekannte Typografierolle: ${typographyRole}`);
    return role.steps.map((step) => [Number(step.size), Number(step.line_height), String(step.status || 'standard')]);
  }

  function trackingForText(text, size, family) {
    if (family === 'Noto Serif' && size >= 36) return round2(size * -0.0075);
    if (family !== 'Noto Sans' || !isUpper(text)) return 0;
    let ratio;
    if (RARITY_TRACKING_LABELS.has(text)) ratio = 0.10;
    else if (size > 20) ratio = 0.015;
    else if (size > 14) ratio = 0.04;
    else if (size >= 12) ratio = 0.06;
    else ratio = 0.08;
    return round2(size * ratio);
  }

  function round2(value) {
    return pyRound(value * 100) / 100;
  }

  function lexicalToken(token) {
    return token.replace(/^[^\p{L}\p{N}_]+|[^\p{L}\p{N}_]+$/gu, '');
  }

  const stripClosers = (token) => token.replace(/[”’›»)\]}]+$/u, '');
  const isSentenceBreak = (token) => lexicalToken(token).length > 1 && /[.!?]$/.test(stripClosers(token));
  const isClauseBreak = (token) => /[,;:]$/.test(stripClosers(token));
  const isStrongClauseBreak = (token) => /[;:]$/.test(stripClosers(token));
  function startsUpper(token) {
    const lexical = lexicalToken(token);
    return Boolean(lexical) && isUpperChar(Array.from(lexical)[0]);
  }

  function protectedGermanSplits(words) {
    const isStarter = (word) => GERMAN_PREPOSITIONS.has(word) || GERMAN_DETERMINERS.has(word) || GERMAN_NUMBER_WORDS.has(word);
    const protectedSplits = new Set();
    for (let start = 0; start < words.length - 1; start += 1) {
      const token = words[start];
      const lexical = lexicalToken(token);
      const normalized = casefold(lexical);
      if (isStarter(normalized) && !isClauseBreak(token) && !isSentenceBreak(token)) {
        let head = null;
        for (let candidate = start + 1; candidate < words.length; candidate += 1) {
          if (
            startsUpper(words[candidate])
            || isClauseBreak(words[candidate])
            || isSentenceBreak(words[candidate])
            || candidate === words.length - 1
          ) {
            head = candidate;
            break;
          }
        }
        if (head !== null) for (let index = start + 1; index <= head; index += 1) protectedSplits.add(index);
      }
      const nextLexical = lexicalToken(words[start + 1]);
      const first = Array.from(lexical)[0] || '';
      const nextFirst = Array.from(nextLexical)[0] || '';
      const looksLikeAttributiveModifier = Boolean(lexical)
        && isLowerChar(first)
        && /(e|en|er|es|em)$/.test(normalized)
        && Boolean(nextLexical)
        && isUpperChar(nextFirst);
      const numberBeforeNoun = hasDigit(lexical)
        && !isClauseBreak(token)
        && !isSentenceBreak(token)
        && Boolean(nextLexical)
        && isUpperChar(nextFirst);
      if (looksLikeAttributiveModifier || numberBeforeNoun) protectedSplits.add(start + 1);
    }
    return protectedSplits;
  }

  function balanceParagraphLines(lines, role, size, width, letterSpacing) {
    if (lines.length < 2) return lines;
    const rightWords = splitWords(lines[lines.length - 1]);
    const rightWidth = textWidth(lines[lines.length - 1], role, size, letterSpacing);
    if (rightWidth >= width * C.LAST_LINE_MIN_MEASURE && rightWords.length > 1) return lines;

    const words = splitWords(lines.join(' '));
    const lineCount = lines.length;
    const greedyBreaks = [];
    let consumed = 0;
    for (const line of lines.slice(0, -1)) {
      consumed += splitWords(line).length;
      greedyBreaks.push(consumed);
    }
    const protectedSplits = protectedGermanSplits(words);
    const cache = new Map();
    const measuredWidth = (start, end) => {
      const key = `${start}:${end}`;
      if (!cache.has(key)) cache.set(key, textWidth(words.slice(start, end).join(' '), role, size, letterSpacing));
      return cache.get(key);
    };

    let states = new Map([[0, [0, 0, []]]]);
    for (let lineIndex = 0; lineIndex < lineCount; lineIndex += 1) {
      const nextStates = new Map();
      const remainingLines = lineCount - lineIndex - 1;
      for (const [start, [baseScore, baseDistance, breaks]] of states) {
        const lastPossibleEnd = words.length - remainingLines;
        for (let end = start + 1; end <= lastPossibleEnd; end += 1) {
          const lineWidth = measuredWidth(start, end);
          if (lineWidth > width) continue;
          const isLastLine = lineIndex === lineCount - 1;
          if (isLastLine !== (end === words.length)) continue;

          const fillRatio = lineWidth / width;
          let score = baseScore + (1 - fillRatio) ** 2;
          if (fillRatio < C.LAST_LINE_MIN_MEASURE) {
            const shortfall = (C.LAST_LINE_MIN_MEASURE - fillRatio) / C.LAST_LINE_MIN_MEASURE;
            score += C.PROSE_SHORT_LINE_PENALTY * shortfall ** 2;
          }
          if (end - start === 1) score += C.PROSE_SINGLE_WORD_PENALTY;

          let distance = baseDistance;
          let candidateBreaks = breaks;
          if (!isLastLine) {
            if (protectedSplits.has(end)) score += C.PROSE_PROTECTED_SPLIT_PENALTY;
            if (isSentenceBreak(words[end - 1])) score -= C.PROSE_SENTENCE_BREAK_BONUS;
            else if (isStrongClauseBreak(words[end - 1])) score -= C.PROSE_STRONG_CLAUSE_BREAK_BONUS;
            else if (isClauseBreak(words[end - 1])) score -= C.PROSE_CLAUSE_BREAK_BONUS;
            distance += Math.abs(end - greedyBreaks[lineIndex]);
            candidateBreaks = [...breaks, end];
          }
          const candidate = [score, distance, candidateBreaks];
          const previous = nextStates.get(end);
          if (!previous || compareTuples(candidate, previous) < 0) nextStates.set(end, candidate);
        }
      }
      states = nextStates;
    }
    const fitted = states.get(words.length);
    if (!fitted) return lines;
    const cuts = [0, ...fitted[2], words.length];
    return Array.from({ length: lineCount }, (_, index) => words.slice(cuts[index], cuts[index + 1]).join(' '));
  }

  function balanceFlavorTwoLines(lines, role, size, width, letterSpacing) {
    if (lines.length !== 2) return lines;
    const words = splitWords(lines.join(' '));
    const greedySplit = splitWords(lines[0]).length;
    const protectedSplits = protectedGermanSplits(words);
    let best = null;
    for (let split = 1; split < words.length; split += 1) {
      if (protectedSplits.has(split)) continue;
      const left = words.slice(0, split).join(' ');
      const right = words.slice(split).join(' ');
      const leftWidth = textWidth(left, role, size, letterSpacing);
      const rightWidth = textWidth(right, role, size, letterSpacing);
      if (leftWidth > width || rightWidth > width) continue;
      if (Math.min(leftWidth, rightWidth) < width * C.FLAVOR_MIN_LINE_MEASURE) continue;
      let score = Math.abs(leftWidth - rightWidth) / width;
      if (isSentenceBreak(words[split - 1])) score -= C.FLAVOR_SENTENCE_BREAK_BONUS;
      else if (isClauseBreak(words[split - 1])) score -= C.FLAVOR_CLAUSE_BREAK_BONUS;
      if (GERMAN_PREPOSITIONS.has(casefold(lexicalToken(words[split])))) score -= C.FLAVOR_PHRASE_BREAK_BONUS;
      const candidate = [score, Math.abs(split - greedySplit), -split, left, right];
      if (!best || compareTuples(candidate, best) < 0) best = candidate;
    }
    return best ? [best[3], best[4]] : lines;
  }

  function wrapWords(text, role, size, width, letterSpacing = 0, { balanceLastLine = true, flavorAware = false } = {}) {
    const lines = [];
    for (const paragraph of text.replace(/\r/g, '').split('\n')) {
      const words = splitWords(paragraph);
      if (!words.length) {
        lines.push('');
        continue;
      }
      let paragraphLines = [];
      let current = words[0];
      for (const word of words.slice(1)) {
        const candidate = `${current} ${word}`;
        if (textWidth(candidate, role, size, letterSpacing) <= width) current = candidate;
        else {
          paragraphLines.push(current);
          current = word;
        }
      }
      paragraphLines.push(current);
      if (flavorAware) paragraphLines = balanceFlavorTwoLines(paragraphLines, role, size, width, letterSpacing);
      else if (balanceLastLine) paragraphLines = balanceParagraphLines(paragraphLines, role, size, width, letterSpacing);
      lines.push(...paragraphLines);
    }
    return lines;
  }

  function fitText(text, role, steps, width, height, { family, singleLine = false, balanceLastLine = true, flavorAware = false, field = null } = {}) {
    for (const [size, lineHeight, status] of steps) {
      const letterSpacing = trackingForText(text, size, family);
      const lines = singleLine
        ? [text]
        : wrapWords(text, role, size, width, letterSpacing, { balanceLastLine, flavorAware });
      const fittedHeight = lines.length * lineHeight;
      const fittedWidth = Math.max(0, ...lines.map((line) => textWidth(line, role, size, letterSpacing)));
      if (fittedWidth <= width + 0.1 && fittedHeight <= height + 0.1) {
        return { size, lineHeight, lines, letterSpacing, status };
      }
    }
    throw new RenderError(
      `Text passt nicht in ${width.toFixed(0)}×${height.toFixed(0)}: ${text.slice(0, 72)}${text.length > 72 ? '…' : ''}`,
      field,
    );
  }

  function drawText(parent, text, {
    x, y, width, height, steps, role = 'regular', fill = '#17212B', family = 'Noto Serif',
    anchor = 'start', vertical = 'top', singleLine = false, balanceLastLine = true,
    flavorAware = false, dataRole = null, fitted = null, field = null,
  }) {
    const fit = fitted || fitText(text, role, steps, width, height, { family, singleLine, balanceLastLine, flavorAware, field });
    let textX = x;
    if (anchor === 'middle') textX = x + width / 2;
    else if (anchor === 'end') textX = x + width;
    const blockHeight = fit.lines.length * fit.lineHeight;
    let baseline;
    if (vertical === 'font-metrics-middle') {
      if (fit.lines.length !== 1) throw new RenderError('Metrische Vertikalzentrierung ist nur einzeilig möglich');
      const [ascent, descent] = fontMetrics(role, fit.size);
      baseline = y + (height - (ascent + descent) / 4) / 2 + ascent / 4;
    } else {
      let top = y;
      if (vertical === 'middle') top = y + (height - blockHeight) / 2;
      else if (vertical === 'bottom') top = y + height - blockHeight;
      baseline = top + fit.size;
    }
    const element = el(parent, 'text', {
      x: textX,
      y: baseline,
      fill,
      'font-family': family,
      'font-size': fit.size,
      'font-weight': role === 'bold' || role === 'sans_bold' ? '700' : '400',
      'font-style': role === 'italic' ? 'italic' : 'normal',
      'text-anchor': anchor,
      'letter-spacing': fit.letterSpacing || null,
      'font-feature-settings': hasDigit(text) ? "'tnum' 1, 'lnum' 1" : null,
      'data-role': dataRole,
      'data-font-role': role,
      'data-type-size-step': fit.size,
      'data-line-height': fit.lineHeight,
      'data-type-step-status': fit.status,
    });
    fit.lines.forEach((line, index) => {
      const tspan = el(element, 'tspan', { x: textX, dy: index === 0 ? 0 : fit.lineHeight });
      tspan.textContent = line;
    });
    return [fit.size, fit.lines];
  }

  function drawTitle(parent, text, zone, mapping) {
    const [size] = drawText(parent, text, {
      x: zone.x, y: zone.y, width: zone.width, height: zone.height,
      steps: typographySteps(mapping, 'title'),
      role: 'bold',
      fill: color(mapping, 'text/primary'),
      vertical: 'font-metrics-middle',
      singleLine: true,
      dataRole: 'card-title',
      field: 'name',
    });
    return size;
  }

  /* ---------- card appearance ---------- */

  function familyKey(card, layoutKey) {
    if (layoutKey === 'factor') return card.factor_family || 'wildcard';
    return 'wildcard';
  }

  function appearance(card, mapping, layoutKey) {
    if (layoutKey === 'factor') {
      const family = mapping.families[familyKey(card, layoutKey)];
      if (!family) throw new RenderError(`Unbekannte Faktorfamilie ${card.factor_family}`, 'factor_family');
      return { accentToken: family.color_token, label: family.label };
    }
    if (layoutKey === 'event') return { accentToken: mapping.card_types.Ereignis.color_token };
    const domain = mapping.families[card.domain_primary || 'wildcard'] || mapping.families.wildcard;
    return { accentToken: domain.color_token, label: domain.label };
  }

  function layoutKeyFor(card) {
    const key = { Projekt: 'project', Projektfaktor: 'factor', Ereignis: 'event' }[card.card_type];
    if (!key) throw new RenderError(`${card.card_id || '<ohne ID>'}: unbekannte Kartenart`, 'card_type');
    return key;
  }

  function color(mapping, token) {
    const entry = mapping.colors[token];
    if (!entry) throw new RenderError(`Unbekannter Farbtoken: ${token}`);
    return String(entry.hex);
  }

  /* ---------- plates and materials ---------- */

  function defineArtEdgeGradients(defs, mapping) {
    const warm = color(mapping, 'material/art-warm');
    const specifications = [
      ['art-warm-left', 'left', '0%', '0%', '100%', '0%', false],
      ['art-warm-right', 'right', '0%', '0%', '100%', '0%', true],
      ['art-warm-top', 'top', '0%', '0%', '0%', '100%', false],
      ['art-warm-bottom', 'bottom', '0%', '0%', '0%', '100%', true],
    ];
    for (const [id, edge, x1, y1, x2, y2, reverse] of specifications) {
      const gradient = el(defs, 'linearGradient', {
        id, x1, y1, x2, y2,
        'data-role': 'art-edge-warmth-gradient',
        'data-edge': edge,
      });
      const [first, second] = reverse ? [0, C.ART_EDGE_WARMTH_OPACITY] : [C.ART_EDGE_WARMTH_OPACITY, 0];
      el(gradient, 'stop', { offset: '0%', 'stop-color': warm, 'stop-opacity': first });
      el(gradient, 'stop', { offset: '100%', 'stop-color': warm, 'stop-opacity': second });
    }
  }

  function defineMaterialDefs(defs, mapping) {
    defineArtEdgeGradients(defs, mapping);
    const inner = el(defs, 'linearGradient', {
      id: 'inner-card-field-gradient', x1: '0%', y1: '0%', x2: '0%', y2: '100%',
      'data-role': 'inner-card-field-gradient',
    });
    for (const [offset, token] of [
      ['0%', 'background/shell-raised-top'],
      ['50%', 'background/shell-raised'],
      ['100%', 'background/shell-raised-bottom'],
    ]) {
      el(inner, 'stop', { offset, 'stop-color': color(mapping, token), 'data-color-token': token });
    }
    const shadow = el(defs, 'linearGradient', {
      id: 'art-top-inner-shadow', x1: '0%', y1: '0%', x2: '0%', y2: '100%',
      'data-role': 'artwork-top-inner-shadow-gradient',
    });
    for (const [offset, opacity] of [['0%', C.ART_TOP_INNER_SHADOW_OPACITY], ['35%', 0.018], ['100%', 0]]) {
      el(shadow, 'stop', { offset, 'stop-color': '#000000', 'stop-opacity': opacity });
    }
  }

  function selectiveRoundedRect(parent, x, y, width, height, { radius, corners, fill, stroke = null, strokeWidth = null, role = null }) {
    const right = x + width;
    const bottom = y + height;
    let path;
    if (corners === 'top') {
      path = `M ${x + radius} ${y} H ${right - radius} A ${radius} ${radius} 0 0 1 ${right} ${y + radius} `
        + `V ${bottom} H ${x} V ${y + radius} A ${radius} ${radius} 0 0 1 ${x + radius} ${y} Z`;
    } else if (corners === 'bottom') {
      path = `M ${x} ${y} H ${right} V ${bottom - radius} A ${radius} ${radius} 0 0 1 ${right - radius} ${bottom} `
        + `H ${x + radius} A ${radius} ${radius} 0 0 1 ${x} ${bottom - radius} V ${y} Z`;
    } else {
      throw new RenderError(`Unbekannter Eckenmodus: ${corners}`);
    }
    return el(parent, 'path', {
      d: path,
      fill,
      stroke,
      'stroke-width': strokeWidth,
      'data-role': role,
      'data-box-x': x,
      'data-box-y': y,
      'data-box-width': width,
      'data-box-height': height,
      'data-corner-mode': corners,
      'data-corner-radius': radius,
    });
  }

  function plateShape(parent, x, y, width, height, { corners, radius, fill, role, stroke = null, strokeWidth = null }) {
    if (corners === 'none') return rect(parent, x, y, width, height, { fill, stroke, strokeWidth, role });
    return selectiveRoundedRect(parent, x, y, width, height, { radius, corners, fill, stroke, strokeWidth, role });
  }

  function drawPlateKeyline(parent, x, y, width, height, mapping, { plateRole, corners, radius }) {
    const strokeWidth = C.MAIN_BOX_KEYLINE_STROKE_WIDTH;
    const inset = strokeWidth / 2;
    const keyline = plateShape(parent, x + inset, y + inset, width - 2 * inset, height - 2 * inset, {
      corners,
      radius: Math.max(0, radius - inset),
      fill: 'none',
      stroke: color(mapping, 'line/default'),
      strokeWidth,
      role: 'plate-keyline',
    });
    setAttr(keyline, 'data-plate-role', plateRole);
    setAttr(keyline, 'data-relief', 'flat');
    setAttr(keyline, 'data-color-token', 'line/default');
    setAttr(keyline, 'data-inset', inset);
    setAttr(keyline, 'data-stroke-width', strokeWidth);
    setAttr(keyline, 'data-box-x', x + inset);
    setAttr(keyline, 'data-box-y', y + inset);
    setAttr(keyline, 'data-box-width', width - 2 * inset);
    setAttr(keyline, 'data-box-height', height - 2 * inset);
  }

  function flatPlate(parent, zone, mapping, accent, { fillToken, role, corners = 'none', radius = 0, showAccent = true }) {
    const { x, y, width, height } = zone;
    plateShape(parent, x, y, width, height, { corners, radius, fill: color(mapping, fillToken), role });
    if (showAccent) {
      rect(parent, C.ACCENT_RULE_X_START, y + C.PLATE_ACCENT_TOP_OFFSET, C.ACCENT_RULE_X_END - C.ACCENT_RULE_X_START, C.PLATE_ACCENT_HEIGHT, {
        fill: accent,
        role: `${role}-accent`,
      }).setAttribute('data-accent-mode', 'inset-rule');
    }
    drawPlateKeyline(parent, x, y, width, height, mapping, { plateRole: role, corners, radius });
  }

  /* ---------- title bar, type line, footer ---------- */

  function drawTypeSymbol(parent, layoutKey, symbolColor) {
    const typeIcon = { project: 'project', factor: 'project_factor', event: 'event' }[layoutKey];
    if (!typeIcon) throw new RenderError(`Unbekanntes Typzeichen: ${layoutKey}`);
    const iconSize = layoutKey === 'factor' ? 24 : 22;
    const offset = (40 - iconSize) / 2;
    drawIcon(parent, typeIcon, offset, offset, iconSize, symbolColor, { role: 'card-type-symbol' });
  }

  function drawIdentityStamp(parent, zones, mapping, layoutKey) {
    const carrierInset = 2;
    const x = zones.type.x - carrierInset;
    const y = zones.title_surface.y + 5;
    const group = el(parent, 'g', {
      transform: `translate(${attrNumber(x)} ${attrNumber(y)})`,
      'data-role': 'card-type-badge',
      'data-card-type': layoutKey,
    });
    const fillToken = 'background/paper';
    const carrier = ellipse(group, carrierInset, carrierInset, 36, 36, {
      fill: color(mapping, fillToken),
      stroke: color(mapping, 'line/default'),
      strokeWidth: C.STROKE_EMPHASIS,
    });
    carrier.setAttribute('data-role', 'card-type-carrier');
    carrier.setAttribute('data-fill-mode', 'neutral-paper');
    carrier.setAttribute('data-fill-token', fillToken);
    drawTypeSymbol(group, layoutKey, color(mapping, 'line/default'));
  }

  function drawProjectRequirementIcons(parent, card, typeSurface, mapping, { pointsX }) {
    const requirements = (card.requirements || '').split('+').filter(Boolean);
    if (!requirements.length) throw new RenderError(`${card.card_id}: Projektanforderungen fehlen`, 'requirements');
    const totalWidth = requirements.length * C.PROJECT_TYPE_SLOT_SIZE + (requirements.length - 1) * C.PROJECT_REQUIREMENT_ICON_GAP;
    const right = pointsX - C.PROJECT_REQUIREMENT_TO_POINTS_GAP;
    const left = right - totalWidth;
    if (left < typeSurface.x) throw new RenderError(`${card.card_id}: Anforderungsicons sind zu breit`, 'requirements');

    const centerY = typeSurface.y + typeSurface.height / 2;
    const top = centerY - C.PROJECT_TYPE_CIRCLE_SIZE / 2 + C.PROJECT_TYPE_CIRCLE_Y_OFFSET;
    const carrierInset = (C.PROJECT_TYPE_SLOT_SIZE - C.PROJECT_TYPE_CIRCLE_SIZE) / 2;
    const iconInset = (C.PROJECT_TYPE_SLOT_SIZE - C.PROJECT_REQUIREMENT_ICON_SIZE) / 2;
    const group = el(parent, 'g', {
      'data-role': 'project-requirements',
      'data-count': requirements.length,
      'data-left': left,
      'data-right': right,
    });
    requirements.forEach((requirement, index) => {
      const family = mapping.families[requirement];
      if (!family) throw new RenderError(`${card.card_id}: Unbekannte Projektanforderung '${requirement}'`, 'requirements');
      const slotX = left + index * (C.PROJECT_TYPE_SLOT_SIZE + C.PROJECT_REQUIREMENT_ICON_GAP);
      const familyColor = color(mapping, family.color_token);
      const carrier = ellipse(group, slotX + carrierInset, top, C.PROJECT_TYPE_CIRCLE_SIZE, C.PROJECT_TYPE_CIRCLE_SIZE, {
        fill: color(mapping, 'background/paper-raised'),
        stroke: familyColor,
        strokeWidth: C.STROKE_LINE,
      });
      carrier.setAttribute('data-role', 'project-requirement-carrier');
      carrier.setAttribute('data-family', requirement);
      carrier.setAttribute('data-slot', String(index + 1));
      carrier.setAttribute('data-count', '1');
      drawIcon(
        group,
        family.icon,
        slotX + iconInset,
        top + (C.PROJECT_TYPE_CIRCLE_SIZE - C.PROJECT_REQUIREMENT_ICON_SIZE) / 2,
        C.PROJECT_REQUIREMENT_ICON_SIZE,
        familyColor,
        { role: 'project-requirement-symbol', attributes: { 'data-family': requirement, 'data-slot': index + 1, 'data-count': 1 } },
      );
    });
    return left;
  }

  function drawTypeLine(parent, card, zones, mapping, accent, look, layoutKey) {
    let primary;
    let secondary;
    let secondaryIcon;
    if (layoutKey === 'project') {
      primary = 'PROJEKT';
      const family = mapping.families[card.domain_primary || ''];
      if (!family) throw new RenderError(`${card.card_id}: Unbekannte Projektfamilie '${card.domain_primary || ''}'`, 'domain_primary');
      secondary = family.label;
      secondaryIcon = family.icon;
    } else if (layoutKey === 'factor') {
      primary = 'PROJEKTFAKTOR';
      secondary = look.label;
      secondaryIcon = mapping.families[familyKey(card, layoutKey)].icon;
    } else {
      primary = 'EREIGNIS';
      const effectLabel = mapping.effect_templates[card.effect_template || ''] || '';
      const targetKeys = (card.target_family || '').split('+').filter(Boolean);
      const targetLabel = targetKeys.map((key) => {
        if (!mapping.families[key]) throw new RenderError(`${card.card_id}: Unbekanntes Ziel '${key}'`, 'target_family');
        return mapping.families[key].label;
      }).join(' + ');
      secondary = effectLabel + (targetLabel ? ` · ZIEL: ${targetLabel}` : '');
      secondaryIcon = (mapping.effect_icons || {})[card.effect_template || ''] || '';
    }

    const zone = zones.type;
    const primarySteps = typographySteps(mapping, 'type_primary');
    const primarySize = primarySteps[0][0];
    const primaryWidth = textWidth(primary, 'sans_bold', primarySize, trackingForText(primary, primarySize, 'Noto Sans'));
    drawText(parent, primary, {
      x: zone.x, y: zone.y, width: primaryWidth + 2, height: zone.height,
      steps: primarySteps, role: 'sans_bold', fill: accent, family: 'Noto Sans',
      vertical: 'middle', singleLine: true, dataRole: 'card-type',
    });
    let secondaryRight = zone.x + primaryWidth;
    let secondaryX = zone.x + primaryWidth + 5;
    if (secondary) {
      if (secondaryIcon) {
        const iconSize = layoutKey === 'project' ? C.PROJECT_FAMILY_ICON_SIZE : 18;
        let iconRole = 'factor-family-symbol';
        if (layoutKey === 'event') iconRole = 'event-effect-symbol';
        else if (layoutKey === 'project') iconRole = 'project-family-symbol';
        drawIcon(parent, secondaryIcon, secondaryX, zone.y + (zone.height - iconSize) / 2, iconSize, accent, { role: iconRole });
        secondaryX += iconSize + 5;
      }
      const secondarySteps = typographySteps(mapping, 'type_secondary');
      const secondarySize = secondarySteps[0][0];
      const secondaryWidth = textWidth(secondary, 'sans_regular', secondarySize, trackingForText(secondary, secondarySize, 'Noto Sans'));
      let boxWidth;
      if (layoutKey === 'project') boxWidth = secondaryWidth + 2;
      else if (layoutKey === 'event') {
        const surface = zones.type_surface;
        boxWidth = Math.max(80, surface.x + surface.width - 12 - secondaryX);
      } else {
        boxWidth = Math.max(80, zone.x + zone.width - secondaryX);
      }
      drawText(parent, secondary, {
        x: secondaryX, y: zone.y + 1, width: boxWidth, height: zone.height,
        steps: secondarySteps, role: 'sans_regular', fill: color(mapping, 'text/primary'), family: 'Noto Sans',
        vertical: 'middle', singleLine: true,
        dataRole: layoutKey === 'event' ? 'event-keyword' : 'card-category',
        field: layoutKey === 'event' ? 'target_family' : null,
      });
      secondaryRight = secondaryX + secondaryWidth;
    }
    if (layoutKey === 'project') {
      const pointsText = `${card.points || ''}P`;
      const surface = zones.type_surface;
      const pointsColor = color(mapping, 'line/default');
      const badgeSlotX = surface.x + surface.width - C.PROJECT_TYPE_SLOT_SIZE - 12;
      const badgeX = badgeSlotX + (C.PROJECT_TYPE_SLOT_SIZE - C.PROJECT_TYPE_CIRCLE_SIZE) / 2;
      const badgeY = surface.y + (surface.height - C.PROJECT_TYPE_CIRCLE_SIZE) / 2 + C.PROJECT_TYPE_CIRCLE_Y_OFFSET;
      const requirementsLeft = drawProjectRequirementIcons(parent, card, surface, mapping, { pointsX: badgeSlotX });
      if (requirementsLeft - secondaryRight < 12) {
        throw new RenderError(`${card.card_id}: Projektfamilie und Anforderungen kollidieren`, 'requirements');
      }
      const circle = ellipse(parent, badgeX, badgeY, C.PROJECT_TYPE_CIRCLE_SIZE, C.PROJECT_TYPE_CIRCLE_SIZE, {
        fill: color(mapping, 'background/paper-raised'),
        stroke: pointsColor,
        strokeWidth: C.STROKE_LINE,
      });
      circle.setAttribute('data-role', 'project-points');
      circle.setAttribute('data-shape', 'circle');
      drawText(parent, pointsText, {
        x: badgeX + 1, y: badgeY, width: C.PROJECT_TYPE_CIRCLE_SIZE - 2, height: C.PROJECT_TYPE_CIRCLE_SIZE,
        steps: typographySteps(mapping, 'points'), role: 'sans_bold', fill: pointsColor, family: 'Noto Sans',
        anchor: 'middle', vertical: 'middle', singleLine: true, dataRole: 'project-points-label', field: 'points',
      });
    }
  }

  function drawFooter(parent, card, zone, mapping, rarityOverride) {
    const group = el(parent, 'g', { 'data-role': 'card-footer' });
    const rarity = rarityOverride || mapping.rarities[card.rarity];
    if (!rarity) throw new RenderError(`${card.card_id}: Unbekannte Seltenheit`, 'rarity');
    const filledMarks = Number(rarity.marks);
    const minimum = rarityOverride ? 0 : 1;
    if (!(filledMarks >= minimum && filledMarks <= C.RARITY_PIP_COUNT)) {
      throw new RenderError(`${card.card_id}: Seltenheitsstufe ${filledMarks} liegt außerhalb der ${C.RARITY_PIP_COUNT} Pips`, 'rarity');
    }
    group.setAttribute('data-rarity-filled', String(filledMarks));
    group.setAttribute('data-rarity-total', String(C.RARITY_PIP_COUNT));
    const identitySteps = typographySteps(mapping, 'footer_identity');
    const identitySize = identitySteps[0][0];
    const identityGroup = el(group, 'g', { 'data-role': 'footer-identity-rarity' });
    let identityX = zone.x;
    const segments = [
      [card.card_id, 'footer-card-id'],
      ['·', 'footer-identity-separator'],
      [rarity.label, 'footer-rarity'],
    ];
    segments.forEach(([text, dataRole], index) => {
      const tracking = rarityOverride && dataRole === 'footer-rarity'
        ? round2(identitySize * 0.10)
        : trackingForText(text, identitySize, 'Noto Sans');
      const segmentWidth = textWidth(text, 'sans_bold', identitySize, tracking);
      drawText(identityGroup, text, {
        x: identityX, y: zone.y, width: segmentWidth + 2, height: zone.height,
        steps: identitySteps, role: 'sans_bold', fill: color(mapping, 'text/on-dark'), family: 'Noto Sans',
        vertical: 'middle', singleLine: true, dataRole,
        fitted: rarityOverride && dataRole === 'footer-rarity'
          ? { size: identitySize, lineHeight: identitySteps[0][1], lines: [text], letterSpacing: tracking, status: identitySteps[0][2] }
          : null,
        field: dataRole === 'footer-card-id' ? 'card_id' : null,
      });
      identityX += segmentWidth;
      if (index < segments.length - 1) identityX += C.FOOTER_IDENTITY_GAP;
    });

    const markColor = color(mapping, 'line/highlight');
    const trackX = zone.x + (zone.width - C.RARITY_PIP_TRACK_WIDTH) / 2;
    for (let index = 0; index < C.RARITY_PIP_COUNT; index += 1) {
      const filled = index < filledMarks;
      const inset = filled ? 0 : C.RARITY_PIP_OUTLINE_WIDTH / 2;
      const pip = rect(group, trackX + index * C.RARITY_PIP_STEP + inset, zone.y + 8 + inset, C.RARITY_PIP_SIZE - 2 * inset, C.RARITY_PIP_SIZE - 2 * inset, {
        fill: filled ? markColor : 'none',
        stroke: filled ? null : markColor,
        strokeWidth: filled ? null : C.RARITY_PIP_OUTLINE_WIDTH,
        radius: C.RARITY_PIP_RADIUS - inset,
        role: 'rarity-mark',
      });
      pip.setAttribute('data-index', String(index + 1));
      pip.setAttribute('data-state', filled ? 'filled' : 'empty');
    }
    drawText(group, 'OTTERS OF THE COAST™  © 2026', {
      x: zone.x + 215, y: zone.y, width: zone.width - 215, height: zone.height,
      steps: typographySteps(mapping, 'footer_brand'), role: 'sans_regular', fill: color(mapping, 'text/on-dark-muted'),
      family: 'Noto Sans', anchor: 'end', vertical: 'middle', singleLine: true, dataRole: 'footer-brand',
    });
  }

  /* ---------- artwork ---------- */

  function drawArtwork(parent, defs, card, zone, artwork, mapping, reviewBlocked, { cornerRadius = 2, clipSuffix }) {
    const { x, y, width, height } = zone;
    const clipId = `art-clip-${clipSuffix}`;
    const clip = el(defs, 'clipPath', { id: clipId });
    rect(clip, x, y, width, height, { radius: cornerRadius });
    if (artwork && artwork.href && !reviewBlocked) {
      el(parent, 'image', {
        x, y, width, height,
        preserveAspectRatio: 'xMidYMid slice',
        'clip-path': `url(#${clipId})`,
        href: artwork.href,
        'data-role': 'artwork',
      });
      const rim = el(parent, 'g', {
        'clip-path': `url(#${clipId})`,
        'data-role': 'artwork-warm-rim',
        'data-depth': C.ART_EDGE_WARMTH_DEPTH,
        'data-strength': C.ART_EDGE_WARMTH_OPACITY,
      });
      const depth = C.ART_EDGE_WARMTH_DEPTH;
      for (const [edge, edgeX, edgeY, edgeWidth, edgeHeight, gradient] of [
        ['left', x, y, depth, height, 'art-warm-left'],
        ['right', x + width - depth, y, depth, height, 'art-warm-right'],
        ['top', x, y, width, depth, 'art-warm-top'],
        ['bottom', x, y + height - depth, width, depth, 'art-warm-bottom'],
      ]) {
        const edgeElement = rect(rim, edgeX, edgeY, edgeWidth, edgeHeight, { fill: `url(#${gradient})`, role: 'artwork-warm-edge' });
        edgeElement.setAttribute('data-edge', edge);
        edgeElement.setAttribute('style', 'mix-blend-mode:multiply');
      }
      const shadow = rect(parent, x, y, width, C.ART_TOP_INNER_SHADOW_DEPTH, { fill: 'url(#art-top-inner-shadow)', role: 'artwork-top-inner-shadow' });
      shadow.setAttribute('clip-path', `url(#${clipId})`);
      shadow.setAttribute('data-edge', 'top');
      setAttr(shadow, 'data-depth', C.ART_TOP_INNER_SHADOW_DEPTH);
      setAttr(shadow, 'data-max-opacity', C.ART_TOP_INNER_SHADOW_OPACITY);
      return artwork.sha256 || '';
    }
    const placeholder = el(parent, 'g', { 'clip-path': `url(#${clipId})`, 'data-role': 'artwork-placeholder-group' });
    rect(placeholder, x, y, width, height, { fill: color(mapping, 'background/placeholder'), radius: cornerRadius, role: 'artwork-placeholder' });
    for (let offset = -Math.trunc(height); offset < Math.trunc(width); offset += 30) {
      el(placeholder, 'line', {
        x1: x + Math.max(offset, 0),
        y1: y + Math.max(-offset, 0),
        x2: x + Math.min(offset + height, width),
        y2: y + Math.min(height, height + offset),
        stroke: color(mapping, 'line/recessed'),
        'stroke-width': C.INTERNAL_PLACEHOLDER_HATCH_STROKE,
        opacity: 0.22,
        'data-role': 'artwork-placeholder-hatch',
      });
    }
    drawText(placeholder, reviewBlocked ? 'BILDREVIEW OFFEN' : 'ILLUSTRATION FEHLT', {
      x: x + 20, y: y + height / 2 - 18, width: width - 40, height: 36,
      steps: typographySteps(mapping, 'artwork_placeholder'), role: 'sans_bold', fill: color(mapping, 'text/secondary'),
      family: 'Noto Sans', anchor: 'middle', vertical: 'middle', singleLine: true,
    });
    return '';
  }

  /* ---------- content stack ---------- */

  function drawLabeledSection(parent, label, text, zone, mapping, accent, typographyRole, dataRole, fitted) {
    const { x, y, width, height } = zone;
    el(parent, 'line', {
      x1: x, y1: y + C.SECTION_DIVIDER_OFFSET, x2: x + width, y2: y + C.SECTION_DIVIDER_OFFSET,
      stroke: accent, 'stroke-width': C.ACCENT_RULE_STROKE_WIDTH,
      'data-role': 'section-divider', 'data-section': casefold(label),
    });
    drawText(parent, label, {
      x, y: y + C.SECTION_LABEL_Y_OFFSET, width: 160, height: 21,
      steps: typographySteps(mapping, 'section_label'), role: 'sans_bold', fill: accent, family: 'Noto Sans',
      singleLine: true, dataRole: 'section-label',
    });
    drawText(parent, text, {
      x, y: y + C.SECTION_BODY_TOP_OFFSET, width, height: height - 14,
      steps: typographySteps(mapping, typographyRole), role: 'regular', fill: color(mapping, 'text/primary'),
      dataRole, fitted,
    });
  }

  function planFlavor(cardId, text, zone, mapping) {
    const { y, width, height } = zone;
    if (!text.trim()) return { fit: null, dividerY: null, contentFrameBottom: y };
    let fit;
    try {
      fit = fitText(text, 'italic', typographySteps(mapping, 'flavor'), width, height - C.FLAVOR_TOP_CLEARANCE - C.FLAVOR_BOTTOM_INSET, {
        family: 'Noto Serif', flavorAware: true, field: 'flavor_text',
      });
    } catch (error) {
      throw new RenderError(`${cardId}: Flavor-Text passt nicht`, 'flavor_text');
    }
    const blockTop = y + height - C.FLAVOR_BOTTOM_INSET - fit.lines.length * fit.lineHeight;
    const dividerY = blockTop - C.FLAVOR_DIVIDER_GAP;
    if (dividerY < y) {
      throw new RenderError(`${cardId}: Flavor-Trenner passt nicht ohne Fallback (${dividerY.toFixed(4)} < ${y.toFixed(4)})`, 'flavor_text');
    }
    return { fit, dividerY, contentFrameBottom: dividerY - C.ACCENT_RULE_STROKE_WIDTH / 2 };
  }

  function contentStackFrame(cardId, mapping, flavorPlan) {
    const frame = mapping.geometry.content_stack_frame;
    const x = Number(frame.x);
    const top = Number(frame.y);
    const width = Number(frame.width);
    const freeAbove = Number(frame.free_above_ratio);
    const freeBelow = Number(frame.free_below_ratio);
    if (!(width > 0) || top >= flavorPlan.contentFrameBottom) throw new RenderError(`${cardId}: Ungültiger gemeinsamer Inhaltsframe`);
    if (freeAbove < 0 || freeBelow < 0 || Math.abs(freeAbove + freeBelow - 1) > 1e-9) {
      throw new RenderError('Inhaltsframe benötigt komplementäre Freiraumanteile');
    }
    return [x, top, width, freeAbove, freeBelow];
  }

  function balancedStackTop(cardId, { frameTop, frameBottom, stackHeight, freeAboveRatio, field }) {
    const frameHeight = frameBottom - frameTop;
    if (frameHeight <= 0 || stackHeight <= 0 || !(freeAboveRatio >= 0 && freeAboveRatio <= 1)) {
      throw new RenderError(`${cardId}: Ungültige Inhaltsblockgeometrie`, field);
    }
    const freeHeight = frameHeight - stackHeight;
    if (freeHeight <= 0) {
      throw new RenderError(
        `${cardId}: Inhaltsblock lässt keinen freien Raum für 45/55 und passt nicht ohne Fallback (${stackHeight.toFixed(4)} >= ${frameHeight.toFixed(4)})`,
        field,
      );
    }
    return frameTop + freeHeight * freeAboveRatio;
  }

  function contentStackGroup(parent, cardId, layoutKey, mapping, { flavorPlan, stackHeight, field }) {
    const [, frameTop, , freeAbove, freeBelow] = contentStackFrame(cardId, mapping, flavorPlan);
    const frameBottom = flavorPlan.contentFrameBottom;
    const stackTop = balancedStackTop(cardId, { frameTop, frameBottom, stackHeight, freeAboveRatio: freeAbove, field });
    const freeHeight = frameBottom - frameTop - stackHeight;
    const group = el(parent, 'g', {
      'data-role': 'content-stack',
      'data-layout': layoutKey,
      'data-frame-top': frameTop,
      'data-frame-bottom': frameBottom,
      'data-stack-top': stackTop,
      'data-stack-bottom': stackTop + stackHeight,
      'data-stack-height': stackHeight,
      'data-free-above': freeHeight * freeAbove,
      'data-free-below': freeHeight * freeBelow,
      'data-free-above-ratio': freeAbove,
      'data-free-below-ratio': freeBelow,
    });
    return [group, stackTop];
  }

  function drawProjectStack(parent, card, requirementsText, zones, mapping, accent, flavorPlan) {
    const cardId = card.card_id;
    const [frameX, , frameWidth] = contentStackFrame(cardId, mapping, flavorPlan);
    const spec = zones.content_stack;
    const requirementsFitHeight = Number(spec.requirements_fit_height);
    const goalFitHeight = Number(spec.goal_fit_height);
    const sectionGap = Number(spec.section_gap);
    if (!(goalFitHeight > 0) || !(requirementsFitHeight > 0) || sectionGap < 0) {
      throw new RenderError(`${cardId}: Ungültige Projekt-Stackgeometrie`);
    }
    const requirementsFit = fitText(requirementsText, 'regular', typographySteps(mapping, 'project_requirements'), frameWidth, requirementsFitHeight, {
      family: 'Noto Serif', field: 'requirements',
    });
    const goalFit = fitText(card.project_goal || '', 'regular', typographySteps(mapping, 'project_goal'), frameWidth, goalFitHeight, {
      family: 'Noto Serif', field: 'project_goal',
    });
    const requirementsHeight = requirementsFit.lines.length * requirementsFit.lineHeight;
    const goalHeight = goalFit.lines.length * goalFit.lineHeight;
    const headerSpan = C.SECTION_BODY_TOP_OFFSET - C.SECTION_LABEL_Y_OFFSET;
    const stackHeight = 2 * headerSpan + requirementsHeight + sectionGap + goalHeight;
    const [group, stackTop] = contentStackGroup(parent, cardId, 'project', mapping, { flavorPlan, stackHeight, field: 'project_goal' });
    setAttr(group, 'data-section-gap', sectionGap);
    group.setAttribute('data-section-order', 'anforderungen,projektziel');
    const requirementsZone = { x: frameX, y: stackTop - C.SECTION_LABEL_Y_OFFSET, width: frameWidth, height: requirementsHeight + 14 };
    const goalLabelTop = stackTop + headerSpan + requirementsHeight + sectionGap;
    const goalZone = { x: frameX, y: goalLabelTop - C.SECTION_LABEL_Y_OFFSET, width: frameWidth, height: goalHeight + 14 };
    drawLabeledSection(group, 'ANFORDERUNGEN', requirementsText, requirementsZone, mapping, accent, 'project_requirements', 'project-requirements-text', requirementsFit);
    drawLabeledSection(group, 'PROJEKTZIEL', card.project_goal || '', goalZone, mapping, accent, 'project_goal', 'project-goal-text', goalFit);
  }

  function drawFactorStack(parent, card, zones, mapping, flavorPlan) {
    const cardId = card.card_id;
    const key = familyKey(card, 'factor');
    const family = mapping.families[key];
    if (!family) throw new RenderError(`${cardId}: Unbekannte Faktorfamilie '${key}'`, 'factor_family');
    const [frameX, , frameWidth] = contentStackFrame(cardId, mapping, flavorPlan);
    const spec = zones.content_stack;
    const sideInset = Number(spec.text_side_inset);
    const carrierSize = Number(spec.carrier_size);
    const iconSize = Number(spec.icon_size);
    const paintedGap = Number(spec.painted_emblem_to_text_gap);
    const maxTextLines = Math.trunc(Number(spec.max_text_lines));
    const textWidthValue = frameWidth - 2 * sideInset;
    const factorSteps = typographySteps(mapping, 'factor_rules');
    const maxLineHeight = Math.max(...factorSteps.map((step) => step[1]));
    const textFit = fitText(card.rules_text, 'regular', factorSteps, textWidthValue, maxTextLines * maxLineHeight, {
      family: 'Noto Serif', field: 'rules_text',
    });
    if (textFit.lines.length > maxTextLines) throw new RenderError(`${cardId}: Faktor-Regeltext überschreitet ${maxTextLines} Zeilen`, 'rules_text');
    const textHeight = textFit.lines.length * textFit.lineHeight;
    const paintedCarrierHeight = carrierSize + C.STROKE_LINE;
    const stackHeight = paintedCarrierHeight + paintedGap + textHeight;
    const [stackGroup, stackTop] = contentStackGroup(parent, cardId, 'factor', mapping, { flavorPlan, stackHeight, field: 'rules_text' });
    setAttr(stackGroup, 'data-emblem-to-text-gap', paintedGap);
    const familyColor = color(mapping, family.color_token);
    const circleX = frameX + (frameWidth - carrierSize) / 2;
    const circleY = stackTop + C.STROKE_LINE / 2;
    const iconInset = (carrierSize - iconSize) / 2;
    const group = el(stackGroup, 'g', { 'data-role': 'factor-family-emblem', 'data-family': key });
    const carrier = ellipse(group, circleX, circleY, carrierSize, carrierSize, {
      fill: 'none', stroke: familyColor, strokeWidth: C.STROKE_LINE, opacity: C.FACTOR_EMBLEM_CARRIER_OPACITY,
    });
    carrier.setAttribute('data-role', 'factor-family-emblem-carrier');
    carrier.setAttribute('data-family', key);
    drawIcon(group, family.icon, circleX + iconInset, circleY + iconInset, iconSize, familyColor, {
      role: 'factor-family-emblem-symbol', opacity: C.FACTOR_EMBLEM_ICON_OPACITY, attributes: { 'data-family': key },
    });
    drawText(stackGroup, card.rules_text, {
      x: frameX + sideInset, y: stackTop + paintedCarrierHeight + paintedGap, width: textWidthValue, height: textHeight,
      steps: factorSteps, role: 'regular', fill: color(mapping, 'text/primary'), anchor: 'middle',
      dataRole: 'rules-text', fitted: textFit,
    });
  }

  function drawEventStack(parent, card, zones, mapping, flavorPlan) {
    const cardId = card.card_id;
    const [frameX, , frameWidth] = contentStackFrame(cardId, mapping, flavorPlan);
    const maxTextLines = Math.trunc(Number(zones.content_stack.max_text_lines));
    const eventSteps = typographySteps(mapping, 'event_rules');
    const maxLineHeight = Math.max(...eventSteps.map((step) => step[1]));
    const fit = fitText(card.rules_text, 'regular', eventSteps, frameWidth, maxTextLines * maxLineHeight, {
      family: 'Noto Serif', field: 'rules_text',
    });
    if (fit.lines.length > maxTextLines) throw new RenderError(`${cardId}: Ereignis-Regeltext überschreitet ${maxTextLines} Zeilen`, 'rules_text');
    const stackHeight = fit.lines.length * fit.lineHeight;
    const [group, stackTop] = contentStackGroup(parent, cardId, 'event', mapping, { flavorPlan, stackHeight, field: 'rules_text' });
    drawText(group, card.rules_text, {
      x: frameX, y: stackTop, width: frameWidth, height: stackHeight,
      steps: eventSteps, role: 'regular', fill: color(mapping, 'text/primary'), dataRole: 'rules-text', fitted: fit,
    });
  }

  function drawFlavor(parent, text, zone, mapping, accent, plan) {
    if (!plan.fit || plan.dividerY === null) return;
    const { x, y, width, height } = zone;
    drawText(parent, text, {
      x, y: y + C.FLAVOR_TOP_CLEARANCE, width, height: height - C.FLAVOR_TOP_CLEARANCE - C.FLAVOR_BOTTOM_INSET,
      steps: typographySteps(mapping, 'flavor'), role: 'italic', fill: color(mapping, 'text/secondary'),
      vertical: 'bottom', flavorAware: true, dataRole: 'flavor-text', fitted: plan.fit,
    });
    el(parent, 'line', {
      x1: x, y1: plan.dividerY, x2: x + width, y2: plan.dividerY,
      stroke: accent, 'stroke-width': C.ACCENT_RULE_STROKE_WIDTH, opacity: C.FLAVOR_RULE_OPACITY,
      'data-role': 'flavor-divider',
    });
  }

  /* ---------- whole card ---------- */

  function reviewFlags(cardId, mapping) {
    const gates = mapping.review_gates || {};
    return [
      (gates.content_blocked_card_ids || []).includes(cardId),
      (gates.artwork_blocked_card_ids || []).includes(cardId),
    ];
  }

  function resolveArtTreatment(mapping, zones) {
    const spec = mapping.art_treatment;
    if (!spec || String(spec.id) !== C.ART_TREATMENT) {
      throw new RenderError(`Layout und Renderer verwenden unterschiedliche Bildbehandlungen: ${spec && spec.id} != ${C.ART_TREATMENT}`);
    }
    const artSurface = zones.art_surface;
    const art = zones.art;
    if (Math.abs(art.width * 2 - art.height * 3) > 1e-6) throw new RenderError(`${spec.id}: Bildfenster ist nicht exakt 3:2`);
    return {
      treatment: String(spec.id),
      artSurface,
      art,
      matToken: String(spec.mat_color_token),
      matRadius: Number(spec.outer_radius),
      artRadius: Number(spec.art_radius),
    };
  }

  function cardFaceScale(profile) {
    const halfWidth = profile.master_svg.rectangles.vendor_safe.width / 2;
    return (halfWidth - C.CARD_FACE_SAFE_CLEARANCE) / (halfWidth - C.INNER_CARD_FIELD_INSET);
  }

  function cardFaceTransform(profile) {
    const trim = profile.master_svg.rectangles.trim;
    const centreX = trim.x + trim.width / 2;
    const centreY = trim.y + trim.height / 2;
    return `translate(${attrNumber(centreX)} ${attrNumber(centreY)}) scale(${cardFaceScale(profile).toFixed(12)}) `
      + `translate(${attrNumber(-centreX)} ${attrNumber(-centreY)})`;
  }

  function safeIdSuffix(cardId) {
    return String(cardId || 'karte').replace(/[^A-Za-z0-9_-]/g, '-');
  }

  /**
   * Build one card as an SVG element in the profile coordinate system.
   *
   * options.artwork: { href, sha256? } or null for the placeholder
   * options.rarityOverride: { label, marks } for cards without a print rarity
   * options.proof: draw trim and safe guides
   */
  function buildCardSvg(card, options = {}) {
    const { artwork = null, rarityOverride = null, proof = false } = options;
    const mapping = LAYOUT;
    const profile = DATA.profile;
    const viewBox = profile.master_svg.view_box;
    const layoutKey = layoutKeyFor(card);
    const zones = mapping.geometry.layouts[layoutKey];
    let polarityKey = '';
    if (layoutKey === 'event') {
      polarityKey = card.polarity || '';
      if (!polarityKey) throw new RenderError(`${card.card_id}: Polarität fehlt`, 'effect_template');
      if (!mapping.polarities[polarityKey]) throw new RenderError(`${card.card_id}: Unbekannte Polarität '${polarityKey}'`, 'effect_template');
    }
    const art = resolveArtTreatment(mapping, zones);
    const look = appearance(card, mapping, layoutKey);
    const accent = color(mapping, look.accentToken);
    const flavorText = card.flavor_text;
    if (typeof flavorText !== 'string') throw new RenderError(`${card.card_id || '<ohne ID>'}: flavor_text fehlt`, 'flavor_text');
    if (flavorText && !flavorText.trim()) throw new RenderError(`${card.card_id || '<ohne ID>'}: flavor_text enthält nur Leerraum`, 'flavor_text');
    const flavorPlan = planFlavor(card.card_id, flavorText, zones.flavor, mapping);
    const [contentBlocked, artworkBlocked] = reviewFlags(card.card_id, mapping);
    const idSuffix = safeIdSuffix(card.card_id);

    const root = el(null, 'svg', {
      version: '1.1',
      width: '69.6mm',
      height: '95mm',
      viewBox: viewBox.join(' '),
      'data-renderer': `dhk-card-renderer-web/${WEB_RENDERER_VERSION}`,
      'data-card-id': card.card_id,
      'data-mode': 'preview',
      'data-art-treatment': art.treatment,
      'data-icon-manifest-sha256': DATA.icon_manifest_sha256,
      'data-polarity': polarityKey || null,
    });
    el(root, 'title').textContent = `${card.card_id} · ${card.name}`;
    const metadata = el(root, 'metadata');
    const defs = el(root, 'defs');
    defineMaterialDefs(defs, mapping);
    const trim = profile.master_svg.rectangles.trim;
    const trimClipId = `trim-clip-${idSuffix}`;
    const trimClip = el(defs, 'clipPath', { id: trimClipId });
    rect(trimClip, trim.x, trim.y, trim.width, trim.height);
    rect(root, 0, 0, viewBox[2], viewBox[3], { fill: color(mapping, 'background/outer-bleed'), role: 'full-bleed-background' });
    rect(root, trim.x, trim.y, trim.width, trim.height, { fill: color(mapping, 'background/shell'), role: 'trim-background' });
    const vendorSafe = profile.master_svg.rectangles.vendor_safe;
    const designClip = el(root, 'g', { id: 'card-design-clip', 'clip-path': `url(#${trimClipId})` });
    const face = el(designClip, 'g', { id: 'card-face', transform: cardFaceTransform(profile) });
    rect(
      face,
      vendorSafe.x + C.INNER_CARD_FIELD_INSET,
      vendorSafe.y + C.INNER_CARD_FIELD_INSET,
      vendorSafe.width - 2 * C.INNER_CARD_FIELD_INSET,
      vendorSafe.height - 2 * C.INNER_CARD_FIELD_INSET,
      { fill: 'url(#inner-card-field-gradient)', radius: C.INNER_CARD_FIELD_RADIUS, role: 'inner-card-field' },
    );
    const scaleX = viewBox[2] / mapping.geometry.document.width;
    const scaleY = viewBox[3] / mapping.geometry.document.height;
    const design = el(face, 'g', { id: 'card-design', transform: `scale(${scaleX.toFixed(12)} ${scaleY.toFixed(12)})` });

    flatPlate(design, zones.title_surface, mapping, accent, { fillToken: 'background/paper-raised', role: 'title-panel', corners: 'top', radius: C.TITLE_FOOTER_CORNER_RADIUS, showAccent: false });
    flatPlate(design, zones.type_surface, mapping, accent, { fillToken: 'background/paper-raised', role: 'type-panel' });
    flatPlate(design, zones.content_surface, mapping, accent, { fillToken: 'background/paper-raised', role: 'content-panel' });
    flatPlate(design, zones.footer_surface, mapping, accent, { fillToken: 'background/shell-raised-bottom', role: 'footer-panel', corners: 'bottom', radius: C.TITLE_FOOTER_CORNER_RADIUS, showAccent: false });

    rect(design, art.artSurface.x, art.artSurface.y, art.artSurface.width, art.artSurface.height, {
      fill: color(mapping, art.matToken), radius: art.matRadius, role: 'art-mat',
    });
    drawTitle(design, card.name, zones.title, mapping);
    drawIdentityStamp(design, zones, mapping, layoutKey);
    const artworkSha = drawArtwork(design, defs, card, art.art, artwork, mapping, artworkBlocked, { cornerRadius: art.artRadius, clipSuffix: idSuffix });
    drawPlateKeyline(design, art.artSurface.x, art.artSurface.y, art.artSurface.width, art.artSurface.height, mapping, {
      plateRole: 'art-mat', corners: 'none', radius: art.matRadius,
    });
    drawTypeLine(design, card, zones, mapping, accent, look, layoutKey);

    if (layoutKey === 'project') {
      let requirementsText = card.rules_text;
      if (casefold(requirementsText).startsWith('abschluss:')) requirementsText = requirementsText.slice('Abschluss:'.length).trimStart();
      drawProjectStack(design, card, requirementsText, zones, mapping, accent, flavorPlan);
    } else if (layoutKey === 'factor') {
      drawFactorStack(design, card, zones, mapping, flavorPlan);
    } else {
      drawEventStack(design, card, zones, mapping, flavorPlan);
    }
    drawFlavor(design, flavorText, zones.flavor, mapping, accent, flavorPlan);
    drawFooter(design, card, zones.footer, mapping, rarityOverride);

    if (contentBlocked || artworkBlocked) {
      const labels = [];
      if (contentBlocked) labels.push('INHALT');
      if (artworkBlocked) labels.push('BILD');
      const badgeWidth = 170;
      const badgeInset = 7;
      const badgeX = art.art.x + art.art.width - badgeWidth - badgeInset;
      const badgeY = art.art.y + badgeInset;
      rect(design, badgeX, badgeY, badgeWidth, 30, { fill: '#F5EEDB', stroke: accent, strokeWidth: C.STROKE_LINE, radius: 3, opacity: 0.95, role: 'review-badge' });
      drawText(design, `REVIEW · ${labels.join('+')}`, {
        x: badgeX + 6, y: badgeY + 4, width: 158, height: 22,
        steps: typographySteps(mapping, 'review_badge'), role: 'sans_bold', fill: accent, family: 'Noto Sans',
        anchor: 'middle', vertical: 'middle', singleLine: true, dataRole: 'review-badge-label',
      });
    }

    const usedIcons = {};
    design.querySelectorAll('[data-icon]').forEach((node) => {
      usedIcons[node.getAttribute('data-icon')] = {
        file: node.getAttribute('data-icon-source'),
        sha256: node.getAttribute('data-icon-sha256'),
      };
    });
    metadata.textContent = JSON.stringify({
      artwork_blocked: artworkBlocked,
      artwork_sha256: artworkSha,
      art_treatment: art.treatment,
      card_id: card.card_id,
      content_blocked: contentBlocked,
      icon_manifest_sha256: DATA.icon_manifest_sha256,
      icons: Object.fromEntries(Object.keys(usedIcons).sort().map((key) => [key, usedIcons[key]])),
      layout: layoutKey,
      layout_config_sha256: mapping._sha256,
      port_of_renderer: C.RENDERER_VERSION,
      port_of_renderer_sha256: DATA.renderer.sha256,
      profile_sha256: profile._sha256,
      renderer: WEB_RENDERER_VERSION,
    });

    if (proof) {
      const proofGroup = el(root, 'g', { id: 'proof-guides', 'pointer-events': 'none' });
      const [proofSize, proofLineHeight, proofStatus] = typographySteps(mapping, 'proof_label')[0];
      for (const [key, guideColor, label, yOffset, anchor] of [
        ['trim', '#00AEEF', 'SCHNITT', 16, 'start'],
        ['vendor_safe', '#E5007D', 'LIEFERANTEN-SAFE', 16, 'end'],
        ['internal_text_safe', '#F4B400', 'DHK-SAFE +1 MM', 34, 'start'],
      ]) {
        const box = profile.master_svg.rectangles[key];
        rect(proofGroup, box.x, box.y, box.width, box.height, { stroke: guideColor, strokeWidth: C.STROKE_LINE, opacity: 0.95, role: `proof-${key}` });
        el(proofGroup, 'text', {
          x: anchor === 'start' ? box.x + 6 : box.x + box.width - 6,
          y: box.y + yOffset,
          fill: guideColor,
          'font-family': 'Noto Sans',
          'font-size': proofSize,
          'font-weight': 700,
          'letter-spacing': trackingForText(label, proofSize, 'Noto Sans'),
          'font-feature-settings': hasDigit(label) ? "'tnum' 1, 'lnum' 1" : null,
          'text-anchor': anchor,
          'data-role': `proof-label-${key}`,
          'data-font-role': 'sans_bold',
          'data-type-size-step': proofSize,
          'data-line-height': proofLineHeight,
          'data-type-step-status': proofStatus,
        }).textContent = label;
      }
    }
    return root;
  }

  global.BusfaktorRenderer = {
    RenderError,
    buildCardSvg,
    loadFonts,
    measure,
    version: WEB_RENDERER_VERSION,
    data: DATA,
  };
})(window);
