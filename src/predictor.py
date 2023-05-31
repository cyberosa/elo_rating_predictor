from src.io_utils import *

logger = logging.getLogger(__name__)

class Predictor:
	def __init__(self, name):
		self.name = name

	def get_prediction(self, white_player, black_player, game_date, game_type):
		logger.info("Parent class. Method to be implemented by each children")
		pass

	def evaluate_predictor(self, evaluation_df):
		logger.info("Parent class. Method to be implemented by each children")
		pass

	def predict_games(self, test_folder, results_folder):
		'''
		It predicts the results for the games included in the test folder and it saves the results in json format
		at the results folder.
		:param test_folder: input folder
		:param results_folder: output folder
		:return:
		'''
		files = os.listdir(test_folder)
		for file in files:
			if not file.endswith('.json'):
				logger.info(f"Ignoring file {file}")
				continue
			full_path = test_folder + file
			logger.info(f"Reading file {full_path}")
			m = magic.Magic(mime_encoding=True)
			with open(full_path, "rb") as read_it:
				blob = open(full_path, 'rb').read()
				encoding = m.from_buffer(blob)
				logger.debug(f"Encoding of the file {encoding}")
				raw = json.load(read_it)
				data = pd.json_normalize(raw)
				filename = data['name'].values[0]
				nr_tour = data['tours'].values[0]
				game_type = data['time_control'].values[0]
				prefix = 'games.tour_'
				logger.info("Generating predictions for the different tournaments")
				games = dict()
				for i in range(1, nr_tour+1):
					column_name = prefix + str(i)
					games_dict_list = list()
					for d in data[column_name][0]:
						white_player = build_name(d['white'], encoding == 'utf-8')
						d['white'] = white_player
						black_player = build_name(d['black'], encoding == 'utf-8')
						d['black'] = black_player
						game_date = d['date']
						result = self.get_prediction(white_player, black_player, game_date, game_type)
						d['result'] = result
						games_dict_list.append(d)
					games['tour_'+str(i)] = games_dict_list

				read_it.close()
			json_dict = dict()
			json_dict['name'] = filename
			json_dict['start_date'] = data['start_date'].values[0]
			json_dict['end_date'] = data['end_date'].values[0]
			json_dict['games'] = games
			json_dict['tours'] = str(nr_tour)
			json_dict['time_control'] = game_type

			logging.info(f"Generating results file {results_folder+file}")
			with open(results_folder+file, "w") as fp:
				json.dump(json_dict, fp, ensure_ascii=False, indent=4)
				fp.close()
