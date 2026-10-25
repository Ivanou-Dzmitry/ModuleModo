import math

import bmesh
from mathutils import Vector

MIN_MARGIN = 0.05
MIN_STRAIGHT = 0.05
MIN_GAP = 0.15
EPS = 1e-6


def _clamp(value, low, high):
    return max(low, min(high, value))


def _fit(avail, count, size, gap, min_size=0.1):
    """Shrink `count` openings of `size` with `gap` between them so they fit into `avail`."""
    if count == 1:
        return _clamp(size, min_size, avail), 0.0
    gap = max(gap, MIN_GAP)
    if count * size + (count - 1) * gap > avail:
        size = (avail - (count - 1) * gap) / count
        if size < min_size:
            size = min_size
            gap = max((avail - count * size) / (count - 1), 0.0)
    return size, gap


def resolve_params(p):
    """Clamp raw operator values into a layout that is guaranteed to build.

    The wall is cut into one cell per opening (cells meet halfway between the
    openings); every opening is inset and extruded inside its own cell.
    """
    width, height = p["width"], p["height"]
    kind = p["opening"]

    out = {"width": width, "height": height, "kind": kind, "openings": [], "plain": [], "slab": None}
    if kind == 'NONE':
        return out
    if kind == 'BALCONY':
        return _resolve_balcony(p, out)

    count = int(_clamp(p["count"], 1, 3))
    vertical = p["direction"] == 'VERTICAL' and kind == 'WINDOW'
    gap = p["gap"]

    rise_req = p["arch_rise"] if p["arch"] else 0.0
    pointed = p["arch"] and p["arch_type"] == 'POINTED'
    segments = _arch_segments(p)

    if vertical:
        ow = _clamp(p["open_width"], 0.1, width - 2 * MIN_MARGIN)
        x_center = _clamp(width / 2 + p["offset_x"], ow / 2 + MIN_MARGIN, width - ow / 2 - MIN_MARGIN)
        bottom = 2 * MIN_MARGIN
        oh, g = _fit(height - bottom - MIN_MARGIN, count, p["open_height"], gap)
        total = count * oh + (count - 1) * g
        z_start = _clamp(p["sill_height"], bottom, height - MIN_MARGIN - total)
        placed = [(x_center - ow / 2, x_center + ow / 2, z_start + i * (oh + g)) for i in range(count)]
        cuts = [z_start + (i + 1) * oh + i * g + g / 2 for i in range(count - 1)]
        cells = [(0.0, width, lo, hi) for lo, hi in zip([0.0] + cuts, cuts + [height])]
    else:
        ow, g = _fit(width - 2 * MIN_MARGIN, count, p["open_width"], gap)
        total = count * ow + (count - 1) * g
        x_start = _clamp(width / 2 + p["offset_x"] - total / 2, MIN_MARGIN, width - MIN_MARGIN - total)
        if kind == 'DOOR':
            z0 = 0.0
        else:
            z0 = _clamp(p["sill_height"], 2 * MIN_MARGIN, height - 0.1 - MIN_MARGIN)
        oh = _clamp(p["open_height"], 0.1, height - z0 - MIN_MARGIN)
        placed = [(x_start + i * (ow + g), x_start + i * (ow + g) + ow, z0) for i in range(count)]
        cuts = [x_start + (i + 1) * ow + i * g + g / 2 for i in range(count - 1)]
        cells = [(lo, hi, 0.0, height) for lo, hi in zip([0.0] + cuts, cuts + [width])]

    rise, pointed = _arch_rise(rise_req, ow, oh, pointed)

    for (x0, x1, z0), cell in zip(placed, cells):
        sill = None
        if kind == 'WINDOW' and p["sill"]:
            room = z0 - cell[2] - 0.02
            sill = {
                "z_bottom": z0 - max(0.005, min(p["sill_thickness"], room)),
                "depth": max(p["sill_depth"], 0.01),
            }
        out["openings"].append({
            "cell": cell,
            "x0": x0,
            "x1": x1,
            "z0": z0,
            "z_top": z0 + oh,
            "rise": rise,
            "segments": segments,
            "pointed": pointed,
            "sill": sill,
        })

    out["depth"] = max(p["depth"], 0.0)
    return out


def _arch_segments(p):
    """Segment count of the arch; a pointed arch has the same number on both sides, so it is even."""
    if not p["arch"]:
        return 0
    segments = max(2, p["arch_segments"])
    if p["arch_type"] == 'POINTED':
        segments += segments % 2
    return segments


def _arch_rise(rise_req, width, open_height, pointed):
    """Return (rise, pointed) for one opening.

    Round arches cannot be higher than a semicircle. A pointed arch needs at least a
    semicircle's rise (lower would bulge above its own tip) and may use the whole
    opening height; when the opening is too low for that it falls back to a round arch.
    """
    if rise_req <= 0:
        return 0.0, False
    half = width / 2
    limit = open_height - MIN_STRAIGHT
    if pointed and limit >= half:
        return _clamp(rise_req, half, limit), True
    return _clamp(rise_req, 0.01, min(half, limit)), False


def _resolve_balcony(p, out):
    """Door and window side by side, optionally standing on a balcony slab.

    Columns: [left margin] [door cell] [window cell] [right margin]. The slab is
    a row spanning the cells; the margins stay plain wall. The door stands
    `door_step` above the slab and the window top is aligned with the door top.
    """
    width, height = out["width"], out["height"]
    slab_on = p["slab"]

    sx0, sx1 = 0.0, width
    z_bottom = z_top_slab = base_z = 0.0
    if slab_on:
        margin = _clamp(p["slab_margin"], 0.0, width / 4)
        sx0, sx1 = margin, width - margin
        z_bottom = _clamp(p["slab_offset"], 0.0, height / 4)
        z_top_slab = z_bottom + _clamp(p["slab_thickness"], 0.02, height / 4)
        base_z = z_top_slab

    avail = (sx1 - sx0) - 2 * MIN_MARGIN
    dw, ww = p["door_width"], p["open_width"]
    gap = max(p["gap"], MIN_GAP)
    if dw + ww + gap > avail:
        scale = max(avail - gap, 0.2) / (dw + ww)
        dw, ww = dw * scale, ww * scale
    dw, ww = max(dw, 0.1), max(ww, 0.1)
    total = dw + gap + ww
    start = _clamp((sx0 + sx1) / 2 + p["offset_x"] - total / 2, sx0 + MIN_MARGIN, max(sx0 + MIN_MARGIN, sx1 - MIN_MARGIN - total))

    door_z0 = base_z + (_clamp(p["door_step"], 0.0, height / 4) if slab_on else 0.0)
    door_top = _clamp(door_z0 + p["door_height"], door_z0 + 0.2, height - MIN_MARGIN)
    win_h = _clamp(p["open_height"], 0.1, door_top - base_z - 2 * MIN_MARGIN)
    win_z0 = door_top - win_h

    # Seen from the front (+Y) world +X runs to the left, so the first opening along +X is the right-hand one.
    first, second = (("door", dw), ("window", ww)) if p["flip"] else (("window", ww), ("door", dw))
    x_first = start
    x_second = start + first[1] + gap
    cut = start + first[1] + gap / 2

    rise_req = p["arch_rise"] if p["arch"] else 0.0
    pointed = p["arch"] and p["arch_type"] == 'POINTED'
    segments = _arch_segments(p)

    cells = [(sx0, cut, base_z, height), (cut, sx1, base_z, height)]
    for (name, w), x0, cell in zip((first, second), (x_first, x_second), cells):
        z0, z_top = (door_z0, door_top) if name == "door" else (win_z0, door_top)
        oh = z_top - z0
        sill = None
        if name == "window" and p["sill"]:
            room = z0 - cell[2] - 0.02
            sill = {
                "z_bottom": z0 - max(0.005, min(p["sill_thickness"], room)),
                "depth": max(p["sill_depth"], 0.01),
            }
        rise, is_pointed = _arch_rise(rise_req, w, oh, pointed)
        out["openings"].append({
            "cell": cell,
            "x0": x0,
            "x1": x0 + w,
            "z0": z0,
            "z_top": z_top,
            "rise": rise,
            "segments": segments,
            "pointed": is_pointed,
            "sill": sill,
        })

    if slab_on:
        rows = sorted({round(z, 5) for z in (0.0, z_bottom, z_top_slab, height)})
        if sx0 > EPS:
            # Side strips: no vertices on the outer wall edge, only a fan from the bottom wall corner
            # to the vertices on the slab's end line.
            for corner_x, inner_x in ((0.0, sx0), (width, sx1)):
                corner, top = (corner_x, 0.0), (corner_x, height)
                # With a strip under the slab the floor vertex of the slab end line is dropped:
                # that strip runs out to the wall corner instead.
                inner = [(inner_x, z) for z in rows if z > EPS or z_bottom <= EPS]
                for a, b in zip(inner[:-2], inner[1:-1]):
                    out["plain"].append([corner, a, b])
                out["plain"].append([corner, inner[-2], inner[-1], top])
        # Vertices on the slab's top edge: the cell cut plus every opening that sits on the slab,
        # so the slab and the wall above share all their vertices (no T-junctions).
        xs = {round(sx0, 5), round(cut, 5), round(sx1, 5)}
        for o in out["openings"]:
            if o["z0"] - o["cell"][2] <= EPS:
                xs.update((round(o["x0"], 5), round(o["x1"], 5)))
        xs = sorted(xs)
        if z_bottom > EPS:
            last = len(xs) - 2
            for i, (lo, hi) in enumerate(zip(xs, xs[1:])):
                lo_floor = 0.0 if i == 0 else lo
                hi_floor = width if i == last else hi
                out["plain"].append([(lo_floor, 0.0), (hi_floor, 0.0), (hi, z_bottom), (lo, z_bottom)])
        out["slab"] = {
            "xs": xs,
            "z_bottom": z_bottom,
            "z_top": z_top_slab,
            "depth": max(p["slab_depth"], 0.05),
        }

    out["depth"] = max(p["depth"], 0.0)
    return out


def _pointed_arch_points(x0, x1, z_spring, rise, segments):
    """Two-centred (pointed) arch: each half is a circle arc whose centre is on the spring line."""
    half = (x1 - x0) / 2
    xc = (x0 + x1) / 2
    radius = (half * half + rise * rise) / (2 * half)
    cx = x0 + radius
    end = math.atan2(rise, xc - cx)
    per_side = segments // 2
    left = []
    for k in range(per_side + 1):
        a = math.pi + (end - math.pi) * k / per_side
        left.append((cx + radius * math.cos(a), z_spring + radius * math.sin(a)))
    left[0] = (x0, z_spring)
    left[-1] = (xc, z_spring + rise)
    return left + [(2 * xc - x, z) for x, z in left[-2::-1]]


def _arch_points(x0, x1, z_spring, rise, segments, pointed=False):
    """Points (x, z) along an arch from the left spring to the right one."""
    if pointed:
        return _pointed_arch_points(x0, x1, z_spring, rise, segments)
    half = (x1 - x0) / 2
    xc = (x0 + x1) / 2
    radius = (half * half + rise * rise) / (2 * rise)
    zc = z_spring + rise - radius
    start = math.atan2(z_spring - zc, -half)
    end = math.atan2(z_spring - zc, half)
    points = []
    for k in range(segments + 1):
        a = start + (end - start) * k / segments
        points.append((xc + radius * math.cos(a), zc + radius * math.sin(a)))
    points[0] = (x0, z_spring)
    points[-1] = (x1, z_spring)
    return points


def _plane_face(bm, verts):
    """Create a face in an XZ plane with its normal towards -Y, whatever the input winding."""
    area = 0.0
    for a, b in zip(verts, verts[1:] + verts[:1]):
        area += a.co.x * b.co.z - b.co.x * a.co.z
    if area < 0:
        verts = verts[::-1]
    return bm.faces.new(verts)


def _face_plus_y(bm):
    """Mirror the module in Y so the wall normal points to +Y and the recess goes towards -Y."""
    for v in bm.verts:
        v.co.y = -v.co.y
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces))
    bm.normal_update()


def _oriented_face(bm, verts, inside):
    """Create a face whose normal points away from the `inside` reference point."""
    normal = (verts[1].co - verts[0].co).cross(verts[2].co - verts[1].co)
    center = sum((v.co for v in verts), Vector()) / len(verts)
    if normal.dot(center - inside) < 0:
        verts = verts[::-1]
    return bm.faces.new(verts)


def _fill_opening(bm, outline):
    """Fill the opening with quads and one top triangle: a rectangle plus horizontal strips up the arch.

    `outline` runs bottom-left, bottom-right, spring-right, arch right to left, spring-left.
    """
    arch_count = len(outline) - 4
    if arch_count <= 0:
        _plane_face(bm, outline)
        return

    segments = arch_count + 1
    spring_r, spring_l = outline[2], outline[-1]
    arch = [spring_l] + outline[3:-1][::-1] + [spring_r]
    _plane_face(bm, [outline[0], outline[1], spring_r, spring_l])
    for k in range(segments // 2):
        if k + 1 == segments - k - 1:
            _plane_face(bm, [arch[k], arch[segments - k], arch[k + 1]])
        else:
            _plane_face(bm, [arch[k], arch[segments - k], arch[segments - k - 1], arch[k + 1]])


def build_module(bm, p):
    """Plane -> inset -> extrude, in the XZ plane facing +Y.

    The wall is a single plane at Y=0 with its normal towards +Y. Every opening
    is inset (four faces whose diagonals run from its cell corners to the
    opening corners) and its inner fill is pushed back by `depth` towards -Y.
    A window sill is the plane face under the window extruded out towards +Y.

    Everything is built facing -Y first and mirrored in Y at the end.
    """
    r = resolve_params(p)
    width, height = r["width"], r["height"]

    cache = {}

    def vert(x, z, y=0.0):
        key = (round(x, 5), round(y, 5), round(z, 5))
        if key not in cache:
            cache[key] = bm.verts.new((x, y, z))
        return cache[key]

    if r["kind"] == 'NONE':
        _plane_face(bm, [vert(0, 0), vert(width, 0), vert(width, height), vert(0, height)])
    else:
        for polygon in r["plain"]:
            _plane_face(bm, [vert(x, z) for x, z in polygon])
        for opening in r["openings"]:
            _build_opening(bm, vert, opening, r["depth"])
        if r["slab"]:
            _build_slab(bm, vert, r["slab"])

    _face_plus_y(bm)


def _build_opening(bm, vert, o, depth):
    cx0, cx1, cz0, cz1 = o["cell"]
    c_bl, c_br, c_tr, c_tl = vert(cx0, cz0), vert(cx1, cz0), vert(cx1, cz1), vert(cx0, cz1)

    x0, x1, z0, z_top, rise = o["x0"], o["x1"], o["z0"], o["z_top"], o["rise"]
    z_spring = z_top - rise
    flush = z0 - cz0 <= EPS      # opening starts right at the bottom of its cell
    open_floor = z0 <= EPS       # opening reaches the world floor, so the niche has no floor
    sill = o["sill"]

    open_bl, open_br = vert(x0, z0), vert(x1, z0)
    spring_l, spring_r = vert(x0, z_spring), vert(x1, z_spring)

    _plane_face(bm, [c_bl, open_bl, spring_l, c_tl])
    _plane_face(bm, [open_br, c_br, c_tr, spring_r])

    sill_bl = sill_br = None
    if sill:
        sill_bl, sill_br = vert(x0, sill["z_bottom"]), vert(x1, sill["z_bottom"])
        _plane_face(bm, [c_bl, c_br, sill_br, sill_bl])
        _plane_face(bm, [c_bl, sill_bl, open_bl])
        _plane_face(bm, [c_br, open_br, sill_br])
    elif not flush:
        _plane_face(bm, [c_bl, c_br, open_br, open_bl])

    arch_mid = []
    if rise > 0:
        arch = _arch_points(x0, x1, z_spring, rise, o["segments"], o["pointed"])
        arch_mid = [vert(x, z) for x, z in arch[1:-1]]
        arch_row = [spring_l] + arch_mid + [spring_r]
        n = len(arch_row) - 1
        m = n // 2
        for k in range(m):
            _plane_face(bm, [c_tl, arch_row[k], arch_row[k + 1]])
        if n % 2:
            _plane_face(bm, [c_tl, arch_row[m], arch_row[m + 1], c_tr])
            first_right = m + 1
        else:
            _plane_face(bm, [c_tl, arch_row[m], c_tr])
            first_right = m
        for k in range(first_right, n):
            _plane_face(bm, [c_tr, arch_row[k], arch_row[k + 1]])
    else:
        _plane_face(bm, [spring_l, spring_r, c_tr, c_tl])

    outline = [open_bl, open_br, spring_r] + arch_mid[::-1] + [spring_l]
    if depth <= EPS:
        _fill_opening(bm, outline)
    else:
        inner = [vert(v.co.x, v.co.z, depth) for v in outline]
        _fill_opening(bm, inner)
        for i in range(len(outline)):
            if open_floor and i == 0:
                continue
            j = (i + 1) % len(outline)
            bm.faces.new((outline[i], outline[j], inner[j], inner[i]))

    if sill:
        _extrude_sill(bm, open_bl, open_br, sill_bl, sill_br, sill["depth"])


def _build_slab(bm, vert, slab):
    """Balcony slab: the plane strip under the openings extruded out towards -Y (built pre-mirror)."""
    xs, zb, zt, depth = slab["xs"], slab["z_bottom"], slab["z_top"], slab["depth"]
    back_b = [vert(x, zb) for x in xs]
    back_t = [vert(x, zt) for x in xs]
    front_b = [bm.verts.new((x, -depth, zb)) for x in xs]
    front_t = [bm.verts.new((x, -depth, zt)) for x in xs]
    inside = Vector(((xs[0] + xs[-1]) / 2, -depth / 2, (zb + zt) / 2))

    last = len(xs) - 1
    for i in range(last):
        _plane_face(bm, [front_b[i], front_b[i + 1], front_t[i + 1], front_t[i]])
        _oriented_face(bm, [back_t[i], back_t[i + 1], front_t[i + 1], front_t[i]], inside)
        _oriented_face(bm, [back_b[i], back_b[i + 1], front_b[i + 1], front_b[i]], inside)
    _oriented_face(bm, [back_b[0], back_t[0], front_t[0], front_b[0]], inside)
    _oriented_face(bm, [back_b[last], back_t[last], front_t[last], front_b[last]], inside)


def _extrude_sill(bm, top_l, top_r, bottom_l, bottom_r, depth):
    """Extrude the (left out) plane rectangle under the window towards -Y."""
    front = [bm.verts.new((v.co.x, -depth, v.co.z)) for v in (bottom_l, bottom_r, top_r, top_l)]
    back = [bottom_l, bottom_r, top_r, top_l]
    inside = Vector(((top_l.co.x + top_r.co.x) / 2, 0.0, (top_l.co.z + bottom_l.co.z) / 2))
    bm.faces.new(front)
    for i in range(4):
        j = (i + 1) % 4
        _oriented_face(bm, [back[i], back[j], front[j], front[i]], inside)


def apply_pivot(bm, pivot, width):
    """The wall plane stays at Y=0; X is the center or the left corner."""
    if pivot == 'CENTER':
        bmesh.ops.translate(bm, verts=list(bm.verts), vec=Vector((-width / 2, 0.0, 0.0)))
