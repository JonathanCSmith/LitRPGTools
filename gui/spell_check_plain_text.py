"""QPlainTextEdit With Inline Spell Check
Original PyQt4 Version:
    https://nachtimwald.com/2009/08/22/qplaintextedit-with-in-line-spell-check/
Copyright 2009 John Schember
Copyright 2018 Stephan Sokolow
Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:
The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__license__ = 'MIT'
__author__ = 'John Schember; Stephan Sokolow'
__docformat__ = 'restructuredtext en'

import sys
import enchant
from PyQt6.QtCore import QEvent, Qt
from PyQt6.QtGui import QFocusEvent, QAction, QActionGroup, QTextCursor, QSyntaxHighlighter, QTextCharFormat, QTextBlockUserData
from enchant import tokenize
from enchant.utils import trim_suggestions
from enchant.errors import TokenizerNotFoundError
from PyQt6.QtWidgets import QPlainTextEdit, QMenu


# pylint: disable=no-name-in-module
# from PyQt5.Qt import Qt
# from PyQt5.QtCore import QEvent
# from PyQt5.QtGui import (QFocusEvent, QSyntaxHighlighter, QTextBlockUserData,
#                          QTextCharFormat, QTextCursor)
# from PyQt5.QtWidgets import (QAction, QActionGroup, QApplication, QMenu,
#                              QPlainTextEdit)

class SpellTextEdit(QPlainTextEdit):
    """QPlainTextEdit subclass which does spell-checking using PyEnchant"""

    # Clamping value for words like "regex" which suggest so many things that
    # the menu runs from the top to the bottom of the screen and spills over
    # into a second column.
    max_suggestions = 20

    def __init__(self, *args):
        QPlainTextEdit.__init__(self, *args)

        # Start with a default dictionary based on the current locale.
        self.highlighter = EnchantHighlighter(self.document())
        self.highlighter.setDict(enchant.Dict())

    def contextMenuEvent(self, event):
        """Custom context menu handler to add a spelling suggestions submenu"""
        popup_menu = self.createSpellcheckContextMenu(event.pos())
        popup_menu.exec(event.globalPos())

        # Fix bug observed in Qt 5.2.1 on *buntu 14.04 LTS where:
        # 1. The cursor remains invisible after closing the context menu
        # 2. Keyboard input causes it to appear, but it doesn't blink
        # 3. Switching focus away from and back to the window fixes it
        self.focusInEvent(QFocusEvent(QEvent.Type.FocusIn))

    def createSpellcheckContextMenu(self, pos):
        """Create and return an augmented default context menu.
        This may be used as an alternative to the QPoint-taking form of
        ``createStandardContextMenu`` and will work on pre-5.5 Qt.
        """
        try:  # Recommended for Qt 5.5+ (Allows contextual Qt-provided entries)
            menu = self.createStandardContextMenu(pos)
        except TypeError:  # Before Qt 5.5
            menu = self.createStandardContextMenu()

        # Add a submenu for setting the spell-check language
        menu.addSeparator()
        menu.addMenu(self.createLanguagesMenu(menu))
        menu.addMenu(self.createFormatsMenu(menu))

        # Try to retrieve a menu of corrections for the right-clicked word
        spell_menu = self.createCorrectionsMenu(
            self.cursorForMisspelling(pos), menu)

        if spell_menu:
            menu.insertSeparator(menu.actions()[0])
            menu.insertMenu(menu.actions()[0], spell_menu)

        return menu

    def createCorrectionsMenu(self, cursor, parent=None):
        """Create and return a menu for correcting the selected word."""
        if not cursor:
            return None

        text = cursor.selectedText()
        suggests = trim_suggestions(text,
                                    self.highlighter.dict().suggest(text),
                                    self.max_suggestions)

        spell_menu = QMenu('Spelling Suggestions', parent)
        for word in suggests:
            action = QAction(word, spell_menu)
            action.setData((cursor, word))
            spell_menu.addAction(action)

        # Only return the menu if it's non-empty
        if spell_menu.actions():
            spell_menu.triggered.connect(self.cb_correct_word)
            return spell_menu

        return None

    def createLanguagesMenu(self, parent=None):
        """Create and return a menu for selecting the spell-check language."""
        curr_lang = self.highlighter.dict().tag
        lang_menu = QMenu("Language", parent)
        lang_actions = QActionGroup(lang_menu)

        for lang in enchant.list_languages():
            action = lang_actions.addAction(lang)
            action.setCheckable(True)
            action.setChecked(lang == curr_lang)
            action.setData(lang)
            lang_menu.addAction(action)

        lang_menu.triggered.connect(self.cb_set_language)
        return lang_menu

    def createFormatsMenu(self, parent=None):
        """Create and return a menu for selecting the spell-check language."""
        fmt_menu = QMenu("Format", parent)
        fmt_actions = QActionGroup(fmt_menu)

        curr_format = self.highlighter.chunkers()
        for name, chunkers in (('Text', []), ('HTML', [tokenize.HTMLChunker])):
            action = fmt_actions.addAction(name)
            action.setCheckable(True)
            action.setChecked(chunkers == curr_format)
            action.setData(chunkers)
            fmt_menu.addAction(action)

        fmt_menu.triggered.connect(self.cb_set_format)
        return fmt_menu

    def cursorForMisspelling(self, pos):
        """Return a cursor selecting the misspelled word at ``pos`` or ``None``
        This leverages the fact that QPlainTextEdit already has a system for
        processing its contents in limited-size blocks to keep things fast.
        """
        cursor = self.cursorForPosition(pos)
        misspelled_words = getattr(cursor.block().userData(), 'misspelled', [])

        # If the cursor is within a misspelling, select the word
        for (start, end) in misspelled_words:
            if start <= cursor.positionInBlock() <= end:
                block_pos = cursor.block().position()

                cursor.setPosition(block_pos + start, QTextCursor.MoveMode.MoveAnchor)
                cursor.setPosition(block_pos + end, QTextCursor.MoveMode.KeepAnchor)
                break

        if cursor.hasSelection():
            return cursor
        else:
            return None

    def cb_correct_word(self, action):  # pylint: disable=no-self-use
        """Event handler for 'Spelling Suggestions' entries."""
        cursor, word = action.data()

        cursor.beginEditBlock()
        cursor.removeSelectedText()
        cursor.insertText(word)
        cursor.endEditBlock()

    def cb_set_language(self, action):
        """Event handler for 'Language' menu entries."""
        lang = action.data()
        self.highlighter.setDict(enchant.Dict(lang))

    def cb_set_format(self, action):
        """Event handler for 'Language' menu entries."""
        chunkers = action.data()
        self.highlighter.setChunkers(chunkers)
        # TODO: Emit an event so this menu can trigger other things

class EnchantHighlighter(QSyntaxHighlighter):
    """QSyntaxHighlighter subclass which consults a PyEnchant dictionary"""
    tokenizer = None
    token_filters = (tokenize.EmailFilter, tokenize.URLFilter)

    # Define the spellcheck style once and just assign it as necessary
    # XXX: Does QSyntaxHighlighter.setFormat handle keeping this from
    #      clobbering styles set in the data itself?
    err_format = QTextCharFormat()
    err_format.setUnderlineColor(Qt.GlobalColor.red)
    err_format.setUnderlineStyle(QTextCharFormat.UnderlineStyle.SpellCheckUnderline)

    def __init__(self, *args):
        QSyntaxHighlighter.__init__(self, *args)

        # Initialize private members
        self._sp_dict = None
        self._chunkers = []

    def chunkers(self):
        """Gets the chunkers in use"""
        return self._chunkers

    def dict(self):
        """Gets the spelling dictionary in use"""
        return self._sp_dict

    def setChunkers(self, chunkers):
        """Sets the list of chunkers to be used"""
        self._chunkers = chunkers
        self.setDict(self.dict())
        # FIXME: Revert self._chunkers on failure to ensure consistent state

    def setDict(self, sp_dict):
        """Sets the spelling dictionary to be used"""
        try:
            self.tokenizer = tokenize.get_tokenizer(sp_dict.tag,
                chunkers=self._chunkers, filters=self.token_filters)
        except TokenizerNotFoundError:
            # Fall back to the "good for most euro languages" English tokenizer
            self.tokenizer = tokenize.get_tokenizer(
                chunkers=self._chunkers, filters=self.token_filters)
        self._sp_dict = sp_dict

        self.rehighlight()

    def highlightBlock(self, text):
        """Overridden QSyntaxHighlighter method to apply the highlight"""
        if not self._sp_dict:
            return

        # Build a list of all misspelled words and highlight them
        misspellings = []
        for (word, pos) in self.tokenizer(text):
            if not self._sp_dict.check(word):
                self.setFormat(pos, len(word), self.err_format)
                misspellings.append((pos, pos + len(word)))

        # Store the list so the context menu can reuse this tokenization pass
        # (Block-relative values so editing other blocks won't invalidate them)
        data = QTextBlockUserData()
        data.misspelled = misspellings
        self.setCurrentBlockUserData(data)
