from waitress import serve

from statsapp.wsgi import application

if __name__ == '__main__':
    serve(
        application,
        threads=16,
        port='8000'
    )