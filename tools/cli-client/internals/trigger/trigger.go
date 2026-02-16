package trigger

import (
	"github.com/canonical/oci-factory/tools/cli-client/internals/logger"
	"gopkg.in/yaml.v3"
)

type UploadReleaseRisks struct {
	Risks []string `yaml:"risks"`
}

type UploadRelease struct {
	EndOfLife          string `yaml:"end-of-life"`
	UploadReleaseRisks `yaml:",inline"`
}

type UploadReleaseTrack map[string]UploadRelease

type UploadImageTrigger struct {
	Source                 string             `yaml:"source"`
	Commit                 string             `yaml:"commit"`
	Directory              string             `yaml:"directory"`
	Release                UploadReleaseTrack `yaml:"release,omitempty"`
	IgnoredVulnerabilities []string           `yaml:"ignored-vulnerabilities,omitempty"`
}

type UploadTrigger struct {
	Version             int                  `yaml:"version"`
	UploadImageTriggers []UploadImageTrigger `yaml:"upload"`
}

// All the arguments should be validated before passing to this function
func NewUploadReleaseTrack(track string, risks []string, eol string) UploadReleaseTrack {
	newTrack := UploadReleaseTrack{
		track: {
			EndOfLife: eol,
			UploadReleaseRisks: UploadReleaseRisks{
				Risks: risks,
			},
		},
	}

	return newTrack
}

func NewUploadImageTrigger(buildMetadata BuildMetadata, tracks UploadReleaseTrack) UploadImageTrigger {
	UploadImageTrigger := UploadImageTrigger{
		Source:                 buildMetadata.Source,
		Commit:                 buildMetadata.Commit,
		Directory:              buildMetadata.Directory,
		IgnoredVulnerabilities: buildMetadata.IgnoredVulnerabilities,
		Release:                tracks,
	}
	return UploadImageTrigger
}

func NewUploadTrigger(imageTriggers []UploadImageTrigger) UploadTrigger {
	trigger := UploadTrigger{
		Version:             1,
		UploadImageTriggers: imageTriggers,
	}
	return trigger
}

func (u *UploadTrigger) ToYamlString() string {
	yamlData, err := yaml.Marshal(u)
	if err != nil {
		logger.Panicf("Unable to marshal trigger: %s", err)
	}
	return string(yamlData)
}
