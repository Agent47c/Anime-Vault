# Manga Light — neumorphic reference analysis

Reviewed all five supplied `code.html` files and their screen images in
`Light Theme (Manga Brutalism)` on 14 November 2026. No separate folder named
Adidas/Neomorphic was present; this analysis covers the supplied Manga screens.

## Shared material and lighting

The light screens use a paper-grey canvas (`#EEF0F5`), near-white raised faces,
cool grey shadows (`166,175,195`) below/right, and white highlights above/left.
This paired lighting makes controls look moulded from the same material. It is
different from a single dark drop shadow beneath a flat card.

| Treatment | Supplied CSS | Use |
|---|---|---|
| Small raised | Lower/right 2–3 px offset, 6–7 px blur; upper/left −2 px white highlight | Header, small controls |
| Raised | Lower/right 5–6 px, 14–16 px blur; upper/left −4 px white highlight | Main panels and poster areas |
| Large raised | 10 px / 24 px lower shadow; −6 px / 18 px highlight | Larger Details/Edit surfaces |
| Sunken | Inset 3 px / 6 px grey and −2 px / 5 px white | Search, metadata fields, linked-record card |
| Deep sunken | Inset 4 px / 8 px shadow | Deeper field/track surfaces |
| Neutral button | Two outer shadows; larger shadows on hover; inset shadow while pressed | Back, secondary actions, rail |
| Pink button | Grey outer shadow plus pink glow; stronger glow on hover | Primary actions |

Transitions in Updates/Rematch are 150–180 ms for buttons. The rail expands over
the content, rather than changing its layout. Blur/fade are presentation effects,
not disabled states: every navigation item remains reachable by hover and keyboard.

## Per-screen mapping

- **Library:** raised shell, search well, poster frames, paper hero and raised
  action controls. Its HTML still contains dark-mode shadow utilities; the light
  screenshot remains authoritative, as recorded in the master contract.
- **Updates:** small raised header/buttons, white update cards with a pink edge;
  selected chips and saved disposition labels. Its rail HTML defines expansion,
  opacity, blur and slight shrink; the user's later instructions override the
  original uniform blur with selected-item distance falloff.
- **Details:** raised hero/poster and local-release rows; inset personal-status
  track/notes; primary playback accent; white episode cards.
- **Edit Entry:** sunken title/genre/synopsis/folder/notes fields, raised poster
  and image actions, inset status/rating band, primary Save.
- **Rematch:** raised dotted white canvas, sunken currently-linked/search panels,
  selected pink-outline result, raised footer actions.

## Implementation audit and limits

The 15 November master-control correction adds paired white upper-left and grey
lower-right shadows through `components/neumorphic.py`. Two small raised/inset
tiles are generated once and reused through nine-slice painting. The search
field, filter track and disabled/pressed pagination controls use inset depth;
sort/select, page numbers, refresh and sidebar tiles use raised depth.

Tracks and the pagination panel paint their own depth instead of nesting parent
and child graphics effects: nested Qt effects suppressed the button shadows.
The navigation effect paints the same cached material before its existing blur.
Large scrolling views receive no new whole-view shadow or blur effects. Some
older poster surfaces still use a single drop shadow. Windows DPI, font metrics
and Qt compositing can differ from CSS; pixel-perfect equivalence is not claimed.

The latest visibility correction keeps the selected item at full opacity, its
immediate neighbours at 50%, and farther items faintly visible (30% minimum).
Hovered/focused items temporarily reveal themselves for navigation. Leaving the
rail restores the closed icon strip. High contrast/reduced motion retain clear
controls. Collection groups use the same selected-item rule when a tag is active.
