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

from Qt import QtCore, QtWidgets, Qt, QtGui, QtWebEngineWidgets, WEB_ENGINE_AVAILABLE
import json
import os


class NavigationButton(QtWidgets.QPushButton):
    """Custom navigation button for sidebar"""
    
    def __init__(self, text, icon_name=None, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(45)
        self.setText(text)
        
        # Style the button with minimal colors
        self.setStyleSheet("""
            NavigationButton {
                background-color: transparent;
                border: none;
                text-align: left;
                padding-left: 15px;
                color: #495057;
                font-size: 14px;
                font-weight: 500;
            }
            NavigationButton:hover {
                background-color: #e9ecef;
            }
            NavigationButton:checked {
                background-color: #495057;
                color: white;
                border-left: 4px solid #343a40;
            }
        """)


class SidebarNavigation(QtWidgets.QWidget):
    """Modern left sidebar navigation panel"""
    
    # Signals for view changes
    viewChanged = QtCore.pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()
        
    def setupUI(self):
        """Setup the sidebar UI"""
        self.setFixedWidth(250)
        self.setStyleSheet("""
            SidebarNavigation {
                background-color: #f8f9fa;
                border-right: 2px solid #dee2e6;
            }
        """)
        
        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Header
        header = QtWidgets.QWidget()
        header.setStyleSheet("""
            background-color: #343a40;
            color: white;
            padding: 10px;
        """)
        header.setFixedHeight(80)
        
        header_layout = QtWidgets.QVBoxLayout(header)
        header_layout.setContentsMargins(5, 8, 5, 8)
        header_layout.setSpacing(4)
        
        title_label = QtWidgets.QLabel("TrackTitans")
        title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        subtitle_label = QtWidgets.QLabel("Railway Operations")
        subtitle_label.setStyleSheet("font-size: 11px; color: rgba(255,255,255,0.8);")
        subtitle_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(subtitle_label)
        
        layout.addWidget(header)
        
        # Navigation buttons
        self.button_group = QtWidgets.QButtonGroup()
        self.button_group.setExclusive(True)
        
        nav_container = QtWidgets.QWidget()
        nav_layout = QtWidgets.QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 10, 0, 0)
        nav_layout.setSpacing(2)
        
        # Define navigation items
        nav_items = [
            ("simulation", "Simulation View"),
            ("map_overview", "Map Overview"),
            ("train_management", "Train Management"),
            ("system_status", "System Status"), 
            ("whatif_analysis", "What-If Analysis"),
            ("kpi_dashboard", "KPI Dashboard"),
            ("audit_logs", "Audit Logs"),
            ("settings", "Settings")
        ]
        
        for view_name, display_text in nav_items:
            button = NavigationButton(display_text)
            button.clicked.connect(lambda checked, name=view_name: self.onButtonClicked(name))
            self.button_group.addButton(button)
            nav_layout.addWidget(button)
            
        # Set simulation as default active
        self.button_group.buttons()[0].setChecked(True)
        
        nav_layout.addStretch()
        layout.addWidget(nav_container)
        
        # Status indicator at bottom
        status_widget = QtWidgets.QWidget()
        status_widget.setFixedHeight(40)
        status_widget.setStyleSheet("background-color: #e9ecef; border-top: 1px solid #dee2e6;")
        
        status_layout = QtWidgets.QHBoxLayout(status_widget)
        
        self.connection_status = QtWidgets.QLabel("● Connected")
        self.connection_status.setStyleSheet("color: #28a745; font-size: 12px;")
        status_layout.addWidget(self.connection_status)
        
        layout.addWidget(status_widget)
        
    def onButtonClicked(self, view_name):
        """Handle navigation button clicks"""
        self.viewChanged.emit(view_name)
        
    def setConnectionStatus(self, connected):
        """Update connection status indicator"""
        if connected:
            self.connection_status.setText("● Connected")
            self.connection_status.setStyleSheet("color: #28a745; font-size: 12px;")
        else:
            self.connection_status.setText("● Disconnected")
            self.connection_status.setStyleSheet("color: #dc3545; font-size: 12px;")


class MapOverviewWidget(QtWidgets.QWidget):
    """Interactive map overview with section search and zoom"""
    
    # Signal for section selection
    sectionSelected = QtCore.pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.sections_data = []
        self.setupUI()
        self.loadDummyData()
        
    def setupUI(self):
        """Setup simple map overview UI - just title and map view"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Simple centered title only
        title = QtWidgets.QLabel("Railway Network Map")
        title.setStyleSheet("font-size: 24px; font-weight: bold; color: #495057; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        # Map view - stable railway network visualization
        self.createRailwayNetworkView(layout)
    
    def createRailwayNetworkView(self, layout):
        """Create stable railway network visualization"""
        # Create main map frame
        map_frame = QtWidgets.QFrame()
        map_frame.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 8px;
            }
        """)
        
        map_layout = QtWidgets.QVBoxLayout(map_frame)
        map_layout.setContentsMargins(30, 30, 30, 30)
        map_layout.setSpacing(20)
        
        # Create interactive railway network grid
        network_widget = QtWidgets.QWidget()
        network_layout = QtWidgets.QGridLayout(network_widget)
        network_layout.setSpacing(25)
        network_layout.setContentsMargins(20, 20, 20, 20)
        
        # Major Indian railway stations
        stations = [
            ("New Delhi", 0, 1, "#343a40", "Main Terminal"),
            ("Mumbai Central", 1, 0, "#495057", "Western Hub"),
            ("Kolkata", 2, 1, "#495057", "Eastern Gateway"),
            ("Chennai Central", 1, 2, "#495057", "Southern Hub"),
            ("Bangalore", 2, 0, "#6c757d", "Tech City"),
            ("Hyderabad", 0, 2, "#6c757d", "Central Junction"),
            ("Pune Junction", 1, 1, "#343a40", "Express Hub"),
            ("Ahmedabad", 0, 0, "#6c757d", "Western Junction"),
            ("Lucknow", 2, 2, "#6c757d", "Northern Terminal")
        ]
        
        self.station_widgets = {}
        
        for name, row, col, color, description in stations:
            station_box = QtWidgets.QFrame()
            station_box.setFixedSize(140, 80)
            station_box.setStyleSheet(f"""
                QFrame {{
                    background-color: white;
                    border: 2px solid {color};
                    border-radius: 8px;
                    margin: 5px;
                }}
                QFrame:hover {{
                    background-color: #f8f9fa;
                    border-color: #343a40;
                    border-width: 3px;
                }}
            """)
            
            station_layout = QtWidgets.QVBoxLayout(station_box)
            station_layout.setContentsMargins(8, 8, 8, 8)
            station_layout.setSpacing(4)
            
            # Station name
            station_label = QtWidgets.QLabel(name)
            station_label.setAlignment(Qt.AlignCenter)
            station_label.setWordWrap(True)
            station_label.setStyleSheet(f"font-size: 12px; font-weight: bold; color: {color};")
            station_layout.addWidget(station_label)
            
            # Station description
            desc_label = QtWidgets.QLabel(description)
            desc_label.setAlignment(Qt.AlignCenter)
            desc_label.setStyleSheet("font-size: 10px; color: #6c757d; font-style: italic;")
            station_layout.addWidget(desc_label)
            
            # Add click functionality
            station_box.mousePressEvent = lambda event, station=name, desc=description: self.onStationClicked(station, desc)
            station_box.setCursor(Qt.PointingHandCursor)
            
            self.station_widgets[name] = station_box
            network_layout.addWidget(station_box, row, col)
        
        map_layout.addWidget(network_widget)
        
        # Bottom status and link panel
        bottom_panel = QtWidgets.QWidget()
        bottom_layout = QtWidgets.QHBoxLayout(bottom_panel)
        bottom_layout.setContentsMargins(10, 5, 10, 5)
        
        # Network status
        status_label = QtWidgets.QLabel("● Network Status: Operational")
        status_label.setStyleSheet("color: #495057; font-weight: bold; font-size: 12px;")
        bottom_layout.addWidget(status_label)
        
        bottom_layout.addStretch()
        
        # Online map link
        online_btn = QtWidgets.QPushButton("View Full OpenRailwayMap")
        online_btn.clicked.connect(self.openOnlineMap)
        online_btn.setStyleSheet("""
            QPushButton {
                background-color: #495057;
                border: 1px solid #495057;
                border-radius: 4px;
                padding: 8px 16px;
                color: white;
                font-weight: 500;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #343a40;
            }
        """)
        bottom_layout.addWidget(online_btn)
        
        map_layout.addWidget(bottom_panel)
        layout.addWidget(map_frame)
        
    def onStationClicked(self, station_name, description):
        """Handle station click"""
        QtWidgets.QMessageBox.information(
            self, "Railway Station", 
            f"Station: {station_name}\nType: {description}\n\nClick to view detailed station information, train schedules, and platform status."
        )
        
    def openOnlineMap(self):
        """Open OpenRailwayMap in external browser"""
        import webbrowser
        webbrowser.open("https://openrailwaymap.app/#view=11.62/23.2703/77.403")
        
    def loadDummyData(self):
        """Load dummy sections data"""
        try:
            data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'dummy_data.json')
            # Simplified - no need to load sections data for map-only view
            pass
        except Exception as e:
            print(f"Error loading dummy data: {e}")


class TrainManagementWidget(QtWidgets.QWidget):
    """Comprehensive train management system"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.trains_data = []
        self.selected_train = None
        self.setupUI()
        self.loadDummyData()
        
    def setupUI(self):
        """Setup train management UI with anti-cropping layout"""
        layout = QtWidgets.QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)  # Reduced margins for more space
        layout.setSpacing(15)  # Reduced spacing
        
        # Left panel - Train list (responsive width)
        left_panel = QtWidgets.QWidget()
        left_panel.setMinimumWidth(320)  # Minimum required width
        left_panel.setMaximumWidth(400)  # Maximum to prevent it from growing too large
        left_panel.setSizePolicy(QtWidgets.QSizePolicy.Preferred, QtWidgets.QSizePolicy.Expanding)
        left_layout = QtWidgets.QVBoxLayout(left_panel)
        left_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins
        
        trains_label = QtWidgets.QLabel("Active Trains")
        trains_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #495057; margin-bottom: 10px;")
        left_layout.addWidget(trains_label)
        
        self.trains_table = QtWidgets.QTableWidget()
        self.trains_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.trains_table.selectionModel().selectionChanged.connect(self.onTrainSelected)
        # Ensure table expands within its panel
        self.trains_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        left_layout.addWidget(self.trains_table)
        
        layout.addWidget(left_panel)
        
        # Right panel - Train details and controls (fully expanding)
        right_panel = QtWidgets.QWidget() 
        right_panel.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        right_panel.setMinimumWidth(450)  # Increased minimum width to prevent cropping
        right_layout = QtWidgets.QVBoxLayout(right_panel)
        right_layout.setContentsMargins(8, 8, 8, 8)  # Reduced margins for more space
        
        details_label = QtWidgets.QLabel("Train Details & Controls")
        details_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #495057;")
        right_layout.addWidget(details_label)
        
        # Details display
        self.details_widget = QtWidgets.QScrollArea()
        self.details_content = QtWidgets.QWidget()
        self.details_layout = QtWidgets.QVBoxLayout(self.details_content)
        self.details_widget.setWidget(self.details_content)
        self.details_widget.setWidgetResizable(True)
        right_layout.addWidget(self.details_widget)
        
        # Control buttons
        controls_frame = QtWidgets.QFrame()
        controls_frame.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        controls_layout = QtWidgets.QHBoxLayout(controls_frame)
        
        self.accept_btn = QtWidgets.QPushButton("Accept Route")
        self.reroute_btn = QtWidgets.QPushButton("Reroute")
        self.halt_btn = QtWidgets.QPushButton("Halt")
        self.ai_hint_btn = QtWidgets.QPushButton("AI Hints")
        
        for btn in [self.accept_btn, self.reroute_btn, self.halt_btn, self.ai_hint_btn]:
            btn.setMinimumHeight(35)
            controls_layout.addWidget(btn)
            
        right_layout.addWidget(controls_frame)
        
        layout.addWidget(right_panel)
        
        # Set layout proportions to prevent cropping
        layout.setStretch(0, 1)  # Left panel gets some flexibility
        layout.setStretch(1, 2)  # Right panel gets more space priority
        
    def loadDummyData(self):
        """Load dummy train data"""
        try:
            data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'dummy_data.json')
            with open(data_file, 'r') as f:
                data = json.load(f)
                self.trains_data = data.get('trains', [])
                self.updateTrainsTable()
        except Exception as e:
            print(f"Error loading dummy data: {e}")
            
    def updateTrainsTable(self):
        """Update the trains table"""
        self.trains_table.setRowCount(len(self.trains_data))
        self.trains_table.setColumnCount(4)
        self.trains_table.setHorizontalHeaderLabels(["Train ID", "Status", "Speed", "Delay"])
        
        for row, train in enumerate(self.trains_data):
            self.trains_table.setItem(row, 0, QtWidgets.QTableWidgetItem(train['id']))
            self.trains_table.setItem(row, 1, QtWidgets.QTableWidgetItem(train['status']))
            self.trains_table.setItem(row, 2, QtWidgets.QTableWidgetItem(f"{train['speed']} km/h"))
            self.trains_table.setItem(row, 3, QtWidgets.QTableWidgetItem(f"{train['delay']} min"))
            
        # Fix right-side cropping - ensure table uses full width with proper column distribution
        header = self.trains_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # Train ID
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Status (expandable)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Speed
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Delay
        header.setStretchLastSection(False)  # Let us control the sizing manually
        
    def onTrainSelected(self):
        """Handle train selection"""
        current_row = self.trains_table.currentRow()
        if current_row >= 0 and current_row < len(self.trains_data):
            self.selected_train = self.trains_data[current_row]
            self.updateTrainDetails()
            
    def updateTrainDetails(self):
        """Update train details panel"""
        # Clear existing details
        for i in reversed(range(self.details_layout.count())):
            child = self.details_layout.itemAt(i).widget()
            if child:
                child.deleteLater()
                
        if not self.selected_train:
            return
            
        train = self.selected_train
        
        # Basic info
        basic_group = QtWidgets.QGroupBox("Basic Information")
        basic_layout = QtWidgets.QFormLayout(basic_group)
        
        basic_layout.addRow("Train ID:", QtWidgets.QLabel(train['id']))
        basic_layout.addRow("Service Code:", QtWidgets.QLabel(train['serviceCode']))
        basic_layout.addRow("Current Section:", QtWidgets.QLabel(train['currentSection']))
        basic_layout.addRow("Status:", QtWidgets.QLabel(train['status']))
        basic_layout.addRow("Current Speed:", QtWidgets.QLabel(f"{train['speed']} km/h"))
        basic_layout.addRow("Delay:", QtWidgets.QLabel(f"{train['delay']} minutes"))
        
        self.details_layout.addWidget(basic_group)
        
        # Route info
        route_group = QtWidgets.QGroupBox("Route Information")
        route_layout = QtWidgets.QVBoxLayout(route_group)
        
        route_text = " → ".join(train['route'])
        route_layout.addWidget(QtWidgets.QLabel(f"Planned Route: {route_text}"))
        
        # Next stops
        stops_label = QtWidgets.QLabel("Next Stops:")
        stops_label.setStyleSheet("font-weight: bold;")
        route_layout.addWidget(stops_label)
        
        for stop in train['nextStops']:
            stop_text = f"• {stop['station']} - Platform {stop['platform']} at {stop['scheduledTime']}"
            route_layout.addWidget(QtWidgets.QLabel(stop_text))
            
        self.details_layout.addWidget(route_group)
        
        # Specifications
        specs_group = QtWidgets.QGroupBox("Train Specifications")
        specs_layout = QtWidgets.QFormLayout(specs_group)
        
        specs = train['specs']
        specs_layout.addRow("Type:", QtWidgets.QLabel(specs['type']))
        specs_layout.addRow("Length:", QtWidgets.QLabel(f"{specs['length']}m"))
        specs_layout.addRow("Weight:", QtWidgets.QLabel(f"{specs['weight']}t"))
        specs_layout.addRow("Passengers:", QtWidgets.QLabel(f"{specs['passengers']}/{specs['maxPassengers']}"))
        
        self.details_layout.addWidget(specs_group)


class SystemStatusWidget(QtWidgets.QWidget):
    """System status view for signals and maintenance"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals_data = []
        self.setupUI()
        self.loadDummyData()
        
    def setupUI(self):
        """Setup system status UI with proper layout"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # Header
        header = QtWidgets.QLabel("System Status Monitor")
        header.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057; margin-bottom: 10px;")
        layout.addWidget(header)
        
        # Signals table
        signals_group = QtWidgets.QGroupBox("Traffic Signals")
        signals_group.setStyleSheet("QGroupBox { font-weight: bold; color: #495057; }")
        signals_layout = QtWidgets.QVBoxLayout(signals_group)
        signals_layout.setContentsMargins(10, 15, 10, 10)
        
        self.signals_table = QtWidgets.QTableWidget()
        self.signals_table.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        signals_layout.addWidget(self.signals_table)
        
        # Control buttons
        controls_frame = QtWidgets.QFrame()
        controls_frame.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        controls_frame.setStyleSheet("QFrame { background-color: #f8f9fa; border-radius: 4px; }")
        controls_layout = QtWidgets.QHBoxLayout(controls_frame)
        controls_layout.setContentsMargins(10, 8, 10, 8)
        
        self.change_signal_btn = QtWidgets.QPushButton("Change Signal Status")
        self.maintenance_btn = QtWidgets.QPushButton("Mark for Maintenance")
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        
        button_style = """
            QPushButton {
                background-color: white;
                border: 1px solid #ced4da;
                border-radius: 3px;
                padding: 8px 12px;
                color: #495057;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e9ecef;
            }
        """
        
        for btn in [self.change_signal_btn, self.maintenance_btn, self.refresh_btn]:
            btn.setMinimumHeight(35)
            btn.setStyleSheet(button_style)
            controls_layout.addWidget(btn)
            
        signals_layout.addWidget(controls_frame)
        layout.addWidget(signals_group)
        
    def loadDummyData(self):
        """Load dummy signals data"""
        try:
            data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'dummy_data.json')
            with open(data_file, 'r') as f:
                data = json.load(f)
                self.signals_data = data.get('signals', [])
                self.updateSignalsTable()
        except Exception as e:
            print(f"Error loading dummy data: {e}")
            
    def updateSignalsTable(self):
        """Update the signals table"""
        self.signals_table.setRowCount(len(self.signals_data))
        self.signals_table.setColumnCount(5)
        self.signals_table.setHorizontalHeaderLabels(["Signal ID", "Name", "Status", "Type", "Last Changed"])
        
        for row, signal in enumerate(self.signals_data):
            self.signals_table.setItem(row, 0, QtWidgets.QTableWidgetItem(signal['id']))
            self.signals_table.setItem(row, 1, QtWidgets.QTableWidgetItem(signal['name']))
            
            # Status with color coding
            status_item = QtWidgets.QTableWidgetItem(signal['status'])
            if signal['status'] == 'GREEN':
                status_item.setBackground(QtGui.QColor(200, 255, 200))
            elif signal['status'] == 'RED':
                status_item.setBackground(QtGui.QColor(255, 200, 200))
            elif signal['status'] == 'YELLOW':
                status_item.setBackground(QtGui.QColor(255, 255, 200))
                
            self.signals_table.setItem(row, 2, status_item)
            self.signals_table.setItem(row, 3, QtWidgets.QTableWidgetItem(signal['type']))
            self.signals_table.setItem(row, 4, QtWidgets.QTableWidgetItem(signal['lastChanged']))
            
        # Fix right-side cropping - ensure table uses full width with proper column distribution
        header = self.signals_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # Signal ID
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Name (expandable)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)  # Last Changed
        header.setStretchLastSection(False)  # Manual control
