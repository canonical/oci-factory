package cli

import (
	"fmt"
	"os"
	"regexp"
	"slices"
	"strings"

	"github.com/canonical/oci-factory/tools/cli-client/internals/client"
	"github.com/canonical/oci-factory/tools/cli-client/internals/trigger"
)

type UploadRelease struct {
	Track     string
	Risks     []string
	EndOfLife string
}

type CmdUpload struct {
	UploadRelease          []string `long:"release" description:"Release images to container registries.\nSyntax: --release track=<release track>,risks=<risk1>[,<risk2>...],eol=yyyy-mm-dd"`
	IgnoredVulnerabilities string   `long:"ignored-vulnerabilities" description:"Comma-separated list of vulnerabilities to ignore when triggering the build and release. This is a global flag that applies to all releases specified with --release. Syntax: --ignored-vulnerabilities FINDING_ID_1[,FINDING_ID_2...]"`
}

var riskOptions = []string{"stable", "candidate", "beta", "edge"}

func init() {
	parser.AddCommand("upload", "Trigger the build and release for a rock",
		`Trigger the build of a rock with the rockcraft.yaml in the current working
		directory and the release with --release`,
		&CmdUpload{})
}

func (c *CmdUpload) Execute(args []string) error {
	releases, err := parseUploadReleases(c.UploadRelease)
	if err != nil {
		return fmt.Errorf("error parsing release arguments: %v", err)
	}
	ignoredVulnerabilities := parseIgnoredVulnerabilities(c.IgnoredVulnerabilities)
	triggerUploadReleases(releases, ignoredVulnerabilities)
	return nil
}

func checkMissingFields(release UploadRelease) []string {
	var missing []string
	if release.Track == "" {
		missing = append(missing, "track")
	}
	if len(release.Risks) == 0 {
		missing = append(missing, "risks")
	}
	if release.EndOfLife == "" {
		missing = append(missing, "eol")
	}
	return missing
}

// parseUploadReleases parses the release arguments and returns a list of UploadRelease structs.
// The release arguments are expected to be in the format "track=<track>,risks=<risk1>[,<risk2>...],eol=yyyy-mm-dd".
// Multiple release arguments can be passed, separated by spaces.
func parseUploadReleases(args []string) ([]UploadRelease, error) {
	releases := make([]UploadRelease, 0)
	regex := regexp.MustCompile(`(\w+)=(([^,=]*?,)*)`)

	for _, origArgStr := range args {
		// Append a "," to the end of the string to enable a simpler regex matching key-value pairs
		argStr := origArgStr + ","
		var release UploadRelease
		matches := regex.FindAllStringSubmatch(argStr, -1)
		if matches == nil {
			return nil, fmt.Errorf("invalid argument: %s", origArgStr)
		}

		for _, part := range matches {
			if part == nil || len(part) < 3 {
				return nil, fmt.Errorf("invalid argument: %s", origArgStr)
			}
			key := part[1]
			valueString := strings.TrimRight(part[2], ",")
			values := strings.Split(valueString, ",")

			switch key {
			case "track":
				if len(values) != 1 || values[0] == "" {
					return nil, fmt.Errorf("invalid track value: %s", valueString)
				}
				if release.Track != "" {
					return nil, fmt.Errorf("duplicated value for track")
				}
				release.Track = values[0]
			case "risks":
				for _, risk := range values {
					if !slices.Contains(riskOptions, risk) {
						return nil, fmt.Errorf("invalid risk value: %s", risk)
					}
				}
				if len(release.Risks) > 0 {
					return nil, fmt.Errorf("duplicated value for risks")
				}
				release.Risks = values
			case "eol":
				if len(values) != 1 || values[0] == "" {
					return nil, fmt.Errorf("invalid eol value: %s", valueString)
				}
				eol, err := validateAndFormatDate(values[0])
				if err != nil {
					return nil, fmt.Errorf("EOL with wrong data formats: %v", err)
				}
				if release.EndOfLife != "" {
					return nil, fmt.Errorf("duplicated value for eol")
				}
				release.EndOfLife = eol
			default:
				return nil, fmt.Errorf("invalid key-value pair: %s=%s", key, valueString)
			}
		}

		// Check if all required fields are present
		if missing := checkMissingFields(release); missing != nil {
			return nil, fmt.Errorf("missing fields: %s", strings.Join(missing, ", "))
		}

		releases = append(releases, release)
	}
	if len(releases) == 0 {
		return nil, fmt.Errorf("no release track specified, no build will be triggered")
	}
	return releases, nil
}

func parseIgnoredVulnerabilities(arg string) []string {
	splitFn := func(c rune) bool {
		return c == ','
	}
	return strings.FieldsFunc(arg, splitFn)
}

func triggerUploadReleases(releases []UploadRelease, ignored_vulnerabilities []string) {
	// really builds
	buildMetadata := trigger.InferBuildMetadata()
	buildMetadata.IgnoredVulnerabilities = ignored_vulnerabilities
	var uploadReleaseTrack = make(trigger.UploadReleaseTrack)
	for _, release := range releases {
		uploadReleaseTrack[release.Track] = trigger.UploadRelease{
			EndOfLife: release.EndOfLife,
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
	if !opts.SkipConfirmation {
		err := blockForConfirm("Do you want to continue?")
		if err != nil {
			fmt.Println(err)
			os.Exit(1)
		}
	}
	externalRefID := payload.Inputs.ExternalRefID
	client.DispatchWorkflow(payload)
	client.WorkflowPolling(externalRefID)
}
