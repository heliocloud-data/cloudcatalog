# first split manifest into pieces
#!/bin/sh

infile="$1"

if [ -z "$infile" ] || [ ! -f "$infile" ]; then
  echo "Usage: $0 <input_file>" >&2
  exit 1
fi

# filters into [file]_sorted.[ext]
case "$infile" in
  *.*)
    base="${infile%.*}"
    ext="${infile##*.}"
    ;;
  *)
    base="$infile"
    ext=""
    ;;
esac

output="${base}_sorted.${ext}"
if [ ! -f "$output" ]; then
    echo "Filtering ${infile}"
    grep -E '\.(nc|cdf|fits|fts)' "$infile" | sort > "$output"
fi

# Define output files
sdac="${base}_sdac.${ext}"
spdf="${base}_spdf.${ext}"
contrib="${base}_contrib.${ext}"
other="${base}_other.${ext}"

if ! [ -f "$sdac" ]; then
    echo "Extracting sdac"
    grep "^sdac/" $output > $sdac
fi
if ! [ -f "$spdf" ]; then
    echo "Extracting spdf"
    grep "^spdf/" $output > $spdf
fi
if ! [ -f "$contrib" ]; then
    echo "Extracting contrib"
    grep "^contrib/" $output > $contrib
fi
if ! [ -f "$other" ]; then
    echo "Extracting other"
    grep -v -E "^sdac/|^spdf/|^contrib/" $output > $other
fi

# now generate new indices and an 'updates.csv' to update catalog.json with
echo "Generating"

if [ -f "$sdac" ]; then
    cloudcatalog-manifest2indices "$sdac" s3://gov-nasa-hdrl-data1/ --quiet
    echo "Processed SDAC"
    mv errors.lst errors_sdac.lst
    mv ignore.lst ignore_sdac.lst
    mv newids.csv newids_sdac.csv
    mv updates.csv updates_sdac.csv
fi

if [ -f "$spdf" ]; then
    cloudcatalog-manifest2indices "$spdf" s3://gov-nasa-hdrl-data1/ --ensure_prefix spdf/cdaweb/data --metadata_file all.xml --strip_me pub/data --quiet
    echo "Processed SPDF"
    mv errors.lst errors_spdf.lst
    mv ignore.lst ignore_spdf.lst
    mv newids.csv newids_spdf.csv
    mv updates.csv updates_spdf.csv
fi

if [ -f "$contrib" ]; then
    cloudcatalog-manifest2indices "$contrib" s3://gov-nasa-hdrl-data1/ --quiet
    echo "Processed contrib"
    mv errors.lst errors_contrib.lst
    mv ignore.lst ignore_contrib.lst
    mv newids.csv newids_contrib.csv
    mv updates.csv updates_contrib.csv
fi

if [ -f "$other" ]; then
    cloudcatalog-manifest2indices "$other" s3://gov-nasa-hdrl-data1/ --quiet
    echo "Processed 'other'"
    mv errors.lst errors_other.lst
    mv ignore.lst ignore_other.lst
    mv newids.csv newids_other.csv
    mv updates.csv updates_other.csv
fi
