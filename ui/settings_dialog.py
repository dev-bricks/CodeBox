#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Settings Dialog for CodeBox"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLabel,
    QSpinBox, QCheckBox, QComboBox, QDialogButtonBox, QFontComboBox
)
from PySide6.QtGui import QFont
from config import load_settings, save_settings
from features.theme_manager import get_available_themes


class SettingsDialog(QDialog):
    """Einstellungsdialog für Editor, Theme und Verhalten"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Einstellungen")
        self.resize(380, 260)
        self._settings = load_settings()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        # Font Family
        self.font_combo = QFontComboBox()
        self.font_combo.setFontFilters(QFontComboBox.FontFilter.MonospacedFonts)
        current_font = self._settings.get("font_family", "Consolas")
        self.font_combo.setCurrentFont(QFont(current_font))
        form_layout.addRow(QLabel("Schriftart:"), self.font_combo)

        # Font Size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(6, 72)
        self.font_size_spin.setValue(int(self._settings.get("font_size", 10)))
        form_layout.addRow(QLabel("Schriftgröße:"), self.font_size_spin)

        # Tab Size
        self.tab_size_spin = QSpinBox()
        self.tab_size_spin.setRange(1, 8)
        self.tab_size_spin.setValue(int(self._settings.get("tab_size", 4)))
        form_layout.addRow(QLabel("Tab-Breite (Leerzeichen):"), self.tab_size_spin)

        # Theme
        self.theme_combo = QComboBox()
        themes = get_available_themes()
        for theme in themes:
            self.theme_combo.addItem(theme.capitalize(), theme)
        current_theme = self._settings.get("theme", "dark").lower()
        theme_idx = self.theme_combo.findData(current_theme)
        if theme_idx >= 0:
            self.theme_combo.setCurrentIndex(theme_idx)
        form_layout.addRow(QLabel("Theme:"), self.theme_combo)

        # Auto Save
        self.auto_save_cb = QCheckBox("Dateien beim Ausführen automatisch speichern")
        self.auto_save_cb.setChecked(bool(self._settings.get("auto_save", False)))
        form_layout.addRow(self.auto_save_cb)

        # Show Minimap
        self.minimap_cb = QCheckBox("Minimap anzeigen")
        self.minimap_cb.setChecked(bool(self._settings.get("show_minimap", True)))
        form_layout.addRow(self.minimap_cb)

        layout.addLayout(form_layout)

        # Dialog Buttons
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def get_settings(self) -> dict:
        """Gibt die aktuell eingestellten Optionen als Dict zurück."""
        settings = self._settings.copy()
        settings["font_family"] = self.font_combo.currentFont().family()
        settings["font_size"] = self.font_size_spin.value()
        settings["tab_size"] = self.tab_size_spin.value()
        settings["theme"] = self.theme_combo.currentData() or "dark"
        settings["auto_save"] = self.auto_save_cb.isChecked()
        settings["show_minimap"] = self.minimap_cb.isChecked()
        return settings

    def accept(self):
        """Speichert die Einstellungen und schließt den Dialog."""
        new_settings = self.get_settings()
        save_settings(new_settings)
        super().accept()
