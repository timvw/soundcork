# soundcork
Intercept API for Bose SoundTouch after they turn off the servers

## Status

This project is pre-alpha. We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for more information, and the project [milestones](https://github.com/deborahgu/soundcork/milestones?sort=title&direction=asc) for our goals.

## Background
[Bose has announced that they are shutting down the servers for the SoundTouch system in February, 2026. ](https://www.bose.com/soundtouch-end-of-life) When those servers go away, certain network-based functionality currently available to SoundTouch devices will stop working.

This is an attempt to reverse-engineer those servers so that users can continue to use the full set of SoundTouch functionality after Bose shuts the official servers down.

### Context

[As described here](https://flarn2006.blogspot.com/2014/09/hacking-bose-soundtouch-and-its-linux.html), it is possible to access the underlying server by creating a USB stick with an empty file called **remote_services** and then booting the SoundTouch with the USB stick plugged in to the USB port in the back. From there we can then telnet (or ssh, but the ssh server running is fairly old) over and log in as root (no password).

### Pointing the Bose Speaker to a Local Server

Once logged into the speaker, you can go to `/opt/Bose/etc` and look at the file `SoundTouchSdkPrivateCfg.xml`:

	<?xml version="1.0" encoding="utf-8"?>
	<SoundTouchSdkPrivateCfg>
	  <margeServerUrl>https://streaming.bose.com</margeServerUrl>
	  <statsServerUrl>https://events.api.bosecm.com</statsServerUrl>
	  <swUpdateUrl>https://worldwide.bose.com/updates/soundtouch</swUpdateUrl>
	  <usePandoraProductionServer>true</usePandoraProductionServer>
	  <isZeroconfEnabled>true</isZeroconfEnabled>
	  <saveMargeCustomerReport>false</saveMargeCustomerReport>
	  <bmxRegistryUrl>https://content.api.bose.io/bmx/registry/v1/services</bmxRegistryUrl>
	</SoundTouchSdkPrivateCfg>

Assumingly all four servers listed there will be shut down. From testing, the `marge` server is necessary for basic network functionality, and the `bmx` server seems to be required for TuneIn radio.

To point your system to another server, simple enter into read-write mode, edit the file (vi is available) and replace the URLs with your local URLs, and then reboot

	root@spotty:etc# rw                            
	root@spotty:etc# vi SoundTouchSdkPrivateCfg.xml
	root@spotty:etc# reboot

## Running, testing, and installing

### Installing

This has been written and tested with Python 3.12. Eventually it will be bundled as an installable app but for now you'll want a virtual environment.


1. You can use `venv`, `virtualenvwrapper`, or any other tool that lets you
manage virtual environments. These docs assume `venv`.
	- Unix, Windows, and MaxOS [installation and use guide for venv](https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/).
	- Your operating system might have some prerequisites here. On ubuntu, you may need:
		```sh
		sudo apt-install python3-pip python3.12-venv
		```
1. Set up the virtual environment and run it. Run these commands in the
directory where you've cloned the repository. (Adapt as needed for your shell
or OS.)

	```sh
	mkdir .venv
	python3.12 -m venv .venv
	source .venv/bin/activate
	```
1. Install the pre-requisites
	```bash
	pip install requirements.txt
	```

When you're done with the virtual environment, you can type `deactivate` to leave that shell.

### Running

- To run in test
	```sh
	fastapi dev main.py
	# server is on http://127.0.0.1:8000
	```
- To run a prod server
	```sh
	fastapi run main.py
	```
- To run as a daemon
    - install the package in your virtualenv
		```sh
		pip install build && \
		python -m build && \
		pip install dist/*.whl
		``` 
    - If using systemd, make a copy of `soundcork.service.example`, named `soundcork.service`
	- modify the placeholder strings appropriately
	- then mv to systemd and enable.
		```sh
		sudo mv soundcork.service /etc/systemd/system && \
		sudo systemctl daemon-reload && \
		sudo systemctl enable soundcork && \
		sudo systemctl start soundcork
		```

You can verify the server by checking the `/docs` endpoint at your URL.