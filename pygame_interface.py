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

    def __init__(self, title="Party Chair Sim"):
        pygame.init()
        self.screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption(title)
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("menlo,consolas,monospace", 15)
        self.bold = pygame.font.SysFont("menlo,consolas,monospace", 15, bold=True)
        self.title_font = pygame.font.SysFont("menlo,consolas,monospace", 20, bold=True)

        self.log = []          # list of already-emitted text lines
        self.log_scroll = 0    # lines scrolled up from the bottom

        self.log_rect = pygame.Rect(self.PAD, self.PAD,
                                    self.WIDTH - 2 * self.PAD, 392)
        self.control_rect = pygame.Rect(self.PAD, self.log_rect.bottom + self.PAD,
                                        self.WIDTH - 2 * self.PAD,
                                        self.HEIGHT - self.log_rect.bottom - 2 * self.PAD)

    # ------------------------------------------------------------------ #
    # GameInterface: output
    # ------------------------------------------------------------------ #

    def announce(self, text=""):
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

    # ------------------------------------------------------------------ #
    # GameInterface: input (each runs a blocking event loop)
    # ------------------------------------------------------------------ #

    def select(self, prompt, options, labeler=str, *, details=None, allow_quit=False):
        options = list(options)
        if details is not None:
            for option in options:
                details(self, option)
        entries = [(labeler(option), option) for option in options]
        return self._choose(prompt, entries, allow_quit=allow_quit)

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

    def _choose(self, prompt, entries, *, allow_quit=False, keymap=None, any_key=False):
        """Render the log + a control panel of clickable option rows, and block
        until the player picks one. Returns the chosen entry's value (or None
        for quit). `keymap` maps pygame keys to values; number keys 1-9 select
        by position; `any_key` lets any key resolve the first entry (for pause)."""
        keymap = keymap or {}
        list_scroll = 0
        prompt_lines = self._wrap(prompt, self.control_rect.width - 2 * self.PAD, self.bold)
        list_top = self.control_rect.y + self.PAD + len(prompt_lines) * self.bold.get_linesize() + 6
        list_bottom = self.control_rect.bottom - self.PAD - 20  # leave room for hint
        visible_rows = max(1, (list_bottom - list_top) // self.ROW_H)

        while True:
            mouse = pygame.mouse.get_pos()
            row_rects = self._row_rects(list_top, list_bottom, len(entries), list_scroll, visible_rows)

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
                    if pygame.K_1 <= event.key <= pygame.K_9:
                        pick = event.key - pygame.K_1
                        if pick < len(entries):
                            return entries[pick][1]
                    if any_key:
                        return entries[0][1]

            self._render(prompt_lines=prompt_lines, row_rects=row_rects,
                         entries=entries, mouse=mouse, allow_quit=allow_quit)

        # unreachable

    # ------------------------------------------------------------------ #
    # rendering
    # ------------------------------------------------------------------ #

    def _render(self, prompt_lines=None, row_rects=None, entries=None, mouse=(0, 0),
                allow_quit=False):
        self.screen.fill(self.BG)
        pygame.draw.rect(self.screen, self.PANEL, self.log_rect, border_radius=8)
        pygame.draw.rect(self.screen, self.PANEL, self.control_rect, border_radius=8)
        self._render_log()

        if prompt_lines is not None:
            y = self.control_rect.y + self.PAD
            for line in prompt_lines:
                self.screen.blit(self.bold.render(line, True, self.TEXT),
                                 (self.control_rect.x + self.PAD, y))
                y += self.bold.get_linesize()

        if row_rects is not None:
            for idx, rect in row_rects:
                hover = rect.collidepoint(mouse)
                self._button(rect, str(idx + 1) + ".  " + str(entries[idx][0]),
                             hover, primary=True)
            if allow_quit:
                qrect = self._quit_rect()
                self._button(qrect, "Quit  (Q)", qrect.collidepoint(mouse), quit_style=True)
            hint = self.font.render("Click a row, or press 1-9"
                                    + ("  /  Q to quit" if allow_quit else ""),
                                    True, self.MUTED)
            self.screen.blit(hint, (self.control_rect.x + self.PAD,
                                    self.control_rect.bottom - 18))

        pygame.display.flip()
        self.clock.tick(self.FPS)

    def _render_log(self):
        inner = self.log_rect.inflate(-2 * self.PAD, -2 * self.PAD)
        wrapped = []
        for line in self.log:
            wrapped.extend(self._wrap(line, inner.width, self.font))
        line_h = self.font.get_linesize()
        max_lines = max(1, inner.height // line_h)
        self.log_scroll = self._clamp(self.log_scroll, 0, max(0, len(wrapped) - max_lines))
        end = len(wrapped) - self.log_scroll
        start = max(0, end - max_lines)
        y = inner.top
        for line in wrapped[start:end]:
            self.screen.blit(self.font.render(line, True, self.TEXT), (inner.left, y))
            y += line_h

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

    def _row_rects(self, top, bottom, count, scroll, visible_rows):
        rects = []
        for i in range(scroll, min(count, scroll + visible_rows)):
            y = top + (i - scroll) * self.ROW_H
            rects.append((i, pygame.Rect(self.control_rect.x + self.PAD, y,
                                         self.control_rect.width - 2 * self.PAD,
                                         self.ROW_H - 6)))
        return rects

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
