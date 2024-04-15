from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI()


@app.get('/')
def root():
    return {'message': 'Hello World'}


@app.get('/about')
def about():
    return 'Стартовое веб-приложение на FastAPI'
