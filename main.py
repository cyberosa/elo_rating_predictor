import argparse
import sys
from src.elo_predictor import *
from src.elo_ratings import *
from src.find_opt_seed import *

if __name__ == '__main__':
	try:
		# parsing arguments of the main script
		parser = argparse.ArgumentParser(description="Chess winner predictor")
		# add arguments to the parser
		parser.add_argument("action", help='valid actions: [get_data, compute_ratings, '
										   'eval_predictor, predict_test_games]')
		parser.add_argument("version", help='the version of the ratings for the predictor: [v1, v2, v4]')
		parser.add_argument('-e', "--evaluation", help='use evaluation dataset for the predictor')
		args = parser.parse_args()
		action = args.action
		version = args.version
		if action is None or version is None:
			print("Please include the mandatory parameters")
			parser.print_help()
			sys.exit(1)

		print(f"Action = {action}")
		if version and version =='v0':
			print("Ignoring version")
		else:
			print(f"Ratings version: {version}")
		print(f"Evaluation dataset mode: {args.evaluation}")
	except Exception as e:
		parser.print_help()
		print("Error parsing the script parameters")
		sys.exit(1)

	try:
		# TODO Add logging parameters into a yaml file
		logging.basicConfig(filename='project.log', format='%(asctime)s %(levelname)-8s '
														   '[%(filename)s:%(lineno)d] %(message)s',
							level=logging.DEBUG)
		logger = logging.getLogger('project_logger')
		full = not args.evaluation
		if action == "get_data":
			logger.info("Parsing training data. Ignoring version.")
			success = get_training_dataset(full)
			logger.debug(f"Result of the process= {success}")

		elif action == 'compute_ratings':
			logger.debug(f"Computing separate ratings for version {version}")
			# read optional parameter eval
			train_df = read_train_dataset(full)

			# read initial ratings
			# TODO add a yaml parameter for the ini_ratings file
			players_list = prepare_ini_players("rating_2014.txt", train_df)

			# Generate separate ratings
			generate_ratings(players_list, train_df, version, export=True)

		elif action == 'eval_predictor':
			# read evaluation json file
			eval_df = read_evaluation_files()

			# create predictor
			logger.info(f"Creating the Elo predictor for version {version}")
			elo_predictor = EloPredictor(version)

			# evaluate the predictor
			accuracy, _ = elo_predictor.evaluate_predictor(eval_df)
			logger.info(f"After evaluating the predictor we achieved a {accuracy} accuracy")

		elif action == 'predict_test_games':
			# create predictor
			logger.info(f"Creating the Elo predictor for version {version}")
			elo_predictor = EloPredictor(version)

			# generate results for test games
			elo_predictor.predict_games("./data/test/", "./data/test/")

		elif action == 'find_optimal_seed':
			find_opt_seed()
		else:
			logger.error("Action not recognized. Please enter a valid action")
	except Exception as e:
		logger.error(f"Error at the main script.Reason={e}")
