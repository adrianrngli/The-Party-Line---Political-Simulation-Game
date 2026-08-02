"""A pygame frontend for Party Chair Sim.

`Game.run()` calls the GameInterface methods synchronously and expects the
input methods (select / confirm / pause) to block until the player responds.
This frontend honors that contract: each input method runs its own pygame
event loop -- pumping events, redrawing, and ticking the clock -- until the
player makes a choice. The output methods (announce / show_person /
show_state) append to a scrolling log that the next redraw renders.

Requires: pip install pygame
"""

import sys
import pygame

from interfaces import GameInterface


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

    PAD = 12
    ROW_H = 34
    HEADER_H = 40

    def __init__(self, title="Party Chair Sim"):
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("menlo,consolas,monospace", 15)
        self.bold = pygame.font.SysFont("menlo,consolas,monospace", 15, bold=True)
        self.title_font = pygame.font.SysFont("menlo,consolas,monospace", 20, bold=True)

        self.log = []          # emitted entries: str lines or poll widgets (dict)
        self.log_scroll = 0    # lines scrolled up from the bottom
        self._capture = None   # when a list, interface output is diverted here
                               # (used to build per-option detail cards)
        self.context = {}      # persistent header info (year, president, party)

        self.header_rect = pygame.Rect(self.PAD, self.PAD,
                                       self.WIDTH - 2 * self.PAD, self.HEADER_H)
        self.log_rect = pygame.Rect(self.PAD, self.header_rect.bottom + self.PAD,
                                    self.WIDTH - 2 * self.PAD,
                                    392 - self.HEADER_H - self.PAD)
        self.control_rect = pygame.Rect(self.PAD, self.log_rect.bottom + self.PAD,
                                        self.WIDTH - 2 * self.PAD,
                                        self.HEIGHT - self.log_rect.bottom - 2 * self.PAD)

    # ------------------------------------------------------------------ #
    # GameInterface: output
    # ------------------------------------------------------------------ #

    def announce(self, text=""):
        if self._capture is not None:
            self._capture.append(str(text))  # building a detail card, not logging
            return
        self.log.append(str(text))
        self.log_scroll = 0  # snap to newest
        self._render()       # keep the window responsive between prompts

    def show_person(self, person, issues=[]):
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
        self.announce(state.name + " (" + str(state.rep_number) + " reps)")
        self.announce("  Wealth: " + state.wealth_classification()
                      + "   Density: " + state.density_classification())
        biggest = [ind.replace('_', ' ').title()
                   for ind in ["agriculture", "manufacturing", "professional_services", "public_sector"]
                   if state.stats[ind].value >= 25.0]
        if biggest:
            self.announce("  Biggest industries: " + ", ".join(biggest))
        for issue in issues:
            self.announce("  " + str(issue) + ": " + str(state.get_stance(issue)))
        self.announce("")

    def show_poll(self, title, results):
        if self._capture is not None:  # building a detail card: keep it textual
            GameInterface.show_poll(self, title, results)
            return
        self.log.append({"poll": str(title),
                         "results": [(str(label), float(pct)) for label, pct in results]})
        self.log_scroll = 0
        self._render()

    def set_context(self, **fields):
        self.context.update(fields)

    # ------------------------------------------------------------------ #
    # GameInterface: input (each runs a blocking event loop)
    # ------------------------------------------------------------------ #

    def select(self, prompt, options, labeler=str, *, details=None, allow_quit=False):
        options = list(options)
        cards = None
        if details is not None:
            # Divert each option's detail output into its own buffer, so we can
            # render it as a card beside the list rather than flooding the log.
            cards = []
            for option in options:
                self._capture = []
                details(self, option)
                cards.append([line for line in self._capture if line != ""] or [""])
            self._capture = None
        entries = [(labeler(option), option) for option in options]
        return self._choose(prompt, entries, allow_quit=allow_quit, cards=cards)

    def confirm(self, prompt):
        entries = [("Yea  (Y)", True), ("Nay  (N)", False)]
        keymap = {pygame.K_y: True, pygame.K_n: False}
        return self._choose(prompt, entries, allow_quit=False, keymap=keymap)

    def pause(self, message=""):
        self._choose(message or "Press Enter to continue",
                     [("Continue  (Enter)", None)],
                     allow_quit=False,
                     keymap={pygame.K_RETURN: 0, pygame.K_SPACE: 0},
                     any_key=True)

    # ------------------------------------------------------------------ #
    # core blocking loop shared by select / confirm / pause
    # ------------------------------------------------------------------ #

    def _choose(self, prompt, entries, *, allow_quit=False, keymap=None,
                any_key=False, cards=None):
        """Render the log + a control panel of clickable option rows, and block
        until the player picks one. Returns the chosen entry's value (or None
        for quit). `keymap` maps pygame keys to values; number keys 1-9 select
        by position; `any_key` lets any key resolve the first entry (for pause).
        When `cards` is given (one detail block per entry), the list is shown on
        the left and the focused entry's detail card on the right; up/down arrows
        move the focus and Enter picks it."""
        keymap = keymap or {}
        list_scroll = 0
        focus = 0
        prompt_lines = self._wrap(prompt, self.control_rect.width - 2 * self.PAD, self.bold)
        list_top = self.control_rect.y + self.PAD + len(prompt_lines) * self.bold.get_linesize() + 6
        list_bottom = self.control_rect.bottom - self.PAD - 20  # leave room for hint

        if cards is not None:
            list_w = int(self.control_rect.width * 0.40)
            card_rect = pygame.Rect(self.control_rect.x + self.PAD + list_w + self.PAD,
                                    list_top,
                                    self.control_rect.right - self.PAD
                                    - (self.control_rect.x + self.PAD + list_w + self.PAD),
                                    list_bottom - list_top)
        else:
            list_w = self.control_rect.width - 2 * self.PAD
            card_rect = None
        visible_rows = max(1, (list_bottom - list_top) // self.ROW_H)

        while True:
            mouse = pygame.mouse.get_pos()
            row_rects = self._row_rects(self.control_rect.x + self.PAD, list_w,
                                        list_top, len(entries), list_scroll, visible_rows)
            for idx, rect in row_rects:
                if rect.collidepoint(mouse):
                    focus = idx  # hovering a row focuses its card

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self._shutdown()
                elif event.type == pygame.MOUSEWHEEL:
                    if self._point_in(mouse, self.log_rect):
                        self._scroll_log(event.y)
                    else:
                        list_scroll = self._clamp(list_scroll - event.y,
                                                  0, max(0, len(entries) - visible_rows))
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for idx, rect in row_rects:
                        if rect.collidepoint(event.pos):
                            return entries[idx][1]
                    if allow_quit and self._quit_rect().collidepoint(event.pos):
                        return None
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
                    elif any_key:
                        return entries[0][1]

            self._render(prompt_lines=prompt_lines, row_rects=row_rects,
                         entries=entries, mouse=mouse, allow_quit=allow_quit,
                         card_rect=card_rect, card_lines=(cards[focus] if cards else None),
                         focus=focus)

        # unreachable

    # ------------------------------------------------------------------ #
    # rendering
    # ------------------------------------------------------------------ #

    def _render(self, prompt_lines=None, row_rects=None, entries=None, mouse=(0, 0),
                allow_quit=False, card_rect=None, card_lines=None, focus=None):
        self.screen.fill(self.BG)
        self._render_header()
        pygame.draw.rect(self.screen, self.PANEL, self.log_rect, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL, self.control_rect, border_radius=8)
        self._render_log()

        if prompt_lines is not None:
            y = self.control_rect.y + self.PAD
            for line in prompt_lines:
                self.screen.blit(self.bold.render(line, True, self.TEXT),
                                 (self.control_rect.x + self.PAD, y))
                y += self.bold.get_linesize()

        if card_rect is not None and card_lines is not None:
            self._render_card(card_rect, card_lines)

        if row_rects is not None:
            for idx, rect in row_rects:
                highlighted = rect.collidepoint(mouse) or idx == focus
                self._button(rect, str(idx + 1) + ".  " + str(entries[idx][0]),
                             highlighted, primary=True)
            if allow_quit:
                qrect = self._quit_rect()
                self._button(qrect, "Quit  (Q)", qrect.collidepoint(mouse), quit_style=True)
            hint_text = "Click a row, or press 1-9"
            if card_rect is not None:
                hint_text += "  /  ↑↓ + Enter"
            if allow_quit:
                hint_text += "  /  Q to quit"
            hint = self.font.render(hint_text, True, self.MUTED)
            self.screen.blit(hint, (self.control_rect.x + self.PAD,
                                    self.control_rect.bottom - 18))

        pygame.display.flip()
        self.clock.tick(self.FPS)

    def _render_card(self, rect, lines):
        """Draw a detail panel; the first line is treated as a bold header."""
        pygame.draw.rect(self.screen, self.PANEL_LIGHT, rect, border_radius=8)
        inner = rect.inflate(-2 * self.PAD, -2 * self.PAD)
        line_h = self.font.get_linesize()
        y = inner.top
        for i, line in enumerate(lines):
            font = self.bold if i == 0 else self.font
            color = self.WHITE if i == 0 else self.TEXT
            for piece in self._wrap(line, inner.width, font):
                if y + line_h > inner.bottom:
                    return
                self.screen.blit(font.render(piece, True, color), (inner.left, y))
                y += line_h

    def _render_header(self):
        pygame.draw.rect(self.screen, self.PANEL_LIGHT, self.header_rect, border_radius=8)
        segments = []
        if self.context.get("year") is not None:
            segments.append((str(self.context["year"]), self.ACCENT_HOVER))
        pres = self.context.get("president")
        if pres is not None:
            # str(pres) is already self-labeling: "President <name> (<party>-<state>)".
            segments.append((str(pres), self.TEXT))
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

    def _render_log(self):
        inner = self.log_rect.inflate(-2 * self.PAD, -2 * self.PAD)
        line_h = self.font.get_linesize()
        ops = self._log_ops(inner.width)
        max_lines = max(1, inner.height // line_h)
        self.log_scroll = self._clamp(self.log_scroll, 0, max(0, len(ops) - max_lines))
        end = len(ops) - self.log_scroll
        start = max(0, end - max_lines)
        y = inner.top
        for op in ops[start:end]:
            if op[0] == "text":
                self.screen.blit(op[2].render(op[1], True, op[3]), (inner.left, y))
            else:  # ("bar", label, pct)
                self._render_bar(inner.left, y, inner.width, op[1], op[2])
            y += line_h

    def _log_ops(self, width):
        """Flatten log entries into one-line render ops so the tail-scroll math
        stays uniform. Text lines wrap; poll widgets expand to a title + a bar
        per option."""
        ops = []
        for entry in self.log:
            if isinstance(entry, dict) and "poll" in entry:
                ops.append(("text", entry["poll"], self.bold, self.TEXT))
                for label, pct in entry["results"]:
                    ops.append(("bar", label, pct))
            else:
                for piece in self._wrap(str(entry), width, self.font):
                    ops.append(("text", piece, self.font, self.TEXT))
        return ops

    def _render_bar(self, x, y, width, label, pct):
        line_h = self.font.get_linesize()
        label_w, pct_w = 170, 56
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

    def _button(self, rect, label, hover, *, primary=True, quit_style=False):
        if quit_style:
            color = self.QUIT_HOVER if hover else self.QUIT_COLOR
        elif primary:
            color = self.ACCENT_HOVER if hover else self.ACCENT
        else:
            color = self.PANEL_LIGHT
        pygame.draw.rect(self.screen, color, rect, border_radius=6)
        label = self._truncate(label, rect.width - 20, self.font)
        txt = self.font.render(label, True, self.WHITE)
        self.screen.blit(txt, (rect.x + 10, rect.y + (rect.height - txt.get_height()) // 2))

    # ------------------------------------------------------------------ #
    # geometry + text helpers
    # ------------------------------------------------------------------ #

    def _row_rects(self, x, width, top, count, scroll, visible_rows):
        rects = []
        for i in range(scroll, min(count, scroll + visible_rows)):
            y = top + (i - scroll) * self.ROW_H
            rects.append((i, pygame.Rect(x, y, width, self.ROW_H - 6)))
        return rects

    @staticmethod
    def _keep_visible(focus, scroll, visible_rows, count):
        """Scroll the list minimally so `focus` stays within the visible window."""
        if focus < scroll:
            return focus
        if focus >= scroll + visible_rows:
            return focus - visible_rows + 1
        return scroll

    def _quit_rect(self):
        return pygame.Rect(self.control_rect.right - 120,
                           self.control_rect.bottom - 44, 100, 30)

    def _scroll_log(self, delta):
        self.log_scroll = max(0, self.log_scroll + delta)

    @staticmethod
    def _point_in(point, rect):
        return rect.collidepoint(point)

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
