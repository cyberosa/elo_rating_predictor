from src.elo_predictor import *
from src.elo_ratings import *
import pandas as pd

logger = logging.getLogger(__name__)

def prepare_ini_players_with_seed(filename, games_data, seed):
	'''
	It returns the total list of initial players before parsing any game results
	:param filename: the file with some initial classic ratings for players.
	:param games_data: the games information with the players and games.
	:param seed: the default initial rating
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
		else:
			new_player = Player(player, seed, seed, True, True)
		total_players.append(new_player)
	logger.debug(f"Total number of players = {len(total_players)}")
	return total_players

def generate_last_ratings(players_list, games_data, return_year):
	try:
		logger.info("Generating ratings from the games data for v4")
		# data should be sorted by game_date but we will use the year field to collect yearly data
		min_year = min(games_data['game_year'])
		max_year = max(games_data['game_year'])
		prev_list = players_list
		first_date = min(games_data.game_date)
		separate_ratings = False
		balanced = True
		ratings_version = 'v4_val'
		logger.debug(f"separate_ratings = {separate_ratings} and balanced {balanced}")
		for year in range(min_year, max_year + 1):
			logger.debug(f"Processing data from year {year}")
			year_data = games_data.loc[games_data['game_year'] == year]
			elo_ratings = update_ratings(prev_list, first_date, year_data, ratings_version)
			if elo_ratings is None:
				logger.error(f"Error while processing games from {year}. Skipping")
				continue

			if year == return_year:
				found = dict()
				players_list = elo_ratings.get_players(separate_ratings, as_dicts=True)
				players = pd.DataFrame()
				for player in players_list:
					player_df = pd.DataFrame([player])
					players = pd.concat([players, player_df], ignore_index=True)
				return dict(zip(players.name, players.rating)), dict(), dict()
			prev_list = elo_ratings.get_players(separate_ratings)
		return None
	except Exception as e:
		logger.error(f"Error while generating the ratings. Reason:{e}")
		return None

def get_ref_2020_ratings():
	ref_ratings_2020 = dict()
	try:
		with open('./data/io/rating_2020.txt', encoding="utf-8") as f:
			for line in f.readlines():
				line = line.rstrip()
				line = line.lstrip()
				# remove commas
				line = line.replace(",", "")
				line = line.replace('\t', ' ')
				words = line.split(" ")
				name = words[0] + ' ' + words[1]
				if 'ü' in name:
					name = name.replace('ü', 'u')
				rating = words[2]
				ref_ratings_2020[name] = int(rating)
			f.close()
	except Exception as e:
		print(e)
	return ref_ratings_2020

def find_opt_seed():
	train_df = read_train_dataset(False)
	full_train_df = read_train_dataset(True)

	seeds = [900, 1000, 1500, 1800]
	results = pd.DataFrame(columns=['seed', 'correct_results', 'accuracy', 'correct_ratings'])
	for seed in seeds:
		logger.info("Initial players ratings")
		players_list = prepare_ini_players_with_seed("rating_2014.txt", train_df, seed)

		logger.info("Generating ratings for 2020")
		ratings_2020, c_stats, r_stats = generate_last_ratings(players_list, full_train_df, 2020)
		tmp = dict()
		tmp['seed'] = seed
		# ratings difference
		ref_ratings_2020 = get_ref_2020_ratings()
		logger.info("Dataframe with reference ratings")
		v_ratings_2020 = pd.DataFrame()
		v_ratings_2020['name'] = ref_ratings_2020.keys()
		v_ratings_2020['ref_rating'] = ref_ratings_2020.values()

		logger.info("Dataframe with computed ratings")
		players_2020 = pd.DataFrame()
		players_2020['name'] = ratings_2020.keys()
		players_2020['rating'] = ratings_2020.values()
		v_ratings_2020 = v_ratings_2020.merge(players_2020, how='left', on='name')
		v_ratings_2020['rating_diff'] = v_ratings_2020['ref_rating'] - v_ratings_2020['rating']
		right_rating = v_ratings_2020[v_ratings_2020['rating_diff'].between(-15, 15)]
		logger.info(f"Number of correct ratings {len(right_rating)}")
		tmp['correct_ratings'] = len(right_rating)


		logger.info("Generating ratings for 2019")
		ratings_2019, c_stats, r_stats = generate_last_ratings(players_list, train_df, 2019)
		if ratings_2019:
			# evaluation metrics
			eval_df = read_evaluation_files()
			logger.info(f"Creating the Elo predictor for version v4_val")
			# initialize ratings disable
			elo_predictor = EloPredictor('v4_val')
			logger.info("Adding year information to the list of available ratings")
			elo_predictor.found_ratings['2019'] = ratings_2019
			elo_predictor.found_c_stats['2019'] = c_stats
			elo_predictor.found_r_stats['2019'] = r_stats
			accuracy, correct_cases = elo_predictor.evaluate_predictor(eval_df)
			tmp['correct_results'] = correct_cases
			tmp['accuracy'] = accuracy

		print(tmp)
		results = results.append(tmp, ignore_index=True)
		print(results)
	return results