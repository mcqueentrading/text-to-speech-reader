#!/usr/bin/env python3
import curses
import sys
import time

text_file = sys.argv[1]
index_file = sys.argv[2]

with open(text_file, "r") as f:
    text = f.read()

words = text.split()


def main(stdscr):
    curses.curs_set(0)
    curses.start_color()
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_YELLOW)
    max_y, max_x = stdscr.getmaxyx()

    while True:
        try:
            with open(index_file, "r") as f:
                content = f.read().strip()
            start, end = map(int, content.split(",")) if content else (0, 0)
        except Exception:
            start, end = 0, 0

        stdscr.clear()
        display_lines = []
        line = ""
        for word in words:
            if len(line) + len(word) + 1 >= max_x:
                display_lines.append(line)
                line = word + " "
            else:
                line += word + " "
        if line:
            display_lines.append(line)

        highlight_line_index = 0
        word_count = 0
        for idx, display_line in enumerate(display_lines):
            word_count += len(display_line.split())
            if word_count > start:
                highlight_line_index = idx
                break

        start_line = max(0, highlight_line_index - max_y // 2)
        word_index = 0
        for y, display_line in enumerate(display_lines[start_line:start_line + max_y]):
            x = 0
            for word in display_line.split():
                if start <= word_index < end:
                    stdscr.addstr(y, x, word + " ", curses.color_pair(1))
                else:
                    stdscr.addstr(y, x, word + " ")
                x += len(word) + 1
                word_index += 1
        stdscr.refresh()
        time.sleep(0.05)


curses.wrapper(main)
