package client_test

import (
	"io"
	"net/http"
	"net/http/httptest"
	"os"
	"testing"

	. "gopkg.in/check.v1"

	"github.com/canonical/oci-factory/cli-client/internals/client"
	"github.com/canonical/oci-factory/cli-client/internals/token"
)

type ClientSuite struct{}

func Test(t *testing.T) { TestingT(t) }

var _ = Suite(&ClientSuite{})

func (s *ClientSuite) TestSendRequest(c *C) {
	mockPayload := []byte(`{"mock":"payload"}`)
	expectedStatusCode := http.StatusOK

	// Create a mock server
	mockServer := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Verify the request method, URL, and payload
		c.Assert(r.Method, Equals, http.MethodPost)
		body, _ := io.ReadAll(r.Body)
		c.Assert(body, DeepEquals, mockPayload)
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

	c.Assert(response, DeepEquals, expectedResponse)
}
