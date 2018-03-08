function [p,distance] = PACKER(parms,stimTest,stimTrain,categories,task)
% PACKER model of categorisation
% Written to see if the python version is actually making any sense.
% Parms is a vector of [specificity, tradeoff, determinism]
% Task can be 'generate' or 'assign'. 'generate' will yield predictions of
% the probability that a stimulus is generated as category 1
% given the training stim, and 'assign' will yield predictions of the 
% probability that a stimulus is assigned as category 1.
% 270218 Start

nStimTest = size(stimTest,1);
nStimTrain = size(stimTrain,1);
nCat = numel(unique(categories));
nDim = size(stimTrain,2);
w_k = ones(nStimTrain,nCat)./nDim; %equally weight for now
specificity = parms(1);
tradeoff = parms(2);
determinism = parms(3);

softmax = false;

if nCat~=2
    error('Fix generation of fx vector in the code before proceeding')
else
    %This will need to be fixed if nCat>2
    fx = repmat(tradeoff-1,nStimTrain,nCat); %gammas
    for k = 1:nCat       
        fx(categories==k,k) = tradeoff; %target category
    end
end
if numel(categories)~=nStimTrain
    error('Size of categories vector doesn''nt match size of stimTrain.')
end

r = 1;

distance = zeros(nStimTrain,nStimTest);
similarity = zeros(nStimTrain,nStimTest);
similarity_tradeoff = zeros(nStimTest,nCat);

for i = 1:nStimTest
    currStimTest = stimTest(i,:);
    for j = 1:nStimTrain         
        currStimTrain = stimTrain(j,:);
        diff = currStimTest-currStimTrain; %x-y
        weighted_diff = diff.^r .* w_k(j); %(x-y)^r
        distance(j,i) = sum(abs(weighted_diff),2).^(1/r); %sum((x-y)^r)^1/r
        similarity(j,i) = exp(-specificity*distance(j,i));
    end
    for k = 1:nCat
        similarity_tradeoff(i,k) = sum(fx(:,k) .* similarity(:,i));
    end
end

% similarity
% exp_sim

if softmax
    exp_sim = exp(determinism*similarity_tradeoff);
else %use Luce's regular rule
    exp_sim = determinism*similarity_tradeoff; %for consistency I'm leaving the exp in, but note there's no exp actually happening
end
% similarity_tradeoff
% exp_sim
switch task
    case 'generate'
        sum_sim = sum(exp_sim,1); %across all stim
        sum_sim = repmat(sum_sim,nStimTest,1);
        p = exp_sim ./ sum_sim;
    case 'assign'
        sum_sim = sum(exp_sim,2); %across all dim
        sum_sim = repmat(sum_sim,1,nCat);
        p = exp_sim ./ sum_sim;
    case 'error'
        sum_sim = sum(exp_sim,2); %across all dim
        sum_sim = repmat(sum_sim,1,nCat);
        p = 1-(exp_sim ./ sum_sim); %error
end
fx
similarity
similarity_tradeoff
exp_sim
sum_sim
exp_sim(1)/sum_sim(1)

sum_sim2 = sum(exp_sim,1);
sum_sim2 = repmat(sum_sim2,nStimTest,1)
p2 = exp_sim./sum_sim2
p = p(:,1); %only take out category 1 (for now?) 010318




