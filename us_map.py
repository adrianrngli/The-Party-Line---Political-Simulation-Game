"""Geographic US map: projection, drawing, and click hit-testing.

Loads state-boundary polygons (input_files/us_states_geojson.json, keyed by
2-letter abbreviation) and projects lon/lat into a target screen rect. Alaska
and Hawaii are projected separately into bottom-left insets; the tiny District
of Columbia rides along in the continental projection.

Projection and hit-testing need no display, so USMap can be exercised headlessly
(only draw() touches a pygame surface).
"""

import json
import math
import pygame

# Abbreviations projected on their own, away from the continental bounding box.
INSETS = ("AK", "HI")


class USMap:
    # Small eastern states (and DC) that are hard to click get a callout box.
    CALLOUTS = ("VT", "NH", "MA", "RI", "CT", "NJ", "DE", "MD", "DC")

    def __init__(self, geojson_path, rect, callouts=None):
        with open(geojson_path) as f:
            self.raw = json.load(f)
        self.rect = rect
        self.projected = {}        # abbrev -> list of rings; each ring a list of (x, y)
        self.callout_boxes = {}    # abbrev -> pygame.Rect (clickable side box)
        self.callout_anchors = {}  # abbrev -> (x, y) on the map, for a leader line
        self.callouts = [c for c in (self.CALLOUTS if callouts is None else callouts)
                         if c in self.raw]
        self._project_all(rect)

    # ------------------------------------------------------------------ #
    # projection
    # ------------------------------------------------------------------ #

    def _rings(self, geom):
        """Flatten Polygon / MultiPolygon coordinates to a list of rings."""
        if geom["type"] == "Polygon":
            return geom["coordinates"]
        return [ring for polygon in geom["coordinates"] for ring in polygon]

    def _project_group(self, abbrs, target, wrap=False):
        """Fit the given states' polygons into `target`, preserving aspect.

        Longitude is scaled by cos(mean latitude) so the shapes don't look
        stretched. `wrap` shifts positive longitudes west by 360 degrees so
        Alaska's Aleutian islands stay contiguous with the mainland instead of
        wrapping across the antimeridian.
        """
        def to_planar(lon, lat, cos_mid):
            if wrap and lon > 0:
                lon -= 360.0
            return (lon * cos_mid, lat)

        lats = [lat for a in abbrs for ring in self._rings(self.raw[a]) for _, lat in ring]
        cos_mid = math.cos(math.radians(sum(lats) / len(lats)))

        pts = [to_planar(lon, lat, cos_mid)
               for a in abbrs for ring in self._rings(self.raw[a]) for lon, lat in ring]
        min_x = min(p[0] for p in pts)
        max_x = max(p[0] for p in pts)
        min_y = min(p[1] for p in pts)
        max_y = max(p[1] for p in pts)
        span_x = (max_x - min_x) or 1e-9
        span_y = (max_y - min_y) or 1e-9
        scale = min(target.width / span_x, target.height / span_y) * 0.92
        mid_x = (min_x + max_x) / 2.0
        mid_y = (min_y + max_y) / 2.0

        def project(lon, lat):
            px, py = to_planar(lon, lat, cos_mid)
            return (target.centerx + (px - mid_x) * scale,
                    target.centery - (py - mid_y) * scale)  # flip y for screen

        for a in abbrs:
            self.projected[a] = [[project(lon, lat) for lon, lat in ring]
                                 for ring in self._rings(self.raw[a])]

    def _project_all(self, rect):
        # Reserve a right-hand gutter for the callout boxes so they sit clearly
        # off the coast rather than on top of the small states.
        gutter = 64 if self.callouts else 0
        cont_rect = pygame.Rect(rect.left, rect.top, rect.width - gutter, rect.height)
        continental = [a for a in self.raw if a not in INSETS]
        self._project_group(continental, cont_rect)

        inset_h = int(cont_rect.height * 0.22)
        ak_rect = pygame.Rect(cont_rect.left + 8, cont_rect.bottom - inset_h - 8,
                              int(cont_rect.width * 0.20), inset_h)
        self._project_group(["AK"], ak_rect, wrap=True)
        hi_rect = pygame.Rect(ak_rect.right + 8, cont_rect.bottom - int(inset_h * 0.6) - 8,
                              int(cont_rect.width * 0.10), int(inset_h * 0.6))
        self._project_group(["HI"], hi_rect)

        self._layout_callouts(rect)

    def _layout_callouts(self, rect):
        box_w, box_h, gap = 34, 22, 6
        x = rect.right - box_w - 8
        y = rect.top + 10
        for abbr in self.callouts:
            if abbr not in self.projected:
                continue
            self.callout_boxes[abbr] = pygame.Rect(x, y, box_w, box_h)
            self.callout_anchors[abbr] = self._centroid(self.projected[abbr])
            y += box_h + gap

    @staticmethod
    def _centroid(rings):
        pts = [p for ring in rings for p in ring]
        return (sum(p[0] for p in pts) / len(pts), sum(p[1] for p in pts) / len(pts))

    # ------------------------------------------------------------------ #
    # drawing + hit-testing
    # ------------------------------------------------------------------ #

    def draw(self, surface, fill_for, outline_for, outline_width=1):
        """Fill and outline each state. fill_for(abbrev) / outline_for(abbrev)
        return an (r, g, b) color or None to skip."""
        for abbrev, rings in self.projected.items():
            fill = fill_for(abbrev)
            outline = outline_for(abbrev)
            for ring in rings:
                if len(ring) < 3:
                    continue
                if fill is not None:
                    pygame.draw.polygon(surface, fill, ring)
                if outline is not None:
                    pygame.draw.polygon(surface, outline, ring, outline_width)

    def draw_callouts(self, surface, fill_for, outline_for, font, label_color, line_color):
        """Draw the labeled side boxes for small states, each with a leader line
        back to the state, filled/outlined via the same callbacks as the map."""
        for abbrev, box in self.callout_boxes.items():
            pygame.draw.line(surface, line_color, self.callout_anchors[abbrev],
                             box.midleft, 1)
            fill = fill_for(abbrev)
            if fill is not None:
                pygame.draw.rect(surface, fill, box, border_radius=3)
            outline = outline_for(abbrev)
            if outline is not None:
                pygame.draw.rect(surface, outline, box, 1, border_radius=3)
            lbl = font.render(abbrev, True, label_color)
            surface.blit(lbl, (box.centerx - lbl.get_width() // 2,
                               box.centery - lbl.get_height() // 2))

    def hit_test(self, pos):
        """Return the abbreviation of the state under `pos`, or None. Callout
        boxes take precedence over the polygons underneath them."""
        for abbrev, box in self.callout_boxes.items():
            if box.collidepoint(pos):
                return abbrev
        for abbrev, rings in self.projected.items():
            for ring in rings:
                if self._point_in_ring(pos, ring):
                    return abbrev
        return None

    @staticmethod
    def _point_in_ring(point, ring):
        x, y = point
        inside = False
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i]
            xj, yj = ring[j]
            if ((yi > y) != (yj > y)) and \
                    (x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-12) + xi):
                inside = not inside
            j = i
        return inside
