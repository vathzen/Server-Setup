!^s::MonitOff(MonitVar) ;hotkey to toggle the monitor on and off

MonitOff(ByRef x) {

SetTimer, MonitOffLabel, % (x:=!x) ? "50" : "Off" ;toggle the var and turn the timer on or off

If x ;if it turned on turn monitor off

  SendMessage,0x112,0xF170,2,,Program Manager

Else ;if it turned off move the mouse to wake up the screen

  MouseMove, 0,0,0,R

Return

MonitOffLabel: 

If(A_TimeIdle<500) ;if there has been activity

  SendMessage,0x112,0xF170,2,,Program Manager

Return

}