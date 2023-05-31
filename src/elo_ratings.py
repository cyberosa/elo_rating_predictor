import math
import logging
import pickle
import json
from src.player import Player

logger = logging.getLogger(__name__)

def check_version(ratings_version):
	'''
	Function to check the version of the predictor and to return two flags:
	-- separate_ratings : True if two ratings are used
	-- balanced: True if the Hill-Climb algorithm is used for updating
	:param ratings_version: the version to check
	:return: the two flags
	'''
	if (ratings_version == 'v1') or (ratings_version == 'v1_val'):
		return True, False
	if (ratings_version == 'v2') or (ratings_version == 'v2_val'):
		return True, True
	if (ratings_version == 'v3') or (ratings_version == 'v3_val'):
		return False, False
	if (ratings_version == 'v4') or (ratings_version == 'v4_val'):
		return False, True

def compute_estimate(rating_w, rating_b):
	'''
	Function to compute the probability for player a and for player b to win
	:param rating_w: elo rating for player white
	:param rating_b: elo rating for player b
	:return: the estimates for w and b
	'''
	q_w = math.pow(10, rating_w/400)
	q_b = math.pow(10, rating_b/400)

	e_w = q_w / (q_w + q_b)
	e_b = q_b / (q_w + q_b)
	return e_w, e_b

def compute_k_factor(rating_w, rating_b, game_type, games_w, games_b):
	'''
	K = 20 for RAPID and BLITZ ratings all players.
	K = 10 for a top player with rating >= 2400
	K = 40 for a player new to the rating list until he has completed events with at least 30 games
	K = 20 as long as a player's rating remains under 2400.

	:param rating_w: rating of player w
	:param rating_b: rating of player b
	:param game_type: the type of game they played
	:param games_w: the number of games player w played
	:param games_b: the number of games player b played
	:return:
	'''
	if game_type == 'rapid':
		return 20, 20
	k_w = -1
	k_b = -1
	if rating_w >= 2400:
		k_w = 10
	if rating_b >= 2400:
		k_b = 10
	if k_w == -1 and games_w < 30:
		k_w = 40
	if k_b == -1 and games_b < 30:
		k_b = 40
	if k_w == -1:
		k_w = 20 # rating has to be under 2400
	if k_b == -1:
		k_b = 20
	return k_w, k_b

def get_scores(result):
	'''
	Result = 0.5 -> draw
	Result = 1 -> player w (white) wins
	Result = 0 -> player b (black) wins
	:param result:
	:return:
	'''
	if result == 0.5:
		return 0.5, 0.5
	if result == 1.0:
		return 1.0, 0.0
	return 0.0, 1.0

def check_new_ratings(w_player, b_player, e_w, e_b, k_w, k_b, score_w, score_b, rapid_game, balanced):
	'''
	It checks if the players have provisional ratings and updates the new ratings for both players
	:param w_player: name of white player
	:param b_player: name of black player
	:param e_w: estimated score for white player
	:param e_b: estimated score for black player
	:param k_w: k factor for white player
	:param k_b: k factor for black player
	:param score_w: actual score for white player
	:param score_b: actual score for black player
	:param rapid_game: True if the game is rapid and we use separate ratings
	:param balanced: if True the hill-climbing approach is used to weight the new rating
	:return:
	'''
	# if white has provisional rating but black not --> only update the rating of the provisional
	w_prov_rating = w_player.get_flag_prov_rating(rapid_game)
	b_prov_rating = b_player.get_flag_prov_rating(rapid_game)
	if w_prov_rating:
		w_player.compute_prov_rating(rapid_game)

	# if white has provisional rating but black not --> only update the rating of the provisional
	if b_prov_rating:
		b_player.compute_prov_rating(rapid_game)

	# if both players have ratings that we can trust --> update ratings following elo system
	if (not(w_prov_rating) and not(b_prov_rating)):
		w_rating = w_player.get_rating(rapid_game)
		new_rating_w = w_rating + k_w * (score_w - e_w)

		if balanced:
			avg_opp_rating = w_player.get_avg_opponents_ratings(rapid_game)
			new_rating_w = max(new_rating_w, avg_opp_rating)
		if new_rating_w > 0:
			w_player.set_rating(round(new_rating_w), rapid_game)

		b_rating = b_player.get_rating(rapid_game)
		new_rating_b = b_rating + k_b * (score_b - e_b)

		if balanced:
			avg_opp_rating = b_player.get_avg_opponents_ratings(rapid_game)
			new_rating_b = max(new_rating_b, avg_opp_rating)
		if new_rating_b > 0:
			b_player.set_rating(round(new_rating_b), rapid_game)

		if new_rating_w < 0 or new_rating_b < 0:
			logger.warning("Negative rating reached. No change")
			# just keep the previous value. Alternative: mean tournament rating


'''
Class to encapsulate the logic of the Elo rating system
https://en.wikipedia.org/wiki/Elo_rating_system
@author: A. Rosa Castillo
'''
class EloRatings:
	def __init__(self, players_list, first_date, last_date):
		self.players = players_list
		self.first_date = first_date
		self.last_date = last_date

	def get_player(self, name):
		for player in self.players:
			# player is of Player class
			if player == name:
				return player
		logger.warning(f"Player not found in the list of players. Adding to the list with default ratings")
		new_player = Player(name, 1000, 1000, True, True) # provisional rating
		self.players.append(new_player)
		return new_player

	def process_game(self, white_p, black_p, result, game_type, ratings_version):
		separate_ratings, balanced = check_version(ratings_version)
		w_player = self.get_player(white_p)
		b_player = self.get_player(black_p)

		# provisional ratings?
		rapid_ratings = (game_type == 'rapid') and separate_ratings
		w_player.check_prov_rating(rapid_ratings)
		b_player.check_prov_rating(rapid_ratings)

		# get ratings of both players
		b_player.add_opponent_rating(w_player.rating, rapid_ratings)
		w_player.add_opponent_rating(b_player.rating, rapid_ratings)

		# update nr of games for both players
		w_player.add_game(rapid_ratings)
		b_player.add_game(rapid_ratings)

		# get estimates for both players
		w_rating = w_player.get_rating(rapid_ratings)
		b_rating = b_player.get_rating(rapid_ratings)
		e_w, e_b = compute_estimate(w_rating, b_rating)

		# get k factors for each player
		games_w = w_player.get_nr_games(rapid_ratings)
		games_b = b_player.get_nr_games(rapid_ratings)
		k_w, k_b = compute_k_factor(w_rating, b_rating, game_type, games_w, games_b)

		# get scores for each player
		score_w, score_b = get_scores(result)
		if score_w == 1.0:
			w_player.add_win(rapid_ratings)
			b_player.add_loss(rapid_ratings)
		if score_b == 1.0:
			b_player.add_win(rapid_ratings)
			w_player.add_loss(rapid_ratings)

		# updating ratings
		check_new_ratings(w_player, b_player, e_w, e_b, k_w, k_b, score_w, score_b, rapid_ratings, balanced)

	def get_players(self, separate_ratings, as_dicts=False):
		if as_dicts:
			players_dict_list = list()
			for player in self.players:
				players_dict_list.append(player.to_dict(separate_ratings))
			return players_dict_list
		return self.players

	def export_ratings(self, ratings_version, file='json'):
		logger.info(f"Exporting ratings in {file} format")
		separate_ratings, balanced = check_version(ratings_version)
		players_dict_list = self.get_players(separate_ratings, as_dicts=True)
		json_dict = dict()
		json_dict['players'] = players_dict_list
		json_dict['first_date'] = str(self.first_date)
		json_dict['last_date'] = str(self.last_date)
		json_dict['nr_players'] = len(players_dict_list)
		last_year = self.last_date.year
		if file == 'json':
			folder = './data/ratings/'+ratings_version+"/"
			with open(folder+"ratings_"+str(last_year)+".json", "w") as fp:
				json.dump(json_dict, fp, ensure_ascii=False)
				fp.close()
		else:
			logger.error("Other formats not implemented yet")

def update_ratings(players_list, first_date, year_data, ratings_version):
	'''
	Based on all games from the year, update the ratings of players depending on results
	:param players_list: the initial list of players rated and provisionally rated
	:param first_date: first date of historical data
	:param year_data: the games data of a year
	:param ratings_version: version of the ratings to use [v1, v2 ,v3, v4]
	:return: the elo ratings class
	'''
	try:
		logger.info("Updating elo ratings")
		last_date = max(year_data.game_date)
		# initialize the class with the data we have
		elo_ratings = EloRatings(players_list, first_date, last_date)
		total_games = len(year_data)
		logger.debug(f"Processing {total_games} total games")
		for	row in year_data.itertuples():
			dict_row = row._asdict()
			white_p = dict_row['white']
			black_p = dict_row['black']
			result = dict_row['result']
			game_type = dict_row['time_control']
			elo_ratings.process_game(white_p, black_p, result, game_type, ratings_version)
		return elo_ratings
	except Exception as e:
		logger.error(f"Error while updating ratings. Reason: {e}")
		return None

def generate_ratings(players_list, games_data, ratings_version, export=False):
	'''
	Function to generate the year ratings dictionaries for all years covered with the games dataset.
	The year dictionaries with the ratings will be saved into the data/ratings folder
	:param players_list: the initial list of players rated and provisionally rated
	:param games_data: data with the registered games and results to generate new ratings
	:param ratings_version: version of the ratings to use [v1, v2 ,v4, v4]
	:param export: True if we want to generate json ratings data files
	:return: True if the generation process was successful
	'''
	try:
		logger.info(f"Generating ratings from the games data, predictor version={ratings_version}")
		# data should be sorted by game_date but we will use the year field to collect yearly data
		min_year = min(games_data['game_year'])
		max_year = max(games_data['game_year'])
		prev_list = players_list
		first_date = min(games_data.game_date)
		separate_ratings, balanced = check_version(ratings_version)
		logger.debug(f"separate_ratings = {separate_ratings} and balanced {balanced}")
		for year in range(min_year, max_year+1):
			logger.debug(f"Processing data from year {year}")
			year_data = games_data.loc[games_data['game_year'] == year]
			elo_ratings = update_ratings(prev_list, first_date, year_data, ratings_version)
			if elo_ratings is None:
				logger.error(f"Error while processing games from {year}. Skipping")
				continue

			if export:
				elo_ratings.export_ratings(ratings_version)

			# save player as dictionary to pickle file
			folder = './data/ratings/'+ratings_version+"/"
			with open(folder+"ratings_"+ str(year)+".pickle", "wb") as file:
				pickle.dump(elo_ratings.get_players(separate_ratings, as_dicts=True), file)
				file.close()
			prev_list = elo_ratings.get_players(separate_ratings)
		return True
	except Exception as e:
		logger.error(f"Error while generating the ratings. Reason:{e}")
		return False
