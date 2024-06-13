package client_test

import (
	"bytes"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/canonical/oci-factory/cli-client/internals/client"
	"github.com/canonical/oci-factory/cli-client/internals/token"
)

func TestSendRequest(t *testing.T) {
	mockPayload := []byte(`{"mock":"payload"}`)
	expectedStatusCode := http.StatusOK

	// Create a mock server
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify the request method, URL, and payload
		if r.Method != http.MethodPost {
			t.Errorf("unexpected request method, want POST, got %s", r.Method)
		}
		body, _ := io.ReadAll(r.Body)
		if !bytes.Equal(body, mockPayload) {
			t.Errorf("unexpected request payload, want %s, got %s", string(mockPayload), string(body))
		}
		// Set the response status code and body
		w.WriteHeader(expectedStatusCode)
		w.Write([]byte(`{"mock":"response"}`))
	}))
	defer mockServer.Close()

	saveToken := os.Getenv(token.TokenVarName)
	os.Setenv(token.TokenVarName, "ghp_AAAAAAAA")
	// Call the SendRequest function
	response := client.SendRequest(http.MethodPost, mockServer.URL, mockPayload, expectedStatusCode)
	token.RestoreTokenEnv(saveToken)

	// Verify the response
	expectedResponse := []byte(`{"mock":"response"}`)
	if !bytes.Equal(response, expectedResponse) {
		t.Errorf("unexpected response, want %s, got %s", string(expectedResponse), string(response))
	}
}
