"""A pygame frontend for Party Chair Sim: an interactive US-map dashboard.

`Game.run()` calls the GameInterface methods synchronously and expects the
input methods (select / confirm / pause / pick_state) to block until the player
responds. This frontend honors that contract: each input method runs its own
pygame event loop -- pumping events, redrawing, and ticking the clock -- until
the player acts.

The layout is a persistent dashboard: a header, a clickable US map in the
center, a side button bar (Nation / Polling / President / Parties panels), and
a bottom control strip. The map is the "home" view during pause() and pick_state(); list/card
pickers (candidate/stance/party selection, confirmations) appear in the control
strip with the map still visible above. There is no scrolling text log --
running narration surfaces through the panels plus a small transient status
line.

Requires: pip install pygame
"""

import sys
import pygame

from interfaces import GameInterface

GEOJSON_PATH = "input_files/us_states_geojson.json"


class PygameInterface(GameInterface):
    WIDTH, HEIGHT = 1024, 720
    FPS = 60

    # palette
    BG = (18, 20, 28)
    PANEL = (28, 31, 44)
    PANEL_LIGHT = (44, 48, 66)
    TEXT = (223, 226, 233)
    MUTED = (150, 155, 170)
    ACCENT = (78, 118, 224)
    ACCENT_HOVER = (108, 148, 250)
    QUIT_COLOR = (120, 66, 74)
    QUIT_HOVER = (168, 86, 96)
    WHITE = (245, 247, 250)

    # map / party colors
    DEM = (58, 90, 200)
    REP = (200, 72, 72)
    SPLIT = (126, 86, 178)
    NEUTRAL = (70, 74, 92)

    PAD = 12
    ROW_H = 34
    HEADER_H = 40
    CONTROL_H = 230
    BTN_W = 170

    def __init__(self, title="Party Chair Sim"):
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("menlo,consolas,monospace", 15)
        self.bold = pygame.font.SysFont("menlo,consolas,monospace", 15, bold=True)
        self.title_font = pygame.font.SysFont("menlo,consolas,monospace", 20, bold=True)

        # dashboard state
        self.nation = None
        self.context = {}          # header fields (year, president, party)
        self._state_index = {}     # abbrev -> State (built when nation is bound)
        self.polls = {}            # issue title -> [(label, pct), ...]
        self.result_summary = None # (title, [rows]) headline result shown in the control strip
        self._capture = None       # when a list, output is diverted to build cards
        self.active_panel = None   # None | "national" | "polling" | "president" | "platforms" | "state"
        self.panel_state = None    # abbrev when active_panel == "state"
        self._map_colors = None    # {abbrev: party letter} while showing results
        self._state_results = None # {abbrev: [lines]} of election results while showing them
        self._pick_states = None   # abbrevs selectable during pick_state (for the panel button)
        self._pick_info = None     # {abbrev: line} shown on hover during pick_state
        self._pick_locked = set()  # abbrevs shown-but-locked during pick_state (already decided)

        # geometry
        self.header_rect = pygame.Rect(self.PAD, self.PAD,
                                       self.WIDTH - 2 * self.PAD, self.HEADER_H)
        content_top = self.header_rect.bottom + self.PAD
        self.control_rect = pygame.Rect(self.PAD, self.HEIGHT - self.PAD - self.CONTROL_H,
                                        self.WIDTH - 2 * self.PAD, self.CONTROL_H)
        main_bottom = self.control_rect.top - self.PAD
        self.button_bar_rect = pygame.Rect(self.WIDTH - self.PAD - self.BTN_W, content_top,
                                            self.BTN_W, main_bottom - content_top)
        self.map_rect = pygame.Rect(self.PAD, content_top,
                                    self.button_bar_rect.left - self.PAD - self.PAD,
                                    main_bottom - content_top)

        from us_map import USMap
        self.map = USMap(GEOJSON_PATH, self.map_rect)

    # ------------------------------------------------------------------ #
    # GameInterface: output
    # ------------------------------------------------------------------ #

    def announce(self, text=""):
        # announce() is the game's generic narration sink. On this dashboard the
        # standing facts it carries (compositions, approval, the annual report)
        # already live in the panels and modals, so echoing them into the control
        # strip only reproduced an unreadable scrolling console. The strip is now
        # reserved for the formatted result summary set via show_result(); plain
        # narration is dropped here (the console frontend still prints it). The one
        # exception is card/reference capture, which builds info-card text.
        if self._capture is not None:
            self._capture.append(str(text))

    def show_person(self, person, issues=[]):
        if self._capture is None:
            return  # full profiles surface via detail cards / panels, not the strip
        self.announce(str(person))
        self.announce("  Age: " + str(person.age)
                      + "   Experience: " + str(person.years_of_experience) + " yrs")
        self.announce("  Fame: " + person.fame_classification()
                      + "   Popularity: " + person.popularity_classification())
        self.announce("  Charisma: " + person.charisma_classification()
                      + "   Corruptness: " + person.corruptness_classification())
        for issue in issues:
            self.announce("  " + str(issue) + ": " + str(person.get_stance(issue)))
        self.announce("")

    def show_state(self, state, issues=[]):
        if self._capture is None:
            return  # state profiles surface via the state panel / info card, not the strip
        self.announce(state.name + " (" + str(state.rep_number) + " reps)")
        self.announce("  Wealth: " + state.wealth_classification()
                      + "   Density: " + state.density_classification())
        for issue in issues:
            self.announce("  " + str(issue) + ": " + str(state.get_stance(issue)))
        self.announce("")

    def show_poll(self, title, results):
        if self._capture is not None:  # building a detail card: keep it textual
            GameInterface.show_poll(self, title, results)
            return
        self.polls[str(title)] = [(str(label), float(pct)) for label, pct in results]

    def show_result(self, title, rows):
        # Store the latest headline result; it is drawn as a titled, labeled block
        # in the control strip and persists until the next result replaces it.
        self.result_summary = (str(title), [str(row) for row in rows])

    def set_context(self, **fields):
        nation = fields.pop("nation", None)
        if nation is not None:
            self.nation = nation
            self._state_index = {s.abbreviation: s for s in nation.states}
            if getattr(nation, "dc", None) is not None:
                self._state_index[nation.dc.abbreviation] = nation.dc  # DC: presidential only
        self.context.update(fields)

    def set_map_colors(self, party_by_state=None):
        self._map_colors = party_by_state

    def set_state_results(self, results_by_state=None):
        self._state_results = results_by_state

    # ------------------------------------------------------------------ #
    # GameInterface: input (each runs a blocking event loop)
    # ------------------------------------------------------------------ #

    def pause(self, message=""):
        """Interactive dashboard: inspect states/panels until Continue."""
        self.active_panel = None
        self._pick_states = None
        prompt = message.strip() or "Click a state to inspect it, or open a panel."
        while True:
            mouse = pygame.mouse.get_pos()
            hover = self._map_hover(mouse)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._shutdown()
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._action_rect().collidepoint(event.pos):
                        return
                    if self._handle_click(event.pos):
                        continue
                    self._open_state_panel(event.pos)
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    if self.active_panel is None:
                        return
                    self.active_panel = None
            self._render_dashboard(hover_state=hover, mouse=mouse)
            self._draw_action_and_prompt("Continue", prompt, mouse)
            pygame.display.flip()
            self.clock.tick(self.FPS)

    def pick_state(self, prompt, state_abbrevs, allow_quit=True, info=None,
                   locked=None):
        """Let the player inspect ANY state's info, and choose one of
        `state_abbrevs` (via a button in that state's info panel). `info` maps
        abbreviations to a detail line shown on hover. `locked` is a set of
        abbreviations the player may still inspect but not choose (their race
        is already decided) -- shown marked on the map and with a locked notice
        instead of a choose button. Returns the chosen abbreviation, or None on
        quit."""
        highlight = set(state_abbrevs)
        self._pick_locked = set(locked or ())
        self.active_panel = None
        self._pick_states = highlight
        self._pick_info = info or {}
        try:
            while True:
                mouse = pygame.mouse.get_pos()
                hover = self._map_hover(mouse)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        self._shutdown()
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if self.active_panel == "state" and self.panel_state in highlight \
                                and self.panel_state not in self._pick_locked \
                                and self._state_action_rect().collidepoint(event.pos):
                            self.active_panel = None
                            return self.panel_state
                        if allow_quit and self._action_rect().collidepoint(event.pos):
                            return None
                        if self._handle_click(event.pos):
                            continue
                        self._open_state_panel(event.pos)
                    elif event.type == pygame.KEYDOWN:
                        if allow_quit and event.key in (pygame.K_q, pygame.K_ESCAPE):
                            return None
                self._render_dashboard(highlight=highlight, hover_state=hover, mouse=mouse)
                self._draw_action_and_prompt("Quit" if allow_quit else None, prompt, mouse)
                if hover in self._pick_info:
                    note = self._pick_info[hover]
                    if hover in self._pick_locked:
                        note += "   (candidate locked in)"
                    self._draw_hover_info(hover, note)
                pygame.display.flip()
                self.clock.tick(self.FPS)
        finally:
            self._pick_states = None
            self._pick_info = None
            self._pick_locked = set()

    def show_vote(self, title, summary, details=None):
        """Blocking vote modal: the final tally shows up front; individual
        member votes stay hidden behind a toggle. Continue/Enter dismisses."""
        self._modal(title, summary, details, "Review the vote, then continue.")

    def show_decision(self, title, summary):
        """Blocking screen for the president's sign/veto decision on a bill."""
        self._modal(title, summary, None, "Review the decision, then continue.")

    def event(self, title, lines=()):
        """Blocking popup the player must acknowledge (news events + annual report)."""
        self._modal(str(title), [str(line) for line in lines], None,
                    "Press Continue to acknowledge.")

    def _modal(self, title, summary, details, prompt):
        """Shared blocking overlay: a titled panel with summary lines and an
        optional scrollable, toggle-gated details list. Continue/Enter returns."""
        self.active_panel = None
        self._pick_states = None
        details = list(details or [])
        showing = False
        scroll = 0
        while True:
            mouse = pygame.mouse.get_pos()
            visible_rows = self._vote_visible_rows()
            max_scroll = max(0, len(details) - visible_rows)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._shutdown()
                elif event.type == pygame.MOUSEWHEEL:
                    if showing:
                        scroll = self._clamp(scroll - event.y, 0, max_scroll)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self._action_rect().collidepoint(event.pos):
                        return
                    if details and self._vote_toggle_rect().collidepoint(event.pos):
                        showing = not showing
                        scroll = 0
                elif event.type == pygame.KEYDOWN and event.key in (pygame.K_RETURN, pygame.K_SPACE):
                    return
            # A modal is self-contained: the vote/decision/event panel and its
            # own prompt carry everything relevant, so suppress the result summary
            # -- otherwise a headline result from earlier in the turn lingers at
            # the top of the control strip as stray text behind the modal.
            self._render_dashboard(mouse=mouse, show_summary=False)
            self._render_vote_panel(title, summary, details, showing, scroll, mouse)
            self._draw_action_and_prompt("Continue", prompt, mouse)
            pygame.display.flip()
            self.clock.tick(self.FPS)

    def select(self, prompt, options, labeler=str, *, details=None, allow_quit=False,
               reference=None, focus_state=None):
        options = list(options)
        cards = None
        if details is not None:
            cards = []
            for option in options:
                self._capture = []
                details(self, option)
                cards.append([line for line in self._capture if line != ""] or [""])
            self._capture = None
        ref_lines = None
        if reference is not None:
            self._capture = []
            reference(self)
            ref_lines = [line for line in self._capture if line != ""] or None
            self._capture = None
        entries = [(labeler(option), option) for option in options]
        return self._choose(prompt, entries, allow_quit=allow_quit, cards=cards,
                            ref_lines=ref_lines, focus_state=focus_state)

    def confirm(self, prompt):
        entries = [("Yea  (Y)", True), ("Nay  (N)", False)]
        keymap = {pygame.K_y: True, pygame.K_n: False}
        return self._choose(prompt, entries, allow_quit=False, keymap=keymap)

    # ------------------------------------------------------------------ #
    # list/card picker (select / confirm) -- lives in the control strip
    # ------------------------------------------------------------------ #

    def _choose(self, prompt, entries, *, allow_quit=False, keymap=None, cards=None,
                ref_lines=None, focus_state=None):
        keymap = keymap or {}
        list_scroll = 0
        focus = 0
        # ref mode: state whose compact card is shown alongside the opponent
        sel_state = focus_state if (focus_state in self._state_index) else None
        ref_collapsed = False  # ref mode: opponent card shrunk to its heading to reveal the map
        c = self.control_rect
        prompt_lines = self._wrap(prompt, c.width - 2 * self.PAD, self.bold)
        list_top = c.y + self.PAD + len(prompt_lines) * self.bold.get_linesize() + 4
        list_bottom = c.bottom - self.PAD - 18

        if cards is not None:
            list_w = int(c.width * 0.40)
            card_rect = pygame.Rect(c.x + self.PAD + list_w + self.PAD, list_top,
                                    c.right - self.PAD - (c.x + self.PAD + list_w + self.PAD),
                                    list_bottom - list_top)
        else:
            list_w = c.width - 2 * self.PAD
            card_rect = None
        visible_rows = max(1, (list_bottom - list_top) // self.ROW_H)

        while True:
            mouse = pygame.mouse.get_pos()
            row_rects = self._row_rects(c.x + self.PAD, list_w, list_top,
                                        len(entries), list_scroll, visible_rows)
            for idx, rect in row_rects:
                if rect.collidepoint(mouse):
                    focus = idx

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._shutdown()
                elif event.type == pygame.MOUSEWHEEL:
                    list_scroll = self._clamp(list_scroll - event.y, 0,
                                              max(0, len(entries) - visible_rows))
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for idx, rect in row_rects:
                        if rect.collidepoint(event.pos):
                            return entries[idx][1]
                    if allow_quit and self._action_rect().collidepoint(event.pos):
                        return None
                    if self._handle_click(event.pos):
                        continue
                    if ref_lines:
                        # ref mode: the opponent card + an optional state card float
                        # over the map. Each card has a corner button -- collapse the
                        # opponent card (or dismiss the state card) to reveal and click
                        # the map beneath (e.g. a state hidden under the card).
                        if self.active_panel is None:
                            _, ref_rect, _, state_rect = self._ref_layout(
                                ref_lines, ref_collapsed, sel_state)
                            if self._card_toggle_rect(ref_rect).collidepoint(event.pos):
                                ref_collapsed = not ref_collapsed
                            elif ref_rect.collidepoint(event.pos):
                                pass  # opponent card body: no-op
                            elif state_rect is not None \
                                    and self._card_toggle_rect(state_rect).collidepoint(event.pos):
                                sel_state = None  # dismiss the state card
                            elif state_rect is not None and state_rect.collidepoint(event.pos):
                                pass  # state card body: no-op
                            else:
                                hit = self._map_hover(event.pos)
                                if hit is not None and hit in self._state_index:
                                    sel_state = hit
                        continue
                    self._open_state_panel(event.pos)  # inspect a state while choosing
                elif event.type == pygame.KEYDOWN:
                    if event.key in keymap:
                        return entries[keymap[event.key]][1]
                    if allow_quit and event.key == pygame.K_q:
                        return None
                    if event.key in (pygame.K_DOWN, pygame.K_UP):
                        focus = self._clamp(focus + (1 if event.key == pygame.K_DOWN else -1),
                                            0, len(entries) - 1)
                        list_scroll = self._keep_visible(focus, list_scroll, visible_rows, len(entries))
                    elif cards is not None and event.key == pygame.K_RETURN:
                        return entries[focus][1]
                    elif pygame.K_1 <= event.key <= pygame.K_9:
                        pick = event.key - pygame.K_1
                        if pick < len(entries):
                            return entries[pick][1]

            self._render_dashboard(mouse=mouse)
            if ref_lines and self.active_panel is None:
                ref_disp, ref_rect, state_disp, state_rect = self._ref_layout(
                    ref_lines, ref_collapsed, sel_state)
                self._render_info_card(ref_rect, ref_disp)
                self._render_card_toggle(ref_rect, mouse, "+" if ref_collapsed else "-")
                if state_rect is not None:
                    self._render_info_card(state_rect, state_disp)
                    self._render_card_toggle(state_rect, mouse, "x")
            self._render_picker(prompt_lines, row_rects, entries, mouse, allow_quit,
                                card_rect, cards[focus] if cards else None, focus)
            pygame.display.flip()
            self.clock.tick(self.FPS)

    def _render_picker(self, prompt_lines, row_rects, entries, mouse, allow_quit,
                       card_rect, card_lines, focus):
        c = self.control_rect
        pygame.draw.rect(self.screen, self.PANEL, c, border_radius=8)  # cover status
        y = c.y + self.PAD
        for line in prompt_lines:
            self.screen.blit(self.bold.render(line, True, self.TEXT), (c.x + self.PAD, y))
            y += self.bold.get_linesize()
        if card_rect is not None and card_lines is not None:
            self._render_card(card_rect, card_lines)
        for idx, rect in row_rects:
            highlighted = rect.collidepoint(mouse) or idx == focus
            self._button(rect, str(idx + 1) + ".  " + str(entries[idx][0]), highlighted)
        if allow_quit:
            self._button(self._action_rect(), "Quit  (Q)",
                         self._action_rect().collidepoint(mouse), quit_style=True)
        hint = "Click a row / 1-9" + ("  /  ↑↓ + Enter" if card_rect else "")
        self.screen.blit(self.font.render(hint, True, self.MUTED),
                         (c.x + self.PAD, c.bottom - 16))

    # ------------------------------------------------------------------ #
    # dashboard rendering
    # ------------------------------------------------------------------ #

    def _render_dashboard(self, *, highlight=None, hover_state=None, mouse=(0, 0),
                          show_summary=True):
        self.screen.fill(self.BG)
        self._render_header()
        pygame.draw.rect(self.screen, self.PANEL, self.map_rect, border_radius=8)
        eff_hover = hover_state if (highlight is None or hover_state in highlight) else None
        self._render_map(highlight, eff_hover)
        self._render_buttons(mouse)
        pygame.draw.rect(self.screen, self.PANEL, self.control_rect, border_radius=8)
        if show_summary:
            self._render_result_panel()
        if self.active_panel:
            self._render_panel()

    def _render_header(self):
        pygame.draw.rect(self.screen, self.PANEL_LIGHT, self.header_rect, border_radius=8)
        segments = []
        if self.context.get("year") is not None:
            segments.append((str(self.context["year"]), self.ACCENT_HOVER))
        pres = self.context.get("president")
        if pres is not None:
            segments.append((str(pres), self.TEXT))  # already "President <name> (<party>-<st>)"
        party = self.context.get("party")
        if party is not None:
            label = "You: " + str(party)
            if getattr(party, "letter", None):
                label += " (" + party.letter + ")"
            segments.append((label, self.TEXT))
        x = self.header_rect.x + self.PAD
        y = self.header_rect.y + (self.header_rect.height - self.bold.get_linesize()) // 2
        for i, (text, color) in enumerate(segments):
            if i > 0:
                sep = self.font.render("|", True, self.MUTED)
                self.screen.blit(sep, (x, y))
                x += sep.get_width() + 16
            surf = self.bold.render(text, True, color)
            self.screen.blit(surf, (x, y))
            x += surf.get_width() + 16

    def _render_map(self, highlight, hover):
        def fill_for(ab):
            base = self._result_color(ab)
            if highlight is not None and ab not in highlight:
                return self._scale(base, 0.55)
            if ab == hover:
                return self._scale(base, 1.4)
            return base

        def outline_for(ab):
            return self.BG

        def box_outline(ab):
            if highlight is not None and ab in highlight and ab not in self._pick_locked:
                return self.ACCENT_HOVER
            return self.MUTED

        self.screen.set_clip(self.map_rect)
        self.map.draw(self.screen, fill_for, outline_for, 1)
        if highlight:
            # actionable races glow with the accent; locked (already-decided)
            # races get a muted outline so they read as done, not clickable.
            self.map.draw(
                self.screen,
                lambda ab: None,
                lambda ab: (self.MUTED if ab in self._pick_locked else self.ACCENT_HOVER)
                if ab in highlight else None,
                2)
        self.map.draw_callouts(self.screen, fill_for, box_outline, self.font,
                               self.WHITE, self.MUTED)
        self.screen.set_clip(None)

    def _render_buttons(self, mouse):
        bar = self.button_bar_rect
        pygame.draw.rect(self.screen, self.PANEL, bar, border_radius=8)
        for label, key, rect in self._side_button_rects():
            active = self.active_panel == key
            hover = rect.collidepoint(mouse)
            color = self.ACCENT if (active or hover) else self.PANEL_LIGHT
            pygame.draw.rect(self.screen, color, rect, border_radius=6)
            surf = self.bold.render(label, True, self.WHITE)
            self.screen.blit(surf, (rect.x + 12, rect.centery - surf.get_height() // 2))
        # legend -- only meaningful while an election result coloring is active
        if self._map_colors:
            y = self._side_button_rects()[-1][2].bottom + 18
            self.screen.blit(self.font.render("Results", True, self.MUTED), (bar.x + 12, y))
            y += 22
            for label, color in [("Democrat", self.DEM), ("Republican", self.REP)]:
                sw = pygame.Rect(bar.x + 12, y, 16, 16)
                pygame.draw.rect(self.screen, color, sw, border_radius=3)
                self.screen.blit(self.font.render(label, True, self.MUTED), (sw.right + 8, y))
                y += 24

    def _render_result_panel(self):
        """Draw the latest headline result (from show_result) as a titled, labeled
        block in the control strip: a bold title over wrapped, fully-legible rows.
        Nothing is truncated -- long lines wrap -- so a title like "Electoral
        votes" can never be cut off. Skipped during a pick, where the hover strip
        owns this area, and when there is no result yet."""
        if self._pick_info:  # during a pick, the hover strip owns this area
            return
        if not self.result_summary:
            return
        title, rows = self.result_summary
        c = self.control_rect
        inner_w = c.width - 2 * self.PAD
        x = c.left + self.PAD
        y = c.top + self.PAD
        for line in self._wrap(title, inner_w, self.title_font):
            self.screen.blit(self.title_font.render(line, True, self.WHITE), (x, y))
            y += self.title_font.get_linesize()
        y += 6
        # leave room for the prompt/Continue button that sits at the bottom
        limit = c.bottom - self.PAD - self.bold.get_linesize()
        for row in rows:
            for line in self._wrap(str(row), inner_w, self.font):
                if y + self.font.get_linesize() > limit:
                    return
                self.screen.blit(self.font.render(line, True, self.TEXT), (x, y))
                y += self.font.get_linesize()

    def _draw_action_and_prompt(self, action_label, prompt, mouse):
        c = self.control_rect
        if prompt:
            lines = self._wrap(prompt, c.width - 190, self.bold)
            y = c.bottom - 14 - len(lines) * self.bold.get_linesize()
            for line in lines:
                self.screen.blit(self.bold.render(line, True, self.TEXT), (c.left + 12, y))
                y += self.bold.get_linesize()
        if action_label:
            r = self._action_rect()
            hover = r.collidepoint(mouse)
            pygame.draw.rect(self.screen, self.ACCENT_HOVER if hover else self.ACCENT, r,
                             border_radius=6)
            surf = self.bold.render(action_label, True, self.WHITE)
            self.screen.blit(surf, (r.centerx - surf.get_width() // 2,
                                    r.centery - surf.get_height() // 2))

    def _draw_hover_info(self, abbrev, text):
        """A prominent strip at the top of the control area showing the hovered
        state's detail (e.g. its senate race polling) -- visible without clicking."""
        c = self.control_rect
        strip = pygame.Rect(c.left + 4, c.top + 4, c.width - 8, 28)
        pygame.draw.rect(self.screen, self.PANEL_LIGHT, strip, border_radius=6)
        label = abbrev + " senate race:  " + str(text)
        surf = self.bold.render(self._truncate(label, strip.width - 16, self.bold), True, self.WHITE)
        self.screen.blit(surf, (strip.left + 8, strip.centery - surf.get_height() // 2))

    def _render_panel(self):
        rect = self._panel_rect()
        pygame.draw.rect(self.screen, self.PANEL_LIGHT, rect, border_radius=10)
        pygame.draw.rect(self.screen, self.ACCENT, rect, 2, border_radius=10)
        cr = self._panel_close_rect()
        pygame.draw.rect(self.screen, self.QUIT_COLOR, cr, border_radius=6)
        x = self.bold.render("X", True, self.WHITE)
        self.screen.blit(x, (cr.centerx - x.get_width() // 2, cr.centery - x.get_height() // 2))

        inner = rect.inflate(-2 * self.PAD, -2 * self.PAD)
        self.screen.set_clip(inner)
        line_h = self.font.get_linesize()
        y = inner.top
        for i, item in enumerate(self._panel_items()):
            if isinstance(item, tuple) and item and item[0] == "bar":
                self._render_bar(inner.left, y, inner.width, item[1], item[2])
                y += line_h
            else:
                font = self.title_font if i == 0 else self.font
                color = self.WHITE if i == 0 else self.TEXT
                for piece in self._wrap(str(item), inner.width, font):
                    self.screen.blit(font.render(piece, True, color), (inner.left, y))
                    y += font.get_linesize()
        self.screen.set_clip(None)

        # during a senate pick, a race state's panel offers a nominate button --
        # unless its candidate is already chosen, in which case it shows a locked
        # notice the player can't act on.
        if self._pick_states and self.active_panel == "state" \
                and self.panel_state in self._pick_states:
            r = self._state_action_rect()
            if self.panel_state in self._pick_locked:
                pygame.draw.rect(self.screen, self.PANEL, r, border_radius=6)
                pygame.draw.rect(self.screen, self.MUTED, r, 1, border_radius=6)
                surf = self.bold.render("Candidate locked in", True, self.MUTED)
            else:
                pygame.draw.rect(self.screen, self.ACCENT, r, border_radius=6)
                surf = self.bold.render("Choose candidate", True, self.WHITE)
            self.screen.blit(surf, (r.centerx - surf.get_width() // 2,
                                    r.centery - surf.get_height() // 2))

    REF_CARD_W = 380

    def _card_rect(self, lines, *, right=False):
        """A compact card in the map area, sized to its content and anchored to
        the top-left (or top-right) so the national map stays visible around it.
        Two cards (opponent + state) fit side by side with the map behind."""
        m = self.map_rect
        width = min(self.REF_CARD_W, m.width - 2 * self.PAD)
        inner_w = width - 2 * self.PAD
        height = self.PAD
        for i, line in enumerate(lines):
            font = self.title_font if i == 0 else self.font
            height += len(self._wrap(str(line), inner_w, font)) * font.get_linesize()
            if i == 0:
                height += 4
        height = min(height + self.PAD, m.height - 2 * self.PAD)
        x = (m.right - self.PAD - width) if right else (m.left + self.PAD)
        return pygame.Rect(x, m.top + self.PAD, width, height)

    def _reference_rect(self, ref_lines):
        return self._card_rect(ref_lines)

    def _render_info_card(self, rect, lines):
        """Draw a titled, accent-bordered card. The first line is the heading."""
        pygame.draw.rect(self.screen, self.PANEL_LIGHT, rect, border_radius=10)
        pygame.draw.rect(self.screen, self.ACCENT, rect, 2, border_radius=10)
        inner = rect.inflate(-2 * self.PAD, -2 * self.PAD)
        self.screen.set_clip(inner)
        y = inner.top
        for i, line in enumerate(lines):
            font = self.title_font if i == 0 else self.font
            color = self.WHITE if i == 0 else self.TEXT
            for piece in self._wrap(str(line), inner.width, font):
                self.screen.blit(font.render(piece, True, color), (inner.left, y))
                y += font.get_linesize()
            if i == 0:
                y += 4
        self.screen.set_clip(None)

    def _render_reference(self, ref_lines):
        """The opponent's candidate card, pinned top-left so the map stays visible."""
        self._render_info_card(self._card_rect(ref_lines), ref_lines)

    def _card_toggle_rect(self, rect):
        """Small button in a card's top-right corner (collapse / dismiss)."""
        return pygame.Rect(rect.right - self.PAD - 20, rect.top + self.PAD - 2, 20, 20)

    def _render_card_toggle(self, rect, mouse, glyph):
        r = self._card_toggle_rect(rect)
        hover = r.collidepoint(mouse)
        pygame.draw.rect(self.screen, self.ACCENT_HOVER if hover else self.QUIT_COLOR,
                         r, border_radius=4)
        surf = self.bold.render(glyph, True, self.WHITE)
        self.screen.blit(surf, (r.centerx - surf.get_width() // 2,
                                r.centery - surf.get_height() // 2))

    def _ref_layout(self, ref_lines, ref_collapsed, sel_state):
        """Current display lines and rects for the opponent card (full or
        collapsed to its heading) and the optional state card, so click handling
        and rendering agree frame to frame."""
        ref_disp = ref_lines[:1] if ref_collapsed else ref_lines
        ref_rect = self._card_rect(ref_disp)
        state_disp = self._state_panel_items(sel_state) if sel_state is not None else None
        state_rect = self._card_rect(state_disp, right=True) if state_disp is not None else None
        return ref_disp, ref_rect, state_disp, state_rect

    def _render_vote_panel(self, title, summary, details, showing, scroll, mouse):
        """Overlay in the map area: title + result summary, with the individual
        votes gated behind a toggle button and scrollable when revealed."""
        rect = self._panel_rect()
        pygame.draw.rect(self.screen, self.PANEL_LIGHT, rect, border_radius=10)
        pygame.draw.rect(self.screen, self.ACCENT, rect, 2, border_radius=10)
        inner = rect.inflate(-2 * self.PAD, -2 * self.PAD)
        self.screen.set_clip(inner)
        y = inner.top
        self.screen.blit(self.title_font.render(
            self._truncate(title, inner.width, self.title_font), True, self.WHITE),
            (inner.left, y))
        y += self.title_font.get_linesize() + 6
        for line in summary:
            for piece in self._wrap(str(line), inner.width, self.bold):
                self.screen.blit(self.bold.render(piece, True, self.TEXT), (inner.left, y))
                y += self.bold.get_linesize()
        self.screen.set_clip(None)

        if not details:
            return
        toggle = self._vote_toggle_rect()
        hover = toggle.collidepoint(mouse)
        pygame.draw.rect(self.screen, self.ACCENT_HOVER if hover else self.ACCENT,
                         toggle, border_radius=6)
        label = ("Hide" if showing else "Show") + " individual votes"
        surf = self.bold.render(label, True, self.WHITE)
        self.screen.blit(surf, (toggle.centerx - surf.get_width() // 2,
                                toggle.centery - surf.get_height() // 2))
        if not showing:
            return
        visible_rows = self._vote_visible_rows()
        list_top = toggle.bottom + 8
        list_rect = pygame.Rect(inner.left, list_top, inner.width, rect.bottom - self.PAD - list_top)
        self.screen.set_clip(list_rect)
        line_h = self.font.get_linesize()
        yy = list_rect.top
        for line in details[scroll:scroll + visible_rows]:
            self.screen.blit(self.font.render(line, True, self.TEXT), (list_rect.left, yy))
            yy += line_h
        self.screen.set_clip(None)
        if len(details) > visible_rows:
            hint = "scroll for more (" + str(scroll + 1) + "-" \
                + str(min(len(details), scroll + visible_rows)) \
                + " of " + str(len(details)) + ")"
            self.screen.blit(self.font.render(hint, True, self.MUTED),
                             (list_rect.left, rect.bottom - self.PAD - line_h + 2))

    def _vote_toggle_rect(self):
        p = self._panel_rect()
        return pygame.Rect(p.left + self.PAD, p.top + self.PAD + 190, 240, 32)

    def _vote_visible_rows(self):
        p = self._panel_rect()
        list_top = self._vote_toggle_rect().bottom + 8
        # leave a line at the bottom for the scroll hint
        return max(1, (p.bottom - self.PAD - list_top) // self.font.get_linesize() - 1)

    def _panel_items(self):
        """Build the current panel's content from live nation data."""
        n = self.nation
        if n is None:
            return ["No data yet."]
        if self.active_panel == "national":
            items = ["National Overview", ""]
            items.append("Year: " + str(n.year))
            items.append(str(n.president))
            items.append("Approval: "
                         + str(round(n.president.stats["popularity"].value, 1)) + "%")
            items.append("Senate: " + n.get_senate_totals())
            items.append("House:  " + n.get_house_totals())
            items.append("")
            for party in n.parties:
                items.append(str(party) + " approval: "
                             + str(round(party.stats["popularity"].value, 1)) + "%")
            items.append("")
            items.append("Economy grew "
                         + str(round(n.econ_record.get_growth(n.year - 1), 1)) + "% last year.")
            return items
        if self.active_panel == "polling":
            items = ["National Polling", ""]
            for issue in n.issues:
                results = self.polls.get(str(issue))
                if results:
                    items.append(str(issue))
                    for label, pct in results:
                        items.append(("bar", label, pct))
                    items.append("")
            if len(items) == 2:
                items.append("No polling yet this year.")
            return items
        if self.active_panel == "president":
            p = n.president
            items = [str(p), ""]
            items.append("Approval: "
                         + str(round(p.stats["popularity"].value, 1)) + "%")
            items.append("Years in office: " + str(p.years_in_office))
            items.append("Age: " + str(p.age)
                         + "    Experience: " + str(p.years_of_experience) + " yrs")
            items.append("Fame: " + p.fame_classification())
            items.append("Charisma: " + p.charisma_classification())
            items.append("Corruptness: " + p.corruptness_classification())
            items.append("")
            items.append("Positions:")
            for issue in n.issues:
                items.append("  " + str(issue) + ": " + str(p.get_stance(issue)))
            return items
        if self.active_panel == "platforms":
            return self._platform_panel_items()
        if self.active_panel == "state":
            return self._state_panel_items(self.panel_state)
        return [""]

    def _platform_panel_items(self):
        """Every party's current platform: its adopted stance on each live issue.
        Platforms are re-chosen only every four years, so an issue that has come
        along since is shown as having no position yet rather than being silently
        dropped."""
        n = self.nation
        items = ["Party Platforms", ""]
        player_party = self.context.get("party")
        for party in n.parties:
            heading = str(party)
            if getattr(party, "letter", None):
                heading += " (" + party.letter + ")"
            if party is player_party:
                heading += "  -- yours"
            items.append(heading)
            platform = party.platform or {}
            for issue in n.issues:
                stance = platform.get(issue)
                items.append("  " + str(issue) + ": "
                             + (str(stance) if stance is not None else "(no position yet)"))
            items.append("")
        return items

    def _state_panel_items(self, abbrev):
        """Build a state's info card content from live nation data."""
        n = self.nation
        if n is None:
            return ["No data yet."]
        st = self._state_index.get(abbrev)
        if st is None:
            return ["Unknown state."]
        items = [st.name + " (" + str(st.rep_number) + " reps)", ""]
        race_poll = (self._pick_info or {}).get(abbrev)
        if race_poll:
            items.append("Senate race polling:")
            items.append("  " + str(race_poll))
            if abbrev in self._pick_locked:
                items.append("  Your candidate is locked in and can't be changed.")
            items.append("")
        results = (self._state_results or {}).get(abbrev)
        if results:
            items.append("Election results:")
            for line in results:
                items.append("  " + line)
            items.append("")
        items.append("Wealth: " + st.wealth_classification()
                     + "    Density: " + st.density_classification())
        items.append("")
        items.append("Senators:")
        if any(sen is not None for sen in st.senators):
            for sen in st.senators:
                items.append("  " + (str(sen) if sen is not None else "(vacant)"))
        else:
            items.append("  (none)")
        items.append("")
        items.append("Positions:")
        for issue in n.issues:
            items.append("  " + str(issue) + ": " + str(st.get_stance(issue)))
        return items

    # ------------------------------------------------------------------ #
    # shared event handling + geometry
    # ------------------------------------------------------------------ #

    def _handle_click(self, pos):
        """Side-button toggles and panel dismissal shared by every screen.
        Returns True if the click was consumed. A click inside an open panel's
        body is consumed (it stays open); the X or a click outside closes it."""
        for label, key, rect in self._side_button_rects():
            if rect.collidepoint(pos):
                self.active_panel = None if self.active_panel == key else key
                return True
        if self.active_panel is not None:
            if self._panel_close_rect().collidepoint(pos) or not self._panel_rect().collidepoint(pos):
                self.active_panel = None
                return True
            return True  # click within the panel body: keep it open
        return False

    def _open_state_panel(self, pos):
        """Open the info panel for the state clicked on the map, if any."""
        hit = self._map_hover(pos)
        if hit is not None and hit in self._state_index:
            self.active_panel, self.panel_state = "state", hit
            return True
        return False

    def _map_hover(self, pos):
        if self.active_panel is not None or not self.map_rect.collidepoint(pos):
            return None
        return self.map.hit_test(pos)

    def _side_button_rects(self):
        bar = self.button_bar_rect
        w = bar.width - 16
        national = pygame.Rect(bar.x + 8, bar.y + 8, w, 40)
        polling = pygame.Rect(bar.x + 8, national.bottom + 8, w, 40)
        president = pygame.Rect(bar.x + 8, polling.bottom + 8, w, 40)
        platforms = pygame.Rect(bar.x + 8, president.bottom + 8, w, 40)
        return [("Nation", "national", national), ("Polling", "polling", polling),
                ("President", "president", president),
                ("Parties", "platforms", platforms)]

    def _action_rect(self):
        c = self.control_rect
        return pygame.Rect(c.right - 160, c.bottom - 52, 148, 40)

    def _panel_rect(self):
        return pygame.Rect(self.map_rect.left, self.map_rect.top,
                           self.map_rect.width, self.map_rect.height)

    def _panel_close_rect(self):
        p = self._panel_rect()
        return pygame.Rect(p.right - 36, p.top + 8, 28, 28)

    def _state_action_rect(self):
        p = self._panel_rect()
        return pygame.Rect(p.left + self.PAD, p.bottom - self.PAD - 38, 220, 34)

    def _result_color(self, abbrev):
        """Neutral unless an election result coloring is active."""
        if self._map_colors:
            letter = self._map_colors.get(abbrev)
            if letter == "D":
                return self.DEM
            if letter == "R":
                return self.REP
        return self.NEUTRAL

    @staticmethod
    def _scale(color, factor):
        return tuple(max(0, min(255, int(c * factor))) for c in color)

    # ------------------------------------------------------------------ #
    # small render + geometry helpers
    # ------------------------------------------------------------------ #

    def _render_card(self, rect, lines):
        pygame.draw.rect(self.screen, self.PANEL_LIGHT, rect, border_radius=8)
        inner = rect.inflate(-2 * self.PAD, -2 * self.PAD)
        self.screen.set_clip(inner)
        line_h = self.font.get_linesize()
        y = inner.top
        for i, line in enumerate(lines):
            font = self.bold if i == 0 else self.font
            color = self.WHITE if i == 0 else self.TEXT
            for piece in self._wrap(line, inner.width, font):
                self.screen.blit(font.render(piece, True, color), (inner.left, y))
                y += line_h
        self.screen.set_clip(None)

    def _render_bar(self, x, y, width, label, pct):
        line_h = self.font.get_linesize()
        label_w, pct_w = 150, 52
        bar_x = x + label_w
        bar_w = max(20, width - label_w - pct_w)
        lbl = self._truncate("  " + str(label), label_w - 8, self.font)
        self.screen.blit(self.font.render(lbl, True, self.TEXT), (x, y))
        track = pygame.Rect(bar_x, y + 3, bar_w, line_h - 6)
        pygame.draw.rect(self.screen, self.PANEL, track, border_radius=4)
        frac = self._clamp(pct / 100.0, 0.0, 1.0)
        if frac > 0:
            fill = pygame.Rect(bar_x, y + 3, int(bar_w * frac), line_h - 6)
            pygame.draw.rect(self.screen, self.ACCENT, fill, border_radius=4)
        self.screen.blit(self.font.render(str(round(pct, 1)) + "%", True, self.MUTED),
                         (bar_x + bar_w + 8, y))

    def _button(self, rect, label, hover, *, quit_style=False):
        if quit_style:
            color = self.QUIT_HOVER if hover else self.QUIT_COLOR
        else:
            color = self.ACCENT_HOVER if hover else self.ACCENT
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        label = self._truncate(label, rect.width - 20, self.font)
        txt = self.font.render(label, True, self.WHITE)
        self.screen.blit(txt, (rect.x + 10, rect.y + (rect.height - txt.get_height()) // 2))

    def _row_rects(self, x, width, top, count, scroll, visible_rows):
        rects = []
        for i in range(scroll, min(count, scroll + visible_rows)):
            y = top + (i - scroll) * self.ROW_H
            rects.append((i, pygame.Rect(x, y, width, self.ROW_H - 6)))
        return rects

    @staticmethod
    def _keep_visible(focus, scroll, visible_rows, count):
        if focus < scroll:
            return focus
        if focus >= scroll + visible_rows:
            return focus - visible_rows + 1
        return scroll

    @staticmethod
    def _clamp(value, low, high):
        return max(low, min(high, value))

    def _wrap(self, text, max_px, font):
        if text == "":
            return [""]
        lines, current = [], ""
        for word in text.split(" "):
            trial = word if current == "" else current + " " + word
            if font.size(trial)[0] <= max_px:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word
        lines.append(current)
        return lines

    def _truncate(self, text, max_px, font):
        if font.size(text)[0] <= max_px:
            return text
        while text and font.size(text + "...")[0] > max_px:
            text = text[:-1]
        return text + "..."

    def _shutdown(self):
        pygame.quit()
        sys.exit(0)
