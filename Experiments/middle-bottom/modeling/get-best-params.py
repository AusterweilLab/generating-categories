import sys, pickle

# add modeling module
sys.path.insert(0, "../../../Modules/") # generate-categories/Modules
from models import CopyTweak, Packer, ConjugateJK13, Optimize
import utils

# get data from pickle
with open( "data.pickle", "rb" ) as f:
	trials, stimuli = pickle.load( f )


# options for the optimization routine
options = dict(
	method = 'Nelder-Mead',
	options = dict(maxiter = 500, disp = False),
	tol = 0.01,
) 

for o in [CopyTweak, Packer, ConjugateJK13]:
	inits = o.rvs()

	print '\nInit values:'
	print dict(zip(o.parameter_names, [round(i,3) for i in inits]))

	Optimize.hillclimber(o, inits, trials, stimuli, options)


	