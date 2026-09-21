"""Shared desktop palette and Qt styling; presentation only."""
from PySide6.QtGui import QColor, QBrush, QPen

BACKGROUND = "#101925"
SURFACE = "#192638"
TEXT = "#e2eaf5"
MUTED = "#a6b7cd"
ACCENT = "#619aff"

QSS = """
QWidget { background: #101925; color: #e2eaf5; font-family: 'Segoe UI'; font-size: 13px; }
QLabel { background: transparent; }
QFrame#sidebar { background: #0c1420; border-right: 1px solid #26374e; }
QLabel#brand { color: #eef4fc; font-size: 27px; font-weight: 700; padding: 6px 0; }
QLabel#sidebarCaption { color: #8ca5c2; font-size: 12px; }
QLabel#sidebarUser { background: #1a2b41; color: #cfdef0; border: 1px solid #314967; border-radius: 10px; padding: 16px; }
QPushButton, QToolButton { background: #24364d; color: #dbe7f7; border: 1px solid #344c69; border-radius: 8px; padding: 10px 16px; font-weight: 600; }
QPushButton:hover, QToolButton:hover { background: #304966; border-color: #6b9bda; }
QPushButton:pressed { background: #162b44; }
QPushButton:focus, QToolButton:focus { border: 2px solid #82b4ff; }
QPushButton#navButton { text-align: left; background: transparent; border: none; padding: 14px; color: #a5b7cf; }
QPushButton#navButton:hover { background: #1c2d43; color: #eef4ff; }
QPushButton#navButton:checked { background: #203d60; border-left: 3px solid #67a5ff; color: #eef4ff; }
QPushButton#primaryButton { background: #316cc3; color: #ffffff; border: 1px solid #5d95e2; }
QPushButton#primaryButton:hover { background: #3d80da; }
QPushButton#dangerButton { background: #813340; color: #fff0f1; border: 1px solid #b65561; }
QPushButton#dangerButton:hover { background: #a43c4b; }
QPushButton:disabled { background: #1c2a3b; color: #77899f; border-color: #293b51; }
QFrame#card { background: qlineargradient(x1:0,y1:0,x2:1,y2:1,stop:0 #1d2d42,stop:1 #172335); border: 1px solid #30445f; border-radius: 14px; padding: 12px; }
QFrame#emptyState { background: #182638; border: 1px dashed #405b7a; border-radius: 14px; min-height: 180px; }
QLabel#pageTitle { font-size: 29px; font-weight: 700; color: #edf3fc; }
QLabel#pageSubtitle, QLabel#mutedText { color: #a6b7cd; }
QLabel#sectionTitle { font-size: 17px; font-weight: 600; color: #e2eaf5; }
QLabel#eyebrow, QLabel#metricTitle { color: #a9bfd8; font-size: 12px; font-weight: 600; }
QLabel#heroScore, QLabel#monitorScore { color: #86b8ff; font-size: 46px; font-weight: 700; }
QLabel#metricValue { color: #e7f0fc; font-size: 24px; font-weight: 600; }
QLabel#sessionTime { font-size: 22px; color: #bdcee4; }
QLabel#videoSurface { background: #080f19; color: #a6bad5; border: 1px solid #354d6a; border-radius: 12px; }
QLabel#cameraStatus, QLabel#statusText, QLabel#stateBadge { background: #24364d; color: #c5d6eb; border: 1px solid #405875; border-radius: 8px; padding: 7px 12px; }
QLabel#plainMetric { background: #152235; color: #c6d7ec; padding: 10px; border-radius: 7px; }
QProgressBar { background: #0e1928; border: 1px solid #30455f; border-radius: 7px; min-height: 14px; max-height: 14px; }
QProgressBar::chunk { background: #619aff; border-radius: 6px; }
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical { background: #111d2c; width: 10px; }
QScrollBar::handle:vertical { background: #3b526e; min-height: 30px; border-radius: 5px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QCheckBox { background: transparent; color: #c0d2e9; spacing: 10px; padding: 8px; }
QCheckBox::indicator { width: 16px; height: 16px; border: 2px solid #6e8aaa; border-radius: 4px; background: #102034; }
QCheckBox::indicator:checked { background: #619aff; border-color: #a4caff; }
QLineEdit { background: #102034; color: #e2eaf5; border: 1px solid #45658c; padding: 8px; border-radius: 8px; }
QToolTip { color: #eef4fc; background: #223852; border: 1px solid #6286b0; padding: 8px; }
"""


def style_level(widget, color=None):
    """Retain the badge surface while highlighting an available assessment."""
    color = {"#238a5a": "#79d9ad", "#b77900": "#f0cd74",
             "#d96812": "#ffae75", "#c93737": "#ff929a",
             "#831c2c": "#ed879e"}.get(color, color)
    widget.setStyleSheet(f"color: {color}; border-color: {color};" if color else "")


def style_chart(chart):
    chart.setBackgroundBrush(QBrush(QColor(SURFACE)))
    chart.setTitleBrush(QBrush(QColor(TEXT)))
    chart.setPlotAreaBackgroundBrush(QBrush(QColor(BACKGROUND)))
    chart.setPlotAreaBackgroundVisible(True)
    for axis in chart.axes():
        axis.setLabelsBrush(QBrush(QColor(MUTED)))
        axis.setTitleBrush(QBrush(QColor(MUTED)))
        axis.setGridLinePen(QPen(QColor("#2b405a")))
        axis.setLinePen(QPen(QColor("#486383")))
    for series in chart.series():
        series.setPen(QPen(QColor(ACCENT), 2.5))
        series.setPointsVisible(True)
