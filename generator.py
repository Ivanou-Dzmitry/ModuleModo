import math

import bmesh
from mathutils import Matrix, Vector

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

    out = {"width": width, "height": height, "kind": kind, "openings": [], "plain": [], "slab": None, "slabs": []}
    if kind == 'NONE':
        return out
    if kind == 'BALCONY':
        return _resolve_balcony(p, out)
    if kind == 'LOGGIA':
        return _resolve_loggia(p, out)
    if kind == 'ENTRANCE':
        return _resolve_entrance(p, out)

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
            z0 = _clamp(p["door_step"], 0.0, height / 4)   # threshold; 0 leaves the niche open to the floor
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

    for opening in out["openings"]:
        opening["frame"] = _frame_spec(opening, p)
        opening["trim"] = None if opening["frame"] else _trim_spec(opening, p)

    out["depth"] = max(p["depth"], 0.0)
    return out


def _frame_spec(o, p):
    """A frame round an opening: two posts and a head (a flat bar, or an arch band over an arch).

    The frame replaces the lintel and the arch band. It is sized to stay inside the cell of the
    opening and is left out when there is no room for it.
    """
    if not p.get("frame"):
        return None
    cx0, cx1, cz0, cz1 = o["cell"]
    room_x = min(o["x0"] - cx0, cx1 - o["x1"]) - 0.05
    room_up = cz1 - o["z_top"] - 0.05
    if o["rise"] > 0:
        room_up /= 1.7 if o["pointed"] else 1.05    # the offset of an arch is longer at its tip
    # A raised opening without a sill gets a bar under it too: the frame is a closed ring. A sill
    # takes the place of that bar, and an opening near the floor (a door) has none.
    bottom = o["sill"] is None and o["z0"] - cz0 >= 0.25
    width = min(p.get("frame_width", 0.12), room_x, room_up)
    if bottom:
        width = min(width, o["z0"] - cz0 - 0.05)
    if width < 0.03:
        return None
    return {"width": width, "depth": max(p.get("frame_depth", 0.04), 0.02), "bottom": bottom}


def _trim_spec(o, p):
    """Trim above an opening: a trapezoid lintel over a straight top, an archivolt band round an arch.

    Both are plane regions extruded out of the wall; they are sized so that they stay inside the
    cell of the opening, and left out when there is no room for them.
    """
    if not p.get("trim"):
        return None
    cx0, cx1, cz0, cz1 = o["cell"]
    depth = max(p.get("trim_depth", 0.06), 0.02)
    room_x = min(o["x0"] - cx0, cx1 - o["x1"]) - 0.05
    room_up = cz1 - o["z_top"] - 0.05
    if o["rise"] > 0:
        # the offset of a pointed arch is longer at the tip, so keep more room above it
        width = min(p.get("trim_width", 0.2), room_x, room_up / (1.7 if o["pointed"] else 1.05))
        if width < 0.03:
            return None
        return {"kind": 'ARCH', "width": width, "depth": depth}
    height = min(p.get("trim_height", 0.35), room_up)
    if height < 0.05:
        return None
    # The top corners of the lintel must stay inside the face above the opening, that is on the inner
    # side of the diagonals that run from the cell corners to the corners of the opening.
    t = (cz1 - o["z_top"] - height) / (cz1 - o["z_top"])
    left_limit = o["x0"] - (cx0 + t * (o["x0"] - cx0)) - 0.03
    right_limit = (cx1 - t * (cx1 - o["x1"])) - o["x1"] - 0.03
    flare = _clamp(p.get("trim_flare", 0.15), 0.0, max(min(left_limit, right_limit, room_x), 0.0))
    return {"kind": 'LINTEL', "height": height, "flare": flare, "depth": depth}


def _resolve_entrance(p, out):
    """Door(s) with an optional porch slab at the bottom and an optional canopy slab on top.

    Both slabs are plane rectangles extruded out of the wall, like the balcony slab. The
    porch stands on the ground, so it has no bottom face. Doors stand on a threshold above it.
    """
    width, height = out["width"], out["height"]
    count = int(_clamp(p["count"], 1, 3))
    margin = _clamp(p["porch_margin"], 0.0, width / 4)
    sx0, sx1 = margin, width - margin

    porch_top = _clamp(p["porch_thickness"], 0.02, height / 4) if p["porch"] else 0.0
    canopy_t = _clamp(p["canopy_thickness"], 0.02, height / 8) if p["canopy"] else 0.0
    canopy_gap = max(p["canopy_gap"], 0.1) if p["canopy"] else 0.0

    dw, gap = _fit((sx1 - sx0) - 2 * MIN_MARGIN, count, p["door_width"], p["gap"])
    total = count * dw + (count - 1) * gap
    x_start = _clamp((sx0 + sx1) / 2 + p["offset_x"] - total / 2, sx0 + MIN_MARGIN,
                     max(sx0 + MIN_MARGIN, sx1 - MIN_MARGIN - total))

    z0 = porch_top + _clamp(p["door_step"], 0.0, height / 4)
    top_limit = height - MIN_MARGIN - canopy_t - canopy_gap
    door_top = _clamp(z0 + p["door_height"], z0 + 0.3, max(z0 + 0.3, top_limit))
    cell_top = door_top + canopy_gap if p["canopy"] else height
    canopy_top = cell_top + canopy_t

    cuts = [x_start + (i + 1) * dw + i * gap + gap / 2 for i in range(count - 1)]
    xs_cells = [sx0] + cuts + [sx1]

    rise_req = p["arch_rise"] if p["arch"] else 0.0
    pointed_req = p["arch"] and p["arch_type"] == 'POINTED'
    segments = _arch_segments(p)
    rise, pointed = _arch_rise(rise_req, dw, door_top - z0, pointed_req)

    for i, (lo, hi) in enumerate(zip(xs_cells, xs_cells[1:])):
        x0 = x_start + i * (dw + gap)
        out["openings"].append({
            "cell": (lo, hi, porch_top, cell_top),
            "x0": x0,
            "x1": x0 + dw,
            "z0": z0,
            "z_top": door_top,
            "rise": rise,
            "segments": segments,
            "pointed": pointed,
            "sill": None,
        })

    rows = sorted({round(z, 5) for z in (0.0, porch_top, cell_top, canopy_top, height) if z <= height + EPS})
    if margin > EPS:
        # Side strips: a fan from the bottom wall corner to the vertices on the slab end line.
        for corner_x, inner_x in ((0.0, sx0), (width, sx1)):
            corner, top = (corner_x, 0.0), (corner_x, height)
            inner = [(inner_x, z) for z in rows]
            for a, b in zip(inner[:-2], inner[1:-1]):
                out["plain"].append([corner, a, b])
            out["plain"].append([corner, inner[-2], inner[-1], top])

    if p["canopy"] and canopy_top < height - EPS:
        for lo, hi in zip(xs_cells, xs_cells[1:]):
            out["plain"].append([(lo, canopy_top), (hi, canopy_top), (hi, height), (lo, height)])

    if p["porch"]:
        xs = {round(x, 5) for x in xs_cells}
        for o in out["openings"]:
            if o["z0"] - porch_top <= EPS:   # a door flush with the porch puts its jambs on the slab edge
                xs.update((round(o["x0"], 5), round(o["x1"], 5)))
        out["slabs"].append({"xs": sorted(xs), "z_bottom": 0.0, "z_top": porch_top,
                             "depth": max(p["porch_depth"], 0.05), "bottom": False})
    if p["canopy"]:
        out["slabs"].append({"xs": [round(x, 5) for x in xs_cells], "z_bottom": cell_top, "z_top": canopy_top,
                             "depth": max(p["canopy_depth"], 0.05), "bottom": True})

    out["depth"] = max(p["depth"], 0.0)
    return out


def _resolve_loggia(p, out):
    """A recess in the facade (the loggia) with a parapet in front of its lower part.

    The back wall of the loggia is a door + window module (the balcony layout without
    the slab) or a single door, standing on the loggia floor; the parapet hides its lower part.
    """
    width, height = out["width"], out["height"]
    lw = _clamp(p["loggia_width"], 0.8, width - 0.2)
    lx0 = _clamp(width / 2 + p["offset_x"] - lw / 2, 0.1, width - 0.1 - lw)
    floor = _clamp(p["loggia_floor"], 0.0, height / 3)
    z_open = floor + _clamp(p["parapet_height"], 0.3, height / 2)
    z_top = _clamp(z_open + p["loggia_height"], z_open + 0.3, height - 0.1)
    depth = max(p["loggia_depth"], 0.4)
    thick = _clamp(p["parapet_thickness"], 0.03, depth / 2)

    back_height = z_top - floor
    if p["loggia_content"] == 'DOOR':
        # one door in the middle of the back wall: an ordinary door module, so no cut between cells
        door_p = dict(p, opening='DOOR', width=lw, height=back_height, open_width=p["door_width"],
                      open_height=p["door_height"], count=1, direction='HORIZONTAL', offset_x=0.0,
                      door_step=max(p["door_step"], 0.03), sill=False, base=False, cornice=False)
        back = resolve_params(door_p)
        cut = None
    else:
        back_p = dict(p, width=lw, height=back_height, offset_x=0.0, slab=False, floor_step=True)
        back = _resolve_balcony(back_p, {"width": lw, "height": back_height, "kind": 'BALCONY',
                                         "openings": [], "plain": [], "slab": None, "slabs": []})
        cut = lx0 + back["openings"][0]["cell"][1]
    out["loggia"] = {
        "x0": lx0,
        "x1": lx0 + lw,
        "cut": cut,
        "floor": floor,
        "z_open": z_open,
        "z_top": z_top,
        "depth": depth,
        "parapet": thick,
    }
    out["back"] = back
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

    step = _clamp(p["door_step"], 0.0, height / 4) if (slab_on or p.get("floor_step")) else 0.0
    if p.get("floor_step"):
        step = max(step, 0.03)   # the door must not sit flush with the floor, the floor edge needs no extra vertices
    door_z0 = base_z + step
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


def _face_plus_y(bm, verts=None, faces=None):
    """Mirror the module in Y so the wall normal points to +Y and the recess goes towards -Y.

    Only the given vertices and faces are mirrored (default: the whole mesh).
    """
    for v in (bm.verts if verts is None else verts):
        v.co.y = -v.co.y
    bmesh.ops.reverse_faces(bm, faces=list(bm.faces if faces is None else faces))
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

    An optional plinth (bottom band) and cornice (top band) are rectangles of the plane
    extruded out towards +Y; the module itself is built in the height that is left.

    Everything is built facing -Y first and mirrored in Y at the end.
    """
    if p["opening"] == 'CORNER':
        _build_corner(bm, p)
    elif p["opening"] == 'INNER_CORNER':
        _build_corner(bm, p, inner=True)
    elif p["opening"] == 'BAY':
        _build_bay(bm, p)
    else:
        _build_straight(bm, p)


def _build_straight(bm, p):
    start_verts, start_faces = set(bm.verts), set(bm.faces)
    base_h, cornice_h = _band_heights(p)
    inner_p = dict(p, height=p["height"] - base_h - cornice_h) if (base_h or cornice_h) else p
    r = resolve_params(inner_p)

    before = set(bm.verts)
    if r["kind"] == 'LOGGIA':
        _build_loggia(bm, r)
    else:
        _build_wall(bm, r)

    if base_h or cornice_h:
        inner = [v for v in bm.verts if v not in before]
        bmesh.ops.translate(bm, verts=inner, vec=Vector((0.0, 0.0, base_h)))
        _build_bands(bm, inner, p, base_h, cornice_h)
    _face_plus_y(bm, [v for v in bm.verts if v not in start_verts], [f for f in bm.faces if f not in start_faces])


def _build_bay(bm, p):
    """A bay window (oriel): a box or a splayed (trapezoid) volume sticking out of the wall.

    The facade has a rectangular opening; the front and the two sides of the bay are ordinary
    window modules (so they get the usual inset windows), placed and rotated around the opening,
    and a flat top and bottom close the volume. Every part shares its vertices with its
    neighbours, so the whole mesh is closed without T-junctions.

    The bay is built in its final orientation: it sticks out towards +Y.

    `bay_full` makes the bay take the whole width and height of the module and leaves out the
    facade, the top and the bottom: such modules stack into floors and connect to neighbouring
    walls along their vertical edges. Only this variant takes a plinth and a cornice (a plinth
    for the ground floor, a cornice for the top one); the ordinary bay ignores them.
    """
    width, height = p["width"], p["height"]
    full = p.get("bay_full", False)
    bay_w = width if full else _clamp(p["bay_width"], 0.8, width - 0.2)
    depth = max(p["bay_depth"], 0.2)
    splay = _clamp(p["bay_splay"], 0.0, max(0.0, min(depth * 2, bay_w / 2 - 0.3)))
    xl = 0.0 if full else _clamp(width / 2 + p["offset_x"] - bay_w / 2, 0.1, width - 0.1 - bay_w)
    xr = xl + bay_w
    z0 = 0.0 if full else _clamp(p["bay_floor"], 0.1, height / 2)
    bay_h = height if full else _clamp(p["bay_height"], 0.8, height - z0 - 0.1)
    zt = z0 + bay_h
    # a full-height bay can carry a plinth and a cornice; the windows get the height that is left
    hb, ht = _band_heights(p) if full else (0.0, 0.0)
    if full:
        # The bands are the outline moved along +Y, which needs sides that are not parallel to Y. The
        # limit applies with or without bands, so floors with and without them still stack.
        splay = max(splay, min(0.25, depth * 2, bay_w / 2 - 0.3))
    front_w = bay_w - 2 * splay
    side_len = math.hypot(depth, splay)
    angle = math.atan2(depth, splay)

    if not full:
        # Facade: the wall plane with the opening for the bay.
        c_bl, c_br, c_tr, c_tl = (bm.verts.new(v) for v in ((0, 0, 0), (width, 0, 0), (width, 0, height), (0, 0, height)))
        o_bl, o_br, o_tr, o_tl = (bm.verts.new(v) for v in ((xl, 0, z0), (xr, 0, z0), (xr, 0, zt), (xl, 0, zt)))
        for verts in ([c_bl, o_bl, o_tl, c_tl], [o_br, c_br, c_tr, o_tr], [c_bl, c_br, o_br, o_bl], [o_tl, o_tr, c_tr, c_tl]):
            _directed_face(bm, verts, (0, 1, 0))

    def module(length, windowed, open_width):
        sides = dict(p, opening='WINDOW' if windowed else 'NONE', width=length, height=bay_h - hb - ht, count=1,
                     base=False, cornice=False, offset_x=0.0, open_width=open_width, mitre=None)
        before = set(bm.verts)
        _build_straight(bm, sides)
        return [v for v in bm.verts if v not in before]

    def place(verts, turn, shift):
        if turn:
            bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), matrix=Matrix.Rotation(turn, 3, 'Z'), verts=verts)
        bmesh.ops.translate(bm, verts=verts, vec=Vector(shift))

    side_windows = p["bay_side_windows"]
    side_open = max(0.3, min(p["open_width"], side_len - 0.4))
    place(module(front_w, True, p["open_width"]), 0.0, (xl + splay, depth, z0 + hb))
    place(module(side_len, side_windows, side_open), angle, (xl, 0.0, z0 + hb))
    place(module(side_len, side_windows, side_open), -angle, (xr - splay, depth, z0 + hb))

    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)   # welds the shared edges

    found = {(round(v.co.x, 5), round(v.co.y, 5), round(v.co.z, 5)): v for v in bm.verts}

    def vert(x, y, z):
        return found[(round(x, 5), round(y, 5), round(z, 5))]

    if hb or ht:
        _bay_bands(bm, [(xl, 0.0), (xl + splay, depth), (xr - splay, depth), (xr, 0.0)], hb, ht, p)
    if not full:   # a full-height bay is open at the top and the bottom so that floors can be stacked
        for z, direction in ((zt, (0, 0, 1)), (z0, (0, 0, -1))):
            _directed_face(bm, [vert(xl, 0, z), vert(xl + splay, depth, z), vert(xr - splay, depth, z), vert(xr, 0, z)], direction)
    bm.normal_update()


def _bay_bands(bm, outline, hb, ht, p):
    """Plinth and cornice of a full-height bay.

    Each band is the strip between the outline of the bay and the same outline moved by the
    band depth along +Y. At the ends of the module that is the same profile as the straight
    bands of a neighbouring wall, so the bands run on from module to module. The ends stay open.
    """
    if hb:
        _band_along_outline(bm, outline, hb, 0.0, max(p["base_depth"], 0.02))
    if ht:
        _band_along_outline(bm, outline, p["height"] - ht, p["height"], max(p["cornice_depth"], 0.02))


def _band_along_outline(bm, outline, z_adj, z_far, depth):
    """A band attached to the module along `outline` at height `z_adj`, reaching to `z_far`."""
    path = []
    for (ax, ay), (bx, by) in zip(outline, outline[1:]):
        dx, dy = bx - ax, by - ay
        length = math.hypot(dx, dy)
        on = []
        for v in bm.verts:
            if abs(v.co.z - z_adj) > 1e-5:
                continue
            wx, wy = v.co.x - ax, v.co.y - ay
            t = (wx * dx + wy * dy) / (length * length)
            if -1e-6 <= t <= 1 + 1e-6 and abs(wx * dy - wy * dx) / length < 1e-5:
                on.append((t, v))
        for _, v in sorted(on, key=lambda item: item[0]):
            if not path or path[-1] is not v:
                path.append(v)

    made = {}

    def vert(x, y, z):
        key = (round(x, 5), round(y, 5), round(z, 5))
        if key not in made:
            made[key] = bm.verts.new((x, y, z))
        return made[key]

    towards_adjacent = 1.0 if z_adj > z_far else -1.0   # the face at the module edge looks away from the band
    for a, b in zip(path, path[1:]):
        ax, ay, bx, by = a.co.x, a.co.y, b.co.x, b.co.y
        outward = (-(by - ay), bx - ax, 0.0)
        a_far, b_far = vert(ax, ay, z_far), vert(bx, by, z_far)
        a_adj_front, b_adj_front = vert(ax, ay + depth, z_adj), vert(bx, by + depth, z_adj)
        a_far_front, b_far_front = vert(ax, ay + depth, z_far), vert(bx, by + depth, z_far)
        _directed_face(bm, [a, b, b_adj_front, a_adj_front], (0, 0, towards_adjacent))
        _directed_face(bm, [a_adj_front, b_adj_front, b_far_front, a_far_front], outward)
        _directed_face(bm, [a_far, b_far, b_far_front, a_far_front], (0, 0, -towards_adjacent))


def _build_corner(bm, p, inner=False):
    """Two window walls meeting at a vertical edge on the Z axis, bands mitred at the corner.

    Outer corner: wall A faces +Y and runs along -X, wall B faces +X and runs along -Y (the
    solid is behind both). Inner corner: wall A runs along +X, wall B along +Y, and the two
    face into the quadrant between them. The origin is at the bottom of the corner edge.

    Each wall is an ordinary module with its own plinth and cornice. At the corner the front
    edge of each band runs on to the outer corner (outer) or stops at the inner vertex (inner),
    so the two bands meet along one diagonal and no extra vertices are needed.
    """
    width = p["width"]
    both = p["corner_walls"] == 'BOTH'
    # Positive offset moves the windows away from the corner. The corner is at A's last end and
    # B's first end for an outer corner, and the other way round for an inner one.
    away = -p["offset_x"] if not inner else p["offset_x"]
    side_a = dict(p, opening='WINDOW', offset_x=away, mitre='FIRST_IN' if inner else 'LAST')
    side_b = dict(p, opening='WINDOW' if both else 'NONE', offset_x=-away, mitre='LAST_IN' if inner else 'FIRST')

    before = set(bm.verts)
    _build_straight(bm, side_a)
    wall_a = [v for v in bm.verts if v not in before]
    if not inner:
        bmesh.ops.translate(bm, verts=wall_a, vec=Vector((-width, 0.0, 0.0)))

    before = set(bm.verts)
    _build_straight(bm, side_b)
    wall_b = [v for v in bm.verts if v not in before]
    bmesh.ops.rotate(bm, cent=(0.0, 0.0, 0.0), matrix=Matrix.Rotation(-math.pi / 2, 3, 'Z'), verts=wall_b)
    if inner:
        bmesh.ops.translate(bm, verts=wall_b, vec=Vector((0.0, width, 0.0)))

    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-5)   # welds the shared corner edge
    bm.normal_update()


def _band_heights(p):
    """Heights of the plinth and the cornice, kept small enough to leave room for the module."""
    height = p["height"]
    base_h = _clamp(p["base_height"], 0.02, height / 4) if p["base"] else 0.0
    if p["opening"] == 'ENTRANCE' and p["porch"]:
        base_h = 0.0   # the porch slab already stands on the ground and acts as the base
    cornice_h = _clamp(p["cornice_height"], 0.02, height / 4) if p["cornice"] else 0.0
    return base_h, cornice_h


def _build_bands(bm, inner, p, base_h, cornice_h):
    """Plinth and cornice: full-width rectangles extruded out of the wall plane.

    A band shares every vertex of the module's edge it touches, so there are no T-junctions.
    The plinth keeps its bottom face: on an upper floor it does not meet the module below
    (on the ground floor that face is easy to delete by hand).
    """
    height = p["height"]
    found = {(round(v.co.x, 5), round(v.co.z, 5)): v for v in inner if abs(v.co.y) < 1e-6}

    def vert(x, z):
        key = (round(x, 5), round(z, 5))
        if key not in found:
            found[key] = bm.verts.new((x, 0.0, z))
        return found[key]

    def edge_xs(z):
        return sorted({x for x, vz in found if abs(vz - round(z, 5)) < 1e-4})

    # 'FIRST' / 'LAST': this end of the wall meets an outer corner, the band runs on past the wall end.
    # '..._IN': an inner corner, the band stops short of the wall end.
    mitre = p.get("mitre")

    def mitred(slab):
        depth = slab["depth"]
        if mitre == 'FIRST':
            slab["extend_first"] = depth
        elif mitre == 'LAST':
            slab["extend_last"] = depth
        elif mitre == 'FIRST_IN':
            slab["extend_first"] = -depth
        elif mitre == 'LAST_IN':
            slab["extend_last"] = -depth
        return slab

    if base_h:
        _build_slab(bm, vert, mitred({"xs": edge_xs(base_h), "z_bottom": 0.0, "z_top": base_h,
                                      "depth": max(p["base_depth"], 0.02), "bottom": True, "ends": False}))
    if cornice_h:
        _build_slab(bm, vert, mitred({"xs": edge_xs(height - cornice_h), "z_bottom": height - cornice_h,
                                      "z_top": height, "depth": max(p["cornice_depth"], 0.02),
                                      "bottom": True, "ends": False}))


def _vertex_cache(bm):
    cache = {}

    def vert(x, z, y=0.0):
        key = (round(x, 5), round(y, 5), round(z, 5))
        if key not in cache:
            cache[key] = bm.verts.new((x, y, z))
        return cache[key]

    return vert


def _build_wall(bm, r):
    width, height = r["width"], r["height"]
    vert = _vertex_cache(bm)

    if r["kind"] == 'NONE':
        _plane_face(bm, [vert(0, 0), vert(width, 0), vert(width, height), vert(0, height)])
        return
    for polygon in r["plain"]:
        _plane_face(bm, [vert(x, z) for x, z in polygon])
    for opening in r["openings"]:
        _build_opening(bm, vert, opening, r["depth"])
    if r["slab"]:
        _build_slab(bm, vert, r["slab"])
    for slab in r["slabs"]:
        _build_slab(bm, vert, slab)


def _directed_face(bm, verts, direction):
    """Create a face whose normal points the way `direction` does."""
    normal = (verts[1].co - verts[0].co).cross(verts[2].co - verts[1].co)
    if normal.dot(Vector(direction)) < 0:
        verts = verts[::-1]
    return bm.faces.new(verts)


def _build_loggia(bm, r):
    """Facade with a big opening, a loggia behind it and a parapet under the opening.

    Built facing -Y like everything else, so the loggia depth runs towards +Y here.
    All parts share their vertices with the back wall, so the mesh has no T-junctions.
    """
    width, height = r["width"], r["height"]
    L = r["loggia"]
    lx0, lx1, cut = L["x0"], L["x1"], L["cut"]
    fl, zo, zt, depth, thick = L["floor"], L["z_open"], L["z_top"], L["depth"], L["parapet"]
    vert = _vertex_cache(bm)

    # Facade: the wall plane with the opening above the parapet.
    c_bl, c_br, c_tr, c_tl = vert(0, 0), vert(width, 0), vert(width, height), vert(0, height)
    o_bl, o_br, o_tr, o_tl = vert(lx0, zo), vert(lx1, zo), vert(lx1, zt), vert(lx0, zt)
    _plane_face(bm, [c_bl, o_bl, o_tl, c_tl])
    _plane_face(bm, [o_br, c_br, c_tr, o_tr])
    _plane_face(bm, [c_bl, c_br, o_br, o_bl])
    _plane_face(bm, [o_tl, o_tr, c_tr, c_tl])

    # Back wall: the door and window module, moved to the back of the loggia.
    before = set(bm.verts)
    _build_wall(bm, r["back"])
    back_verts = [v for v in bm.verts if v not in before]
    bmesh.ops.translate(bm, verts=back_verts, vec=Vector((lx0, depth, fl)))
    back = {(round(v.co.x, 5), round(v.co.z, 5)): v for v in back_verts if abs(v.co.y - depth) < 1e-6}

    def back_at(x, z):
        return back[(round(x, 5), round(z, 5))]

    # With a door and a window the back wall has a vertex on its top and bottom edge where the two
    # cells meet. Only the ceiling and the floor touch those edges, so they are a quad plus a triangle
    # and the facade, parapet and the front edges of the floor and ceiling need no vertex there.
    bt_l, bt_r = back_at(lx0, zt), back_at(lx1, zt)
    bf_l, bf_r = back_at(lx0, fl), back_at(lx1, fl)
    bt_m = back_at(cut, zt) if cut is not None else None
    bf_m = back_at(cut, fl) if cut is not None else None
    p_open_l, p_open_r = vert(lx0, zo, thick), vert(lx1, zo, thick)
    p_floor_l, p_floor_r = vert(lx0, fl, thick), vert(lx1, fl, thick)

    if bt_m is not None:
        _directed_face(bm, [o_tl, o_tr, bt_r, bt_m], (0, 0, -1))
        _directed_face(bm, [o_tl, bt_m, bt_l], (0, 0, -1))
    else:
        _directed_face(bm, [o_tl, o_tr, bt_r, bt_l], (0, 0, -1))
    _directed_face(bm, [o_bl, o_br, p_open_r, p_open_l], (0, 0, 1))
    _directed_face(bm, [p_open_l, p_open_r, p_floor_r, p_floor_l], (0, 1, 0))
    if bf_m is not None:
        _directed_face(bm, [p_floor_l, p_floor_r, bf_r, bf_m], (0, 0, 1))
        _directed_face(bm, [p_floor_l, bf_m, bf_l], (0, 0, 1))
    else:
        _directed_face(bm, [p_floor_l, p_floor_r, bf_r, bf_l], (0, 0, 1))

    # Side walls: the L-shaped wall is two quads split by the diagonal from the parapet's
    # top corner to the back ceiling corner.
    sides = (
        (1, o_bl, o_tl, bt_l, p_open_l, bf_l, p_floor_l),
        (-1, o_br, o_tr, bt_r, p_open_r, bf_r, p_floor_r),
    )
    for inward, f_bottom, f_top, b_top, p_open, b_floor, p_floor in sides:
        direction = (inward, 0, 0)
        _directed_face(bm, [f_bottom, f_top, b_top, p_open], direction)
        _directed_face(bm, [p_open, b_top, b_floor, p_floor], direction)


def _offset_row(vert, arch_row, width):
    """The outer row of an arch band: the arch moved out by `width`, with horizontal feet at the springs."""
    pts = [(v.co.x, v.co.z) for v in arch_row]
    count = len(pts) - 1

    def normal(a, b):
        dx, dz = b[0] - a[0], b[1] - a[1]
        length = math.hypot(dx, dz)
        return (-dz / length, dx / length)

    outer = [vert(pts[0][0] - width, pts[0][1])]
    for k in range(1, count):
        n1, n2 = normal(pts[k - 1], pts[k]), normal(pts[k], pts[k + 1])
        scale = width / (1.0 + n1[0] * n2[0] + n1[1] * n2[1])    # miter: the offset is `width` on both sides
        outer.append(vert(pts[k][0] + (n1[0] + n2[0]) * scale, pts[k][1] + (n1[1] + n2[1]) * scale))
    outer.append(vert(pts[-1][0] + width, pts[-1][1]))
    return outer


def _archivolt_band(bm, vert, arch_row, outer, depth, feet):
    """The band between an arch and its outer row, extruded out towards -Y. `feet` closes its two ends.

    The front vertices come from the shared cache, so a frame that meets the band shares them.
    """
    def front(v):
        return vert(v.co.x, v.co.z, -depth)

    for k in range(len(arch_row) - 1):
        a, b = arch_row[k].co, arch_row[k + 1].co
        e, f = outer[k].co, outer[k + 1].co
        _plane_face(bm, [front(arch_row[k]), front(arch_row[k + 1]), front(outer[k + 1]), front(outer[k])])
        _directed_face(bm, [arch_row[k], arch_row[k + 1], front(arch_row[k + 1]), front(arch_row[k])], (b.z - a.z, 0, a.x - b.x))
        _directed_face(bm, [outer[k], outer[k + 1], front(outer[k + 1]), front(outer[k])], (e.z - f.z, 0, f.x - e.x))
    if feet:
        _directed_face(bm, [arch_row[0], outer[0], front(outer[0]), front(arch_row[0])], (0, 0, -1))
        _directed_face(bm, [arch_row[-1], outer[-1], front(outer[-1]), front(arch_row[-1])], (0, 0, -1))


def _extrude_frame(bm, vert, depth, window, foot, head, wall=None, feet=False, bottom=False):
    """A frame: two posts and a head round a window, extruded out towards -Y.

    `window` is (open_bl, open_br, spring_l, spring_r, arch_row or None), `foot` is the front
    vertices (left, right) of the outer outline's feet, and `head` is (head_l, head_r, outer row or
    None): the top corners of the outer outline for a flat head, or the outer row of the arch band.
    `wall` is the wall vertices (lb, rb) of those feet. It gives the posts their outer sides; leave it
    out when a sill under the posts builds the sides. `feet` closes the bottoms of the posts; a sill
    that carries the posts does it instead. With `bottom` the frame is a closed ring: a bar under the
    window joins the posts, and the feet are its underside.
    """
    open_bl, open_br, spring_l, spring_r, arch_row = window
    flb, frb = foot
    head_l, head_r, outer = head

    def F(v):
        return vert(v.co.x, v.co.z, -depth)

    if arch_row:
        _plane_face(bm, [flb, F(open_bl), F(spring_l), F(outer[0])])
        _archivolt_band(bm, vert, arch_row, outer, depth, feet=False)
        _plane_face(bm, [F(open_br), frb, F(outer[-1]), F(spring_r)])
    else:
        _plane_face(bm, [flb, F(open_bl), F(spring_l), F(head_l)])
        _plane_face(bm, [F(spring_l), F(spring_r), F(head_r), F(head_l)])
        _plane_face(bm, [F(open_br), frb, F(head_r), F(spring_r)])
        _directed_face(bm, [head_l, head_r, F(head_r), F(head_l)], (0, 0, 1))
        _directed_face(bm, [spring_l, spring_r, F(spring_r), F(spring_l)], (0, 0, -1))
    if wall:
        lb, rb = wall
        _directed_face(bm, [lb, head_l, F(head_l), flb], (-1, 0, 0))
        _directed_face(bm, [head_r, rb, frb, F(head_r)], (1, 0, 0))
        if feet:
            _directed_face(bm, [lb, open_bl, F(open_bl), flb], (0, 0, -1))
            _directed_face(bm, [open_br, rb, frb, F(open_br)], (0, 0, -1))
        if bottom:
            _plane_face(bm, [flb, frb, F(open_br), F(open_bl)])
            _directed_face(bm, [lb, rb, frb, flb], (0, 0, -1))
            _directed_face(bm, [open_bl, open_br, F(open_br), F(open_bl)], (0, 0, 1))
    _directed_face(bm, [open_bl, spring_l, F(spring_l), F(open_bl)], (1, 0, 0))
    _directed_face(bm, [spring_r, open_br, F(open_br), F(spring_r)], (-1, 0, 0))


def _extrude_frame_sill(bm, vert, depth, sill_bl, sill_br, open_bl, open_br):
    """A sill as wide as the frame and as deep, with the posts of the frame standing on it.

    Sill and frame form one body: the posts start at the bottom of the sill (`sill_bl`, `sill_br`)
    and build its outer sides, so the sill only has a front, a bottom and the part of its top that
    lies under the window.
    """
    def F(v):
        return vert(v.co.x, v.co.z, -depth)

    _plane_face(bm, [F(sill_bl), F(sill_br), F(open_br), F(open_bl)])
    _directed_face(bm, [sill_bl, sill_br, F(sill_br), F(sill_bl)], (0, 0, -1))
    _directed_face(bm, [open_bl, open_br, F(open_br), F(open_bl)], (0, 0, 1))


def _extrude_frame_sill_deep(bm, vert, depth, sill_depth, sill_bl, sill_br, open_bl, open_br, head_l, head_r):
    """A sill that sticks out further than the frame; the posts of the frame stand on it.

    Side view: the frame is a thin rectangle on the wall, the sill a thicker one under it. The top
    of the sill is the part under the window plus the strip in front of the posts. Each outer side
    of the sill and its post is one L-shaped plane, built from two quads.
    Returns the front vertices (left, right) of the feet of the posts.
    """
    def F(v):
        return vert(v.co.x, v.co.z, -depth)

    def S(v, z=None):
        return vert(v.co.x, v.co.z if z is None else z, -sill_depth)

    zt = open_bl.co.z
    flb, frb = vert(sill_bl.co.x, zt, -depth), vert(sill_br.co.x, zt, -depth)
    slb, srb = S(sill_bl, zt), S(sill_br, zt)
    sbl, sbr = S(sill_bl), S(sill_br)
    fol, fir = F(open_bl), F(open_br)

    _plane_face(bm, [sbl, sbr, srb, slb])
    _directed_face(bm, [sill_bl, sill_br, sbr, sbl], (0, 0, -1))
    _directed_face(bm, [sill_bl, sbl, slb, flb], (-1, 0, 0))
    _directed_face(bm, [sill_bl, flb, F(head_l), head_l], (-1, 0, 0))
    _directed_face(bm, [sill_br, sbr, srb, frb], (1, 0, 0))
    _directed_face(bm, [sill_br, frb, F(head_r), head_r], (1, 0, 0))
    _directed_face(bm, [open_bl, open_br, fir, fol], (0, 0, 1))
    _directed_face(bm, [fol, fir, srb, slb], (0, 0, 1))
    _directed_face(bm, [flb, fol, slb], (0, 0, 1))
    _directed_face(bm, [fir, frb, srb], (0, 0, 1))
    return flb, frb


def _extrude_lintel(bm, a, b, c, d, depth):
    """The trapezoid a-b-c-d (a, b on the top of the window, c, d above) extruded out towards -Y."""
    fa, fb, fc, fd = (bm.verts.new((v.co.x, -depth, v.co.z)) for v in (a, b, c, d))
    height = c.co.z - b.co.z
    flare = c.co.x - b.co.x
    _plane_face(bm, [fa, fb, fc, fd])
    _directed_face(bm, [a, b, fb, fa], (0, 0, -1))
    _directed_face(bm, [d, c, fc, fd], (0, 0, 1))
    _directed_face(bm, [a, d, fd, fa], (-height, 0, -flare))
    _directed_face(bm, [b, c, fc, fb], (height, 0, -flare))


def _build_opening(bm, vert, o, depth):
    cx0, cx1, cz0, cz1 = o["cell"]
    c_bl, c_br, c_tr, c_tl = vert(cx0, cz0), vert(cx1, cz0), vert(cx1, cz1), vert(cx0, cz1)

    x0, x1, z0, z_top, rise = o["x0"], o["x1"], o["z0"], o["z_top"], o["rise"]
    z_spring = z_top - rise
    flush = z0 - cz0 <= EPS      # opening starts right at the bottom of its cell
    open_floor = z0 <= EPS       # opening reaches the world floor, so the niche has no floor
    sill = o["sill"]

    frame = o.get("frame")
    deep_sill = False
    if frame and sill:
        # the posts of the frame stand on the sill. A sill that sticks out further than the frame is
        # a body of its own; otherwise the two are one body and share the deeper of the two depths
        if sill["depth"] > frame["depth"] + 0.005:
            deep_sill = True
        else:
            frame = dict(frame, depth=max(frame["depth"], sill["depth"]))
    trim = o.get("trim")
    arch_trim = bool(trim and trim["kind"] == 'ARCH' and rise > 0)
    lintel = trim if (trim and trim["kind"] == 'LINTEL' and rise <= 0) else None

    open_bl, open_br = vert(x0, z0), vert(x1, z0)
    spring_l, spring_r = vert(x0, z_spring), vert(x1, z_spring)

    arch_mid = []
    arch_row = outer = None
    if rise > 0:
        arch = _arch_points(x0, x1, z_spring, rise, o["segments"], o["pointed"])
        arch_mid = [vert(x, z) for x, z in arch[1:-1]]
        arch_row = [spring_l] + arch_mid + [spring_r]
        if frame or arch_trim:
            outer = _offset_row(vert, arch_row, frame["width"] if frame else trim["width"])

    sill_bl = sill_br = None
    if sill:
        wide = frame["width"] if frame else 0.0      # under a frame the sill is as wide as the frame
        sill_bl, sill_br = vert(x0 - wide, sill["z_bottom"]), vert(x1 + wide, sill["z_bottom"])

    # Posts of a frame: on a sill they start at its bottom, otherwise their feet stand on the bottom
    # edge of the opening and the frame is a П.
    lb = rb = head_l = head_r = None
    if frame:
        w = frame["width"]
        zf = z0 - w if frame.get("bottom") else z0      # a bottom bar puts the feet of the posts below the window
        lb, rb = (sill_bl, sill_br) if sill else (vert(x0 - w, zf), vert(x1 + w, zf))
        head_l, head_r = (outer[0], outer[-1]) if rise > 0 else (vert(x0 - w, z_top + w), vert(x1 + w, z_top + w))

    # Left and right faces
    if frame:
        _plane_face(bm, [c_bl, lb, head_l, c_tl])
        _plane_face(bm, [rb, c_br, c_tr, head_r])
    elif arch_trim:
        _plane_face(bm, [c_bl, open_bl, spring_l, outer[0]])
        _plane_face(bm, [outer[-1], spring_r, open_br, c_br])
        _plane_face(bm, [c_bl, outer[0], c_tl])
        _plane_face(bm, [outer[-1], c_br, c_tr])
    else:
        _plane_face(bm, [c_bl, open_bl, spring_l, c_tl])
        _plane_face(bm, [open_br, c_br, c_tr, spring_r])

    # Below the opening
    if sill:
        _plane_face(bm, [c_bl, c_br, sill_br, sill_bl])
        if not frame:
            _plane_face(bm, [c_bl, sill_bl, open_bl])
            _plane_face(bm, [c_br, open_br, sill_br])
    elif not flush:
        if frame and frame.get("bottom"):
            _plane_face(bm, [c_bl, c_br, rb, lb])
        else:
            _plane_face(bm, [c_bl, c_br, open_br, open_bl])
            if frame:
                _plane_face(bm, [c_bl, open_bl, lb])
                _plane_face(bm, [c_br, rb, open_br])

    # Above the opening
    top_left = top_right = None
    if rise > 0:
        top_row = outer if outer is not None else arch_row
        n = len(top_row) - 1
        m = n // 2
        for k in range(m):
            _plane_face(bm, [c_tl, top_row[k], top_row[k + 1]])
        if n % 2:
            _plane_face(bm, [c_tl, top_row[m], top_row[m + 1], c_tr])
            first_right = m + 1
        else:
            _plane_face(bm, [c_tl, top_row[m], c_tr])
            first_right = m
        for k in range(first_right, n):
            _plane_face(bm, [c_tr, top_row[k], top_row[k + 1]])
    elif frame:
        _plane_face(bm, [head_l, head_r, c_tr, c_tl])
    elif lintel:
        top_left = vert(x0 - lintel["flare"], z_top + lintel["height"])
        top_right = vert(x1 + lintel["flare"], z_top + lintel["height"])
        _plane_face(bm, [c_tl, spring_l, top_left])
        _plane_face(bm, [c_tl, top_left, top_right, c_tr])
        _plane_face(bm, [spring_r, c_tr, top_right])
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

    if frame:
        window = (open_bl, open_br, spring_l, spring_r, arch_row)
        head = (head_l, head_r, outer)
        fd = frame["depth"]
        if deep_sill:
            foot = _extrude_frame_sill_deep(bm, vert, fd, sill["depth"], sill_bl, sill_br, open_bl, open_br, head_l, head_r)
            _extrude_frame(bm, vert, fd, window, foot, head)
        else:
            if sill:
                _extrude_frame_sill(bm, vert, fd, sill_bl, sill_br, open_bl, open_br)
            foot = (vert(lb.co.x, lb.co.z, -fd), vert(rb.co.x, rb.co.z, -fd))
            ring = bool(frame.get("bottom")) and not sill
            _extrude_frame(bm, vert, fd, window, foot, head, wall=(lb, rb), feet=not sill and not ring, bottom=ring)
    else:
        if sill:
            _extrude_sill(bm, open_bl, open_br, sill_bl, sill_br, sill["depth"])
        if arch_trim:
            _archivolt_band(bm, vert, arch_row, outer, trim["depth"], feet=True)
        elif lintel:
            _extrude_lintel(bm, spring_l, spring_r, top_right, top_left, lintel["depth"])


def _build_slab(bm, vert, slab):
    """A slab: a plane strip extruded out towards -Y (built pre-mirror). It has no bottom face when
    slab["bottom"] is False, for a porch that stands on the ground, and no end walls when
    slab["ends"] is False, for a band that continues into the next module. `extend_first` and
    `extend_last` push the front edge past the end of the slab, for a mitred corner."""
    xs, zb, zt, depth = slab["xs"], slab["z_bottom"], slab["z_top"], slab["depth"]
    last = len(xs) - 1
    with_bottom = slab.get("bottom", True)
    with_ends = slab.get("ends", True)
    # Without a bottom face only the two end walls touch the bottom edge; a band has neither.
    back_b = [vert(x, zb) if (with_bottom or (with_ends and i in (0, last))) else None for i, x in enumerate(xs)]
    back_t = [vert(x, zt) for x in xs]
    def front_x(i):
        # a mitred end: the front edge runs on past the wall end by the slab depth
        return xs[i] - (slab.get("extend_first", 0.0) if i == 0 else 0.0) + (slab.get("extend_last", 0.0) if i == last else 0.0)

    front_b = [bm.verts.new((front_x(i), -depth, zb)) for i in range(len(xs))]
    front_t = [bm.verts.new((front_x(i), -depth, zt)) for i in range(len(xs))]
    inside = Vector(((xs[0] + xs[-1]) / 2, -depth / 2, (zb + zt) / 2))

    for i in range(last):
        _plane_face(bm, [front_b[i], front_b[i + 1], front_t[i + 1], front_t[i]])
        _oriented_face(bm, [back_t[i], back_t[i + 1], front_t[i + 1], front_t[i]], inside)
        if with_bottom:
            _oriented_face(bm, [back_b[i], back_b[i + 1], front_b[i + 1], front_b[i]], inside)
    if with_ends:
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
