package main

import (
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestSoloLocal(t *testing.T) {
	h := soloLocal(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(200) }))
	casos := []struct {
		host, origin string
		want         int
	}{
		{"127.0.0.1:8765", "", 200},
		{"127.0.0.1:8765", "http://127.0.0.1:8765", 200},
		{"localhost:8765", "http://localhost:8765", 200},
		{"127.0.0.1:8765", "https://malo.example", 403},
		{"127.0.0.1:8765", "null", 403},
		{"malo.example:8765", "", 403}, // DNS rebinding
		{"127.0.0.1:9999", "", 403},
	}
	for _, c := range casos {
		r := httptest.NewRequest("POST", "http://"+c.host+"/api/restaurar", nil)
		r.Host = c.host
		if c.origin != "" {
			r.Header.Set("Origin", c.origin)
		}
		w := httptest.NewRecorder()
		h.ServeHTTP(w, r)
		if w.Code != c.want {
			t.Errorf("host=%q origin=%q: %d, esperaba %d", c.host, c.origin, w.Code, c.want)
		}
	}
}
