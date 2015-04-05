#
# gtkui.py
#
# Copyright (C) 2015 Eric Zinnikas <hi@ericz.com>
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
from subprocess import Popen, PIPE, STDOUT
from time import sleep, time


class GtkUI(GtkPluginBase):
    #def __init__(self, plugin_name):
        #self.running = False

    def enable(self):
        self.transfer_stopped = False
        self.running = False
        self.speed = 0.0
        self.time_bytes = 0
        self.local_size = 0
        self.local_size_prev = 0
        self.glade = gtk.glade.XML(get_resource("config.glade"))

        self.config = None
        client.thindl.get_config().addCallback(self.cb_init_config)

        component.get("Preferences").add_page("thindl", self.glade.get_widget("prefs_box"))
        component.get("PluginManager").register_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").register_hook("on_show_prefs", self.on_show_prefs)

        self.isWindows = deluge.common.windows_check()

        self.proc = None
        self.local_folder = None
        self.remote_size = None
        self.remote_isFolder = None
        self.textview = None
        self.dl_dialog = None
        self.load_interface()
        self.transfer = None

    def on_get(self, data):
        torrent = component.get("TorrentView").get_torrent_status(self.t_id)
        conn = client.connection_info()
        host = conn[0]
        user = conn[2]
        if host == "127.0.0.1":
            msg = gtk.MessageDialog(parent=None, flags=gtk.DIALOG_MODAL,
                                    type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK,
                                    message_format="Cannot transfer file from localhost!")
            msg.run()
            msg.destroy()
            return False

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

        self.dl_builder.get_object("localData").set_filename(self.config["local_folder"])
        self.dl_builder.get_object("hostData").set_label(host)
        self.dl_builder.get_object("userEntry").set_text(user)

        self.dl_builder.get_object("connData").set_value(self.config["lftp_pget"])
        self.dl_builder.get_object("continueToggle").set_active(True)

        self.dl_builder.get_object("yesButton").connect("clicked", self.on_yesButton)
        self.dl_builder.get_object("noButton").connect("clicked", self.on_noButton)
        self.dl_builder.get_object("downloadDialog").connect("close", self.on_noButton)

        ## pre-fetch because it breaks things later...
        client.thindl.get_size(self.remote_path).addCallback(self.cb_get_rsize)

        self.dl_dialog.show_all()

    def cb_get_rsize(self, data):
        size = data[0]
        isFolder = data[1]
        log.info("Folder is: {}".format(isFolder))
        self.remote_size = size
        self.remote_isFolder = isFolder

    def open_progress(self):
        self.pr_builder = gtk.Builder()
        self.window = component.get("MainWindow")

        self.pr_builder.add_from_file(get_resource("progress.glade"))
        self.prog_dialog = self.pr_builder.get_object("progressDialog")

        self.pr_builder.get_object("progressDialog").connect("delete-event", self.on_progDelete)
        self.pr_builder.get_object("cancelButton").connect("clicked", self.on_cancelButton)
        self.pr_builder.get_object("doneButton").connect("clicked", self.on_doneButton)

        self.prog_dialog.show_all()
        ## NOTE progress updates happen in update() loop [every 1s]

    def on_progDelete(self, widget=None, *data):
        msg_dialog = gtk.MessageDialog(parent=None, flags=gtk.DIALOG_MODAL,
                                       type=gtk.MESSAGE_QUESTION, buttons=gtk.BUTTONS_OK_CANCEL,
                                       message_format="Press 'Ok' to stop the transfer.")

        res = msg_dialog.run()
        msg_dialog.destroy()
        if res == gtk.RESPONSE_CANCEL:
            return True  # True --> no, don't close

        self.stop_transfer()
        return False

    def stop_transfer(self):
        ## if ^ returns True, set self.running == False
        if self.transfer is not None:
            try:
                self.transfer.terminate()
            except OSError:  ## no such process
                return True
            sleep(0.10)

            if self.transfer.poll() is None:
                try:
                    self.transfer.kill()
                except OSError:  ## process already dead
                    return True
            sleep(0.10)

            if self.transfer.poll() is None:
                return False  # uhhh....
        return True

    def on_doneButton(self, data=None):
        self.stop_transfer()

        self.prog_dialog.destroy()
        del self.prog_dialog

    def on_cancelButton(self, data=None):
        self.transfer_stopped = True
        self.stop_transfer()

        self.prog_dialog.destroy()
        del self.prog_dialog

    def on_yesButton(self, data=None):
        self.user = self.dl_builder.get_object("userEntry").get_text()
        self.password = self.dl_builder.get_object("passwordEntry").get_text()
        self.resume = self.dl_builder.get_object("continueToggle").get_active()
        self.pget = self.dl_builder.get_object("connData").get_value()
        #self.host = self.builder.get_object("hostData").get_text()
        self.local_folder = self.dl_builder.get_object("localData").get_filename()
        self.local_folder = os.path.join(self.local_folder, self.remote_name)
        if not os.path.exists(self.local_folder):
            ## NOTE technically possible to get race condition...not probable though
            os.makedirs(self.local_folder)

        if self.isWindows:
            cygpath = Popen(["cygpath.exe", "-u", self.local_folder],
                    stdin=PIPE, stdout=PIPE, stderr=PIPE, env={'PATH': os.environ['PATH']})
            self.local_folder_cygwin = cygpath.communicate()[0].strip()


        log.info("Starting test transfer...")
        if self.test_transfer():
            log.info("Starting real transfer...")
            self.running = True
            self.transfer_time = int(time())
            self.start_transfer()  # TODO actually pass args
            self.open_progress()
        else:
            msg = gtk.MessageDialog(parent=None, flags=gtk.DIALOG_MODAL,
                                    type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK,
                                    message_format="Connection Error!  Check user/password and network.")
            msg.run()
            msg.destroy()

        self.dl_dialog.destroy()
        del self.dl_dialog

    def test_transfer(self):
        self.test_transfer = Popen(["lftp", "sftp://{}".format(self.host)],
            stdin=PIPE, stdout=PIPE, stderr=PIPE, env={'PATH': os.environ['PATH']})
        out = self.test_transfer.communicate(
                "user {} {} && ((ls && echo THINDLSUCCESS && exit) || (echo THINDLFAILURE && exit))".format(
                self.user, self.password))
        if self.test_transfer.poll() is None:
            self.test_transfer.terminate()

        if self.test_transfer.poll() is None:
            self.test_transfer.kill()

        return "THINDLSUCCESS" in out[0]

    def start_transfer(self):  #, host, user, password, remote_path, local_folder):
        ## TODO add in variables for connections per file
        ## TODO choose method sftp, etc...?

        self.transfer = Popen(["lftp", "sftp://{}".format(self.host)],
            stdin=PIPE, stdout=PIPE, stderr=PIPE, env={'PATH': os.environ['PATH']})

        ## TODO cleanup this mess
        if self.pget > 0:
            if self.remote_isFolder:
                opts = " --use-pget-n={}".format(self.pget)
            else:
                opts = " -n {}".format(self.pget)
        else:
            opts = ""

        if self.resume:
            opts += " -c"

        if self.isWindows:
            l_path = self.local_folder_cygwin
        else:
            l_path = self.local_folder

        if self.remote_isFolder:
            ## NOTE this doesn't block
            self.transfer.stdin.write("user {} {} && (mirror{} {} {} || exit)\n".format(
                self.user, self.password, opts, self.remote_path, l_path))
        else:
            opts += " -O " + self.l_path
            self.transfer.stdin.write("user {} {} && (pget{} {} || exit)\n".format(
                self.user, self.password, opts, self.remote_path))


    def update(self):

        if self.running:
            if self.transfer.poll() is not None and not self.transfer_stopped:
                ## ended prematurely
                ## TODO figure out failure state: i.e. process has stopped, but filesizes not matched
                msg = gtk.MessageDialog(parent=None, flags=gtk.DIALOG_MODAL,
                                        type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK,
                                        message_format="Transfer unexpectedly interrupted! Try restarting.")

                self.prog_dialog.destroy()
                msg.run()
                msg.destroy()
            elif self.local_folder is not None and self.remote_size is not None:

                if self.local_size == self.remote_size:
                    self.pr_builder.get_object("doneButton").set_sensitive(True)
                    self.pr_builder.get_object("cancelButton").set_sensitive(False)
                    self.running = False

                ## TODO find good way to measure speed....seems like size/time can lag a bit
                if time() % 3 < 1:
                    self.local_size = deluge.common.get_path_size(self.local_folder)
                    self.time_bytes += self.local_size - self.local_size_prev
                    self.speed = self.time_bytes / 3.0
                    self.time_bytes = 0
                else:
                    self.time_bytes += self.local_size - self.local_size_prev

                if self.local_size <= 0:
                    self.local_size = 0.0
                else:
                    self.local_size = float(self.local_size)

                prog_str = "{} / {}".format(deluge.common.fsize(self.local_size),
                        deluge.common.fsize(self.remote_size))
                self.pr_builder.get_object("progBar").set_fraction( self.local_size / self.remote_size )
                self.pr_builder.get_object("progressDialog").set_markup("Completed: {} ({})".format(
                    deluge.common.fpcnt( self.local_size / self.remote_size ), deluge.common.fspeed( self.speed )))
                self.local_size_prev = self.local_size
                self.pr_builder.get_object("progressDialog").format_secondary_text("Progress: {}".format(prog_str))

    def on_noButton(self, data=None):
        self.dl_dialog.destroy()
        del self.dl_dialog

    def load_interface(self):
        mainmenu = component.get("MenuBar")
        torrentmenu = mainmenu.torrentmenu

        self.menu = gtk.MenuItem(_("Local Download"))
        self.menu.show()


        self.menu.connect("activate", self.on_menu_activate)

        mainmenu.add_torrentmenu_separator()
        torrentmenu.append(self.menu)

    def get_selected(self):
        """
        returns selected torrents
        """
        return component.get("TorrentView").get_selected_torrents()

    def on_menu_activate(self, data=None):
        selected = self.get_selected()
        if selected is None:
            ## TODO error
            pass

        tx = Transfer(selected[0])
        ## what to do with TX? add to list?
        ## add to dict { torrent_hash : tx_obj }

        t_data = component.get("SessionProxy").get_torrent_status(self.t_id,
            ["move_on_completed","move_on_completed_path","save_path"]).addCallback(self.on_get)

    def disable(self):
        torrentmenu = component.get("MenuBar").torrentmenu
        torrentmenu.remove(self.menu)

        self.stop_transfer()

        component.get("Preferences").remove_page("thindl")
        component.get("PluginManager").deregister_hook("on_apply_prefs", self.on_apply_prefs)
        component.get("PluginManager").deregister_hook("on_show_prefs", self.on_show_prefs)

    def on_apply_prefs(self):
        log.debug("applying prefs for thindl")
        config = {
            "lftp_pget":self.glade.get_widget("lftp_pget_config").get_value(),
            "local_folder":self.glade.get_widget("local_folder_config").get_filename()
        }
        client.thindl.set_config(config)

    def on_show_prefs(self):
        client.thindl.get_config().addCallback(self.cb_get_config)

    def cb_init_config(self, config):
        self.config = config

    def cb_get_config(self, config):
        "callback for on show_prefs"
        self.config = config
        self.glade.get_widget("lftp_pget_config").set_value(config["lftp_pget"])
        self.glade.get_widget("local_folder_config").set_filename(config["local_folder"])


class Transfer(object):
    """
    transfer stuff goes here
    notes: have dict with hash:Torrent in main class
    """
    def __init__(self, hash):
        self.hash = hash  # who am I?

        self.is_running = False  # am I transferring files?
        self.is_completed = False  # all files transferred?

        self.local['size']      = 0
        self.local['folder']    = None  # TODO load from config

        self.remote['size']     = None  # TODO set remotely
        self.remote['folder']   = None  # TODO set remotely??
        self.remote['name']     = None  # TODO set remotely ? or thru client

        ## TODO dict/list for dialogs
        pass
