#
#   Copyright (C) 2008-2015 by Nicolas Piganeau
#   npi@m4x.org
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the
#   Free Software Foundation, Inc.,
#   59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#

from Qt import QtCore, QtWidgets, Qt, QtGui
from ts2.gui import widgets


class ModernHeaderWidget(QtWidgets.QWidget):
    """Modern header widget with perfect layout and minimal design"""
    
    # Signals
    openActionTriggered = QtCore.pyqtSignal()
    editActionTriggered = QtCore.pyqtSignal()
    speedChanged = QtCore.pyqtSignal(int)
    zoomChanged = QtCore.pyqtSignal(int)
    pauseToggled = QtCore.pyqtSignal(bool)
    restartRequested = QtCore.pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_speed = 1
        self.is_paused = True
        self.setupUI()
        
    def setupUI(self):
        """Setup the modern header UI with responsive layout"""
        self.setFixedHeight(50)
        self.setStyleSheet("""
            ModernHeaderWidget {
                background-color: #f8f9fa;
                border-bottom: 1px solid #dee2e6;
            }
        """)
        
        # Main horizontal layout with better space management
        main_layout = QtWidgets.QHBoxLayout(self)
        main_layout.setContentsMargins(10, 6, 10, 6)  # Reduced margins
        main_layout.setSpacing(12)  # Reduced spacing
        
        # File Actions Section
        self.setupFileSection(main_layout)
        
        # Speed Control Section  
        self.setupSpeedSection(main_layout)
        
        # Zoom Control Section (make collapsible on small screens)
        self.setupZoomSection(main_layout)
        
        # Performance Section
        self.setupPerformanceSection(main_layout)
        
        # Time Control Section
        self.setupTimeSection(main_layout)
        
        # Flexible spacer (but limited)
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Preferred)
        spacer.setMinimumWidth(20)  # Minimum spacer width
        spacer.setMaximumWidth(100)  # Maximum spacer width
        main_layout.addWidget(spacer)
        
        # Simulation Title Section (most important, gets priority)
        self.setupTitleSection(main_layout)
        
    def setupFileSection(self, main_layout):
        """Setup file actions section"""
        self.file_container = QtWidgets.QWidget()
        file_layout = QtWidgets.QHBoxLayout(self.file_container)
        file_layout.setContentsMargins(0, 0, 0, 0)
        file_layout.setSpacing(8)
        
        # Section label
        file_label = QtWidgets.QLabel("File")
        file_label.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 11px;")
        file_layout.addWidget(file_label)
        
        # Open button
        self.open_btn = QtWidgets.QPushButton("Open")
        self.open_btn.clicked.connect(self.openActionTriggered.emit)
        self.open_btn.setFixedHeight(32)
        self.open_btn.setStyleSheet(self.getButtonStyle())
        file_layout.addWidget(self.open_btn)
        
        # Edit button
        self.edit_btn = QtWidgets.QPushButton("Edit")
        self.edit_btn.clicked.connect(self.editActionTriggered.emit)
        self.edit_btn.setFixedHeight(32)
        self.edit_btn.setStyleSheet(self.getButtonStyle())
        file_layout.addWidget(self.edit_btn)
        
        self.file_container.setFixedHeight(34)
        main_layout.addWidget(self.file_container)
        # Hide the file section in the header by default
        self.file_container.setVisible(False)
        
    def setupSpeedSection(self, main_layout):
        """Setup speed control section"""
        speed_container = QtWidgets.QWidget()
        speed_layout = QtWidgets.QHBoxLayout(speed_container)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        speed_layout.setSpacing(8)
        
        # Section label
        speed_label = QtWidgets.QLabel("Speed")
        speed_label.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 11px;")
        speed_layout.addWidget(speed_label)
        
        # Speed control group
        speed_group = QtWidgets.QWidget()
        speed_group_layout = QtWidgets.QHBoxLayout(speed_group)
        speed_group_layout.setContentsMargins(0, 0, 0, 0)
        speed_group_layout.setSpacing(1)
        
        # Decrease button
        self.speed_down = QtWidgets.QPushButton("−")
        self.speed_down.setFixedSize(32, 32)
        self.speed_down.clicked.connect(self.decreaseSpeed)
        self.speed_down.setStyleSheet(self.getSpeedButtonStyle())
        speed_group_layout.addWidget(self.speed_down)
        
        # Speed display
        self.speed_display = QtWidgets.QLabel("1x")
        self.speed_display.setFixedSize(40, 32)
        self.speed_display.setAlignment(Qt.AlignCenter)
        self.speed_display.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #ced4da;
                color: #495057;
                font-weight: bold;
                font-size: 12px;
            }
        """)
        speed_group_layout.addWidget(self.speed_display)
        
        # Increase button
        self.speed_up = QtWidgets.QPushButton("+")
        self.speed_up.setFixedSize(32, 32)
        self.speed_up.clicked.connect(self.increaseSpeed)
        self.speed_up.setStyleSheet(self.getSpeedButtonStyle())
        speed_group_layout.addWidget(self.speed_up)
        
        speed_layout.addWidget(speed_group)
        speed_container.setFixedHeight(34)
        main_layout.addWidget(speed_container)
        
    def setupZoomSection(self, main_layout):
        """Setup zoom control section with compact layout"""
        zoom_container = QtWidgets.QWidget()
        zoom_layout = QtWidgets.QHBoxLayout(zoom_container)
        zoom_layout.setContentsMargins(0, 0, 0, 0)
        zoom_layout.setSpacing(6)  # Reduced spacing
        
        # Section label
        zoom_label = QtWidgets.QLabel("Zoom")
        zoom_label.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 10px;")
        zoom_layout.addWidget(zoom_label)
        
        # Zoom widget - more compact
        self.zoom_widget = widgets.ZoomWidget(self)
        # Ensure enough width to avoid clipping internal slider/spinbox
        self.zoom_widget.setFixedHeight(32)
        self.zoom_widget.setMinimumWidth(260)
        self.zoom_widget.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.zoom_widget.valueChanged.connect(self.zoomChanged.emit)
        self.zoom_widget.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 1px solid #ced4da;
                height: 5px;
                background: white;
                border-radius: 2px;
            }
            QSlider::handle:horizontal {
                background: #495057;
                border: 1px solid #343a40;
                width: 12px;
                height: 12px;
                border-radius: 6px;
                margin: -4px 0;
            }
            QSlider::handle:horizontal:hover {
                background: #343a40;
            }
            QSpinBox {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 10px;
                max-width: 45px;
            }
            QSpinBox::up-button, QSpinBox::down-button {
                width: 0px;
            }
            QToolButton {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 2px 4px;
                font-size: 10px;
            }
        """)
        zoom_layout.addWidget(self.zoom_widget)
        # Allow the zoom widget to take available horizontal space within its section
        zoom_layout.setStretch(0, 0)
        zoom_layout.setStretch(1, 1)
        
        zoom_container.setFixedHeight(34)
        zoom_container.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        main_layout.addWidget(zoom_container)
        
    def setupPerformanceSection(self, main_layout):
        """Setup performance metrics section"""
        self.perf_container = QtWidgets.QWidget()
        perf_layout = QtWidgets.QHBoxLayout(self.perf_container)
        perf_layout.setContentsMargins(0, 0, 0, 0)
        perf_layout.setSpacing(8)
        
        # Section label
        perf_label = QtWidgets.QLabel("Score")
        perf_label.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 11px;")
        perf_layout.addWidget(perf_label)
        
        # Score display
        self.score_display = QtWidgets.QLCDNumber()
        self.score_display.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.score_display.setSegmentStyle(QtWidgets.QLCDNumber.Flat)
        self.score_display.setNumDigits(5)
        self.score_display.setFixedSize(80, 32)
        self.score_display.setStyleSheet("""
            QLCDNumber {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 3px;
                color: #495057;
            }
        """)
        perf_layout.addWidget(self.score_display)
        
        self.perf_container.setFixedHeight(34)
        main_layout.addWidget(self.perf_container)
        # Hide the score section in the header by default
        self.perf_container.setVisible(False)
        
    def setupTimeSection(self, main_layout):
        """Setup time control section"""
        time_container = QtWidgets.QWidget()
        time_layout = QtWidgets.QHBoxLayout(time_container)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(8)
        
        # Section label
        time_label = QtWidgets.QLabel("Time")
        time_label.setStyleSheet("color: #6c757d; font-weight: bold; font-size: 11px;")
        time_layout.addWidget(time_label)
        
        # Pause/Start button
        self.pause_btn = QtWidgets.QPushButton("Start")
        self.pause_btn.setCheckable(True)
        self.pause_btn.setChecked(True)  # Initially paused
        self.pause_btn.clicked.connect(self.togglePause)
        self.pause_btn.setFixedSize(60, 32)
        self.updatePauseButtonStyle()
        time_layout.addWidget(self.pause_btn)

        # Restart button
        self.restart_btn = QtWidgets.QPushButton("Restart")
        self.restart_btn.setFixedSize(70, 32)
        self.restart_btn.setStyleSheet(self.getButtonStyle())
        self.restart_btn.clicked.connect(self.restartRequested.emit)
        time_layout.addWidget(self.restart_btn)
        
        # Clock display
        self.clock_widget = widgets.ClockWidget(self)
        self.clock_widget.setFixedSize(90, 32)
        self.clock_widget.setStyleSheet("""
            QLCDNumber {
                background-color: #343a40;
                border: 1px solid #495057;
                border-radius: 3px;
                color: white;
                font-size: 12px;
            }
        """)
        time_layout.addWidget(self.clock_widget)
        
        time_container.setFixedHeight(34)
        main_layout.addWidget(time_container)
        
    def setupTitleSection(self, main_layout):
        """Setup simulation title section with responsive sizing"""
        title_container = QtWidgets.QWidget()
        title_layout = QtWidgets.QHBoxLayout(title_container)
        title_layout.setContentsMargins(0, 0, 0, 0)
        
        self.title_label = QtWidgets.QLabel("TrackTitans - No simulation loaded")
        self.title_label.setAlignment(Qt.AlignCenter | Qt.AlignVCenter)
        self.title_label.setFixedHeight(32)
        # Responsive width - minimum needed, maximum reasonable
        self.title_label.setMinimumWidth(200)  # Reduced minimum
        self.title_label.setMaximumWidth(400)  # Set reasonable maximum
        # Allow the title to shrink and expand as needed
        self.title_label.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        self.title_label.setStyleSheet("""
            QLabel {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 6px 10px;
                color: #495057;
                font-size: 12px;
                font-weight: 500;
            }
        """)
        title_layout.addWidget(self.title_label)
        
        title_container.setFixedHeight(34)
        title_container.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Fixed)
        main_layout.addWidget(title_container)
        
    def getButtonStyle(self):
        """Get standard button style"""
        return """
            QPushButton {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 8px 12px;
                color: #495057;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """
        
    def getSpeedButtonStyle(self):
        """Get speed button style"""
        return """
            QPushButton {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 3px;
                color: #495057;
                font-weight: bold;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
            QPushButton:pressed {
                background-color: #dee2e6;
            }
        """
        
    def updatePauseButtonStyle(self):
        """Update pause button style based on state"""
        if self.is_paused:
            self.pause_btn.setText("Start")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #28a745;
                    border: 1px solid #28a745;
                    border-radius: 3px;
                    color: white;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #218838;
                }
            """)
        else:
            self.pause_btn.setText("Pause")
            self.pause_btn.setStyleSheet("""
                QPushButton {
                    background-color: #ffc107;
                    border: 1px solid #ffc107;
                    border-radius: 3px;
                    color: #212529;
                    font-weight: bold;
                    font-size: 12px;
                }
                QPushButton:hover {
                    background-color: #e0a800;
                }
            """)
            
    def togglePause(self):
        """Toggle pause state"""
        self.is_paused = not self.is_paused
        self.updatePauseButtonStyle()
        self.pauseToggled.emit(self.is_paused)
        
    def setPauseState(self, paused):
        """Set pause state externally"""
        self.is_paused = paused
        self.pause_btn.setChecked(paused)
        self.updatePauseButtonStyle()
        
    def increaseSpeed(self):
        """Increase simulation speed"""
        if self.current_speed < 10:
            self.current_speed += 1
            self.speed_display.setText(f"{self.current_speed}x")
            self.speedChanged.emit(self.current_speed)
            
    def decreaseSpeed(self):
        """Decrease simulation speed"""
        if self.current_speed > 1:
            self.current_speed -= 1
            self.speed_display.setText(f"{self.current_speed}x")
            self.speedChanged.emit(self.current_speed)
            
    def setSpeed(self, speed):
        """Set speed externally"""
        self.current_speed = max(1, min(10, speed))
        self.speed_display.setText(f"{self.current_speed}x")
        
    def setSimulationTitle(self, title):
        """Update simulation title"""
        if title:
            self.title_label.setText(f"TrackTitans - {title}")
        else:
            self.title_label.setText("TrackTitans - No simulation loaded")
            
    def setScore(self, score):
        """Update penalty score"""
        self.score_display.display(score)
        
    def setTime(self, time):
        """Update clock time"""
        self.clock_widget.setTime(time)
        
    def setControlsEnabled(self, enabled):
        """Enable/disable controls"""
        self.open_btn.setEnabled(enabled)
        self.edit_btn.setEnabled(enabled)
        self.speed_up.setEnabled(enabled)
        self.speed_down.setEnabled(enabled)
        self.pause_btn.setEnabled(enabled)
        self.restart_btn.setEnabled(enabled)
        self.zoom_widget.setEnabled(enabled)
