from src.io_utils import *
from src.predictor import Predictor
from src.elo_ratings import check_version
from datetime import datetime
import pandas as pd
import logging
import math

logger = logging.getLogger(__name__)

def check_player_rating(player_name, players_pool, year_ratings, game_type, two_ratings):
	'''
	It checks if the predictor has rating information for the given player and it results the data
	:param player_name: player name
	:param players_pool: the pool with all players names available
	:param year_ratings: the year ratings information
	:param game_type: the type of game
	:param two_ratings: True if we need a different rating depending on the game type
	:return:
	'''
	if player_name in players_pool:
		ratings = year_ratings[player_name]
		if two_ratings:
			# return the right rating position 0 is classic, position 1 is rapid
			if game_type == 'rapid':
				return ratings[1]
			return ratings[0]
		return ratings # only one rating

	logger.info(f"No rating information for {player_name}, giving average rating of 1000")
	return 1000

def check_player_win_prob(player_name, players_pool, c_stats, r_stats, game_type, two_ratings):
	'''
	Function to compute the probability to win a game based only in winning statistics collected for the player
	:param player_name: player
	:param players_pool: list of player names available
	:param c_stats: the statistics collected for classic games
	:param r_stats: the statistics collected for rapid games
	:param game_type: the type of game classic or rapid
	:param two_ratings: True if two ratings have been used per player
	:return: the winning probability based on statistics
	'''
	stats = None
	if not(c_stats and r_stats):
		# no information at the dictionaries
		return 0.5

	if player_name in players_pool:
		if two_ratings:
			# return the right rating position 0 is classic, position 1 is rapid
			if game_type == 'rapid':
				stats = r_stats[player_name]
			else:
				stats = c_stats[player_name]
		else:
			stats = c_stats[player_name]

	if stats and stats[1] > 0:
		# list of wins and games
		wins = stats[0]
		games = stats[1]
		return wins/games

	logger.warning(f"No information from player {player_name}")
	return 0.5 # no info

def get_year_ratings(year, rapid_ratings, ratings_version, stats=False):
	logger.debug(f"Searching for ratings in year {year} with rapid_ratings {rapid_ratings}")
	try:
		ratings_file = 'ratings_' + str(year) + '.pickle'
		folder = "./data/ratings/" + ratings_version +"/"
		# TODO yaml config file with data path
		players_list = pd.read_pickle(folder + ratings_file)
		players = pd.DataFrame()
		for player in players_list:
			player_df = pd.DataFrame([player])
			players = pd.concat([players, player_df], ignore_index=True)

		logger.debug("Ratings information loaded successfully")
		r_stats_dict = None
		c_stats_dict = None
		if stats:
			if rapid_ratings:
				r_stats_dict = dict(zip(players.name, list(zip(players.rapid_wins, players.rapid_games))))
				c_stats_dict = dict(zip(players.name, list(zip(players.classic_wins, players.classic_games))))
			else:
				r_stats_dict = dict()
				c_stats_dict = dict(zip(players.name, list(zip(players.wins, players.nr_games))))
		if rapid_ratings: # two ratings
			return dict(zip(players.name, list(zip(players.rating, players.rapid_rating)))), c_stats_dict, r_stats_dict
		return dict(zip(players.name, players.rating)), c_stats_dict,  r_stats_dict
	except Exception as e:
		logger.error("Error while reading the pickle ratings file")
		logger.error(f"Reason {e}")
		return None

def compute_probability(elo_p, game_type):
	'''
	It returns the predicted result based on the winning probability of white player
	:param elo_p: winning probability of white player based on the elo ratings difference
	:param game_type: type of game classic or rapic
	:return: 0.5 for draw, 1.0 for white and 0.0 for black
	'''
	draw = 0.5
	if game_type == 'classic':
		# 44% of cases are draw so the range needs to be wider
		w_threshold = 0.65
		high_draw_prob = (elo_p >= 0.40 and elo_p <= w_threshold)

	else:
		# 36% are the white player the winner
		w_threshold = 0.55
		high_draw_prob = (elo_p >= 0.45 and elo_p < w_threshold)

	if high_draw_prob:
		return draw

	if elo_p >= w_threshold:
		return 1.0
	return 0.0

def get_factor(r):
	if r >= 2000 and r <= 2350:
		return 100
	if r > 2450 and r <= 2550:
		return -100
	if r > 2550:
		return -200
	return 0 # no correction

def correction_factor(white_rating, black_rating):
	return white_rating + get_factor(white_rating), black_rating + get_factor(black_rating)

class EloPredictor(Predictor):
	def __init__(self, ratings_version):
		super().__init__("Elo Predictor")
		self.rapid_ratings, _ = check_version(ratings_version)
		self.ratings_version = ratings_version
		# getting all available years from the available info
		self.avlb_years = get_available_rating_years_info(ratings_version)
		logger.debug(f"Available years {self.avlb_years}")
		self.found_ratings = dict()
		self.found_c_stats = dict()
		self.found_r_stats = dict()
		self.initialize_all_ratings()

	def initialize_all_ratings(self):
		logger.info("Initializing Elo predictor")
		for game_year in self.avlb_years:
			# get the ratings
			year_ratings, c_stats, r_stats = get_year_ratings(game_year, self.rapid_ratings,
															  self.ratings_version, stats=True)

			logger.info("Adding year information to the list of available ratings")
			self.found_ratings[game_year] = year_ratings
			self.found_c_stats[game_year] = c_stats
			self.found_r_stats[game_year] = r_stats

	def evaluate_predictor(self, evaluation_df):
		'''
		Function to generate predictions where we know the results and get an idea of the accuracy of the predictions
		:param evaluation_df: the dataframe with the games to predict and the results
		:return: a metric of the accuracy for the predictor. A report is also generated.
		'''
		total_games = len(evaluation_df)
		print(evaluation_df.head())
		logger.info(f"Evaluating the predictor for {total_games} games")
		evaluation_df = evaluation_df.sort_values(by='game_date')

		predictions = pd.DataFrame()
		# for each game, predict the result
		for row in evaluation_df.itertuples():
			dict_row = row._asdict()
			game_year = dict_row['game_year']
			game_type = dict_row['time_control']
			pred, elo_p, white_prob, black_prob = self.compute_prediction_data(game_year,
																			   dict_row['white'],
																			   dict_row['black'],
																			   game_type)

			tmp = {'game_date': row.game_date,
				   'probability': elo_p,
				   'white_prob': white_prob,
				   'black_prob': black_prob,
				   'predicted': pred,
				   'actual': dict_row['result'],
				   'time_control': game_type}
			predictions = predictions.append(tmp, ignore_index=True)

		predictions['correct'] = predictions.predicted == predictions.actual
		correct_predictions = predictions.correct.sum()
		logger.info(f"Number of correct predictions = {correct_predictions} from {total_games}")
		accuracy = (correct_predictions * 100) / total_games
		logger.info(f"Accuracy = {accuracy}")
		predictions.to_pickle("./data/predictions/predictor_"+self.ratings_version)
		return accuracy, correct_predictions

	def compute_prediction_data(self, game_year, white_name, black_name, game_type):
		while str(game_year) not in self.avlb_years:
			logger.debug("Searching for a previous year information")
			game_year = game_year - 1
		if str(game_year) in self.avlb_years:
			year_ratings = self.found_ratings[str(game_year)]
			c_stats = self.found_c_stats[str(game_year)]
			r_stats = self.found_r_stats[str(game_year)]
		else:
			logger.error(f"No ratings information available for {game_year}")
			return 0

		players_pool = list(year_ratings.keys())
		logger.debug(f"Total number of players = {len(players_pool)}")
		white_rating = check_player_rating(white_name, players_pool,
										   year_ratings, game_type, self.rapid_ratings)
		black_rating = check_player_rating(black_name, players_pool,
										   year_ratings, game_type, self.rapid_ratings)

		#white_rating, black_rating = correction_factor(white_rating, black_rating)
		elo_rating_diff = white_rating - black_rating
		logger.debug(f"Elo ratings difference = {elo_rating_diff}")
		d = math.pow(10, -elo_rating_diff / 400)
		elo_p = 1 / (d + 1)

		white_prob = check_player_win_prob(white_name, players_pool, c_stats, r_stats, game_type,
										   self.rapid_ratings)
		black_prob = check_player_win_prob(black_name, players_pool, c_stats, r_stats, game_type,
										   self.rapid_ratings)
		pred = compute_probability(elo_p, game_type)
		return pred, elo_p, white_prob, black_prob

	def get_prediction(self, white_player, black_player, game_date, game_type):
		if isinstance(game_date, str):
			game_date = datetime.strptime(game_date, '%Y-%m-%d')
			game_year = game_date.year
		else:
			# game date should be of timestamp class
			game_year = game_date.dt.year
		pred, elo_p, white_prob, black_prob = self.compute_prediction_data(game_year, white_player,
																		   black_player, game_type)
		return pred
