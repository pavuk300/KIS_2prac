import argparse
import os
import sys
import re

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
		choices=["off", "readonly", "simulate"],
		default="off"
	)

	# Режим вывода в ASCII-дереве
	parser.add_argument(
		"--ascii-tree",
		choices=["off", "simple", "detailed"],
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

def main(argv=None):
	try:
		args = parse_args(argv)
		validate_args(args)
		print_config(args)
	except SystemExit as e:
		# argparse использует SystemExit если код != 0 — считаем это ошибкой парсинга
		if e.code != 0:
			raise
		else:
			return
	except Exception as exc:
		error(f"Необработанная ошибка: {exc}")

main()