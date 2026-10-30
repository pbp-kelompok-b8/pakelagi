import markdown
import nh3
from django.utils.html import escape


MARKDOWN_TAGS = {
    'a', 'blockquote', 'br', 'code', 'div', 'em', 'h1', 'h2', 'h3',
    'h4', 'h5', 'h6', 'hr', 'img', 'li', 'ol', 'p', 'pre', 'strong',
    'table', 'tbody', 'td', 'th', 'thead', 'tr', 'ul',
}
MARKDOWN_ATTRIBUTES = {
    'a': {'href', 'title'},
    'img': {'src', 'alt', 'title'},
    'div': {'class'},
    'code': {'class'},
    **{f'h{level}': {'id'} for level in range(1, 7)},
}


def render_guide_markdown(content):
    """Escape raw HTML, then sanitize generated HTML and TOC with a URL allowlist."""
    md = markdown.Markdown(extensions=['toc', 'tables', 'nl2br'])
    html = md.convert(escape(content))

    def sanitize(value):
        return nh3.clean(
            value,
            tags=MARKDOWN_TAGS,
            attributes=MARKDOWN_ATTRIBUTES,
            url_schemes={'http', 'https', 'mailto'},
        )

    return sanitize(html), sanitize(md.toc)
