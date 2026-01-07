import os
import wx
import gui
import addonHandler
import globalPluginHandler
import ui
import webbrowser
import core
import ctypes # Windows API için doğrudan erişim

# Dil dosyasını yükle
addonHandler.initTranslation()

class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	scriptCategory = _("Quick Reply")
	_config_path = os.path.join(os.path.dirname(__file__), "replies.txt")

	@classmethod
	def _ensure_config(cls):
		if not os.path.exists(cls._config_path):
			try:
				with open(cls._config_path, "w", encoding="utf-8") as f:
					f.write("Greeting:Merhaba, size nasıl yardımcı olabilirim?\n")
			except:
				pass

	@classmethod
	def _get_replies(cls):
		replies = {}
		if os.path.exists(cls._config_path):
			try:
				with open(cls._config_path, "r", encoding="utf-8") as f:
					for line in f:
						if ":" in line:
							parts = line.strip().split(":", 1)
							if len(parts) == 2:
								replies[parts[0].strip()] = parts[1].strip()
			except:
				pass
		return replies

	def __init__(self):
		super().__init__()
		self.menu_item = None
		wx.CallAfter(self._add_menu_item)

	def _add_menu_item(self):
		try:
			tools_menu = gui.mainFrame.sysTrayIcon.toolsMenu
			self.menu_item = tools_menu.Append(wx.ID_ANY, _("Quick Reply Settings..."))
			gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.on_settings, self.menu_item)
		except Exception:
			pass

	def on_settings(self, evt):
		dlg = QuickReplyManagerDialog(gui.mainFrame, self)
		dlg.ShowModal()

	def terminate(self):
		if self.menu_item:
			try:
				gui.mainFrame.sysTrayIcon.toolsMenu.Remove(self.menu_item)
			except:
				pass

# --- KOPYALAMA MOTORU (WINDOWS API ZORLAMALI) ---
GlobalPlugin._ensure_config()
replies_data = GlobalPlugin._get_replies()

for label, content in replies_data.items():
	_safe_label = "".join(c for c in label if c.isalnum())
	method_name = f"script_copy_{_safe_label}"
	
	def make_paster(text, name):
		def script(self, gesture):
			# Windows API kullanarak panoya doğrudan yazma (Zorla Kopyalama)
			try:
				# Panoyu aç
				ctypes.windll.user32.OpenClipboard(None)
				# Panoyu temizle
				ctypes.windll.user32.EmptyClipboard()
				# Metni hazırla
				h_global_mem = ctypes.windll.kernel32.GlobalAlloc(0x42, len(text.encode('utf-16-le')) + 2)
				lp_global_mem = ctypes.windll.kernel32.GlobalLock(h_global_mem)
				ctypes.cdll.msvcrt.wcscpy(ctypes.c_wchar_p(lp_global_mem), text)
				ctypes.windll.kernel32.GlobalUnlock(h_global_mem)
				# Panoya metni (CF_UNICODETEXT = 13) formatında bas
				ctypes.windll.user32.SetClipboardData(13, h_global_mem)
				# Panoyu kapat
				ctypes.windll.user32.CloseClipboard()
				
				# Bildirim: "Kopyalandı: {name}"
				ui.message(_("Pasted: {name}").format(name=name))
			except Exception:
				# Eğer Windows API hata verirse NVDA Pano metodunu kullan (Yedek)
				import api
				api.copyToClipboard(text)
				ui.message(_("Pasted: {name}").format(name=name))
			
		script.__doc__ = _("Pastes the text for: {name}").format(name=name)
		script.category = GlobalPlugin.scriptCategory
		return script

	setattr(GlobalPlugin, method_name, make_paster(content, label))

class QuickReplyManagerDialog(wx.Dialog):
	def __init__(self, parent, plugin):
		super().__init__(parent, title=_("Quick Reply Manager"), size=(550, 520))
		self.plugin = plugin
		mainSizer = wx.BoxSizer(wx.VERTICAL)
		mainSizer.Add(wx.StaticText(self, label=_("Current Templates:")), 0, wx.ALL, 10)
		self.listCtrl = wx.ListBox(self, size=(-1, 150))
		self._load_list()
		mainSizer.Add(self.listCtrl, 0, wx.EXPAND | wx.ALL, 10)
		inputSizer = wx.FlexGridSizer(2, 2, 10, 10)
		inputSizer.AddGrowableCol(1)
		inputSizer.Add(wx.StaticText(self, label=_("Template Name:")))
		self.nameInput = wx.TextCtrl(self)
		inputSizer.Add(self.nameInput, 1, wx.EXPAND)
		inputSizer.Add(wx.StaticText(self, label=_("Text Content:")))
		self.contentInput = wx.TextCtrl(self, style=wx.TE_MULTILINE, size=(-1, 100))
		inputSizer.Add(self.contentInput, 1, wx.EXPAND)
		mainSizer.Add(inputSizer, 0, wx.EXPAND | wx.ALL, 10)
		actionSizer = wx.BoxSizer(wx.HORIZONTAL)
		addBtn = wx.Button(self, label=_("&Add/Update"))
		addBtn.Bind(wx.EVT_BUTTON, self.on_save)
		actionSizer.Add(addBtn, 1, wx.ALL, 5)
		deleteBtn = wx.Button(self, label=_("&Delete Selected"))
		deleteBtn.Bind(wx.EVT_BUTTON, self.on_delete)
		actionSizer.Add(deleteBtn, 1, wx.ALL, 5)
		mainSizer.Add(actionSizer, 0, wx.EXPAND)
		bottomSizer = wx.BoxSizer(wx.HORIZONTAL)
		donateBtn = wx.Button(self, label=_("Donate (PayTR)"))
		donateBtn.Bind(wx.EVT_BUTTON, lambda e: webbrowser.open("https://www.paytr.com/link/N2IAQKm_"))
		bottomSizer.Add(donateBtn, 1, wx.ALL, 5)
		restartBtn = wx.Button(self, label=_("&Restart NVDA to Apply"))
		restartBtn.Bind(wx.EVT_BUTTON, self.on_restart)
		bottomSizer.Add(restartBtn, 1, wx.ALL, 5)
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
		if not name or not content: return
		replies = self.plugin._get_replies()
		replies[name] = content
		self._write_file(replies)
		self._load_list()
		self.nameInput.Clear()
		self.contentInput.Clear()
		ui.message(_("Saved. Please restart NVDA to update Input Gestures."))

	def on_delete(self, evt):
		sel = self.listCtrl.GetSelection()
		if sel == wx.NOT_FOUND: return
		name = self.listCtrl.GetString(sel)
		replies = self.plugin._get_replies()
		if name in replies:
			del replies[name]
			self._write_file(replies)
			self._load_list()
			ui.message(_("Deleted successfully."))

	def on_restart(self, evt):
		core.restart()

	def _write_file(self, replies):
		with open(self.plugin._config_path, "w", encoding="utf-8") as f:
			for k, v in replies.items():
				f.write(f"{k}:{v}\n")