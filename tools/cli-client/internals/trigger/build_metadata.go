package trigger

import (
	"fmt"
	"os"
	"os/exec"
	"regexp"
	"strings"

	"github.com/canonical/oci-factory/tools/cli-client/internals/logger"
	git "github.com/go-git/go-git/v5"
	"gopkg.in/yaml.v3"
)

type BuildMetadata struct {
	Source                 string
	Commit                 string
	Directory              string
	IgnoredVulnerabilities []string
}

func InferBuildMetadata() BuildMetadata {
	_, err := os.Stat("rockcraft.yaml")
	if os.IsNotExist(err) {
		fmt.Fprintln(os.Stderr, "No rockcraft.yaml found in current working directory")
		os.Exit(1)
	} else if err != nil {
		logger.Panicf("OS error: %v", err)
	}
	repo, err := git.PlainOpenWithOptions(".",
		&git.PlainOpenOptions{DetectDotGit: true, EnableDotGitCommonDir: false})
	if err != nil {
		fmt.Fprintf(os.Stderr, "Unable to open repository: %v\n", err)
		os.Exit(1)
	}

	// find the source URL
	remotes, err := repo.Remotes()
	if err != nil {
		fmt.Fprintf(os.Stderr, "Unable to obtain remotes: %v\n", err)
		os.Exit(1)
	}
	if len(remotes) < 1 || len(remotes[0].Config().URLs) < 1 {
		fmt.Fprintf(os.Stderr, "No valid remote exists for this repo\n")
		os.Exit(1)
	}
	remoteURL := remotes[0].Config().URLs[0]
	logger.Debugf("Remote URL: %s", remoteURL)

	// use regex to match the repo location
	regex := regexp.MustCompile(`github.com[:\/](canonical\/[A-Za-z0-9_-]*)(\.git)?`)
	matches := regex.FindStringSubmatch(remoteURL)
	if len(matches) < 3 {
		fmt.Fprintf(os.Stderr, "oci-factory must be called in a git local repository belonging to the organization [canonical]\n")
		os.Exit(1)
	}
	source := matches[1]
	logger.Debugf("Source: %s", source)

	headSha256, err := repo.ResolveRevision("HEAD")
	if err != nil {
		fmt.Fprintf(os.Stderr, "Unable to resolve HEAD: %v\n", err)
		os.Exit(1)
	}
	logger.Debugf("HEAD SHA-256: %s", headSha256)

	// find the directory using git rev-parse
	// have to use a subprocess since go-git
	// does not support git rev-parse yet
	prefixBytes, err := exec.Command("git", "rev-parse", "--show-prefix").Output()
	if err != nil {
		logger.Panicf("Subprocess `git rev-parse --show-prefix` failed: %v", err)
	}
	// remote the trailing newline
	// also prepend a "./" to cope with empty prefixes
	prefix := "./" + strings.TrimSpace(string(prefixBytes))
	logger.Debugf("Directory: %s", prefix)

	buildMetadata := BuildMetadata{
		Source:    source,
		Commit:    headSha256.String(),
		Directory: prefix,
	}

	return buildMetadata
}

func GetRockcraftImageName() string {
	yamlFile, err := os.ReadFile("rockcraft.yaml")
	if err != nil {
		fmt.Fprint(os.Stderr, "Unable to read rockcraft.yaml in current working directory\n")
		os.Exit(1)
	}
	y := struct {
		Name string `yaml:"name"`
	}{}
	err = yaml.Unmarshal(yamlFile, &y)
	if err != nil {
		logger.Panicf("Unable to marshal trigger: %s", err)
	}

	logger.Debugf("Image name: %s", y.Name)
	return y.Name
}
