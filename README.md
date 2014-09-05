OneTouchDriver
==============

Driver for Ingenious Technology Co Ltd "OneTouch" transparent touchscreen overlay

Copyright 2011, Joe Koberg <joe@osoft.us>

Data format is a 3 or 5 byte report sent at 19200 8N1, either

    0xFF 0xFE 0xFE    - Sent upon touch release and sometimes alone on taps/short touches.
    0xFF X0 X1 Y0 Y1  - Where X and Y are little-endian 2-byte integers. Position is the high bits so divide by 64.

There is significant position noise at the start and end of each raw touch event.    
We wait for DISCARD_START reports to come in after a touch, then start putting them into a buffer.
When AVG_COUNT + DISCARD_END have accumulated, we output the average of the earliest AVG_COUNT samples.
When the touch is released the fifo is cleared. Thus the final DISCARD_END samples are ignored.
The panel reports at 200Hz.

There is also an attempt at auto-calibration/scaling. The edges of the panel are intermittent
and it's best to use a smaller active screen area.
