package trigger

import (
	"github.com/canonical/oci-factory/cli-client/internals/logger"
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
	Source    string             `yaml:"source"`
	Commit    string             `yaml:"commit"`
	Directory string             `yaml:"directory"`
	Release   UploadReleaseTrack `yaml:"release,omitempty"`
}

type UploadTrigger struct {
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

func (u *UploadReleaseTrack) AddTrack(track string, risks []string, eol string) {
	(*u)[track] = UploadRelease{
		EndOfLife: eol,
		UploadReleaseRisks: UploadReleaseRisks{
			Risks: risks,
		},
	}
}

func NewUploadImageTrigger(buildMetadata BuildMetadata, tracks UploadReleaseTrack) UploadImageTrigger {
	UploadImageTrigger := UploadImageTrigger{
		Source:    buildMetadata.Source,
		Commit:    buildMetadata.Commit,
		Directory: buildMetadata.Directory,
		Release:   tracks,
	}
	return UploadImageTrigger
}

func NewUploadTrigger(imageTriggers []UploadImageTrigger) UploadTrigger {
	trigger := UploadTrigger{
		UploadImageTriggers: imageTriggers,
	}
	return trigger
}

func (u *UploadTrigger) ToYamlString() string {
	yamlData, err := yaml.Marshal(u)
	if err != nil {
		logger.Panicf("Unable to marshall trigger: %s", err)
	}
	return string(yamlData)
}
