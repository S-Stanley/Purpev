from dotenv import load_dotenv
import os, requests, json, sys
from tqdm import tqdm

load_dotenv()

def find_author_or_create(arr, item):
	for tmp in arr:
		if tmp['username'] == item['author']['username']:
			tmp['merges'].append(item)
			return
	arr.append({
		'username': item['author']['username'],
		'merges': [item]
	})

def sort_by_merges_number(e):
	return len(e['merges'])

def get_grad(nb_merge):
	with open('grad.json', 'r') as f:
		all_grades = json.loads(f.read())
	for grade in all_grades:
		if int(grade['number']) <= nb_merge:
			previous = grade['name']
			continue
		else:
			return previous

def get_level(nb_merge: int):
	with open('grad.json', 'r') as f:
		all_grades = json.loads(f.read())
	for grade in all_grades:
		if int(grade['number']) <= nb_merge:
			previous = grade['level']
			continue
		else:
			return previous

def count_merges(data):
	output = []
	for merge in tqdm(data):
		if 'state' in merge and merge['state'] == 'merged':
			find_author_or_create(output, merge)
	output.sort(reverse=True, key=sort_by_merges_number)
	to_return = []
	for i in output:
		to_return.append({
			'username': i['username'],
			'merges': len(i['merges']),
			'grade': get_grad(len(i['merges'])),
			'level': get_level(len(i['merges'])),
		})
	return to_return

def get_all_merge_request_by_project_id(access_token, projects, uri_gitlab, last_fetch):
	output = []
	for project in projects:
		items_get = 100
		page = 0
		while items_get == 100:
			page += 1
			if (last_fetch):
				url = '{}/api/v4/projects/{}/merge_requests?access_token={}&per_page=100&page={}&created_after={}'.format(uri_gitlab, project['id'], access_token, page, last_fetch)
			else:
				url = '{}/api/v4/projects/{}/merge_requests?access_token={}&per_page=100&page={}'.format(uri_gitlab, project['id'], access_token, page)
			req = requests.get(url)
			items_get = len(req.json())
			for i in req.json():
				output.append(dict(i))
	print(len(output))
	with open('merges.json', 'w') as f:
		f.write(json.dumps(output))
	return output


def get_user_info(access_token, uri_gitlab):
	url = '{}/api/v4/user?access_token={}'.format(uri_gitlab, access_token)
	req = requests.get(url)
	return (req.json())

def get_all_project_by_user(access_token, uri_gitlab):
	url = '{}/api/v4/projects?membership=true&access_token={}'.format(uri_gitlab, access_token)
	req = requests.get(url)
	with open('projects.json', 'w') as f:
		f.write(json.dumps(req.json()))
	return req.json()

def get_auth_uri():
	url = 'https://gitlab.com/oauth/authorize?client_id={}&redirect_uri={}&response_type=code&state={}&scope={}'.format(
		os.environ['client_id'],
		os.environ['redirect_uri'],
		os.environ['state'],
		os.environ['scope'],
	)
	return url

def get_token(code):
	data = {
		'client_id': os.environ['client_id'],
		'code' : code,
		'grant_type': 'authorization_code',
		'redirect_uri': os.environ['redirect_uri'],
		'client_secret': os.environ['client_secret'],
	}
	url = f'https://gitlab.com/oauth/token'
	req = requests.post(url, data)
	print(req.status_code, req.text)
	return req.json()
