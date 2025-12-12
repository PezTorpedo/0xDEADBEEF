### Connect the serial wires
Pin 1 = GND
Pin 4 = RX In (connect to TX Out of your serial cable)
Pin 5 = TX Out (connect to RX in of your serial cable).

### Connect to minicom 
minicom -b 115200 -o -D /dev/ttyAMA0

''With logs''
minicom -b 115200 -o -D /dev/ttyAMA0 -C minicom.log

Turn the Hue, and if first time then short and add 'setenv bootdelay 3' and 'saveenv'

Then boot again and stop the boot this way, and add setenv 'std_bootargs 'board=BSB002 console=ttyS0,115200 ubi.mtd=overlay rootfs=/dev/mtdblock:rootfs rootfstype=squashfs noinitrd init=/bin/sh''

Then boot again and in new terminal add:


```
mount -t ubifs ubi1_1 /overlay
mkdir /overlay/upper/bin
# Let's make ourselves a proper login shell in fully booted system
cat - >/overlay/upper/bin/secure-console.sh <<'EOF'
#!/bin/sh
exec /bin/ash --login
EOF
chmod a+x /overlay/upper/bin/secure-console.sh
umount /overlay/
```

and 

```exec /sbin/init```

''Add ssh key''

```ssh-factory-key -r -
ssh-rsa AAAAB3N........................== key
registered: key
installed: firewall rule for ssh
```

And restore everything to the orginal env

```
cd /overlay/upper/
rm bin/secure-console.sh
rmdir bin
# unfortunately this screws up all of /bin (until reboot)
# thus... make it so:
reboot
```


### Connect to the philips HUE
ssh -i ~/.ssh/my_rsa_key -o 'PubkeyAcceptedAlgorithms +ssh-rsa' -o 'HostkeyAlgorithms +ssh-rsa' root@192.168.10.10
