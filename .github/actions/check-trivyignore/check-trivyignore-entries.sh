#!/usr/bin/env bash

if [ $# -ne 2 ]; then
    echo "Usage: $0 <scan-result> <trivyignores>"
    exit 1
fi

scan_result=$1
trivyignores=$2

temp_dir=$(mktemp -d)

output=$(jq -r '.scanner.result.Results[]| .Vulnerabilities | try to_entries[] | .value.VulnerabilityID' \
        <"$scan_result" 2>"${temp_dir}/errors.txt" || true)
if [ -s "${temp_dir}/errors.txt" ]; then
    echo "Unable to parse scan result."
    exit 1
fi
line=0
while read -r CVE;
do
    line=$(( line + 1 ))
    if [[ "$output" != *"$CVE"* && ! "$CVE" =~ ^#.* ]]
    then
    echo "::notice file=$trivyignores,line=${line}::$CVE not present anymore, can be safely removed."
    fi
done < "$trivyignores"
