#!/usr/bin/env python3
"""
figma-extract.py — Fetch and extract per-component CSS specs from a Figma design.

Usage:
    python3 claude-master-plugin/scripts/figma-extract.py <ticket-id>

Reads:  docs/artifacts/<ticket>/.state/pipeline_state.json  (for figma.link)
        ~/.claude.json  (for FIGMA_API_KEY)
Writes: /tmp/figma_specs_<ticket>.json  (extracted component specs)
Prints: summary of extracted components + viewport context
"""

import json, re, math, urllib.request, os, sys

# ── Helpers ────────────────────────────────────────────────────────────────

def rgba(c, opacity=1.0):
    r = round(c.get('r', 0) * 255)
    g = round(c.get('g', 0) * 255)
    b = round(c.get('b', 0) * 255)
    a = round(c.get('a', 1.0) * opacity, 3)
    return f"rgba({r},{g},{b},{a})" if a < 1 else f"#{r:02x}{g:02x}{b:02x}"

def gradient_css(fill):
    stops = fill.get('gradientStops', [])
    stop_css = ', '.join(f"{rgba(s['color'])} {round(s['position']*100)}%" for s in stops)
    t = fill.get('type', '')
    if t == 'GRADIENT_LINEAR':
        handles = fill.get('gradientHandlePositions', [])
        angle = 'to bottom'
        if len(handles) >= 2:
            dx = handles[1]['x'] - handles[0]['x']
            dy = handles[1]['y'] - handles[0]['y']
            deg = round(math.degrees(math.atan2(dx, -dy)) % 360)
            angle = f"{deg}deg"
        return f"linear-gradient({angle}, {stop_css})"
    if t == 'GRADIENT_RADIAL':
        return f"radial-gradient(circle, {stop_css})"
    if t == 'GRADIENT_ANGULAR':
        return f"conic-gradient({stop_css})"
    return None

def extract_fills_css(node):
    fills = [f for f in node.get('fills', []) if f.get('visible', True)]
    if not fills:
        return None
    fill = fills[0]
    opacity = node.get('opacity', 1.0)
    ft = fill.get('type', '')
    if ft == 'SOLID':
        return rgba(fill.get('color', {}), fill.get('opacity', 1.0) * opacity)
    if ft in ('GRADIENT_LINEAR', 'GRADIENT_RADIAL', 'GRADIENT_ANGULAR'):
        return gradient_css(fill)
    if ft == 'IMAGE':
        return 'url(<figma-image-asset>)'
    return None

def extract_border_radius(node):
    cr  = node.get('cornerRadius', 0)
    tl  = node.get('topLeftRadius',     cr)
    tr  = node.get('topRightRadius',    cr)
    br  = node.get('bottomRightRadius', cr)
    bl  = node.get('bottomLeftRadius',  cr)
    if not any([tl, tr, br, bl]):
        return None
    if tl == tr == br == bl:
        return f"{tl}px"
    return f"{tl}px {tr}px {br}px {bl}px"

def extract_padding(node):
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
    mode = node.get('layoutMode', 'NONE')
    props = {}
    if mode in ('HORIZONTAL', 'VERTICAL'):
        props['display'] = 'flex'
        props['flex-direction'] = 'row' if mode == 'HORIZONTAL' else 'column'
        align_map = {
            'MIN': 'flex-start', 'CENTER': 'center', 'MAX': 'flex-end',
            'SPACE_BETWEEN': 'space-between', 'STRETCH': 'stretch', 'BASELINE': 'baseline',
        }
        pa = node.get('primaryAxisAlignItems')
        ca = node.get('counterAxisAlignItems')
        if pa: props['justify-content'] = align_map.get(pa, pa.lower())
        if ca: props['align-items']     = align_map.get(ca, ca.lower())
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
    if   size_h == 'FIXED' and w: props['width']  = f"{round(w)}px"
    elif size_h == 'HUG':          props['width']  = 'fit-content'
    elif size_h == 'FILL':         props['width']  = '100%'
    if   size_v == 'FIXED' and h: props['height'] = f"{round(h)}px"
    elif size_v == 'HUG':          props['height'] = 'fit-content'
    elif size_v == 'FILL':         props['height'] = '100%'
    if 'width'  not in props and w and not size_h: props['width']  = f"{round(w)}px"
    if 'height' not in props and h and not size_v: props['height'] = f"{round(h)}px"
    if node.get('clipsContent'): props['overflow'] = 'hidden'
    return props

def extract_effects(node):
    shadows, filters, backdrop = [], [], []
    for eff in node.get('effects', []):
        if not eff.get('visible', True): continue
        t      = eff.get('type')
        c      = eff.get('color', {})
        op     = node.get('opacity', 1.0)
        color  = rgba(c, c.get('a', 1) * op)
        offset = eff.get('offset', {})
        x, y   = offset.get('x', 0), offset.get('y', 0)
        radius = eff.get('radius', 0)
        spread = eff.get('spread', 0)
        if   t == 'DROP_SHADOW':      shadows.append(f"{x}px {y}px {radius}px {spread}px {color}")
        elif t == 'INNER_SHADOW':     shadows.append(f"inset {x}px {y}px {radius}px {spread}px {color}")
        elif t == 'LAYER_BLUR':       filters.append(f"blur({radius}px)")
        elif t == 'BACKGROUND_BLUR':  backdrop.append(f"blur({radius}px)")
    result = {}
    if shadows:  result['box-shadow']        = ', '.join(shadows)
    if filters:  result['filter']            = ' '.join(filters)
    if backdrop: result['backdrop-filter']   = ' '.join(backdrop)
    return result

def extract_border(node):
    strokes = [s for s in node.get('strokes', []) if s.get('visible', True)]
    if not strokes: return {}
    color  = rgba(strokes[0].get('color', {}))
    align  = node.get('strokeAlign', 'CENTER')
    top_w  = node.get('strokeTopWeight')    or node.get('strokeWeight', 0)
    bot_w  = node.get('strokeBottomWeight') or node.get('strokeWeight', 0)
    left_w = node.get('strokeLeftWeight')   or node.get('strokeWeight', 0)
    rgt_w  = node.get('strokeRightWeight')  or node.get('strokeWeight', 0)
    props = {}
    if top_w == bot_w == left_w == rgt_w:
        props['border'] = f"{top_w}px solid {color}"
    else:
        if top_w:  props['border-top']    = f"{top_w}px solid {color}"
        if bot_w:  props['border-bottom'] = f"{bot_w}px solid {color}"
        if left_w: props['border-left']   = f"{left_w}px solid {color}"
        if rgt_w:  props['border-right']  = f"{rgt_w}px solid {color}"
    if align == 'INSIDE':  props['_stroke_note'] = 'box-sizing: border-box required'
    if align == 'OUTSIDE': props['_stroke_note'] = 'use outline or wrapper div for outside stroke'
    return props

def extract_typography(node):
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
    lh_px   = style.get('lineHeightPx')
    if lh_unit == 'INTRINSIC_%': props['line-height'] = 'normal'
    elif lh_px: props['line-height'] = f"{round(lh_px)}px"
    align = style.get('textAlignHorizontal')
    if align and align != 'LEFT':
        props['text-align'] = {'CENTER': 'center', 'RIGHT': 'right', 'JUSTIFIED': 'justify'}.get(align, align.lower())
    deco = style.get('textDecoration')
    if deco and deco != 'NONE':
        props['text-decoration'] = 'underline' if deco == 'UNDERLINE' else 'line-through'
    case = style.get('textCase')
    if case and case not in ('ORIGINAL', 'NONE'):
        props['text-transform'] = {'UPPER': 'uppercase', 'LOWER': 'lowercase', 'TITLE': 'capitalize'}.get(case)
    if style.get('textAutoResize') == 'TRUNCATE':
        props['overflow'] = 'hidden'
        props['text-overflow'] = 'ellipsis'
        props['white-space'] = 'nowrap'
    ps = style.get('paragraphSpacing')
    if ps: props['_paragraph_spacing'] = f"{ps}px"
    text_color = extract_fills_css(node)
    if text_color: props['color'] = text_color
    return props

def extract_positioning(node):
    props = {}
    if node.get('layoutPositioning') == 'ABSOLUTE':
        props['position'] = 'absolute'
        bbox = node.get('absoluteBoundingBox') or {}
        x = node.get('x', bbox.get('x'))
        y = node.get('y', bbox.get('y'))
        if x is not None: props['left'] = f"{round(x)}px"
        if y is not None: props['top']  = f"{round(y)}px"
    rot = node.get('rotation')
    if rot and abs(rot) > 0.1:
        props['transform'] = f"rotate({-round(rot, 2)}deg)"
    blend = node.get('blendMode', 'NORMAL')
    if blend not in ('NORMAL', 'PASS_THROUGH'):
        blend_map = {
            'MULTIPLY': 'multiply', 'SCREEN': 'screen', 'OVERLAY': 'overlay',
            'DARKEN': 'darken', 'LIGHTEN': 'lighten', 'COLOR_DODGE': 'color-dodge',
            'COLOR_BURN': 'color-burn', 'HARD_LIGHT': 'hard-light', 'SOFT_LIGHT': 'soft-light',
            'DIFFERENCE': 'difference', 'EXCLUSION': 'exclusion', 'HUE': 'hue',
            'SATURATION': 'saturation', 'COLOR': 'color', 'LUMINOSITY': 'luminosity',
        }
        if blend in blend_map: props['mix-blend-mode'] = blend_map[blend]
    opacity = node.get('opacity')
    if opacity is not None and opacity < 1.0: props['opacity'] = str(round(opacity, 2))
    return props

def extract_component_spec(node):
    node_type = node.get('type', '')
    name = node.get('name', 'unnamed')
    spec = {'name': name, 'type': node_type, 'css': {}}
    if not node.get('visible', True):
        spec['css']['display'] = 'none'
        return spec
    spec['css'].update(extract_layout(node))
    if node_type != 'TEXT':
        bg = extract_fills_css(node)
        if bg:
            key = 'background' if ('gradient' in str(bg) or bg.startswith('url')) else 'background-color'
            spec['css'][key] = bg
    radius = extract_border_radius(node)
    if radius:
        spec['css']['border-radius'] = radius
    padding = extract_padding(node)
    if padding:
        spec['css']['padding'] = padding
    spec['css'].update(extract_border(node))
    spec['css'].update(extract_effects(node))
    if node_type == 'TEXT':
        spec['css'].update(extract_typography(node))
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
    'default': '', 'normal': '',
}

def parse_variant_state(component_name):
    parts = {}
    for pair in component_name.split(','):
        k, _, v = pair.partition('=')
        parts[k.strip().lower()] = v.strip().lower()
    for key in ('state', 'status'):
        val = parts.get(key, '')
        if val in VARIANT_STATE_MAP:
            return VARIANT_STATE_MAP[val]
    for val in parts.values():
        if val in VARIANT_STATE_MAP:
            return VARIANT_STATE_MAP[val]
    return None

def collect_specs(node, specs=None, depth=0, viewport=None):
    if specs is None: specs = []
    node_type = node.get('type', '')
    name = node.get('name', '')

    # Capture viewport from top-level FRAME
    if depth == 0 and node_type == 'FRAME' and viewport is None:
        bbox = node.get('absoluteBoundingBox') or {}
        w = node.get('width') or bbox.get('width')
        h = node.get('height') or bbox.get('height')
        if w:
            if w <= 430:   vp_label = f"mobile ({round(w)}px)"
            elif w <= 834: vp_label = f"tablet ({round(w)}px)"
            else:          vp_label = f"desktop ({round(w)}px)"
            viewport = {'width': round(w), 'height': round(h) if h else None, 'label': vp_label}
            specs.insert(0, {'name': '__viewport__', 'type': 'VIEWPORT', 'viewport': viewport, 'css': {}})

    # COMPONENT_SET: children are variant frames
    if node_type == 'COMPONENT_SET':
        base_name = name
        for child in node.get('children', []):
            pseudo = parse_variant_state(child.get('name', ''))
            if pseudo is None: pseudo = ''
            spec = extract_component_spec(child)
            if spec['css']:
                spec['depth'] = depth
                spec['variant_of'] = base_name
                spec['css_selector_suffix'] = pseudo
                spec['name'] = f"{base_name}{pseudo or ' (default)'}"
                specs.append(spec)
        return specs

    # Standard nodes
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

# ── Main ───────────────────────────────────────────────────────────────────

def load_api_key():
    try:
        cfg = json.load(open(os.path.expanduser('~/.claude.json')))
        for proj in cfg.get('projects', {}).values():
            for srv in proj.get('mcpServers', {}).values():
                key = srv.get('env', {}).get('FIGMA_API_KEY', '')
                if key: return key
    except Exception:
        pass
    return os.environ.get('FIGMA_API_KEY', '')

def main():
    if len(sys.argv) < 2:
        print('Usage: python3 figma-extract.py <ticket-id>', file=sys.stderr)
        sys.exit(1)

    ticket = sys.argv[1]
    state_path = f'docs/artifacts/{ticket}/.state/pipeline_state.json'

    try:
        state = json.load(open(state_path))
    except FileNotFoundError:
        print(f'ERROR: {state_path} not found. Run requirements phase first.', file=sys.stderr)
        sys.exit(1)

    url = (state.get('figma') or {}).get('link')
    if not url:
        print('ERROR: No figma.link in pipeline_state.json', file=sys.stderr)
        sys.exit(1)

    api_key = load_api_key()
    if not api_key:
        print('ERROR: FIGMA_API_KEY not found in ~/.claude.json or environment', file=sys.stderr)
        sys.exit(1)

    # Parse URL
    branch = re.search(r'/branch/([A-Za-z0-9]+)', url)
    file_  = re.search(r'/(?:file|design)/([A-Za-z0-9]+)', url)
    key    = branch.group(1) if branch else (file_.group(1) if file_ else None)
    node_m = re.search(r'node-id=([^&]+)', url)
    node_id = node_m.group(1).replace('%3A', '-').replace('%3a', '-') if node_m else None

    if not key:
        print(f'ERROR: Could not extract file key from URL: {url}', file=sys.stderr)
        sys.exit(1)

    # Fetch
    if node_id:
        api_url = f'https://api.figma.com/v1/files/{key}/nodes?ids={node_id}'
    else:
        # No node-id — fetch full file with no depth cap to capture all layers
        api_url = f'https://api.figma.com/v1/files/{key}'

    req = urllib.request.Request(api_url, headers={'X-Figma-Token': api_key})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            response = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        print(f'ERROR: Figma API HTTP {e.code}: {e.reason}', file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f'ERROR: Figma API call failed: {e}', file=sys.stderr)
        sys.exit(1)

    # Extract specs — handle both /nodes and /files response shapes
    all_specs = []
    if node_id:
        for nid, wrapper in response.get('nodes', {}).items():
            doc = wrapper.get('document', {})
            all_specs.extend(collect_specs(doc))
    else:
        doc = response.get('document', {})
        all_specs.extend(collect_specs(doc))

    # Write output
    out_path = f'/tmp/figma_specs_{ticket}.json'
    with open(out_path, 'w') as f:
        json.dump(all_specs, f, indent=2)

    # Summary
    viewport   = next((s for s in all_specs if s.get('type') == 'VIEWPORT'), None)
    components = [s for s in all_specs if s.get('type') != 'VIEWPORT']
    base_specs = [s for s in components if not s.get('css_selector_suffix')]
    state_specs = [s for s in components if s.get('css_selector_suffix')]

    if viewport:
        print(f"Viewport: {viewport['viewport']['label']}")
    print(f"Extracted {len(base_specs)} component specs, {len(state_specs)} variant/state specs")
    for s in base_specs[:10]:
        states_for = [x['css_selector_suffix'] for x in state_specs if x.get('variant_of') == s['name']]
        states_str = f"  [{', '.join(states_for)}]" if states_for else ''
        print(f"  {s['type']:12} {s['name']}{states_str}  ({len(s['css'])} CSS props)")
    if len(base_specs) > 10:
        print(f"  ... and {len(base_specs)-10} more")
    print(f"Written: {out_path}")

if __name__ == '__main__':
    main()
