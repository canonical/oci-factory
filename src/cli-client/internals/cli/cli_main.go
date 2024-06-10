package cli

import (
	"bufio"
	"fmt"
	"os"
	"strings"

	"github.com/canonical/go-flags"
	"github.com/canonical/oci-factory/cli-client/internals/client"
	"github.com/canonical/oci-factory/cli-client/internals/logger"
	"github.com/canonical/oci-factory/cli-client/internals/trigger"
)

type cmdUploadRelease struct {
	Track     string
	Risks     []string
	EndOfLife string
}

var releases = make([]cmdUploadRelease, 0)

func CliMain() {

	switch os.Args[1] {
	case "help":
		fmt.Println("Placeholder for help messages")

	case "upload":
		var opts struct {
			UploadReleases []string `long:"release" description:"Release images to container registries"`
		}

		args, err := flags.ParseArgs(&opts, os.Args[1:])
		if err != nil {
			logger.Panicf("Unable to parse --release arguments: %v", err)
		}

		if len(args) > 0 {
			fmt.Errorf("To many arguments given\n")
		}

		err = parseUploadReleases(opts.UploadReleases)
		if err != nil {
			fmt.Errorf("Failed to parse --release: %v", err)
			os.Exit(1)
		}

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
			blockForConfirm("Do you want to continue?", 2)
			externalRefID := payload.Inputs.ExternalRefID
			client.DispatchWorkflow(payload)
			client.WorkflowPolling(externalRefID)
		} else {
			fmt.Println("Nothing passed in --release, upload will be skipped.")
		}

	}
}

func parseUploadReleases(args []string) error {
	var release cmdUploadRelease
	for _, argStr := range args {
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

func blockForConfirm(s string, tries int) {
	r := bufio.NewReader(os.Stdin)

	for ; tries > 0; tries-- {
		fmt.Printf("%s [Y/n]: ", s)

		res, err := r.ReadString('\n')
		if err != nil {
			logger.Panicf("%v", err)
		}

		res = strings.TrimSpace(res)

		if res == "y" || res == "yes" || res == "" {
			return
		} else if res == "n" || res == "no" {
			fmt.Println("Cancelled")
			os.Exit(0)
		} else {
			continue
		}
	}

}
