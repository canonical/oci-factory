package cli

import (
	"fmt"
	"time"
)

func ValidateAndFormatDate(dateStr string) (string, error) {
	// Parse the date string to check its validity
	parsedDate, err := time.Parse("2006-01-02", dateStr)
	if err != nil {
		return "", fmt.Errorf("invalid date format: %w", err)
	}

	// Add the time component to be 00:00:00Z
	formattedDate := parsedDate.Format("2006-01-02T15:04:05Z")
	return formattedDate, nil
}
