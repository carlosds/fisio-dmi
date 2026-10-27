package main

import "testing"

func TestSesionValida(t *testing.T) {
	casos := map[string]string{
		"":             "",
		"-":            "-",
		"c:abc":        "c:abc",
		"s:raiz":       "s:raiz",
		"c:":           "",
		"x:abc":        "",
		"!c:abc":       "!c:abc",
		"!c:abc,s:def": "!c:abc,s:def",
		"!c:abc,":      "",
		"!":            "",
		"!-":           "",
		"!c:abc,x:1":   "",
		"todas":        "",
	}
	for entrada, quiero := range casos {
		if got := sesionValida(entrada); got != quiero {
			t.Errorf("sesionValida(%q) = %q; quiero %q", entrada, got, quiero)
		}
	}
}
