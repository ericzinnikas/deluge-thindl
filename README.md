# ThinDL Plugin
This plugin offers a convenient way for those using Deluge's [Thin Client](http://dev.deluge-torrent.org/wiki/UserGuide/ThinClient) feature to fetch remotely downloaded torrents onto their local machine.


## Usage
Currently under development and lacking any testing, but the author has verified it works (at least on a basic level).  Many more improvements are needed before advocating it to the world.  If you really want to use it, clone this repo then build the plugin yourself with `python setup.py bdist_egg`.


## Features
- Uses [LFTP](http://lftp.yar.ru/) to fetch files over SFTP
- Plugin auto-configures LFTP per torrent: host, user, remote directory, local directory (pget options coming soon)


## Screenshots
Here are some examples of functionality, excuse the UI...hopefully that will improve over time.

First you can access the plugin through the context menu on a per-torrent basis:

![Context Menu](/screenshots/thindl-menu.png?raw=true "Context Menu")

The next dialog shows selected options (more configuration will be available in the future):

![Download Dialog](/screenshots/thindl-dialog.png?raw=true "Download Dialog")

Finally, you've got a progress window showing completion of the download and an option to cancel it:

![Progress Dialog](/screenshots/thindl-prog.png?raw=true "Progress Dialog")


## Dependencies
### Client Side
- Deluge (connected to seedbox)
- LFTP
- Linux (Windows support thru Cygwin/[native binary](http://nwgat.ninja/lftp-for-windows/) soon)

### Seedbox Side
- Deluged (obviously)
- FTP server


## To Do
- [ ] Options for number of simultaneous connections (pget stuff)
- [X] Fix Done button
- [ ] Save/Load options to/from config
- [ ] Catch edge cases when exiting dialogs (escape instead of button press)
- [ ] Differentiate files vs. directories (different LFTP options)
- [ ] Catch transfer error states
- [ ] Support for multiple LFTP sessions at once
- [ ] Autofind LFTP binary (not hardcoded)
- [ ] Average speed display in progress dialog
