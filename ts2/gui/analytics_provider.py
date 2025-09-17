#
#   Copyright (C) 2008-2015 by
#     Nicolas Piganeau <npi@m4x.org> & TS2 Team
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

import threading
import requests
import time
import json

from Qt import QtCore


class KPIDataProvider(QtCore.QObject):
    """Asynchronous provider for fetching KPI analytics from server API.

    This class uses background threads (Python threading) to avoid blocking the UI.
    Results are emitted back on the Qt signal thread.
    """

    def __init__(self, base_url=None, api_key=None, parent=None):
        super().__init__(parent)
        # Base URL of analytics API, e.g. http://localhost:22222
        self._base_url = base_url or "http://localhost:22222"
        self._api_key = api_key
        self._session = requests.Session()
        self._timeout_seconds = 5

    kpisUpdated = QtCore.pyqtSignal(dict)
    historicalUpdated = QtCore.pyqtSignal(str, dict)
    errorOccurred = QtCore.pyqtSignal(str)

    def setBaseUrl(self, base_url):
        self._base_url = base_url or self._base_url

    def setApiKey(self, api_key):
        self._api_key = api_key

    def refreshKpis(self, time_range="1d"):
        """Fetch current KPI snapshot.

        :param time_range: one of ("1h","6h","1d","1w","1m")
        """

        def _run():
            try:
                headers = {}
                if self._api_key:
                    headers["X-API-Key"] = self._api_key
                url = f"{self._base_url}/api/analytics/kpis"
                params = {"timeRange": time_range}
                resp = self._session.get(url, params=params, headers=headers, timeout=self._timeout_seconds)
                resp.raise_for_status()
                data = resp.json()
                # Emit from worker thread; Qt will queue to receiver thread
                self.kpisUpdated.emit(data)
            except Exception as exc:
                self.errorOccurred.emit(str(exc))

        threading.Thread(target=_run, daemon=True).start()

    def fetchHistorical(self, metric="rtp", period="hourly"):
        """Fetch historical series for a metric.

        :param metric: "punctuality|rtp|averageDelay|p90Delay|throughput|utilization|acceptanceRate|openConflicts|headwayAdherence|headwayBreaches"
        :param period: "hourly|daily|weekly"
        """

        def _run():
            try:
                headers = {}
                if self._api_key:
                    headers["X-API-Key"] = self._api_key
                url = f"{self._base_url}/api/analytics/historical"
                params = {"metric": metric, "period": period}
                resp = self._session.get(url, params=params, headers=headers, timeout=self._timeout_seconds)
                resp.raise_for_status()
                data = resp.json()
                self.historicalUpdated.emit(metric, data)
            except Exception as exc:
                self.errorOccurred.emit(str(exc))

        threading.Thread(target=_run, daemon=True).start()


class AuditLogsProvider(QtCore.QObject):
    """Provider for Audit Logs: HTTP backfill + SSE live stream.

    Emits signals on the Qt thread; workers run in Python threads.
    """

    itemsAdded = QtCore.pyqtSignal(list)
    itemReceived = QtCore.pyqtSignal(dict)
    streamStatusChanged = QtCore.pyqtSignal(bool)
    errorOccurred = QtCore.pyqtSignal(str)

    def __init__(self, base_url=None, api_key=None, parent=None):
        super().__init__(parent)
        self._base_url = base_url or "http://localhost:22222"
        self._api_key = api_key
        self._session = requests.Session()
        self._timeout_seconds = 10
        self._running = False
        self._sse_thread = None
        self._last_id = 0
        self._lock = threading.Lock()

    def setBaseUrl(self, base_url):
        self._base_url = base_url or self._base_url

    def setApiKey(self, api_key):
        self._api_key = api_key

    def start(self, since_id=0, limit=500):
        """Start backfill and SSE stream."""
        with self._lock:
            self._last_id = max(self._last_id, int(since_id or 0))
            self._running = True

        # Kick off an initial backfill
        self.backfill(limit=limit)

        # Start SSE thread if not already
        if not self._sse_thread or not self._sse_thread.is_alive():
            self._sse_thread = threading.Thread(target=self._run_sse, daemon=True)
            self._sse_thread.start()

    def stop(self):
        """Stop the SSE stream."""
        with self._lock:
            self._running = False
        # Closing the session should help break out of iter_lines
        try:
            self._session.close()
        except Exception:
            pass

    def backfill(self, limit=500):
        """Fetch recent audit items after last_id via HTTP."""

        def _run():
            try:
                headers = {"Accept": "application/json"}
                if self._api_key:
                    headers["X-API-Key"] = self._api_key
                with self._lock:
                    since_id = self._last_id
                url = f"{self._base_url}/api/audit/logs"
                params = {"sinceId": since_id, "limit": max(1, min(int(limit or 500), 1000))}
                resp = self._session.get(url, params=params, headers=headers, timeout=self._timeout_seconds)
                resp.raise_for_status()
                data = resp.json() or {}
                items = data.get("items", [])

                # Update last_id and emit
                max_id = since_id
                normalized = []
                for it in items:
                    normalized.append(it)
                    try:
                        n = int(it.get("id", 0))
                        if n > max_id:
                            max_id = n
                    except Exception:
                        pass
                with self._lock:
                    if max_id > self._last_id:
                        self._last_id = max_id

                if normalized:
                    self.itemsAdded.emit(normalized)
            except Exception as exc:
                self.errorOccurred.emit(str(exc))

        threading.Thread(target=_run, daemon=True).start()

    def _run_sse(self):
        """Connect to SSE endpoint and emit incoming audit events."""
        headers = {
            "Accept": "text/event-stream",
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
        if self._api_key:
            headers["X-API-Key"] = self._api_key

        while True:
            with self._lock:
                if not self._running:
                    break
            try:
                url = f"{self._base_url}/api/audit/stream"
                # stream=True to iterate SSE
                resp = self._session.get(url, headers=headers, stream=True, timeout=(5, 60))
                resp.raise_for_status()
                self.streamStatusChanged.emit(True)

                event_type = None
                data_lines = []
                for raw_line in resp.iter_lines(decode_unicode=True):
                    with self._lock:
                        if not self._running:
                            break
                    if raw_line is None:
                        continue
                    line = raw_line.strip()
                    if not line:
                        # dispatch accumulated event
                        if event_type == "audit" and data_lines:
                            try:
                                payload = json.loads("\n".join(data_lines))
                                self._on_sse_item(payload)
                            except Exception as exc:
                                self.errorOccurred.emit(f"SSE parse error: {exc}")
                        event_type = None
                        data_lines = []
                        continue
                    if line.startswith(":"):
                        # heartbeat comment
                        continue
                    if line.startswith("event:"):
                        event_type = line.split(":", 1)[1].strip()
                        continue
                    if line.startswith("data:"):
                        data_lines.append(line.split(":", 1)[1].strip())
                        continue
                # loop ended; mark disconnected
                self.streamStatusChanged.emit(False)
            except Exception as exc:
                self.streamStatusChanged.emit(False)
                self.errorOccurred.emit(str(exc))
            # If still running, wait briefly and reconnect
            with self._lock:
                if not self._running:
                    break
            time.sleep(1)

    def _on_sse_item(self, item):
        # Update last id if numeric
        try:
            n = int(item.get("id", 0))
            with self._lock:
                if n > self._last_id:
                    self._last_id = n
        except Exception:
            pass
        self.itemReceived.emit(item)

