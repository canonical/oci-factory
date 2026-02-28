package trigger_test

import (
	"testing"

	. "gopkg.in/check.v1"

	"github.com/canonical/oci-factory/tools/cli-client/internals/trigger"
	"gopkg.in/yaml.v3"
)

const track = "1.0-22.04"
const eol = "2025-05-01T00:00:00Z"

type TriggerSuite struct{}

func Test(t *testing.T) { TestingT(t) }

var _ = Suite(&TriggerSuite{})

var buildMetadata = trigger.BuildMetadata{
	Source:    "canonical/oci-factory",
	Commit:    "f0250895d1758cdab6619122a4fd67dbbde3004a",
	Directory: "examples/mock-rock/1.0/",
}
var risks = []string{"candidate", "stable"}

func (s *TriggerSuite) TestNewUploadReleaseTrack(c *C) {
	result := trigger.NewUploadReleaseTrack(track, risks, eol)
	expectedYaml := `1.0-22.04:
    end-of-life: "2025-05-01T00:00:00Z"
    risks:
        - candidate
        - stable
`
	resultBytes, err := yaml.Marshal(result)
	c.Assert(err, IsNil)
	resultYaml := string(resultBytes)

	c.Assert(resultYaml, Equals, expectedYaml)
}

func (s *TriggerSuite) TestNewUploadImageTrigger(c *C) {
	result := trigger.NewUploadImageTrigger(buildMetadata, trigger.NewUploadReleaseTrack(track, risks, eol))
	expectedYaml := `source: canonical/oci-factory
commit: f0250895d1758cdab6619122a4fd67dbbde3004a
directory: examples/mock-rock/1.0/
release:
    1.0-22.04:
        end-of-life: "2025-05-01T00:00:00Z"
        risks:
            - candidate
            - stable
`
	resultBytes, err := yaml.Marshal(result)
	c.Assert(err, IsNil)
	resultYaml := string(resultBytes)

	c.Assert(resultYaml, Equals, expectedYaml)
}

func (s *TriggerSuite) TestNewUploadTrigger(c *C) {
	result := trigger.NewUploadTrigger([]trigger.UploadImageTrigger{
		trigger.NewUploadImageTrigger(buildMetadata, trigger.NewUploadReleaseTrack(track, risks, eol)),
	},
	)
	resultYaml := result.ToYamlString()
	expectedYaml := `version: 2
upload:
    - source: canonical/oci-factory
      commit: f0250895d1758cdab6619122a4fd67dbbde3004a
      directory: examples/mock-rock/1.0/
      release:
        1.0-22.04:
            end-of-life: "2025-05-01T00:00:00Z"
            risks:
                - candidate
                - stable
`
	c.Assert(resultYaml, Equals, expectedYaml)
}
