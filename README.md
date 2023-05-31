# Best chess player predictor
In this project we analyzed some data with the chess matches results of different international chess players, including Chinese players..
Based on historical information we processed ratings in a year fashion to obtain the final predicted level of the player at the end of the year.
Chess games were parsed following the procedure to update chess players scores after a match for the ELO ratings. This procedure is given by the International Chess Organization.

## Datasets for this project
The datasets used within this project are not included in the repository, so you need to add your own datasets following this hierarchy of folders.

### data folder
It should contain different folders:
- eval folder: folder with json files with games data (including result) for the evaluation of the predictor (not used in the training)
- predictions folder: the predictions' data of the predictor containing different properties. One pickle file per each version.
- ratings folder: the ratings' data of every year available for the predictor. Both as a pickle and as a json file.
- test folder: folder with the json files and the results. The final chinese names are the same as the original ones but in readable format for those who cannot read Chinese characters.
- io folder: input/output folder to store pickle files and ratings txt reference files.

## Notebooks
### Project_Approach
In this notebook we discuss the goal of this project and which resources have been analyzed to find a valid approach.
Finally, we propose four different ways to compute the ratings.

### Reading_files
Some challenges were found when reading the players names in Chinese. In this notebook we show the solution we found to use a uniform format. The final logic to parse the files and format them correctly can be found at the file io_utils.py inside the src folder.

The final chinese names are the same as the original ones but in readable format for those who cannot read Chinese characters.

### EDA
Notebook to explore the training dataset, to do some formatting/cleaning and to highlight some findings in the data. For instance regarding game results and players.

Read the summary to find out the ideas and conclusions.

### Analyzing_year_ratings
The computed predictions are based on the ratings of the players, so it makes sense that we analyze how well these ratings are after processing all the training data.

We have as reference the elo classic ratings from 2020 of the top 200 players. These reference ratings are compared with the computed ones reaching some interesting conclusions.


### Elo_Predictor_Evaluation
We used some evaluation data (that we skipped during training) to check how well we can predict the results of those games.
The four proposed predictors with four different ways of computing ratings are evaluated and one final approach is chosen as the best one. 



## Src
Folder with the python files used for the project. The main script though is under the project folder with the name *main.py*.
- io_utils: several functions to read and to write files plus formatting logic.
- elo_ratings: class to wrap the functionality of the elo rating system plus the updating rules by FIDE and state-of-the-art guidelines.
- player: class to model the player with all the game metrics.
- predictor: parent class for all predictors.
- elo_predictor: predictor implemented following the Elo system using the Elo ratings data.
- find_opt_seed: final quick check to confirm the hypothesis of the best value for the initial rating of unrated players.

# Predictor Setup
## Preparing the python environment
Please create your own virtual environment and install the dependencies in requirements.txt

## Parsing new training data
Remove old json training data from the train folder and copy the new json files within the same location.
The optional parameter "e" allows to keep part of the training data for the evaluation of the predictor.
We need to put some dummy version "v0", because we do not want the version parameter to be optional for the other actions.
From the command line inside the project folder type to keep some data for evaluation:

$ python main.py get_data v0 -e True

Or just to use all training data:

$ python main.py get_data v0

To generate the training dataset inside the data/io folder.

## Compute ratings
Previous steps:
1. Parsing of the training data (follow the 'Parsing new training data' chapter)
2. Remove any previous rating files from the years we want to compute at the data/ratings folder.

After these steps, we can compute the ratings that will be used for the predictor.
The parameter "v" is used to indicate the ratings version that we will use to predict probabilities.
Right now there are three predictors:
- v1 predictor that uses separate ratings for classic and rapid and updates ratings following FIDE rules.
- v2 predictor that is the same as v1 but incorporates the hill-climbing algorithm for updating ratings.
- v3 predictor that uses just one rating per player, no matter which game type.
- v4 predictor that is the same as v3 but incorporates the hill-climbing algorithm for updating ratings.

The optional parameter "e" is used to indicate with training dataset to use:
- the full train dataset
- the train dataset without the evaluation data

For the full train dataset and just one rating per player (we can choose for v3 or v4):
$ python main.py compute_ratings v3
$ python main.py compute_ratings v4 

For the full train dataset and two ratings per player (we can choose for v1 or v2):
$ python main.py compute_ratings v1
$ python main.py compute_ratings v2

For the reduced train dataset and just one rating per player:
$ python main.py compute_ratings v3_val -e True
$ python main.py compute_ratings v4_val -e True

For the reduced train dataset and two ratings per player:
$python main.py compute_ratings v1_val -e True
$python main.py compute_ratings v2_val -e True

After the execution of this script, the ratings dictionaries will be saved into the data/ratings folder.

# Evaluating the Predictor
Part of the training dataset was removed from the training to check how well the predictor can guess the result of those games and this way to have an idea of how well this approach can predict a game.
A pickle file with the predictions data of the predictor will be saved at the data/predictions folder.

The script to evaluate one predictor is:
$python main.py eval_predictor <version> 

where version can be v1_val, v2_val, v3_val or v4_val.

# Generating results for the test data
At the data/test folder should be the json files without the result field. 
We need to specify the version of the approach that will be used to generate the results, in our case v4.

$python main.py predict_test_games v4

