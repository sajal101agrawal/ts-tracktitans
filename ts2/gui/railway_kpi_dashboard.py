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
from datetime import datetime, timedelta
from .charts import (LineChart, KPITile)
from .analytics_provider import KPIDataProvider


class RailwayKPIDashboard(QtWidgets.QWidget):
    """Minimal Operations Analytics Dashboard (API-driven)"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.kpi_tiles = {}
        self.kpi_config = []  # (tile_key, api_key, title, unit)
        self.provider = KPIDataProvider()
        self.provider.kpisUpdated.connect(self.onKpisUpdated)
        self.provider.historicalUpdated.connect(self.onHistoricalUpdated)
        self.provider.errorOccurred.connect(self.onProviderError)
        self._provider_errors = 0
        # Charts map and metadata for historical metrics
        self.charts_by_metric = {}
        self.metrics_for_history = [
            "punctuality", "averageDelay", "p90Delay", "throughput",
            "utilization", "acceptanceRate", "openConflicts",
            "headwayAdherence", "headwayBreaches"
        ]
        self.metric_meta = {
            "punctuality": {"name": "Right-Time Performance", "unit": "%"},
            "averageDelay": {"name": "Average Delay", "unit": "min"},
            "p90Delay": {"name": "P90 Delay", "unit": "min"},
            "throughput": {"name": "Throughput", "unit": "tr/h"},
            "utilization": {"name": "Utilization", "unit": "%"},
            "acceptanceRate": {"name": "Acceptance Rate", "unit": "%"},
            "openConflicts": {"name": "Open Conflicts", "unit": "count"},
            "headwayAdherence": {"name": "Headway Adherence", "unit": "%"},
            "headwayBreaches": {"name": "Headway Breaches", "unit": "count"},
        }
        self.setupUI()
        self.requestDataRefresh()
        
        # Auto-refresh timer
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.requestDataRefresh)
        self.refresh_timer.start(15000)  # 15 seconds
        
    def setupUI(self):
        """Setup modern analytics dashboard UI"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Set modern background
        self.setStyleSheet("""
            QWidget {
                background-color: #f8fafc;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            }
        """)

        # Scrollable container with modern styling
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: #f8fafc;
            }
            QScrollBar:vertical {
                background: #e2e8f0;
                width: 8px;
                border-radius: 4px;
            }
            QScrollBar::handle:vertical {
                background: #cbd5e1;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #94a3b8;
            }
        """)
        
        content = QtWidgets.QWidget()
        content_layout = QtWidgets.QVBoxLayout(content)
        content_layout.setContentsMargins(24, 24, 24, 24)
        content_layout.setSpacing(24)
        
        # Header
        self.setupHeader(content_layout)
        
        # KPI tiles grid
        self.setupKPIGrid(content_layout)

        # Stacked trends for all metrics with vertical scrolling
        self.setupTrendsSection(content_layout)

        scroll.setWidget(content)
        main_layout.addWidget(scroll)
        
    def setupHeader(self, main_layout):
        """Setup minimal header with essential controls only"""
        # Simple controls row without decorative background
        controls_row = QtWidgets.QHBoxLayout()
        
        # Time range selector with minimal styling
        range_label = QtWidgets.QLabel("Time Range")
        range_label.setStyleSheet("color: #64748b; font-weight: 500; font-size: 14px;")
        controls_row.addWidget(range_label)
        
        self.time_combo = QtWidgets.QComboBox()
        self.time_combo.addItems(["Last Hour", "Last 6 Hours", "Today", "Last 24h", "Last Week", "Last Month"])
        self.time_combo.setCurrentText("Today")
        self.time_combo.setStyleSheet(self._getModernComboBoxStyle("#3b82f6"))
        controls_row.addWidget(self.time_combo)
        self.time_combo.currentTextChanged.connect(self.requestDataRefresh)
        
        controls_row.addStretch()
        
        # Status indicator (minimal)
        self.updated_label = QtWidgets.QLabel("Updated: --")
        self.updated_label.setStyleSheet("""
            color: #9ca3af; 
            font-size: 12px; 
            font-weight: 400;
        """)
        controls_row.addWidget(self.updated_label)
        
        # Export button (minimal)
        self.export_btn = QtWidgets.QPushButton("Export")
        self.export_btn.clicked.connect(self.exportReport)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                color: #374151;
                border: 1px solid #d1d5db;
                padding: 6px 12px;
                border-radius: 6px;
                font-weight: 500;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
            QPushButton:pressed {
                background-color: #d1d5db;
            }
        """)
        controls_row.addWidget(self.export_btn)
        
        # Add controls with minimal spacing
        controls_container = QtWidgets.QWidget()
        controls_container.setLayout(controls_row)
        controls_container.setStyleSheet("margin-bottom: 16px;")
        
        main_layout.addWidget(controls_container)
        
    def setupKPIGrid(self, main_layout):
        """Setup modern KPI tiles grid with minimal design"""
        kpi_container = QtWidgets.QWidget()
        grid = QtWidgets.QGridLayout(kpi_container)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(16)

        # Define KPI tiles: (tile_key, api_key, title, unit)
        self.kpi_config = [
            ("punctuality", "punctuality", "Right-Time Performance", "%"),
            ("averageDelay", "averageDelay", "Avg Delay", "min"),
            ("p90Delay", "p90Delay", "P90 Delay", "min"),
            ("throughput", "throughput", "Throughput", "tr/h"),
            ("openConflicts", "openConflicts", "Open Conflicts", "count"),
            ("mttrConflict", "mttrConflict", "MTTR-Conflict", "min"),
            ("acceptanceRate", "acceptanceRate", "Acceptance Rate", "%"),
            ("utilization", "utilization", "Utilization", "%"),
            ("headwayAdherence", "headwayAdherence", "Headway Adherence", "%"),
            ("headwayBreaches", "headwayBreaches", "Headway Breaches", "count"),
            ("efficiency", "efficiency", "Operational Efficiency", "%"),
            ("performance", "performance", "System Performance", "%"),
        ]

        cols = 4
        for idx, (tile_key, api_key, title, unit) in enumerate(self.kpi_config):
            tile = KPITile(title, "--", unit)
            self.kpi_tiles[tile_key] = tile
            r = idx // cols
            c = idx % cols
            grid.addWidget(tile, r, c)
            
        main_layout.addWidget(kpi_container)
        
    def setupTrendsSection(self, main_layout):
        """Setup minimal historical trend charts section"""
        # Simple period selector without decorative header
        period_row = QtWidgets.QHBoxLayout()
        
        period_label = QtWidgets.QLabel("Period")
        period_label.setStyleSheet("color: #64748b; font-weight: 500; font-size: 14px;")
        period_row.addWidget(period_label)
        
        self.period_combo = QtWidgets.QComboBox()
        self.period_combo.addItems(["Hourly", "Daily", "Weekly"])
        self.period_combo.setCurrentText("Hourly")
        self.period_combo.setStyleSheet(self._getModernComboBoxStyle("#10b981"))
        self.period_combo.currentTextChanged.connect(self._onPeriodChanged)
        period_row.addWidget(self.period_combo)
        
        period_row.addStretch()
        
        # Add period selector with minimal spacing
        period_container = QtWidgets.QWidget()
        period_container.setLayout(period_row)
        period_container.setStyleSheet("margin-bottom: 16px;")
        
        main_layout.addWidget(period_container)

        # Charts container with responsive grid
        charts_container = QtWidgets.QWidget()
        
        # Use a grid layout for better organization
        charts_grid = QtWidgets.QGridLayout(charts_container)
        charts_grid.setContentsMargins(0, 0, 0, 0)
        charts_grid.setSpacing(20)

        # Group metrics by category for better layout
        performance_metrics = ["punctuality", "averageDelay", "p90Delay"]
        operational_metrics = ["throughput", "utilization", "acceptanceRate"]
        reliability_metrics = ["openConflicts", "headwayAdherence", "headwayBreaches"]
        
        metric_groups = [
            ("Performance Metrics", performance_metrics, "#10b981"),
            ("Operational Metrics", operational_metrics, "#3b82f6"), 
            ("Reliability Metrics", reliability_metrics, "#f59e0b")
        ]

        row = 0
        for group_name, metrics, accent_color in metric_groups:
            # Group header
            group_header = QtWidgets.QLabel(group_name)
            group_header.setStyleSheet(f"""
                font-size: 18px;
                font-weight: 600;
                color: {accent_color};
                margin: 16px 0 8px 0;
                padding: 8px 0;
                border-bottom: 2px solid {accent_color};
            """)
            charts_grid.addWidget(group_header, row, 0, 1, 2)
            row += 1
            
            # Charts in this group (2 per row)
            col = 0
            for metric in metrics:
                if metric not in self.metrics_for_history:
                    continue
                    
                meta = self.metric_meta.get(metric, {"name": metric, "unit": ""})
                
                # Enhanced chart card
                chart_card = QtWidgets.QWidget()
                chart_card.setStyleSheet(f"""
                    QWidget {{
                        background-color: white;
                        border-radius: 16px;
                        border: 2px solid #f1f5f9;
                        padding: 0;
                    }}
                    QWidget:hover {{
                        border-color: {accent_color};
                    }}
                """)
                card_layout = QtWidgets.QVBoxLayout(chart_card)
                card_layout.setContentsMargins(20, 20, 20, 20)
                card_layout.setSpacing(16)

                # Chart header with value and trend
                header_row = QtWidgets.QHBoxLayout()
                
                chart_title = QtWidgets.QLabel(meta['name'])
                chart_title.setStyleSheet("""
                    font-size: 16px;
                    font-weight: 600;
                    color: #1e293b;
                """)
                header_row.addWidget(chart_title)
                
                header_row.addStretch()
                
                unit_label = QtWidgets.QLabel(meta['unit'])
                unit_label.setStyleSheet(f"""
                    font-size: 12px;
                    font-weight: 600;
                    color: {accent_color};
                    background-color: rgba({int(accent_color[1:3], 16)}, {int(accent_color[3:5], 16)}, {int(accent_color[5:7], 16)}, 0.1);
                    padding: 4px 8px;
                    border-radius: 12px;
                """)
                header_row.addWidget(unit_label)
                
                card_layout.addLayout(header_row)

                # Chart with enhanced styling
                chart = LineChart()
                chart.setFixedHeight(260)  # Increased height to prevent clipping
                chart.setAxisLabels("Time", meta.get("unit", ""))
                chart.setStyleSheet("""
                    QWidget {
                        border-radius: 8px;
                        background-color: #fafbfc;
                    }
                """)
                card_layout.addWidget(chart)

                self.charts_by_metric[metric] = chart
                charts_grid.addWidget(chart_card, row, col)
                
                col += 1
                if col >= 2:  # 2 charts per row
                    col = 0
                    row += 1
            
            if col > 0:  # If we ended mid-row, move to next row
                row += 1

        main_layout.addWidget(charts_container)
        
    def _onPeriodChanged(self):
        """Refetch all historical series when period changes"""
        self.fetchAllHistorical()
        
    def _mapPeriodToApi(self, display_text):
        """Map display text to API parameter"""
        mapping = {
            "Hourly": "hourly",
            "Daily": "daily", 
            "Weekly": "weekly"
        }
        return mapping.get(display_text, "hourly")
        
    def _getModernComboBoxStyle(self, accent_color):
        """Get minimal combo box styling - clean and simple"""
        return f"""
            QComboBox {{
                padding: 8px 12px;
                border: 1px solid #d1d5db;
                border-radius: 4px;
                background-color: white;
                font-size: 14px;
                color: #374151;
                min-width: 120px;
            }}
            QComboBox:hover {{
                border-color: #9ca3af;
            }}
            QComboBox:focus {{
                border-color: #6b7280;
                outline: none;
            }}
            QComboBox QAbstractItemView {{
                border: 1px solid #d1d5db;
                background-color: white;
                selection-background-color: #e5e7eb;
                selection-color: #374151;
            }}
            QComboBox QAbstractItemView::item {{
                padding: 8px 12px;
                color: #374151;
            }}
            QComboBox QAbstractItemView::item:selected {{
                background-color: #e5e7eb;
                color: #374151;
            }}
        """
        
    def updateAllKPIs(self):
        """Deprecated: analytics is fully server-driven."""
        pass

    def requestDataRefresh(self):
        """Trigger provider refresh using current filters; fallback to mock after repeated errors."""
        time_range = self._mapTimeRange(self.time_combo.currentText())
        self.provider.refreshKpis(time_range=time_range)
        # Refresh historical for all metrics
        self.fetchAllHistorical()

    def fetchAllHistorical(self):
        """Fetch historical data for all configured metrics"""
        period_display = getattr(self, "period_combo", None).currentText() if hasattr(self, "period_combo") else "Hourly"
        period_api = self._mapPeriodToApi(period_display)
        for m in self.metrics_for_history:
            self.provider.fetchHistorical(metric=m, period=period_api)

    def _mapTimeRange(self, text):
        mapping = {
            "Last Hour": "1h",
            "Last 6 Hours": "6h",
            "Today": "1d",
            "Last 24h": "1d",
            "Last Week": "1w",
            "Last Month": "1m",
        }
        return mapping.get(text, "1d")

    def _mapTrainType(self, text):
        mapping = {
            "All Classes": "all",
            "Mail/Express": "express",
            "Suburban": "regional",
            "Freight": "freight",
        }
        return mapping.get(text, "all")

    @QtCore.pyqtSlot(dict)
    def onKpisUpdated(self, data):
        self._provider_errors = 0
        kpis = data.get("kpis", {})
        trends = data.get("trends", {})

        for tile_key, api_key, _title, unit in self.kpi_config:
            if tile_key in self.kpi_tiles and api_key in kpis:
                value = kpis.get(api_key)
                # Trend delta
                trend = trends.get(api_key) or trends.get(tile_key) or {}
                change = trend.get("change")
                delta = None
                if isinstance(change, (int, float)):
                    if trend.get("direction") == "DOWN":
                        delta = -abs(change)
                    elif trend.get("direction") == "UP":
                        delta = abs(change)
                    else:
                        delta = change

                tile = self.kpi_tiles[tile_key]
                tile.unit_label.setText(unit)

                # Minimal color rules per metric
                if tile_key in ("punctuality", "headwayAdherence"):
                    color = self.getKPIColor(value, 85 if tile_key == "punctuality" else 95,
                                              75 if tile_key == "punctuality" else 90)
                elif tile_key in ("averageDelay", "p90Delay", "mttrConflict", "openConflicts", "headwayBreaches"):
                    thr = (6, 8) if tile_key == "averageDelay" else (12, 15) if tile_key == "p90Delay" else (5, 10)
                    if tile_key in ("openConflicts", "headwayBreaches"):
                        thr = (2, 4)
                    color = self.getKPIColor(value, thr[0], thr[1], reverse=True)
                elif tile_key in ("acceptanceRate",):
                    color = self.getKPIColor(value, 70, 50)
                elif tile_key in ("efficiency",):
                    color = self.getKPIColor(value, 90, 80)
                elif tile_key in ("performance",):
                    color = self.getKPIColor(value, 80, 60)
                else:
                    color = "#495057"

                self.updateKPITile(tile_key, value, delta, color)

        # Update header timestamp if provided
        ts = data.get("timestamp") or data.get("time")
        if isinstance(ts, str) and hasattr(self, "updated_label"):
            self.updated_label.setText(f"Updated: {ts}")

    @QtCore.pyqtSlot(str, dict)
    def onHistoricalUpdated(self, metric, data):
        try:
            # Map alias 'rtp' to 'punctuality'
            key = "punctuality" if metric in ("punctuality", "rtp") else metric
            chart = self.charts_by_metric.get(key)
            if chart is None:
                return

            series = data.get("series") or data.get("data") or []
            values = []
            for item in series:
                if isinstance(item, dict):
                    val = item.get("v")
                    if val is None:
                        val = item.get("value")
                    if val is not None:
                        values.append(val)
                else:
                    values.append(item)

            if values:
                chart.clearSeries()
                meta = self.metric_meta.get(key, {"name": key})
                label = meta.get("name", key)
                chart.addSeries(label, values, QtGui.QColor(73, 80, 87))

                # Optional target lines for certain metrics (minimal)
                if key == "punctuality":
                    target_line = [85] * len(values)
                    chart.addSeries("Target (85%)", target_line, QtGui.QColor(134, 142, 150))
        except Exception:
            pass

    @QtCore.pyqtSlot(str)
    def onProviderError(self, message):
        self._provider_errors += 1
        
    def updateKPITile(self, key, value, delta, color):
        """Update a specific KPI tile"""
        if key in self.kpi_tiles:
            tile = self.kpi_tiles[key]
            
            # Format value based on type
            if isinstance(value, float):
                formatted_value = f"{value:.1f}" if value < 100 else f"{value:.0f}"
            else:
                formatted_value = str(int(value))
                
            # Minimal trend data (no mock randomness)
            trend_data = [value] * 20
            
            tile.updateValue(formatted_value, delta, trend_data)
            tile.setValueColor(color)
            
    def getKPIColor(self, value, green_threshold, red_threshold, reverse=False):
        """Get modern color based on KPI thresholds"""
        if reverse:
            if value <= green_threshold:
                return "#10b981"  # Modern green (good)
            elif value <= red_threshold:
                return "#f59e0b"  # Modern amber (caution)
            else:
                return "#ef4444"  # Modern red (poor)
        else:
            if value >= green_threshold:
                return "#10b981"  # Modern green (good)
            elif value >= red_threshold:
                return "#f59e0b"  # Modern amber (caution)
            else:
                return "#ef4444"  # Modern red (poor)
                
    def updateCharts(self):
        """No-op: retained for compatibility."""
        pass
                    
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
                        "punctuality": "≥85%",
                        "averageDelay": "<6-8 min",
                        "p90Delay": "<12-15 min",
                        "throughput": "Contextual",
                        "openConflicts": "≤2",
                        "mttrConflict": "<5 min",
                        "acceptanceRate": ">70%",
                        "utilization": "≤60% (peak)",
                        "efficiency": "≥90%",
                        "performance": "≥80%",
                        "headwayAdherence": "≥95%",
                        "headwayBreaches": "≤2",
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
