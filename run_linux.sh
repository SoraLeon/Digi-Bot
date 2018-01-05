#!/bin/bash
until python3 monkeyslave.py; do
	echo "Monkey Slave crashed... Restarting" >&2
	sleep 3
done