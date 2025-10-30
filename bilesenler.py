import sys
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QTabWidget, QScrollArea, QFrame
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QTextCursor


def create_styled_label(text, bold=False, bg_color="#f0f0f0"):
    label = QLabel(text)
    label.setWordWrap(True)
    label.setStyleSheet(f"""
        background-color: {bg_color};
        border: 1px solid #aaa;
        padding: 8px;
        margin: 5px;
        border-radius: 10px;
        font-size: 14px;
        {'font-weight: bold;' if bold else ''}
    """)
    return label


def create_scrollable_container():
    container = QWidget()
    layout = QVBoxLayout()
    layout.setAlignment(Qt.AlignTop)
    container.setLayout(layout)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(container)
    scroll.setStyleSheet("background-color: #fff;")

    return scroll, layout


def create_top_bar(search_handler):
    top_bar = QHBoxLayout()

    search_input = QLineEdit()
    search_input.setPlaceholderText("Kelime, kök veya ayet numarası girin...")
    search_input.setStyleSheet("font-size: 14px; padding: 6px;")

    search_button = QPushButton("Ara")
    search_button.setStyleSheet("font-size: 14px; padding: 6px;")

    top_bar.addWidget(search_input)
    top_bar.addWidget(search_button)

    return top_bar, search_input, search_button


def create_pagination_controls(prev_handler, next_handler):
    controls = QHBoxLayout()
    controls.setAlignment(Qt.AlignCenter)

    prev_button = QPushButton("◀ Geri")
    next_button = QPushButton("İleri ▶")

    prev_button.setStyleSheet("padding: 6px; font-size: 13px;")
    next_button.setStyleSheet("padding: 6px; font-size: 13px;")

    controls.addWidget(prev_button)
    controls.addWidget(next_button)

    return controls, prev_button, next_button


def wrap_result_widget(result_widget):
    wrapper = QFrame()
    wrapper.setFrameShape(QFrame.StyledPanel)
    wrapper.setStyleSheet("background-color: #f9f9f9; border-radius: 12px; margin: 8px; padding: 6px;")

    layout = QVBoxLayout()
    layout.setContentsMargins(10, 10, 10, 10)
    layout.addWidget(result_widget)

    wrapper.setLayout(layout)
    return wrapper

