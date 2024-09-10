package trigger_test

import (
	"bytes"
	"os"
	"os/exec"
	"path/filepath"
	"strings"

	. "gopkg.in/check.v1"

	"github.com/canonical/oci-factory/tools/cli-client/internals/trigger"
)

type BuildMetadataSuite struct {
	dir string
}

var _ = Suite(&BuildMetadataSuite{})

func (s *BuildMetadataSuite) SetUpTest(c *C) {
	s.dir = c.MkDir()
}

func (s *BuildMetadataSuite) TestGetRockcraftYamlName(c *C) {
	f := filepath.Join(s.dir, "rockcraft.yaml")
	err := os.WriteFile(f, []byte("name: cli-client-tester"), 0644)
	c.Assert(err, IsNil)
	err = os.Chdir(s.dir)
	c.Assert(err, IsNil)
	result := trigger.GetRockcraftImageName()
	expected := "cli-client-tester"
	c.Assert(result, Equals, expected)
}

func (s *BuildMetadataSuite) TestGetBuildMetadataCustomDirector(c *C) {
	cmd := exec.Command("git", "--version")
	if err := cmd.Run(); err != nil {
		c.Fatal("git not installed")
	}
	repoPath := filepath.Join(s.dir, "tester-path")
	cmd = exec.Command("git", "clone", "https://github.com/canonical/oci-factory.git", repoPath)
	var errBuf bytes.Buffer
	cmd.Stderr = &errBuf
	if err := cmd.Run(); err != nil {
		c.Logf("stderr: %s", errBuf.String())
		c.Fatal(err)
	}

	err := os.Chdir(filepath.Join(repoPath, "examples", "mock-rock", "1.0"))
	c.Assert(err, IsNil)

	result := trigger.InferBuildMetadata()

	prefix := filepath.Join("examples", "mock-rock", "1.0") + "/"
	head, err := exec.Command("git", "rev-parse", "HEAD").Output()
	headStr := strings.TrimSpace(string(head))
	c.Assert(err, IsNil)
	source := "canonical/oci-factory"
	expected := trigger.BuildMetadata{
		Source:    source,
		Directory: prefix,
		Commit:    headStr,
	}

	c.Assert(result, DeepEquals, expected)
}
