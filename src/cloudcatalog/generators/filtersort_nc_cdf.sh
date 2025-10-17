#!/bin/bash
#!/bin/bash
# Usage: ./process_manifest.sh manifest_sep23.csv

# Check argument
if [ $# -ne 1 ]; then
  echo "Usage: $0 <input_filename>"
  exit 1
fi

input="$1"
base="${input%.*}"        # strip extension
ext="${input##*.}"        # get extension
output="${base}_sorted.${ext}"

# Run pipeline
sort "$input" | egrep "\.nc|\.cdf" > "$output"

echo "Created $output"
