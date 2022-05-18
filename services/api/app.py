from time import time
from flask import Flask, request, jsonify, abort
from flask_cors import CORS
import os
from datetime import datetime, timedelta
from core.utils import gitlab
from core.database.functions.project import create_project
from core.database.functions.merges import create_merge, find_all_merges_by_project_id
from core.database.functions.data import add_stats
from core.database.functions.users import create_user
from core.database.functions.login import add_new_login
from core.database.functions.fetch_stats import insert_new_fetch_request, get_last_fetch_request
from core.database.functions.project_user import create_project_user, find_all_project_user_by_repo_id

from core.routes.graphs import graphs
from core.routes.users import users
from core.routes.repo import repo

app = Flask(__name__)

CORS(app)

app.config['MONGO_URI'] = os.environ['db_link']
app.register_blueprint(graphs, url_prefix='/graphs')
app.register_blueprint(users, url_prefix='/users')
app.register_blueprint(repo, url_prefix='/repo')


@app.route('/')
def welcome():
	return jsonify('API is running')

@app.route('/ladder')
def get_ladder():
	repo_id = request.args.get('repo_id')
	sorted_by = request.args.get('sorted_by')
	if not repo_id:
		print('missing user_id or repo_id')
		abort(400)
	all_projects = find_all_project_user_by_repo_id(repo_id)
	all_merges = []
	for project_user in all_projects:
		all_merges += (find_all_merges_by_project_id(project_user['project_id']))
	ladder = gitlab.count_merges(all_merges, sorted_by)
	return (jsonify(ladder))

@app.route('/ladder/month/weight')
def get_ladder_weight_by_month():
	try:
		repo_id = request.args.get('repo_id')
		if not repo_id:
			print('missing user_id or repo_id')
			abort(400)
		all_projects = find_all_project_user_by_repo_id(repo_id)
		all_merges = []
		for project_user in all_projects:
			all_merges += (find_all_merges_by_project_id(project_user['project_id']))
		all_authors = gitlab.get_all_authors_in_all_merges(all_merges)
		to_return = []
		for author in all_authors:
			all_merge_by_username = gitlab.get_all_merge_by_author(all_merges, author)
			for merge_by_username in all_merge_by_username:
				this_year = datetime.now().year
				this_month = datetime.now().month - 3
				total_weight_by_user_and_month = 0
				while this_month <= datetime.now().month:
					if (int(this_month) < 10):
						this_month = f'0{this_month}'
						dt = merge_by_username['merged_at'].split('T')[0].split('-')
						if (dt[0] == str(this_year)) and (dt[1] == this_month):
							weight = gitlab.get_weight_by_merge(merge_by_username['id'])
							if weight:
								total_weight_by_user_and_month += weight
				to_return.append({
					'username': author,
					'month': this_month,
					'weight': total_weight_by_user_and_month,
				})
			return jsonify(to_return)
	except Exception as e:
		print(e)
		return ("error while fetching data", 400)

@app.route('/fetch', methods=["POST"])
def fetch_info():
	try:
		access_token = request.form.get("access_token")
		refresh_token = request.form.get("refresh_token")
		uri_gitlab = request.form.get("uri_gitlab")
		basic_auth = request.form.get("basic_auth")
		if not access_token or not uri_gitlab:
			raise Exception("Access or refresh token is empty")
		user = gitlab.get_user_info(access_token, uri_gitlab, basic_auth)
		last_fetch = get_last_fetch_request(user['email'])
		insert_new_fetch_request(user['email'])
		all_projects = gitlab.get_all_project_by_user(access_token, uri_gitlab, basic_auth)
		all_merges = []
		for project in all_projects:
			all_merges += find_all_merges_by_project_id(project['id'])
			create_project(project)
			create_project_user(project['id'], user['username'])
		all_merges += gitlab.get_all_merge_request_by_project_id(access_token, all_projects, uri_gitlab, last_fetch, basic_auth)
		for merge in all_merges:
			if merge['state'] == 'merged':
					create_merge(merge)
		create_user(user, {
			'access_token': access_token,
			'refresh_token': refresh_token,
		})
		add_new_login(user['email'])
		print('finish')
		return jsonify({
			'username': user['username'],
		})
	except Exception as e:
		print(e)
		return ("error while fetching data", 400)

if __name__ == "__main__":
	app.run(host="0.0.0.0", port="1240")
