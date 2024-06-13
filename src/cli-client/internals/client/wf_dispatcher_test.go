package client_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	"github.com/canonical/oci-factory/cli-client/internals/client"
	"github.com/canonical/oci-factory/cli-client/internals/token"
)

func testHeaderEntriesEqual(header1 map[string][]string, header2 map[string]string) bool {
	for key, value := range header2 {
		fmt.Println(key, header1[key])
		fmt.Println(key, header2[key])
		fmt.Println(key, header1[key][0])
		if header1[key][0] != value {
			return false
		}
	}
	return true
}

func TestSetHeaderWithMap(t *testing.T) {
	mockUrl := "https://mock.url"
	mockJson := []byte(`{"mock":"json"}`)
	os.Setenv("GITHUB_TOKEN", "ghp_AAAAAAAA")
	header := client.NewGithubAuthHeaderMap()
	request1, _ := http.NewRequest("POST", mockUrl, bytes.NewBuffer(mockJson))
	client.SetHeaderWithMap(request1, header)
	request2, _ := http.NewRequest("POST", mockUrl, bytes.NewBuffer(mockJson))
	request2.Header.Set("Accept", "application/vnd.github+json")
	request2.Header.Set("Authorization", "Bearer "+token.GetAccessToken())
	request2.Header.Set("X-GitHub-Api-Version", "2022-11-28")

	if fmt.Sprintf("%+v", request1) != fmt.Sprintf("%+v", request2) {
		t.Fatalf("request 1 not equals to request 2\nrequest1: %+v\nrequest2: %+v", request1, request2)
	}
}

func TestDispatchWorkflow(t *testing.T) {
	mockJson := []byte(`{"mock":"json"}`)
	saveToken := token.UpdateEnvToken("ghp_AAAAAAAA")
	header := client.NewGithubAuthHeaderMap()

	expectedPayload := client.NewPayload("image-name", "image-trigger")
	expectedPayloadJSON, _ := json.Marshal(expectedPayload)

	// Create a mock server
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify the request method, URL, and payload
		if r.Method != http.MethodPost {
			t.Fatalf("unexpected request method, want POST, got %s", r.Method)
		}
		// Verify the request header
		// TODO received header is missing X-GitHub-Api-Version
		if !testHeaderEntriesEqual(r.Header, header) {
			t.Fatalf("unexpected request header, want %v, got %v", header, r.Header)
		}
		// header setting is tested above and transferring is tested in the http library
		body, _ := io.ReadAll(r.Body)
		if !bytes.Equal(body, expectedPayloadJSON) {
			t.Fatalf("unexpected request payload, want %s, got %s", string(expectedPayloadJSON), string(body))
		}
		// Set the no content response status code and body
		w.WriteHeader(http.StatusNoContent)
		w.Write([]byte(``))
	}))
	defer mockServer.Close()

	request, _ := http.NewRequest(http.MethodPost, mockServer.URL, bytes.NewBuffer(mockJson))
	client.SetHeaderWithMap(request, header)

	// Call the DispatchWorkflow function
	client.DispatchWorkflowImpl_(expectedPayload, mockServer.URL)
	token.RestoreTokenEnv(saveToken)
}
