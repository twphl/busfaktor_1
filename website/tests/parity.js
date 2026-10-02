/* Compares renderer.js with the Python renderer, element by element.
 * Called from check_renderer_parity.mjs with the Python SVGs by card ID. */
(function () {
  'use strict';
  const NUMBER = /-?\d+(?:\.\d+)?(?:e-?\d+)?/gi;
  // Pillow rounds every glyph advance to 1/64 px at four times the layout
  // size; canvas measures unrounded. Positions derived from text widths may
  // therefore differ by a few thousandths of a layout unit (1 unit = 0.1 mm).
  const FORMAT_TOLERANCE = 0.0001;
  const MEASURE_TOLERANCE = 0.05;

  function numericDeviation(a, b) {
    const left = a.match(NUMBER) || [];
    const right = b.match(NUMBER) || [];
    if (left.length !== right.length || a.replace(NUMBER, '#') !== b.replace(NUMBER, '#')) return Infinity;
    return Math.max(0, ...left.map((value, index) => Math.abs(Number(value) - Number(right[index]))));
  }

  function compareNodes(reference, candidate, path, report) {
    if (reference.localName !== candidate.localName) {
      report.structure.push(`${path}: <${reference.localName}> ≠ <${candidate.localName}>`);
      return;
    }
    const isRoot = path === 'svg';
    const skip = new Set(isRoot ? ['data-renderer', 'xmlns'] : []);
    const names = new Set([...reference.getAttributeNames(), ...candidate.getAttributeNames()]);
    for (const name of names) {
      if (skip.has(name)) continue;
      const a = reference.getAttribute(name);
      const b = candidate.getAttribute(name);
      if (a === b) continue;
      const deviation = a === null || b === null ? Infinity : numericDeviation(a, b);
      if (deviation <= FORMAT_TOLERANCE) report.rounding += 1;
      else if (deviation <= MEASURE_TOLERANCE) {
        report.measured += 1;
        report.maxDeviation = Math.max(report.maxDeviation, deviation);
      } else report.attributes.push(`${path} @${name}: ${a} ≠ ${b}`);
    }
    if (reference.localName === 'metadata') return;
    if (['tspan', 'title', 'text'].includes(reference.localName)) {
      const ownText = (node) => [...node.childNodes].filter((child) => child.nodeType === 3).map((child) => child.data).join('');
      if (ownText(reference) !== ownText(candidate)) {
        report.text.push(`${path}: „${ownText(reference)}“ ≠ „${ownText(candidate)}“`);
      }
    }
    const left = [...reference.children];
    const right = [...candidate.children];
    if (left.length !== right.length) {
      report.structure.push(`${path}: ${left.length} ≠ ${right.length} Kindelemente`);
      return;
    }
    left.forEach((child, index) => {
      const role = child.getAttribute('data-role');
      compareNodes(child, right[index], `${path}/${child.localName}${role ? `[${role}]` : ''}#${index}`, report);
    });
  }

  window.runParity = async function runParity(references) {
    await BusfaktorRenderer.loadFonts('../');
    const parser = new DOMParser();
    const results = {};
    for (const card of window.CARDS) {
      const report = { structure: [], attributes: [], text: [], rounding: 0, measured: 0, maxDeviation: 0, error: null };
      try {
        const candidate = BusfaktorRenderer.buildCardSvg(card, { artwork: null });
        const reference = parser.parseFromString(references[card.card_id], 'image/svg+xml').documentElement;
        compareNodes(reference, candidate, 'svg', report);
      } catch (error) {
        report.error = String(error && error.stack || error);
      }
      results[card.card_id] = report;
    }
    return results;
  };
})();
