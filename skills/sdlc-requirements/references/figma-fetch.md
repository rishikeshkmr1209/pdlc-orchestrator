# Figma Design Fetch Procedure

Fetch the Figma design referenced in `pipeline_state_<ticket>.json figma.link`. Make **exactly one call** — no chaining, no retries with a different method.

## IRON LAW: One Call, Complete Data

Never combine `view_node` + REST, or `add_figma_file` + `view_node`. Each scenario below is a single self-contained call that returns everything needed. Pick one scenario and stop.

---

## Fetch Strategy

**Decision:** both REST and MCP use the same Figma API key stored in `~/.claude.json` under the MCP server's `env` config. The only factor that determines which scenario to use is whether a `node-id` is present in the URL.

### Pre-flight check — ask for node-scoped URL if missing

Before fetching, inspect the Figma URL from `pipeline_state_<ticket>.json`:

- If `node-id=` **is present** → proceed to Scenario A directly.
- If `node-id=` **is absent** → **stop and ask the user:**

  > The Figma link in this ticket points to the whole file, not a specific component. For complete layer extraction (no depth truncation), please share a node-scoped URL:
  > 1. Open the Figma file
  > 2. Right-click the target component/frame → **Copy link to selection**
  > 3. Paste the new URL here
  >
  > Press **Enter** to skip and continue with `depth=6` (may miss layers nested deeper than 6 levels).

  - If the user provides a node-scoped URL → update `pipeline_state_<ticket>.json figma.link` with the new URL and proceed to Scenario A.
  - If the user skips → proceed to Scenario B with `depth=6`.

---

### Scenario A — node-id present in URL (primary path)

Use the REST API scoped to the target node. Depth is not capped — omit the `depth` parameter to get the full subtree, which is required for deeply-nested components.

> **Why no depth?** The `ids={node_id}` parameter already scopes the response to just that node's subtree (not the whole file). Without a depth cap, we get all descendant layers — necessary for components nested deeper than 6 levels. This makes exactly **one API call** and cannot trigger rate limiting.
>
> **If the Figma URL has no node-id** (designer linked the whole file): fall through to Scenario B. Never use Scenario A against a whole-file URL without a node-id — the response would be the entire file.
>
> **If the response is unexpectedly large** (>2 MB): the designer likely linked a full-page frame. Ask them to right-click the specific component in Figma → "Copy link to selection" to get a node-scoped URL.

```bash
python3 << 'EOF'
import json, re, urllib.request, os

state = json.load(open('docs/artifacts/<ticket>/.state/pipeline_state_<ticket>.json'))
url = state['figma']['link']

# Read API key from ~/.claude.json MCP server env config
api_key = ''
try:
    cfg = json.load(open(os.path.expanduser('~/.claude.json')))
    for proj in cfg.get('projects', {}).values():
        for srv in proj.get('mcpServers', {}).values():
            api_key = srv.get('env', {}).get('FIGMA_API_KEY', '')
            if api_key: break
        if api_key: break
except: pass

# Extract file/branch key (branch takes priority over file key)
branch = re.search(r'/branch/([A-Za-z0-9]+)', url)
file_  = re.search(r'/(?:file|design)/([A-Za-z0-9]+)', url)
key = branch.group(1) if branch else (file_.group(1) if file_ else None)

# Extract node-id
node_m = re.search(r'node-id=([^&]+)', url)
node_id = node_m.group(1).replace('%3A', '-') if node_m else None

# No depth parameter — fetch complete subtree for full component data
req = urllib.request.Request(
    f'https://api.figma.com/v1/files/{key}/nodes?ids={node_id}',
    headers={'X-Figma-Token': api_key}
)
with urllib.request.urlopen(req) as r:
    print(r.read().decode())
EOF
```

Parse the full JSON response using the `extract_component_specs()` function below.

### Scenario B — no node-id in URL (fallback)

Run the same extraction script — it automatically falls back to the full-file REST endpoint when no node-id is present in the URL:

```bash
python3 claude-master-plugin/scripts/figma-extract.py <ticket>
```

The script uses `/v1/files/{key}?depth=6` when no node-id is found. `depth=6` covers most real-world component nesting (Document → Page → Frame → Section → Component → Inner Frame → Element) while keeping the payload bounded. For components nested deeper than 6 levels, ask the designer to right-click the specific component in Figma → "Copy link to selection" to get a node-scoped URL, then re-run as Scenario A (no depth cap).

---

## Complete Figma → CSS Property Map

This is the authoritative mapping. Every property in this table MUST be extracted when present.

### Layout & Flexbox

| Figma field | Values | CSS output |
|-------------|--------|-----------|
| `layoutMode` | `"HORIZONTAL"` | `display: flex; flex-direction: row` |
| `layoutMode` | `"VERTICAL"` | `display: flex; flex-direction: column` |
| `layoutMode` | `"NONE"` | `display: block` (default, no flex) |
| `primaryAxisAlignItems` | `"MIN"` | `justify-content: flex-start` |
| `primaryAxisAlignItems` | `"CENTER"` | `justify-content: center` |
| `primaryAxisAlignItems` | `"MAX"` | `justify-content: flex-end` |
| `primaryAxisAlignItems` | `"SPACE_BETWEEN"` | `justify-content: space-between` |
| `counterAxisAlignItems` | `"MIN"` | `align-items: flex-start` |
| `counterAxisAlignItems` | `"CENTER"` | `align-items: center` |
| `counterAxisAlignItems` | `"MAX"` | `align-items: flex-end` |
| `counterAxisAlignItems` | `"STRETCH"` | `align-items: stretch` |
| `counterAxisAlignItems` | `"BASELINE"` | `align-items: baseline` |
| `layoutWrap` | `"WRAP"` | `flex-wrap: wrap` |
| `layoutWrap` | `"NO_WRAP"` | `flex-wrap: nowrap` |
| `itemSpacing` | N px | `gap: Npx` |
| `counterAxisSpacing` | N px | `column-gap: Npx` (when wrap is on) |

### Sizing

| Figma field | Values | CSS output |
|-------------|--------|-----------|
| `layoutSizingHorizontal` | `"FIXED"` | `width: <width>px` |
| `layoutSizingHorizontal` | `"HUG"` | `width: fit-content` |
| `layoutSizingHorizontal` | `"FILL"` | `width: 100%` or `flex: 1` |
| `layoutSizingVertical` | `"FIXED"` | `height: <height>px` |
| `layoutSizingVertical` | `"HUG"` | `height: fit-content` |
| `layoutSizingVertical` | `"FILL"` | `height: 100%` or `flex: 1` |
| `width` + `height` | N px | Use when `layoutSizingH/V` is FIXED or node has no auto-layout parent |

### Spacing

| Figma field | CSS output |
|-------------|-----------|
| `paddingTop` | `padding-top: Npx` |
| `paddingBottom` | `padding-bottom: Npx` |
| `paddingLeft` | `padding-left: Npx` |
| `paddingRight` | `padding-right: Npx` |
| All four equal | `padding: Npx` (shorthand) |
| Top=Bottom, Left=Right | `padding: VNpx HNpx` (shorthand) |

### Overflow & Visibility

| Figma field | Values | CSS output |
|-------------|--------|-----------|
| `clipsContent` | `true` | `overflow: hidden` |
| `clipsContent` | `false` | `overflow: visible` |
| `visible` | `false` | `display: none` |
| `opacity` | 0–1 | `opacity: X` (omit if 1.0) |

### Corner Radius

| Figma field | CSS output |
|-------------|-----------|
| `cornerRadius` (all equal) | `border-radius: Npx` |
| `topLeftRadius`, `topRightRadius`, `bottomRightRadius`, `bottomLeftRadius` (mixed) | `border-radius: TLpx TRpx BRpx BLpx` |

### Colors & Fills

| Figma field / fill type | CSS output |
|------------------------|-----------|
| `fills[].type == "SOLID"` | `background-color: rgba(r,g,b,a)` or `color:` for text |
| `fills[].type == "GRADIENT_LINEAR"` | `background: linear-gradient(angle, stop1, stop2, ...)` |
| `fills[].type == "GRADIENT_RADIAL"` | `background: radial-gradient(circle, stop1, stop2, ...)` |
| `fills[].type == "GRADIENT_ANGULAR"` | `background: conic-gradient(stop1, stop2, ...)` |
| `fills[].type == "IMAGE"` | `background-image: url(...)` — note: asset URL from Figma |
| `fills[].opacity` | Multiply with `color.a` to get final alpha |
| `blendMode` (non-NORMAL) | `mix-blend-mode: <value>` |

Figma color conversion: `r,g,b` are 0–1 floats → multiply by 255 and round. `a` is 0–1 → use directly in rgba. Final opacity = `fill.opacity × fill.color.a`.

### Borders & Strokes

| Figma field | CSS output |
|-------------|-----------|
| `strokeWeight` (uniform) | `border-width: Npx` |
| `strokeTopWeight` | `border-top-width: Npx` |
| `strokeBottomWeight` | `border-bottom-width: Npx` |
| `strokeLeftWeight` | `border-left-width: Npx` |
| `strokeRightWeight` | `border-right-width: Npx` |
| `strokes[].color` | `border-color: rgba(r,g,b,a)` |
| `strokeAlign == "INSIDE"` | Add note: element needs `box-sizing: border-box` |
| `strokeAlign == "OUTSIDE"` | Add note: element needs `outline` or wrapper |
| `strokeAlign == "CENTER"` | Standard `border` (default) |

### Effects

| Figma effect type | CSS output |
|------------------|-----------|
| `DROP_SHADOW` | `box-shadow: Xpx Ypx blurpx spreadpx rgba(r,g,b,a)` |
| `INNER_SHADOW` | `box-shadow: inset Xpx Ypx blurpx spreadpx rgba(r,g,b,a)` |
| `LAYER_BLUR` | `filter: blur(Npx)` |
| `BACKGROUND_BLUR` | `backdrop-filter: blur(Npx)` |
| Multiple effects | Comma-separate box-shadow values; chain filter values |

### Typography

| Figma field | Values | CSS output |
|-------------|--------|-----------|
| `style.fontFamily` | string | `font-family: "Name"` |
| `style.fontWeight` | 100–900 | `font-weight: N` |
| `style.fontSize` | N | `font-size: Npx` |
| `style.italic` | `true` | `font-style: italic` |
| `style.letterSpacing` | N px | `letter-spacing: Npx` |
| `style.lineHeightPx` | N | `line-height: Npx` |
| `style.lineHeightUnit == "INTRINSIC_%"` | — | `line-height: normal` |
| `style.textAlignHorizontal` | `"LEFT"` / `"CENTER"` / `"RIGHT"` / `"JUSTIFIED"` | `text-align: left` / `center` / `right` / `justify` |
| `style.textDecoration` | `"UNDERLINE"` | `text-decoration: underline` |
| `style.textDecoration` | `"STRIKETHROUGH"` | `text-decoration: line-through` |
| `style.textCase` | `"UPPER"` | `text-transform: uppercase` |
| `style.textCase` | `"LOWER"` | `text-transform: lowercase` |
| `style.textCase` | `"TITLE"` | `text-transform: capitalize` |
| `style.textAutoResize` | `"TRUNCATE"` | `overflow: hidden; text-overflow: ellipsis; white-space: nowrap` |
| `style.paragraphSpacing` | N | `margin-bottom: Npx` on `<p>` |
| Text color | `fills[0]` on TEXT node | `color: rgba(r,g,b,a)` |

### Positioning

| Figma field | Values | CSS output |
|-------------|--------|-----------|
| `layoutPositioning` | `"ABSOLUTE"` | `position: absolute; left: Xpx; top: Ypx` |
| `layoutPositioning` | `"AUTO"` | element in normal flex flow (no position needed) |
| `rotation` | N degrees | `transform: rotate(-Ndeg)` (**negate** — Figma CCW, CSS CW) |
| `relativeTransform` | 2×3 matrix | Use `rotation` field instead when possible |

---

## Extraction Helper

Run this after the REST call to produce per-component CSS specs:

```python
import json, re, sys

def rgba(c, opacity=1.0):
    """Convert Figma RGBA (0-1 floats) to CSS rgba string."""
    r = round(c.get('r', 0) * 255)
    g = round(c.get('g', 0) * 255)
    b = round(c.get('b', 0) * 255)
    a = round(c.get('a', 1.0) * opacity, 3)
    return f"rgba({r},{g},{b},{a})" if a < 1 else f"#{r:02x}{g:02x}{b:02x}"

def gradient_css(fill):
    """Convert Figma gradient fill to CSS gradient string."""
    stops = fill.get('gradientStops', [])
    stop_css = ', '.join(f"{rgba(s['color'])} {round(s['position']*100)}%" for s in stops)
    t = fill.get('type', '')
    if t == 'GRADIENT_LINEAR':
        # Compute angle from gradientHandlePositions if present
        handles = fill.get('gradientHandlePositions', [])
        angle = 'to bottom'  # default
        if len(handles) >= 2:
            dx = handles[1]['x'] - handles[0]['x']
            dy = handles[1]['y'] - handles[0]['y']
            import math
            deg = round(math.degrees(math.atan2(dx, -dy)) % 360)
            angle = f"{deg}deg"
        return f"linear-gradient({angle}, {stop_css})"
    if t == 'GRADIENT_RADIAL':
        return f"radial-gradient(circle, {stop_css})"
    if t == 'GRADIENT_ANGULAR':
        return f"conic-gradient({stop_css})"
    return None

def extract_fills_css(node):
    """Return CSS background/color value from node fills."""
    fills = [f for f in node.get('fills', []) if f.get('visible', True)]
    if not fills:
        return None
    fill = fills[0]  # primary fill
    opacity = node.get('opacity', 1.0)
    ft = fill.get('type', '')
    if ft == 'SOLID':
        return rgba(fill.get('color', {}), fill.get('opacity', 1.0) * opacity)
    if ft in ('GRADIENT_LINEAR', 'GRADIENT_RADIAL', 'GRADIENT_ANGULAR'):
        return gradient_css(fill)
    if ft == 'IMAGE':
        return 'url(<figma-image-asset>)'  # requires separate Figma asset fetch
    return None

def extract_border_radius(node):
    """Return CSS border-radius value, handling mixed corners."""
    tl = node.get('topLeftRadius') or node.get('cornerRadius')
    tr = node.get('topRightRadius') or node.get('cornerRadius')
    br = node.get('bottomRightRadius') or node.get('cornerRadius')
    bl = node.get('bottomLeftRadius') or node.get('cornerRadius')
    cr = node.get('cornerRadius', 0)
    # All equal — use shorthand
    if tl == tr == br == bl:
        return f"{cr}px" if cr else None
    # Mixed — use 4-value shorthand (CSS order: TL TR BR BL)
    if any([tl, tr, br, bl]):
        return f"{tl or 0}px {tr or 0}px {br or 0}px {bl or 0}px"
    return None

def extract_padding(node):
    """Return CSS padding shorthand."""
    t = node.get('paddingTop', 0)
    b = node.get('paddingBottom', 0)
    l = node.get('paddingLeft', 0)
    r = node.get('paddingRight', 0)
    if not any([t, b, l, r]):
        return None
    if t == b == l == r:
        return f"{t}px"
    if t == b and l == r:
        return f"{t}px {l}px"
    return f"{t}px {r}px {b}px {l}px"

def extract_layout(node):
    """Return CSS flex/layout properties dict."""
    mode = node.get('layoutMode', 'NONE')
    props = {}
    if mode in ('HORIZONTAL', 'VERTICAL'):
        props['display'] = 'flex'
        props['flex-direction'] = 'row' if mode == 'HORIZONTAL' else 'column'
        align_map = {'MIN': 'flex-start', 'CENTER': 'center', 'MAX': 'flex-end',
                     'SPACE_BETWEEN': 'space-between', 'STRETCH': 'stretch', 'BASELINE': 'baseline'}
        pa = node.get('primaryAxisAlignItems')
        ca = node.get('counterAxisAlignItems')
        if pa: props['justify-content'] = align_map.get(pa, pa.lower())
        if ca: props['align-items'] = align_map.get(ca, ca.lower())
        wrap = node.get('layoutWrap')
        if wrap == 'WRAP': props['flex-wrap'] = 'wrap'
        gap = node.get('itemSpacing')
        if gap: props['gap'] = f"{gap}px"
        cgap = node.get('counterAxisSpacing')
        if cgap and wrap == 'WRAP': props['column-gap'] = f"{cgap}px"
    size_h = node.get('layoutSizingHorizontal')
    size_v = node.get('layoutSizingVertical')
    w = node.get('width')
    h = node.get('height')
    if size_h == 'FIXED' and w: props['width'] = f"{round(w)}px"
    elif size_h == 'HUG': props['width'] = 'fit-content'
    elif size_h == 'FILL': props['width'] = '100%'
    if size_v == 'FIXED' and h: props['height'] = f"{round(h)}px"
    elif size_v == 'HUG': props['height'] = 'fit-content'
    elif size_v == 'FILL': props['height'] = '100%'
    # Fallback: fixed dimensions when no sizing mode
    if 'width' not in props and w and not size_h: props['width'] = f"{round(w)}px"
    if 'height' not in props and h and not size_v: props['height'] = f"{round(h)}px"
    if node.get('clipsContent'): props['overflow'] = 'hidden'
    return props

def extract_effects(node):
    """Return CSS shadow/filter properties."""
    shadows, filters, backdrop = [], [], []
    for eff in node.get('effects', []):
        if not eff.get('visible', True): continue
        t = eff.get('type')
        c = eff.get('color', {})
        opacity = node.get('opacity', 1.0)
        color = rgba(c, c.get('a', 1) * opacity)
        offset = eff.get('offset', {})
        x, y = offset.get('x', 0), offset.get('y', 0)
        radius = eff.get('radius', 0)
        spread = eff.get('spread', 0)
        if t == 'DROP_SHADOW':
            shadows.append(f"{x}px {y}px {radius}px {spread}px {color}")
        elif t == 'INNER_SHADOW':
            shadows.append(f"inset {x}px {y}px {radius}px {spread}px {color}")
        elif t == 'LAYER_BLUR':
            filters.append(f"blur({radius}px)")
        elif t == 'BACKGROUND_BLUR':
            backdrop.append(f"blur({radius}px)")
    result = {}
    if shadows: result['box-shadow'] = ', '.join(shadows)
    if filters: result['filter'] = ' '.join(filters)
    if backdrop: result['backdrop-filter'] = ' '.join(backdrop)
    return result

def extract_border(node):
    """Return CSS border properties."""
    strokes = [s for s in node.get('strokes', []) if s.get('visible', True)]
    if not strokes: return {}
    color = rgba(strokes[0].get('color', {}))
    align = node.get('strokeAlign', 'CENTER')
    # Per-side weights
    top_w = node.get('strokeTopWeight') or node.get('strokeWeight', 0)
    bot_w = node.get('strokeBottomWeight') or node.get('strokeWeight', 0)
    left_w = node.get('strokeLeftWeight') or node.get('strokeWeight', 0)
    right_w = node.get('strokeRightWeight') or node.get('strokeWeight', 0)
    props = {}
    if top_w == bot_w == left_w == right_w:
        props['border'] = f"{top_w}px solid {color}"
    else:
        if top_w:   props['border-top']    = f"{top_w}px solid {color}"
        if bot_w:   props['border-bottom'] = f"{bot_w}px solid {color}"
        if left_w:  props['border-left']   = f"{left_w}px solid {color}"
        if right_w: props['border-right']  = f"{right_w}px solid {color}"
    if align == 'INSIDE': props['_stroke_note'] = 'box-sizing: border-box required'
    if align == 'OUTSIDE': props['_stroke_note'] = 'use outline or wrapper div for outside stroke'
    return props

def extract_typography(node):
    """Return CSS text properties from a TEXT node."""
    style = node.get('style', {})
    props = {}
    ff = style.get('fontFamily')
    if ff: props['font-family'] = f'"{ff}"'
    fw = style.get('fontWeight')
    if fw: props['font-weight'] = str(fw)
    fs = style.get('fontSize')
    if fs: props['font-size'] = f"{fs}px"
    if style.get('italic'): props['font-style'] = 'italic'
    ls = style.get('letterSpacing')
    if ls: props['letter-spacing'] = f"{ls}px"
    lh_unit = style.get('lineHeightUnit', '')
    lh_px = style.get('lineHeightPx')
    if lh_unit == 'INTRINSIC_%': props['line-height'] = 'normal'
    elif lh_px: props['line-height'] = f"{round(lh_px)}px"
    align = style.get('textAlignHorizontal')
    if align and align != 'LEFT':
        align_map = {'CENTER': 'center', 'RIGHT': 'right', 'JUSTIFIED': 'justify'}
        props['text-align'] = align_map.get(align, align.lower())
    deco = style.get('textDecoration')
    if deco and deco != 'NONE':
        props['text-decoration'] = 'underline' if deco == 'UNDERLINE' else 'line-through'
    case = style.get('textCase')
    if case and case not in ('ORIGINAL', 'NONE'):
        case_map = {'UPPER': 'uppercase', 'LOWER': 'lowercase', 'TITLE': 'capitalize'}
        props['text-transform'] = case_map.get(case)
    resize = style.get('textAutoResize')
    if resize == 'TRUNCATE':
        props['overflow'] = 'hidden'
        props['text-overflow'] = 'ellipsis'
        props['white-space'] = 'nowrap'
    ps = style.get('paragraphSpacing')
    if ps: props['_paragraph_spacing'] = f"{ps}px"
    # Text color from fills
    text_color = extract_fills_css(node)
    if text_color: props['color'] = text_color
    return props

def extract_positioning(node):
    """Return CSS positioning for absolutely-positioned nodes."""
    props = {}
    if node.get('layoutPositioning') == 'ABSOLUTE':
        props['position'] = 'absolute'
        bbox = node.get('absoluteBoundingBox', {})
        x = node.get('x', bbox.get('x'))
        y = node.get('y', bbox.get('y'))
        if x is not None: props['left'] = f"{round(x)}px"
        if y is not None: props['top'] = f"{round(y)}px"
    rot = node.get('rotation')
    if rot and abs(rot) > 0.1:
        props['transform'] = f"rotate({-round(rot, 2)}deg)"  # negate: Figma CCW, CSS CW
    blend = node.get('blendMode', 'NORMAL')
    if blend not in ('NORMAL', 'PASS_THROUGH'):
        blend_map = {'MULTIPLY': 'multiply', 'SCREEN': 'screen', 'OVERLAY': 'overlay',
                     'DARKEN': 'darken', 'LIGHTEN': 'lighten', 'COLOR_DODGE': 'color-dodge',
                     'COLOR_BURN': 'color-burn', 'HARD_LIGHT': 'hard-light',
                     'SOFT_LIGHT': 'soft-light', 'DIFFERENCE': 'difference',
                     'EXCLUSION': 'exclusion', 'HUE': 'hue', 'SATURATION': 'saturation',
                     'COLOR': 'color', 'LUMINOSITY': 'luminosity'}
        if blend in blend_map: props['mix-blend-mode'] = blend_map[blend]
    opacity = node.get('opacity')
    if opacity is not None and opacity < 1.0: props['opacity'] = str(round(opacity, 2))
    return props

def extract_component_spec(node):
    """Extract complete CSS spec for one component/frame node."""
    node_type = node.get('type', '')
    name = node.get('name', 'unnamed')
    spec = {'name': name, 'type': node_type, 'css': {}}

    # Skip invisible nodes
    if not node.get('visible', True):
        spec['css']['display'] = 'none'
        return spec

    # Layout, sizing, overflow
    spec['css'].update(extract_layout(node))

    # Background / fill
    if node_type != 'TEXT':
        bg = extract_fills_css(node)
        if bg:
            spec['css']['background' if 'gradient' in str(bg) or bg.startswith('url') else 'background-color'] = bg

    # Corner radius
    radius = extract_border_radius(node)
    if radius and radius != '0px':
        spec['css']['border-radius'] = radius

    # Padding
    padding = extract_padding(node)
    if padding:
        spec['css']['padding'] = padding

    # Borders
    spec['css'].update(extract_border(node))

    # Effects (shadows, blur)
    spec['css'].update(extract_effects(node))

    # Typography (TEXT nodes)
    if node_type == 'TEXT':
        spec['css'].update(extract_typography(node))

    # Positioning, rotation, blend mode, opacity
    spec['css'].update(extract_positioning(node))

    return spec

VARIANT_STATE_MAP = {
    'hover': ':hover', 'hovered': ':hover',
    'pressed': ':active', 'active': ':active',
    'focused': ':focus', 'focus': ':focus', 'focus-visible': ':focus-visible',
    'disabled': ':disabled', 'inactive': ':disabled',
    'checked': ':checked', 'selected': ':checked',
    'loading': '[data-loading="true"]',
    'error': '[data-error="true"]',
    'default': '',  # base state — no pseudo-class
    'normal': '',
}

def parse_variant_state(component_name):
    """Extract CSS pseudo-class from Figma variant name like 'State=Hover, Size=Large'."""
    parts = {k.strip().lower(): v.strip().lower()
             for pair in component_name.split(',')
             for k, _, v in [pair.partition('=')]}
    # Check 'state', 'status', 'type', or any key whose VALUE maps to a pseudo-class
    for key in ('state', 'status'):
        val = parts.get(key, '')
        if val in VARIANT_STATE_MAP:
            return VARIANT_STATE_MAP[val]
    # Fallback: check if any value matches
    for val in parts.values():
        if val in VARIANT_STATE_MAP:
            return VARIANT_STATE_MAP[val]
    return None  # not a state variant

def collect_specs(node, specs=None, depth=0, viewport=None):
    """Recursively collect per-component CSS specs. Handles variant states."""
    if specs is None: specs = []
    node_type = node.get('type', '')
    name = node.get('name', '')

    # Capture viewport from top-level FRAME dimensions
    if depth == 0 and node_type == 'FRAME' and viewport is None:
        bbox = node.get('absoluteBoundingBox', {})
        w = node.get('width') or bbox.get('width')
        h = node.get('height') or bbox.get('height')
        if w:
            if w <= 430:
                vp_label = f"mobile ({round(w)}px)"
            elif w <= 834:
                vp_label = f"tablet ({round(w)}px)"
            else:
                vp_label = f"desktop ({round(w)}px)"
            viewport = {'width': round(w), 'height': round(h) if h else None, 'label': vp_label}
            specs.insert(0, {'name': '__viewport__', 'type': 'VIEWPORT', 'viewport': viewport, 'css': {}})

    # COMPONENT_SET: its children are variant frames — extract each as a state spec
    if node_type == 'COMPONENT_SET':
        base_name = name
        for child in node.get('children', []):
            pseudo = parse_variant_state(child.get('name', ''))
            if pseudo is None:
                pseudo = ''  # unknown state — include as base
            spec = extract_component_spec(child)
            if spec['css']:
                spec['depth'] = depth
                spec['variant_of'] = base_name
                spec['css_selector_suffix'] = pseudo  # e.g. ':hover', ':disabled', ''
                spec['name'] = f"{base_name}{pseudo or ' (default)'}"
                specs.append(spec)
        return specs  # children already processed above

    # Standard structural and visual nodes
    if node_type in ('FRAME', 'COMPONENT', 'INSTANCE', 'TEXT', 'RECTANGLE', 'VECTOR') or \
       (node_type == 'GROUP' and name and not name.startswith('Group')):
        spec = extract_component_spec(node)
        if spec['css']:
            spec['depth'] = depth
            spec['css_selector_suffix'] = ''
            specs.append(spec)

    for child in node.get('children', []):
        collect_specs(child, specs, depth + 1, viewport)

    return specs
```

---

## Complete Invocation

Use the standalone extraction script — handles both Scenario A (node-id present) and Scenario B (no node-id) automatically:

```bash
python3 claude-master-plugin/scripts/figma-extract.py <ticket>
```

The script reads `docs/artifacts/<ticket>/.state/pipeline_state_<ticket>.json` for the Figma URL and the API key from `~/.claude.json`. For Scenario A it calls `/v1/files/{key}/nodes?ids={node_id}` with no depth cap (node-id already scopes the payload); for Scenario B it calls `/v1/files/{key}?depth=6` to cover most real-world nesting while keeping the payload bounded. Writes output to `/tmp/figma_specs_<ticket>.json` and prints a component summary.

After running, load the specs with:

```python
all_specs = json.load(open(f'/tmp/figma_specs_{ticket}.json'))
```

---

## Output: Write to `ph1_problem_spec.md`

Append BOTH sections below. The `## Design Tokens` section is the source of truth for implementation — every CSS property listed here MUST be used exactly as specified.

````markdown
## Figma Design Reference

- **Figma link:** <original URL>
- **Screens:** <list of top-level FRAME names>
- **Components used in design:**
  - `<ComponentName>` — <brief description of role in the screen>
- **Key variants/states:** <e.g., default, hover, disabled, loading>

## Design Tokens

> **Implementation contract — these values are non-negotiable.**
> Every CSS property listed below MUST be implemented exactly as shown.
> Do NOT approximate, substitute, or use defaults when a value is specified here.
> Flag any value that cannot be implemented as specified (e.g., a font not loaded in the project).

### Viewport Context

- **Design viewport:** `<mobile (375px) | tablet (768px) | desktop (1440px)>`
- **Breakpoint note:** `<e.g., "This is a mobile design. Desktop layout not in scope for this ticket.">`

*(This tells the implementor which media query context applies. If the ticket covers multiple viewports, list each with its own component specs below.)*

### Per-Component CSS Specifications

For each named component extracted from Figma, a complete CSS spec is listed.
Implementors MUST apply ALL properties shown for each component.

---

#### `<ComponentName>` *(e.g., PausedDeliveryBanner)* — default state

```css
/* Layout */
display: flex;
flex-direction: row;
justify-content: space-between;
align-items: center;
gap: 8px;

/* Sizing */
width: 100%;
height: fit-content;

/* Spacing */
padding: 12px 16px;

/* Visual */
background-color: #f5f5f5;
border-radius: 4px;           /* ← MUST be 4px, NOT 8px or 0 */
border: 1px solid #e0e0e0;
overflow: hidden;

/* Effects */
box-shadow: 0px 2px 8px 0px rgba(0,0,0,0.12);
```

#### `<ComponentName>:hover` — hover state *(from Figma variant State=Hover)*

```css
background-color: #ebebeb;
border-color: #bdbdbd;
box-shadow: 0px 4px 12px 0px rgba(0,0,0,0.18);
```

#### `<ComponentName>:disabled` — disabled state *(from Figma variant State=Disabled)*

```css
opacity: 0.4;
pointer-events: none;
```

> **Variant state rules:**
> - Each Figma variant frame maps to a CSS selector suffix (`:hover`, `:disabled`, `:active`, `:focus`, `[data-loading="true"]`, `[data-error="true"]`)
> - Only include the **delta properties** for each state — properties that differ from the default state
> - If Figma has no variant for a state, do NOT invent hover/disabled styles — leave them unspecified
> - States with `css_selector_suffix: ''` are base/default — their CSS goes in the main class
> - States with `css_selector_suffix: ':hover'` etc. go in the corresponding pseudo-class or data attribute

---

#### `<ChildComponent>` *(e.g., StatusIcon)*

```css
/* Sizing */
width: 24px;
height: 24px;

/* Visual */
background-color: #ff6b00;
border-radius: 50%;
opacity: 0.9;
```

---

#### `<TextElement>` *(e.g., BannerTitle)*

```css
/* Typography */
font-family: "Inter";
font-weight: 600;
font-size: 14px;
line-height: 20px;
letter-spacing: 0px;
color: #1a1a1a;
text-align: left;
```

---

### Design Token Summary

Quick-reference table for all unique values found across components.

| Token | Value | Used in |
|-------|-------|---------|
| Primary background | `#f5f5f5` | PausedDeliveryBanner |
| Accent color | `#ff6b00` | StatusIcon, CTAButton |
| Border color | `#e0e0e0` | PausedDeliveryBanner, Divider |
| Border radius — card | `4px` | PausedDeliveryBanner |
| Border radius — icon | `50%` | StatusIcon |
| Body font size | `14px` | BannerTitle, BannerSubtitle |
| Heading font weight | `600` | BannerTitle |
| Standard padding | `12px 16px` | PausedDeliveryBanner |
| Icon gap | `8px` | PausedDeliveryBanner |
| Card shadow | `0px 2px 8px 0px rgba(0,0,0,0.12)` | PausedDeliveryBanner |

````

**Rules for populating the output:**
- List EVERY named component and text layer that the implementor will create as a new file or class
- Omit components the implementor will reuse unchanged (they're in the EXISTING list from Phase 4.5)
- If a property is the project-wide default (e.g., `font-family` same as global base), still include it — the implementor should confirm, not assume
- If a value cannot be determined from the Figma data (e.g., image asset URL), write `<TBD: asset reference>` — do NOT omit the property
- Omit the Shadows / Borders / Effects section for a component only if the Figma data contains genuinely zero values for those properties

---

## Update `pipeline_state_<ticket>.json`

After a successful fetch (even partial), use the canonical write function:

```bash
python3 -c "
import json, re
path = 'docs/artifacts/<ticket>/.state/pipeline_state_<ticket>.json'
with open(path) as f: state = json.load(f)
state['figma']['fetched'] = True
raw = json.dumps(state, indent=2)
lines = ['    ' + json.dumps(n) + ': ' + json.dumps(d, separators=(',', ': ')) for n, d in state['phases'].items()]
compact = '  \"phases\": {\n' + ',\n'.join(lines) + '\n  }'
result = re.sub(r'  \"phases\": \{.*?\n  \}', compact, raw, flags=re.DOTALL)
open(path, 'w').write(result)
"
```

## On Failure

If the single call fails (error response, empty result, or missing credentials):
- Log: `⚠️ Figma fetch failed: <reason>. Continuing without design reference.`
- Leave `figma.fetched: false` — do NOT update it.
- Do NOT write a `## Figma Design Reference` or `## Design Tokens` section to `ph1_problem_spec.md`.
- Do NOT retry with a different method. Move on to Step 4.
