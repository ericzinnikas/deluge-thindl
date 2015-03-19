# ThinDL Plugin
This plugin offers a convenient way for those using Deluge's [Thin Client](http://dev.deluge-torrent.org/wiki/UserGuide/ThinClient) to fetch torrents from their seedbox onto their local computer.


## Features
- Uses [LFTP](http://lftp.yar.ru/) to fetch files over SFTP (very fast, thanks to [segmented downloading](https://whatbox.ca/wiki/Multi-threaded_and_Segmented_FTP))
- Plugin auto-configures LFTP per torrent: host, user, remote directory, local directory
- LFTP run interactively in the background, your password never leaves memory; does not use `lftp -f` or `lftp -c` (FTP credentials never saved to disk, or visible in process listing `ps`)


## Screenshots
Access the plugin through the right-click context menu:

![Context Menu](/screenshots/thindl-menu.png?raw=true "Context Menu")

Confirm/Change settings:

![Download Dialog](/screenshots/thindl-dialog.png?raw=true "Download Dialog")

Progress window showing details:

![Progress Dialog](/screenshots/thindl-prog.png?raw=true "Progress Dialog")


## Dependencies
### Client Side
- Deluge (connected to seedbox)
- LFTP
- Linux (Windows support thru Cygwin/[native binary](http://nwgat.ninja/lftp-for-windows/) soon)

### Seedbox Side
- Deluged (obviously)
- FTP server


## Usage
Currently under heavy development and lacking formal testing, but the author has verified it works (at least on a basic level).  If you really want to use it (feedback appreciated):

```shell
git clone https://github.com/ericzinnikas/deluge-thindl.git
cd deluge-thindl
python2 setup.py bdist_egg
```
Install the egg file produced in `deluge-thindl/dist/`.  Ensure you build the proper python version (2.6 or 2.7) egg for your seedbox.  If seedbox and client python version differ, you'll need to manually install the proper egg on your seedbox.


## To Do
- [X] Options for number of simultaneous connections (pget stuff)
- [X] Options to resume downloads (-c option)
- [X] Fix Done button
- [X] Save/Load options to/from config
- [X] Catch edge cases when exiting dialogs (escape instead of button press)
- [ ] Average speed display in progress dialog
- [X] Differentiate files vs. directories (different LFTP options)
- [ ] Catch transfer error states

### Long Term
- [ ] Support for multiple LFTP sessions at once
- [ ] Autofind LFTP binary (not hardcoded)
- [ ] Windows/Linux interoperability (client side)
