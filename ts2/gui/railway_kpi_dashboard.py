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
        self.setupUI()
        self.requestDataRefresh()
        
        # Auto-refresh timer
        self.refresh_timer = QtCore.QTimer()
        self.refresh_timer.timeout.connect(self.requestDataRefresh)
        self.refresh_timer.start(15000)  # 15 seconds
        
    def setupUI(self):
        """Setup minimal analytics dashboard UI"""
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Header
        self.setupHeader(main_layout)
        
        # KPI tiles grid
        self.setupKPIGrid(main_layout)

        # Single trend chart with metric selector
        self.setupTrendSection(main_layout)
        
    def setupHeader(self, main_layout):
        """Setup header with title and controls"""
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        
        title = QtWidgets.QLabel("TrackTitans - Operations Analytics")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #343a40; margin-bottom: 6px;")
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Time range selector
        header_layout.addWidget(QtWidgets.QLabel("Range:"))
        self.time_combo = QtWidgets.QComboBox()
        self.time_combo.addItems(["Last Hour", "Last 6 Hours", "Today", "Last 24h", "Last Week", "Last Month"])
        self.time_combo.setCurrentText("Today")
        header_layout.addWidget(self.time_combo)
        self.time_combo.currentTextChanged.connect(self.requestDataRefresh)
        
        # Updated timestamp label
        self.updated_label = QtWidgets.QLabel("Updated: --")
        self.updated_label.setStyleSheet("color: #6c757d; font-size: 12px; margin-left: 10px;")
        header_layout.addWidget(self.updated_label)
        
        # Export button
        self.export_btn = QtWidgets.QPushButton("Export CSV")
        self.export_btn.clicked.connect(self.exportReport)
        self.export_btn.setStyleSheet("QPushButton { padding: 6px 12px; }")
        header_layout.addWidget(self.export_btn)
        
        main_layout.addWidget(header)
        
    def setupKPIGrid(self, main_layout):
        """Setup a compact grid of KPI tiles bound to API fields"""
        kpi_frame = QtWidgets.QFrame()
        kpi_frame.setStyleSheet(
            "QFrame { background-color: #f8f9fa; border: 1px solid #dee2e6; border-radius: 4px; margin: 6px 0; }"
        )
        grid = QtWidgets.QGridLayout(kpi_frame)
        grid.setContentsMargins(10, 10, 10, 10)
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(10)

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
            
        main_layout.addWidget(kpi_frame)
        
    def setupTrendSection(self, main_layout):
        """Setup a single historical trend chart with selectors"""
        section = QtWidgets.QGroupBox("Historical Trend")
        section.setStyleSheet("QGroupBox { font-weight: bold; }")
        v = QtWidgets.QVBoxLayout(section)

        # Controls row
        controls = QtWidgets.QHBoxLayout()
        controls.addWidget(QtWidgets.QLabel("Metric:"))
        self.metric_combo = QtWidgets.QComboBox()
        # Allowed metrics for historical API
        self.metric_combo.addItems([
            "punctuality", "rtp", "averageDelay", "p90Delay", "throughput",
            "utilization", "acceptanceRate", "openConflicts", "headwayAdherence", "headwayBreaches"
        ])
        self.metric_combo.setCurrentText("punctuality")
        self.metric_combo.currentTextChanged.connect(self._onTrendSelectorChanged)
        controls.addWidget(self.metric_combo)

        controls.addSpacing(10)
        controls.addWidget(QtWidgets.QLabel("Period:"))
        self.period_combo = QtWidgets.QComboBox()
        self.period_combo.addItems(["hourly", "daily", "weekly"])
        self.period_combo.setCurrentText("hourly")
        self.period_combo.currentTextChanged.connect(self._onTrendSelectorChanged)
        controls.addWidget(self.period_combo)

        controls.addStretch()
        v.addLayout(controls)

        # Chart
        self.trend_chart = LineChart()
        self.trend_chart.setFixedHeight(180)
        v.addWidget(self.trend_chart)

        main_layout.addWidget(section)
        
    def _onTrendSelectorChanged(self):
        # Refetch historical when metric or period changes
        metric = self.metric_combo.currentText()
        period = self.period_combo.currentText()
        self.provider.fetchHistorical(metric=metric, period=period)
        
    def updateAllKPIs(self):
        """Deprecated: analytics is fully server-driven."""
        pass

    def requestDataRefresh(self):
        """Trigger provider refresh using current filters; fallback to mock after repeated errors."""
        time_range = self._mapTimeRange(self.time_combo.currentText())
        self.provider.refreshKpis(time_range=time_range)
        # Refresh historical for selected metric
        metric = getattr(self, "metric_combo", None).currentText() if hasattr(self, "metric_combo") else "punctuality"
        period = getattr(self, "period_combo", None).currentText() if hasattr(self, "period_combo") else "hourly"
        self.provider.fetchHistorical(metric=metric, period=period)

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
            if not hasattr(self, "trend_chart"):
                return
            # Only refresh if this metric is currently selected
            selected = self.metric_combo.currentText() if hasattr(self, "metric_combo") else None
            if selected and metric != selected and not (metric == "punctuality" and selected == "rtp"):
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
                self.trend_chart.clearSeries()
                # Friendly name
                name_map = {
                    "punctuality": "Right-Time Performance",
                    "rtp": "Right-Time Performance",
                    "averageDelay": "Average Delay",
                    "p90Delay": "P90 Delay",
                    "throughput": "Throughput",
                    "utilization": "Utilization",
                    "acceptanceRate": "Acceptance Rate",
                    "openConflicts": "Open Conflicts",
                    "headwayAdherence": "Headway Adherence",
                    "headwayBreaches": "Headway Breaches",
                }
                label = name_map.get(metric, metric)
                self.trend_chart.addSeries(label, values, QtGui.QColor(73, 80, 87))

                # Optional target lines for certain metrics
                if metric in ("punctuality", "rtp"):
                    target_line = [85] * len(values)
                    self.trend_chart.addSeries("Target (85%)", target_line, QtGui.QColor(134, 142, 150))
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
