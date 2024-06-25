package trigger_test

import (
	"testing"

	"github.com/canonical/oci-factory/cli-client/internals/trigger"
	"gopkg.in/yaml.v3"
)

const track = "1.0-22.04"
const eol = "2025-05-01T00:00:00Z"

var buildMetadata = trigger.BuildMetadata{
	Source:    "canonical/oci-factory",
	Commit:    "f0250895d1758cdab6619122a4fd67dbbde3004a",
	Directory: "examples/mock-rock/1.0/",
}
var risks = []string{"candidate", "stable"}

func TestNewUploadReleaseTrack(t *testing.T) {
	result := trigger.NewUploadReleaseTrack(track, risks, eol)
	expectedYaml := `1.0-22.04:
    end-of-life: "2025-05-01T00:00:00Z"
    risks:
        - candidate
        - stable
`
	resultBytes, err := yaml.Marshal(result)
	if err != nil {
		t.Fatal(err)
	}
	resultYaml := string(resultBytes)

	if resultYaml != expectedYaml {
		t.Fatalf("result != expected value\n result: %s\nexpected: %s", resultYaml, expectedYaml)
	}
}

func TestNewUploadImageTrigger(t *testing.T) {
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
	if err != nil {
		t.Fatal(err)
	}
	resultYaml := string(resultBytes)

	if resultYaml != expectedYaml {
		t.Fatalf("result != expected value\n result: %s\nexpected: %s", resultYaml, expectedYaml)
	}
}

func TestNewUploadTrigger(t *testing.T) {
	result := trigger.NewUploadTrigger([]trigger.UploadImageTrigger{
		trigger.NewUploadImageTrigger(buildMetadata, trigger.NewUploadReleaseTrack(track, risks, eol)),
	},
	)
	resultYaml := result.ToYamlString()
	expectedYaml := `version: 1
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

	if resultYaml != expectedYaml {
		t.Fatalf("result != expected value\n result: %s\nexpected: %s", resultYaml, expectedYaml)
	}
}
