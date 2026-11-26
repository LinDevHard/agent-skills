# Styles

Each style is a recipe for the whole series: fonts, background, how colour changes from frame to frame, decor,
device. Previews (six Pixstage screens, 2-wide cover) are in `assets/previews/<style>.jpg`; show the one you
propose to the user.

| Style | Looks like | Pick it when |
|---|---|---|
| `sketch` | Off-white, hand-lettered caps with a colour marker behind the last word, doodles across every border, slightly turned phones | Friendly consumer apps, creative tools, anything playful |
| `tone` | Each frame tinted from its own shot, high-contrast serif caption, large devices | Apps with colourful, varied screens (themes, photos, media); calm, premium feel |
| `poster` | Near-black frames, heavy uppercase caption, the brightest brand colour on the last word, brand glow on the cover | Fitness, finance, games-adjacent, dark-UI apps |
| `minimal` | Soft brand-tinted gradients, clean sans caption, one large device | Utilities and productivity; when unsure |

## What you may override

In `series.json`, `"style": {"name": "tone", "overrides": {...}}` merges into the style's `style.json`:

- `"background": {"mode": "solid", "colors": ["#101418"]}` — modes: `solid`, `gradient`, `soft-brand`,
  `shot-tone`, `cover-gradient` (with `"base"` for the dark colour).
- `"caption": {"size": 0.09}` — caption size as a share of the frame's caption unit (frame width on phones).
- `"device": {"kind": "none"}` — `phone`, `none` (rounded screenshot with a shadow); `"rotate": [-3, 3]` turns
  devices frame by frame.
- `"frameColors": "cycle-brand"` and `"accent": "brightest"` — how the accent colour is chosen.
- `"decor": ["swirl", "arrow"]` — doodles placed across each border; `[]` for none. Kinds are the SVG files in
  `assets/decor/`. Explicit `"decor"` items in the series replace the automatic ones.

Brand colours come from `app.brand` in the series; take them from the app's theme or icon (`palette.py` can
read dominant colours from an image).

## Frame shapes

Layouts follow the frame's shape, not the target name: tall (9:16, 10:16) puts the caption on top and lets
devices run off the bottom; square (1:1, 3:4) puts the caption on top with smaller devices; wide (16:9, 4:3)
puts the caption in a left column and the device on the right. Captions shrink until their longest word fits;
a word longer than the column is broken and check.py warns.
