#!/bin/bash

if [ ! -d "$2" ]; then
	echo "Delete .uaem files created by fs-uae"
	echo "Usage: $0 [-u | -a] /path/to/harddrive_dir [-m]"
	echo "Options:"
	echo "-u   delete (possibly) unwanted .uaem files"
	echo "-a   delete all .uaem files"
	echo "-m   also change atime and mtime of host filesystem's files (not a good idea!)"
	exit 0
fi

HDD="$2"
FILELIST=$(mktemp)

if [ "$1" == "-a" ]; then
	find "$HDD" -type f -name "*.uaem" > "$FILELIST"
elif [ "$1" == "-u" ]; then
	find "$HDD" -type f -size 33c -name "*.uaem" -print0 | \
		xargs -0 grep -lEe "^----rw[e-]d" > "$FILELIST"
else
	echo "Bad option: $1"
	rm "$FILELIST"
	exit 1
fi

if [ ! -s "$FILELIST" ]; then
	echo "No files to delete."
	rm "$FILELIST"
	exit 0
fi


COUNT=0
while read UAEMFILE; do
	if [ "$3" == "-m" ]; then
		REALFILE="${UAEMFILE%*.uaem}"
		MTIME=$(cat "$UAEMFILE" |  cut -c10-31)
		echo "Mod: $REALFILE --> $MTIME"
		touch -d "$MTIME" "$REALFILE"
	fi
	echo "Del: $UAEMFILE"
	#echo -n "Del: $UAEMFILE   "; cat "$UAEMFILE"
	rm "$UAEMFILE"
	((COUNT++))
done < "$FILELIST"

rm "$FILELIST"

echo -e "\nDeleted $COUNT files, saved $(($COUNT*33))Bytes, $(($COUNT*4))kb @ 4k blocksize, $(($COUNT*32))kb @ 32k blocksize."
