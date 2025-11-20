import argparse
import os
import sys
import re
import gzip
from tempfile import gettempdir
from urllib import request

import yed

def error(msg): # Вывод ошибки
	print(f"Ошибка: {msg}", file=sys.stderr)
	sys.exit(2)


def is_valid_url(url: str): # Проверка URL
	regex_pattern = re.compile(
		r"^(?:http|ftp)s?://"
		r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?$)"
		r"(?::\d+)?"
		r"(?:/?|[/?]\S+)$", re.IGNORECASE)
	return re.match(regex_pattern, url) is not None


def parse_args(argv=None): # Парсин аргументов
	parser = argparse.ArgumentParser() # Парсер аргументов командной строки

	# Имя анализируемого пакета
	parser.add_argument(
		"-p", "--package",
		required=True,
	)

	# URL репозитория или путь к файлу тестового репозитория
	repo_group = parser.add_mutually_exclusive_group(required=True) # Требуется либо --repo-url либо --repo-path
	repo_group.add_argument(
		"--repo-url"
	)
	repo_group.add_argument(
		"--repo-path"
	)

	# Режим работы с тестовым репозиторием
	parser.add_argument(
		"--test-mode",
		choices=["off", "on"],
		default="off"
	)

	# Режим вывода в ASCII-дереве
	parser.add_argument(
		"--ascii-tree",
		choices=["off", "on"],
		default="off"
	)

	# Максимальная глубина анализа зависимостей
	parser.add_argument(
		"--max-depth",
		type=int,
		default=5
	)

	# Подстрока для фильтра пакетов
	parser.add_argument(
		"--filter",
		dest="filter_substr",
		default=""
	)

	args = parser.parse_args(argv)
	return args


def validate_args(args):
	# package: не пустое без пробелов
	if not args.package or not args.package.strip():
		error("Параметр --package пуст или содержит только пробелы.")
	if " " in args.package:
		error("Параметр --package не должен содержать пробелов.")

	# repo-url или repo-path: проверяем URL или путь
	if args.repo_url:
		if not is_valid_url(args.repo_url):
			error(f"Неправильный формат URL репозитория: '{args.repo_url}'")
	else:
		rp = args.repo_path
		if not rp or not rp.strip():
			error("Параметр --repo-path пуст.")
		# проверяем существование пути
		if not os.path.exists(rp):
			error(f"Указанный путь --repo-path не найден: '{rp}'")

	# test-mode: валидация совместимости
	if args.test_mode == "off" and args.repo_path:
		# если тестовый режим выключен, но задан локальный путь это ошибка
		error("Вы указали --repo-path, но --test-mode установлен в 'off'. Для работы с локальным репозиторием установите --test-mode readonly или simulate.")

	# max-depth: целое и не меньше 0
	if args.max_depth is None:
		error("Параметр --max-depth не задан.")
	if not isinstance(args.max_depth, int) or args.max_depth < 0:
		error("--max-depth должен быть целым числом >= 0.")


def print_config(args): # Вывод в формате ключ=значение
	cfg = {
		"package": args.package,
		"repo_url": args.repo_url if args.repo_url else "",
		"repo_path": args.repo_path if args.repo_path else "",
		"test_mode": args.test_mode,
		"ascii_tree": args.ascii_tree,
		"max_depth": args.max_depth,
		"filter": args.filter_substr,
	}
	for k, v in cfg.items():
		if v:
			print(f"{k}={v!s}")


def parse_repo_url(url, package): #parse url repo
	try:
		request.urlretrieve(url + "/Packages.gz", gettempdir() + "\\Packages.gz")
		with gzip.open(gettempdir() + "\\Packages.gz", "rt", encoding="utf-8") as f:
			return f.read()
	except Exception as e:
		raise ValueError("Invalid repo")


def parse_path_repo(path, package): #parse path repo
	try:
		with open(path, "rt", encoding="utf-8") as f:
			return f.read()
	except Exception as e:
		raise ValueError("Invalid repo")


def load_packages(text): # load packs from package file
	packages = {}
	for line in text.split("\n"):
		if line.startswith('Package:'):
			name = line.split()[1]
			packages[name] = set()
		elif re.match(r'(Pre-|)Depends:', line):
			deps = re.sub(r'(Pre-|)Depends:|:any|,|\||\([^,]+\)', ' ', line)
			packages[name] |= set(deps.split())
	return packages


def make_graph(root, packages, dep, fl): # create dependations graph
	def dfs(name, depth = dep, filter = fl):
		if depth:
			graph[name] = set()
			for dep in packages.get(name, set()):
				if filter not in dep:
					if dep not in graph:
						dfs(dep, depth - 1)
					if dep in seen:
						graph[name].add(dep)
			seen.add(name)
		else:
			return
	seen = set()
	graph = {}
	dfs(root)
	return graph


def viz(graph, path): # yED generator(not used)
	y = yed.Graph()
	nodes = {}
	for name in graph:
		nodes[name] = y.node(text=name, font_family='Times New Roman', shape='box', height=25)
	for name, deps in graph.items():
		for dep in deps:
			y.edge(nodes[name], nodes[dep])
	y.save(f'{path}.graphml')


def print_ascii_tree(graph, root, prefix=""): # ascii tree generator
	print(prefix + root)
	for dep in graph.get(root, []):
		print_ascii_tree(graph, dep, prefix + "  ├─ ")


d = ["@startwbs"]
def graph_to_plantuml(graph, root, prefix="*"): # Uml generator
	global d
	d += [prefix + " " + root]
	for dep in graph.get(root, []):
		graph_to_plantuml(graph, dep, prefix + "*")

def main(argv=None):
	try:
		global d
		args = parse_args(argv)
		validate_args(args)
		if not args.repo_path:
			pars = parse_repo_url(args.repo_url, args.package)
		else:
			pars = parse_path_repo(args.repo_path, args.package)
		packs = load_packages(pars)
		if args.package in packs:
			graph = make_graph(args.package, packs, args.max_depth, args.filter_substr)
			#stage 4
			mas = []
			stage = 5
			if stage == 4:
				for i in reversed(graph):
					for j in graph[i]:
						if j not in mas:
							mas += [j]
				print("\n".join(mas))

			# planetUML http://editor.plantuml.com/
			with open("grph.txt", 'w') as f:
				graph_to_plantuml(graph, args.package)
				d += ["@endwbs"]
				f.write("\n".join(d))
				print("\n".join(d) + "\n")
			# ascii-tree
			if args.ascii_tree == "on":
				print_ascii_tree(graph, args.package)
		else:
			print("Пакет отсутствует")
	except SystemExit as e:
		# argparse использует SystemExit если код != 0 — считаем это ошибкой парсинга
		if e.code != 0:
			raise
		else:
			return
	except Exception as exc:
		error(exc)

main()