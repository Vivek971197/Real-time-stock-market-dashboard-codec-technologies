import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta
import ta

# --- Fetch stock data ---
def fetch_stock_data(ticker, period, interval):
    end_date = datetime.now()
    if period == '1wk':
        start_date = end_date - timedelta(days=7)
        data = yf.download(ticker, start=start_date, end=end_date, interval=interval)
    else:
        data = yf.download(ticker, period=period, interval=interval)
    return data

# --- Process data & flatten columns ---
def process_data(data):
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = [' '.join(col).strip() for col in data.columns.values]
    if data.index.tzinfo is None:
        data.index = data.index.tz_localize('UTC')
    data.index = data.index.tz_convert('US/Eastern')
    data.reset_index(inplace=True)
    if 'Date' in data.columns:
        data.rename(columns={'Date': 'Datetime'}, inplace=True)
    elif 'Datetime' not in data.columns:
        data.rename(columns={data.columns[0]: 'Datetime'}, inplace=True)
    return data

# --- Normalize Yahoo Finance columns ---
def normalize_column_names(data):
    col_map = {}
    for col in data.columns:
        if 'Open' in col: col_map[col] = 'Open'
        elif 'High' in col: col_map[col] = 'High'
        elif 'Low' in col: col_map[col] = 'Low'
        elif 'Close' in col: col_map[col] = 'Close'
        elif 'Volume' in col: col_map[col] = 'Volume'
    data.rename(columns=col_map, inplace=True)
    return data

# --- Calculate Metrics ---
def calculate_metrics(data):
    last_close = float(data['Close'].iloc[-1])
    prev_close = float(data['Close'].iloc[0])
    change = last_close - prev_close
    pct_change = (change / prev_close) * 100
    high = float(data['High'].max())
    low = float(data['Low'].min())
    volume = int(data['Volume'].sum())
    return last_close, change, pct_change, high, low, volume

# --- Add Indicators ---
def add_technical_indicators(data):
    close_series = data['Close']
    if isinstance(close_series, pd.DataFrame) or len(close_series.shape) > 1:
        close_series = close_series.squeeze()
    data['SMA_20'] = ta.trend.sma_indicator(close_series, window=20)
    data['EMA_20'] = ta.trend.ema_indicator(close_series, window=20)
    return data

# --- Streamlit Layout ---
st.set_page_config(layout="wide")
st.title('Real Time Stock Dashboard')

# --- Sidebar Controls ---
st.sidebar.header('Chart Parameters')
ticker = st.sidebar.text_input('Ticker', 'ADBE')
time_period = st.sidebar.selectbox('Time Period', ['1d', '1wk', '1mo', '1y', 'max'])
chart_type = st.sidebar.selectbox('Chart Type', ['Candlestick', 'Line'])
indicators = st.sidebar.multiselect('Technical Indicators', ['SMA 20', 'EMA 20'])

interval_mapping = {
    '1d': '5m',
    '1wk': '30m',
    '1mo': '1d',
    '1y': '1wk',
    'max': '1wk'
}

# --- Main Chart Area ---
if st.sidebar.button('Update'):
    try:
        data = fetch_stock_data(ticker, time_period, interval_mapping[time_period])
        if data.empty or len(data) < 2:
            st.warning("Not enough data to display chart.")
        else:
            data = process_data(data)
            data = normalize_column_names(data)
            last_close, change, pct_change, high, low, volume = calculate_metrics(data)
            data = add_technical_indicators(data)

            st.metric(f"{ticker} Last Price", f"{last_close:.2f} USD", f"{change:.2f} ({pct_change:.2f}%)")
            col1, col2, col3 = st.columns(3)
            col1.metric("High", f"{high:.2f} USD")
            col2.metric("Low", f"{low:.2f} USD")
            col3.metric("Volume", f"{volume:,}")

            if chart_type == 'Candlestick' and len(data) >= 5:
                fig = go.Figure()
                fig.add_trace(go.Candlestick(
                    x=data['Datetime'],
                    open=data['Open'],
                    high=data['High'],
                    low=data['Low'],
                    close=data['Close']
                ))
            else:
                if chart_type == 'Candlestick':
                    st.warning("Not enough candles. Showing line chart instead.")
                fig = px.line(data, x='Datetime', y='Close')

            for indicator in indicators:
                if indicator == 'SMA 20':
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['SMA_20'], name='SMA 20'))
                elif indicator == 'EMA 20':
                    fig.add_trace(go.Scatter(x=data['Datetime'], y=data['EMA_20'], name='EMA 20'))

            fig.update_layout(title=f'{ticker} {time_period.upper()} Chart',
                              xaxis_title='Time', yaxis_title='Price (USD)', height=600)
            st.plotly_chart(fig, use_container_width=True)

            st.subheader('Historical Data')
            st.dataframe(data[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']])
            st.subheader('Technical Indicators')
            st.dataframe(data[['Datetime', 'SMA_20', 'EMA_20']])
    except Exception as e:
        st.error(f"An error occurred: {e}")

# --- Sidebar Real-Time Prices ---
st.sidebar.header('Real-Time Stock Prices')
stock_symbols = ['AAPL', 'GOOGL', 'AMZN', 'MSFT']
for symbol in stock_symbols:
    real_time_data = fetch_stock_data(symbol, '1d', '1m')
    if not real_time_data.empty:
        if isinstance(real_time_data.columns, pd.MultiIndex):
            real_time_data.columns = [' '.join(col).strip() for col in real_time_data.columns.values]
        real_time_data = process_data(real_time_data)
        real_time_data = normalize_column_names(real_time_data)

        try:
            last_price = float(real_time_data['Close'].iloc[-1])
            open_price = float(real_time_data['Open'].iloc[0])
            change = last_price - open_price
            pct_change = (change / open_price) * 100
            st.sidebar.metric(f"{symbol}", f"{last_price:.2f} USD", f"{change:.2f} ({pct_change:.2f}%)")
        except Exception as e:
            st.sidebar.warning(f"Data error for {symbol}: {e}")

# --- About Section ---
st.sidebar.subheader('About')
st.sidebar.info('This dashboard provides real-time stock prices and technical indicators using Yahoo Finance.')
