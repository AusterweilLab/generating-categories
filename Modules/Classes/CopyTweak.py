import numpy as np

# imports from module
import Modules.Funcs as funcs
from Model import Model

class CopyTweak(Model):
	"""
		Exemplar similarity implementation of the copy-and-tweak model.
	"""

	model = 'Copy and Tweak'
	parameter_names = [
		'specificity', # > 0
		'tolerance', # 0 < tolerance <= 1
		'determinism' # > 0
	]

	@staticmethod
	def rvs():
		params = [
			np.random.uniform(0.1, 6.0), # specificity
			np.random.uniform(0.5, 1.0), # tolerance. biased high.
			np.random.uniform(0.1, 6.0) # determinism
		]
		return params


	def _param_handler_(self):
		super(CopyTweak, self)._param_handler_()
		if self.specificity <= 0: self.specificity = 1e-10
		if self.tolerance > 1.0: self.tolerance = 1.0
		if self.determinism <= 0: self.determinism = 1e-10

	def get_generation_ps(self, stimuli, category):

		# return uniform probabilities if there are no exemplars
		target_is_populated = any(self.assignments == category)
		if not target_is_populated:
			ncandidates = stimuli.shape[0]
			return np.ones(ncandidates) / float(ncandidates)

		# get source probabilities
		nsources = self.nexemplars[category]
		sources = self.categories[category]
		source_ps = np.ones(nsources) / float(nsources)

		# get pairwise similarities
		distances  = funcs.pdist(stimuli, sources, w = self.wts)
		similarity = np.exp(-1.0 * self.specificity * distances)

		# get generation probabilities given each source
		generation_ps = np.exp(float(self.determinism) * similarity)

		# zero out probabilities above the similiarity tolerance
		generation_ps[similarity > self.tolerance] = 0.0

		# zero out examples already in the target category
		known_members = funcs.intersect2d(stimuli, self.categories[category])
		generation_ps[known_members] = 0.0

		# normalize
		generation_ps = generation_ps / generation_ps.sum(axis = 0, keepdims = True)
		
		# find nan columns to prevent nan ps
		nancols = np.all(np.isnan(generation_ps), axis = 0)
		generation_ps[:,nancols] = 1.0 / stimuli.shape[0]

		# multiply generation and source probabilities, then sum over sources
		ps = generation_ps * source_ps[None, :]
	
		ps = np.sum(ps, axis = 1)
		return ps


