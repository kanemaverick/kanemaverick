"""Render the terminal card from public GitHub metrics and a fixed ASCII avatar."""

from datetime import date, datetime, timezone
from html import escape
from itertools import groupby
from pathlib import Path

from public_stats import fetch_stats


ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
LOGIN = "kanemaverick"
THEMES = {
    "dark": dict(bg="#101619", border="#303b3e", fg="#e4e9e6", muted="#a1b0ad",
                 accent="#8bd4bc", photo="#101619", ink="#d5e2da"),
    "light": dict(bg="#f8faf8", border="#cfd8d2", fg="#1c302b", muted="#52665e",
                  accent="#16664d", photo="#172023", ink="#dae5dd"),
}


def text(x, y, value, role="fg", size=15, weight=400):
    return (f'<text x="{x}" y="{y}" class="{role}" font-size="{size}" '
            f'font-weight="{weight}">{escape(value)}</text>')


def shade(char):
    ramp = " .:;-=+itfoOX%#@"
    return ramp.index(char) * 4 // (len(ramp) - 1)


def portrait(rows, x, y, size):
    # The glyph grid keeps the chalkboard, shirt and hands in their original proportions.
    width = max(map(len, rows))
    dy = 256 / len(rows)
    parts = [f'<g aria-hidden="true" transform="translate({x} {y}) scale({size / 272:.5f})">',
             '<rect width="272" height="272" rx="3" class="photo"/>']
    for i, row in enumerate(rows):
        runs = (f'<tspan opacity="{0.30 + tone * 0.175:.3f}">{escape("".join(group))}</tspan>'
                for tone, group in groupby(row.ljust(width), key=shade))
        parts.append(f'<text x="8" y="{8 + (i + 0.86) * dy:.2f}" class="ink glyph" '
                     f'textLength="256" lengthAdjust="spacingAndGlyphs" '
                     f'xml:space="preserve">{"".join(runs)}</text>')
    parts.append('</g>')
    return parts


def palette(theme):
    colors = THEMES[theme]
    fills = " ".join(f".{name} {{fill:{value}}}" for name, value in colors.items())
    return fills + f' .rule, .frame {{stroke:{colors["border"]}}}'


def render(stats, rows, mobile, today):
    width, height = (376, 610) if mobile else (840, 424)
    info_x, value_x = (20, 119) if mobile else (324, 449)
    top = 249 if mobile else 40
    cell = 23 if mobile else 25
    body_size = 13 if mobile else 15
    days = (today - date.fromisoformat(stats["joined"])).days
    profile = [
        ("Name", "Kane Xie / KM"),
        ("Host", "Tongji University"),
        ("Major", "Marine Science"),
        ("Focus", "Underwater robotics"),
        ("Interests", "AI, physics, ocean engineering"),
        ("Languages", ", ".join(stats["languages"]) or "—"),
        ("Contact", "kanemaverickai@gmail.com"),
    ]
    activity = [
        ("Uptime", f'{days:,} days on GitHub'),
        ("Repos", f'{stats["repo_count"]:,} public'),
        ("Stars", f'{stats["stars"]:,} received'),
        ("Commits", f'{stats["commits"]:,}'),
        ("Lines", f'+{stats["added"]:,} / −{stats["removed"]:,}'),
    ]
    style = palette("light") + " @media (prefers-color-scheme: dark) {" + palette("dark") + "}"
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Kane Xie — GitHub profile</title>',
        '<desc id="desc">' + escape(". ".join(f"{k}: {v}" for k, v in profile + activity)) + '</desc>',
        '<style>text {font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace} '
        '.glyph {font-family: Menlo, Consolas, "Liberation Mono", monospace; font-size: 9px; '
        'font-weight: 700; white-space: pre} ' + style + '</style>',
        f'<rect x="0.5" y="0.5" width="{width-1}" height="{height-1}" rx="6" '
        'class="bg frame"/>',
        text(20 if mobile else 24, 28 if mobile else 39, '~ $ neofetch', 'muted', 13),
    ]
    parts.extend(portrait(rows, 94 if mobile else 24, 39 if mobile else 62, 188 if mobile else 272))
    if not mobile:
        parts.extend([text(26, 369, '“My job is wind,', 'muted', 14),
                      text(26, 390, 'so you gotta feel it.”', 'muted', 14)])
    parts.extend([
        text(info_x, top, f'{LOGIN}@github', 'accent', 21 if mobile else 24, 600),
        f'<path d="M {info_x} {top + 14} H {width - (20 if mobile else 24)}" '
        'class="rule"/>',
    ])
    first_y = top + (42 if mobile else 46)
    for i, (label, value) in enumerate(profile):
        y = first_y + cell * i
        parts.extend([text(info_x, y, label, "muted", body_size),
                      text(value_x, y, value, size=body_size)])
    heading_y = first_y + cell * len(profile) + 16
    parts.extend([
        text(info_x, heading_y, "GitHub stats", "accent", body_size, 600),
        f'<path d="M {info_x + (110 if mobile else 132)} {heading_y - 4} H {width - (20 if mobile else 24)}" '
        'class="rule"/>',
    ])
    for i, (label, value) in enumerate(activity):
        y = heading_y + 28 + cell * i
        parts.extend([text(info_x, y, label, "muted", body_size),
                      text(value_x, y, value, size=body_size)])
    parts.append('</svg>')
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    metrics = fetch_stats(LOGIN)
    ascii_rows = (ASSETS / "portrait.txt").read_text(encoding="utf-8").splitlines()
    utc_date = datetime.now(timezone.utc).date()
    for compact in (False, True):
        layout = "mobile" if compact else "desktop"
        svg = render(metrics, ascii_rows, compact, utc_date)
        (ASSETS / f"{layout}.svg").write_text(svg, encoding="utf-8")
