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

import io
import os
import signal
import subprocess
import tempfile
import time
import zipfile
from os import path

import simplejson as json
import websocket

from Qt import QtCore, QtGui, QtWidgets, Qt
from ts2 import __PROJECT_WWW__, __PROJECT_HOME__, __PROJECT_BUGS__, \
    __ORG_CONTACT__, __VERSION__, utils
from ts2 import simulation
from ts2.editor import editorwindow
from ts2.gui import dialogs, trainlistview, servicelistview, widgets, \
    opendialog, settingsdialog, sidebar, analytics_views, ai_hints, modern_header
from ts2.scenery import placeitem
from ts2.utils import settings

WS_TIMEOUT = 10


class MainWindow(QtWidgets.QMainWindow):
    """MainWindow Class"""

    simulationLoaded = QtCore.pyqtSignal(simulation.Simulation)

    def __init__(self, args=None):
        super().__init__()
        MainWindow._self = self

        self.fileName = None
        self.simServer = args.server

        if args:
            settings.setDebug(args.debug)
            if args.file:
                # TODO absolute paths
                self.fileName = args.file

        self.setObjectName("ts2_main_window")
        self.editorWindow = None
        # Set initial window size with proper minimum sizes
        self.setGeometry(100, 100, 1400, 900)  # Increased size for better layout
        self.setMinimumSize(1200, 700)  # Minimum size to prevent severe cropping
        self.setWindowTitle(self.tr("TrackTitans - Railway Operations Center - %s")
                            % __VERSION__)

        # Simulation
        self.simulation = None
        self.webSocket = None
        self.serverPID = None
        if settings.debug:
            websocket.enableTrace(True)
            
        # View management
        self.current_view = "simulation"
        self.views = {}

        # Actions  ======================================
        self.openAction = QtWidgets.QAction(self.tr("&Open..."), self)
        self.openAction.setShortcut(QtGui.QKeySequence.Open)
        self.openAction.setToolTip(self.tr("Open a simulation or a "
                                           "previously saved game"))
        self.openAction.triggered.connect(self.onOpenSimulation)

        self.closeAction = QtWidgets.QAction(self.tr("&Close"))
        self.closeAction.setShortcut(QtGui.QKeySequence.Close)
        self.closeAction.setToolTip(self.tr("Close the current simulation"))
        self.closeAction.triggered.connect(self.simulationClose)

        self.openRecentAction = QtWidgets.QAction(self.tr("Recent"), self)
        menu = QtWidgets.QMenu()
        self.openRecentAction.setMenu(menu)
        menu.triggered.connect(self.onRecent)

        self.saveGameAsAction = QtWidgets.QAction(self.tr("&Save game"), self)
        self.saveGameAsAction.setShortcut(QtGui.QKeySequence.SaveAs)
        self.saveGameAsAction.setToolTip(self.tr("Save the current game"))
        self.saveGameAsAction.triggered.connect(self.saveGame)
        self.saveGameAsAction.setEnabled(False)

        # Properties
        self.propertiesAction = QtWidgets.QAction(self.tr("Sim &Properties..."),
                                                  self)
        self.propertiesAction.setShortcut(
            QtGui.QKeySequence(self.tr("Ctrl+P"))
        )
        self.propertiesAction.setToolTip(self.tr("Edit simulation properties"))
        self.propertiesAction.triggered.connect(self.openPropertiesDialog)
        self.propertiesAction.setEnabled(False)

        # Settings
        self.settingsAction = QtWidgets.QAction(self.tr("Settings..."),
                                                self)
        self.settingsAction.setToolTip(self.tr("User Settings"))
        self.settingsAction.triggered.connect(self.openSettingsDialog)

        self.quitAction = QtWidgets.QAction(self.tr("&Quit"), self)
        self.quitAction.setShortcut(QtGui.QKeySequence(self.tr("Ctrl+Q")))
        self.quitAction.setToolTip(self.tr("Quit TS2"))
        self.quitAction.triggered.connect(self.close)

        self.editorAction = QtWidgets.QAction(self.tr("&Open Editor"), self)
        self.editorAction.setShortcut(QtGui.QKeySequence(self.tr("Ctrl+E")))
        self.editorAction.setToolTip(self.tr("Open the simulation editor"))
        self.editorAction.triggered.connect(self.openEditor)

        self.editorCurrAction = QtWidgets.QAction(self.tr("&Edit"), self)
        self.editorCurrAction.setToolTip(self.tr("Open this sim in editor"))
        self.editorCurrAction.triggered.connect(self.onEditorCurrent)

        # Web Links
        self.actionGroupWwww = QtWidgets.QActionGroup(self)
        self.actionGroupWwww.triggered.connect(self.onWwwAction)

        self.aboutWwwHompage = QtWidgets.QAction(self.tr("&TS2 Homepage"), self)
        self.aboutWwwHompage.setProperty("url", __PROJECT_WWW__)
        self.actionGroupWwww.addAction(self.aboutWwwHompage)

        self.aboutWwwProject = QtWidgets.QAction(self.tr("&TS2 Project"), self)
        self.aboutWwwProject.setProperty("url", __PROJECT_HOME__)
        self.actionGroupWwww.addAction(self.aboutWwwProject)

        self.aboutWwwBugs = QtWidgets.QAction(self.tr("&TS2 Bugs && Feedback"),
                                              self)
        self.aboutWwwBugs.setProperty("url", __PROJECT_BUGS__)
        self.actionGroupWwww.addAction(self.aboutWwwBugs)

        # About
        self.aboutAction = QtWidgets.QAction(self.tr("&About TS2..."), self)
        self.aboutAction.setToolTip(self.tr("About TS2"))
        self.aboutAction.triggered.connect(self.showAboutBox)

        self.aboutQtAction = QtWidgets.QAction(self.tr("About Qt..."), self)
        self.aboutQtAction.setToolTip(self.tr("About Qt"))
        self.aboutQtAction.triggered.connect(QtWidgets.QApplication.aboutQt)

        # ===============================================
        # Menus

        # FileMenu
        self.fileMenu = self.menuBar().addMenu(self.tr("&File"))
        self.fileMenu.addAction(self.openAction)
        self.fileMenu.addAction(self.openRecentAction)
        self.fileMenu.addAction(self.saveGameAsAction)
        self.fileMenu.addAction(self.closeAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.propertiesAction)
        self.fileMenu.addAction(self.settingsAction)
        self.fileMenu.addSeparator()
        self.fileMenu.addAction(self.quitAction)

        # Editor Menu
        self.editorMenu = self.menuBar().addMenu(self.tr("&Editor"))
        self.editorMenu.addAction(self.editorAction)
        self.editorMenu.addAction(self.editorCurrAction)

        # Help Menu
        self.helpMenu = self.menuBar().addMenu(self.tr("&Help"))
        self.helpMenu.addAction(self.aboutWwwHompage)
        self.helpMenu.addAction(self.aboutWwwProject)
        self.helpMenu.addAction(self.aboutWwwBugs)
        self.helpMenu.addSeparator()
        self.helpMenu.addAction(self.aboutAction)
        self.helpMenu.addAction(self.aboutQtAction)

        self.menuBar().setCursor(Qt.PointingHandCursor)

        # ==============================================================
        # Modern Header Widget (Perfect Layout)

        # Create modern header with proper layout management
        self.modern_header = modern_header.ModernHeaderWidget(self)
        
        # Connect header signals
        self.modern_header.openActionTriggered.connect(self.onOpenSimulation)
        self.modern_header.editActionTriggered.connect(self.onEditorCurrent)
        self.modern_header.speedChanged.connect(self.onSpeedChanged)
        self.modern_header.zoomChanged.connect(self.zoom)
        self.modern_header.pauseToggled.connect(self.onPauseToggled)
        self.modern_header.restartRequested.connect(self.onRestartRequested)
        
        # Add as a widget above the main container (not as toolbar)
        self.header_container = QtWidgets.QWidget()
        header_layout = QtWidgets.QVBoxLayout(self.header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(0)
        header_layout.addWidget(self.modern_header)
        
        # Store references for compatibility
        self.scoreDisplay = self.modern_header.score_display
        self.clockWidget = self.modern_header.clock_widget
        self.buttPause = self.modern_header.pause_btn
        self.zoomWidget = self.modern_header.zoom_widget
        self.lblTitle = self.modern_header.title_label

        # ===============================================================
        # Dock Widgets

        # Train Info
        self.trainInfoPanel = QtWidgets.QDockWidget(
            self.tr("Train Information"), self
        )
        self.trainInfoPanel.setObjectName("train_information")
        self.trainInfoPanel.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetFloatable
        )
        # Ensure dock widget cannot be closed accidentally
        self.trainInfoPanel.setFeatures(self.trainInfoPanel.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        self.trainInfoView = QtWidgets.QTreeView(self)
        self.trainInfoView.setItemsExpandable(False)
        self.trainInfoView.setRootIsDecorated(False)
        self.trainInfoView.setContextMenuPolicy(Qt.CustomContextMenu)
        self.trainInfoView.customContextMenuRequested.connect(
            self.showContextMenu
        )
        self.trainInfoPanel.setWidget(self.trainInfoView)
        self.addDockWidget(Qt.RightDockWidgetArea, self.trainInfoPanel)

        # Service Info
        self.serviceInfoPanel = QtWidgets.QDockWidget(
            self.tr("Service Information"), self
        )
        self.serviceInfoPanel.setObjectName("service_information")
        self.serviceInfoPanel.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetFloatable
        )
        # Ensure dock widget cannot be closed accidentally
        self.serviceInfoPanel.setFeatures(self.serviceInfoPanel.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)

        sty = "background-color: #444444; color: white; padding: 2px;" \
              " font-size: 10pt"
        wid = QtWidgets.QScrollArea()
        self.serviceInfoPanel.setWidget(wid)
        grid = QtWidgets.QGridLayout()
        wid.setLayout(grid)
        self.lblServiceInfoCode = QtWidgets.QLabel()
        self.lblServiceInfoCode.setStyleSheet(sty)
        self.lblServiceInfoCode.setText("")
        self.lblServiceInfoCode.setMaximumWidth(100)
        grid.addWidget(self.lblServiceInfoCode, 0, 0)
        self.lblServiceInfoDescription = QtWidgets.QLabel()
        self.lblServiceInfoDescription.setText("")
        self.lblServiceInfoDescription.setStyleSheet(sty)
        self.lblServiceInfoDescription.setScaledContents(False)
        grid.addWidget(self.lblServiceInfoDescription, 0, 1)
        self.serviceInfoView = QtWidgets.QTreeView(self)
        self.serviceInfoView.setItemsExpandable(False)
        self.serviceInfoView.setRootIsDecorated(False)
        grid.addWidget(self.serviceInfoView, 1, 0, 1, 2)
        self.serviceInfoPanel.setWidget(wid)
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 4)
        grid.setSpacing(0)
        grid.setContentsMargins(0, 0, 0, 0)
        self.addDockWidget(Qt.RightDockWidgetArea, self.serviceInfoPanel)

        # Stations + Places Info
        self.placeInfoPanel = QtWidgets.QDockWidget(
            self.tr("Station Information"), self
        )
        self.placeInfoPanel.setObjectName("place_information")
        self.placeInfoPanel.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetFloatable
        )
        # Ensure dock widget cannot be closed accidentally
        self.placeInfoPanel.setFeatures(self.placeInfoPanel.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        wid = QtWidgets.QScrollArea()
        self.placeInfoPanel.setWidget(wid)
        hb = QtWidgets.QVBoxLayout()
        wid.setLayout(hb)
        self.lblPlaceInfoName = QtWidgets.QLabel()
        self.lblPlaceInfoName.setStyleSheet(sty)
        self.lblPlaceInfoName.setText("")
        hb.addWidget(self.lblPlaceInfoName)

        self.placeInfoView = QtWidgets.QTreeView(self)
        self.placeInfoView.setItemsExpandable(False)
        self.placeInfoView.setRootIsDecorated(False)
        self.placeInfoView.setModel(placeitem.Place.selectedPlaceModel)
        hb.addWidget(self.placeInfoView)

        hb.setSpacing(0)
        hb.setContentsMargins(0, 0, 0, 0)

        self.placeInfoPanel.setWidget(wid)
        self.addDockWidget(Qt.RightDockWidgetArea, self.placeInfoPanel)

        # Trains (Bottom Panel - Always visible in simulation)
        self.trainListPanel = QtWidgets.QDockWidget(self.tr("Trains"), self)
        self.trainListPanel.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetFloatable
        )
        # Ensure dock widget cannot be closed or hidden accidentally
        self.trainListPanel.setFeatures(self.trainListPanel.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        # Keep bottom docks from collapsing to zero height and restrict to bottom area
        self.trainListPanel.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.trainListPanel.setMinimumHeight(120)
        self.trainListPanel.setObjectName("trains_panel")
        self.trainListView = trainlistview.TrainListView(self)
        self.trainListView.setMinimumHeight(100)
        self.simulationLoaded.connect(self.trainListView.setupTrainList)
        self.trainListPanel.setWidget(self.trainListView)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.trainListPanel)
        
        # Ensure trains panel is visible by default
        self.trainListPanel.setVisible(True)
        self.trainListPanel.show()

        # Services (Bottom Panel - Always visible in simulation)
        self.serviceListPanel = QtWidgets.QDockWidget(self.tr("Services"), self)
        self.serviceListPanel.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetFloatable
        )
        # Ensure dock widget cannot be closed or hidden accidentally
        self.serviceListPanel.setFeatures(self.serviceListPanel.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        # Keep bottom docks from collapsing to zero height and restrict to bottom area
        self.serviceListPanel.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.serviceListPanel.setMinimumHeight(120)
        self.serviceListPanel.setObjectName("services_panel")
        self.serviceListView = servicelistview.ServiceListView(self)
        self.serviceListView.setMinimumHeight(100)
        self.simulationLoaded.connect(self.serviceListView.setupServiceList)
        self.serviceListPanel.setWidget(self.serviceListView)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.serviceListPanel)
        self.tabifyDockWidget(self.serviceListPanel, self.trainListPanel)
        
        # Ensure services panel is visible by default
        self.serviceListPanel.setVisible(True)
        self.serviceListPanel.show()
        
        # Make trains panel the active tab by default
        self.trainListPanel.raise_()
        self.trainListPanel.activateWindow()

        # Message Logger
        self.loggerPanel = QtWidgets.QDockWidget(self.tr("Messages"), self)
        self.loggerPanel.setFeatures(QtWidgets.QDockWidget.DockWidgetMovable |
                                     QtWidgets.QDockWidget.DockWidgetFloatable)
        # Ensure dock widget cannot be closed accidentally
        self.loggerPanel.setFeatures(self.loggerPanel.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        # Keep bottom docks from collapsing to zero height and restrict to bottom area
        self.loggerPanel.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.loggerPanel.setMinimumHeight(100)
        self.loggerPanel.setObjectName("logger_panel")
        self.loggerView = QtWidgets.QTreeView(self)
        self.loggerView.setItemsExpandable(False)
        self.loggerView.setRootIsDecorated(False)
        self.loggerView.setHeaderHidden(True)
        self.loggerView.setMinimumHeight(80)
        self.loggerView.setPalette(QtGui.QPalette(Qt.black))
        self.loggerView.setVerticalScrollMode(
            QtWidgets.QAbstractItemView.ScrollPerItem
        )
        self.loggerPanel.setWidget(self.loggerView)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.loggerPanel)

        # ===========================================
        # Main Application Layout with Header
        
        # Create main container with vertical layout (header on top)
        main_container = QtWidgets.QWidget(self)
        main_layout = QtWidgets.QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Add header at the top
        main_layout.addWidget(self.modern_header)
        
        # Content area below header (fixed layout for no cropping)
        content_container = QtWidgets.QWidget()
        content_layout = QtWidgets.QHBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Sidebar Navigation (fixed width)
        self.sidebar = sidebar.SidebarNavigation(self)
        self.sidebar.viewChanged.connect(self.onViewChanged)
        content_layout.addWidget(self.sidebar)
        
        # Create stacked widget for different views (expanding)
        self.view_stack = QtWidgets.QStackedWidget()
        self.view_stack.setMinimumWidth(900)  # Increased minimum width to prevent cropping
        self.view_stack.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        content_layout.addWidget(self.view_stack)
        
        # Set layout proportions to prevent cropping
        content_layout.setStretch(0, 0)  # Sidebar fixed width
        content_layout.setStretch(1, 2)  # View stack expands with higher priority
        
        # Add content area to main layout
        main_layout.addWidget(content_container)
        
        # Original simulation view (board)
        self.board = QtWidgets.QWidget()
        board_layout = QtWidgets.QVBoxLayout(self.board)
        board_layout.setContentsMargins(0, 0, 0, 0)
        board_layout.setSpacing(0)
        
        # Canvas
        self.view = widgets.XGraphicsView(self.board)
        self.view.setInteractive(True)
        self.view.setRenderHint(QtGui.QPainter.Antialiasing, False)
        self.view.setDragMode(QtWidgets.QGraphicsView.ScrollHandDrag)
        self.view.setPalette(QtGui.QPalette(Qt.black))
        self.view.wheelChanged.connect(self.onWheelChanged)
        
        board_layout.addWidget(self.view)
        
        # Add simulation view to stack
        self.view_stack.addWidget(self.board)
        self.view_index_map = {"simulation": 0}
        
        # Create and add new views
        self.setupNewViews()
        
        self.setCentralWidget(main_container)

        # Editor
        self.editorOpened = False
        self.setControlsDisabled(True)

        self.refreshRecent()
        settings.restoreWindow(self)
        
        # CRITICAL: Force bottom panels to be visible after settings restore
        # settings.restoreWindow() often restores a state where panels were hidden
        print("Forcing bottom panels visibility after settings restore...")
        self.trainListPanel.setVisible(True)
        self.serviceListPanel.setVisible(True)
        self.trainListPanel.show()
        self.serviceListPanel.show()
        
        # Make them non-closable to prevent accidental hiding
        self.trainListPanel.setFeatures(self.trainListPanel.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        self.serviceListPanel.setFeatures(self.serviceListPanel.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        
        print(f"After restore - Trains visible: {self.trainListPanel.isVisible()}")
        print(f"After restore - Services visible: {self.serviceListPanel.isVisible()}")

        if args and args.file:
            if args.edit:
                self.openEditor(args.file)
                # else:
                # here we call after window is shown
        
        # Final check to ensure bottom panels are visible at startup
        QtCore.QTimer.singleShot(50, self.ensureBottomPanelsVisible)
        QtCore.QTimer.singleShot(100, self.onAfterShow)
        QtCore.QTimer.singleShot(200, lambda: self.onViewChanged("simulation"))  # Force simulation view setup
        
    def setupNewViews(self):
        """Setup all the new view components"""
        
        # Map Overview
        self.map_overview = sidebar.MapOverviewWidget(self)
        self.map_overview.sectionSelected.connect(self.onSectionSelected)
        self.view_stack.addWidget(self.map_overview)
        self.view_index_map["map_overview"] = self.view_stack.count() - 1
        self.views["map_overview"] = self.map_overview
        
        # Map View - Live Train Tracking
        self.map_view = analytics_views.MapViewWidget(self)
        self.view_stack.addWidget(self.map_view)
        self.view_index_map["map_view"] = self.view_stack.count() - 1
        self.views["map_view"] = self.map_view
        
        # Train Management
        self.train_management = sidebar.TrainManagementWidget(self)
        self.view_stack.addWidget(self.train_management)
        self.view_index_map["train_management"] = self.view_stack.count() - 1
        self.views["train_management"] = self.train_management
        
        # System Status
        self.system_status = sidebar.SystemStatusWidget(self)
        self.view_stack.addWidget(self.system_status)
        self.view_index_map["system_status"] = self.view_stack.count() - 1
        self.views["system_status"] = self.system_status
        
        # What-If Analysis
        self.whatif_analysis = analytics_views.WhatIfAnalysisWidget(self)
        self.view_stack.addWidget(self.whatif_analysis)
        self.view_index_map["whatif_analysis"] = self.view_stack.count() - 1
        self.views["whatif_analysis"] = self.whatif_analysis
        
        # KPI Dashboard - using the new comprehensive railway dashboard
        self.kpi_dashboard = analytics_views.KPIDashboardWidget(self)
        self.view_stack.addWidget(self.kpi_dashboard)
        self.view_index_map["kpi_dashboard"] = self.view_stack.count() - 1
        self.views["kpi_dashboard"] = self.kpi_dashboard
        
        # Audit Logs
        self.audit_logs = analytics_views.AuditLogsWidget(self)
        self.view_stack.addWidget(self.audit_logs)
        self.view_index_map["audit_logs"] = self.view_stack.count() - 1
        self.views["audit_logs"] = self.audit_logs
        
        # Settings view (placeholder)
        settings_widget = QtWidgets.QWidget()
        settings_layout = QtWidgets.QVBoxLayout(settings_widget)
        settings_label = QtWidgets.QLabel("Settings")
        settings_label.setAlignment(Qt.AlignCenter)
        settings_label.setStyleSheet("font-size: 24px; color: #666666;")
        settings_layout.addWidget(settings_label)
        
        self.view_stack.addWidget(settings_widget)
        self.view_index_map["settings"] = self.view_stack.count() - 1
        self.views["settings"] = settings_widget
        
        # Add AI Hints dock widget
        self.ai_hints_dock = ai_hints.AIHintsDockWidget(self)
        self.addDockWidget(Qt.RightDockWidgetArea, self.ai_hints_dock)
        
        # Set default view
        self.view_stack.setCurrentIndex(0)  # Start with simulation view
        self.current_view = "simulation"  # Explicitly set current view
        
        # Ensure bottom panels (trains & services) are visible for simulation
        self.ensureBottomPanelsVisible()
        
        # Ensure simulation dock panels are visible initially
        self.onViewChanged("simulation")
        
    def ensureBottomPanelsVisible(self):
        """Ensure trains and services panels are visible in simulation view"""
        print("Ensuring bottom panels visibility for simulation view...")
        
        # Only show bottom panels if we're in simulation view
        if hasattr(self, 'current_view') and self.current_view == "simulation":
            # Force visibility of bottom panels
            if hasattr(self, 'trainListPanel'):
                self.trainListPanel.show()
                print(f"Trains panel visible: {self.trainListPanel.isVisible()}")
            
            if hasattr(self, 'serviceListPanel'):
                self.serviceListPanel.show()
                print(f"Services panel visible: {self.serviceListPanel.isVisible()}")
            
            # Set trains as the default active tab
            if hasattr(self, 'trainListPanel'):
                self.trainListPanel.raise_()
        else:
            print("Not in simulation view - bottom panels should be hidden")
            
        # Ensure they can't be accidentally closed (but can be hidden in other views)
        if hasattr(self, 'trainListPanel'):
            self.trainListPanel.setFeatures(self.trainListPanel.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        if hasattr(self, 'serviceListPanel'):
            self.serviceListPanel.setFeatures(self.serviceListPanel.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        
    @QtCore.pyqtSlot(str)
    def onViewChanged(self, view_name):
        """Handle view changes from sidebar navigation"""
        if view_name in self.view_index_map:
            self.view_stack.setCurrentIndex(self.view_index_map[view_name])
            self.current_view = view_name
            
            # Panel visibility management based on view
            if view_name == "simulation":
                # SIMULATION VIEW - Show all panels
                print("Switching to simulation view - showing all panels")
                
                # Right-side panels
                self.trainInfoPanel.show()
                self.serviceInfoPanel.show() 
                self.placeInfoPanel.show()
                self.loggerPanel.show()
                
                # Bottom panels (Trains & Services) - ONLY visible in simulation view
                self.trainListPanel.show()
                self.serviceListPanel.show()
                
                # Ensure trains panel is the active tab
                self.trainListPanel.raise_()
                
                # AI hints available
                self.ai_hints_dock.show()
                
                print(f"Simulation panels visible: Trains={self.trainListPanel.isVisible()}, Services={self.serviceListPanel.isVisible()}")
                
            else:
                # OTHER VIEWS - Hide simulation-specific panels
                print(f"Switching to {view_name} view - hiding simulation panels")
                
                # Hide right-side simulation panels
                self.trainInfoPanel.hide()
                self.serviceInfoPanel.hide()
                self.placeInfoPanel.hide() 
                self.loggerPanel.hide()
                
                # Hide bottom panels (trains & services) - only for simulation view
                self.trainListPanel.hide()
                self.serviceListPanel.hide()
                
                # Hide AI hints in non-simulation views
                self.ai_hints_dock.hide()
                
                print(f"Bottom panels hidden in {view_name} view")
            
    @QtCore.pyqtSlot(str)
    def onSectionSelected(self, section_id):
        """Handle section selection from map overview"""
        # Switch to train management view and filter by section
        self.view_stack.setCurrentIndex(self.view_index_map["train_management"])
        self.current_view = "train_management"
        
        # In a real implementation, this would filter trains by section
        QtWidgets.QMessageBox.information(
            self, "Section Selected",
            f"Section {section_id} selected. Train management view filtered accordingly."
        )

    @staticmethod
    def instance():
        return MainWindow._self

    @QtCore.pyqtSlot()
    def onAfterShow(self):
        """Fires a few moments after window shows"""
        # FINAL enforcement of bottom panel visibility - only if in simulation view
        print("onAfterShow: Final bottom panels enforcement...")
        
        if hasattr(self, 'current_view') and self.current_view == "simulation":
            self.trainListPanel.setVisible(True)
            self.serviceListPanel.setVisible(True)
            self.trainListPanel.show()
            self.serviceListPanel.show()
            self.trainListPanel.raise_()
            print(f"Final check - Trains visible: {self.trainListPanel.isVisible()}")
            print(f"Final check - Services visible: {self.serviceListPanel.isVisible()}")
        else:
            print("Not in simulation view - skipping panel enforcement")
        
        if not settings.b(settings.INITIAL_SETUP, False):
            self.openSettingsDialog()

        if not self.fileName and settings.b(settings.LOAD_LAST, False):
            actions = self.openRecentAction.menu().actions()
            if actions:
                self.fileName = actions[0].text()

        if self.fileName:
            self.loadSimulation(self.fileName)

    def onOpenSimulation(self):
        d = opendialog.OpenDialog(self)
        d.openFile.connect(self.loadSimulation)
        d.connectToServer.connect(self.connectToServer)
        d.exec_()

    @QtCore.pyqtSlot(str)
    def loadSimulation(self, fileName=None):
        """This is where the simulation server is spawn"""
        if fileName:
            self.fileName = fileName
            if zipfile.is_zipfile(fileName):
                with zipfile.ZipFile(fileName) as zipArchive:
                    zipArchive.extract("simulation.json", path=tempfile.gettempdir())
                fileName = path.join(tempfile.gettempdir(), "simulation.json")

            QtWidgets.qApp.setOverrideCursor(Qt.WaitCursor)
            logLevel = "info"
            if settings.debug:
                logLevel = "dbug"

            if not self.simServer:
                cmd = settings.serverLoc
            else:
                cmd = self.simServer

            self.simulationClose()
            try:
                serverCmd = subprocess.Popen([cmd, "-loglevel", logLevel, fileName])
            except FileNotFoundError:
                QtWidgets.qApp.restoreOverrideCursor()
                QtWidgets.QMessageBox.critical(self, "Configuration Error",
                                               "ts2-sim-server executable not found in the server directory.\n"
                                               "Go to File->Settings to download it")
                raise
            except OSError as e:
                QtWidgets.qApp.restoreOverrideCursor()
                dialogs.ExceptionDialog.popupException(self, e)
                raise
            self.serverPID = serverCmd.pid
            settings.addRecent(self.fileName)
            time.sleep(1)
            QtWidgets.qApp.restoreOverrideCursor()
            self.connectToServer("localhost", "22222")
        else:
            self.onOpenSimulation()

    def connectToServer(self, host, port):
        QtWidgets.qApp.setOverrideCursor(Qt.WaitCursor)
        self.webSocket = WebSocketController("ws://%s:%s/ws" % (host, port), self)
        self.webSocket.connectionReady.connect(self.simulationLoad)
        # Propagate HTTP base URL to API-driven widgets
        try:
            self._http_base_url = f"http://{host}:{port}"
            if hasattr(self, "ai_hints_dock") and hasattr(self.ai_hints_dock, "hints_widget"):
                self.ai_hints_dock.hints_widget.provider.setBaseUrl(self._http_base_url)
            if hasattr(self, "system_status"):
                self.system_status._base_url = self._http_base_url
            if hasattr(self, "train_management"):
                self.train_management._base_url = self._http_base_url
            if hasattr(self, "kpi_dashboard") and hasattr(self.kpi_dashboard, "provider"):
                self.kpi_dashboard.provider.setBaseUrl(self._http_base_url)
        except Exception:
            pass

    @QtCore.pyqtSlot()
    def simulationLoad(self):
        def load_sim(data):
            simData = json.dumps(data)
            self.simulation = simulation.load(self, io.StringIO(simData))
            # Title is now handled in simulationConnectSignals
            self.setWindowTitle(self.tr(
                "TrackTitans - Railway Operations - %s") % self.simulation.option("title"))
            self.simulationConnectSignals()
            self.webSocket.sendRequest("server", "renotify")
            self.simulationLoaded.emit(self.simulation)

            self.refreshRecent()
            self.setControlsDisabled(False)

            QtWidgets.QApplication.restoreOverrideCursor()

        self.webSocket.sendRequest("simulation", "dump", callback=load_sim)
        
        # Update sidebar connection status
        self.sidebar.setConnectionStatus(True)

    def simulationConnectSignals(self):
        """Connects the signals and slots to the simulation."""

        # Set models
        self.trainInfoView.setModel(self.simulation.selectedTrainModel)
        self.serviceInfoView.setModel(self.simulation.selectedServiceModel)
        self.loggerView.setModel(self.simulation.messageLogger)
        # Set scene
        self.view.setScene(self.simulation.scene)
        # TrainListView
        self.trainListView.trainSelected.connect(
            self.simulation.trainSelected
        )
        self.simulation.trainSelected.connect(
            self.simulation.selectedTrainModel.setTrainByTrainId
        )
        self.simulation.trainSelected.connect(
            self.serviceListView.updateServiceSelection
        )
        self.trainListView.trainSelected.connect(self.centerViewOnTrain)
        # ServiceListView
        self.serviceListView.serviceSelected.connect(
            self.simulation.selectedServiceModel.setServiceCode
        )
        self.serviceListView.serviceSelected.connect(
            self.onServiceSelected
        )
        # TrainInfoView
        self.simulation.trainStatusChanged.connect(
            self.trainInfoView.model().update
        )
        self.simulation.timeChanged.connect(
            self.trainInfoView.model().updateSpeed
        )
        # Place view
        placeitem.Place.selectedPlaceModel.modelReset.connect(
            self.onPlaceSelected
        )
        # MessageLogger
        self.simulation.messageLogger.rowsInserted.connect(
            self.loggerView.scrollToBottom
        )
        # Panel - Connect to modern header
        self.simulation.timeChanged.connect(self.modern_header.setTime)
        self.simulation.simulationPaused.connect(self.modern_header.setPauseState)
        self.simulation.scorer.scoreChanged.connect(self.modern_header.setScore)
        self.modern_header.setScore(self.simulation.scorer.score)
        self.simulation.timeFactorChanged.connect(self.updateSpeedDisplay)
        
        # Set initial values in header
        initial_speed = int(self.simulation.option("timeFactor"))
        self.modern_header.setSpeed(initial_speed)
        self.modern_header.setSimulationTitle(self.simulation.option("title"))

        # Menus
        self.saveGameAsAction.setEnabled(True)
        self.propertiesAction.setEnabled(True)

        # WebSocket listeners for server events impacting UI panels
        try:
            # AI Hints updates (new server event) and suggestions engine refresh
            # Disable push-driven refresh to avoid repeated GETs; rely on timer and manual refresh
            # self.webSocket.registerHandler("NEW_AI_HINTS", self, lambda _self, data: self.ai_hints_dock.hints_widget.provider.refreshHints(recompute=True))
            # self.webSocket.registerHandler("suggestionsUpdated", self, lambda _self, data: self.ai_hints_dock.hints_widget.provider.refreshHints(recompute=True))

            # Signal status changes -> refresh System Status view table
            self.webSocket.registerHandler("SIGNAL_STATUS_CHANGED", self, lambda _self, data: getattr(self, "system_status", None) and self.system_status.loadOverviewFromApi())
            self.webSocket.registerHandler("signalAspectChanged", self, lambda _self, data: getattr(self, "system_status", None) and self.system_status.loadOverviewFromApi())
        except Exception:
            pass

    def simulationDisconnect(self):
        """Disconnects the simulation for deletion."""
        # Unset models
        self.trainListView.setModel(None)
        self.trainInfoView.setModel(None)
        self.serviceInfoView.setModel(None)
        self.serviceListView.setModel(None)
        self.loggerView.setModel(None)
        self.placeInfoView.setModel(None)
        # Unset scene
        self.view.setScene(None)
        # Disconnect signals
        try:
            self.simulation.trainSelected.disconnect()
        except TypeError:
            pass
        try:
            self.trainListView.trainSelected.disconnect()
        except TypeError:
            pass
        try:
            self.serviceListView.serviceSelected.disconnect()
        except TypeError:
            pass
        try:
            self.simulation.trainStatusChanged.disconnect()
        except TypeError:
            pass
        try:
            self.simulation.timeChanged.disconnect()
        except TypeError:
            pass
        try:
            self.simulation.messageLogger.rowsInserted.disconnect()
        except TypeError:
            pass
        try:
            self.simulation.scorer.scoreChanged.disconnect()
        except TypeError:
            pass
        # Panel
        try:
            self.simulation.timeChanged.disconnect()
        except TypeError:
            pass
        try:
            self.simulation.simulationPaused.disconnect()
        except TypeError:
            pass
        try:
            self.simulation.scorer.scoreChanged.disconnect()
        except TypeError:
            pass
        self.scoreDisplay.display(0)
        try:
            self.simulation.timeFactorChanged.disconnect()
        except TypeError:
            pass
        try:
            self.buttPause.toggled.disconnect()
        except TypeError:
            pass
        # Reset header controls
        if hasattr(self, 'modern_header'):
            self.modern_header.setSpeed(1)
            self.modern_header.setScore(0) 
            self.modern_header.setPauseState(True)
            self.modern_header.setSimulationTitle(None)
            
        # Ensure bottom panels remain visible even when simulation closes
        self.ensureBottomPanelsVisible()

        # Menus
        self.saveGameAsAction.setEnabled(False)
        self.propertiesAction.setEnabled(False)
        # Clock
        self.clockWidget.setTime(QtCore.QTime())

        self.webSocket.removeHandlers()

    def simulationClose(self):
        if self.simulation is not None:
            self.simulationDisconnect()
            self.simulation = None
            self.fileName = None
            if self.serverPID:
                os.kill(self.serverPID, signal.SIGTERM)
                self.serverPID = None
            self.setControlsDisabled(True)
            
        # Update sidebar connection status
        self.sidebar.setConnectionStatus(False)

    @QtCore.pyqtSlot()
    def saveGame(self):
        """Saves the current game to file."""
        if self.simulation is not None:
            fileName, _ = QtWidgets.QFileDialog.getSaveFileName(
                self,
                self.tr("Save the simulation as"),
                QtCore.QDir.homePath(),
                self.tr("TS2 game files (*.tsg)")
            )
            if fileName != "":
                QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)
                # try:
                self.simulation.saveGame(fileName)
                # except:
                #     dialogs.ExceptionDialog.popupException(self)
                settings.addRecent(fileName)
                QtWidgets.QApplication.restoreOverrideCursor()

    @QtCore.pyqtSlot(int)
    def zoom(self, percent):
        transform = QtGui.QTransform()
        transform.scale(percent / 100, percent / 100)
        self.view.setTransform(transform)

    @QtCore.pyqtSlot()
    def showAboutBox(self):
        """Shows the about box"""
        QtWidgets.QMessageBox.about(self, self.tr("About TS2"), self.tr(
            "TS2 is a train signalling simulation.\n\n"
            "Version %s\n\n"
            "Copyright 2008-%s, NPi (%s)\n"
            "%s\n\n"
            "TS2 is licensed under the terms of the GNU GPL v2\n""") %
                                    (__VERSION__,
                                     QtCore.QDate.currentDate().year(),
                                     __ORG_CONTACT__,
                                     __PROJECT_WWW__))
        if self.editorOpened:
            self.editorWindow.activateWindow()

    @QtCore.pyqtSlot(QtCore.QPoint)
    def showContextMenu(self, pos):
        if self.sender() == self.trainInfoView:
            train = self.trainInfoView.model().train
            if train is not None:
                train.showTrainActionsMenu(self.trainInfoView,
                                           self.trainInfoView.mapToGlobal(pos))

    @QtCore.pyqtSlot()
    def onEditorCurrent(self):
        if self.fileName:
            self.openEditor(fileName=self.fileName)

    @QtCore.pyqtSlot()
    def openEditor(self, fileName=None):
        """This slot opens the editor window if it is not already opened"""
        if not self.editorOpened:
            self.editorWindow = editorwindow.EditorWindow(self, fileName=fileName)
            self.editorWindow.simulationConnect()
            self.editorWindow.closed.connect(self.onEditorClosed)
            self.editorOpened = True
            self.editorWindow.show()
        else:
            self.editorWindow.activateWindow()

    @QtCore.pyqtSlot()
    def onEditorClosed(self):
        self.editorOpened = False

    @QtCore.pyqtSlot(bool)
    def checkPauseButton(self, paused):
        """Update pause button state and text based on simulation state"""
        if hasattr(self, 'modern_header'):
            self.modern_header.setPauseState(paused)
    
    def updateSpeedDisplay(self, value):
        """Update speed display when simulation speed changes"""
        self.current_speed = value
        if hasattr(self, 'modern_header'):
            self.modern_header.setSpeed(value)
    
    # New header signal handlers
    def onSpeedChanged(self, speed):
        """Handle speed change from modern header"""
        if hasattr(self, 'simulation') and self.simulation:
            self.simulation.setTimeFactor(speed)
            
    def onPauseToggled(self, paused):
        """Handle pause toggle from modern header"""
        if hasattr(self, 'simulation') and self.simulation:
            self.simulation.pause(paused)

    @QtCore.pyqtSlot()
    def onRestartRequested(self):
        """Restart simulation via WebSocket and update UI state based on response."""
        if not hasattr(self, 'webSocket') or not self.webSocket:
            QtWidgets.QMessageBox.critical(self, "Not Connected", "No connection to simulation server.")
            return

        # Disable button and show busy cursor
        try:
            if hasattr(self, 'modern_header') and hasattr(self.modern_header, 'restart_btn'):
                self.modern_header.restart_btn.setEnabled(False)
        except Exception:
            pass
        QtWidgets.QApplication.setOverrideCursor(Qt.WaitCursor)

        def on_restart_response(msg):
            QtWidgets.QApplication.restoreOverrideCursor()
            try:
                if hasattr(self, 'modern_header') and hasattr(self.modern_header, 'restart_btn'):
                    self.modern_header.restart_btn.setEnabled(True)
            except Exception:
                pass

            ok = bool(msg and msg.get("status") == "OK")
            if ok:
                # Ask server to renotify current state
                try:
                    self.webSocket.sendRequest('server', 'renotify')
                except Exception:
                    pass

                # Query started state to reflect Pause/Start button correctly
                def on_is_started(state):
                    try:
                        started = bool(state)
                        if hasattr(self, 'modern_header'):
                            self.modern_header.setPauseState(not started)
                    except Exception:
                        pass

                try:
                    self.webSocket.sendRequest('simulation', 'isStarted', callback=on_is_started)
                except Exception:
                    pass

                QtWidgets.QMessageBox.information(self, "Simulation Restarted", msg.get("message", "Simulation restarted successfully"))
            else:
                err_msg = (msg and msg.get("message")) or "Unknown error"
                QtWidgets.QMessageBox.critical(self, "Restart Failed", f"Failed to restart simulation: {err_msg}")

        # Auto-start after restart to match previous behavior
        self.webSocket.sendRequest('simulation', 'restart', params={"autoStart": True}, callback=on_restart_response)

    @QtCore.pyqtSlot()
    def openPropertiesDialog(self):
        """Pops-up the simulation properties dialog."""
        if self.simulation is not None:
            propertiesDialog = dialogs.PropertiesDialog(self, self.simulation)
            propertiesDialog.exec_()

    @QtCore.pyqtSlot(str)
    def openReassignServiceWindow(self, trainId):
        """Opens the reassign service window."""
        if self.simulation is not None:
            dialogs.ServiceAssignDialog.reassignServiceToTrain(
                self.simulation, trainId
            )

    @QtCore.pyqtSlot(str)
    def openSplitTrainWindow(self, trainId):
        """Opens the split train dialog window."""
        if self.simulation is not None:
            dialogs.SplitTrainDialog.getSplitIndexPopUp(
                self.simulation.trains[trainId]
            )

    def refreshRecent(self):
        """Reload the recent menu"""
        menu = self.openRecentAction.menu()
        menu.clear()
        act = []
        for fileName in settings.getRecent():
            if not fileName:
                continue
            if os.path.exists(fileName):
                act.append(menu.addAction(fileName))

    def onRecent(self, act):
        """Open a  recent item"""
        self.loadSimulation(fileName=act.iconText())

    def closeEvent(self, event):
        """Save window postions on close"""
        settings.saveWindow(self)
        settings.sync()
        self.simulationClose()
        if self.webSocket:
            self.webSocket.wsThread.exit()
        super().closeEvent(event)

    def onWheelChanged(self, direction):
        """Handle scrollwheel on canvas, sent from
        :class:`~ts2.gui.widgets.XGraphicsView` """
        percent = self.zoomWidget.spinBox.value()
        self.zoomWidget.spinBox.setValue(percent + (direction * 10))

    def onWwwAction(self, act):
        url = act.property("url")
        QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    def _make_toolbar_group(self, title, bg=None, fg=None):
        """Creates a toolbar containing a `ToolBarGroup`"""
        tbar = QtWidgets.QToolBar()
        tbar.setObjectName("toolbar_" + title)
        tbar.setFloatable(False)
        tbar.setMovable(True)

        tbg = widgets.ToolBarGroup(self, title=title, bg=bg, fg=fg)
        tbar.addWidget(tbg)
        return tbar, tbg

    def onServiceSelected(self, serviceCode):
        serv = self.simulation.service(serviceCode)
        self.lblServiceInfoCode.setText(serviceCode)
        self.lblServiceInfoDescription.setText(serv.description)

    def onPlaceSelected(self):
        place = placeitem.Place.selectedPlaceModel.place
        if place:
            self.lblPlaceInfoName.setText(place.name)

    def setControlsDisabled(self, state):
        """Enable/disable header controls based on simulation state"""
        # Enable/disable modern header controls
        if hasattr(self, 'modern_header'):
            self.modern_header.setControlsEnabled(not state)
            
        # Handle editor action separately
        if not state and self.fileName:
            self.modern_header.edit_btn.setEnabled(True)
        else:
            self.modern_header.edit_btn.setEnabled(False)

    def openSettingsDialog(self):
        d = settingsdialog.SettingsDialog(self)
        d.exec_()

    def centerViewOnTrain(self, trainId):
        """Centers the graphics view on the given train."""
        if self.simulation:
            train = self.simulation.trains[int(trainId)]
            if train.isOnScenery():
                trackItem = train.trainHead.trackItem
                self.view.centerOn(trackItem.graphicsItem)

    def eventFilter(self, obj, event):
        """Handle window resize events for responsive layout"""
        if obj is self and event.type() == QtCore.QEvent.Resize:
            self.handleWindowResize(event.size())
        return super().eventFilter(obj, event)
        
    def handleWindowResize(self, size):
        """Handle window resize for responsive layout adjustments"""
        width = size.width()
        height = size.height()
        
        # Adjust layout based on window size
        if width < 1300:  # Smaller window
            # Make header more compact
            if hasattr(self, 'modern_header'):
                # Could adjust header sections here if needed
                pass
                
            # Ensure view stack still has enough space
            if hasattr(self, 'view_stack'):
                self.view_stack.setMinimumWidth(max(600, width - 300))
        else:  # Larger window
            # Restore normal sizing
            if hasattr(self, 'view_stack'):
                self.view_stack.setMinimumWidth(900)


def wsOnMessage(ws, message):
    if settings.debug:
        print("< %s" % message)
    ws.onMessage(message)


def wsOnError(ws, error):
    print("WS Error", error)


def wsOnClose(ws):
    QtCore.qDebug("WS Closed")
    ws.connectionClosed.emit()


class WebSocketConnection(websocket.WebSocketApp, QtCore.QObject):

    def __init__(self, controller, url):
        websocket.WebSocketApp.__init__(self, url, on_message=wsOnMessage, on_error=wsOnError, on_close=wsOnClose)
        QtCore.QObject.__init__(self)
        self.controller = controller
        self.ready = False

    messageReceived = QtCore.pyqtSignal(str)
    connectionReady = QtCore.pyqtSignal()
    connectionClosed = QtCore.pyqtSignal()

    def onMessage(self, message):
        self.messageReceived.emit(message)


class WebSocketController(QtCore.QObject):

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self._requests = []
        self._callbacks = {}
        self._handlers = {}
        self._counter = 1
        self.conn = WebSocketConnection(self, url)
        self.conn.messageReceived.connect(self.executeCallback)
        self.conn.connectionReady.connect(self.connectionReady)
        self.conn.connectionClosed.connect(self.onClosed)

        def login(w):
            def setReady(msg):
                if msg["status"] == "OK":
                    w.connectionReady.emit()
                else:
                    raise Exception("Error while connecting to simulation server", msg["message"])

            w.controller.sendRequest("server", "register", {"type": "client", "token": "client-secret"},
                                     callback=setReady)

        self.conn.on_open = login
        self.wsThread = WebSocketThread(self.conn)
        self.wsThread.start()

    connectionReady = QtCore.pyqtSignal()

    def sendRequest(self, obj, action, params=None, callback=None):
        """Send a websocket request. Response will be handled by given callback.
        :param obj: server object to call
        :param action: server action to execute
        :param params: parameters to send for action as dict
        :param callback: function taking a msg dict as argument
        """
        data = {
            "id": self._counter,
            "object": obj,
            "action": action,
            "params": params,
        }
        msg = json.dumps(data)
        if settings.debug:
            print("> %s" % data)
        self.conn.send(msg)
        self._callbacks[self._counter] = callback
        self._counter += 1

    @QtCore.pyqtSlot(str)
    def executeCallback(self, message):
        """Call the callback with the given id and remove it from the registry.
        :param message: raw JSON message received
        """
        msg = json.loads(message)
        if msg["msgType"] == "response":
            msgID = msg["id"]
            msgData = msg["data"]
            if msgID not in self._callbacks:
                if settings.debug:
                    print("msgID not in registry: %s" % msgID)
                return
            if self._callbacks[msgID]:
                self._callbacks[msgID](msgData)
            del self._callbacks[msgID]
        elif msg["msgType"] == "notification":
            msgData = msg["data"]
            if self._handlers.get(msgData["name"]):
                hData = self._handlers[msgData["name"]]
                hData[1](hData[0], msgData["object"])

    def registerHandler(self, eventName, sim, handler):
        self.sendRequest("server", "addListener", params={"event": "%s" % eventName})
        self._handlers[eventName] = (sim, handler)

    def removeHandlers(self):
        for eventName in self._handlers.keys():
            self.sendRequest("server", "removeListener", params={"event": "%s" % eventName})
            self._handlers = {}

    def onClosed(self):
        QtWidgets.QApplication.restoreOverrideCursor()
        mainWindow = self.parent()
        if not mainWindow.fileName:
            # Only notify if we are connected to a network simulation
            QtWidgets.QMessageBox.critical(
                mainWindow,
                mainWindow.tr("Connection closed"),
                mainWindow.tr("The server closed the connection to the simulation."),
                QtWidgets.QMessageBox.Ok
            )
        mainWindow.simulationClose()


class WebSocketThread(QtCore.QThread):

    def __init__(self, ws, parent=None):
        super(WebSocketThread, self).__init__(parent)
        self.websocket = ws

    def run(self):
        self.websocket.run_forever()
