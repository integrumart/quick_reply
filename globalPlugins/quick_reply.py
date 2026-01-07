import os
import wx
import gui
import addonHandler
import globalPluginHandler
import ui
import webbrowser
import keyboardHandler
import api
import winUser

addonHandler.initTranslation()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
    scriptCategory = _("Quick Reply")
    _config_path = os.path.join(os.path.dirname(__file__), "replies.txt")

    @classmethod
    def _ensure_config(cls):
        if not os.path.exists(cls._config_path):
            with open(cls._config_path, "w", encoding="utf-8") as f:
                f.write("Greeting:Hello, how can I help you?\n")

    @classmethod
    def _get_replies(cls):
        replies = {}
        if os.path.exists(cls._config_path):
            with open(cls._config_path, "r", encoding="utf-8") as f:
                for line in f:
                    if ":" in line:
                        k, v = line.strip().split(":", 1)
                        replies[k.strip()] = v.strip()
        return replies

    def __init__(self):
        super().__init__()
        try:
            self.menu_item = gui.mainFrame.sysTrayIcon.toolsMenu.Append(
                wx.ID_ANY, _("Quick Reply Settings...")
            )
            gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.on_settings, self.menu_item)
        except:
            pass

    def on_settings(self, evt):
        dlg = QuickReplyManagerDialog(gui.mainFrame, self)
        dlg.ShowModal()

    def terminate(self):
        try:
            gui.mainFrame.sysTrayIcon.toolsMenu.Remove(self.menu_item)
        except:
            pass

# --- DINAMIK SCRIPT ENJEKSIYONU ---
GlobalPlugin._ensure_config()
_replies = GlobalPlugin._get_replies()

for _label, _content in _replies.items():
    _method_name = "script_%s" % _label.replace(" ", "_").replace(".", "").replace("-", "")
    
    def _make_script(text, name):
        def script(self, gesture):
            api.copyToClipboard(text)
            keyboardHandler.KeyboardInputGesture.fromName("control+v").send()
            ui.message(_("Pasted: {name}").format(name=name))
        script.__doc__ = _("Pastes the text for: {name}").format(name=name)
        script.category = GlobalPlugin.scriptCategory
        return script

    setattr(GlobalPlugin, _method_name, _make_script(_content, _label))

class QuickReplyManagerDialog(wx.Dialog):
    def __init__(self, parent, plugin):
        super().__init__(parent, title=_("Quick Reply Manager"), size=(500, 450))
        self.plugin = plugin
        mainSizer = wx.BoxSizer(wx.VERTICAL)
        
        mainSizer.Add(wx.StaticText(self, label=_("Current Templates:")), 0, wx.ALL, 10)
        
        # Liste Kutusu
        self.listCtrl = wx.ListBox(self, size=(-1, 150))
        self._load_list()
        mainSizer.Add(self.listCtrl, 0, wx.EXPAND | wx.ALL, 10)
        
        # Ekleme Alanları
        inputSizer = wx.FlexGridSizer(2, 2, 10, 10)
        inputSizer.AddGrowableCol(1)
        
        inputSizer.Add(wx.StaticText(self, label=_("Template Name:")))
        self.nameInput = wx.TextCtrl(self)
        inputSizer.Add(self.nameInput, 1, wx.EXPAND)
        
        inputSizer.Add(wx.StaticText(self, label=_("Text Content:")))
        self.contentInput = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1, 60))
        inputSizer.Add(self.contentInput, 1, wx.EXPAND)
        
        mainSizer.Add(inputSizer, 0, wx.EXPAND | wx.ALL, 10)
        
        # İşlem Butonları
        actionSizer = wx.BoxSizer(wx.HORIZONTAL)
        
        addBtn = wx.Button(self, label=_("&Add/Update"))
        addBtn.Bind(wx.EVT_BUTTON, self.on_save)
        actionSizer.Add(addBtn, 1, wx.ALL, 5)
        
        deleteBtn = wx.Button(self, label=_("&Delete Selected"))
        deleteBtn.Bind(wx.EVT_BUTTON, self.on_delete)
        actionSizer.Add(deleteBtn, 1, wx.ALL, 5)
        
        mainSizer.Add(actionSizer, 0, wx.EXPAND)

        # Alt Butonlar (Bağış ve Kapat)
        bottomSizer = wx.BoxSizer(wx.HORIZONTAL)
        donateBtn = wx.Button(self, label=_("Donate (PayTR)"))
        donateBtn.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open("https://www.paytr.com/link/N2IAQKm_"))
        bottomSizer.Add(donateBtn, 1, wx.ALL, 5)
        
        closeBtn = wx.Button(self, id=wx.ID_OK, label=_("&Restart NVDA to Apply"))
        bottomSizer.Add(closeBtn, 1, wx.ALL, 5)
        
        mainSizer.Add(bottomSizer, 0, wx.EXPAND | wx.ALL, 10)
        
        self.SetSizer(mainSizer)
        self.Layout()

    def _load_list(self):
        self.listCtrl.Clear()
        replies = self.plugin._get_replies()
        for name in replies:
            self.listCtrl.Append(name)

    def on_save(self, evt):
        name = self.nameInput.GetValue().strip()
        content = self.contentInput.GetValue().strip()
        if not name or not content:
            return
        
        replies = self.plugin._get_replies()
        replies[name] = content
        self._write_file(replies)
        self._load_list()
        self.nameInput.Clear()
        self.contentInput.Clear()
        ui.message(_("Saved. Restart NVDA to see changes in Input Gestures."))

    def on_delete(self, evt):
        sel = self.listCtrl.GetSelection()
        if sel == wx.NOT_FOUND: return
        name = self.listCtrl.GetString(sel)
        
        replies = self.plugin._get_replies()
        if name in replies:
            del replies[name]
            self._write_file(replies)
            self._load_list()
            ui.message(_("Deleted."))

    def _write_file(self, replies):
        with open(self.plugin._config_path, "w", encoding="utf-8") as f:
            for k, v in replies.items():
                f.write(f"{k}:{v}\n")