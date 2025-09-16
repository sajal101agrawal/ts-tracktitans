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
import random
import math
from datetime import datetime, timedelta
from .charts import (SparklineChart, BarChart, LineChart, HeatmapChart, 
                    GaugeChart, KPITile, generateMockData)


class RailwayKPIDashboard(QtWidgets.QWidget):
    """Comprehensive Railway Operations KPI Dashboard"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kpi_tiles = {}
        self.charts = {}
        self.mock_data = generateMockData()
        self.setupUI()
        self.updateAllKPIs()
        
        # Auto-refresh timer
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.updateAllKPIs)
        self.refresh_timer.start(30000)  # 30 seconds
        
    def setupUI(self):
        """Setup comprehensive KPI dashboard UI"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        self.setupHeader(main_layout)
        
        # Top KPI Strip (always visible)
        self.setupKPIStrip(main_layout)
        
        # Main content area
        content_splitter = QtWidgets.QSplitter(Qt.Horizontal)
        
        # Left Filters Panel
        self.setupFiltersPanel(content_splitter)
        
        # Center Charts Area  
        self.setupCenterChartsArea(content_splitter)
        
        # Right Panel - Recommendations
        self.setupRightPanel(content_splitter)
        
        # Set splitter proportions
        content_splitter.setSizes([200, 600, 250])
        main_layout.addWidget(content_splitter)
        
        # Bottom Diagnostics Row
        self.setupBottomDiagnostics(main_layout)
        
    def setupHeader(self, main_layout):
        """Setup header with title and controls"""
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        
        title = QtWidgets.QLabel("TrackTitans - Railway Operations Dashboard")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: #343a40; margin-bottom: 10px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Time range selector
        header_layout.addWidget(QtWidgets.QLabel("Time Range:"))
        self.time_combo = QtWidgets.QComboBox()
        self.time_combo.addItems(["Last Hour", "Last 6 Hours", "Today", "Last 24h", "Last Week"])
        self.time_combo.setCurrentText("Today")
        header_layout.addWidget(self.time_combo)
        
        # Export button
        self.export_btn = QtWidgets.QPushButton("Export Report")
        self.export_btn.clicked.connect(self.exportReport)
        self.export_btn.setStyleSheet("QPushButton { padding: 6px 12px; }")
        header_layout.addWidget(self.export_btn)
        
        main_layout.addWidget(header)
        
    def setupKPIStrip(self, main_layout):
        """Setup top KPI strip with key metrics"""
        kpi_frame = QtWidgets.QFrame()
        kpi_frame.setStyleSheet("""
            QFrame { 
                background-color: #f8f9fa; 
                border: 1px solid #dee2e6; 
                border-radius: 4px;
                margin: 5px 0; 
            }
        """)
        kpi_layout = QtWidgets.QHBoxLayout(kpi_frame)
        kpi_layout.setContentsMargins(10, 10, 10, 10)
        
        # Define top KPIs (always visible)
        top_kpis = [
            ("rtp", "Right-Time Performance", "%"),
            ("avg_delay", "Avg Delay", "min"), 
            ("p90_delay", "P90 Delay", "min"),
            ("throughput", "Throughput", "tr/h"),
            ("conflicts", "Open Conflicts", "count"),
            ("mttr", "MTTR-C", "min"),
            ("acceptance", "Accept Rate", "%")
        ]
        
        for key, name, unit in top_kpis:
            tile = KPITile(name, "--", unit)
            self.kpi_tiles[key] = tile
            kpi_layout.addWidget(tile)
            
        main_layout.addWidget(kpi_frame)
        
    def setupFiltersPanel(self, splitter):
        """Setup left filters panel"""
        filters_widget = QtWidgets.QWidget()
        filters_widget.setStyleSheet("QWidget { background-color: white; }")
        filters_layout = QtWidgets.QVBoxLayout(filters_widget)
        filters_layout.setContentsMargins(10, 10, 10, 10)
        
        # Title
        title = QtWidgets.QLabel("Filters")
        title.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 15px; color: #343a40;")
        filters_layout.addWidget(title)
        
        # Section filter
        filters_layout.addWidget(QtWidgets.QLabel("Section:"))
        self.section_combo = QtWidgets.QComboBox()
        self.section_combo.addItems(["All Sections", "Central", "Northern", "Southern", "Eastern"])
        filters_layout.addWidget(self.section_combo)
        filters_layout.addSpacing(10)
        
        # Direction filter
        filters_layout.addWidget(QtWidgets.QLabel("Direction:"))
        self.direction_combo = QtWidgets.QComboBox()
        self.direction_combo.addItems(["Both", "Up", "Down"])
        filters_layout.addWidget(self.direction_combo)
        filters_layout.addSpacing(10)
        
        # Train class filter
        filters_layout.addWidget(QtWidgets.QLabel("Train Class:"))
        self.class_combo = QtWidgets.QComboBox()
        self.class_combo.addItems(["All Classes", "Mail/Express", "Suburban", "Freight"])
        filters_layout.addWidget(self.class_combo)
        filters_layout.addSpacing(10)
        
        # Incident type filter
        filters_layout.addWidget(QtWidgets.QLabel("Incident Type:"))
        self.incident_combo = QtWidgets.QComboBox()
        self.incident_combo.addItems(["All", "Signal Failure", "Track Work", "Weather", "Rolling Stock"])
        filters_layout.addWidget(self.incident_combo)
        
        filters_layout.addStretch()
        
        splitter.addWidget(filters_widget)
        
    def setupCenterChartsArea(self, splitter):
        """Setup center area with map and timeline"""
        center_widget = QtWidgets.QWidget()
        center_widget.setStyleSheet("QWidget { background-color: white; }")
        center_layout = QtWidgets.QVBoxLayout(center_widget)
        center_layout.setContentsMargins(10, 10, 10, 10)
        
        # Map section
        map_group = QtWidgets.QGroupBox("Network Map - Block Hotspots")
        map_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        map_layout = QtWidgets.QVBoxLayout(map_group)
        
        # Simplified map representation
        map_frame = QtWidgets.QFrame()
        map_frame.setStyleSheet("""
            QFrame { 
                background-color: #f0f8ff; 
                border: 1px solid #ccc; 
                border-radius: 4px;
            }
        """)
        map_frame.setMinimumHeight(200)
        map_inner_layout = QtWidgets.QVBoxLayout(map_frame)
        
        map_label = QtWidgets.QLabel("Network Overview\nBlock conflict indicators and platform utilization\nClick sections for detailed analysis")
        map_label.setAlignment(Qt.AlignCenter)
        map_label.setStyleSheet("color: #666; padding: 20px; font-size: 13px;")
        map_inner_layout.addWidget(map_label)
        
        # Add some mock network elements
        elements_layout = QtWidgets.QHBoxLayout()
        for i, (name, status) in enumerate([("Central", "Normal"), ("North", "Busy"), ("South", "Alert")]):
            element = QtWidgets.QFrame()
            element.setFixedSize(80, 60)
            color = "#495057" if status == "Normal" else "#6c757d" if status == "Busy" else "#868e96"
            element.setStyleSheet(f"QFrame {{ background-color: {color}; border-radius: 4px; }}")
            
            element_layout = QtWidgets.QVBoxLayout(element)
            element_layout.addWidget(QtWidgets.QLabel(name))
            element_layout.addWidget(QtWidgets.QLabel(status))
            
            elements_layout.addWidget(element)
            
        map_inner_layout.addLayout(elements_layout)
        map_layout.addWidget(map_frame)
        center_layout.addWidget(map_group)
        
        # Timeline section
        timeline_group = QtWidgets.QGroupBox("Block/Platform Occupancy Timeline")
        timeline_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        timeline_layout = QtWidgets.QVBoxLayout(timeline_group)
        
        # Platform heatmap
        self.platform_heatmap = HeatmapChart()
        self.platform_heatmap.setMinimumHeight(150)
        timeline_layout.addWidget(self.platform_heatmap)
        
        center_layout.addWidget(timeline_group)
        
        splitter.addWidget(center_widget)
        
    def setupRightPanel(self, splitter):
        """Setup right panel with recommendations funnel"""
        right_widget = QtWidgets.QWidget()
        right_widget.setStyleSheet("QWidget { background-color: white; }")
        right_layout = QtWidgets.QVBoxLayout(right_widget)
        right_layout.setContentsMargins(10, 10, 10, 10)
        
        # Recommendations funnel
        funnel_group = QtWidgets.QGroupBox("Recommendation Funnel")
        funnel_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        funnel_layout = QtWidgets.QVBoxLayout(funnel_group)
        
        # Funnel chart
        self.funnel_chart = BarChart()
        self.funnel_chart.setMinimumHeight(120)
        funnel_layout.addWidget(self.funnel_chart)
        
        # Override reasons
        override_label = QtWidgets.QLabel("Top Override Reasons:")
        override_label.setStyleSheet("font-weight: bold; margin-top: 10px; color: #343a40;")
        funnel_layout.addWidget(override_label)
        
        override_reasons = ["Manual dispatcher preference", "Local knowledge", "Passenger priority"]
        for reason in override_reasons:
            reason_label = QtWidgets.QLabel(f"• {reason}")
            reason_label.setStyleSheet("margin-left: 10px; color: #666; font-size: 12px;")
            funnel_layout.addWidget(reason_label)
            
        right_layout.addWidget(funnel_group)
        
        # Current alerts
        alerts_group = QtWidgets.QGroupBox("Current Alerts")
        alerts_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        alerts_layout = QtWidgets.QVBoxLayout(alerts_group)
        
        alert_items = [
            ("Platform 3: High utilization (92%)", "#6c757d"),
            ("Section B: Approaching capacity", "#6c757d"),
            ("Signal 42: Maintenance due", "#6c757d")
        ]
        
        for alert, color in alert_items:
            alert_frame = QtWidgets.QFrame()
            alert_frame.setStyleSheet(f"QFrame {{ background-color: #f8f9fa; border-left: 3px solid {color}; padding: 5px; margin: 2px 0; }}")
            alert_layout = QtWidgets.QHBoxLayout(alert_frame)
            
            alert_label = QtWidgets.QLabel(alert)
            alert_label.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: bold;")
            alert_layout.addWidget(alert_label)
            
            alerts_layout.addWidget(alert_frame)
            
        right_layout.addWidget(alerts_group)
        right_layout.addStretch()
        
        splitter.addWidget(right_widget)
        
    def setupBottomDiagnostics(self, main_layout):
        """Setup bottom row with diagnostic charts"""
        diagnostics_frame = QtWidgets.QFrame()
        diagnostics_frame.setStyleSheet("QFrame { background-color: white; border: 1px solid #dee2e6; border-radius: 4px; }")
        diagnostics_layout = QtWidgets.QHBoxLayout(diagnostics_frame)
        diagnostics_layout.setContentsMargins(10, 10, 10, 10)
        
        # Delay cause chart
        delay_group = QtWidgets.QGroupBox("Delay Causes")
        delay_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        delay_layout = QtWidgets.QVBoxLayout(delay_group)
        
        self.delay_chart = BarChart()
        self.delay_chart.setFixedHeight(120)
        delay_layout.addWidget(self.delay_chart)
        
        diagnostics_layout.addWidget(delay_group)
        
        # Headway control chart
        headway_group = QtWidgets.QGroupBox("Headway Compliance")
        headway_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        headway_layout = QtWidgets.QVBoxLayout(headway_group)
        
        self.headway_chart = LineChart()
        self.headway_chart.setFixedHeight(120)
        headway_layout.addWidget(self.headway_chart)
        
        diagnostics_layout.addWidget(headway_group)
        
        # Performance trend
        trend_group = QtWidgets.QGroupBox("RTP Trend (24h)")
        trend_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        trend_layout = QtWidgets.QVBoxLayout(trend_group)
        
        self.rtp_trend = LineChart()
        self.rtp_trend.setFixedHeight(120)
        trend_layout.addWidget(self.rtp_trend)
        
        diagnostics_layout.addWidget(trend_group)
        
        # Solver latency
        latency_group = QtWidgets.QGroupBox("System Performance")
        latency_group.setStyleSheet("QGroupBox { font-weight: bold; }")
        latency_layout = QtWidgets.QVBoxLayout(latency_group)
        
        latency_stats = QtWidgets.QWidget()
        stats_layout = QtWidgets.QVBoxLayout(latency_stats)
        
        stats = [
            ("Solver Latency:", "2.3s avg"),
            ("P90 Latency:", "8.1s"),
            ("P99 Latency:", "15.2s"),
            ("Success Rate:", "99.2%")
        ]
        
        for label, value in stats:
            row = QtWidgets.QHBoxLayout()
            row.addWidget(QtWidgets.QLabel(label))
            value_label = QtWidgets.QLabel(value)
            value_label.setStyleSheet("font-weight: bold; color: #495057;")
            row.addWidget(value_label)
            stats_layout.addLayout(row)
            
        latency_layout.addWidget(latency_stats)
        diagnostics_layout.addWidget(latency_group)
        
        main_layout.addWidget(diagnostics_frame)
        
    def updateAllKPIs(self):
        """Update all KPI values and charts with realistic railway data"""
        # Generate realistic KPI values based on time of day
        current_hour = datetime.now().hour
        is_peak = current_hour in [7, 8, 9, 17, 18, 19]  # Peak hours
        
        # Right-Time Performance (target ≥85%)
        rtp_base = 82 if is_peak else 91
        rtp = max(72, min(96, rtp_base + random.uniform(-4, 4)))
        
        # Average Delay (target <6-8 min)
        delay_base = 8.5 if is_peak else 4.2
        avg_delay = max(1.5, delay_base + random.uniform(-1.5, 2.5))
        
        # P90 Delay (target <12-15 min)
        p90_delay = avg_delay * 1.9 + random.uniform(3, 6)
        
        # Throughput (trains per hour)
        throughput_base = 22 if is_peak else 16
        throughput = throughput_base + random.randint(-3, 4)
        
        # Open Conflicts (should be minimal)
        conflicts = random.randint(0, 6) if is_peak else random.randint(0, 2)
        
        # MTTR-C (target <5 min)
        mttr = random.uniform(3.8, 8.2) if is_peak else random.uniform(2.1, 5.5)
        
        # Acceptance Rate (target >70%)
        acceptance = random.uniform(68, 85) if is_peak else random.uniform(78, 92)
        
        # Update KPI tiles with appropriate color coding
        self.updateKPITile("rtp", rtp, random.uniform(-2.5, 1.8), 
                          self.getKPIColor(rtp, 85, 75))
        self.updateKPITile("avg_delay", avg_delay, random.uniform(-1.2, 1.5), 
                          self.getKPIColor(avg_delay, 6, 8, reverse=True))
        self.updateKPITile("p90_delay", p90_delay, random.uniform(-0.8, 2.2), 
                          self.getKPIColor(p90_delay, 12, 15, reverse=True))
        self.updateKPITile("throughput", throughput, random.uniform(-1.5, 3.0), "#495057")
        self.updateKPITile("conflicts", conflicts, random.uniform(-2.0, 1.0), 
                          self.getKPIColor(conflicts, 1, 3, reverse=True))
        self.updateKPITile("mttr", mttr, random.uniform(-0.8, 0.5), 
                          self.getKPIColor(mttr, 5, 7, reverse=True))
        self.updateKPITile("acceptance", acceptance, random.uniform(-1.5, 4.2), 
                          self.getKPIColor(acceptance, 70, 60))
        
        # Update charts
        self.updateCharts()
        
    def updateKPITile(self, key, value, delta, color):
        """Update a specific KPI tile"""
        if key in self.kpi_tiles:
            tile = self.kpi_tiles[key]
            
            # Format value based on type
            if isinstance(value, float):
                formatted_value = f"{value:.1f}" if value < 100 else f"{value:.0f}"
            else:
                formatted_value = str(int(value))
                
            # Generate realistic trend data
            base_val = value
            trend_data = []
            for i in range(20):
                variation = random.uniform(-base_val*0.08, base_val*0.08)
                trend_val = max(0, base_val + variation + math.sin(i/3) * base_val * 0.05)
                trend_data.append(trend_val)
            
            tile.updateValue(formatted_value, delta, trend_data)
            tile.setValueColor(color)
            
    def getKPIColor(self, value, green_threshold, red_threshold, reverse=False):
        """Get color based on KPI thresholds - minimal color scheme"""
        if reverse:
            if value <= green_threshold:
                return "#495057"  # Dark gray (good)
            elif value <= red_threshold:
                return "#6c757d"  # Medium gray (caution)
            else:
                return "#868e96"  # Light gray (poor)
        else:
            if value >= green_threshold:
                return "#495057"  # Dark gray (good)
            elif value >= red_threshold:
                return "#6c757d"  # Medium gray (caution)
            else:
                return "#868e96"  # Light gray (poor)
                
    def updateCharts(self):
        """Update all dashboard charts with realistic railway data"""
        # Update platform heatmap (8 platforms x 24 hours)
        # Higher values during peak hours
        current_hour = datetime.now().hour
        heatmap_data = []
        
        for platform in range(8):
            platform_data = []
            for hour in range(24):
                # Peak hours have higher utilization
                if hour in [7, 8, 9, 17, 18, 19]:
                    base_util = random.randint(60, 95)
                elif hour in [10, 11, 16, 20]:
                    base_util = random.randint(40, 70)
                else:
                    base_util = random.randint(10, 40)
                    
                platform_data.append(base_util)
            heatmap_data.append(platform_data)
            
        self.platform_heatmap.setData(heatmap_data, 
                                    [f"Platform {i+1}" for i in range(8)],
                                    [f"{i:02d}:00" for i in range(24)])
        
        # Update recommendation funnel
        base_detected = random.randint(40, 55)
        funnel_data = [
            base_detected,  # Detected
            int(base_detected * 0.82),  # Recommended
            int(base_detected * 0.65),  # Accepted
            int(base_detected * 0.58)   # Cleared
        ]
        funnel_labels = ["Detected", "Recommended", "Accepted", "Cleared"]
        self.funnel_chart.setData(funnel_data, funnel_labels)
        
        # Update delay causes (realistic railway delays)
        delay_causes = [
            random.randint(20, 35),  # Signal failures
            random.randint(15, 28),  # Track work
            random.randint(8, 20),   # Weather
            random.randint(10, 18),  # Rolling stock
            random.randint(5, 15)    # Other
        ]
        self.delay_chart.setData(delay_causes, ["Signal", "Track", "Weather", "Stock", "Other"])
        
        # Update headway chart (inter-train spacing)
        headway_data = []
        min_headway = 3.0  # Minimum safe headway in minutes
        
        for i in range(50):
            # Most headways should be above minimum, some violations
            if random.random() < 0.93:  # 93% compliance
                headway = random.uniform(min_headway + 0.2, 5.5)
            else:
                headway = random.uniform(2.2, min_headway - 0.1)  # Violation
            headway_data.append(headway)
            
        self.headway_chart.clearSeries()
        self.headway_chart.addSeries("Actual Headway", headway_data, QtGui.QColor(73, 80, 87))
        
        # Add minimum headway line
        min_headway_line = [min_headway] * 50
        self.headway_chart.addSeries("Minimum Required", min_headway_line, QtGui.QColor(134, 142, 150))
        
        # Update RTP trend (24-hour pattern)
        rtp_data = []
        for hour in range(24):
            if hour in [7, 8, 9, 17, 18, 19]:  # Peak hours
                base_rtp = random.uniform(75, 88)
            elif hour in [0, 1, 2, 3, 4, 5]:  # Night hours
                base_rtp = random.uniform(92, 98)
            else:
                base_rtp = random.uniform(85, 95)
                
            rtp_data.append(base_rtp)
            
        self.rtp_trend.clearSeries()
        self.rtp_trend.addSeries("Right-Time Performance", rtp_data, QtGui.QColor(73, 80, 87))
        
        # Add target line
        target_line = [85] * 24  # 85% target
        self.rtp_trend.addSeries("Target (85%)", target_line, QtGui.QColor(134, 142, 150))
                    
    def exportReport(self):
        """Export comprehensive railway KPI report"""
        file_path, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export Railway KPI Report", 
            f"Railway_Operations_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            "CSV files (*.csv)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w') as f:
                    f.write("Railway Operations KPI Report\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"Time Range: {self.time_combo.currentText()}\n\n")
                    
                    f.write("Real-time Controller KPIs:\n")
                    f.write("KPI,Current Value,Unit,Target,Status\n")
                    
                    # Export current KPI values with targets
                    kpi_targets = {
                        "rtp": "≥85%",
                        "avg_delay": "<6-8 min",
                        "p90_delay": "<12-15 min", 
                        "throughput": "Variable",
                        "conflicts": "≤2",
                        "mttr": "<5 min",
                        "acceptance": ">70%"
                    }
                    
                    for key, tile in self.kpi_tiles.items():
                        value = tile.value_label.text()
                        unit = tile.unit_label.text()
                        target = kpi_targets.get(key, "TBD")
                        f.write(f"{tile.title},{value},{unit},{target},Active\n")
                    
                    f.write("\nGenerated by TS2 TrackTitans Railway Management System\n")
                    
                QtWidgets.QMessageBox.information(self, "Export Complete", 
                    f"Railway operations report exported to:\n{file_path}")
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Export Error", 
                    f"Failed to export report:\n{str(e)}")


# Alias for backward compatibility
KPIDashboardWidget = RailwayKPIDashboard
