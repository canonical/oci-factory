package trigger_test

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"strings"
	"testing"

	"github.com/canonical/oci-factory/cli-client/internals/trigger"
)

func TestGetRockcraftYamlName(t *testing.T) {
	tempDir := t.TempDir()
	f := filepath.Join(tempDir, "rockcraft.yaml")
	err := os.WriteFile(f, []byte("name: cli-client-tester"), 0644)
	if err != nil {
		t.Fatal(err)
	}
	err = os.Chdir(tempDir)
	if err != nil {
		t.Fatal(err)
	}
	result := trigger.GetRockcraftImageName()
	expected := "cli-client-tester"
	if result != expected {
		t.Fatalf("result != expected value")
	}
}

func TestGetBuildMetadataCustomDirectory(t *testing.T) {
	cmd := exec.Command("git", "--version")
	if err := cmd.Run(); err != nil {
		t.Fatal(err)
	}
	tempDir := t.TempDir()
	repoPath := filepath.Join(tempDir, "tester-path")
	cmd = exec.Command("git", "clone", "https://github.com/canonical/oci-factory.git", repoPath)
	var errBuf bytes.Buffer
	cmd.Stderr = &errBuf
	if err := cmd.Run(); err != nil {
		t.Logf("stderr: %s", errBuf.String())
		t.Fatal(err)
	}

	err := os.Chdir(filepath.Join(repoPath, "examples", "mock-rock", "1.0"))
	if err != nil {
		t.Fatal(err)
	}

	result := trigger.InferBuildMetadata()

	prefix := filepath.Join("examples", "mock-rock", "1.0") + "/"
	head, err := exec.Command("git", "rev-parse", "HEAD").Output()
	headStr := strings.TrimSpace(string(head))
	if err != nil {
		t.Fatal(err)
	}
	source := "canonical/oci-factory"
	expected := trigger.BuildMetadata{
		Source:    source,
		Directory: prefix,
		Commit:    headStr,
	}

	if result != expected {
		t.Fatalf("result != expected value\n result: %+v\nexpected: %+v", result, expected)
	}
}
