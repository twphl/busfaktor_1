"""Fill `<!-- prefix:name -->` regions of a hand-written page.

The pages of the website are hand-written HTML; only marked regions inside
them are generated. This keeps the generated part honest: a missing or
doubled marker stops the build instead of writing the fragment somewhere
unexpected. `rules_page.py` uses it for the rules, `site_chrome.py` for the
navigation and the footer.
"""
import textwrap


def fill(page, prefix, fragments, label):
    """Return `page` with each `fragments[name]` written between its markers."""
    for name, fragment in fragments.items():
        start, end = f'<!-- {prefix}:{name} -->', f'<!-- /{prefix}:{name} -->'
        if page.count(start) != 1 or page.count(end) != 1:
            raise ValueError(f'{label}: Markierung {prefix}:{name} fehlt oder ist doppelt.')
        head, rest = page.split(start)
        _, tail = rest.split(end)
        if '\n' in fragment:
            line = head[head.rfind('\n') + 1:]
            indent = line[:len(line) - len(line.lstrip())]
            fragment = '\n' + textwrap.indent(fragment, indent) + '\n' + indent
        page = head + start + fragment + end + tail
    return page
