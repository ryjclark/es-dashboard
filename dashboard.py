import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import yfinance as yf
import ta
import json
import os

# Initialize session state
if 'support_levels' not in st.session_state:
    st.session_state.support_levels = [
        {"price": 6022, "major": True},
        {"price": 6016, "major": False},
        {"price": 6006, "major": False},
        {"price": 6002, "major": False},
        {"price": 5996, "major": True}
    ]

if 'resistance_levels' not in st.session_state:
    st.session_state.resistance_levels = [
        {"price": 6027, "major": False},
        {"price": 6033, "major": True},
        {"price": 6043, "major": False},
        {"price": 6054, "major": False}
    ]

if 'dynamic_zone' not in st.session_state:
    st.session_state.dynamic_zone = {'top': 6143.0, 'bottom': 6105.0}
if 'magnet_price' not in st.session_state:
    st.session_state.magnet_price = 6130.0

# Page config
st.set_page_config(page_title="ES Futures Dashboard", page_icon="📈", layout="wide")

# Sidebar
with st.sidebar:
    st.header("ES Futures Settings")
    
    # Quick Level Add
    st.subheader("Quick Add Level")
    quick_price = st.number_input("Price", step=0.25)
    col1, col2 = st.columns(2)
    with col1:
        level_type = st.radio("Type", ["Support", "Resistance"])
    with col2:
        is_major = st.checkbox("Major")
    
    if st.button("Add"):
        if level_type == "Support":
            st.session_state.support_levels.append({"price": quick_price, "major": is_major})
            st.session_state.support_levels.sort(key=lambda x: x['price'])
        else:
            st.session_state.resistance_levels.append({"price": quick_price, "major": is_major})
            st.session_state.resistance_levels.sort(key=lambda x: x['price'])
    
    # Dynamic Zone Settings
    st.subheader("Dynamic Zone")
    dynamic_top = st.number_input("Zone Top", value=st.session_state.dynamic_zone['top'], step=0.25)
    dynamic_bottom = st.number_input("Zone Bottom", value=st.session_state.dynamic_zone['bottom'], step=0.25)
    magnet_price = st.number_input("Magnet", value=st.session_state.magnet_price, step=0.25)
    
    if st.button("Update Zones"):
        st.session_state.dynamic_zone['top'] = dynamic_top
        st.session_state.dynamic_zone['bottom'] = dynamic_bottom
        st.session_state.magnet_price = magnet_price

# Main content
tab1, tab2 = st.tabs(["Chart", "Level Management"])

with tab1:
    # Chart settings
    col1, col2, col3 = st.columns(3)
    with col1:
        timeframe = st.selectbox("Timeframe", ['1m', '5m', '15m', '1h'], index=1)
    with col2:
        show_ema = st.checkbox("Show EMAs", value=True)
    with col3:
        show_volume = st.checkbox("Show Volume", value=True)

    # Get data
    @st.cache_data(ttl=60)
    def get_data(timeframe):
        symbol = "ES=F"
        data = yf.download(symbol, start=datetime.now() - timedelta(days=3), interval=timeframe)
        if show_ema:
            data['EMA_5'] = ta.trend.ema_indicator(data['Close'], window=5)
            data['EMA_13'] = ta.trend.ema_indicator(data['Close'], window=13)
        return data

    data = get_data(timeframe)

    def create_chart(data):
        fig = go.Figure()
        
        # Dynamic Zone
        fig.add_scatter(
            x=[data.index[0], data.index[0], data.index[-1], data.index[-1]],
            y=[st.session_state.dynamic_zone['bottom'], st.session_state.dynamic_zone['top'],
               st.session_state.dynamic_zone['top'], st.session_state.dynamic_zone['bottom']],
            fill="toself",
            fillcolor='rgba(128, 128, 128, 0.2)',
            line=dict(color='gray', width=1),
            name="Dynamic Zone"
        )
        
        # Support Levels
        for level in st.session_state.support_levels:
            fig.add_hline(
                y=level["price"],
                line_color='green',
                line_width=2 if level["major"] else 1,
                line_dash='solid' if level["major"] else 'dot',
            )
        
        # Resistance Levels
        for level in st.session_state.resistance_levels:
            fig.add_hline(
                y=level["price"],
                line_color='red',
                line_width=2 if level["major"] else 1,
                line_dash='solid' if level["major"] else 'dot',
            )
        
        # Magnet Price
        fig.add_hline(
            y=st.session_state.magnet_price,
            line_color='blue',
            line_width=2,
            line_dash='dot',
        )
        
        # Candlesticks
        fig.add_trace(go.Candlestick(
            x=data.index,
            open=data['Open'],
            high=data['High'],
            low=data['Low'],
            close=data['Close'],
            name='ES'
        ))
        
        # EMAs
        if show_ema and 'EMA_5' in data.columns:
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['EMA_5'],
                name='EMA 5',
                line=dict(color='#2962ff', width=1)
            ))
            fig.add_trace(go.Scatter(
                x=data.index,
                y=data['EMA_13'],
                name='EMA 13',
                line=dict(color='#ff6d00', width=1)
            ))
        
        # Layout
        fig.update_layout(
            height=800,
            template="plotly_dark",
            xaxis_rangeslider_visible=False,
            margin=dict(l=50, r=50, t=50, b=50),
            showlegend=True,
        )
        
        # Add volume
        if show_volume:
            colors = ['green' if row['Close'] >= row['Open'] else 'red' 
                     for index, row in data.iterrows()]
            fig.add_trace(go.Bar(
                x=data.index,
                y=data['Volume'],
                name='Volume',
                marker_color=colors,
                yaxis='y2'
            ))
            
            fig.update_layout(
                yaxis2=dict(
                    title="Volume",
                    overlaying="y",
                    side="right",
                    showgrid=False
                )
            )
        
        return fig

    # Display chart
    st.plotly_chart(create_chart(data), use_container_width=True)
    
    # Current price metrics
    current_price = data['Close'].iloc[-1]
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Current Price", f"{current_price:.2f}")
    with col2:
        zone_status = "Inside" if st.session_state.dynamic_zone['bottom'] <= current_price <= st.session_state.dynamic_zone['top'] else "Outside"
        st.metric("Dynamic Zone Status", zone_status)
    with col3:
        magnet_diff = current_price - st.session_state.magnet_price
        st.metric("Distance to Magnet", f"{magnet_diff:.2f}")

with tab2:
    st.header("Level Management")
    
    # Save/Load Levels
    col1, col2 = st.columns(2)
    with col1:
        save_name = st.text_input("Save Name", "default")
        if st.button("Save Levels"):
            levels = {
                "support": st.session_state.support_levels,
                "resistance": st.session_state.resistance_levels,
                "dynamic_zone": st.session_state.dynamic_zone,
                "magnet_price": st.session_state.magnet_price
            }
            with open(f"data/{save_name}.json", "w") as f:
                json.dump(levels, f)
            st.success(f"Saved levels as {save_name}")
    
    with col2:
        if os.path.exists("data"):
            saved_files = [f.replace(".json", "") for f in os.listdir("data") if f.endswith(".json")]
            if saved_files:
                load_name = st.selectbox("Load Saved Levels", saved_files)
                if st.button("Load"):
                    with open(f"data/{load_name}.json", "r") as f:
                        levels = json.load(f)
                        st.session_state.support_levels = levels["support"]
                        st.session_state.resistance_levels = levels["resistance"]
                        st.session_state.dynamic_zone = levels["dynamic_zone"]
                        st.session_state.magnet_price = levels["magnet_price"]
                    st.success(f"Loaded levels from {load_name}")
    
    # Level Display and Edit
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Support Levels")
        for i, level in enumerate(st.session_state.support_levels):
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.write(f"{'🟢 Major' if level['major'] else '⚪ Minor'} - {level['price']}")
            with cols[1]:
                if st.button("Delete", key=f"del_s_{i}"):
                    st.session_state.support_levels.pop(i)
                    st.rerun()
    
    with col2:
        st.subheader("Resistance Levels")
        for i, level in enumerate(st.session_state.resistance_levels):
            cols = st.columns([3, 1, 1])
            with cols[0]:
                st.write(f"{'🔴 Major' if level['major'] else '⚪ Minor'} - {level['price']}")
            with cols[1]:
                if st.button("Delete", key=f"del_r_{i}"):
                    st.session_state.resistance_levels.pop(i)
                    st.rerun()

