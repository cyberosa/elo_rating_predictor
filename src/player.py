import logging

logger = logging.getLogger(__name__)

'''
Player class to keep all games information from a player
including win, loss, and opponent ratings metrics
@author: A. Rosa Castillo
'''
class Player:
	def __init__(self, name, rating, rapid_rating, c_prov_rating, r_prov_rating):
		self.name = name
		self.rating = rating
		self.r_rating = rapid_rating
		self.c_prov_rating = c_prov_rating
		self.r_prov_rating = r_prov_rating
		self.nr_c_games = 0
		self.nr_r_games = 0
		self.c_wins = 0
		self.r_wins = 0
		self.c_losses = 0
		self.r_losses = 0
		self.c_opponent_ratings = []
		self.r_opponent_ratings = []

	def set_rating(self, rating, rapid_game):
		if rapid_game:
			self.r_rating = rating
		else:
			self.rating = rating

	def get_rating(self, rapid_game):
		if rapid_game:
			return self.r_rating
		return self.rating

	def get_flag_prov_rating(self, rapid_game):
		if rapid_game:
			return self.r_prov_rating
		return self.c_prov_rating

	def set_flag_prov_rating(self, state, rapid_game):
		if rapid_game:
			self.r_prov_rating = state
		else:
			self.c_prov_rating = state

	def compute_prov_rating(self, rapid_game):
		nr_games = self.get_nr_games(rapid_game)
		wins = self.get_wins(rapid_game)
		losses = self.get_losses(rapid_game)
		opponent_ratings = self.get_opponent_ratings(rapid_game)

		if nr_games == 0:
			logger.error(f"Zero games played for player {self.name}")
			return

		prov_rating = round((sum(opponent_ratings) + 400 * (wins - losses)) / nr_games)

		self.set_rating(prov_rating, rapid_game)

	def check_prov_rating(self, rapid_game):
		if self.get_flag_prov_rating(rapid_game) and self.get_nr_games(rapid_game) >= 20:
			self.set_flag_prov_rating(False, rapid_game)

	def add_opponent_rating(self, o_rating, rapid_game):
		if rapid_game:
			self.r_opponent_ratings.append(o_rating)
		else:
			self.c_opponent_ratings.append(o_rating)

	def get_avg_opponents_ratings(self, rapid_game):
		if rapid_game:
			if self.nr_r_games > 0:
				return round(sum(self.r_opponent_ratings) / self.nr_r_games)

			return 0
		if self.nr_c_games > 0:
			return round(sum(self.c_opponent_ratings) / self.nr_c_games)
		return 0

	def get_opponent_ratings(self, rapid_game):
		if rapid_game:
			return self.r_opponent_ratings
		return self.c_opponent_ratings

	def get_nr_games(self, rapid_game):
		if rapid_game:
			return self.nr_r_games
		return self.nr_c_games

	def add_game(self, rapid_game):
		if rapid_game:
			self.nr_r_games += 1
		else:
			self.nr_c_games += 1

	def add_win(self, rapid_game):
		if rapid_game:
			self.r_wins += 1
		else:
			self.c_wins += 1

	def get_wins(self, rapid_game):
		if rapid_game:
			return self.r_wins
		return self.c_wins

	def get_losses(self, rapid_game):
		if rapid_game:
			return self.r_losses
		return self.c_losses

	def add_loss(self, rapid_game):
		if rapid_game:
			self.r_losses += 1
		else:
			self.c_losses += 1

	def compute_prob_to_win(self, rapid_game):
		# get all stats of the player
		wins = self.get_wins(rapid_game)

		total_games = self.get_nr_games(rapid_game)
		if total_games > 0:
			return wins/total_games
		return 0.5

	def __eq__(self, p_name):
		return self.name == p_name

	def __str__(self):
		print(f"Player name: {self.name}, classic rating: {self.rating}, rapid rating: {self.r_rating}")
		print(f"classic wins: {self.c_wins}, classic losses: {self.c_losses}, classic games: {self.nr_c_games}")
		print(f"rapid wins: {self.r_wins}, rapid losses: {self.r_losses}, rapid games: {self.nr_r_games}")

	def to_dict(self, separate_ratings):
		player = dict()
		player['name'] = self.name
		player['rating'] = self.rating
		if separate_ratings:
			player['rapid_rating'] = self.r_rating
			player['classic_games'] = self.nr_c_games
			player['rapid_games'] = self.nr_r_games
			player['rapid_wins'] = self.r_wins
			player['rapid_losses'] = self.r_losses
			player['classic_wins'] = self.c_wins
			player['classic_losses'] = self.c_losses
			player['avg_c_opp_rating'] = self.get_avg_opponents_ratings(False)
			player['avg_r_opp_rating'] = self.get_avg_opponents_ratings(True)
		else:
			player['nr_games'] = self.nr_c_games
			player['wins'] = self.c_wins
			player['losses'] = self.c_losses
			player['avg_opp_rating'] = self.get_avg_opponents_ratings(False)
		return player
