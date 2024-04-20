import time
import numpy as np
import pandas as pd
from pycoingecko import CoinGeckoAPI
from fastapi import FastAPI, status, HTTPException
from fastapi.responses import Response, RedirectResponse
from typing import List, Dict

cg = CoinGeckoAPI()
app = FastAPI()


@app.get('/')
def root():
    return RedirectResponse('/docs')


@app.get('/api/get_coins')
def get_coins():
    """Список монет."""
    coins_all = cg.get_coins_list()
    coins = {}

    for coin_data in coins_all:
        coins[coin_data['id']] = coin_data['name']

    return coins


@app.get('/api/get_coins_info')
def get_coins_info() -> List[Dict]:
    return cg.get_coins_markets(vs_currency='usd')


@app.get('/api/get_coins_info_small')
def get_coins_info_small():
    """Краткая информация для отображения монет."""
    coins = get_coins_info()

    coins_sml = [
        {
            'id': coin['id'],
            'name': coin['name'],
            'price': coin['current_price'],
            'percent_24h': coin['price_change_percentage_24h'],
            'icon': coin['image'],
            'symbol': coin['symbol'],
            'cap_rank': coin['market_cap_rank']
        } for coin in coins
    ]

    return coins_sml


@app.get('/api/{coin}/get_graph_info', status_code=status.HTTP_200_OK)
def get_graph_info(coin, days):
    """Получить ценовую информацию о монете для построения графика."""
    coins = cg.get_coin_ohlc_by_id(id=coin, vs_currency='usd', days=days, precision='5')

    price_to_candles = [
        {
            'time': coin[0],
            'open_price': coin[1],
            'high_price': coin[2],
            'low_price': coin[3],
            'close_price': coin[4]
        } for coin in coins
    ]

    return price_to_candles


def get_historical_data(coin_id):
    """Получить исторические данные о ценах на криптовалюту за последние 30 дней."""
    historical_data = cg.get_coin_market_chart_by_id(id=coin_id, vs_currency='usd', days=30)

    return historical_data['prices']


def moving_average(prices, window_size):
    """Вычислить простую скользящую среднюю (SMA) для списка цен."""
    weights = np.ones(window_size) / window_size

    return np.convolve(prices, weights, mode='valid')


def exponential_moving_average(prices, span=20):
    """Вычислить экспоненциальную скользящую среднюю (EMA) для списка цен."""
    return pd.Series(prices).ewm(span=span, adjust=False).mean().values


def rsi(prices, period=14):
    """Рассчитать относительный индекс силы (RSI)."""
    deltas = np.diff(prices)
    seed = deltas[:period + 1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs)

    for i in range(period, len(prices)):
        delta = deltas[i - 1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period

        rs = up / down
        rsi[i] = 100. - 100. / (1. + rs)

    return rsi


@app.get('/api/{coin}/advanced_analyze', status_code=status.HTTP_200_OK)
def advanced_analyze_coin_investment(coin: str):
    """Провести расширенный анализ криптовалюты на основе исторических данных."""
    historical_data = get_historical_data(coin)
    prices = [x[1] for x in historical_data]

    if len(prices) > 30:
        ma = moving_average(prices, 30)[-1]
        ema = exponential_moving_average(prices)[-1]
        rsi_value = rsi(np.array(prices))[-1]
        current_price = prices[-1]

        advice = 'Данные анализа:'

        if current_price > ema and rsi_value < 30 and current_price < ma:
            advice += ' Покупайте - Цена выше EMA, ниже SMA и RSI показывает перепроданность.'
        elif current_price < ema and rsi_value > 70 and current_price > ma:
            advice += ' Продавайте - Цена ниже EMA, выше SMA и RSI показывает перекупленность.'
        else:
            advice += ' Держите - Цена приблизительно равна EMA или RSI в нейтральной зоне.'

        return {
            'advice': advice,
            'current_price': current_price,
            'moving_average': ma,
            'EMA': ema,
            'RSI': rsi_value
        }
    else:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Недостаточно данных для анализа.')