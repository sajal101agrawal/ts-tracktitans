// Copyright (C) 2008-2018 by Nicolas Piganeau and the TS2 TEAM
// (See AUTHORS file)
//
// This program is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published by
// the Free Software Foundation; either version 2 of the License, or
// (at your option) any later version.
//
// This program is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with this program; if not, write to the
// Free Software Foundation, Inc.,
// 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

//go:generate statik -src=../static

package server

import (
	"fmt"
	"html/template"
	"io/ioutil"
	"net/http"
	"os"
	"time"
	"encoding/json"

	"github.com/rakyll/statik/fs"
	_ "github.com/ts2/ts2-sim-server/server/statik"
	"github.com/ts2/ts2-sim-server/simulation"
	log "gopkg.in/inconshreveable/log15.v2"
)

const (
	DefaultAddr       string = "0.0.0.0"
	DefaultPort       string = "22222"
	MaxHubStartupTime        = 3 * time.Second
)

var (
	sim    *simulation.Simulation
	hub    *Hub
	logger log.Logger
	// initialSimSnapshot holds the initial JSON snapshot of the simulation
	// so we can restart from the original state via HTTP API.
	initialSimSnapshot []byte
)

// InitializeLogger creates the logger for the server module
func InitializeLogger(parentLogger log.Logger) {
	logger = parentLogger.New("module", "server")
}

// Run starts a http web server and websocket hub for the given simulation, on the given address and port.
func Run(s *simulation.Simulation, addr, port string) {
	logger.Info("Starting server")
	sim = s
	// Capture initial snapshot before any initialization/mutations
	// so we can restore the simulation to its initial state later.
	if b, err := json.Marshal(sim); err == nil {
		initialSimSnapshot = b
	} else {
		logger.Error("Unable to marshal initial simulation snapshot", "error", err)
	}
	startMetricsTicker()
	hubUp := make(chan bool)
	timer := time.After(MaxHubStartupTime)
	go hub.run(hubUp)
	select {
	case <-hubUp:
		HttpdStart(addr, port)
		os.Exit(1)
	case <-timer:
		log.Crit("Hub did not start")
		os.Exit(1)
	}
}

// HttpdStart starts the server which serves on the following routes:
//
//    / - Serves a HTTP home page with the server status and information about the loaded sim.
//        It also includes a JavaScript WebSocket client to communicate and manage the server.
//
//    /ws - WebSocket endpoint for all TS2 clients and managers.
func HttpdStart(addr, port string) {
	statikFS, err := fs.New()
	if err != nil {
		logger.Crit("Unable to read statik FS", "error", err)
		return
	}
	http.Handle("/static/", http.StripPrefix("/static/", http.FileServer(statikFS)))

	homeTemplFile, err := statikFS.Open("/index.html")
	if err != nil {
		logger.Crit("Unable to read index.html from statikFS", "error", err)
		return
	}
	homeTemplData, err := ioutil.ReadAll(homeTemplFile)
	if err != nil {
		logger.Crit("Unable to open `index.html` ", "error", err)
		return
	}
	homeTempl = template.Must(template.New("").Parse(string(homeTemplData)))

	http.HandleFunc("/", serveHome)
	http.HandleFunc("/ws", serveWs)
	http.HandleFunc("/api/suggestions", serveSuggestions)
	installHTTPAPI()

	serverAddress := fmt.Sprintf("%s:%s", addr, port)
	logger.Info("Starting HTTP", "submodule", "http", "address", serverAddress)
	err = http.ListenAndServe(serverAddress, nil)
	logger.Crit("HTTP crashed", "submodule", "http", "error", err)
}

// serveHome serves the html home.html page with integrated JS WebSocket client.
func serveHome(w http.ResponseWriter, r *http.Request) {
	logger.Debug("New HTTP connection", "submodule", "http", "remote", r.RemoteAddr)
	if r.URL.Path != "/" {
		http.Error(w, "Not found", http.StatusNotFound)
		return
	}
	if r.Method != "GET" {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	data := struct {
		Title       string
		Description string
		Host        string
	}{
		sim.Options.Title,
		sim.Options.Description,
		"ws://" + r.Host + "/ws",
	}
	homeTempl.Execute(w, data)
}

var homeTempl *template.Template

// serveSuggestions returns the current suggestions as JSON
func serveSuggestions(w http.ResponseWriter, r *http.Request) {
    logger.Debug("New HTTP suggestions request", "submodule", "http", "remote", r.RemoteAddr)
    if r.Method != "GET" {
        http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
        return
    }
    if sim == nil {
        http.Error(w, "Simulation not initialized", http.StatusServiceUnavailable)
        return
    }
    // force recompute if requested
    if r.URL.Query().Get("recompute") == "1" {
        simulation.RecomputeSuggestions()
    }
    w.Header().Set("Content-Type", "application/json; charset=utf-8")
    if sim.Suggestions == nil {
        _, _ = w.Write([]byte("{\"items\":[],\"generatedAt\":\"00:00:00\"}"))
        return
    }
    data, err := json.Marshal(sim.Suggestions)
    if err != nil {
        http.Error(w, "Internal error", http.StatusInternalServerError)
        return
    }
    _, _ = w.Write(data)
}
