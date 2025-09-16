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
    """Interactive map overview showing OpenRailwayMap"""
    
    # Signal for section selection (kept for compatibility)
    sectionSelected = QtCore.pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()
        
    def setupUI(self):
        """Setup map overview UI - embedded Leaflet map (lightweight)"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if WEB_ENGINE_AVAILABLE:
            try:
                self.map_view = QtWebEngineWidgets.QWebEngineView()
                self.map_view.setContextMenuPolicy(Qt.NoContextMenu)

                # Tweak settings for stability
                settings = self.map_view.settings()
                try:
                    settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.JavascriptEnabled, True)
                    settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.LocalStorageEnabled, True)
                    # Disable WebGL to avoid potential GPU-related crashes
                    settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.WebGLEnabled, False)
                except Exception:
                    pass

                # Load a very small Leaflet app that overlays OpenRailwayMap tiles
                self.map_view.setHtml(self.generateLeafletHtml(), QtCore.QUrl("https://local.map/"))
                layout.addWidget(self.map_view)
                return
            except Exception:
                # If anything goes wrong, fall back to browser open UI
                pass

        # Fallback if web engine is not available or failed
        self.createFallbackUI(layout)
        
    def createFallbackUI(self, layout):
        """Create fallback UI that opens map in browser"""
        fallback_widget = QtWidgets.QWidget()
        fallback_layout = QtWidgets.QVBoxLayout(fallback_widget)
        fallback_layout.setContentsMargins(50, 50, 50, 50)
        fallback_layout.setSpacing(30)
        
        # Header section
        header_widget = QtWidgets.QWidget()
        header_layout = QtWidgets.QVBoxLayout(header_widget)
        header_layout.setSpacing(15)
        
        # Map icon/title
        title_label = QtWidgets.QLabel("🗺️ Railway Network Map")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #495057;")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label)
        
        # Description
        desc_label = QtWidgets.QLabel("View detailed railway infrastructure, signals, and network topology")
        desc_label.setStyleSheet("font-size: 16px; color: #6c757d; margin: 10px;")
        desc_label.setAlignment(Qt.AlignCenter)
        desc_label.setWordWrap(True)
        header_layout.addWidget(desc_label)
        
        fallback_layout.addWidget(header_widget)
        fallback_layout.addStretch()
        
        # Features section
        features_widget = QtWidgets.QWidget()
        features_layout = QtWidgets.QVBoxLayout(features_widget)
        features_layout.setSpacing(15)
        
        features_title = QtWidgets.QLabel("Map Features")
        features_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #495057;")
        features_title.setAlignment(Qt.AlignCenter)
        features_layout.addWidget(features_title)
        
        features = [
            "🚂 Railway infrastructure and tracks",
            "⚡ Electrification status",
            "🚥 Signal systems and controls", 
            "📊 Speed limits and gauges",
            "🏢 Stations and platforms",
            "🔄 Real-time network status"
        ]
        
        for feature in features:
            feature_label = QtWidgets.QLabel(feature)
            feature_label.setStyleSheet("font-size: 14px; color: #495057; margin: 5px;")
            feature_label.setAlignment(Qt.AlignCenter)
            features_layout.addWidget(feature_label)
            
        fallback_layout.addWidget(features_widget)
        fallback_layout.addStretch()
        
        # Action buttons
        buttons_widget = QtWidgets.QWidget()
        buttons_layout = QtWidgets.QVBoxLayout(buttons_widget)
        buttons_layout.setSpacing(15)
        
        # Primary button - Open full map
        open_btn = QtWidgets.QPushButton("🌐 Open Interactive Map")
        open_btn.clicked.connect(self.openOnlineMap)
        open_btn.setStyleSheet("""
            QPushButton {
                background-color: #495057;
                border: 1px solid #495057;
                border-radius: 6px;
                padding: 15px 30px;
                color: white;
                font-weight: 600;
                font-size: 16px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #343a40;
                transform: translateY(-1px);
            }
        """)
        buttons_layout.addWidget(open_btn, 0, Qt.AlignCenter)
        
        # Secondary info
        info_label = QtWidgets.QLabel("Opens OpenRailwayMap in your default browser for best performance")
        info_label.setStyleSheet("font-size: 12px; color: #868e96; font-style: italic;")
        info_label.setAlignment(Qt.AlignCenter)
        buttons_layout.addWidget(info_label)
        
        fallback_layout.addWidget(buttons_widget)
        fallback_layout.addStretch()
        
        layout.addWidget(fallback_widget)
        
    def generateLeafletHtml(self):
        """Return minimal HTML embedding Leaflet with OpenRailwayMap overlay only."""
        # Center over Bhopal area (23.2703, 77.403) with ~11.62 zoom as requested
        html = """<!DOCTYPE html>
<html lang=\"en\">
  <head>
    <meta charset=\"utf-8\">
    <meta name=\"viewport\" content=\"width=device-width, initial-scale=1.0\">
    <title>OpenRailwayMap Embedded</title>
    <link rel=\"stylesheet\" href=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.css\" integrity=\"sha256-p4NxAoJBhIIN+hmNHrzRCf9tD/miZyoHS5obTRR9BMY=\" crossorigin=\"anonymous\" />
    <style>
      html, body, #map { height: 100%; width: 100%; margin: 0; padding: 0; }
      .leaflet-container { background: #f1f3f5; }
      /* Ensure overlay pane sits above base and remains colorful */
      .leaflet-pane.leaflet-overlay-pane { z-index: 400 !important; }
      .leaflet-pane.base-pane { z-index: 200 !important; filter: grayscale(1) brightness(0.9) contrast(1.05); }
      .leaflet-pane.overlay-pane { z-index: 450 !important; filter: saturate(1.25) contrast(1.1); }
    </style>
  </head>
  <body>
    <div id=\"map\"></div>
    <script src=\"https://unpkg.com/leaflet@1.9.4/dist/leaflet.js\" integrity=\"sha256-20nQCchB9co0qIjJZRGuk2/Z9VM+kNiyxNV1lvTlZBo=\" crossorigin=\"anonymous\"></script>
    <script>
      (function() {
        var map = L.map('map', { zoomSnap: 0.25, preferCanvas: true, zoomControl: true });
        map.setView([__LAT__, __LNG__], __ZOOM__);

        // Create separate panes so we can style base vs overlay differently
        map.createPane('base');
        map.getPane('base').classList.add('base-pane');
        map.createPane('rail');
        map.getPane('rail').classList.add('overlay-pane');

        // Base map (lightweight OSM tiles), dimmed and desaturated via CSS filter on pane
        var osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
          maxZoom: 20,
          detectRetina: true,
          pane: 'base',
          opacity: 0.85,
          attribution: '&copy; OpenStreetMap contributors'
        }).addTo(map);

        // OpenRailwayMap overlay (tracks), boosted saturation/contrast via pane styling
        var orm = L.tileLayer('https://{s}.tiles.openrailwaymap.org/standard/{z}/{x}/{y}.png', {
          maxZoom: 20,
          detectRetina: true,
          pane: 'rail',
          opacity: 1.0,
          attribution: '&copy; OpenRailwayMap contributors'
        }).addTo(map);
      })();
    </script>
  </body>
</html>
"""
        html = html.replace("__LAT__", "23.2703").replace("__LNG__", "77.403").replace("__ZOOM__", "11.62")
        return html
        
    def openOnlineMap(self):
        """Open OpenRailwayMap in external browser"""
        import webbrowser
        webbrowser.open("https://openrailwaymap.app/#view=11.62/23.2703/77.403")


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
