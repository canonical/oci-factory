package client_test

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/http/httptest"
	"os"

	. "gopkg.in/check.v1"

	"github.com/canonical/oci-factory/cli-client/internals/client"
	"github.com/canonical/oci-factory/cli-client/internals/token"
)

type DispatcherSuite struct{}

// `func Test(t *testing.T) { TestingT(t) }` defined in client_test.go

var _ = Suite(&DispatcherSuite{})

func (s *DispatcherSuite) TestSetHeaderWithMap(c *C) {
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

	c.Assert(fmt.Sprintf("%+v", request1), Equals, fmt.Sprintf("%+v", request2))
}

func (s *DispatcherSuite) TestDispatchWorkflow(c *C) {
	mockJson := []byte(`{"mock":"json"}`)
	saveToken := token.UpdateEnvToken("ghp_AAAAAAAA")
	header := client.NewGithubAuthHeaderMap()

	expectedPayload := client.NewPayload("image-name", "image-trigger")
	expectedPayloadJSON, _ := json.Marshal(expectedPayload)

	// Create a mock server
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify the request method, URL, and payload
		c.Assert(r.Method, Equals, http.MethodPost)
		c.Assert(r.Header.Get("Accept"), Equals, "application/vnd.github+json")
		c.Assert(r.Header.Get("Authorization"), Equals, "Bearer "+token.GetAccessToken())
		c.Assert(r.Header.Get("X-GitHub-Api-Version"), Equals, "2022-11-28")
		// header setting is tested above and transferring is tested in the http library
		body, _ := io.ReadAll(r.Body)
		c.Assert(body, DeepEquals, expectedPayloadJSON)
		// Set the no content response status code and body
		w.WriteHeader(http.StatusNoContent)
		w.Write([]byte(``))
	}))
	defer mockServer.Close()

	request, _ := http.NewRequest(http.MethodPost, mockServer.URL, bytes.NewBuffer(mockJson))
	client.SetHeaderWithMap(request, header)

	// Call the DispatchWorkflow function
	originalURL := client.SetWorkflowDispatchURL(mockServer.URL)
	client.DispatchWorkflow(expectedPayload)
	token.RestoreTokenEnv(saveToken)
	client.SetWorkflowDispatchURL(originalURL)
}
