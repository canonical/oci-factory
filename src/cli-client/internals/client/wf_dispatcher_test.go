package client_test

import (
	"bytes"
	"fmt"
	"net/http"
	"os"
	"testing"

	"github.com/canonical/oci-factory/cli-client/internals/client"
	"github.com/canonical/oci-factory/cli-client/internals/token"
)

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
