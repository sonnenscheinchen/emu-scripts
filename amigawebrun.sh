#!/bin/bash

#requirements:
#fs-uae
#amiga (fs-uae command-line launcher)
#firefox + OpenWith extension
#dmenu

urldecode(){
  echo -e "$(sed 's/+/ /g; s/%/\\x/g')"
}

if [ -z $1 ]; then
	echo "Usage: amigawebrun <URL of disk image>"
	exit
fi

URL=$1
test -d /tmp/amigawebrun || mkdir /tmp/amigawebrun
cd /tmp/amigawebrun
wget -nc "$URL" --restrict-file-names=nocontrol &
PID=$!

OPTS=$(echo -e "\
-att -0\n\
-bxtt -0\n\
-R wbhd -5\n\
-cxR wbhd -5\
" | dmenu -fn 10x20 -p "options:" -b -l 20)

RET=$?
test $RET || exit 0
FILE=${URL##*/}
DECFILE=$(echo $FILE | urldecode)
wait $PID
killall fs-uae
~/bin/amiga $OPTS "$DECFILE"

