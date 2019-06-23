# UIAccess UAC bypass
In this example, we start a host process (msra.exe) that we steal the UIAccess token from. We downgrade the token IL from Medium+ to Medium so we can communicate with the process with keyboard events. We use the token to spawn a new process (uihack.exe) with the UIAccess flag to send keyboard events to msconfig process. Upon success, a elevated console window should appear.

Not designed to be stealthy, but it's for sure possible! This is a demo in Python, just to display how it works.

Creds to:
 * https://tyranidslair.blogspot.com/2019/02/accessing-access-tokens-for-uiaccess.html
 
 More UAC bypasses:
  * https://github.com/rootm0s/WinPwnage
  * https://github.com/hfiref0x/UACME
