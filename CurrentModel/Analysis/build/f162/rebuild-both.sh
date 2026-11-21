#!/bin/bash
# f162: rebuild both slices end to end: 8T at 1.0 (the failing one) then 8T-CR10Pro at 1.41.
cd /home/rhy/strata-fleet/repos/OpenAirShips || exit 1
bash CurrentModel/Analysis/build/f159/rebuild.sh 1.0 "" check || exit 1
bash CurrentModel/Analysis/build/f159/rebuild.sh 1.41 CR10Pro check || exit 1
echo "=== $(date +%T) BOTH DONE"
