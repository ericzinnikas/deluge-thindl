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
import os
from os import O_NONBLOCK
from subprocess import Popen, PIPE, STDOUT
from fcntl import fcntl, F_GETFL, F_SETFL
from time import sleep


class GtkUI(GtkPluginBase):
    def enable(self):
        self.glade = gtk.glade.XML(get_resource("config.glade"))

        component.get("Preferences").add_page("thindl", self.glade.get_widget("prefs_box"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)

        self.proc = None
        self.local_folder = None
        self.remote_size = None
        self.textview = None
        self.dl_dialog = None
        self.running = False
        self.load_interface()

    def on_get(self, data):
        torrent = component.get("TorrentView").get_torrent_status(self.t_id)
        conn = client.connection_info()
        host = conn[0]
        user = conn[2]
        ## TODO if localhost, don't transfer
        ## TODO check torrent["progress"] != 100.0

        if data["move_on_completed"]:
            path = data["move_on_completed_path"]
        else:
            path = data["save_path"]
        
        log.info("Path is: {}".format(path))
        self.download_dialog(path, torrent["name"], host, user)

    def download_dialog(self, path, name, host, user):
        """popup dialog with data..."""

        self.dl_builder = gtk.Builder()
        self.window = component.get("MainWindow")

        self.remote_name = name
        self.remote_path = os.path.join(path, name)
        self.host = host

        self.dl_builder.add_from_file(get_resource("dialog.glade"))
        self.dl_dialog = self.dl_builder.get_object("downloadDialog")
        self.dl_dialog.set_transient_for(self.window.window)

        self.dl_builder.get_object("nameData").set_label(name)
        self.dl_builder.get_object("remoteData").set_label(path)

        ## TODO load from config
        self.dl_builder.get_object("localData").set_filename("/home/ericz/test/")
        self.dl_builder.get_object("hostData").set_label(host)
        self.dl_builder.get_object("userEntry").set_text(user)

        self.dl_builder.get_object("yesButton").connect("clicked", self.on_yesButton)
        self.dl_builder.get_object("noButton").connect("clicked", self.on_noButton)

        self.dl_dialog.show_all()

    def cb_get_rsize(self, size):
        log.info("GOT RSIZE: {}".format(size))
        self.remote_size = size

    def open_progress(self):
        self.pr_builder = gtk.Builder()
        self.window = component.get("MainWindow")

        self.pr_builder.add_from_file(get_resource("progress.glade"))
        self.prog_dialog = self.pr_builder.get_object("progressDialog")

        ## TODO !!! catch if user hits escape (doesn't click, still need to kill transfer, maybe make this a window)
        self.pr_builder.get_object("cancelButton").connect("clicked", self.on_cancelButton)
        self.pr_builder.get_object("doneButton").connect("clicked", self.on_doneButton)

        ## NOTE use fsize in common and fpcnt and fspeed

        self.prog_dialog.show_all()
        ## NOTE progress updates happen in update() loop [every 1s]

    def on_doneButton(self, data=None):
        ## TODO add catch for kill (i.e. process died, but still hit stop/done) maybe just check poll
        self.transfer.terminate()
        sleep(0.10)
        # .poll() cleans defunct, b/c we don't care anymore?
        if self.transfer.poll() is None:
            self.transfer.kill()
        sleep(0.10)
        if self.transfer.poll() is None:
            pass  # uhhh....
        self.prog_dialog.destroy()
        del self.prog_dialog

    def on_cancelButton(self, data=None):
        # except OSError
        self.transfer.terminate()
        sleep(0.1)  # TODO do we need this?
        # .poll() cleans defunct, b/c we don't care anymore?
        if self.transfer.poll() is None:
            self.transfer.kill()
        sleep(0.1)
        if self.transfer.poll() is None:
            pass  # uhhh....
        self.prog_dialog.destroy()
        del self.prog_dialog

    def on_yesButton(self, data=None):
        log.info("USER: {}".format(self.dl_builder.get_object("userEntry").get_text()))

        self.user = self.dl_builder.get_object("userEntry").get_text()
        self.password = self.dl_builder.get_object("passwordEntry").get_text()
        #self.host = self.builder.get_object("hostData").get_text()
        self.local_folder = self.dl_builder.get_object("localData").get_filename()
        ## change if we are grabbing file or directory TODO
        self.local_folder = os.path.join(self.local_folder, self.remote_name)
        if not os.path.exists(self.local_folder):
            ## NOTE technically possible to get race condition...not probable though
            os.makedirs(self.local_folder)

        client.thindl.get_size(self.remote_path).addCallback(self.cb_get_rsize)

        log.info("Starting test transfer...")
        if self.test_transfer():
            log.info("Starting real transfer...")
            self.start_transfer()  # TODO actually pass args
            log.info("Showing progress...")
            self.open_progress()
            ## TODO catch transfer error when updating...
            ## then see if program still running (though we need to wait for time to connect...? how when it hangs?
            ## TODO figure out failure state: i.e. process has stopped, but filesizes not matched
        else:
            ## TODO connection error
            ## present dialog about wrong user/password or network issues
            pass

        self.dl_dialog.destroy()
        del self.dl_dialog

    def test_transfer(self):
        self.test_transfer = Popen(["/usr/bin/lftp", "sftp://{}".format(self.host)], stdin=PIPE, stdout=PIPE, stderr=PIPE)
        out = self.test_transfer.communicate(
                "user {} {} && ((ls && echo THINDLSUCCESS && exit) || (echo THINDLFAILURE && exit))".format(
                self.user, self.password))
        if self.test_transfer.poll() is None:
            self.test_transfer.terminate()

        if self.test_transfer.poll() is None:
            self.test_transfer.kill()

        return "THINDLSUCCESS" in out[0]

    def start_transfer(self):  #, host, user, password, remote_path, local_folder):
        ## TODO actually pass args (not prog state)...gets icky
        ## TODO add in variables for connections per file
        ## TODO config for location of LFTP binary (autofind initially)
        ## TODO choose method sftp, etc...?

        self.transfer = Popen(["/usr/bin/lftp", "sftp://{}".format(self.host)], stdin=PIPE, stdout=PIPE, stderr=PIPE)

        ## NOTE this doesn't block
        ## TODO determine file vs folder (get vs mirror)
        log.info("Transferring {} to {}".format(self.remote_path, self.local_folder))
        self.transfer.stdin.write("user {} {} && (mirror {} {} || exit) && exit\n".format(
            self.user, self.password, self.remote_path, self.local_folder))
        #self.transfer.stdin.write("user {} {} && (get -O {} {} || exit) && exit\n".format(
            #self.user, self.password, self.local_folder, self.remote_path))

    def update(self):
        ## NOTE use fsize in common and fpcnt and fspeed (and get_path_size)
        ## TODO maybe avg. speed local growing

        if self.local_folder is not None and self.remote_size is not None:
            local_size = deluge.common.get_path_size(self.local_folder)

            if local_size <= 0:
                local_size = 0.0
            else:
                local_size = float(local_size)

            str = "{} / {}".format(deluge.common.fsize(local_size),
                    deluge.common.fsize(self.remote_size))
            self.pr_builder.get_object("progData").set_label(str)
            self.pr_builder.get_object("progBar").set_fraction( local_size / self.remote_size )
            log.info("Set percent to: {}".format(local_size / self.remote_size))
            ## TODO when cancel, stop looping this part

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
        ## TODO testing for save_path...is it accurate?
        t_data = component.get("SessionProxy").get_torrent_status(self.t_id,
            ["move_on_completed","move_on_completed_path","save_path"]).addCallback(self.on_get)

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
