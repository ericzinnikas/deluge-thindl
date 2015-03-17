#
# gtkui.py
#
# Copyright (C) 2009 Eric Zinnikas <hi@ericz.com>
#
# Basic plugin template created by:
# Copyright (C) 2008 Martijn Voncken <mvoncken@gmail.com>
# Copyright (C) 2007-2009 Andrew Resch <andrewresch@gmail.com>
# Copyright (C) 2009 Damien Churchill <damoxc@gmail.com>
#
# Deluge is free software.
#
# You may redistribute it and/or modify it under the terms of the
# GNU General Public License, as published by the Free Software
# Foundation; either version 3 of the License, or (at your option)
# any later version.
#
# deluge is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
# See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with deluge.    If not, write to:
# 	The Free Software Foundation, Inc.,
# 	51 Franklin Street, Fifth Floor
# 	Boston, MA  02110-1301, USA.
#
#    In addition, as a special exception, the copyright holders give
#    permission to link the code of portions of this program with the OpenSSL
#    library.
#    You must obey the GNU General Public License in all respects for all of
#    the code used other than OpenSSL. If you modify file(s) with this
#    exception, you may extend this exception to your version of the file(s),
#    but you are not obligated to do so. If you do not wish to do so, delete
#    this exception statement from your version. If you delete this exception
#    statement from all source files in the program, then also delete it here.
#

import gtk

from deluge.log import LOG as log
from deluge.ui.client import client
from deluge.plugins.pluginbase import GtkPluginBase
import deluge.component as component
import deluge.common

from common import get_resource

import os.path


class GtkUI(GtkPluginBase):
    def enable(self):
        self.glade = gtk.glade.XML(get_resource("config.glade"))

        component.get("Preferences").add_page("thindl", self.glade.get_widget("prefs_box"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)

        self.dl_dialog = None
        self.running = False
        self.load_interface()

    def on_get(self, data):
        torrent = component.get("TorrentView").get_torrent_status(self.t_id)
        ## ask to confirm torrent ??
        ## confirm host?
        #log.info("Connection Info: {}".format(client.connection_info()))
        conn = client.connection_info()
        host = conn[0]
        user = conn[2]
        ## if localhost, don't transfer
        #log.info("Localhost? {}".format(client.is_localhost()))
        ## ask to confirm path / folder [and size too]?
        ## TODO bug if they move completed path around manually...find better way to locate files on disk
        ## check torrent["progress"] != 100.0
        #log.info("Full Path: {}".format(os.path.join(data["move_on_completed_path"], torrent["name"])))
        path = os.path.join(data["move_on_completed_path"], torrent["name"])
        ## check torrent status / compltion

        self.download_dialog(path, host, user)
        ## open dialog box (like prefs or connection mgr window?) DONE
        ## show remote path (break on 2 lines, etc.) [show host] DONE
        ## show local path (browse button to change) TODO
        ## input for # of simultaneous transfers (5 default) TODO
        ## input for username / password (blocked out) [checkmark to remember maybe?? unsafe/only user] DONE
        ## Start button [launch lftp subprocess/pipe stuff] TODO
        ## then clear dialog box, place progress bar (how to get progress %? also get filesizes? transfer speed?) TODO
        ## cancel button / done button TODO

    def download_dialog(self, path, host, user):
        """popup dialog with data..."""

        self.builder = gtk.Builder()
        self.window = component.get("MainWindow")

        self.builder.add_from_file(get_resource("dialog.glade"))
        self.dl_dialog = self.builder.get_object("downloadDialog")
        self.dl_dialog.set_transient_for(self.window.window)

        self.builder.get_object("remoteData").set_label(path)
        self.builder.get_object("localData").set_label("/home/ericz/test/")
        self.builder.get_object("hostData").set_label(host)
        self.builder.get_object("userEntry").set_text(user)

        self.builder.get_object("yesButton").connect("clicked", self.on_yesButton)
        self.builder.get_object("noButton").connect("clicked", self.on_noButton)

        self.dl_dialog.show_all()

    def on_yesButton(self, data=None):
        log.info("USER: {}".format(self.builder.get_object("userEntry").get_text()))

        self.user = self.builder.get_object("userEntry").get_text()
        self.password = self.builder.get_object("passwordEntry").get_text()
        self.host = self.builder.get_object("hostData").get_text()
        self.local_path = self.builder.get_object("localData").get_text()
        self.remote_path = self.builder.get_object("remoteData").get_text()

        self.dl_dialog.destroy()
        del self.dl_dialog

    def on_noButton(self, data=None):
        self.dl_dialog.destroy()
        del self.dl_dialog

    def load_interface(self):
        log.info("loading interface !!!")

        mainmenu = component.get("MenuBar")
        torrentmenu = mainmenu.torrentmenu

        self.menu = gtk.MenuItem(_("Local Download"))
        self.menu.show()


        self.menu.connect("activate", self.on_menu_activate)

        mainmenu.add_torrentmenu_separator()
        torrentmenu.append(self.menu)

    def get_t_ids(self):
        """
        returns selected torrents
        """
        return component.get("TorrentView").get_selected_torrent()

    def on_menu_activate(self, data=None):
        self.t_id = self.get_t_ids()  # just one for now...
        #for t_id in get_t_ids():
            ## got name and state (check completed/seeding whatever)
            #torrent = component.get("TorrentManager")[t_id]

            ## TODO get config data for completed location (remote/server) DONE
            ## TODO get our config data for download location (local/client)
            ## TODO get config data for server IP DONE

            # regardless of 'move_on_completed' or not, path is always where it will be
        t_data = component.get("SessionProxy").get_torrent_status(self.t_id,
            ["move_on_completed_path"]).addCallback(self.on_get)

    def disable(self):
        torrentmenu = component.get("MenuBar").torrentmenu
        torrentmenu.remove(self.menu)

        ## TODO eventually check if download in-progress

        component.get("Preferences").remove_page("thindl")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)

    def on_apply_prefs(self):
        log.debug("applying prefs for thindl")
        config = {
            "test":self.glade.get_widget("txt_test").get_text()
        }
        client.thindl.set_config(config)

    def on_show_prefs(self):
        client.thindl.get_config().addCallback(self.cb_get_config)

    def cb_get_config(self, config):
        "callback for on show_prefs"
        self.glade.get_widget("txt_test").set_text(config["test"])
