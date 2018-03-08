# Directory structure

Like any website, index.html is first loaded on entry. Importantly, it loads a bunch of key variables in the `variables.js` script. It then runs a check on the worker (to see if it's on
some banned list; see `checkworker()` in `js/server.js`. `checkworker()` is first called in `preview.html`) and then if it passes, the participant details are assigned (workerId, assignment number, condition, and counterbalance condition) and the experiment is truly started up (`startup()` in `experiment.js`).

`startup()` loads a bunch of trial templates (the html files in `/templates`) and starts running it, beginning with the
observation trials (`observation.js`). This also creates a new data file (for each new participant) that is saved in
some data directory (this happens when the `savedata()` function is run. The function is written in the server.js file).
And it also creates the stimuli (`stimuli.make_stimuli`, which can be found in the `stimuli.js` file)). 


# Notes 

Before publishing, remember to change these variables:

1. For each cgi file
restore the first line to be `#! /bin/python`

2. in `config.py`
Restore the right path to data on server (around line 11)

Check that conditions names match in `config.py` (line 16) and that the counterbalance number in the next line is appropriate

Also, remember to check where the Workers db is saved in Luke. I'm guessing this is a list of workers we want to block -
check with Nolan.)

