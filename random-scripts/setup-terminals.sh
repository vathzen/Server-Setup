#! /bin/bash
gnome-terminal --geometry 108x29+-6+23    -- /bin/sh -c 'cd;cd go/src/backendSastraMess;./db.sh;bash';
gnome-terminal --geometry 108x25+-10--10  -- /bin/sh -c 'cd;cd go/src/backendSastraMess;go install;./exe.sh;bash';
gnome-terminal --geometry 128x23--10+19   -- /bin/sh -c 'heroku logs --tail -a sastramess;bash';
gnome-terminal --geometry 128x4--10+939   -- /bin/sh -c 'cd;cd Ionic/SASTRAMess/;ionic serve;bash';
gnome-terminal --geometry 128x24--10+474
