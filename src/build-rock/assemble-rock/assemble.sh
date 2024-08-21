#! /bin/bash

set -e


function usage(){
    echo
    echo "$(basename "$0") -d <rock directory> -n <archive name>"
    echo
    echo "Merge multiple OCI Rock images into one multi arch image."
    echo
    echo -e "-d \\t Directory to search for rock OCI images in."
    echo -e "-n \\t Final output archive name. "
}

while getopts "d:n:" opt
do
    case $opt in
        d)
            ROCK_DIR="$OPTARG"
            ;;
        n)
            ARCHIVE_NAME="$OPTARG"
            ;;
        ?)
            usage
            exit 1
            ;;
    esac
done

if [ -z "$ROCK_DIR" ]
then
    echo "Error: Missing rock search directory argument (-d)"
    usage
    exit 1
fi

if [ -z "$ARCHIVE_NAME" ]
then
    echo "Error: Missing final archive name (-n)"
    usage
    exit 1
fi

buildah manifest create multi-arch-rock

for rock in `find "$ROCK_DIR" -name "*.rock" -type f`
do
    buildah manifest add multi-arch-rock oci-archive:$rock
done

buildah manifest push --all multi-arch-rock "oci-archive:$ARCHIVE_NAME"

