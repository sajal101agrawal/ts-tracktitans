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
from ts2.utils import settings


class NavigationButton(QtWidgets.QPushButton):
    """Custom navigation button for sidebar"""
    
    def __init__(self, text, icon_type=None, parent=None):
        super().__init__(text, parent)
        self.setCheckable(True)
        self.setFixedHeight(45)
        self.original_text = text
        self.icon_type = icon_type
        self.collapsed = False
        
        # Set up icon if provided
        if icon_type:
            self.setupIcon(icon_type)
            
        # Connect to toggled signal to update icon color
        self.toggled.connect(self.updateIconColor)
        
        # Style the button with proper icon spacing
        self.setStyleSheet("""
            NavigationButton {
                background-color: transparent;
                border: none;
                text-align: left;
                padding: 8px 15px 8px 15px;
                color: #495057;
                font-size: 14px;
                font-weight: 500;
                border-radius: 6px;
                margin: 2px 8px;
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
        
    def setupIcon(self, icon_type):
        """Setup the icon based on type with custom drawn icons"""
        self.icon_type = icon_type  # Store for later recoloring
        self.updateIconColor()
        
    def updateIconColor(self):
        """Update icon color based on current button state"""
        if not hasattr(self, 'icon_type'):
            return
            
        # Use white for active/checked state, gray for inactive
        if self.isChecked():
            text_color = QtGui.QColor("#ffffff")  # White for active
        else:
            text_color = QtGui.QColor("#495057")  # Gray for inactive
        
        def draw_simulation_icon(painter, rect):
            """Draw simulation/network icon"""
            center = rect.center()
            painter.setBrush(QtGui.QBrush(painter.pen().color()))
            
            # Draw central node
            painter.drawEllipse(center, 3, 3)
            
            # Draw connected nodes
            nodes = [
                QtCore.QPoint(center.x() - 8, center.y() - 6),
                QtCore.QPoint(center.x() + 8, center.y() - 6),
                QtCore.QPoint(center.x() - 8, center.y() + 6),
                QtCore.QPoint(center.x() + 8, center.y() + 6)
            ]
            
            for node in nodes:
                painter.drawEllipse(node, 2, 2)
                painter.drawLine(center, node)
        
        def draw_map_icon(painter, rect):
            """Draw map icon"""
            # Draw folded map outline
            points = [
                QtCore.QPoint(rect.left() + 2, rect.top() + 4),
                QtCore.QPoint(rect.right() - 6, rect.top() + 2),
                QtCore.QPoint(rect.right() - 2, rect.bottom() - 6),
                QtCore.QPoint(rect.left() + 6, rect.bottom() - 2),
                QtCore.QPoint(rect.left() + 2, rect.top() + 4)
            ]
            painter.drawPolyline(points)
            
            # Draw fold lines
            painter.drawLine(rect.left() + 6, rect.top() + 2, rect.left() + 6, rect.bottom() - 2)
            painter.drawLine(rect.right() - 6, rect.top() + 2, rect.right() - 6, rect.bottom() - 2)
        
        def draw_status_icon(painter, rect):
            """Draw status/star icon"""
            center = rect.center()
            painter.setBrush(QtGui.QBrush(painter.pen().color()))
            
            # Draw simplified status indicator (circle with dot)
            painter.drawEllipse(center, 6, 6)
            
            # Use contrasting color for inner dot
            if self.isChecked():
                painter.setBrush(QtGui.QBrush(QtGui.QColor("#495057")))  # Dark dot on light background when active
            else:
                painter.setBrush(QtGui.QBrush(QtCore.Qt.white))  # Light dot on dark background when inactive
            painter.drawEllipse(center, 2, 2)
        
        def draw_analysis_icon(painter, rect):
            """Draw analysis/chart icon"""
            # Draw chart axes
            painter.drawLine(rect.left() + 2, rect.bottom() - 2, rect.right() - 2, rect.bottom() - 2)
            painter.drawLine(rect.left() + 2, rect.top() + 2, rect.left() + 2, rect.bottom() - 2)
            
            # Draw chart line
            points = [
                QtCore.QPoint(rect.left() + 4, rect.bottom() - 4),
                QtCore.QPoint(rect.left() + 8, rect.bottom() - 8),
                QtCore.QPoint(rect.left() + 12, rect.bottom() - 6),
                QtCore.QPoint(rect.right() - 4, rect.bottom() - 10)
            ]
            painter.drawPolyline(points)
            
            # Draw data points
            painter.setBrush(QtGui.QBrush(painter.pen().color()))
            for point in points:
                painter.drawEllipse(point, 2, 2)
        
        def draw_dashboard_icon(painter, rect):
            """Draw dashboard/grid icon"""
            # Draw 2x2 grid
            mid_x = rect.center().x()
            mid_y = rect.center().y()
            
            # Top-left
            painter.drawRect(rect.left() + 2, rect.top() + 2, mid_x - rect.left() - 3, mid_y - rect.top() - 3)
            # Top-right
            painter.drawRect(mid_x + 1, rect.top() + 2, rect.right() - mid_x - 3, mid_y - rect.top() - 3)
            # Bottom-left
            painter.drawRect(rect.left() + 2, mid_y + 1, mid_x - rect.left() - 3, rect.bottom() - mid_y - 3)
            # Bottom-right
            painter.drawRect(mid_x + 1, mid_y + 1, rect.right() - mid_x - 3, rect.bottom() - mid_y - 3)
        
        def draw_logs_icon(painter, rect):
            """Draw logs/document icon"""
            # Draw document outline
            doc_rect = QtCore.QRect(rect.left() + 3, rect.top() + 2, rect.width() - 8, rect.height() - 4)
            painter.drawRect(doc_rect)
            
            # Draw folded corner
            corner_size = 4
            corner_points = [
                QtCore.QPoint(doc_rect.right() - corner_size, doc_rect.top()),
                QtCore.QPoint(doc_rect.right(), doc_rect.top() + corner_size),
                QtCore.QPoint(doc_rect.right() - corner_size, doc_rect.top() + corner_size),
                QtCore.QPoint(doc_rect.right() - corner_size, doc_rect.top())
            ]
            painter.drawPolyline(corner_points)
            
            # Draw text lines
            for i in range(3):
                y = doc_rect.top() + 6 + i * 3
                painter.drawLine(doc_rect.left() + 2, y, doc_rect.right() - 6, y)
        
        icon_functions = {
            'simulation': draw_simulation_icon,
            'map': draw_map_icon,
            'status': draw_status_icon,
            'analysis': draw_analysis_icon,
            'dashboard': draw_dashboard_icon,
            'logs': draw_logs_icon
        }
        
        if self.icon_type in icon_functions:
            # Create pixmap with proper size
            size = 20
            pixmap = QtGui.QPixmap(size, size)
            pixmap.fill(QtCore.Qt.transparent)
            
            # Create painter and set up styling
            painter = QtGui.QPainter(pixmap)
            painter.setRenderHint(QtGui.QPainter.Antialiasing)
            
            # Use current text color for the icon
            pen = QtGui.QPen(text_color)
            pen.setWidth(2)
            pen.setCapStyle(QtCore.Qt.RoundCap)
            pen.setJoinStyle(QtCore.Qt.RoundJoin)
            painter.setPen(pen)
            
            # Draw the icon
            rect = pixmap.rect().adjusted(2, 2, -2, -2)  # Add some padding
            icon_functions[self.icon_type](painter, rect)
            
            painter.end()
            
            # Create icon and set it
            icon = QtGui.QIcon(pixmap)
            self.setIcon(icon)
            self.setIconSize(QtCore.QSize(20, 20))
        
    def setCollapsed(self, collapsed):
        """Set the button to collapsed (icon-only) or expanded (text) state"""
        self.collapsed = collapsed
        if collapsed:
            self.setText("")  # Hide text, show only icon
            self.setToolTip(self.original_text)
            self.setStyleSheet("""
                NavigationButton {
                    background-color: transparent;
                    border: none;
                    text-align: center;
                    padding: 10px;
                    color: #495057;
                    font-size: 16px;
                    font-weight: 500;
                    border-radius: 6px;
                    margin: 2px 8px;
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
            # Update icon color for collapsed state
            self.updateIconColor()
        else:
            self.setText(self.original_text)  # Show text with icon
            self.setToolTip("")
            self.setStyleSheet("""
                NavigationButton {
                    background-color: transparent;
                    border: none;
                    text-align: left;
                    padding: 8px 15px 8px 15px;
                    color: #495057;
                    font-size: 14px;
                    font-weight: 500;
                    border-radius: 6px;
                    margin: 2px 8px;
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
            # Update icon color for expanded state
            self.updateIconColor()


class SidebarNavigation(QtWidgets.QWidget):
    """Modern left sidebar navigation panel"""
    
    # Signals for view changes
    viewChanged = QtCore.pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.expanded_width = 250
        self.collapsed_width = 60
        self.nav_buttons = []
        
        # Load collapsed state from settings
        self.collapsed = settings.value("sidebar_collapsed", False, type=bool)
        
        self.setupUI()
        
        # Apply initial state after UI is set up
        if self.collapsed:
            self.setFixedWidth(self.collapsed_width)
            self.toggle_btn.setText("▶")
            self.updateCollapsedState()
        else:
            self.setFixedWidth(self.expanded_width)
            self.toggle_btn.setText("◀")
        
    def setupUI(self):
        """Setup the sidebar UI"""
        # Width will be set in __init__ after setupUI completes
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
        
        # Header with toggle button
        header = QtWidgets.QWidget()
        header.setStyleSheet("""
            background-color: #343a40;
            color: white;
            padding: 10px;
        """)
        header.setFixedHeight(80)
        
        header_layout = QtWidgets.QHBoxLayout(header)
        header_layout.setContentsMargins(5, 8, 5, 8)
        header_layout.setSpacing(4)
        
        # Left side - Title (initially visible)
        left_container = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)
        
        self.title_label = QtWidgets.QLabel("TrackTitans")
        self.title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        self.title_label.setAlignment(Qt.AlignCenter)
        left_layout.addWidget(self.title_label)
        
        header_layout.addWidget(left_container)
        
        # Right side - Toggle button
        self.toggle_btn = QtWidgets.QPushButton("◀")
        self.toggle_btn.setFixedSize(30, 30)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                border: 1px solid #6c757d;
                border-radius: 15px;
                color: white;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.1);
                border-color: #adb5bd;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.2);
            }
        """)
        self.toggle_btn.clicked.connect(self.toggleCollapsed)
        header_layout.addWidget(self.toggle_btn)
        
        layout.addWidget(header)
        
        # Navigation buttons
        self.button_group = QtWidgets.QButtonGroup()
        self.button_group.setExclusive(True)
        
        nav_container = QtWidgets.QWidget()
        nav_layout = QtWidgets.QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(0, 10, 0, 0)
        nav_layout.setSpacing(2)
        
        # Define navigation items with proper Qt icons
        nav_items = [
            ("simulation", "Section view", "simulation"),
            ("map_view", "Map View", "map"),
            ("system_status", "System Status", "status"), 
            ("whatif_analysis", "What-If Analysis", "analysis"),
            ("kpi_dashboard", "KPI Dashboard", "dashboard"),
            ("audit_logs", "Audit Logs", "logs")
        ]
        
        for view_name, display_text, icon_type in nav_items:
            button = NavigationButton(display_text, icon_type)
            button.clicked.connect(lambda checked, name=view_name: self.onButtonClicked(name))
            self.button_group.addButton(button)
            self.nav_buttons.append(button)
            nav_layout.addWidget(button)
            
        # Set simulation as default active
        self.button_group.buttons()[0].setChecked(True)
        
        nav_layout.addStretch()
        layout.addWidget(nav_container)
        
        # Status indicator at bottom
        self.status_widget = QtWidgets.QWidget()
        self.status_widget.setFixedHeight(40)
        self.status_widget.setStyleSheet("background-color: #e9ecef; border-top: 1px solid #dee2e6;")
        
        self.status_layout = QtWidgets.QHBoxLayout(self.status_widget)
        
        self.connection_status = QtWidgets.QLabel("● Connected")
        self.connection_status.setStyleSheet("color: #28a745; font-size: 12px;")
        self.status_layout.addWidget(self.connection_status)
        
        layout.addWidget(self.status_widget)
        
    def onButtonClicked(self, view_name):
        """Handle navigation button clicks"""
        self.viewChanged.emit(view_name)
        
    def toggleCollapsed(self):
        """Toggle the sidebar between collapsed and expanded states"""
        self.collapsed = not self.collapsed
        
        # Save state to settings
        settings.setValue("sidebar_collapsed", self.collapsed)
        
        if self.collapsed:
            # Collapsing - set to collapsed width
            self.setFixedWidth(self.collapsed_width)
            self.toggle_btn.setText("▶")
            self.updateCollapsedState()
        else:
            # Expanding - set to expanded width
            self.setFixedWidth(self.expanded_width)
            self.toggle_btn.setText("◀")
            self.updateExpandedState()
            
    def updateCollapsedState(self):
        """Update UI for collapsed state"""
        # Hide title text, only show toggle button
        self.title_label.setVisible(False)
        
        # Update all navigation buttons to icon-only mode
        for button in self.nav_buttons:
            button.setCollapsed(True)
            
        # Hide connection status text in collapsed mode
        self.connection_status.setText("●")
        self.connection_status.setToolTip("Connection Status")
        
    def updateExpandedState(self):
        """Update UI for expanded state"""
        # Show title text
        self.title_label.setVisible(True)
        
        # Update all navigation buttons to text mode
        for button in self.nav_buttons:
            button.setCollapsed(False)
            
        # Show full connection status
        self.connection_status.setToolTip("")
        # Restore the connection text based on current status
        current_style = self.connection_status.styleSheet()
        if "#28a745" in current_style:
            self.connection_status.setText("● Connected")
        else:
            self.connection_status.setText("● Disconnected")
        
    def setConnectionStatus(self, connected):
        """Update connection status indicator"""
        if connected:
            if self.collapsed:
                self.connection_status.setText("●")
                self.connection_status.setToolTip("Connected")
            else:
                self.connection_status.setText("● Connected")
                self.connection_status.setToolTip("")
            self.connection_status.setStyleSheet("color: #28a745; font-size: 12px;")
        else:
            if self.collapsed:
                self.connection_status.setText("●")
                self.connection_status.setToolTip("Disconnected")
            else:
                self.connection_status.setText("● Disconnected")
                self.connection_status.setToolTip("")
            self.connection_status.setStyleSheet("color: #dc3545; font-size: 12px;")


class MapOverviewWidget(QtWidgets.QWidget):
    """Interactive map overview showing OpenRailwayMap"""
    
    # Signal for section selection (kept for compatibility)
    sectionSelected = QtCore.pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setupUI()
        
    def setupUI(self):
        """Setup map overview UI with tabbed interface for different maps"""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        if WEB_ENGINE_AVAILABLE:
            # Check Qt WebEngine version
            try:
                from Qt import QtWebEngineCore
                print(f"Qt WebEngine version: {QtWebEngineCore.qWebEngineVersion()}")
            except:
                print("Could not determine Qt WebEngine version")
                
            try:
                # Create tab widget for different map types
                self.tab_widget = QtWidgets.QTabWidget()
                self.tab_widget.setStyleSheet("""
                    QTabWidget::pane {
                        border: 1px solid #c0c0c0;
                        background-color: white;
                    }
                    QTabBar::tab {
                        background-color: #f0f0f0;
                        border: 1px solid #c0c0c0;
                        padding: 8px 16px;
                        margin-right: 2px;
                    }
                    QTabBar::tab:selected {
                        background-color: white;
                        border-bottom-color: white;
                    }
                    QTabBar::tab:hover:!selected {
                        background-color: #e0e0e0;
                    }
                """)
                
                # Create a custom profile to avoid database conflicts
                import tempfile
                import os
                
                self.profile = QtWebEngineWidgets.QWebEngineProfile(f"ts2_map_profile_{os.getpid()}")
                
                # Set a unique cache directory to prevent SQLite locking issues
                cache_dir = os.path.join(tempfile.gettempdir(), f"ts2_webengine_{os.getpid()}")
                self.profile.setCachePath(cache_dir)
                self.profile.setPersistentStoragePath(cache_dir)
                
                # Create web page with the profile
                page = QtWebEngineWidgets.QWebEnginePage(self.profile)
                self.map_view = QtWebEngineWidgets.QWebEngineView()
                self.map_view.setPage(page)
                self.map_view.setContextMenuPolicy(Qt.NoContextMenu)

                # Tweak settings for stability and to prevent database conflicts
                settings = self.map_view.settings()
                try:
                    settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.JavascriptEnabled, True)
                    settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.LocalStorageEnabled, False)  # Disable to prevent DB conflicts
                    settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.WebGLEnabled, False)  # Disable WebGL
                    settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.WebSecurityEnabled, False)
                except Exception:
                    pass

                # Create separate profile for Railway map to avoid conflicts
                self.railway_profile = QtWebEngineWidgets.QWebEngineProfile(f"ts2_railway_profile_{os.getpid()}")
                railway_cache_dir = os.path.join(tempfile.gettempdir(), f"ts2_railway_{os.getpid()}")
                self.railway_profile.setCachePath(railway_cache_dir)
                self.railway_profile.setPersistentStoragePath(railway_cache_dir)
                
                # Create second web view for Railway map with its own profile
                railway_page = QtWebEngineWidgets.QWebEnginePage(self.railway_profile)
                self.railway_map_view = QtWebEngineWidgets.QWebEngineView()
                self.railway_map_view.setPage(railway_page)
                self.railway_map_view.setContextMenuPolicy(Qt.NoContextMenu)
                
                # Apply all necessary settings for external site compatibility
                railway_settings = self.railway_map_view.settings()
                try:
                    # Essential settings
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.JavascriptEnabled, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.LocalStorageEnabled, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.WebGLEnabled, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.PluginsEnabled, True)
                    
                    # Additional settings for compatibility
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.AutoLoadImages, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.JavascriptCanAccessClipboard, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.LinksIncludedInFocusChain, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.LocalContentCanAccessRemoteUrls, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.LocalContentCanAccessFileUrls, False)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.XSSAuditingEnabled, False)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.SpatialNavigationEnabled, False)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.HyperlinkAuditingEnabled, False)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.ScrollAnimatorEnabled, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.ErrorPageEnabled, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.FullScreenSupportEnabled, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.ScreenCaptureEnabled, False)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.WebGLEnabled, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.Accelerated2dCanvasEnabled, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.AutoLoadIconsForPage, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.TouchIconsEnabled, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.FocusOnNavigationEnabled, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.PrintElementBackgrounds, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.AllowRunningInsecureContent, False)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.AllowGeolocationOnInsecureOrigins, False)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.JavascriptCanOpenWindows, False)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.JavascriptCanPaste, True)
                    railway_settings.setAttribute(QtWebEngineWidgets.QWebEngineSettings.WebRTCPublicInterfacesOnly, False)
                    
                    # Set default font sizes
                    railway_settings.setFontSize(QtWebEngineWidgets.QWebEngineSettings.MinimumFontSize, 8)
                    railway_settings.setFontSize(QtWebEngineWidgets.QWebEngineSettings.DefaultFontSize, 16)
                    railway_settings.setFontSize(QtWebEngineWidgets.QWebEngineSettings.DefaultFixedFontSize, 13)
                except Exception as e:
                    print(f"Warning: Some web engine settings could not be applied: {e}")

                # Add map tabs
                self.tab_widget.addTab(self.map_view, "🗺️ OpenRailwayMap")
                self.tab_widget.addTab(self.railway_map_view, "🚂 Railway Infrastructure")
                
                # Connect tab change event
                self.tab_widget.currentChanged.connect(self.onTabChanged)
                
                # Load default map (OpenRailwayMap)
                self.loadOpenRailwayMap()
                
                # Pre-load the Railway map to check if it works
                print("Pre-loading Railway Infrastructure Map...")
                self.railway_map_view.setUrl(QtCore.QUrl("https://rail-map.up.railway.app/"))
                
                layout.addWidget(self.tab_widget)
                return
            except Exception as e:
                print(f"WebEngine failed to initialize: {e}")
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
        
        # Primary button - Open OpenRailwayMap
        open_btn = QtWidgets.QPushButton("🗺️ Open OpenRailwayMap")
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
            }
        """)
        buttons_layout.addWidget(open_btn, 0, Qt.AlignCenter)
        
        # Secondary button - Open Railway Infrastructure Map
        railway_btn = QtWidgets.QPushButton("🚂 Open Railway Infrastructure Map")
        railway_btn.clicked.connect(self.openRailwayInfrastructureMap)
        railway_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                border: 1px solid #28a745;
                border-radius: 6px;
                padding: 15px 30px;
                color: white;
                font-weight: 600;
                font-size: 16px;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        buttons_layout.addWidget(railway_btn, 0, Qt.AlignCenter)
        
        # Info labels
        info_label = QtWidgets.QLabel("Opens maps in your default browser for best performance")
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
        
    def openRailwayInfrastructureMap(self):
        """Open Railway Infrastructure Map in external browser"""
        import webbrowser
        webbrowser.open("https://rail-map.up.railway.app/")
        
    def testWebEngineCapabilities(self):
        """Test if WebEngine can load external content properly"""
        if hasattr(self, 'railway_map_view'):
            test_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <title>WebEngine Test</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    .status { margin: 10px 0; padding: 10px; background: #f0f0f0; }
                </style>
            </head>
            <body>
                <h1>WebEngine Capability Test</h1>
                <div class="status">JavaScript: <span id="js-status">Checking...</span></div>
                <div class="status">WebGL: <span id="webgl-status">Checking...</span></div>
                <div class="status">Canvas: <span id="canvas-status">Checking...</span></div>
                <div class="status">LocalStorage: <span id="storage-status">Checking...</span></div>
                <div class="status">External Resources: <span id="external-status">Checking...</span></div>
                
                <h2>Loading External Site</h2>
                <p>Attempting to load Railway Infrastructure Map in 3 seconds...</p>
                
                <script>
                    // Test JavaScript
                    document.getElementById('js-status').textContent = 'Working ✓';
                    
                    // Test WebGL
                    try {
                        var canvas = document.createElement('canvas');
                        var gl = canvas.getContext('webgl') || canvas.getContext('experimental-webgl');
                        document.getElementById('webgl-status').textContent = gl ? 'Working ✓' : 'Not available ✗';
                    } catch(e) {
                        document.getElementById('webgl-status').textContent = 'Error: ' + e.message;
                    }
                    
                    // Test Canvas
                    try {
                        var canvas2d = document.createElement('canvas').getContext('2d');
                        document.getElementById('canvas-status').textContent = canvas2d ? 'Working ✓' : 'Not available ✗';
                    } catch(e) {
                        document.getElementById('canvas-status').textContent = 'Error: ' + e.message;
                    }
                    
                    // Test LocalStorage
                    try {
                        localStorage.setItem('test', 'value');
                        localStorage.removeItem('test');
                        document.getElementById('storage-status').textContent = 'Working ✓';
                    } catch(e) {
                        document.getElementById('storage-status').textContent = 'Not available: ' + e.message;
                    }
                    
                    // Test external resources
                    fetch('https://api.github.com/rate_limit')
                        .then(response => response.json())
                        .then(data => {
                            document.getElementById('external-status').textContent = 'Working ✓ (Can fetch external APIs)';
                        })
                        .catch(error => {
                            document.getElementById('external-status').textContent = 'Failed: ' + error.message;
                        });
                    
                    // Redirect after 3 seconds
                    setTimeout(function() {
                        window.location.href = 'https://rail-map.up.railway.app/';
                    }, 3000);
                </script>
            </body>
            </html>
            """
            self.railway_map_view.setHtml(test_html, QtCore.QUrl("https://test.local/"))
        
    def onTabChanged(self, index):
        """Handle tab change events"""
        if not hasattr(self, 'tab_widget'):
            return
            
        if index == 0:  # OpenRailwayMap tab
            self.loadOpenRailwayMap()
        elif index == 1:  # Railway Infrastructure tab
            # Run capability test first (comment this out after testing)
            # self.testWebEngineCapabilities()
            # Load the actual map
            self.loadRailwayInfrastructureMap()
            
    def loadOpenRailwayMap(self):
        """Load the OpenRailwayMap using Leaflet"""
        if hasattr(self, 'map_view'):
            self.map_view.setHtml(self.generateLeafletHtml(), QtCore.QUrl("https://local.map/"))
            
    def loadRailwayInfrastructureMap(self):
        """Load the Railway Infrastructure Map"""
        if hasattr(self, 'railway_map_view'):
            # Disconnect any existing handlers
            try:
                self.railway_map_view.loadFinished.disconnect()
                self.railway_map_view.loadProgress.disconnect()
                self.railway_map_view.loadStarted.disconnect()
            except:
                pass
            
            # Set a desktop user agent
            profile = self.railway_map_view.page().profile()
            profile.setHttpUserAgent("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
            
            # Get page for other handlers
            page = self.railway_map_view.page()
            
            # Add certificate error handler
            def handle_certificate_error(error):
                print(f"Certificate Error: {error.url().toString()}")
                error.ignoreCertificateError()
                return True
            
            page.certificateError.connect(handle_certificate_error)
            
            # Add feature permission handler
            def handle_feature_permission(url, feature):
                print(f"Feature permission requested: {feature} for {url.toString()}")
                page.setFeaturePermission(url, feature, QtWebEngineWidgets.QWebEnginePage.PermissionGrantedByUser)
            
            page.featurePermissionRequested.connect(handle_feature_permission)
            
            # Add navigation handler
            def handle_url_changed(url):
                print(f"URL changed to: {url.toString()}")
            
            self.railway_map_view.urlChanged.connect(handle_url_changed)
            
            # Add load progress handler
            def on_load_progress(progress):
                print(f"Railway Map loading progress: {progress}%")
            
            self.railway_map_view.loadProgress.connect(on_load_progress)
            
            # Add load started handler
            def on_load_started():
                print("Railway Map loading started...")
            
            self.railway_map_view.loadStarted.connect(on_load_started)
            
            # Add load finished handler with more debugging
            def on_load_finished(success):
                if success:
                    print("Railway Infrastructure Map loaded successfully")
                    # Check the actual content
                    page.runJavaScript("""
                        JSON.stringify({
                            title: document.title,
                            bodyText: document.body ? document.body.innerText.substring(0, 200) : 'no body',
                            hasCanvas: document.getElementsByTagName('canvas').length,
                            hasScripts: document.getElementsByTagName('script').length,
                            readyState: document.readyState,
                            url: window.location.href
                        })
                    """, lambda result: print(f"Page info: {result}"))
                else:
                    print("Railway Infrastructure Map failed to load")
                    # Get error details
                    page.runJavaScript("document.documentElement.outerHTML", 
                        lambda html: print(f"HTML content: {html[:500]}..." if html else "No HTML content"))
            
            self.railway_map_view.loadFinished.connect(on_load_finished)
            
            # Clear cache before loading
            profile.clearHttpCache()
            
            # Load the URL
            url = QtCore.QUrl("https://rail-map.up.railway.app/")
            print(f"Loading Railway Infrastructure Map from: {url.toString()}")
            self.railway_map_view.load(url)


class TrainManagementWidget(QtWidgets.QWidget):
    """Comprehensive train management system"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.trains_data = []
        self._base_url = "http://localhost:22222"
        self._session = None
        self.selected_train = None
        self.setupUI()
        self.loadTrainsFromApi()
        
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
        
        self.trains_table = self._create_enhanced_table()
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
        self.accept_btn.clicked.connect(self.onAcceptRoute)
        self.reroute_btn.clicked.connect(self.onReroute)
        self.halt_btn.clicked.connect(self.onHalt)
            
        right_layout.addWidget(controls_frame)
        
        layout.addWidget(right_panel)
        
        # Set layout proportions to prevent cropping
        layout.setStretch(0, 1)  # Left panel gets some flexibility
        layout.setStretch(1, 2)  # Right panel gets more space priority
        
    def _create_enhanced_table(self):
        """Create an enhanced table widget for train management"""
        table = QtWidgets.QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #f1f5f9;
                font-size: 13px;
                selection-background-color: #eff6ff;
                border-radius: 8px;
                border: 1px solid #e5e7eb;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #f1f5f9;
                color: #1e293b;
                font-weight: 500;
            }
            QTableWidget::item:selected {
                background-color: #eff6ff;
                color: #1e40af;
                border: none;
            }
            QTableWidget::item:hover {
                background-color: #f8fafc;
                color: #0f172a;
            }
            QHeaderView {
                border: none;
                background-color: transparent;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 12px 8px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                font-weight: 600;
                color: #475569;
                font-size: 12px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QHeaderView::section:horizontal {
                border-right: 1px solid #f1f5f9;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QTableWidget::item:alternate {
                background-color: #f9fafb;
            }
            QScrollBar:vertical {
                background: #f1f5f9;
                width: 8px;
                border-radius: 4px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        
        # Enhanced table properties
        table.setShowGrid(True)
        table.setAlternatingRowColors(False)  # Disable to avoid overriding colors
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        
        # Modern header styling
        header = table.horizontalHeader()
        header.setDefaultSectionSize(120)
        header.setMinimumSectionSize(80)
        header.setCascadingSectionResizes(False)
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        
        # Vertical header styling
        v_header = table.verticalHeader()
        v_header.setVisible(False)  # Hide row numbers for cleaner look
        
        return table
        
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
            
    @QtCore.pyqtSlot()
    def updateTrainsTable(self):
        """Update the trains table with enhanced styling"""
        self.trains_table.setRowCount(len(self.trains_data))
        self.trains_table.setColumnCount(4)
        self.trains_table.setHorizontalHeaderLabels(["Train ID", "Status", "Speed", "Delay"])
        
        for row, train in enumerate(self.trains_data):
            # Train ID with monospace
            id_item = QtWidgets.QTableWidgetItem(train['id'])
            id_item.setFont(QtGui.QFont("monospace"))
            self.trains_table.setItem(row, 0, id_item)
            
            # Status with color coding
            status_text = train['status']
            status_item = QtWidgets.QTableWidgetItem(status_text)
            status_item.font().setBold(True)
            
            if status_text.upper() in ['RUNNING', 'ON TIME', 'ACTIVE']:
                status_item.setForeground(QtGui.QColor("#10b981"))  # Green
                status_item.setBackground(QtGui.QColor("#ecfdf5"))
            elif status_text.upper() in ['DELAYED', 'WARNING']:
                status_item.setForeground(QtGui.QColor("#f59e0b"))  # Amber
                status_item.setBackground(QtGui.QColor("#fffbeb"))
            elif status_text.upper() in ['STOPPED', 'HALTED']:
                status_item.setForeground(QtGui.QColor("#6b7280"))  # Gray
            elif status_text.upper() in ['ERROR', 'EMERGENCY']:
                status_item.setForeground(QtGui.QColor("#ef4444"))  # Red
                status_item.setBackground(QtGui.QColor("#fef2f2"))
            else:
                status_item.setForeground(QtGui.QColor("#6b7280"))  # Default gray
                
            self.trains_table.setItem(row, 1, status_item)
            
            # Speed with color coding and monospace
            speed = train.get('speed', 0)
            speed_item = QtWidgets.QTableWidgetItem(f"{speed} km/h")
            speed_item.setFont(QtGui.QFont("monospace"))
            
            if speed > 80:
                speed_item.setForeground(QtGui.QColor("#ef4444"))  # Red for high speed
            elif speed > 40:
                speed_item.setForeground(QtGui.QColor("#f59e0b"))  # Amber for medium speed
            else:
                speed_item.setForeground(QtGui.QColor("#10b981"))  # Green for low speed
                
            self.trains_table.setItem(row, 2, speed_item)
            
            # Delay with color coding
            delay = train.get('delay', 0)
            delay_item = QtWidgets.QTableWidgetItem(f"{delay} min")
            delay_item.setFont(QtGui.QFont("monospace"))
            
            if delay > 10:
                delay_item.setForeground(QtGui.QColor("#ef4444"))  # Red for major delay
                delay_item.setBackground(QtGui.QColor("#fef2f2"))
            elif delay > 5:
                delay_item.setForeground(QtGui.QColor("#f59e0b"))  # Amber for moderate delay
                delay_item.setBackground(QtGui.QColor("#fffbeb"))
            elif delay <= 0:
                delay_item.setForeground(QtGui.QColor("#10b981"))  # Green for on time/early
                delay_item.setBackground(QtGui.QColor("#ecfdf5"))
            else:
                delay_item.setForeground(QtGui.QColor("#6b7280"))  # Gray for minor delay
                
            self.trains_table.setItem(row, 3, delay_item)
            
        # Enhanced column sizing for better readability
        header = self.trains_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # Train ID
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Status (expandable)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Speed
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Delay
        header.setStretchLastSection(False)  # Manual control
        
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

    def _http(self):
        import requests
        if self._session is None:
            self._session = requests.Session()
        return self._session

    def loadTrainsFromApi(self, section_id=None):
        """Fetch current trains for a section from the server API with fallback to dummy data."""
        import threading

        def _run():
            try:
                sid = section_id or "ALL"
                url = f"{self._base_url}/api/trains/section/{sid}"
                resp = self._http().get(url, timeout=5)
                resp.raise_for_status()
                data = resp.json()
                trains = data.get('currentTrains') or data.get('trains') or []
                self.trains_data = trains
                QtCore.QMetaObject.invokeMethod(self, "updateTrainsTable", Qt.QueuedConnection)
            except Exception as e:
                print(f"Error loading trains from API: {e}, falling back to dummy data")
                # Fallback to dummy data
                QtCore.QMetaObject.invokeMethod(self, "loadDummyData", Qt.QueuedConnection)

        threading.Thread(target=_run, daemon=True).start()

    def _post_route_action(self, action, new_route=None, reason=None):
        if not self.selected_train:
            return
        import threading
        body = {"action": action}
        if new_route:
            body["newRoute"] = new_route
        if reason:
            body["reason"] = reason

        def _run(train_id):
            try:
                url = f"{self._base_url}/api/trains/{train_id}/route"
                resp = self._http().post(url, json=body, timeout=5)
                resp.raise_for_status()
                self.loadTrainsFromApi()
                QtWidgets.QMessageBox.information(self, "Success", f"Action {action} sent for train {train_id}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Error", f"Failed to send action: {e}")

        train_id = self.selected_train.get('id') or self.selected_train.get('trainId')
        threading.Thread(target=_run, args=(train_id,), daemon=True).start()

    def onAcceptRoute(self):
        self._post_route_action("ACCEPT")

    def onReroute(self):
        text, ok = QtWidgets.QInputDialog.getText(self, "Reroute", "Enter new route as comma-separated stops:")
        if ok and text.strip():
            new_route = [s.strip() for s in text.split(',') if s.strip()]
            self._post_route_action("REROUTE", new_route=new_route, reason="Manual reroute")

    def onHalt(self):
        self._post_route_action("HALT", reason="Dispatcher halt")


class SystemStatusWidget(QtWidgets.QWidget):
    """System status view for signals and maintenance"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.signals_data = []
        self.overview_data = {}
        self._base_url = "http://localhost:22222"
        self._session = None
        self.setupUI()
        self.loadOverviewFromApi()
        
        # Auto-refresh timer (3s)
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.loadOverviewFromApi)
        self.refresh_timer.start(3000)
        
    def setupUI(self):
        """Setup enhanced system status UI with modern styling"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Set enhanced background with subtle gradient
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #fdfdfe, stop: 1 #f7f8fc);
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)

        # Simple container without scroll
        content = QtWidgets.QWidget()
        layout = QtWidgets.QVBoxLayout(content)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Minimal header row
        header_row = QtWidgets.QHBoxLayout()
        
        # System status label with clean styling
        status_label = QtWidgets.QLabel("System Status")
        status_label.setStyleSheet("""
            font-size: 18px; 
            font-weight: 700; 
            color: #1e293b;
        """)
        header_row.addWidget(status_label)
        
        header_row.addStretch()
        
        # Status dot indicator
        status_dot = QtWidgets.QLabel("●")
        status_dot.setStyleSheet("""
            color: #10b981; 
            font-size: 12px;
            margin-right: 4px;
        """)
        header_row.addWidget(status_dot)
        
        # Auto-refresh indicator with enhanced styling
        refresh_indicator = QtWidgets.QLabel("Live • 3s refresh")
        refresh_indicator.setStyleSheet("""
            color: #64748b; 
            font-size: 12px; 
            font-weight: 500;
            background-color: #f1f5f9;
            padding: 4px 8px;
            border-radius: 12px;
            border: 1px solid #e2e8f0;
        """)
        header_row.addWidget(refresh_indicator)
        
        layout.addLayout(header_row)
        
        # Simplified KPI strip
        kpi_container = QtWidgets.QWidget()
        kpi_container.setStyleSheet("""
            QWidget {
                background-color: transparent;
            }
        """)
        kpi_layout = QtWidgets.QHBoxLayout(kpi_container)
        kpi_layout.setContentsMargins(0, 0, 0, 0)
        kpi_layout.setSpacing(16)
        
        def _create_compact_kpi(title, color_accent="#6366f1"):
            kpi_widget = QtWidgets.QWidget()
            kpi_widget_layout = QtWidgets.QVBoxLayout(kpi_widget)
            kpi_widget_layout.setContentsMargins(0, 0, 0, 0)
            kpi_widget_layout.setSpacing(4)
            
            # Clean styling without borders or backgrounds
            kpi_widget.setStyleSheet(f"""
                QWidget {{
                    background-color: transparent;
                }}
            """)
            
            # Title with icon-style indicator
            title_container = QtWidgets.QHBoxLayout()
            title_indicator = QtWidgets.QLabel("◆")
            title_indicator.setStyleSheet(f"""
                color: {color_accent};
                font-size: 8px;
                margin-right: 4px;
            """)
            
            title_label = QtWidgets.QLabel(title)
            title_label.setStyleSheet("""
                font-size: 11px; 
                color: #475569; 
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            """)
            
            title_container.addWidget(title_indicator)
            title_container.addWidget(title_label)
            title_container.addStretch()
            
            kpi_widget_layout.addLayout(title_container)
            
            # Value with enhanced styling
            value_label = QtWidgets.QLabel("-")
            value_label.setStyleSheet(f"""
                font-size: 20px; 
                font-weight: 700; 
                color: #0f172a;
                margin-top: 2px;
            """)
            kpi_widget_layout.addWidget(value_label)
            
            return kpi_widget, value_label
        
        # Create KPIs with different accent colors
        util_widget, self.kpi_util_value = _create_compact_kpi("Utilization", "#6366f1")
        trains_widget, self.kpi_trains_value = _create_compact_kpi("Active Trains", "#10b981")
        signals_widget, self.kpi_signals_value = _create_compact_kpi("Signals", "#f59e0b")
        routes_widget, self.kpi_routes_value = _create_compact_kpi("Routes", "#ef4444")
        
        kpi_layout.addWidget(util_widget)
        kpi_layout.addWidget(trains_widget)
        kpi_layout.addWidget(signals_widget)
        kpi_layout.addWidget(routes_widget)
        kpi_layout.addStretch()
        
        layout.addWidget(kpi_container)
        
        # Minimal action buttons
        actions_row = QtWidgets.QHBoxLayout()
        
        self.refresh_btn = QtWidgets.QPushButton("Refresh")
        
        # Apply clean button styling
        button_style = """
            QPushButton {
                background-color: #ffffff;
                color: #475569;
                border: 1px solid #cbd5e1;
                padding: 8px 16px;
                border-radius: 8px;
                font-weight: 600;
                font-size: 13px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #f8fafc;
                border-color: #94a3b8;
                color: #334155;
            }
            QPushButton:pressed {
                background-color: #e2e8f0;
            }
        """
        
        self.refresh_btn.setStyleSheet(button_style)
        
        actions_row.addStretch()
        actions_row.addWidget(self.refresh_btn)
        
        self.refresh_btn.clicked.connect(self.loadOverviewFromApi)
            
        layout.addLayout(actions_row)
        
        # Clean tables container
        tables_container = QtWidgets.QWidget()
        tables_container.setStyleSheet("""
            QWidget {
                background-color: #ffffff;
                border: 1px solid #e1e7ef;
                border-radius: 12px;
            }
        """)
        tables_layout = QtWidgets.QVBoxLayout(tables_container)
        tables_layout.setContentsMargins(0, 0, 0, 0)
        
        # Enhanced modern tabs with subtle gradients and animations
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setStyleSheet("""
            QTabWidget::pane {
                border: none;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #fdfdfe);
                border-radius: 8px;
            }
            QTabWidget::tab-bar {
                alignment: left;
                background: transparent;
            }
            QTabBar {
                qproperty-drawBase: 0;
                border: none;
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f8fafc, stop: 1 #f1f5f9);
                border-top-left-radius: 12px;
                border-top-right-radius: 12px;
            }
            QTabBar::tab {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #f1f5f9, stop: 1 #e2e8f0);
                color: #64748b;
                padding: 14px 24px;
                margin-right: 1px;
                margin-bottom: 0px;
                border-top-left-radius: 10px;
                border-top-right-radius: 10px;
                border-bottom: 3px solid transparent;
                font-weight: 500;
                font-size: 13px;
                min-width: 90px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QTabBar::tab:selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #ffffff, stop: 1 #f8fafc);
                color: #1e293b;
                font-weight: 700;
                border-bottom: 3px solid #6366f1;
                margin-top: 0px;
            }
            QTabBar::tab:hover:!selected {
                background: qlineargradient(x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #e2e8f0, stop: 1 #cbd5e1);
                color: #475569;
                border-bottom: 3px solid #94a3b8;
            }
            QTabBar::tab:first {
                margin-left: 12px;
            }
        """)
        
        # Create minimal tables
        self.signals_table = self._create_minimal_table()
        self.tracks_table = self._create_minimal_table()
        self.routes_table = self._create_minimal_table()
        self.trains_table = self._create_minimal_table()
        
        self.signals_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        for tbl in [self.signals_table, self.tracks_table, self.routes_table, self.trains_table]:
            tbl.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
            tbl.setAlternatingRowColors(True)
            tbl.setSortingEnabled(True)
        
        # Add tables to tabs (no emojis)
        self.tabs.addTab(self.signals_table, "Signals")
        self.tabs.addTab(self.tracks_table, "Tracks") 
        self.tabs.addTab(self.routes_table, "Routes")
        self.tabs.addTab(self.trains_table, "Trains")
        
        tables_layout.addWidget(self.tabs)
        layout.addWidget(tables_container)
        
        main_layout.addWidget(content)
        
    def _create_minimal_table(self):
        """Create an enhanced modern table widget"""
        table = QtWidgets.QTableWidget()
        table.setStyleSheet("""
            QTableWidget {
                border: none;
                background-color: white;
                gridline-color: #f1f5f9;
                font-size: 13px;
                selection-background-color: #eff6ff;
                border-radius: 6px;
            }
            QHeaderView {
                border: none;
                background-color: transparent;
            }
            QHeaderView::section {
                background-color: #f8fafc;
                padding: 12px;
                border: none;
                border-bottom: 2px solid #e2e8f0;
                font-weight: 600;
                color: #475569;
                font-size: 13px;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            QHeaderView::section:horizontal {
                border-right: 1px solid #f1f5f9;
            }
            QHeaderView::section:last {
                border-right: none;
            }
            QScrollBar:vertical {
                background: #f1f5f9;
                width: 10px;
                border-radius: 5px;
                margin: 0;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 5px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar:horizontal {
                background: #f1f5f9;
                height: 10px;
                border-radius: 5px;
                margin: 0;
            }
            QScrollBar::handle:horizontal {
                background: #cbd5e1;
                border-radius: 5px;
                min-width: 20px;
            }
            QScrollBar::handle:horizontal:hover {
                background: #94a3b8;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
        """)
        
        # Enhanced table properties
        table.setShowGrid(True)
        table.setAlternatingRowColors(False)  # Disable to avoid overriding colors
        table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        table.setVerticalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        table.setHorizontalScrollMode(QtWidgets.QAbstractItemView.ScrollPerPixel)
        
        # Modern header styling
        header = table.horizontalHeader()
        header.setDefaultSectionSize(120)
        header.setMinimumSectionSize(80)
        header.setCascadingSectionResizes(False)
        header.setHighlightSections(False)
        header.setStretchLastSection(False)
        
        # Vertical header styling
        v_header = table.verticalHeader()
        v_header.setVisible(False)  # Hide row numbers for cleaner look
        
        return table
        
    def _set_default_item_style(self, item, is_data_item=False):
        """Set default styling for table items"""
        if is_data_item:
            # For data items (non-status), use default colors
            item.setForeground(QtGui.QColor("#1e293b"))
            item.setBackground(QtGui.QColor("transparent"))
        # Add padding through font metrics (Qt doesn't support CSS padding on items)
        font = item.font()
        font.setPixelSize(13)
        font.setWeight(QtGui.QFont.Medium)
        item.setFont(font)
        
    def _http(self):
        import requests
        if self._session is None:
            self._session = requests.Session()
        return self._session

    @QtCore.pyqtSlot()
    def loadOverviewFromApi(self):
        import threading

        def _run():
            try:
                url = f"{self._base_url}/api/systems/overview"
                resp = self._http().get(url, timeout=5)
                resp.raise_for_status()
                data = resp.json()
                self.overview_data = data or {}
                self.signals_data = (self.overview_data.get('signals')
                                     or self.overview_data.get('data', {}).get('signals')
                                     or [])
                QtCore.QMetaObject.invokeMethod(self, "updateFromOverview", Qt.QueuedConnection)
            except Exception as e:
                print(f"Error loading overview from API: {e}, loading fallback demo data")
                # Fallback to demo data structure
                QtCore.QMetaObject.invokeMethod(self, "loadDemoSystemData", Qt.QueuedConnection)

        threading.Thread(target=_run, daemon=True).start()
        
    @QtCore.pyqtSlot()
    def loadDemoSystemData(self):
        """Load demo system status data when API is not available"""
        try:
            import os
            data_file = os.path.join(os.path.dirname(__file__), '..', 'data', 'dummy_data.json')
            with open(data_file, 'r') as f:
                data = json.load(f)
                
                # Structure the data for system status display
                self.overview_data = {
                    'signals': data.get('signals', []),
                    'tracks': [
                        {'id': 'TRK_A1', 'type': 'MAIN', 'name': 'Central Track A1', 'place': 'Junction A', 'trackCode': 'A1', 'occupied': False},
                        {'id': 'TRK_A2', 'type': 'MAIN', 'name': 'Central Track A2', 'place': 'Junction A', 'trackCode': 'A2', 'occupied': True},
                        {'id': 'TRK_B1', 'type': 'PLATFORM', 'name': 'Platform Track B1', 'place': 'Station B', 'trackCode': 'B1', 'occupied': False},
                        {'id': 'TRK_B2', 'type': 'PLATFORM', 'name': 'Platform Track B2', 'place': 'Station B', 'trackCode': 'B2', 'occupied': True},
                        {'id': 'TRK_C1', 'type': 'FREIGHT', 'name': 'Freight Track C1', 'place': 'Yard C', 'trackCode': 'C1', 'occupied': False}
                    ],
                    'routes': [
                        {'id': 'RT_001', 'beginSignal': 'SIG_A1', 'endSignal': 'SIG_B1', 'state': 'ACTIVE', 'isActive': True},
                        {'id': 'RT_002', 'beginSignal': 'SIG_A2', 'endSignal': 'SIG_B2', 'state': 'LOCKED', 'isActive': True},
                        {'id': 'RT_003', 'beginSignal': 'SIG_B1', 'endSignal': 'SIG_C1', 'state': 'INACTIVE', 'isActive': False}
                    ],
                    'trains': [
                        {'id': 'T001', 'serviceCode': 'SVC001', 'status': 'RUNNING', 'active': True, 'speedKmh': 75.5, 'maxSpeed': 120},
                        {'id': 'T002', 'serviceCode': 'SVC002', 'status': 'STOPPED', 'active': False, 'speedKmh': 0, 'maxSpeed': 100}
                    ],
                    'occupancy': {'utilization': 78.5},
                    'totals': {
                        'trains': {'active': 1, 'total': 2},
                        'signals': 3,
                        'routes': 3
                    }
                }
                
                # Extract signals data
                self.signals_data = self.overview_data.get('signals', [])
                
                # Update the display
                self.updateFromOverview()
                
        except Exception as e:
            print(f"Error loading demo data: {e}")
            # Create minimal fallback data
            self.overview_data = {
                'signals': [],
                'tracks': [],
                'routes': [],
                'trains': [],
                'occupancy': {'utilization': 0},
                'totals': {'trains': {'active': 0, 'total': 0}, 'signals': 0, 'routes': 0}
            }
            self.signals_data = []
            self.updateFromOverview()
            
    @QtCore.pyqtSlot()
    def updateFromOverview(self):
        """Update KPIs and all tables from cached overview data."""
        o = self.overview_data or {}
        # KPIs
        occ = o.get('occupancy') or {}
        util = occ.get('utilization')
        try:
            util_text = f"{float(util):.1f}%" if util is not None else "-"
        except Exception:
            util_text = str(util) if util is not None else "-"
        totals = o.get('totals') or {}
        trains_tot = totals.get('trains') or {}
        active = trains_tot.get('active') if isinstance(trains_tot, dict) else None
        total = trains_tot.get('total') if isinstance(trains_tot, dict) else None
        self.kpi_util_value.setText(util_text)
        
        if active is not None and total is not None:
            self.kpi_trains_value.setText(f"{active} / {total}")
        else:
            self.kpi_trains_value.setText("-")
        signals_count = totals.get('signals')
        if signals_count is None:
            signals_count = len(o.get('signals') or [])
        self.kpi_signals_value.setText(str(signals_count))
        routes_count = totals.get('routes')
        if routes_count is None:
            routes_count = len(o.get('routes') or [])
        self.kpi_routes_value.setText(str(routes_count))
        
        # Tables
        self.updateSignalsTable()
        self.updateTracksTable(o.get('tracks') or [])
        self.updateRoutesTable(o.get('routes') or [])
        self.updateTrainsTable(o.get('trains') or [])

    @QtCore.pyqtSlot()
    def updateSignalsTable(self):
        """Update the signals table with enhanced styling"""
        self.signals_table.setRowCount(len(self.signals_data))
        self.signals_table.setColumnCount(5)
        self.signals_table.setHorizontalHeaderLabels(["Signal ID", "Name", "Status", "Type", "Last Changed"])
        
        for row, signal in enumerate(self.signals_data):
            # Signal ID
            id_item = QtWidgets.QTableWidgetItem(signal['id'])
            id_item.setFont(QtGui.QFont("monospace"))  # Monospace for IDs
            self._set_default_item_style(id_item, is_data_item=True)
            self.signals_table.setItem(row, 0, id_item)
            
            # Name
            name_item = QtWidgets.QTableWidgetItem(signal['name'])
            self._set_default_item_style(name_item, is_data_item=True)
            self.signals_table.setItem(row, 1, name_item)
            
            # Status with enhanced badge-style color coding
            status_text = signal['status']
            status_item = QtWidgets.QTableWidgetItem(f" {status_text} ")
            status_font = QtGui.QFont()
            status_font.setBold(True)
            status_font.setPixelSize(11)
            status_item.setFont(status_font)
            status_item.setTextAlignment(QtCore.Qt.AlignCenter)
            
            # Enhanced color coding for various signal states
            status_upper = status_text.upper()
            if status_upper in ['GREEN', 'CLEAR', 'PROCEED', 'GO']:
                status_item.setForeground(QtGui.QColor("#065f46"))  # Darker green text
                status_item.setBackground(QtGui.QColor("#d1fae5"))  # Soft green bg
            elif status_upper in ['RED', 'DANGER', 'STOP', 'BLOCKED']:
                status_item.setForeground(QtGui.QColor("#991b1b"))  # Darker red text
                status_item.setBackground(QtGui.QColor("#fee2e2"))  # Soft red bg
            elif status_upper in ['YELLOW', 'CAUTION', 'APPROACH', 'SLOW']:
                status_item.setForeground(QtGui.QColor("#92400e"))  # Darker amber text
                status_item.setBackground(QtGui.QColor("#fef3c7"))  # Soft amber bg
            elif status_upper in ['BLUE', 'SHUNT', 'ROUTE']:
                status_item.setForeground(QtGui.QColor("#1e3a8a"))  # Blue text
                status_item.setBackground(QtGui.QColor("#dbeafe"))  # Light blue bg
            else:
                status_item.setForeground(QtGui.QColor("#374151"))
                status_item.setBackground(QtGui.QColor("#f3f4f6"))
                
            self.signals_table.setItem(row, 2, status_item)
            
            # Type
            type_item = QtWidgets.QTableWidgetItem(signal['type'])
            self._set_default_item_style(type_item, is_data_item=True)
            type_item.setForeground(QtGui.QColor("#6b7280"))  # Subtle gray
            self.signals_table.setItem(row, 3, type_item)
            
            # Last Changed
            time_item = QtWidgets.QTableWidgetItem(signal['lastChanged'])
            self._set_default_item_style(time_item, is_data_item=True)
            time_item.setForeground(QtGui.QColor("#6b7280"))  # Subtle gray
            time_item.setFont(QtGui.QFont("monospace"))  # Monospace for time
            self.signals_table.setItem(row, 4, time_item)
            
        # Enhanced column sizing for better readability
        header = self.signals_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # Signal ID
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Name (expandable)  
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)  # Last Changed
        header.setStretchLastSection(False)  # Manual control
        
        # Set minimum column widths for better layout
        self.signals_table.setColumnWidth(0, 100)  # Signal ID
        self.signals_table.setColumnWidth(2, 80)   # Status
        self.signals_table.setColumnWidth(3, 100)  # Type

    def updateTracksTable(self, tracks):
        """Update tracks table with enhanced styling"""
        self.tracks_table.setRowCount(len(tracks))
        self.tracks_table.setColumnCount(6)
        self.tracks_table.setHorizontalHeaderLabels(["ID", "Type", "Name", "Place", "Code", "Occupied"])
        
        for row, t in enumerate(tracks):
            # ID with monospace font
            id_item = QtWidgets.QTableWidgetItem(str(t.get('id', '')))
            id_item.setFont(QtGui.QFont("monospace"))
            self.tracks_table.setItem(row, 0, id_item)
            
            # Type with subtle styling
            type_item = QtWidgets.QTableWidgetItem(str(t.get('type', '')))
            type_item.setForeground(QtGui.QColor("#6b7280"))
            self.tracks_table.setItem(row, 1, type_item)
            
            # Name (primary text)
            self.tracks_table.setItem(row, 2, QtWidgets.QTableWidgetItem(str(t.get('name', ''))))
            
            # Place
            place_item = QtWidgets.QTableWidgetItem(str(t.get('place', '')))
            place_item.setForeground(QtGui.QColor("#6b7280"))
            self.tracks_table.setItem(row, 3, place_item)
            
            # Code with monospace
            code_item = QtWidgets.QTableWidgetItem(str(t.get('trackCode', '')))
            code_item.setFont(QtGui.QFont("monospace"))
            code_item.setForeground(QtGui.QColor("#6b7280"))
            self.tracks_table.setItem(row, 4, code_item)
            
            # Enhanced occupied status with comprehensive color coding
            occ = t.get('occupied')
            # Handle string values for occupied status
            if isinstance(occ, str):
                occ_upper = occ.upper()
                if occ_upper in ['TRUE', 'OCCUPIED', 'BLOCKED', 'ENGAGED']:
                    occ_text = "OCCUPIED"
                    occ_color_fg = "#991b1b"  # Red
                    occ_color_bg = "#fee2e2"
                elif occ_upper in ['FALSE', 'FREE', 'CLEAR', 'AVAILABLE']:
                    occ_text = "FREE"
                    occ_color_fg = "#065f46"  # Green
                    occ_color_bg = "#d1fae5"
                elif occ_upper in ['RESERVED', 'PERSISTENT', 'HELD']:
                    occ_text = "RESERVED"
                    occ_color_fg = "#1e3a8a"  # Blue
                    occ_color_bg = "#dbeafe"
                elif occ_upper in ['MAINTENANCE', 'OUT_OF_SERVICE']:
                    occ_text = "MAINTENANCE"
                    occ_color_fg = "#7c2d12"  # Brown
                    occ_color_bg = "#fef7ed"
                else:
                    occ_text = occ_upper
                    occ_color_fg = "#374151"  # Gray
                    occ_color_bg = "#f3f4f6"
            else:
                # Handle boolean values
                if occ is True:
                    occ_text = "OCCUPIED"
                    occ_color_fg = "#991b1b"  # Red
                    occ_color_bg = "#fee2e2"
                elif occ is False:
                    occ_text = "FREE"
                    occ_color_fg = "#065f46"  # Green
                    occ_color_bg = "#d1fae5"
                else:
                    occ_text = "UNKNOWN"
                    occ_color_fg = "#374151"  # Gray
                    occ_color_bg = "#f3f4f6"
            
            occ_item = QtWidgets.QTableWidgetItem(f" {occ_text} ")
            occ_font = QtGui.QFont()
            occ_font.setBold(True)
            occ_font.setPixelSize(10)
            occ_item.setFont(occ_font)
            occ_item.setTextAlignment(QtCore.Qt.AlignCenter)
            occ_item.setForeground(QtGui.QColor(occ_color_fg))
            occ_item.setBackground(QtGui.QColor(occ_color_bg))
                
            self.tracks_table.setItem(row, 5, occ_item)
            
        # Enhanced column sizing
        header = self.tracks_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)  # Name (expandable)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Place
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)  # Code
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)  # Occupied
        header.setStretchLastSection(False)

    def updateRoutesTable(self, routes):
        """Update routes table with enhanced styling"""
        self.routes_table.setRowCount(len(routes))
        self.routes_table.setColumnCount(5)
        self.routes_table.setHorizontalHeaderLabels(["ID", "Begin Signal", "End Signal", "State", "Active"])
        
        for row, r in enumerate(routes):
            # ID with monospace
            id_item = QtWidgets.QTableWidgetItem(str(r.get('id', '')))
            id_item.setFont(QtGui.QFont("monospace"))
            self.routes_table.setItem(row, 0, id_item)
            
            # Begin Signal with monospace
            begin_item = QtWidgets.QTableWidgetItem(str(r.get('beginSignal', '')))
            begin_item.setFont(QtGui.QFont("monospace"))
            begin_item.setForeground(QtGui.QColor("#6b7280"))
            self.routes_table.setItem(row, 1, begin_item)
            
            # End Signal with monospace  
            end_item = QtWidgets.QTableWidgetItem(str(r.get('endSignal', '')))
            end_item.setFont(QtGui.QFont("monospace"))
            end_item.setForeground(QtGui.QColor("#6b7280"))
            self.routes_table.setItem(row, 2, end_item)
            
            # Enhanced state with badge-style color coding
            state_text = str(r.get('state', '')).upper()
            state_item = QtWidgets.QTableWidgetItem(f" {state_text} ")
            state_font = QtGui.QFont()
            state_font.setBold(True)
            state_font.setPixelSize(10)
            state_item.setFont(state_font)
            state_item.setTextAlignment(QtCore.Qt.AlignCenter)
            
            # Enhanced color coding for various route states
            if state_text in ['ACTIVE', 'LOCKED', 'ACTIVATED', 'SET', 'ENGAGED']:
                state_item.setForeground(QtGui.QColor("#065f46"))  # Darker green
                state_item.setBackground(QtGui.QColor("#d1fae5"))  # Soft green
            elif state_text in ['INACTIVE', 'UNLOCKED', 'DEACTIVATED', 'FREE', 'CLEAR']:
                state_item.setForeground(QtGui.QColor("#374151"))  # Dark gray
                state_item.setBackground(QtGui.QColor("#f3f4f6"))  # Light gray
            elif state_text in ['ERROR', 'FAILED', 'FAULT', 'CONFLICT']:
                state_item.setForeground(QtGui.QColor("#991b1b"))  # Darker red
                state_item.setBackground(QtGui.QColor("#fee2e2"))  # Soft red
            elif state_text in ['PENDING', 'WAITING', 'REQUEST', 'PARTIAL']:
                state_item.setForeground(QtGui.QColor("#92400e"))  # Darker amber
                state_item.setBackground(QtGui.QColor("#fef3c7"))  # Soft amber
            elif state_text in ['PERSISTENT', 'HELD', 'RESERVED']:
                state_item.setForeground(QtGui.QColor("#1e3a8a"))  # Blue
                state_item.setBackground(QtGui.QColor("#dbeafe"))  # Light blue
            else:
                state_item.setForeground(QtGui.QColor("#6b7280"))  # Default gray
                state_item.setBackground(QtGui.QColor("#f9fafb"))  # Light gray
                
            self.routes_table.setItem(row, 3, state_item)
            
            # Enhanced active status with badge styling
            act = r.get('isActive')
            act_text = "ACTIVE" if act else "INACTIVE"
            act_item = QtWidgets.QTableWidgetItem(f" {act_text} ")
            act_font = QtGui.QFont()
            act_font.setBold(True)
            act_font.setPixelSize(10)
            act_item.setFont(act_font)
            act_item.setTextAlignment(QtCore.Qt.AlignCenter)
            
            if act:
                act_item.setForeground(QtGui.QColor("#065f46"))  # Darker green for active
                act_item.setBackground(QtGui.QColor("#d1fae5"))  # Soft green bg
            else:
                act_item.setForeground(QtGui.QColor("#374151"))  # Dark gray for inactive
                act_item.setBackground(QtGui.QColor("#f3f4f6"))  # Light gray bg
                
            self.routes_table.setItem(row, 4, act_item)
            
        # Enhanced column sizing
        header = self.routes_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Begin Signal
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)  # End Signal  
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # State
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)  # Active
        header.setStretchLastSection(False)

    def updateTrainsTable(self, trains):
        """Update trains table with enhanced styling"""
        self.trains_table.setRowCount(len(trains))
        self.trains_table.setColumnCount(6)
        self.trains_table.setHorizontalHeaderLabels(["ID", "Service", "Status", "Active", "Speed", "Max Speed"])
        
        for row, tr in enumerate(trains):
            # Train ID with monospace
            id_item = QtWidgets.QTableWidgetItem(str(tr.get('id', '')))
            id_item.setFont(QtGui.QFont("monospace"))
            self._set_default_item_style(id_item, is_data_item=True)
            self.trains_table.setItem(row, 0, id_item)
            
            # Service Code with monospace
            service_item = QtWidgets.QTableWidgetItem(str(tr.get('serviceCode', '')))
            service_item.setFont(QtGui.QFont("monospace"))
            self._set_default_item_style(service_item, is_data_item=True)
            service_item.setForeground(QtGui.QColor("#6b7280"))
            self.trains_table.setItem(row, 1, service_item)
            
            # Enhanced status with badge-style color coding
            status_text = str(tr.get('status', '')).upper()
            status_item = QtWidgets.QTableWidgetItem(f" {status_text} ")
            status_font = QtGui.QFont()
            status_font.setBold(True)
            status_font.setPixelSize(10)
            status_item.setFont(status_font)
            status_item.setTextAlignment(QtCore.Qt.AlignCenter)
            
            # Enhanced color coding for various train states
            if status_text in ['RUNNING', 'MOVING', 'ACTIVE', 'PROCEEDING']:
                status_item.setForeground(QtGui.QColor("#065f46"))  # Darker green
                status_item.setBackground(QtGui.QColor("#d1fae5"))  # Soft green
            elif status_text in ['STOPPED', 'PARKED', 'INACTIVE', 'IDLE']:
                status_item.setForeground(QtGui.QColor("#374151"))  # Dark gray
                status_item.setBackground(QtGui.QColor("#f3f4f6"))  # Light gray
            elif status_text in ['DELAYED', 'WARNING', 'SLOW', 'CAUTION']:
                status_item.setForeground(QtGui.QColor("#92400e"))  # Darker amber
                status_item.setBackground(QtGui.QColor("#fef3c7"))  # Soft amber
            elif status_text in ['ERROR', 'EMERGENCY', 'FAULT', 'CRITICAL']:
                status_item.setForeground(QtGui.QColor("#991b1b"))  # Darker red
                status_item.setBackground(QtGui.QColor("#fee2e2"))  # Soft red
            elif status_text in ['PERSISTENT', 'SCHEDULED', 'WAITING']:
                status_item.setForeground(QtGui.QColor("#1e3a8a"))  # Blue
                status_item.setBackground(QtGui.QColor("#dbeafe"))  # Light blue
            elif status_text in ['DEACTIVATED', 'OUT_OF_SERVICE', 'MAINTENANCE']:
                status_item.setForeground(QtGui.QColor("#7c2d12"))  # Brown
                status_item.setBackground(QtGui.QColor("#fef7ed"))  # Light brown
            else:
                status_item.setForeground(QtGui.QColor("#374151"))  # Default gray
                status_item.setBackground(QtGui.QColor("#f3f4f6"))  # Light gray bg
                
            self.trains_table.setItem(row, 2, status_item)
            
            # Enhanced active status with badge styling
            act = tr.get('active')
            act_text = "ACTIVE" if act else "INACTIVE"
            act_item = QtWidgets.QTableWidgetItem(f" {act_text} ")
            act_font = QtGui.QFont()
            act_font.setBold(True)
            act_font.setPixelSize(10)
            act_item.setFont(act_font)
            act_item.setTextAlignment(QtCore.Qt.AlignCenter)
            
            if act:
                act_item.setForeground(QtGui.QColor("#065f46"))  # Darker green for active
                act_item.setBackground(QtGui.QColor("#d1fae5"))  # Soft green bg
            else:
                act_item.setForeground(QtGui.QColor("#374151"))  # Dark gray for inactive
                act_item.setBackground(QtGui.QColor("#f3f4f6"))  # Light gray bg
                
            self.trains_table.setItem(row, 3, act_item)
            
            # Current Speed with monospace
            speed = tr.get('speedKmh')
            speed_text = f"{speed} km/h" if speed is not None else "-"
            speed_item = QtWidgets.QTableWidgetItem(speed_text)
            speed_item.setFont(QtGui.QFont("monospace"))
            
            # Color code based on speed
            if speed is not None:
                if speed > 80:
                    speed_item.setForeground(QtGui.QColor("#ef4444"))  # Red for high speed
                elif speed > 40:
                    speed_item.setForeground(QtGui.QColor("#f59e0b"))  # Amber for medium speed
                else:
                    speed_item.setForeground(QtGui.QColor("#10b981"))  # Green for low speed
            else:
                speed_item.setForeground(QtGui.QColor("#6b7280"))  # Gray for unknown
                
            self.trains_table.setItem(row, 4, speed_item)
            
            # Max Speed with monospace
            maxs = tr.get('maxSpeed') or tr.get('maxSpeedKmh')
            max_text = f"{maxs} km/h" if maxs is not None else "-"
            max_item = QtWidgets.QTableWidgetItem(max_text)
            max_item.setFont(QtGui.QFont("monospace"))
            max_item.setForeground(QtGui.QColor("#6b7280"))
            self.trains_table.setItem(row, 5, max_item)
            
        # Enhanced column sizing
        header = self.trains_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)  # Service (expandable)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeToContents)  # Status
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeToContents)  # Active
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeToContents)  # Speed
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeToContents)  # Max Speed
        header.setStretchLastSection(False)

