#!/usr/bin/bash

FILES=$(find -name "*.md" | tr "\n" " ")

echo "Files = '${FILES}'";

SCRIPT_PATH=$(readlink -f $(dirname "${0}"))

echo "Script in ${SCRIPT_PATH}"

for file in ${FILES}; do
	dirname=$(dirname "${file}")
	filename=$(basename "${file}")
	echo "File: ${dirname} / ${filename}";

	# ${SCRIPT_PATH}/../node_modules/marked/bin/marked.js
	# sudo dnf install pandoc
	pandoc -o "${file}.docx" "${file}"
done

