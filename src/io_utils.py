import json
import pandas as pd
from unidecode import unidecode
import magic
import os
import logging
from src.player import Player

logger = logging.getLogger(__name__)

def check_chinese_characters(name):
	'''
	Special function needed to translate all chinese characters within the same str variable.
	:param name: the name to translate
	:return: the translated name
	'''
	characters = []
	for a in name:
		characters.append(a)
	# special case not translating well 3 chinese characters
	if len(characters) != 3:
		return unidecode(name)
	# extract individual characters
	chinese_name = " ".join(characters)
	new_name = unidecode(chinese_name)
	# remove any extra spaces
	new_name = new_name.replace('  ', ' ')
	new_name = new_name.rstrip()
	new_name = new_name.lstrip()
	return new_name

def fix_encoding_error(name):
	# special error detected with the um_laut character where ue is replaced by v instead of u
	# there is no names in Chinese with v such as Lv so we need to fix it
	if 'v' in name:
		return name.replace('v', 'u')
	return name

def build_name(x, utf_8=False):
	'''
	Auxiliary function to build the player's name removing commas and under the same ascii encoding
	:param x: the name of the player as a string
	:param utf_8: True if Utf-8 encodings are used
	:return: the clean player's name in Ascii
	'''
	# remove additional whitespaces at the end of the string or at the beginning
	x = x.rstrip()
	x = x.lstrip()
	# remove commas
	x = x.replace(",","")
	if utf_8:
		full_name = check_chinese_characters(x)
	else:
		full_name = x
	words = full_name.split(" ")
	surname = words[0]

	if len(words) == 3:
		name = words[1] + words[2].lower()
		new_name = surname + ' ' + name
		return fix_encoding_error(new_name)

	new_name = surname + ' ' + words[1]
	return fix_encoding_error(new_name)

def build_dataframe(tour_data, utf_8=False):
	'''
	Function to build a dataframe from the parsed json data
	:param tour_data: the json parsed data
	:param utf_8: True if the used encoding is Utf-8
	:return: the dataframe with the formatted data and traslated names.
	'''
	final_df = pd.DataFrame()
	nr_tour = tour_data['tours'].values[0]
	prefix = 'games.tour_'
	for i in range(1, nr_tour):
		column_name = prefix + str(i)
		logger.debug("Extracting games from "+column_name)
		temp = tour_data.explode(column_name)
		temp = temp[['start_date', 'end_date', 'time_control', column_name]]
		temp.rename(columns={column_name: 'games'}, inplace=True)
		final = pd.concat([temp.drop(['games'], axis=1), temp['games'].apply(pd.Series)], axis=1)
		final['white'] = final['white'].apply(lambda x: build_name(x, utf_8))
		final['black'] = final['black'].apply(lambda x: build_name(x, utf_8))
		final_df = pd.concat([final_df, final])
	return final_df

def parse_files(folder):
	'''
	Function to return the final dataframe after parsing the games data from the given folder
	:param folder: folder containing the json files
	:return: the parsed data as a dataframe
	'''
	files = os.listdir(folder)
	final_dataset = pd.DataFrame()
	for file in files:
		if not file.endswith('.json'):
			logger.info(f"Ignoring file {file}")
			continue
		full_path = folder + file
		logger.info(f"Reading file {full_path}")
		m = magic.Magic(mime_encoding=True)
		with open(full_path, "rb") as read_it:
			blob = open(full_path, 'rb').read()
			encoding = m.from_buffer(blob)
			raw = json.load(read_it)
			data = pd.json_normalize(raw)
			file_df = build_dataframe(data, encoding == 'utf-8')
			final_dataset = pd.concat([final_dataset, file_df])
	return final_dataset

def get_training_dataset(full=False):
	'''
	Function to generate the training dataset from parsing the training json files
	:param full: if True we take the full training dataset, if False we skip some training data
	:return: the training dataset
	'''

	try:
		# TODO Add the data path as a yaml configuration parameter
		train_folder = "./data/train/"
		final_dataset = parse_files(train_folder)

		logger.info("Finished processing all training files")
		logger.debug(final_dataset.info())

		# TODO Add a yaml parameter for the split-date to slip the train dataset
		final_dataset['date'] = pd.to_datetime(final_dataset['date'], format='%Y-%m-%d')
		final_dataset['game_year'] = final_dataset['date'].dt.year
		if full:
			final_dataset.to_pickle("./data/io/full_train_df")
			return True

		logger.info("Splitting some training data for evaluation")
		eval_dataset = final_dataset.loc[final_dataset['date'] >= '2020-01-01']
		final_dataset = final_dataset.loc[final_dataset['date'] < '2020-01-01']

		logger.debug("Saving training data into the data/io folder")
		# TODO add a yaml parameter for the path
		final_dataset.to_pickle("./data/io/train_df")
		eval_dataset.to_pickle("./data/io/eval_df")
		return True
	except Exception as e:
		logger.error(f"Error while processing the training data. Reason: {e}")
		return False


def standard_clean(data, no_drop=False):
	'''
	Function to clean the data removing columns and formatting date and category columns
	:param data: the dataframe
	:param no_drop: if we do not want to drop any columns
	:return: the clean dataframe
	'''
	if not no_drop:
		data.drop(['start_date', 'end_date'], inplace=True, axis=1)
	data['date'] = pd.to_datetime(data['date'], format='%Y-%m-%d')
	data.rename(columns={'date': 'game_date'}, inplace=True)
	data['game_year'] = data['game_date'].dt.year
	data = data.sort_values(by='game_date')
	data['white'] = data['white'].astype("category")
	data['black'] = data['black'].astype("category")
	return data

def read_train_dataset(full=False):
	'''
	Function to read the raw generated training dataset and format/clean it
	:param full: if True we take the full training dataset, if False the one without the evaluation dataset
	:return: the clean and formatted dataset
	'''
	# TODO add a yaml parameter for the path
	logger.info(f"Cleaning and preparing training dataset. Full train dataset:{full}")
	if full:
		training_df = pd.read_pickle("./data/io/full_train_df")
	else:
		training_df = pd.read_pickle("./data/io/train_df")

	return standard_clean(training_df)

def get_classic_ratings(filename):
	'''
	Function to read a ratings filename and return the dictionary with the parsed ratings
	:param filename: the name of the txt file in the data folder
	:return: the dictionary where key= player's name and value= rating
	'''
	logger.info("Getting the initial ratings from the data/io folder")
	ratings = dict()
	try:
		# TODO add a yaml parameter for the data path
		with open('./data/io/'+filename) as f:
			for line in f.readlines():
				line = line.rstrip()
				line = line.lstrip()
				# remove commas
				line = line.replace(",", "")
				line = line.replace('\t', ' ')
				words = line.split(" ")
				name = words[0] + ' ' + words[1]
				rating = words[2]
				ratings[name] = int(rating)
	except Exception as e:
		print(e)
	finally:
		f.close()
	return ratings

def prepare_ini_players(filename, games_data):
	'''
	It returns the total list of initial players before parsing any game results
	:param filename: the file with some initial classic ratings for players.
	:param games_data: the games information with the players and games.
	:return:
	'''
	logger.info("Preparing initial ratings")
	ratings_dict = get_classic_ratings(filename)
	players_pool = list(games_data['white'].unique())
	players_pool.extend(list(games_data['black'].unique()))
	players_pool = list(set(players_pool))
	rated_players = list(ratings_dict.keys())
	total_players = list()
	for player in players_pool:
		if player in rated_players:
			# default rapid rating is smaller for a top classic player
			classic_rating = ratings_dict[player]
			new_player = Player(player, classic_rating, classic_rating-200, False, True)
		else: # no info, default 1000
			# TODO Add a yaml parameter for the default Elo rating
			new_player = Player(player, 1000, 1000, True, True)
		total_players.append(new_player)
	logger.debug(f"Total number of players = {len(total_players)}")
	return total_players

def read_evaluation_files(io=False):
	'''
	Function to read evaluation data for the predictor
	:param io: True if we will use already saved evaluation data at the io folder
	:return: the cleaned dataframe with the evaluation data
	'''
	try:
		if io:
			eval_dataset = pd.read_pickle("./data/io/eval_df")
		else:
			# TODO Add the data path as a yaml configuration parameter
			eval_folder = "./data/eval/"
			eval_dataset = parse_files(eval_folder)
		return standard_clean(eval_dataset)
	except Exception as e:
		logger.error(f"Error while reading evaluation data")
		return None

def get_available_rating_years_info(ratings_version):
	'''
	It checks the ratings folder for the predictor version finding all available data in pickle files.
	:param ratings_version: the version of the predictor to check
	:return: the list of years with ratings information
	'''
	files = os.listdir('./data/ratings/'+ratings_version+"/")
	available_years = list()
	for file in files:
		if not file.endswith('.pickle'):
			logger.info(f"Ignoring file {file}")
			continue
		parts = file.split(".")
		year = parts[0][-4:]
		available_years.append(year)
	return available_years
