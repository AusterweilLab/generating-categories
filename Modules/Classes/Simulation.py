import scipy.optimize as op
import scipy.stats as ss
import numpy as np
import sys

import Modules.Funcs as funcs

currmodel='' #temp
currtrials=''
callback = ''
itcount = 0

class Trialset(object):

    """
    A class representing a collection of trials
        Data (i.e., responses) is saved in a list Set
    """
        
    def __init__(self, stimuli):
        
        # figure out what the stimulus domain is        
        self.stimuli = stimuli
        self.stimrange = funcs.getrange(stimuli)
                
        # initialize trials list
        self.Set = [] # compact set
        self.nunique = 0
        self.nresponses = 0
        self.task = ''
        self.nparticipants = 0
        self.participants = []
                
    def __str__(self):
        S  = 'Trialset containing: ' 
        S += '\n\t ' + str(self.nunique) + ' unique trials '
        S += '\n\t ' + str(self.nresponses) + ' total responses'
                # S += '\nTask: ' + self.task
        return S

    def _update(self):
        self.nunique = len(self.Set)
        self.nresponses = sum([len(i['response']) for i in self.Set])

    def add(self, response, categories = [], participant = []):
        """Add a single trial to the trial lists
                
        If response variable is a scalar, then add response to only one
        category. If response variable is a 2-element list, then add the
        value of the first element to the category specified by the
        second element.
        
        Also add participant information (if available)
        
        """
        
        if type(response) is not list:
            add2cat = None
            responseType = 1
            response = response
        elif type(response) is list:
            if len(response) == 2:
                add2cat = response[1]
                responseType = 2
                response = response[0]                                
                
            else:
                raise ValueError('The "response" variable needs',\
                                 'to be either a single number,',\
                                 'or a a list containing',\
                                 'only 2 elements.')
            
        # sort category lists, do a lookup
        categories = [np.sort(i) for i in categories]
        idx = self._lookup(categories)
        # if there is no existing configuration, add a new one
        if idx is None:
            self.nunique += 1            
            if responseType == 1:
                self.Set.append(dict(
                    response = [response], 
                    categories = categories,
                    participant = [participant])
                )
            elif responseType == 2:
                ncat = len(categories)                             
                respList =  [[] for _ in xrange(len(categories))]
                #respList[add2cat] = np.append(respList[add2cat],(response))
                pList = [[] for _ in xrange(len(categories))]
                respList[add2cat].append(response)
                pList[add2cat].append(participant)
                                
                self.Set.append(dict(
                    response = respList,
                    categories = categories,
                    participant = pList)
                )
        # if there is an index, just add the response
        else:
            if responseType == 1:
                self.Set[idx]['response'] = np.append(
                    self.Set[idx]['response'], response)
                self.Set[idx]['participant'] = np.append(
                    self.Set[idx]['participant'], participant)
            elif responseType == 2:
                self.Set[idx]['response'][add2cat].append(response)
                self.Set[idx]['participant'][add2cat].append(participant)
                #self.Set[idx]['response'][add2cat] = np.append(
                #        self.Set[idx]['response'][add2cat],response)
                #Hmm, why can't I just use self.Set[idx]['response']...
                #...[add2cat].append(response)?

        #Add participant to list of unique participants
        if isinstance(participant,int):
            if not participant in self.participants:
                self.participants = np.append(self.participants,participant)
                self.nparticipants += 1
        else: #if list or array
            for pel in participant:
                if not pel in self.participants:
                    self.participants = np.append(self.participants,pel)
                    self.nparticipants += 1

        # increment response counter
        self.nresponses += 1
                
    def _lookup(self, categories):
        """
            Look up if a category set is already in the compact set.
            return the index if so, return None otherwise
        """

        for idx, trial in enumerate(self.Set):

            # if the categories are not the same size, then they are 
            # not equal...
            if len(categories) != len(trial['categories']): continue

            # check equality of all pairs of categories
            equals =[np.array_equal(*arrs) 
                     for arrs in zip(categories, trial['categories'])]

            # return index if all pairs are equal
            if all(equals): return idx

        # otherwise, return None
        return None


    def add_frame(self, generation, task = 'generate'):
        """
        Add trials from a dataframe

        If task=='generate', then the dataframe must have columns:
                participant, trial, stimulus, categories

                If task=='assign', then the dataframe must have columns:
                participant, trial, stimulus, assignment, categories

        Where categories is a embedded list of known categories
        PRIOR to trial = 0.               
        """ 
        if task == 'generate':
            for pid, rows in generation.groupby('participant'):
                for num, row in rows.groupby('trial'):
                    Bs = rows.loc[rows.trial<num, 'stimulus'].as_matrix()
                    categories = row.categories.item() + [Bs]
                    stimulus = row.stimulus.item()
                    self.add(stimulus, categories = categories,participant = row.participant.item())

        elif task == 'assign' or task == 'error':
            # So the response trials added here can be from any
            # category, not just the generated one
            for pid, rows in generation.groupby('participant'):
                #print pid
                for num, row in rows.groupby('trial'):
                    #categories don't grow in size here, so
                    #no + Bs
                    #print row.categories
                    categories = row.categories.item()
                    target = row.stimulus.item()
                    add2cat = row.assignment.item()
                    stimulus = [target,add2cat]
                    self.add(stimulus, categories = categories,participant = row.participant.item())
        else:
            raise ValueError('Oh no, it looks like you have specified an illegal value for the task argument!')

                
        return self
                

    def loglike(self, params, model, fixedparams = None, whole_array=False):
        """
        Evaluate a model object's log-likelihood on the
        trial set based on the provided parameters.
                
        If whole_array is True, then loglike returns the nLL
        of each trial in the Trialset. 
        """
        
        # reverse-transform parameter values
        params = model.parmxform(params, direction = -1)        

        # extract fixed parameters and feed it into params variable
        if hasattr(fixedparams,'keys'):
            #convert free parms to dict
            params = model.params2dict(params)
            for parmname in fixedparams.keys():
                params[parmname] = fixedparams[parmname]
        
        # iterate over trials
        loglike = 0
        ps_list = np.array([])
        task = self.task
        for idx, trial in enumerate(self.Set):

            # format categories
            categories = [self.stimuli[i,:] for i in trial['categories'] if any(i)]

            # if it's an assignment task, also compute probabilities for other category (cat0)
            # ps0 = np.zeros(ps1.shape)
            if task is 'generate':                                
                # compute probabilities of generating exemplar in cat 1
                ps = model(categories, params, self.stimrange).get_generation_ps(self.stimuli, 1,self.task)
                ps_add = ps[trial['response']]
            elif task=='assign':
                #Compute probabilities of assigning exemplar to cat 0
                ps0 = model(categories, params, self.stimrange).get_generation_ps(self.stimuli, 0,self.task)
                #Compute probabilities of assigning exemplar to cat 1
                ps1 = model(categories, params,
                            self.stimrange).get_generation_ps(self.stimuli,
                                                              1,self.task)

                
                idc0 = trial['response'][0]
                idc1 = trial['response'][1]
                #ps_add = ps0[idc0]
                ps_add = np.concatenate([ps0[idc0],ps1[idc1]])
                #How about using binomial likelihoods instead?
                #200218 SX: aahh, it gives the same values. Cool
                # ps = []
                # for i,ps_el in enumerate(ps0):
                #         #find total assignments to category 0
                #         ct0 = sum(np.array(idc0) == i)
                #         #find total assignments to category 1
                #         ct1 = sum(np.array(idc1) == i)
                #         #total assignments overall
                #         ctmax = ct0+ct1
                
                #         ps += [ss.binom.pmf(ct0, ctmax,ps_el)]
                
            elif task=='error':
                #For prediction of error probabilities, simply
                #find the probability of classifying a
                #stimulus as the wrong category

                #The old way (prior to 010618) was to simply treat cat 0 as
                #correct and cat 1 as incorrect, since that's the way that the
                #only error dataset NGPMG1994 has been set up. This is quite
                #pointless, and I've generalised the code here so that it really
                #looks at errors in categorising.
                #ps = model(categories, params, self.stimrange).get_generation_ps(self.stimuli, 0,self.task)
                #idc_err = trial['response'][0]
                #Compute probabilities of assigning exemplar to cat 0
                ps0 = model(categories, params,
                            self.stimrange).get_generation_ps(self.stimuli, 0,self.task)
                #Compute probabilities of assigning exemplar to cat 1
                ps1 = model(categories, params,
                            self.stimrange).get_generation_ps(self.stimuli, 1,self.task)
                idc0 = trial['response'][0] 
                idc1 = trial['response'][1] 
                #Actual category exemplars
                correctcat = trial['categories']

                correctps = []
                wrongps   = []
                #Iterate over each category
                for i in range(len(correctcat)):
                    #Get right and wrong responses
                    correctresp = np.array([exemplar for exemplar in
                                              trial['response'][i] if exemplar in
                                              correctcat[i]])
                    wrongresp = np.array([exemplar for exemplar in
                                              trial['response'][i] if not exemplar in
                                              correctcat[i]])
                    print correctresp
                    print wrongresp
                    #Get entire probability space
                    ps = model(categories, params,
                               self.stimrange).get_generation_ps(self.stimuli,
                                                                 i,self.task)
                    if len(correctresp)>0:
                        correctps = np.concatenate([correctps,ps[correctresp]])
                    if len(wrongresp)>0:
                        wrongps   = np.concatenate([wrongps,ps[wrongresp]])
                        

                print ps0

                print correctps

                print wrongps
                ps_add = np.concatenate([correctps,wrongps])

                                
            # check for nans and zeros
            if np.any(np.isnan(ps_add)):
                ps_add = np.zeros(ps_add.shape)
                # print categories
                # print params
                # print ps_add
                # S = model.model  + ' returned NAN probabilities.'
                # raise Exception(S)
            ps_add[ps_add<1e-308] = 1e-308

            if whole_array:
                ps_list = np.append(ps_list,ps_add)
            else:
                loglike += np.sum(np.log(ps_add))                        

        if whole_array:
            return -1.0 * np.log(ps_list)
        else:
            return -1.0 * loglike

def hillclimber(model_obj, trials_obj, options, fixedparams = None, inits = None, results = True,callbackstyle='none'):
    """
    Run an optimization routine.

    model_obj is one of the model implementation in the module.
    init_params is a numpy array for the routine's starting location.
    trials_obj is a Trialset object.
    options is a dict of options for the routine. Example:
        method = 'Nelder-Mead',
        options = dict(maxiter = 500, disp = False),
        tol = 0.01,

    Function prints results to the console (if results is set to True), and returns the ResultSet
    object.
    """
    global currmodel
    currmodel = model_obj
    global currtrials
    currtrials = trials_obj
    global callback
    callback = callbackstyle
    global itcount
    # set initial params
    if inits is None:    
        inits = model_obj.rvs(fmt = list) #returns random parameters as list
        if results:
            print '\nStarting parms (randomly selected):'
            print inits
    #transform inits to be bounded within rules
    inits = model_obj.parmxform(inits, direction = 1)
    # run search
    itcount = 0
    if results:
        print 'Fitting: ' + model_obj.model
                
    res = op.minimize(    trials_obj.loglike, 
                inits, 
                args = (model_obj,fixedparams),
                callback = _callback_fun_, 
                **options
        )
    #reverse-transform the parms
    res.x = model_obj.parmxform(res.x, direction = -1)
        
    # print results
    if results:
        print '\n' + model_obj.model + ' Results:'
        print '\tIterations = ' + str(res.nit)
        print '\tMessage = ' + str(res.message)
        
        X = model_obj.params2dict(model_obj.clipper(res.x))
        for k, v in X.items():
            print '\t' + k + ' = ' + str(v) + ','
            
        print '\tLogLike = ' + str(res.fun)            
        AIC = funcs.aic(res.fun,len(inits))
        print '\tAIC = ' + str(AIC)
                        
    return res

def _callback_fun_(xk):
    """
    Function executed at each step of the hill-climber
    """
    #callback = '.' #this line is here for easier manual switching of display
    
    model_obj,trials_obj,display = _fetch_global_()
    global itcount
    #Set how many columns to print
    printcol = 20 
    if display is 'iter':
        ll = trials_obj.loglike(xk,model_obj)                
        xk = model_obj.parmxform(xk, direction = -1)
        print '\t[' + ', '.join([str(round(i,4)) for i in xk]) + '] f(x) = ' + str(round(ll,4))
    elif display is '.':                
        if (np.mod(itcount,printcol)!=0) & (itcount>0):
            print '\b.',
            sys.stdout.flush()
        elif (itcount>0):
            print '\b.'

                        
                #print '\t[' + ', '.join([str(round(i,4)) for i in xk]) + ']'
    elif display is 'none':
        pass
    elif type(display) is str:
        if np.mod(itcount,printcol)==0 & itcount>0:
            eval('print ' + display)
        else:
            eval('print ' + '\b' +  display)
            

    itcount += 1


#Temporary function to enable printing of function value during callback of minimization
def _fetch_global_():
    global currmodel
    global currtrials
    global callback
    return currmodel,currtrials,callback


def show_final_p(model_obj, trial_obj, params, show_data = False):
    #One final presentation of the set of probabilities for each stimulus
    task = trial_obj.task
    nstim = len(trial_obj.stimuli)
    for idx, trial in enumerate(trial_obj.Set):
        # format categories
        categories = [trial_obj.stimuli[i,:] for i in trial['categories'] if any(i)]
        
        ps0 = model_obj(categories, params, trial_obj.stimrange).get_generation_ps(trial_obj.stimuli, 0,trial_obj.task)
        ps1 = model_obj(categories, params, trial_obj.stimrange).get_generation_ps(trial_obj.stimuli, 1,trial_obj.task)
        
        
        if show_data is False:
            print 'Model Predictions:'
            dsize = int(np.sqrt(len(ps0)))
            print np.atleast_2d(ps0).reshape(dsize,-1)
            print np.atleast_2d(ps1).reshape(dsize,-1)
        else:                        
            dsize = int(np.sqrt(len(ps0)))
            cat0ct = []
            cat1ct = []
            cat0pt = []
            cat1pt = []
            
            responses = trial['response']                        
            for j in range(nstim):#max(responses[0])+1):
                cat0 = sum(np.array(responses[0])==j)
                cat1 = sum(np.array(responses[1])==j)
                catmaxct = cat0+cat1
                cat0ct += [cat0]
                cat1ct += [cat1]
                p0 = float(cat0)/float(catmaxct)
                p1 = 1-p0
                cat0pt += [p0]
                cat1pt += [p1]
                
                sse = sum((np.array(ps0)-np.array(cat0pt))**2 + \
                          (np.array(ps1)-np.array(cat1pt))**2)
                
                cat0pt = [round(i,4) for i in cat0pt]
                cat1pt = [round(i,4) for i in cat1pt]
                
                ps0 = [round(i,4) for i in ps0]
                ps1 = [round(i,4) for i in ps1]
                
                print 'Condition ' + str(idx)
                print 'SSE = ' + str(sse)
                print 'Model Predictions (Cat0):'
                print np.flipud(np.atleast_2d(ps0).reshape(dsize,-1))
                print 'Observed Data (Cat0):'
                print np.flipud(np.atleast_2d(cat0pt).reshape(dsize,-1))
                # print 'Model Predictions (Cat1):'
                # print np.flipud(np.atleast_2d(ps1).reshape(dsize,-1))
                # print 'Observed Data (Cat1):'
                # print np.flipud(np.atleast_2d(cat1pt).reshape(dsize,-1))
                
                #lll
                #print ps0
                #print ps1
                #print np.atleast_2d(ps0).reshape(4,4)
                #print np.atleast_2d(ps1).reshape(4,4)



# Extract participant-level data and particular unique trials
def extractPptData(trial_obj, ppt = 'all', unique_trials = 'all'):
    """
    Extracts data for a single participant (or range of participants, if it's a list)
    from a trialset object. Can also extract specific unique trials (aka
    trained category stimuli).
    
    If unique_trials is set to 'all', then all unique trials are included.
    
    Returns a trialset object
    """
    import copy as cp
    if ppt != 'all' and type(ppt) is not list:
        ppt = [ppt]        

    if unique_trials is not 'all':
        #check for the type of input
        if not hasattr(unique_trials,'__len__'):
            #scalars don't have this attr
            idx = unique_trials
        elif not hasattr(unique_trials[0],'__len__'):
            #if it's a list of scalars, extract only those
            idx = unique_trials
        else:
            #extract only trials that match these unique trials
            #Only handles one idx at a time for now 130218
            idx = trial_obj._lookup(unique_trials)
                        
        if idx is None:
            S = 'Specified set of unique trials not found in trial set.'
            raise Exception(S)
        #Remove all unique trials except the selected one
        if isinstance(idx,list):
            temp_obj = [chunk for i,chunk in enumerate(trial_obj.Set) if i in idx]
            trial_obj.Set = []
            trial_obj.Set = [chunk for chunk in temp_obj]
        else:
            temp_obj = trial_obj.Set[idx]                        
            trial_obj.Set = []
            trial_obj.Set.append(temp_obj)
                
                
    output_obj = cp.deepcopy(trial_obj)
    ncategories = len(trial_obj.Set[0]['categories'])
    for ti,trialchunk in enumerate(trial_obj.Set):
        responsecats = trialchunk['response']
        pptcats = trialchunk['participant']
        respList = np.array([])
        pptList = np.array([])
        if trial_obj.task is 'generate':
            #convert pptcat and responsecat to array for easier indexing
            if ppt == 'all':
                respList = responsecats
                pptList = pptcats
            else:
                for i in ppt:
                    extractIdx = np.array(pptcats==np.array(round(i)))
                    responsecats = np.array(responsecats)
                    pptcats = np.array(pptcats)
                    respList = responsecats[extractIdx]
                    pptList = pptcats[extractIdx]
                        
        elif trial_obj.task is 'assign' or trial_obj.task is 'error':
            #iterate over categories of responses        
            respList = [np.array([], dtype = int) for _ in xrange(ncategories)]
            pptList = [np.array([], dtype = int) for _ in xrange(ncategories)]        
            for pi,pptcat in enumerate(pptcats):
                #convert pptcat and responsecat to array for easier indexing
                responsecat = np.array(responsecats[pi])
                pptcat = np.array(pptcat)
                if ppt == 'all':
                    respList[pi] = np.append(respList[pi],responsecat)
                    pptList[pi] = np.append(pptList[pi],pptcat)
                else:
                    for i in ppt:
                        extractIdx = pptcat==round(i)
                        respList[pi] = np.append(respList[pi],responsecat[extractIdx])
                        pptList[pi] = np.append(pptList[pi],pptcat[extractIdx])
        else:
            raise ValueError('trialset.task not specified. Please specify this as \'generate\' or \'assign\' in your script.')
                                
        output_obj.Set[ti]['response'] = respList
        output_obj.Set[ti]['participant'] = pptList
    #Clean up
    #cleanIdx = np.ones(len(output_obj.Set),dtype=bool)
    output_objTemp = cp.deepcopy(output_obj.Set)
    output_obj.Set = []
    for ti,trialchunk in enumerate(output_objTemp):
        if trial_obj.task is 'generate':
            if len(trialchunk['participant'])>0:                        
                #cleanIdx[ti] = False
                output_obj.Set.append(trialchunk)
        elif trial_obj.task is 'assign' or trial_obj.task is 'error':
            if len(trialchunk['participant'][0])>0:                        
                #cleanIdx[ti] = False
                output_obj.Set.append(trialchunk)

    #Finally, update the unique participant list
    if not ppt=='all':
        output_obj.participants = ppt
        output_obj.nparticipants = len(ppt)
        
    return output_obj

def loglike_allperm(params, model_obj, categories, stimuli, permute_category = 1,
                    fixedparams = None, task = 'generate'):
    """
    Finds the total loglikelihood of generating all permutations of some
    specified category. Default category to permute is 1 (i.e., the second category.)
    """
    if len(categories)>2:
        raise ValueError('This function can\'t deal with more than two',\
                    'categories yet. To fix this, go bug Xian or do it yourself.')

    import pandas as pd
    import math
    cat2perm = categories[permute_category]
    cat2notperm = categories[1-permute_category]
    nstim = len(cat2perm)
    #condition and ppt numbers aren't important so just give it some arbitrary
    #value
    pptnum = 0;
    pptcondition = 'meh';
    # Get all permutations of cat2perm and make a new trialObj for it
    nbetapermute = math.factorial(nstim)
    raw_array = np.zeros((1,nbetapermute))
    #Iterate over the different permutations of to-be-permuted category
    for i, pexemplars in enumerate(funcs.permute(cat2perm)):
        pptDF = pd.DataFrame(columns = ['participant','stimulus','trial','condition','categories'])
        pptDF.stimulus = pd.to_numeric(pptDF.stimulus)
        pptTrialObj = Trialset(stimuli)
        pptTrialObj.task = task
        for trial,exemplar in enumerate(pexemplars):
                pptDF = pptDF.append(
                        dict(participant=pptnum, stimulus=exemplar, trial=trial, condition=pptcondition, categories=[cat2notperm]),ignore_index = True
                )
        pptTrialObj.add_frame(pptDF)
        raw_array_ps = pptTrialObj.loglike(params,model_obj)
        raw_array[:,i] = raw_array_ps
    #Compute the total likelihood as the sum of the likelihood of each
    #permutation. Since I don't know an easy way to add something which is in
    #log-form, I'll convert it to exp first. However, the neg loglikelihoods can
    #get really large, which will tip it over to Inf when applying exp. To get
    #around this, subtract the LL by some constant (e.g., its max), exp it, add
    #up the probabilities, then log, and add it to the log of the constant
    raw_array_max = raw_array.max()
    raw_array_t = np.exp(-(raw_array - raw_array_max)).sum()
    raw_array_ll = -np.log(raw_array_t) + raw_array_max
    return raw_array_ll


# def add_model_data():
#         #Temporary code to add model parm names to gs results
#         import re
#         import os
#         import pickle

#         pickledir = 'pickles/'
#         prefix = 'gs_'
#         #Compile regexp obj
#         allfiles =  os.listdir(pickledir)
#         r = re.compile(prefix)
#         gsfiles = filter(r.match,allfiles)

#         for i,file in enumerate(gsfiles):
#                 with open(pickledir+file,'rb') as f:
#                         fulldata = pickle.load(f)
#                 modelnames = fulldata.keys()
#                 for j in modelnames:
#                         #Add data on their model type
#                         if j == 'Hierarchical Sampling':
#                                 fulldata[j]['parmnames'] = ['category_mean_bias',
#                                                             'category_variance_bias',
#                                                             'domain_variance_bias',
#                                                             'determinism']
#                         elif j == 'Copy and Tweak':
#                                 fulldata[j]['parmnames'] = ['specificity',
#                                                             'determinism']
#                         elif j == 'PACKER':
#                                 fulldata[j]['parmnames'] =  ['specificity',
#                                                              'tradeoff',
#                                                              'determinism']
#                 with open(pickledir+file,'wb') as f:
#                         pickle.dump(fulldata,f)
                                

# def print_gs_nicenice():
#         #Find all gs fits and print them. Nice nice.        
#         import re
#         import os
#         import pickle
        
#         pickledir = 'pickles/'
#         prefix = 'gs_'
#         #Compile regexp obj
#         allfiles =  os.listdir(pickledir)
#         r = re.compile(prefix)
#         gsfiles = filter(r.match,allfiles)

#         for i,file in enumerate(gsfiles):
#                 #Extract key data from each file
#                 print '\n' + file
#                 print '------'
#                 with open(pickledir+file,'rb') as f:
#                         fulldata = pickle.load(f)
#                 modelnames = fulldata.keys()
#                 for j in modelnames:
#                         print 'Model:' + j
#                         for pi,pname in enumerate(fulldata[j]['parmnames']):
#                                 print '\t' + pname + ': ' + str(fulldata[j]['bestparmsll'][pi])
#                         print '\tLogLike' + ' = ' + '-' + str(fulldata[j]['bestparmsll'][pi+1])
#                         print '\tAIC'  + ' = ' + str(fulldata[j]['bestparmsll'][pi+2])


