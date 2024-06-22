hello:
	echo "Hello, World"

send:
	rsync --exclude="venv" --exclude=".mypy_cache" -rtvzP . pi@"$$(< .ip_development)":~/SpectroSphere --exclude='*.img'

ssh:
	ssh -t pi@"$$(< .ip_development)" "cd ~/SpectroSpehere; bash"

ssh-data:
	ssh -t pi@"$$(< .ip_development)" "cd ~/Data; bash"

ssh-abduco:
	ssh -t pi@"$$(< .ip_development)" "abduco -a my-session"

ssh-kill-bashes:
	ssh pi@"$$(< .ip_development)" "pidof bash | xargs kill"

ssh-kill-pyhton3:
	ssh pi@"$$(< .ip_development)" "pidof python3 | xargs kill"

scp-rm:
	scp -r pi@"$$(< .ip_development)":Data/ /tmp/
	ssh pi@"$$(< .ip_development)" "rm -rfv ~/Data;"

run:
	ssh pi@"$$(< .ip_development)" -t python3 /home/pi/SpectroSpehere/py_tab1_handheld.py

reboot:
	ssh pi@"$$(< .ip_development)" -t sudo reboot

ip_search:
	/home/garid/Documents/learning_shell/piip_scan.sh

ip_set:
	bash -c 'read -p "Set development devices IP address: " username; echo $$username > .ip_development'

ip_get:
	echo "current IP set is:" "$$(< .ip_development)";

