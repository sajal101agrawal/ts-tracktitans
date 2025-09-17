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
import threading
import requests
from datetime import datetime


class AIHintsProvider(QtCore.QObject):
    """HTTP/WS provider for AI hints integration with server API."""

    hintsUpdated = QtCore.pyqtSignal(list)
    errorOccurred = QtCore.pyqtSignal(str)
    respondCompleted = QtCore.pyqtSignal(str, bool)

    def __init__(self, base_url=None, api_key=None, parent=None):
        super().__init__(parent)
        self._base_url = base_url or "http://localhost:22222"
        self._api_key = api_key
        self._session = requests.Session()
        self._timeout_seconds = 5
        self._inflight = False
        # Throttle rapid successive refreshes (e.g., from push events)
        self._cooldown_ms = 1000
        self._last_fetch_started_ms = 0
        self._throttle_timer_active = False
        self._throttle_pending_recompute = False

    def _headers(self):
        headers = {}
        if self._api_key:
            headers["X-API-Key"] = self._api_key
        return headers

    def setBaseUrl(self, base_url):
        self._base_url = base_url or self._base_url

    def refreshHints(self, recompute=True):
        """GET /api/ai/hints and emit hintsUpdated.

        :param recompute: when True, pass recompute=1 to force server to recalc
        """

        # Throttle & coalesce
        if self._inflight:
            # Coalesce recompute intent while request is running
            self._throttle_pending_recompute = self._throttle_pending_recompute or recompute
            return

        now = int(QtCore.QDateTime.currentMSecsSinceEpoch())
        elapsed = now - int(self._last_fetch_started_ms or 0)
        if elapsed < self._cooldown_ms:
            # Schedule a single refresh after cooldown (coalesced)
            self._throttle_pending_recompute = self._throttle_pending_recompute or recompute
            if not self._throttle_timer_active:
                self._throttle_timer_active = True
                delay = max(0, self._cooldown_ms - elapsed + 10)
                QtCore.QTimer.singleShot(delay, lambda: self._throttledRefresh())
            return

        self._inflight = True
        self._last_fetch_started_ms = now

        def _run():
            try:
                url = f"{self._base_url}/api/ai/hints"
                params = {"recompute": 1} if recompute else {}
                QtCore.qDebug(f"AIHintsProvider: GET {url} params={params}")
                resp = self._session.get(url, params=params, headers=self._headers(), timeout=self._timeout_seconds)
                resp.raise_for_status()
                payload = resp.json()
                hints = payload.get("hints", [])
                # Mark source for downstream handling
                for h in hints:
                    if isinstance(h, dict):
                        h.setdefault("source", "ai")
                self.hintsUpdated.emit(hints)
            except Exception as exc:
                # Fallback to suggestions if AI hints endpoint unavailable
                try:
                    fallback_hints = self._fallback_refresh_via_suggestions()
                    self.hintsUpdated.emit(fallback_hints)
                except Exception as exc2:
                    self.errorOccurred.emit(f"{exc2}")
            finally:
                self._inflight = False
                self._last_fetch_started_ms = int(QtCore.QDateTime.currentMSecsSinceEpoch())
                # If more refreshes were requested while inflight, schedule one more (coalesced)
                if self._throttle_pending_recompute:
                    # Defer scheduling to the main thread to avoid QTimer in non-QThread
                    QtCore.QMetaObject.invokeMethod(self, "_scheduleDeferredRefresh", QtCore.Qt.QueuedConnection)

        threading.Thread(target=_run, daemon=True).start()

    def _throttledRefresh(self):
        """Internal handler to execute a coalesced refresh after cooldown."""
        self._throttle_timer_active = False
        pend = self._throttle_pending_recompute
        self._throttle_pending_recompute = False
        self.refreshHints(recompute=pend)

    @QtCore.pyqtSlot()
    def _scheduleDeferredRefresh(self):
        pend = self._throttle_pending_recompute
        self._throttle_pending_recompute = False
        QtCore.QTimer.singleShot(self._cooldown_ms, lambda: self.refreshHints(recompute=pend))

    def respondToHint(self, hint_id, response, override_action=None, user_id=None, callback=None):
        """Use WebSocket RPC to accept/reject suggestions via the suggestions object."""
        # Get main window to access webSocket (robust lookup not relying on activeWindow)
        from Qt import QtWidgets
        main_window = None
        # Prefer walking up from our parent hierarchy
        w = self.parent()
        steps = 0
        while w is not None and steps < 8:
            if hasattr(w, 'webSocket'):
                main_window = w
                break
            w = getattr(w, 'parent', lambda: None)()
            steps += 1
        # Fallbacks
        if not main_window:
            for tw in QtWidgets.QApplication.topLevelWidgets():
                if hasattr(tw, 'webSocket'):
                    main_window = tw
                    break
        if not main_window:
            widget = QtWidgets.QApplication.activeWindow()
            while widget and not hasattr(widget, 'webSocket'):
                widget = widget.parent()
            if widget and hasattr(widget, 'webSocket'):
                main_window = widget
        
        if not main_window or not getattr(main_window, 'webSocket', None):
            self.errorOccurred.emit("WebSocket not available")
            self.respondCompleted.emit(hint_id, False)
            return

        def on_response(msg):
            if msg and msg.get("status") == "OK":
                self.respondCompleted.emit(hint_id, True)
            else:
                error_msg = msg.get("message", "Unknown error") if msg else "No response"
                self.errorOccurred.emit(f"Server error: {error_msg}")
                self.respondCompleted.emit(hint_id, False)

        if response == "ACCEPT":
            main_window.webSocket.sendRequest("suggestions", "accept", {"id": hint_id}, callback=on_response)
        elif response == "DISMISS":
            params = {"id": hint_id}
            if override_action and "dismissMinutes" in override_action:
                params["minutes"] = override_action["dismissMinutes"]
            else:
                params["minutes"] = 10  # Default dismiss duration
            main_window.webSocket.sendRequest("suggestions", "reject", params, callback=on_response)
        else:
            # OVERRIDE - acknowledge but no server action needed per docs
            self.respondCompleted.emit(hint_id, True)

    def _fallback_refresh_via_suggestions(self):
        """Fallback: GET /api/suggestions and map to hints schema."""
        url = f"{self._base_url}/api/suggestions"
        QtCore.qDebug(f"AIHintsProvider (fallback): GET {url}")
        resp = self._session.get(url, headers=self._headers(), timeout=self._timeout_seconds)
        resp.raise_for_status()
        data = resp.json()
        suggestions = data.get("suggestions") if isinstance(data, dict) else data
        suggestions = suggestions or []
        mapped = []
        for s in suggestions:
            if not isinstance(s, dict):
                continue
            hint = {
                "id": s.get("id") or s.get("_id") or s.get("uuid") or f"sugg_{len(mapped)+1}",
                "type": s.get("type") or "SUGGESTION",
                "priority": (s.get("priority") or "MEDIUM").upper(),
                "message": s.get("message") or s.get("text") or s.get("title") or "System suggestion",
                "reasoning": s.get("reason") or s.get("explanation") or "",
                "confidence": s.get("confidence") or s.get("score") or 80,
                "suggestedAction": s.get("suggestedAction") or s.get("action"),
                "timestamp": s.get("timestamp") or s.get("createdAt") or datetime.now().isoformat(),
                "source": "suggestions",
            }
            mapped.append(hint)
        return mapped


class AIHintsWidget(QtWidgets.QWidget):
    """Widget to display and manage AI hints"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.provider = AIHintsProvider(parent=self)
        self.provider.hintsUpdated.connect(self.updateHints)
        self.provider.errorOccurred.connect(self.onProviderError)
        # Ensure responses update UI on main thread
        self.provider.respondCompleted.connect(self.onRespondCompleted)
        self.hint_widgets = []
        self._auto_accepted_ids = set()
        self._auto_accept_inflight_ids = set()
        self._just_accepted_ids = set()
        self.setupUI()
        
    def setupUI(self):
        """Setup the AI hints UI"""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Header
        header = QtWidgets.QWidget()
        header_layout = QtWidgets.QHBoxLayout(header)
        
        # title = QtWidgets.QLabel("AI Routing Hints")
        # title.setStyleSheet("font-size: 16px; font-weight: bold; color: #495057;")
        # header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Controls
        self.auto_hint_cb = QtWidgets.QCheckBox("Auto-refresh")
        self.auto_hint_cb.setChecked(True)
        self.auto_hint_cb.toggled.connect(self.toggleAutoHints)
        # header_layout.addWidget(self.auto_hint_cb)
        
        self.auto_accept_cb = QtWidgets.QCheckBox("Auto-accept")
        self.auto_accept_cb.setToolTip("When enabled, new hints are accepted automatically")
        self.auto_accept_cb.toggled.connect(self.onAutoAcceptToggled)
        header_layout.addWidget(self.auto_accept_cb)
        
        self.manual_hint_btn = QtWidgets.QPushButton("Refresh Now")
        self.manual_hint_btn.clicked.connect(self.triggerRefresh)
        header_layout.addWidget(self.manual_hint_btn)
        
        # Status label
        self.status_label = QtWidgets.QLabel("")
        self.status_label.setStyleSheet("font-size: 11px; color: #868e96;")
        header_layout.addWidget(self.status_label)
        
        layout.addWidget(header)
        
        # Hints container
        self.hints_scroll = QtWidgets.QScrollArea()
        self.hints_scroll.setWidgetResizable(True)
        self.hints_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.hints_container = QtWidgets.QWidget()
        self.hints_layout = QtWidgets.QVBoxLayout(self.hints_container)
        self.hints_layout.setContentsMargins(5, 5, 5, 5)
        self.hints_layout.setSpacing(10)
        
        self.hints_scroll.setWidget(self.hints_container)
        layout.addWidget(self.hints_scroll)
        
        # Initial load and auto timer
        self._refresh_timer = QtCore.QTimer(self)
        self._refresh_timer.timeout.connect(self.triggerRefresh)
        self._refresh_timer.start(5000)
        self.triggerRefresh(force=True)
        
    def toggleAutoHints(self, enabled):
        """Toggle automatic refresh"""
        if enabled:
            self._refresh_timer.start(5000)
            # Only trigger immediate refresh if widget is visible
            if self.isVisible():
                self.triggerRefresh(force=True)
        else:
            self._refresh_timer.stop()

    @QtCore.pyqtSlot()
    def triggerRefresh(self, force=False):
        # Avoid unnecessary calls if widget is not visible, unless auto-accept is enabled
        if not self.isVisible() and not force and not self.auto_accept_cb.isChecked():
            return
        if hasattr(self, "status_label"):
            self.status_label.setText("Fetching...")
            self.status_label.setStyleSheet("font-size: 11px; color: #868e96;")
        # Snapshot a fetch token so late responses don't overwrite status incorrectly
        self._last_fetch_token = QtCore.QDateTime.currentMSecsSinceEpoch()
        # Recompute when forced (initial/manual), otherwise light refresh
        if force:
            self.provider.refreshHints(recompute=True)
        else:
            self.provider.refreshHints()

    # Removed showEvent-triggered fetch to avoid extra requests; rely on timer or manual refresh

    @QtCore.pyqtSlot(str)
    def onProviderError(self, message):
        QtCore.qWarning(f"AIHintsProvider error: {message}")
        self.status_label.setText(f"Error: {message}")
        self.status_label.setStyleSheet("font-size: 11px; color: #dc3545;")
            
    def updateHints(self, hints):
        """Update the hints display"""
        # If multiple inflight, ensure this response is the latest before clearing 'Fetching...'
        try:
            now_token = getattr(self, '_last_fetch_token', None)
            if now_token is None:
                self._last_fetch_token = QtCore.QDateTime.currentMSecsSinceEpoch()
        except Exception:
            pass
        # Clear existing hint widgets
        for widget in self.hint_widgets:
            widget.deleteLater()
        self.hint_widgets.clear()
        
        # Clear existing layout items
        while self.hints_layout.count():
            child = self.hints_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Add new hint widgets or empty state
        if hints:
            # Auto-accept newly arriving hints if enabled (only after confirmation)
            hints_to_display = []
            scheduled_count = 0
            if self.auto_accept_cb.isChecked():
                for hint in hints:
                    hid = hint.get('id')
                    if not hid:
                        hints_to_display.append(hint)
                        continue
                    if hid in self._auto_accepted_ids:
                        # Already accepted previously; no need to show again
                        continue
                    if hid in self._auto_accept_inflight_ids:
                        hints_to_display.append(hint)
                        continue
                    self._auto_accept_inflight_ids.add(hid)
                    self.acceptHintProgrammatically(hint)
                    # Also show the hint card so user sees the accepted state briefly
                    hints_to_display.append(hint)
                    scheduled_count += 1
            else:
                hints_to_display = hints
                
            # Create widgets for remaining hints
            for hint in hints_to_display:
                hint_widget = self.createHintWidget(hint)
                self.hint_widgets.append(hint_widget)
                self.hints_layout.addWidget(hint_widget)
                
            # Always update status to clear any lingering "Fetching..."
            display_count = len(hints_to_display)
            if self.auto_accept_cb.isChecked() and scheduled_count > 0:
                self.status_label.setText(f"Auto-accepting {scheduled_count} hint(s) — Updated {QtCore.QTime.currentTime().toString('hh:mm:ss')}")
                self.status_label.setStyleSheet("font-size: 11px; color: #28a745;")
            else:
                self.status_label.setText(f"Updated {QtCore.QTime.currentTime().toString('hh:mm:ss')} ({display_count} hints)")
                self.status_label.setStyleSheet("font-size: 11px; color: #868e96;")
        else:
            empty = QtWidgets.QLabel("No AI hints at the moment.")
            empty.setStyleSheet("color: #6c757d; font-style: italic; margin: 6px;")
            self.hints_layout.addWidget(empty)
            self.status_label.setText(f"Updated {QtCore.QTime.currentTime().toString('hh:mm:ss')} (0 hints)")
            self.status_label.setStyleSheet("font-size: 11px; color: #868e96;")
        
        # Add stretch at the end
        self.hints_layout.addStretch()

    @QtCore.pyqtSlot(bool)
    def onAutoAcceptToggled(self, enabled):
        if not enabled:
            # Reset memory so that future hints can be auto-accepted again
            self._auto_accepted_ids.clear()
        
    def createHintWidget(self, hint):
        """Create a clean, minimal hint card with complete information"""
        widget = QtWidgets.QFrame()
        widget.setFrameStyle(QtWidgets.QFrame.NoFrame)
        
        # Clean design with subtle priority indication
        priority = hint.get("priority", "LOW")
        if priority == "HIGH":
            accent_color = "#dc3545"
        elif priority == "MEDIUM":
            accent_color = "#fd7e14" 
        else:
            accent_color = "#6c757d"
            
        widget.setStyleSheet(f"""
            QFrame {{
                background-color: #ffffff;
                border: 1px solid #e9ecef;
                border-left: 3px solid {accent_color};
                border-radius: 8px;
                margin: 2px 0;
            }}
            QFrame:hover {{
                border-color: #ced4da;
                background-color: #f8f9fa;
            }}
        """)
        
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)
        
        # Header with priority and confidence
        header_layout = QtWidgets.QHBoxLayout()
        header_layout.setSpacing(12)
        
        # Priority indicator
        priority_label = QtWidgets.QLabel(f"{priority}")
        priority_label.setStyleSheet(f"""
            QLabel {{
                color: {accent_color};
                font-size: 11px;
                font-weight: bold;
                background-color: {accent_color}20;
                padding: 3px 8px;
                border-radius: 4px;
            }}
        """)
        header_layout.addWidget(priority_label)
        
        header_layout.addStretch()
        
        # Confidence
        conf = hint.get("confidence")
        if conf is not None:
            conf_label = QtWidgets.QLabel(f"{conf}%")
            conf_label.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: #6c757d;
                    background-color: #f8f9fa;
                    padding: 3px 8px;
                    border-radius: 4px;
                }
            """)
            header_layout.addWidget(conf_label)
        
        layout.addLayout(header_layout)
        
        # Main message
        message_label = QtWidgets.QLabel(hint.get("message", ""))
        message_label.setWordWrap(True)
        message_label.setStyleSheet("""
            QLabel {
                font-size: 13px;
                color: #212529;
                line-height: 1.4;
                margin: 4px 0;
            }
        """)
        layout.addWidget(message_label)
        
        # Reasoning (if available)
        reasoning = hint.get("reasoning", "")
        if reasoning:
            reasoning_label = QtWidgets.QLabel(reasoning)
            reasoning_label.setWordWrap(True)
            reasoning_label.setStyleSheet("""
                QLabel {
                    font-size: 11px;
                    color: #6c757d;
                    font-style: italic;
                    margin: 2px 0;
                }
            """)
            layout.addWidget(reasoning_label)
        
        # Action buttons and timestamp
        footer_layout = QtWidgets.QHBoxLayout()
        footer_layout.setSpacing(6)
        
        accept_btn = QtWidgets.QPushButton("Accept")
        accept_btn.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        accept_btn.clicked.connect(lambda: self.acceptHint(hint, widget, accept_btn, dismiss_btn, override_btn))
        footer_layout.addWidget(accept_btn)
        
        dismiss_btn = QtWidgets.QPushButton("Dismiss")
        dismiss_btn.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:disabled {
                background-color: #adb5bd;
            }
        """)
        dismiss_btn.clicked.connect(lambda: self.dismissHint(hint, widget, accept_btn, dismiss_btn, override_btn))
        footer_layout.addWidget(dismiss_btn)
        
        override_btn = QtWidgets.QPushButton("Override")
        override_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #6c757d;
                border: 1px solid #ced4da;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 11px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: #e9ecef;
                color: #495057;
            }
        """)
        override_btn.clicked.connect(lambda: self.overrideHint(hint))
        footer_layout.addWidget(override_btn)
        
        footer_layout.addStretch()

        # Accepted chip (hidden by default; shown briefly on acceptance)
        accepted_label = QtWidgets.QLabel("Accepted \u2713")
        accepted_label.setStyleSheet("""
            QLabel {
                font-size: 11px;
                color: #28a745;
                font-weight: 600;
                padding-left: 6px;
            }
        """)
        accepted_label.setVisible(False)
        footer_layout.addWidget(accepted_label)
        
        # Compact timestamp
        ts = hint.get("timestamp")
        if ts:
            time_str = ts[11:16] if len(ts) >= 16 else ts[:8]  # Just HH:MM
            timestamp_label = QtWidgets.QLabel(time_str)
            timestamp_label.setStyleSheet("""
                QLabel {
                    font-size: 10px;
                    color: #adb5bd;
                    font-family: monospace;
                }
            """)
            footer_layout.addWidget(timestamp_label)
        
        layout.addLayout(footer_layout)
        
        # Store hint ID for tracking
        widget.setProperty("_tt_hintId", hint.get("id"))
        widget.setProperty("_tt_acceptedLabel", accepted_label)
        
        # If this hint was just accepted programmatically before widget existed, show accepted now
        hid = hint.get("id")
        if hid and hid in self._just_accepted_ids:
            self._showAcceptedAndRemoveLater(widget, hid)
        
        return widget
        
    def acceptHint(self, hint, widget, accept_btn=None, dismiss_btn=None, override_btn=None):
        """Accept an AI hint via server API, then refresh."""
        # Disable buttons to prevent duplicate submissions
        for b in (accept_btn, dismiss_btn, override_btn):
            if b:
                b.setEnabled(False)
        widget.setProperty("_tt_hintButtons", (accept_btn, dismiss_btn, override_btn))
        widget.setProperty("_tt_hintMessage", hint.get("message", ""))
        # Execute suggested action locally (via WebSocket) if supported
        try:
            self.executeSuggestedAction(hint)
        except Exception as exc:
            QtCore.qWarning(f"AIHintsWidget.executeSuggestedAction error: {exc}")
        self.provider.respondToHint(hint.get("id"), "ACCEPT")
        
    def dismissHint(self, hint, widget, accept_btn=None, dismiss_btn=None, override_btn=None):
        """Dismiss an AI hint via server API, then refresh."""
        # Disable buttons to prevent duplicate submissions
        for b in (accept_btn, dismiss_btn, override_btn):
            if b:
                b.setEnabled(False)
        widget.setProperty("_tt_hintButtons", (accept_btn, dismiss_btn, override_btn))
        widget.setProperty("_tt_hintMessage", hint.get("message", ""))
        self.provider.respondToHint(hint.get("id"), "DISMISS")

    @QtCore.pyqtSlot(str, bool)
    def onRespondCompleted(self, hint_id, ok):
        """Handle completion of accept/dismiss on the UI thread safely."""
        # Always clear inflight tracking (programmatic auto-accept path may have no widget)
        try:
            self._auto_accept_inflight_ids.discard(hint_id)
        except Exception:
            pass

        # Remember accepted IDs even when no widget exists
        if ok:
            try:
                self._auto_accepted_ids.add(hint_id)
            except Exception:
                pass
            self._just_accepted_ids.add(hint_id)

        # Find the corresponding hint widget by hint_id stored as property
        target = None
        for w in self.hint_widgets:
            if w.property("_tt_hintId") == hint_id:
                target = w
                break

        if target is None:
            # Programmatic flow: trigger system status refresh if accepted
            if ok:
                mw = self.getMainWindow()
                if mw and hasattr(mw, 'system_status'):
                    try:
                        QtCore.QTimer.singleShot(0, mw.system_status.loadOverviewFromApi)
                    except Exception:
                        pass
            return

        accept_btn, dismiss_btn, override_btn = target.property("_tt_hintButtons") or (None, None, None)
        msg_text = target.property("_tt_hintMessage") or ""

        if ok:
            # Show accepted state for 1 second, then remove
            self._showAcceptedAndRemoveLater(target, hint_id)

            # Update status
            self.status_label.setText(f"Action completed at {QtCore.QTime.currentTime().toString('hh:mm:ss')}")
            self.status_label.setStyleSheet("font-size: 11px; color: #28a745;")

            # Refresh system status (signals) after actions that may change them
            mw = self.getMainWindow()
            if mw and hasattr(mw, 'system_status'):
                try:
                    QtCore.QTimer.singleShot(0, mw.system_status.loadOverviewFromApi)
                except Exception as exc:
                    QtCore.qWarning(f"Failed to refresh signals: {exc}")
            # Don't refresh hints immediately to avoid UI churn; let timer handle it
        else:
            # Silent failure messaging per UX request
            self.status_label.setText("Failed to update hint")
            self.status_label.setStyleSheet("font-size: 11px; color: #dc3545;")
            # Re-enable buttons on failure
            for b in (accept_btn, dismiss_btn, override_btn):
                if b:
                    b.setEnabled(True)

    # ===== Internal helpers =====
    def getMainWindow(self):
        w = self.parent()
        steps = 0
        while w is not None and steps < 6:
            if hasattr(w, 'webSocket'):
                return w
            w = w.parent()
            steps += 1
        return None

    def executeSuggestedAction(self, hint):
        """Translate suggested action(s) to WS/HTTP commands and send.

        Supports both single `suggestedAction` dict and generic `actions` list
        (object, action, params) as provided in the new suggestion model.

        Supported mappings:
        - route: activate|deactivate
        - train: proceed|reverse|setService
        - signal: status
        """
        actions = []
        sa = hint.get('suggestedAction')
        if isinstance(sa, dict):
            actions.append({
                'object': sa.get('object'),
                'action': sa.get('type'),
                'params': sa.get('params') or {}
            })
        lst = hint.get('actions')
        if isinstance(lst, list):
            for a in lst:
                if isinstance(a, dict):
                    actions.append(a)
        if not actions:
            return False

        mw = self.getMainWindow()
        if not mw or not getattr(mw, 'webSocket', None):
            return False
        success_any = False
        for a in actions:
            obj = (a.get('object') or '').lower()
            action = (a.get('action') or a.get('type') or '').lower()
            params = a.get('params') or {}
            if obj == 'route' and action in ('deactivate', 'activate'):
                rid = params.get('id')
                try:
                    rid_int = int(rid)
                except Exception:
                    rid_int = rid
                mw.webSocket.sendRequest('route', action, params={'id': rid_int})
                success_any = True
            elif obj == 'train' and action in ('proceed', 'reverse', 'setservice'):
                tid = params.get('id')
                try:
                    tid_int = int(tid)
                except Exception:
                    tid_int = tid
                if action == 'setservice':
                    svc = params.get('serviceCode') or params.get('service')
                    mw.webSocket.sendRequest('train', 'setService', params={'id': tid_int, 'serviceCode': svc})
                else:
                    mw.webSocket.sendRequest('train', 'proceed' if action == 'proceed' else 'reverse', params={'id': tid_int})
                success_any = True
            elif obj == 'signal' and action in ('status', 'set_status'):
                sig_id = params.get('id')
                new_status = params.get('newStatus') or params.get('status')
                base_url = getattr(self.provider, '_base_url', None)
                if base_url and sig_id and new_status:
                    def _run():
                        try:
                            url = f"{base_url}/api/systems/signals/{sig_id}/status"
                            normalized = self._normalizeSignalStatus(str(new_status))
                            body = {"newStatus": normalized, "reason": "AI hint accepted", "userId": "DISPATCHER_UI"}
                            resp = requests.put(url, json=body, timeout=5)
                            resp.raise_for_status()
                            # Proactively refresh System Status on success
                            mw2 = self.getMainWindow()
                            if mw2 and hasattr(mw2, 'system_status'):
                                try:
                                    QtCore.QTimer.singleShot(0, mw2.system_status.loadOverviewFromApi)
                                except Exception:
                                    pass
                        except Exception as exc:
                            QtCore.qWarning(f"Signal status set failed: {exc}")
                    threading.Thread(target=_run, daemon=True).start()
                    success_any = True
            else:
                QtCore.qWarning(f"Unsupported suggestedAction: object={obj}, action={action}")
        return success_any

    def _normalizeSignalStatus(self, status):
        """Map various aspect/status names to server-supported tri-state values."""
        if not status:
            return 'RED'
        s = status.strip().upper()
        # Normalize common aliases
        if s in ('RED', 'STOP', 'UK_DANGER', 'DANGER'):
            return 'RED'
        if s in (
            'YELLOW', 'AMBER', 'CAUTION', 'UK_CAUTION', 'UK_PRE_CAUTION', 'PRE_CAUTION', 'PRECAUTION'
        ):
            return 'YELLOW'
        if s in ('GREEN', 'CLEAR', 'UK_CLEAR'):
            return 'GREEN'
        # Fallback: try first letter mapping
        if s.startswith('UK_'):
            if 'DANGER' in s or 'RED' in s:
                return 'RED'
            if 'CLEAR' in s or 'GREEN' in s:
                return 'GREEN'
            return 'YELLOW'
        return 'YELLOW'

    def acceptHintProgrammatically(self, hint):
        """Accept a hint without relying on a visible widget/buttons."""
        try:
            self.executeSuggestedAction(hint)
        except Exception as exc:
            QtCore.qWarning(f"AIHintsWidget.executeSuggestedAction error: {exc}")
        self.provider.respondToHint(hint.get("id"), "ACCEPT")

    def _showAcceptedAndRemoveLater(self, widget, hint_id):
        # Show accepted chip
        try:
            accepted_label = widget.property("_tt_acceptedLabel")
            if accepted_label:
                accepted_label.setVisible(True)
        except Exception:
            pass
        # Soften background to indicate success
        try:
            widget.setStyleSheet(widget.styleSheet() + "\nQFrame { background-color: #eafaf1; border-left-color: #28a745; }")
        except Exception:
            pass
        # Disable or hide action buttons
        try:
            btns = widget.property("_tt_hintButtons") or ()
            for b in btns:
                if b:
                    b.setEnabled(False)
                    b.setVisible(False)
        except Exception:
            pass
        # Schedule removal
        def _remove():
            try:
                if widget in self.hint_widgets:
                    self.hint_widgets.remove(widget)
                widget.setVisible(False)
                widget.deleteLater()
            except Exception:
                pass
            try:
                self._just_accepted_ids.discard(hint_id)
            except Exception:
                pass
        QtCore.QTimer.singleShot(1000, _remove)
        
    def overrideHint(self, hint):
        """Show dialog to override/modify the AI hint"""
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("Override AI Hint")
        dialog.setMinimumSize(500, 300)
        
        layout = QtWidgets.QVBoxLayout(dialog)
        
        # Original hint
        layout.addWidget(QtWidgets.QLabel("Original AI Suggestion:"))
        original_text = QtWidgets.QTextEdit()
        original_text.setPlainText(hint["message"])
        original_text.setReadOnly(True)
        original_text.setMaximumHeight(80)
        layout.addWidget(original_text)
        
        # Override input
        layout.addWidget(QtWidgets.QLabel("Your Override:"))
        override_text = QtWidgets.QTextEdit()
        override_text.setPlaceholderText("Enter your alternative action or reasoning...")
        layout.addWidget(override_text)
        
        # Buttons
        button_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_() == QtWidgets.QDialog.Accepted:
            override_content = override_text.toPlainText().strip()
            if not override_content:
                QtWidgets.QMessageBox.warning(self, "No Override", "Please enter an override action.")
                return

            def _done(ok):
                if ok:
                    self.provider.refreshHints()
                    QtWidgets.QMessageBox.information(self, "Override Recorded", "Override acknowledged.")
                else:
                    QtWidgets.QMessageBox.critical(self, "Error", "Failed to send override.")

            self.provider.respondToHint(hint.get("id"), "OVERRIDE", override_action={"reason": override_content}, callback=_done)


class AIHintsDockWidget(QtWidgets.QDockWidget):
    """Dock widget container for AI hints"""
    
    def __init__(self, parent=None):
        super().__init__("AI Routing Hints", parent)
        
        self.hints_widget = AIHintsWidget(self)
        self.setWidget(self.hints_widget)
        
        # Configure dock widget
        self.setFeatures(
            QtWidgets.QDockWidget.DockWidgetMovable |
            QtWidgets.QDockWidget.DockWidgetFloatable
        )
        # Ensure dock widget cannot be closed accidentally
        self.setFeatures(self.features() & ~QtWidgets.QDockWidget.DockWidgetClosable)
        self.setMinimumWidth(300)
        self.setMaximumWidth(500)



