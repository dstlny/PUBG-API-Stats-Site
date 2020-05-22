from waitress import serve

from statsapp.wsgi import application
import multiprocessing

threads = int((multiprocessing.cpu_count() * 2) + 1)

if __name__ == '__main__':
	serve(
		application,
		threads=threads,
		port='8000'
	)