from waitress import serve

from statsapp.wsgi import application

if __name__ == '__main__':
    serve(
        application,
        threads=8,
        port='8000'
    )