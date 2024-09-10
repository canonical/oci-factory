package token_test

import (
	"os"
	"testing"

	"github.com/canonical/oci-factory/tools/cli-client/internals/token"
)

func TestReadAccessTokenEnv(t *testing.T) {
	expectedToken := "ghp_test123ToKeN"
	originalToken := os.Getenv(token.TokenVarName)
	restoreEnvToken := token.SetEnvToken(expectedToken)
	err := os.Setenv(token.TokenVarName, expectedToken)
	if err != nil {
		t.Fatalf("Unable to set env variable: %v", err)
	}
	resultToken := token.GetAccessToken()
	if resultToken != expectedToken {
		t.Fatalf("")
	}
	restoreEnvToken()
	if os.Getenv(token.TokenVarName) != originalToken {
		t.Fatalf("Unable to restore saved env variable")
	}
}
