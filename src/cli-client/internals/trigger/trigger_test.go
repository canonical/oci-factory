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
	expectedYaml := "1.0-22.04:\n"
	expectedYaml += "    end-of-life: \"2025-05-01T00:00:00Z\"\n"
	expectedYaml += "    risks:\n"
	expectedYaml += "        - candidate\n"
	expectedYaml += "        - stable\n"
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
	expectedYaml := "source: canonical/oci-factory\n"
	expectedYaml += "commit: f0250895d1758cdab6619122a4fd67dbbde3004a\n"
	expectedYaml += "directory: examples/mock-rock/1.0/\n"
	expectedYaml += "release:\n"
	expectedYaml += "    1.0-22.04:\n"
	expectedYaml += "        end-of-life: \"2025-05-01T00:00:00Z\"\n"
	expectedYaml += "        risks:\n"
	expectedYaml += "            - candidate\n"
	expectedYaml += "            - stable\n"
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
	expectedYaml := "version: 1\nupload:\n"
	expectedYaml += "    - source: canonical/oci-factory\n"
	expectedYaml += "      commit: f0250895d1758cdab6619122a4fd67dbbde3004a\n"
	expectedYaml += "      directory: examples/mock-rock/1.0/\n"
	expectedYaml += "      release:\n"
	expectedYaml += "        1.0-22.04:\n"
	expectedYaml += "            end-of-life: \"2025-05-01T00:00:00Z\"\n"
	expectedYaml += "            risks:\n"
	expectedYaml += "                - candidate\n"
	expectedYaml += "                - stable\n"

	if resultYaml != expectedYaml {
		t.Fatalf("result != expected value\n result: %s\nexpected: %s", resultYaml, expectedYaml)
	}
}
