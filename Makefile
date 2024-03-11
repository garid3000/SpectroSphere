send:
	rsync -rtvzP . pi@"$$(< .ip_development)":~/SpecSphere --exclude='venv/*'

ssh:
	ssh -t pi@"$$(< .ip_development)" "cd ~/Spectrum-Catcher-V3; bash"

run: 
	ssh pi@"$$(< .ip_development)" -t python3 /home/pi/Spectrum-Catcher-V3/py_tab1_handheld.py

reboot: 
	ssh pi@"$$(< .ip_development)" -t sudo reboot

ip_search:
	/home/garid/Documents/learning_shell/piip_scan.sh

ip_set:
	bash -c 'read -p "Set development devices IP address: " username; echo $$username > .ip_development'

ip_get:
	echo "current IP set is:" "$$(< .ip_development)";

