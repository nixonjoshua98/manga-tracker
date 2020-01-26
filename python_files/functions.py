import subprocess
import requests


from sqlalchemy.inspection import inspect

from python_files.common.functions import *


def send_request(url):
	headers = requests.utils.default_headers()

	try:
		page = requests.get(url, stream=True, timeout=5, headers=headers)

	except:
		return None

	else:
		return page if page.status_code == 200 else None


def remove_trailing_zeros_if_zero(n):
	if is_float(n):
		if str(n).count(".") == 0 or str(n).endswith(".0"):
			return int(n)

		else:
			return float(n)

	return n


def is_float(f) -> bool:
	try:
		float(f)

	except ValueError:
		return False

	else:
		return True


def find_obj_with_attr(attr, val, arr) -> int:
	for i, ele in enumerate(arr):
		if getattr(ele, attr) == val:
			return i
	return -1


def callback_once_true(master, attr, search_obj, callback):
	if getattr(search_obj, attr):
		callback()
	else:
		master.after(100, callback_once_true, master, attr, search_obj, callback)


def get_latest_offline_chapter(title: str) -> float or int:
	manga_dir = os.path.join(constants.MANGA_DIR, title)

	if os.path.isdir(manga_dir):
		files = os.listdir(manga_dir)

		return max(map(lambda f: remove_trailing_zeros_if_zero(f.split()[-1].replace(".pdf", "")), files))
	return 0


def open_manga_in_explorer(title):
	path = os.path.join(constants.MANGA_DIR, remove_nasty_chars(title))

	subprocess.call("explorer {}".format(path, shell=True))


def get_table_fields(table) -> list:
	return table.__table__.columns.keys()


def get_table_pk(tbl) -> str:
	return inspect(tbl).primary_key[0].name


def get_non_pk_fields(table) -> list:
	table_fields = get_table_fields(table)
	pk = get_table_pk(table)
	table_fields.remove(pk)
	return table_fields


def all_fields_have_value(table, fields_given, ignore_pk=True):
	# Don't check if the primary key has been given a value (normally because it auto-increments)
	if ignore_pk:
		table_fields = get_non_pk_fields(table)
	else:
		table_fields = get_table_fields()

	# All fields have been given a value
	return all(map(lambda f: f in fields_given, table_fields))


def can_make_row(table, **values):
	try:
		table(**values)

	except TypeError as e:
		return False

	else:
		return True
