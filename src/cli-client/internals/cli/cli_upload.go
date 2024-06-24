package cli

import (
	"fmt"
	"os"
	"regexp"
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

var releaseKeys = []string{"tracks", "risks", "eol"}

func init() {
	parser.Command.AddCommand("upload", "Trigger the build and release for the image in the current working directory",
		"long description", &CmdUpload{})
}

func (c *CmdUpload) Execute(args []string) error {
	releases, err := parseUploadReleases(c.UploadRelease)
	if err != nil {
		parser.WriteHelp(os.Stdout)
		return err
	}
	triggerUploadReleases(releases)
	return nil
}

// parseUploadReleases parses the release arguments and returns a list of UploadRelease structs.
// The release arguments are expected to be in the format "tracks=<track>,risks=<risk1>[,<risk2>...],eol=yyyy-mm-dd".
// Multiple release arguments can be passed, separated by spaces.
func parseUploadReleases(args []string) ([]UploadRelease, error) {
	var release UploadRelease
	releases := make([]UploadRelease, 0)
	regex := regexp.MustCompile("(((tracks=[^,]+)|(risks=[^,]+,*[^,]+)|(eol=[^,]+)),?){3}")

	for _, argStr := range args {
		matches := regex.FindStringSubmatch(argStr)
		if matches == nil || len(matches) != 6 {
			return nil, fmt.Errorf("invalid argument: %s", argStr)
		}

		for _, part := range matches[3:] {
			if part == "" {
				return nil, fmt.Errorf("invalid argument: %s", argStr)
			}

			keyValue := strings.Split(part, "=")
			if len(keyValue) != 2 {
				return nil, fmt.Errorf("invalid key-value pair: %s", part)
			}
			key := keyValue[0]
			value := keyValue[1]

			switch key {
			case "tracks":
				release.Track = value
			case "risks":
				release.Risks = strings.Split(value, ",")
			case "eol":
				release.EndOfLife = value
			default:
				return nil, fmt.Errorf("invalid key: %s", key)
			}
		}

		if release.Track == "" || len(release.Risks) == 0 || release.EndOfLife == "" {
			return nil, fmt.Errorf("missing required fields in argument: %s", argStr)
		}

		releases = append(releases, release)
	}
	return releases, nil
}

func triggerUploadReleases(releases []UploadRelease) {
	// really builds
	if len(releases) == 0 {
		fmt.Println("No release track specified, no build will be triggered.")
		return
	}

	buildMetadata := trigger.InferBuildMetadata()
	var uploadReleaseTrack = make(trigger.UploadReleaseTrack)
	for _, release := range releases {
		eol, err := validateAndFormatDate(release.EndOfLife)
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
}