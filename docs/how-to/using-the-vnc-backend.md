# Using The VNC Backend

Using the VNC backend means that at the point you begin to run `yarf`, you will need to have a VM running with a VNC server.

You can do this with QEMU/MIR and other backends.

## Appropriate QEMU Args

To spawn a QEMU VM with an appropriate VNC server, you can use something along the lines of the following command (this example is for an Ubuntu Desktop live ISO):

```
qemu-img create -f qcow2 /tmp/yarf-vm.qcow2 20G

qemu-system-x86_64 -boot d -cdrom /path/to/$series-desktop-amd64.iso -m 8192M -smp 2 -hda /tmp/yarf-vm.qcow2 -enable-kvm -device qxl -vnc :0
```

If you want to allow multiple VNC clients (i.e. if you want to use a VNC viewer), you can replace `-vnc :0` with `-vnc :0,share=ignore`.

If you want to spin up a VM and instantly open the SDL display, you can replace `-vnc :0` with `-vnc :0 -display sdl`.

## Using An Existing VM With A VNC Server With Yarf

You can then connect to the running VM with `yarf` like so:

```
VNC_PORT=0 VNC_HOST=localhost yarf --platform=Vnc
```

If your VM is running on a remote machine, not your localhost, you can use the following:

```
VNC_PORT=1 VNC_HOST=$host yarf --platform=Vnc
```
