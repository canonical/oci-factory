package cli

import (
	"fmt"
	"strings"

	"github.com/canonical/oci-factory/cli-client/internals/client"
	"github.com/canonical/oci-factory/cli-client/internals/logger"
	"github.com/canonical/oci-factory/cli-client/internals/trigger"
)

type UploadRelease struct {
	Track     string
	Risks     []string
	EndOfLife string
}

type CmdUpload struct {
	UploadRelease []string `long:"release" description:"Release images to container registries.\nSyntax: --release tracks=<release track>,risks=<risk1>[,<risk2>...],eol=yyyy-mm-dd"`
}

var cmdUpload CmdUpload
var releases = make([]UploadRelease, 0)

func init() {
	// fmt.Println("DEBUG Adding upload to parser commands")
	parser.Command.AddCommand("upload", "Trigger the build and release for the image in the current working directory",
		"long description", &cmdUpload)
}

func (c *CmdUpload) Execute(args []string) error {
	// fmt.Println("DEBUG CMD upload args:", args)
	parseUploadReleases(c.UploadRelease)
	triggerUploadReleases()
	return nil
}

func parseUploadReleases(args []string) error {
	var release UploadRelease
	for _, argStr := range args {
		// fmt.Println("DEBUG Upload release arg:", argStr)
		parts := strings.Split(argStr, ",")

		var risks []string
		for _, part := range parts {
			keyValue := strings.SplitN(part, "=", 2)
			if len(keyValue) == 1 && len(risks) > 0 {
				// This is part of the risks list (e.g., "stable" in "risks=beta,stable")
				risks = append(risks, keyValue[0])
				continue
			}
			if len(keyValue) != 2 {
				return fmt.Errorf("invalid key-value pair: %s", part)
			}
			key := keyValue[0]
			value := keyValue[1]

			switch key {
			case "tracks":
				release.Track = value
			case "risks":
				risks = append(risks, strings.Split(value, ",")...)
			case "eol":
				release.EndOfLife = value
			default:
				fmt.Errorf("unknown key: %s", key)
			}
		}
		release.Risks = risks
		releases = append(releases, release)
	}
	return nil
}

// use the global variable `releases` directly
func triggerUploadReleases() {
	// really builds
	if len(releases) > 0 {
		buildMetadata := trigger.InferBuildMetadata()
		var uploadReleaseTrack = make(trigger.UploadReleaseTrack)
		for _, release := range releases {
			eol, err := ValidateAndFormatDate(release.EndOfLife)
			if err != nil {
				logger.Panicf("EOL with wrong data formats: %v", err)
			}
			uploadReleaseTrack[release.Track] = trigger.UploadRelease{
				EndOfLife: eol,
				UploadReleaseRisks: trigger.UploadReleaseRisks{
					Risks: release.Risks,
				},
			}
		}
		imageTrigger := trigger.NewUploadImageTrigger(buildMetadata, uploadReleaseTrack)
		uploadTrigger := trigger.NewUploadTrigger([]trigger.UploadImageTrigger{imageTrigger})
		imageName := trigger.GetRockcraftImageName()
		payload := client.NewPayload(imageName, uploadTrigger.ToYamlString())
		fmt.Printf("The %s image will be built and released with following triggers:\n", imageName)
		fmt.Println(uploadTrigger.ToYamlString())
		if !opts.Confirm {
			blockForConfirm("Do you want to continue?", 2)
		}
		externalRefID := payload.Inputs.ExternalRefID
		client.DispatchWorkflow(payload)
		client.WorkflowPolling(externalRefID)
	} else {
		fmt.Println("Nothing passed in --release, upload will be skipped.")
	}
}
